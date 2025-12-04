// EventBridge Scheduler Integration Tests
//
// These tests verify EventBridge rules are deployed correctly for daily report generation.
// Tests run against actual AWS infrastructure in the dev environment.
//
// Usage:
//   cd terraform/tests
//   go test -v -timeout 10m -run TestEventBridge

package test

import (
	"encoding/json"
	"testing"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/eventbridge"
	"github.com/aws/aws-sdk-go/service/lambda"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// EventBridge configuration
var (
	schedulerRuleName = "dr-daily-report-daily-ticker-fetch-" + environment
	schedulerLambdaFn = "dr-daily-report-ticker-scheduler-" + environment
)

// getEventBridgeClient creates an EventBridge client
func getEventBridgeClient(t *testing.T) *eventbridge.EventBridge {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String(awsRegion),
	})
	require.NoError(t, err, "Failed to create AWS session")
	return eventbridge.New(sess)
}

// TestEventBridgeRuleExists verifies the EventBridge rule exists
func TestEventBridgeRuleExists(t *testing.T) {
	t.Parallel()

	client := getEventBridgeClient(t)

	result, err := client.DescribeRule(&eventbridge.DescribeRuleInput{
		Name: aws.String(schedulerRuleName),
	})
	require.NoError(t, err, "EventBridge rule %s should exist", schedulerRuleName)

	assert.NotNil(t, result.Arn, "Rule should have ARN")
	assert.NotEmpty(t, *result.ScheduleExpression, "Rule should have schedule expression")
}

// TestEventBridgeScheduleExpression verifies the schedule is correct (8 AM Bangkok = 01:00 UTC)
func TestEventBridgeScheduleExpression(t *testing.T) {
	t.Parallel()

	client := getEventBridgeClient(t)

	result, err := client.DescribeRule(&eventbridge.DescribeRuleInput{
		Name: aws.String(schedulerRuleName),
	})
	require.NoError(t, err, "Failed to describe rule")

	// Expected: cron(0 1 * * ? *) = 01:00 UTC = 08:00 Bangkok (UTC+7)
	expectedCron := "cron(0 1 * * ? *)"
	assert.Equal(t, expectedCron, *result.ScheduleExpression,
		"Schedule should be 8 AM Bangkok time (01:00 UTC)")
}

// TestEventBridgeTargetExists verifies the Lambda target is configured
func TestEventBridgeTargetExists(t *testing.T) {
	t.Parallel()

	client := getEventBridgeClient(t)

	result, err := client.ListTargetsByRule(&eventbridge.ListTargetsByRuleInput{
		Rule: aws.String(schedulerRuleName),
	})
	require.NoError(t, err, "Failed to list targets")

	require.NotEmpty(t, result.Targets, "Rule should have at least one target")

	// Verify target is the scheduler Lambda
	var foundLambdaTarget bool
	for _, target := range result.Targets {
		if target.Arn != nil && contains(*target.Arn, schedulerLambdaFn) {
			foundLambdaTarget = true
			break
		}
	}
	assert.True(t, foundLambdaTarget, "Target should be the scheduler Lambda")
}

// TestEventBridgeTargetInput verifies the target input includes report generation
func TestEventBridgeTargetInput(t *testing.T) {
	t.Parallel()

	client := getEventBridgeClient(t)

	result, err := client.ListTargetsByRule(&eventbridge.ListTargetsByRuleInput{
		Rule: aws.String(schedulerRuleName),
	})
	require.NoError(t, err, "Failed to list targets")

	require.NotEmpty(t, result.Targets, "Rule should have targets")

	// Find the Lambda target
	var targetInput string
	for _, target := range result.Targets {
		if target.Input != nil {
			targetInput = *target.Input
			break
		}
	}

	// Parse the input JSON
	var input map[string]interface{}
	err = json.Unmarshal([]byte(targetInput), &input)
	require.NoError(t, err, "Target input should be valid JSON")

	// Verify input includes action and include_report
	assert.Equal(t, "precompute", input["action"],
		"Target input should specify 'precompute' action")
	assert.Equal(t, true, input["include_report"],
		"Target input should include report generation (include_report: true)")
}

// TestEventBridgeTargetUsesLiveAlias verifies EventBridge invokes the :live alias, not $LATEST.
// This is critical for zero-downtime deployment - EventBridge should always invoke tested code.
func TestEventBridgeTargetUsesLiveAlias(t *testing.T) {
	t.Parallel()

	client := getEventBridgeClient(t)

	result, err := client.ListTargetsByRule(&eventbridge.ListTargetsByRuleInput{
		Rule: aws.String(schedulerRuleName),
	})
	require.NoError(t, err, "Failed to list targets")
	require.NotEmpty(t, result.Targets, "Rule should have at least one target")

	// Find the Lambda target and verify it uses :live alias
	var targetArn string
	for _, target := range result.Targets {
		if target.Arn != nil && contains(*target.Arn, schedulerLambdaFn) {
			targetArn = *target.Arn
			break
		}
	}

	require.NotEmpty(t, targetArn, "Should find Lambda target")

	// Target ARN should include :live alias, not be the base function ARN
	// Expected: arn:aws:lambda:...:function:dr-daily-report-ticker-scheduler-dev:live
	assert.Contains(t, targetArn, ":live",
		"EventBridge target should invoke :live alias, not $LATEST. Got: %s", targetArn)

	t.Logf("✅ EventBridge target uses live alias: %s", targetArn)
}

// TestEventBridgeLambdaPermission verifies EventBridge has permission to invoke Lambda
func TestEventBridgeLambdaPermission(t *testing.T) {
	t.Parallel()

	lambdaClient := getLambdaClient(t)

	// Get Lambda policy
	result, err := lambdaClient.GetPolicy(&lambda.GetPolicyInput{
		FunctionName: aws.String(schedulerLambdaFn),
	})
	require.NoError(t, err, "Lambda should have resource policy")

	// Parse policy
	var policy struct {
		Statement []struct {
			Effect    string `json:"Effect"`
			Principal struct {
				Service string `json:"Service"`
			} `json:"Principal"`
			Action   string `json:"Action"`
			Resource string `json:"Resource"`
		} `json:"Statement"`
	}
	err = json.Unmarshal([]byte(*result.Policy), &policy)
	require.NoError(t, err, "Failed to parse policy")

	// Find EventBridge permission
	var foundEventBridgePermission bool
	for _, stmt := range policy.Statement {
		if stmt.Principal.Service == "events.amazonaws.com" &&
			stmt.Action == "lambda:InvokeFunction" {
			foundEventBridgePermission = true
			break
		}
	}
	assert.True(t, foundEventBridgePermission,
		"Lambda should allow EventBridge invocation")
}

// TestEventBridgeRuleState verifies the rule state (ENABLED/DISABLED)
func TestEventBridgeRuleState(t *testing.T) {
	t.Parallel()

	client := getEventBridgeClient(t)

	result, err := client.DescribeRule(&eventbridge.DescribeRuleInput{
		Name: aws.String(schedulerRuleName),
	})
	require.NoError(t, err, "Failed to describe rule")

	// Rule should be ENABLED for production, may be DISABLED for testing
	state := *result.State
	assert.Contains(t, []string{"ENABLED", "DISABLED"}, state,
		"Rule state should be either ENABLED or DISABLED")

	// Log the current state for visibility
	t.Logf("EventBridge rule state: %s", state)
}

// TestSchedulerLambdaTimeout verifies scheduler Lambda has sufficient timeout
func TestSchedulerLambdaTimeout(t *testing.T) {
	t.Parallel()

	client := getLambdaClient(t)

	result, err := client.GetFunction(&lambda.GetFunctionInput{
		FunctionName: aws.String(schedulerLambdaFn),
	})
	require.NoError(t, err, "Scheduler Lambda should exist")

	timeout := *result.Configuration.Timeout
	// Scheduler should have at least 5 minutes (300s) for report generation
	assert.GreaterOrEqual(t, timeout, int64(300),
		"Scheduler Lambda should have at least 5 min timeout for report generation")
}

// TestSchedulerLambdaMemory verifies scheduler Lambda has sufficient memory
func TestSchedulerLambdaMemory(t *testing.T) {
	t.Parallel()

	client := getLambdaClient(t)

	result, err := client.GetFunction(&lambda.GetFunctionInput{
		FunctionName: aws.String(schedulerLambdaFn),
	})
	require.NoError(t, err, "Scheduler Lambda should exist")

	memory := *result.Configuration.MemorySize
	// Scheduler should have at least 512MB for report generation
	assert.GreaterOrEqual(t, memory, int64(512),
		"Scheduler Lambda should have at least 512MB memory")
}

// Helper function to check if string contains substring
func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(s) > 0 && containsHelper(s, substr))
}

func containsHelper(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
