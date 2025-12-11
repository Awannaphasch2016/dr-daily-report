# OPA Policy Entry Point for Terraform Validation
#
# This is the main entry point for Conftest to validate Terraform plans.
# Policies are organized into packages:
#   - terraform.security.*   - Security-related policies
#     - terraform.security.mcp - MCP server security policies
#   - terraform.tagging      - Tag enforcement policies
#   - terraform.cost         - Cost control policies
#
# Usage:
#   terraform plan -out=tfplan.binary
#   terraform show -json tfplan.binary > tfplan.json
#   conftest test tfplan.json --policy policies/ --all-namespaces

package main

import future.keywords.in
import future.keywords.if
import future.keywords.contains

# Aggregate all deny rules from all packages
deny contains msg if {
    some namespace
    data.terraform[namespace].deny[msg]
}

deny contains msg if {
    some namespace
    data.terraform[namespace].security[_].deny[msg]
}

# Aggregate all warn rules from all packages (warnings don't block)
warn contains msg if {
    some namespace
    data.terraform[namespace].warn[msg]
}

warn contains msg if {
    some namespace
    data.terraform[namespace].security[_].warn[msg]
}

# Include messaging policies (SQS)
deny contains msg if {
    some namespace
    data.terraform[namespace].messaging[_].deny[msg]
}

warn contains msg if {
    some namespace
    data.terraform[namespace].messaging[_].warn[msg]
}
