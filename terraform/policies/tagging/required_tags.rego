# Required Tags Policy
#
# Enforces consistent tagging across all taggable resources:
# - Project: Identifies the project (e.g., "dr-daily-report")
# - Environment: Identifies the environment (dev, staging, prod)
# - ManagedBy: Identifies who manages the resource (e.g., "Terraform")
#
# Usage: conftest test tfplan.json --policy policies/

package terraform.tagging

import future.keywords.in
import future.keywords.if
import future.keywords.contains

# Required tags for all taggable resources
required_tags := {"Project", "Environment", "ManagedBy"}

# AWS resource types that support tags
taggable_resource_types := {
    "aws_lambda_function",
    "aws_dynamodb_table",
    "aws_s3_bucket",
    "aws_api_gateway_rest_api",
    "aws_apigatewayv2_api",
    "aws_iam_role",
    "aws_sqs_queue",
    "aws_sns_topic",
    "aws_cloudwatch_log_group",
    "aws_secretsmanager_secret",
    "aws_ecr_repository",
    "aws_rds_cluster",
    "aws_security_group",
    "aws_vpc",
    "aws_subnet",
    "aws_cloudfront_distribution"
}

# Check if resource type is taggable
is_taggable(resource_type) if {
    resource_type in taggable_resource_types
}

# Deny resources missing required tags
deny contains msg if {
    resource := input.resource_changes[_]
    resource.change.actions[_] == "create"
    is_taggable(resource.type)

    # Get tags or empty object if null
    tags := object.get(resource.change.after, "tags", {})
    tags != null

    # Find missing tags
    missing := required_tags - {key | tags[key]}
    count(missing) > 0

    msg := sprintf("Resource '%s' (%s) missing required tags: %v", [resource.address, resource.type, missing])
}

# Deny resources with null tags (no tags at all)
deny contains msg if {
    resource := input.resource_changes[_]
    resource.change.actions[_] == "create"
    is_taggable(resource.type)

    # Check if tags is null or not present
    not resource.change.after.tags

    msg := sprintf("Resource '%s' (%s) has no tags. Required tags: %v", [resource.address, resource.type, required_tags])
}

# Warn about inconsistent Environment tag values
warn contains msg if {
    resource := input.resource_changes[_]
    resource.change.actions[_] != "delete"
    is_taggable(resource.type)

    tags := resource.change.after.tags
    tags != null
    env := tags.Environment

    # Check for non-standard environment names
    not env in {"dev", "staging", "prod"}

    msg := sprintf("Resource '%s' uses non-standard Environment tag '%s'. Use 'dev', 'staging', or 'prod'.", [resource.address, env])
}

# Warn about inconsistent ManagedBy tag values
warn contains msg if {
    resource := input.resource_changes[_]
    resource.change.actions[_] != "delete"
    is_taggable(resource.type)

    tags := resource.change.after.tags
    tags != null
    managed_by := tags.ManagedBy

    # Check for non-standard ManagedBy values
    not managed_by in {"Terraform", "terraform"}

    msg := sprintf("Resource '%s' uses non-standard ManagedBy tag '%s'. Use 'Terraform'.", [resource.address, managed_by])
}
