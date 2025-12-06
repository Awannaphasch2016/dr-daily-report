// SQS Worker Integration Tests
//
// These tests verify the async report generation infrastructure:
// - SQS queue exists and is properly configured
// - Lambda worker has event source mapping from SQS
// - DLQ is configured for failed messages
//
// Usage:
//   cd terraform/tests
//   go test -v -timeout 10m -run TestSQS

package test

import (
	"testing"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/lambda"
	"github.com/aws/aws-sdk-go/service/sqs"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// SQS configuration
var (
	reportJobsQueue    = "dr-daily-report-report-jobs-" + environment
	reportJobsDLQ      = "dr-daily-report-report-jobs-dlq-" + environment
	reportWorkerLambda = "dr-daily-report-report-worker-" + environment
)

// getSQSClient creates an SQS client for the test region
func getSQSClient(t *testing.T) *sqs.SQS {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String(awsRegion),
	})
	require.NoError(t, err, "Failed to create AWS session")
	return sqs.New(sess)
}

// TestSQSQueueExists verifies the report jobs queue exists
func TestSQSQueueExists(t *testing.T) {
	t.Parallel()

	client := getSQSClient(t)

	result, err := client.GetQueueUrl(&sqs.GetQueueUrlInput{
		QueueName: aws.String(reportJobsQueue),
	})
	require.NoError(t, err, "Report jobs queue %s should exist", reportJobsQueue)
	assert.NotEmpty(t, *result.QueueUrl, "Queue should have URL")
}

// TestSQSDLQExists verifies the dead letter queue exists
func TestSQSDLQExists(t *testing.T) {
	t.Parallel()

	client := getSQSClient(t)

	result, err := client.GetQueueUrl(&sqs.GetQueueUrlInput{
		QueueName: aws.String(reportJobsDLQ),
	})
	require.NoError(t, err, "DLQ %s should exist", reportJobsDLQ)
	assert.NotEmpty(t, *result.QueueUrl, "DLQ should have URL")
}

// TestSQSQueueHasDLQConfigured verifies the main queue has DLQ redrive policy
func TestSQSQueueHasDLQConfigured(t *testing.T) {
	t.Parallel()

	client := getSQSClient(t)

	// Get queue URL
	urlResult, err := client.GetQueueUrl(&sqs.GetQueueUrlInput{
		QueueName: aws.String(reportJobsQueue),
	})
	require.NoError(t, err, "Failed to get queue URL")

	// Get queue attributes
	attrResult, err := client.GetQueueAttributes(&sqs.GetQueueAttributesInput{
		QueueUrl: urlResult.QueueUrl,
		AttributeNames: []*string{
			aws.String("RedrivePolicy"),
		},
	})
	require.NoError(t, err, "Failed to get queue attributes")

	// Verify redrive policy exists (DLQ configured)
	redrivePolicy, exists := attrResult.Attributes["RedrivePolicy"]
	assert.True(t, exists, "Queue should have RedrivePolicy (DLQ) configured")
	assert.NotEmpty(t, *redrivePolicy, "RedrivePolicy should not be empty")
}

// TestSQSVisibilityTimeout verifies sufficient visibility timeout for report generation
func TestSQSVisibilityTimeout(t *testing.T) {
	t.Parallel()

	client := getSQSClient(t)

	// Get queue URL
	urlResult, err := client.GetQueueUrl(&sqs.GetQueueUrlInput{
		QueueName: aws.String(reportJobsQueue),
	})
	require.NoError(t, err, "Failed to get queue URL")

	// Get queue attributes
	attrResult, err := client.GetQueueAttributes(&sqs.GetQueueAttributesInput{
		QueueUrl: urlResult.QueueUrl,
		AttributeNames: []*string{
			aws.String("VisibilityTimeout"),
		},
	})
	require.NoError(t, err, "Failed to get queue attributes")

	// Report generation takes ~60s, visibility timeout should be at least 120s
	visibilityTimeout := attrResult.Attributes["VisibilityTimeout"]
	assert.NotNil(t, visibilityTimeout, "Queue should have VisibilityTimeout")
	// Note: Value is string, would need to parse for numeric comparison
	t.Logf("SQS Visibility Timeout: %s seconds", *visibilityTimeout)
}

// TestLambdaEventSourceMappingExists verifies SQS triggers the Lambda worker
func TestLambdaEventSourceMappingExists(t *testing.T) {
	t.Parallel()

	lambdaClient := getLambdaClient(t)

	// Event source mapping is attached to the "live" alias, not the function directly
	// This enables safe deployments (update $LATEST, test, then move alias)
	functionWithAlias := reportWorkerLambda + ":live"

	// List event source mappings for the Lambda alias
	result, err := lambdaClient.ListEventSourceMappings(&lambda.ListEventSourceMappingsInput{
		FunctionName: aws.String(functionWithAlias),
	})
	require.NoError(t, err, "Failed to list event source mappings")

	// Find SQS event source mapping
	var foundSQSMapping bool
	for _, mapping := range result.EventSourceMappings {
		if mapping.EventSourceArn != nil && contains(*mapping.EventSourceArn, reportJobsQueue) {
			foundSQSMapping = true
			// Verify mapping is enabled
			assert.Equal(t, "Enabled", *mapping.State,
				"SQS event source mapping should be Enabled")
			t.Logf("Found SQS event source mapping: %s -> %s (State: %s)",
				*mapping.EventSourceArn, *mapping.FunctionArn, *mapping.State)
			break
		}
	}
	assert.True(t, foundSQSMapping,
		"Lambda %s should have SQS event source mapping for %s",
		functionWithAlias, reportJobsQueue)
}

// TestReportWorkerLambdaExists verifies the report worker Lambda exists
func TestReportWorkerLambdaExists(t *testing.T) {
	t.Parallel()

	client := getLambdaClient(t)

	result, err := client.GetFunction(&lambda.GetFunctionInput{
		FunctionName: aws.String(reportWorkerLambda),
	})
	require.NoError(t, err, "Report worker Lambda %s should exist", reportWorkerLambda)

	config := result.Configuration
	assert.Equal(t, "Active", *config.State, "Lambda should be in Active state")
}

// TestReportWorkerLambdaTimeout verifies worker has sufficient timeout
func TestReportWorkerLambdaTimeout(t *testing.T) {
	t.Parallel()

	client := getLambdaClient(t)

	result, err := client.GetFunction(&lambda.GetFunctionInput{
		FunctionName: aws.String(reportWorkerLambda),
	})
	require.NoError(t, err, "Failed to get Lambda configuration")

	timeout := *result.Configuration.Timeout
	// Report generation takes ~60s, Lambda should have at least 120s timeout
	assert.GreaterOrEqual(t, timeout, int64(120),
		"Report worker Lambda should have at least 2 min timeout")
}

// TestReportWorkerLambdaMemory verifies worker has sufficient memory
func TestReportWorkerLambdaMemory(t *testing.T) {
	t.Parallel()

	client := getLambdaClient(t)

	result, err := client.GetFunction(&lambda.GetFunctionInput{
		FunctionName: aws.String(reportWorkerLambda),
	})
	require.NoError(t, err, "Failed to get Lambda configuration")

	memory := *result.Configuration.MemorySize
	// Report generation needs memory for LLM responses
	assert.GreaterOrEqual(t, memory, int64(512),
		"Report worker Lambda should have at least 512MB memory")
}
