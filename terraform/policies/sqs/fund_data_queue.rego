# OPA Policy: SQS Queue Security for Fund Data Sync
#
# Purpose: Pre-apply validation for fund-data-sync SQS queue
# Usage: conftest test tfplan.json --policy policies/
#
# Defensive Programming Principles:
# - Explicit failure detection (DENY rules block insecure configurations)
# - Fail fast and visibly (violations block terraform apply)
# - Configuration validation at startup (pre-apply, not post-deploy)

package terraform.sqs.fund_data_sync

import future.keywords.in

# ============================================================================
# Helper Functions
# ============================================================================

# Get all SQS queue resources from Terraform plan
queues[resource] {
    resource := input.resource_changes[_]
    resource.type == "aws_sqs_queue"
    resource.change.actions[_] == "create"
}

# Get all SQS queue resources being updated
queues[resource] {
    resource := input.resource_changes[_]
    resource.type == "aws_sqs_queue"
    resource.change.actions[_] == "update"
}

# Check if queue name matches fund data pattern
is_fund_data_queue(queue) {
    contains(queue.change.after.name, "fund-data")
}

# ============================================================================
# DENY Rules (Block Deployment on Violation)
# ============================================================================

# DENY: Queue without Dead Letter Queue
deny[msg] {
    queue := queues[_]
    is_fund_data_queue(queue)
    not queue.change.after.redrive_policy

    msg := sprintf(
        "DENY: SQS queue '%s' must have Dead Letter Queue configured. " +
        "ETL pipelines require DLQ for failed message investigation.",
        [queue.change.after.name]
    )
}

# DENY: DLQ maxReceiveCount too low
deny[msg] {
    queue := queues[_]
    is_fund_data_queue(queue)
    redrive_policy := queue.change.after.redrive_policy
    policy := json.unmarshal(redrive_policy)

    # maxReceiveCount should be 3-5 for ETL (balance between retries and poison messages)
    policy.maxReceiveCount < 3

    msg := sprintf(
        "DENY: SQS queue '%s' has maxReceiveCount=%d (too low). " +
        "ETL pipelines should allow 3-5 retries before sending to DLQ.",
        [queue.change.after.name, policy.maxReceiveCount]
    )
}

# DENY: DLQ maxReceiveCount too high
deny[msg] {
    queue := queues[_]
    is_fund_data_queue(queue)
    redrive_policy := queue.change.after.redrive_policy
    policy := json.unmarshal(redrive_policy)

    policy.maxReceiveCount > 5

    msg := sprintf(
        "DENY: SQS queue '%s' has maxReceiveCount=%d (too high). " +
        "Poison messages should move to DLQ after 5 failures.",
        [queue.change.after.name, policy.maxReceiveCount]
    )
}

# DENY: Visibility timeout too short for ETL processing
deny[msg] {
    queue := queues[_]
    is_fund_data_queue(queue)

    # ETL processing (CSV parse + batch upsert) takes ~5-30s
    # Visibility timeout should be 2x max processing time
    queue.change.after.visibility_timeout_seconds < 60

    msg := sprintf(
        "DENY: SQS queue '%s' has visibility_timeout=%ds (too short). " +
        "ETL processing requires minimum 60s to prevent duplicate processing.",
        [queue.change.after.name, queue.change.after.visibility_timeout_seconds]
    )
}

# DENY: Message retention too short for debugging
deny[msg] {
    queue := queues[_]
    is_fund_data_queue(queue)

    # Should retain messages for at least 1 day for investigation
    queue.change.after.message_retention_seconds < 86400

    msg := sprintf(
        "DENY: SQS queue '%s' has message_retention=%ds (too short). " +
        "ETL pipelines should retain messages for at least 1 day (86400s) for debugging.",
        [queue.change.after.name, queue.change.after.message_retention_seconds]
    )
}

# DENY: Missing required tags
deny[msg] {
    queue := queues[_]
    is_fund_data_queue(queue)

    required_tags := ["Environment", "Purpose", "DataSource"]
    missing_tags := [tag | tag := required_tags[_]; not queue.change.after.tags[tag]]

    count(missing_tags) > 0

    msg := sprintf(
        "DENY: SQS queue '%s' missing required tags: %v. " +
        "Tags enable cost tracking and resource management.",
        [queue.change.after.name, missing_tags]
    )
}

# DENY: Encryption not enabled
deny[msg] {
    queue := queues[_]
    is_fund_data_queue(queue)

    # SQS encryption should be enabled (SSE-SQS or SSE-KMS)
    not queue.change.after.kms_master_key_id
    not queue.change.after.sqs_managed_sse_enabled

    msg := sprintf(
        "DENY: SQS queue '%s' must enable encryption (SSE-SQS or SSE-KMS). " +
        "Fund data may contain sensitive financial information.",
        [queue.change.after.name]
    )
}

# ============================================================================
# WARN Rules (Allow Deployment but Log Warning)
# ============================================================================

# WARN: No environment suffix in queue name
warn[msg] {
    queue := queues[_]
    is_fund_data_queue(queue)

    # Queue name should end with -dev, -staging, -prod
    not endswith(queue.change.after.name, "-dev")
    not endswith(queue.change.after.name, "-staging")
    not endswith(queue.change.after.name, "-prod")

    msg := sprintf(
        "WARN: SQS queue '%s' should include environment suffix (-dev, -staging, -prod) " +
        "to prevent cross-environment message routing.",
        [queue.change.after.name]
    )
}

# WARN: Long polling not enabled
warn[msg] {
    queue := queues[_]
    is_fund_data_queue(queue)

    # receive_wait_time_seconds = 0 means short polling (more API calls, higher cost)
    queue.change.after.receive_wait_time_seconds == 0

    msg := sprintf(
        "WARN: SQS queue '%s' should enable long polling (receive_wait_time_seconds > 0) " +
        "to reduce API calls and costs.",
        [queue.change.after.name]
    )
}

# WARN: Max message size not configured
warn[msg] {
    queue := queues[_]
    is_fund_data_queue(queue)

    # Default is 256 KB, but CSV files could be larger
    not queue.change.after.max_message_size

    msg := sprintf(
        "WARN: SQS queue '%s' should explicitly set max_message_size. " +
        "CSV files from SQL Server exports may exceed defaults.",
        [queue.change.after.name]
    )
}

# WARN: Content-based deduplication not enabled for FIFO
warn[msg] {
    queue := queues[_]
    is_fund_data_queue(queue)
    endswith(queue.change.after.name, ".fifo")

    not queue.change.after.content_based_deduplication

    msg := sprintf(
        "WARN: FIFO queue '%s' should enable content_based_deduplication " +
        "to prevent duplicate S3 event processing.",
        [queue.change.after.name]
    )
}

# ============================================================================
# Validation Summary
# ============================================================================

# Pass if no DENY violations
pass {
    count(deny) == 0
}

# Summary report
summary := {
    "pass": pass,
    "deny_count": count(deny),
    "warn_count": count(warn),
    "violations": deny,
    "warnings": warn
}
