# Lambda VPC Configuration Policy
#
# Enforces VPC configuration for Lambda functions that access Aurora:
# - Lambda with AURORA_HOST env var must have vpc_config
# - VPC config must include subnet_ids and security_group_ids
#
# This policy catches the bug where Report Worker Lambda couldn't connect
# to Aurora because it was missing vpc_config while having Aurora env vars.
#
# Usage: conftest test tfplan.json --policy policies/

package terraform.security.lambda_vpc

import future.keywords.in
import future.keywords.if
import future.keywords.contains

# Deny Lambda functions that have Aurora env vars but no VPC config
deny contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_lambda_function"
    resource.change.actions[_] != "delete"

    # Check if Lambda has Aurora environment variables
    env_vars := resource.change.after.environment[0].variables
    env_vars.AURORA_HOST != ""

    # Check if vpc_config is missing or empty
    not has_vpc_config(resource.change.after)

    msg := sprintf(
        "Lambda '%s' has AURORA_HOST env var but no vpc_config. Aurora is in VPC - Lambda must be in VPC to connect.",
        [resource.address]
    )
}

# Deny Lambda functions with Aurora env vars but empty vpc_config
deny contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_lambda_function"
    resource.change.actions[_] != "delete"

    # Check if Lambda has Aurora environment variables
    env_vars := resource.change.after.environment[0].variables
    env_vars.AURORA_HOST != ""

    # Check if vpc_config exists but has no subnets
    vpc_config := resource.change.after.vpc_config[0]
    count(vpc_config.subnet_ids) == 0

    msg := sprintf(
        "Lambda '%s' has vpc_config but no subnet_ids. Must specify subnets for Aurora connectivity.",
        [resource.address]
    )
}

# Deny Lambda functions with Aurora env vars but no security groups
deny contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_lambda_function"
    resource.change.actions[_] != "delete"

    # Check if Lambda has Aurora environment variables
    env_vars := resource.change.after.environment[0].variables
    env_vars.AURORA_HOST != ""

    # Check if vpc_config exists but has no security groups
    vpc_config := resource.change.after.vpc_config[0]
    count(vpc_config.security_group_ids) == 0

    msg := sprintf(
        "Lambda '%s' has vpc_config but no security_group_ids. Must specify security groups for Aurora connectivity.",
        [resource.address]
    )
}

# Helper function to check if vpc_config exists and is non-empty
has_vpc_config(after) if {
    count(after.vpc_config) > 0
    after.vpc_config[0].subnet_ids
}
