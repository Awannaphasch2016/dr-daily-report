# Encryption Security Policy
#
# Enforces encryption best practices:
# - Lambda environment variables should use KMS
# - Secrets Manager should use encryption
# - RDS/Aurora should use encryption at rest
#
# Usage: conftest test tfplan.json --policy policies/

package terraform.security.encryption

import future.keywords.in
import future.keywords.if
import future.keywords.contains

# Helper: Check if Lambda has sensitive environment variables
has_sensitive_env_vars(env_vars) if {
    some key
    env_vars[key]
    contains(lower(key), "password")
}

has_sensitive_env_vars(env_vars) if {
    some key
    env_vars[key]
    contains(lower(key), "secret")
}

has_sensitive_env_vars(env_vars) if {
    some key
    env_vars[key]
    contains(lower(key), "api_key")
}

# Warn about Lambda functions with sensitive environment variables without KMS encryption
warn contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_lambda_function"
    resource.change.actions[_] != "delete"

    env_vars := resource.change.after.environment[_].variables
    has_sensitive_env_vars(env_vars)

    # Check if KMS key is configured
    not resource.change.after.kms_key_arn

    msg := sprintf("Lambda '%s' has sensitive environment variables but no KMS encryption. Consider using AWS Secrets Manager.", [resource.address])
}

# Warn about RDS/Aurora clusters without encryption
warn contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_rds_cluster"
    resource.change.actions[_] == "create"
    resource.change.after.storage_encrypted != true

    msg := sprintf("Aurora cluster '%s' should enable encryption at rest (storage_encrypted = true).", [resource.address])
}

# Warn about RDS instances without encryption
warn contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_db_instance"
    resource.change.actions[_] == "create"
    resource.change.after.storage_encrypted != true

    msg := sprintf("RDS instance '%s' should enable encryption at rest (storage_encrypted = true).", [resource.address])
}

# Warn about Secrets Manager secrets without rotation
warn contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_secretsmanager_secret"
    resource.change.actions[_] != "delete"

    # Check if rotation is configured (hard to detect without full state)
    # This is a general reminder
    msg := sprintf("Secrets Manager secret '%s' should have rotation configured for production.", [resource.address])
}

# Deny CloudWatch Log Groups without encryption in production
warn contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_cloudwatch_log_group"
    resource.change.actions[_] == "create"

    # Check for production indicators
    contains(resource.address, "prod")

    # Check if KMS key is configured
    not resource.change.after.kms_key_id

    msg := sprintf("Production CloudWatch Log Group '%s' should use KMS encryption for sensitive logs.", [resource.address])
}
