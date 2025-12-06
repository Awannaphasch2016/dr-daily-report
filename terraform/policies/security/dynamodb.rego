# DynamoDB Security Policy
#
# Enforces DynamoDB best practices:
# - Point-in-Time Recovery (PITR) for production tables
# - Encryption at rest
# - Deletion protection for production
#
# Usage: conftest test tfplan.json --policy policies/

package terraform.security.dynamodb

import future.keywords.in
import future.keywords.if
import future.keywords.contains

# Helper: Check if table is for production environment
is_production_table(resource) if {
    tags := resource.change.after.tags
    tags.Environment == "prod"
}

is_production_table(resource) if {
    contains(resource.change.after.name, "prod")
}

# Helper: Check if PITR is enabled
has_pitr_enabled(resource) if {
    resource.change.after.point_in_time_recovery[_].enabled == true
}

# Warn about DynamoDB tables without PITR (production only)
warn contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_dynamodb_table"
    resource.change.actions[_] != "delete"
    is_production_table(resource)
    not has_pitr_enabled(resource)
    msg := sprintf("Production DynamoDB table '%s' should enable Point-in-Time Recovery for data protection.", [resource.address])
}

# Warn about DynamoDB tables without deletion protection (production only)
warn contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_dynamodb_table"
    resource.change.actions[_] != "delete"
    is_production_table(resource)
    resource.change.after.deletion_protection_enabled != true
    msg := sprintf("Production DynamoDB table '%s' should enable deletion protection.", [resource.address])
}

# Deny DynamoDB tables with PAY_PER_REQUEST in production without scaling considerations
# (informational - PAY_PER_REQUEST is fine for most cases)
warn contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_dynamodb_table"
    resource.change.actions[_] != "delete"
    is_production_table(resource)
    resource.change.after.billing_mode == "PAY_PER_REQUEST"
    msg := sprintf("Production DynamoDB table '%s' uses PAY_PER_REQUEST billing. Consider PROVISIONED for predictable workloads.", [resource.address])
}

# Warn about tables without encryption specification (uses AWS default, which is fine)
# This is informational only
warn contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_dynamodb_table"
    resource.change.actions[_] == "create"
    not resource.change.after.server_side_encryption
    msg := sprintf("DynamoDB table '%s' uses default encryption. Consider customer-managed KMS key for compliance.", [resource.address])
}
