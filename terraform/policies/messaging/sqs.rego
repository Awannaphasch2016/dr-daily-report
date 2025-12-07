package terraform.policies.messaging.sqs

import rego.v1

# Policy: SQS queues must have appropriate configuration for parallel processing

# Get all SQS queue resources from Terraform plan
sqs_queues := [queue |
    some path, value in input.resource_changes
    value.type == "aws_sqs_queue"
    queue := {
        "address": value.address,
        "change": value.change,
        "name": value.name,
    }
]

# DENY: SQS queues must have visibility timeout >= 900s (15 min)
# This matches Lambda max timeout to prevent duplicate processing
deny contains msg if {
    some queue in sqs_queues
    queue.change.actions[_] != "delete"

    visibility_timeout := object.get(queue.change.after, "visibility_timeout_seconds", 30)
    visibility_timeout < 900

    msg := sprintf(
        "SQS queue '%s' has visibility_timeout_seconds=%d, must be >= 900 (15 min) to match Lambda timeout",
        [queue.address, visibility_timeout]
    )
}

# DENY: SQS queues should have message retention >= 345600s (4 days)
# Allow debugging failed jobs
deny contains msg if {
    some queue in sqs_queues
    queue.change.actions[_] != "delete"

    retention := object.get(queue.change.after, "message_retention_seconds", 0)
    retention < 345600

    msg := sprintf(
        "SQS queue '%s' has message_retention_seconds=%d, should be >= 345600 (4 days) for debugging",
        [queue.address, retention]
    )
}

# DENY: SQS queues should enable long polling (reduce costs)
# receive_wait_time_seconds should be 20s
deny contains msg if {
    some queue in sqs_queues
    queue.change.actions[_] != "delete"

    wait_time := object.get(queue.change.after, "receive_wait_time_seconds", 0)
    wait_time < 20

    msg := sprintf(
        "SQS queue '%s' has receive_wait_time_seconds=%d, should be 20 for long polling (cost optimization)",
        [queue.address, wait_time]
    )
}

# Get all Lambda event source mappings
event_source_mappings := [mapping |
    some path, value in input.resource_changes
    value.type == "aws_lambda_event_source_mapping"
    mapping := {
        "address": value.address,
        "change": value.change,
        "name": value.name,
    }
]

# DENY: Event source mappings for SQS should have batch_size = 1 for max parallelism
deny contains msg if {
    some mapping in event_source_mappings
    mapping.change.actions[_] != "delete"

    # Check if this is an SQS event source (ARN contains 'sqs')
    event_source_arn := object.get(mapping.change.after, "event_source_arn", "")
    contains(event_source_arn, "sqs")

    batch_size := object.get(mapping.change.after, "batch_size", 0)
    batch_size != 1

    msg := sprintf(
        "Lambda event source mapping '%s' has batch_size=%d, should be 1 for maximum parallelism",
        [mapping.address, batch_size]
    )
}

# DENY: Event source mappings for SQS should have maximum_batching_window_in_seconds = 0
# No batching delay for immediate processing
deny contains msg if {
    some mapping in event_source_mappings
    mapping.change.actions[_] != "delete"

    event_source_arn := object.get(mapping.change.after, "event_source_arn", "")
    contains(event_source_arn, "sqs")

    batching_window := object.get(mapping.change.after, "maximum_batching_window_in_seconds", -1)
    batching_window != 0
    batching_window != null  # null is acceptable (defaults to 0)

    msg := sprintf(
        "Lambda event source mapping '%s' has maximum_batching_window_in_seconds=%d, should be 0 for immediate processing",
        [mapping.address, batching_window]
    )
}

# DENY: Event source mappings should be enabled
deny contains msg if {
    some mapping in event_source_mappings
    mapping.change.actions[_] != "delete"

    enabled := object.get(mapping.change.after, "enabled", true)
    enabled == false

    msg := sprintf(
        "Lambda event source mapping '%s' is disabled, should be enabled for processing",
        [mapping.address]
    )
}

# Get all IAM policy documents that grant SQS permissions
iam_policies := [policy |
    some path, value in input.resource_changes
    value.type == "aws_iam_policy"
    policy := {
        "address": value.address,
        "change": value.change,
        "policy_document": value.change.after.policy,
    }
]

# WARN: Scheduler Lambda should have SQS send permissions
# (This is a warning, not a deny, as permissions might be granted via role)
warn contains msg if {
    # Check if we're creating/updating a scheduler-related policy
    some policy in iam_policies
    policy.change.actions[_] != "delete"
    contains(policy.address, "scheduler")

    # Parse policy document (it's a JSON string)
    policy_doc := json.unmarshal(policy.policy_document)

    # Check if policy grants SQS SendMessage
    not has_sqs_send_permission(policy_doc)

    msg := sprintf(
        "IAM policy '%s' for scheduler should include sqs:SendMessage permission for parallel job distribution",
        [policy.address]
    )
}

# Helper: Check if policy document grants SQS SendMessage
has_sqs_send_permission(policy_doc) if {
    some statement in policy_doc.Statement
    statement.Effect == "Allow"

    # Check if Action includes sqs:SendMessage (can be string or array)
    action := statement.Action
    is_string(action)
    action == "sqs:SendMessage"
}

has_sqs_send_permission(policy_doc) if {
    some statement in policy_doc.Statement
    statement.Effect == "Allow"

    some action in statement.Action
    action == "sqs:SendMessage"
}

has_sqs_send_permission(policy_doc) if {
    some statement in policy_doc.Statement
    statement.Effect == "Allow"

    some action in statement.Action
    action == "sqs:*"
}
