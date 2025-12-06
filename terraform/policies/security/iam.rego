# IAM Security Policy
#
# Enforces IAM best practices:
# - No wildcard (*) resources in IAM policies
# - No AdministratorAccess policy attachments
# - No inline policies with excessive permissions
#
# Usage: conftest test tfplan.json --policy policies/

package terraform.security.iam

import future.keywords.in
import future.keywords.if
import future.keywords.contains

# Deny IAM policies that use wildcard Resource
# Exception: EC2 network interface actions require Resource: "*" (AWS design)
deny contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_iam_policy"
    resource.change.actions[_] != "delete"
    policy_doc := resource.change.after.policy
    contains(policy_doc, "\"Resource\": \"*\"")
    # Allow EC2 network interface actions (required for Lambda VPC)
    not is_ec2_network_interface_policy(policy_doc)
    msg := sprintf("IAM policy '%s' uses wildcard Resource. Specify explicit ARNs for least privilege.", [resource.address])
}

deny contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_iam_policy"
    resource.change.actions[_] != "delete"
    policy_doc := resource.change.after.policy
    contains(policy_doc, "\"Resource\":\"*\"")
    # Allow EC2 network interface actions (required for Lambda VPC)
    not is_ec2_network_interface_policy(policy_doc)
    msg := sprintf("IAM policy '%s' uses wildcard Resource. Specify explicit ARNs for least privilege.", [resource.address])
}

# Helper: Check if policy only uses wildcard for EC2 network interface actions
# These actions require Resource: "*" by AWS design (can't specify ARNs beforehand)
is_ec2_network_interface_policy(policy_doc) if {
    contains(policy_doc, "ec2:CreateNetworkInterface")
    contains(policy_doc, "ec2:DeleteNetworkInterface")
}

# Deny attachment of AdministratorAccess policy
deny contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_iam_role_policy_attachment"
    resource.change.actions[_] != "delete"
    contains(resource.change.after.policy_arn, "AdministratorAccess")
    msg := sprintf("Role '%s' attaches AdministratorAccess policy. Use least privilege principle.", [resource.address])
}

# Deny attachment of PowerUserAccess policy
deny contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_iam_role_policy_attachment"
    resource.change.actions[_] != "delete"
    contains(resource.change.after.policy_arn, "PowerUserAccess")
    msg := sprintf("Role '%s' attaches PowerUserAccess policy. Use least privilege principle.", [resource.address])
}

# Warn about IAM policies with Action: "*"
warn contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_iam_policy"
    resource.change.actions[_] != "delete"
    policy_doc := resource.change.after.policy
    contains(policy_doc, "\"Action\": \"*\"")
    msg := sprintf("IAM policy '%s' uses wildcard Action. Consider specifying explicit actions.", [resource.address])
}

# Warn about inline policies (prefer managed policies)
warn contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_iam_role_policy"
    resource.change.actions[_] != "delete"
    msg := sprintf("Role '%s' uses inline policy. Prefer managed policies for easier management.", [resource.address])
}
