# EventBridge Scheduler Policy
#
# Pre-apply validation for EventBridge rules to ensure:
# - Schedule follows naming conventions
# - Lambda targets have proper configuration
# - Input payloads include required fields for report generation
#
# Usage:
#   cd terraform && terraform plan -out=tfplan.binary
#   terraform show -json tfplan.binary > tfplan.json
#   conftest test tfplan.json -p policies/scheduler/

package scheduler.eventbridge

import rego.v1

# Deny rules - violations that block deployment
deny contains msg if {
	some resource in input.resource_changes
	resource.type == "aws_cloudwatch_event_target"
	resource.change.after.input != null
	input_json := json.unmarshal(resource.change.after.input)

	# Must include action for precompute
	not input_json.action
	msg := sprintf("EventBridge target '%s' must specify 'action' in input payload", [resource.address])
}

deny contains msg if {
	some resource in input.resource_changes
	resource.type == "aws_cloudwatch_event_target"
	resource.change.after.input != null
	input_json := json.unmarshal(resource.change.after.input)

	# Action must be 'precompute' for scheduler
	input_json.action
	input_json.action != "precompute"
	msg := sprintf("EventBridge target '%s' action must be 'precompute', got '%s'", [resource.address, input_json.action])
}

deny contains msg if {
	some resource in input.resource_changes
	resource.type == "aws_cloudwatch_event_target"
	resource.change.after.input != null
	input_json := json.unmarshal(resource.change.after.input)

	# Must include_report for daily report generation
	input_json.action == "precompute"
	not input_json.include_report
	msg := sprintf("EventBridge target '%s' must set 'include_report: true' for daily report generation", [resource.address])
}

deny contains msg if {
	some resource in input.resource_changes
	resource.type == "aws_cloudwatch_event_target"
	resource.change.after.input != null
	input_json := json.unmarshal(resource.change.after.input)

	# include_report must be true (not false)
	input_json.include_report == false
	msg := sprintf("EventBridge target '%s' has 'include_report: false' - should be true for daily reports", [resource.address])
}

# Warn rules - best practices
warn contains msg if {
	some resource in input.resource_changes
	resource.type == "aws_cloudwatch_event_rule"
	resource.change.after.state == "DISABLED"
	msg := sprintf("EventBridge rule '%s' is DISABLED - enable after testing", [resource.address])
}

warn contains msg if {
	some resource in input.resource_changes
	resource.type == "aws_lambda_function"
	contains(resource.address, "scheduler")
	resource.change.after.timeout < 300
	msg := sprintf("Scheduler Lambda '%s' timeout is %d seconds - recommend at least 300s for report generation", [resource.address, resource.change.after.timeout])
}

warn contains msg if {
	some resource in input.resource_changes
	resource.type == "aws_lambda_function"
	contains(resource.address, "scheduler")
	resource.change.after.memory_size < 512
	msg := sprintf("Scheduler Lambda '%s' memory is %dMB - recommend at least 512MB", [resource.address, resource.change.after.memory_size])
}

# Info rules - documentation
info contains msg if {
	some resource in input.resource_changes
	resource.type == "aws_cloudwatch_event_rule"
	resource.change.after.schedule_expression
	contains(resource.change.after.schedule_expression, "cron(0 1")
	msg := sprintf("EventBridge rule '%s' scheduled at 01:00 UTC (08:00 Bangkok)", [resource.address])
}

# Helper to check if EventBridge has Lambda target
eventbridge_targets_lambda if {
	some rule in input.resource_changes
	rule.type == "aws_cloudwatch_event_rule"

	some target in input.resource_changes
	target.type == "aws_cloudwatch_event_target"

	some lambda in input.resource_changes
	lambda.type == "aws_lambda_function"

	contains(target.change.after.arn, "lambda")
}
