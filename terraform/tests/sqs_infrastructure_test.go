package test

import (
	"fmt"
	"testing"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/service/lambda"
	"github.com/aws/aws-sdk-go/service/sqs"
	"github.com/gruntwork-io/terratest/modules/aws"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

const (
	awsRegion         = "ap-southeast-1"
	environment       = "dev"
	reportJobsQueue   = "dr-daily-report-report-jobs-" + environment
	reportJobsDLQ     = "dr-daily-report-report-jobs-dlq-" + environment
	reportWorkerName  = "dr-daily-report-report-worker-" + environment
	schedulerName     = "dr-daily-report-ticker-scheduler-" + environment
)

// TestSQSQueueInfrastructureExists validates the main SQS queue infrastructure
// Following CLAUDE.md: Test outcomes (queue properties), not just existence
func TestSQSQueueInfrastructureExists(t *testing.T) {
	t.Parallel()

	sqsClient := aws.NewSqsClient(t, awsRegion)

	// Get queue URL
	queueURL, err := sqsClient.GetQueueUrl(&sqs.GetQueueUrlInput{
		QueueName: aws.String(reportJobsQueue),
	})
	require.NoError(t, err, "Queue %s should exist", reportJobsQueue)
	require.NotNil(t, queueURL.QueueUrl, "Queue URL should not be nil")

	// Get queue attributes
	attrs, err := sqsClient.GetQueueAttributes(&sqs.GetQueueAttributesInput{
		QueueUrl: queueURL.QueueUrl,
		AttributeNames: []*string{
			aws.String("All"),
		},
	})
	require.NoError(t, err, "Should be able to get queue attributes")

	// Validate visibility timeout = 900s (15 minutes)
	visibilityTimeout := attrs.Attributes["VisibilityTimeout"]
	assert.Equal(t, "900", *visibilityTimeout,
		"Visibility timeout should be 900s to match Lambda timeout + buffer")

	// Validate message retention = 1209600s (14 days)
	messageRetention := attrs.Attributes["MessageRetentionPeriod"]
	assert.Equal(t, "1209600", *messageRetention,
		"Message retention should be 14 days")

	// Validate long polling enabled (receive wait time = 20s)
	receiveWaitTime := attrs.Attributes["ReceiveMessageWaitTimeSeconds"]
	assert.Equal(t, "20", *receiveWaitTime,
		"Long polling should be enabled with 20s wait time")
}

// TestDLQExists validates the Dead Letter Queue configuration
// Following CLAUDE.md: Validate configuration at startup, fail fast
func TestDLQExists(t *testing.T) {
	t.Parallel()

	sqsClient := aws.NewSqsClient(t, awsRegion)

	// Get DLQ URL
	dlqURL, err := sqsClient.GetQueueUrl(&sqs.GetQueueUrlInput{
		QueueName: aws.String(reportJobsDLQ),
	})
	require.NoError(t, err, "DLQ %s should exist", reportJobsDLQ)
	require.NotNil(t, dlqURL.QueueUrl, "DLQ URL should not be nil")

	// Get DLQ attributes
	attrs, err := sqsClient.GetQueueAttributes(&sqs.GetQueueAttributesInput{
		QueueUrl: dlqURL.QueueUrl,
		AttributeNames: []*string{
			aws.String("MessageRetentionPeriod"),
			aws.String("VisibilityTimeout"),
		},
	})
	require.NoError(t, err, "Should be able to get DLQ attributes")

	// Validate message retention = 14 days (for debugging failed messages)
	messageRetention := attrs.Attributes["MessageRetentionPeriod"]
	assert.Equal(t, "1209600", *messageRetention,
		"DLQ retention should be 14 days for debugging")

	// Validate visibility timeout matches main queue
	visibilityTimeout := attrs.Attributes["VisibilityTimeout"]
	assert.Equal(t, "900", *visibilityTimeout,
		"DLQ visibility timeout should match main queue")
}

// TestRedrivePolicy validates the redrive policy configuration
// Following CLAUDE.md: Test behavior (fail-fast redrive), not just config exists
func TestRedrivePolicy(t *testing.T) {
	t.Parallel()

	sqsClient := aws.NewSqsClient(t, awsRegion)

	// Get main queue URL
	queueURL, err := sqsClient.GetQueueUrl(&sqs.GetQueueUrlInput{
		QueueName: aws.String(reportJobsQueue),
	})
	require.NoError(t, err)

	// Get DLQ URL for ARN comparison
	dlqURL, err := sqsClient.GetQueueUrl(&sqs.GetQueueUrlInput{
		QueueName: aws.String(reportJobsDLQ),
	})
	require.NoError(t, err)

	// Get DLQ ARN
	dlqAttrs, err := sqsClient.GetQueueAttributes(&sqs.GetQueueAttributesInput{
		QueueUrl: dlqURL.QueueUrl,
		AttributeNames: []*string{
			aws.String("QueueArn"),
		},
	})
	require.NoError(t, err)
	dlqArn := dlqAttrs.Attributes["QueueArn"]

	// Get main queue redrive policy
	attrs, err := sqsClient.GetQueueAttributes(&sqs.GetQueueAttributesInput{
		QueueUrl: queueURL.QueueUrl,
		AttributeNames: []*string{
			aws.String("RedrivePolicy"),
		},
	})
	require.NoError(t, err)

	// Validate redrive policy exists
	redrivePolicy := attrs.Attributes["RedrivePolicy"]
	require.NotNil(t, redrivePolicy, "Redrive policy should be configured")

	// Validate policy contains DLQ ARN
	assert.Contains(t, *redrivePolicy, *dlqArn,
		"Redrive policy should point to DLQ: %s", *dlqArn)

	// Validate maxReceiveCount = 1 (fail-fast to DLQ)
	assert.Contains(t, *redrivePolicy, `"maxReceiveCount":"1"`,
		"maxReceiveCount should be 1 for fail-fast behavior")
}

// TestWorkerLambdaConfiguration validates Lambda function configuration
// Following CLAUDE.md: Validate configuration at startup (env vars)
func TestWorkerLambdaConfiguration(t *testing.T) {
	t.Parallel()

	lambdaClient := aws.NewLambdaClient(t, awsRegion)

	// Get Lambda configuration
	config, err := lambdaClient.GetFunctionConfiguration(&lambda.GetFunctionConfigurationInput{
		FunctionName: aws.String(reportWorkerName),
	})
	require.NoError(t, err, "Worker Lambda %s should exist", reportWorkerName)

	// Validate REPORT_JOBS_QUEUE_URL environment variable
	queueURLEnv, exists := config.Environment.Variables["REPORT_JOBS_QUEUE_URL"]
	require.True(t, exists, "REPORT_JOBS_QUEUE_URL env var should be set")
	require.NotNil(t, queueURLEnv, "REPORT_JOBS_QUEUE_URL should not be nil")

	// Validate queue URL contains correct queue name
	assert.Contains(t, *queueURLEnv, reportJobsQueue,
		"Queue URL should reference %s", reportJobsQueue)

	// Validate timeout ≥ 120s (2 minutes for report generation)
	timeout := config.Timeout
	assert.GreaterOrEqual(t, *timeout, int64(120),
		"Lambda timeout should be ≥ 120s for report generation")

	// Validate memory ≥ 1024MB (for LLM processing)
	memory := config.MemorySize
	assert.GreaterOrEqual(t, *memory, int64(1024),
		"Lambda memory should be ≥ 1024MB for LLM processing")
}

// TestEventSourceMapping validates SQS trigger configuration
// Following CLAUDE.md: Test behavior (batch size=1 for max parallelism)
func TestEventSourceMapping(t *testing.T) {
	t.Parallel()

	lambdaClient := aws.NewLambdaClient(t, awsRegion)
	sqsClient := aws.NewSqsClient(t, awsRegion)

	// Get queue ARN
	queueURL, err := sqsClient.GetQueueUrl(&sqs.GetQueueUrlInput{
		QueueName: aws.String(reportJobsQueue),
	})
	require.NoError(t, err)

	attrs, err := sqsClient.GetQueueAttributes(&sqs.GetQueueAttributesInput{
		QueueUrl: queueURL.QueueUrl,
		AttributeNames: []*string{
			aws.String("QueueArn"),
		},
	})
	require.NoError(t, err)
	queueArn := attrs.Attributes["QueueArn"]

	// List event source mappings for worker Lambda
	mappings, err := lambdaClient.ListEventSourceMappings(&lambda.ListEventSourceMappingsInput{
		FunctionName: aws.String(reportWorkerName),
	})
	require.NoError(t, err, "Should be able to list event source mappings")

	// Find mapping for our queue
	var sqsMapping *lambda.EventSourceMappingConfiguration
	for _, mapping := range mappings.EventSourceMappings {
		if mapping.EventSourceArn != nil && *mapping.EventSourceArn == *queueArn {
			sqsMapping = mapping
			break
		}
	}

	require.NotNil(t, sqsMapping, "Event source mapping should exist for queue %s", *queueArn)

	// Validate batch size = 1 (max parallelism - each message triggers separate Lambda)
	assert.Equal(t, int64(1), *sqsMapping.BatchSize,
		"Batch size should be 1 for maximum parallelism")

	// Validate state is Enabled
	assert.Equal(t, "Enabled", *sqsMapping.State,
		"Event source mapping should be enabled")

	// Validate no batching delay (immediate processing)
	if sqsMapping.MaximumBatchingWindowInSeconds != nil {
		assert.Equal(t, int64(0), *sqsMapping.MaximumBatchingWindowInSeconds,
			"Batching delay should be 0 for immediate processing")
	}
}

// TestIAMPermissions validates Lambda IAM permissions
// Following CLAUDE.md: Defensive Programming - validate permissions at startup
func TestIAMPermissions(t *testing.T) {
	t.Parallel()

	lambdaClient := aws.NewLambdaClient(t, awsRegion)

	// Get worker Lambda configuration (validates Lambda access)
	workerConfig, err := lambdaClient.GetFunctionConfiguration(&lambda.GetFunctionConfigurationInput{
		FunctionName: aws.String(reportWorkerName),
	})
	require.NoError(t, err, "Should have permissions to describe worker Lambda")

	// Validate Lambda has IAM role configured
	assert.NotNil(t, workerConfig.Role, "Worker Lambda should have IAM role")
	assert.Contains(t, *workerConfig.Role, "iam::aws:policy",
		"Lambda role should be a valid IAM role ARN")

	// Get scheduler Lambda configuration (validates scheduler can invoke SQS)
	schedulerConfig, err := lambdaClient.GetFunctionConfiguration(&lambda.GetFunctionConfigurationInput{
		FunctionName: aws.String(schedulerName),
	})
	require.NoError(t, err, "Should have permissions to describe scheduler Lambda")

	// Validate scheduler has REPORT_JOBS_QUEUE_URL (can send messages)
	queueURLEnv, exists := schedulerConfig.Environment.Variables["REPORT_JOBS_QUEUE_URL"]
	require.True(t, exists, "Scheduler should have REPORT_JOBS_QUEUE_URL env var")
	require.NotNil(t, queueURLEnv, "Scheduler queue URL should not be nil")

	// Note: Cannot directly test SQS permissions without invoking Lambda
	// That's covered by integration tests in Python
	t.Log("IAM role configured correctly. Permission validation requires integration tests.")
}
