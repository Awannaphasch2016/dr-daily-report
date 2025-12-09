package test

import (
	"encoding/json"
	"fmt"
	"testing"
	"time"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/service/cloudwatch"
	"github.com/aws/aws-sdk-go/service/sqs"
	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	test_structure "github.com/gruntwork-io/terratest/modules/test-structure"
)

// TestSQSETLQueueModule validates the SQS ETL queue Terraform module
// following Infrastructure TDD principles:
// 1. Deploy infrastructure (terraform apply)
// 2. Verify actual AWS resources created
// 3. Test queue behavior (send/receive messages)
// 4. Verify CloudWatch alarms exist
// 5. Cleanup (terraform destroy)
func TestSQSETLQueueModule(t *testing.T) {
	t.Parallel()

	// Create a directory to store terraform state between test stages
	workingDir := "../modules/sqs-etl-queue"

	// At the end of the test, clean up resources
	defer test_structure.RunTestStage(t, "cleanup", func() {
		terraformOptions := test_structure.LoadTerraformOptions(t, workingDir)
		terraform.Destroy(t, terraformOptions)
	})

	// Deploy the infrastructure
	test_structure.RunTestStage(t, "deploy", func() {
		terraformOptions := configureTerraformOptions(t, workingDir)
		test_structure.SaveTerraformOptions(t, workingDir, terraformOptions)
		terraform.InitAndApply(t, terraformOptions)
	})

	// Validate the infrastructure
	test_structure.RunTestStage(t, "validate", func() {
		terraformOptions := test_structure.LoadTerraformOptions(t, workingDir)

		// Run all validation tests
		t.Run("QueueCreation", func(t *testing.T) { testQueueCreation(t, terraformOptions) })
		t.Run("DLQCreation", func(t *testing.T) { testDLQCreation(t, terraformOptions) })
		t.Run("RedrivePolicy", func(t *testing.T) { testRedrivePolicy(t, terraformOptions) })
		t.Run("QueueAttributes", func(t *testing.T) { testQueueAttributes(t, terraformOptions) })
		t.Run("Encryption", func(t *testing.T) { testEncryption(t, terraformOptions) })
		t.Run("CloudWatchAlarms", func(t *testing.T) { testCloudWatchAlarms(t, terraformOptions) })
		t.Run("MessageFlow", func(t *testing.T) { testMessageFlow(t, terraformOptions) })
		t.Run("DLQBehavior", func(t *testing.T) { testDLQBehavior(t, terraformOptions) })
	})
}

// configureTerraformOptions creates Terraform configuration for testing
func configureTerraformOptions(t *testing.T, workingDir string) *terraform.Options {
	// Generate unique queue name for this test run
	uniqueID := fmt.Sprintf("test-%d", time.Now().Unix())
	queueName := fmt.Sprintf("fund-data-sync-%s-dev", uniqueID)

	terraformOptions := &terraform.Options{
		TerraformDir: workingDir,

		Vars: map[string]interface{}{
			"queue_name":                queueName,
			"message_retention_seconds": 345600,  // 4 days
			"visibility_timeout_seconds": 120,     // 2 minutes
			"max_receive_count":         3,        // DLQ after 3 failures
			"enable_cloudwatch_alarms":  true,
			"allow_s3_event_source":     false,    // Don't need S3 policy for tests
			"common_tags": map[string]string{
				"Environment": "test",
				"Purpose":     "terratest",
				"ManagedBy":   "terratest",
			},
		},

		// Retry on known errors
		MaxRetries:         3,
		TimeBetweenRetries: 5 * time.Second,
	}

	return terraformOptions
}

// testQueueCreation verifies the main queue exists with correct name
func testQueueCreation(t *testing.T, terraformOptions *terraform.Options) {
	queueURL := terraform.Output(t, terraformOptions, "queue_url")
	queueARN := terraform.Output(t, terraformOptions, "queue_arn")

	require.NotEmpty(t, queueURL, "Queue URL should not be empty")
	require.NotEmpty(t, queueARN, "Queue ARN should not be empty")

	// Verify queue name matches input
	expectedQueueName := terraformOptions.Vars["queue_name"].(string)
	queueName := terraform.Output(t, terraformOptions, "queue_name")
	assert.Equal(t, expectedQueueName, queueName, "Queue name should match input")

	// Verify environment suffix
	assert.Contains(t, queueName, "-dev", "Queue name should have environment suffix")
}

// testDLQCreation verifies the DLQ exists
func testDLQCreation(t *testing.T, terraformOptions *terraform.Options) {
	dlqURL := terraform.Output(t, terraformOptions, "dlq_url")
	dlqARN := terraform.Output(t, terraformOptions, "dlq_arn")
	dlqName := terraform.Output(t, terraformOptions, "dlq_name")

	require.NotEmpty(t, dlqURL, "DLQ URL should not be empty")
	require.NotEmpty(t, dlqARN, "DLQ ARN should not be empty")

	// Verify DLQ name is queue name + "-dlq"
	queueName := terraformOptions.Vars["queue_name"].(string)
	expectedDLQName := fmt.Sprintf("%s-dlq", queueName)
	assert.Equal(t, expectedDLQName, dlqName, "DLQ name should be queue name + '-dlq'")
}

// testRedrivePolicy verifies DLQ redrive policy configuration
func testRedrivePolicy(t *testing.T, terraformOptions *terraform.Options) {
	queueURL := terraform.Output(t, terraformOptions, "queue_url")
	dlqARN := terraform.Output(t, terraformOptions, "dlq_arn")

	// Get queue attributes via AWS SDK
	sqsClient := createSQSClient(t)
	result, err := sqsClient.GetQueueAttributes(&sqs.GetQueueAttributesInput{
		QueueUrl:       aws.String(queueURL),
		AttributeNames: []*string{aws.String("RedrivePolicy")},
	})
	require.NoError(t, err, "Should get queue attributes")

	// Parse redrive policy JSON
	redrivePolicyJSON := result.Attributes["RedrivePolicy"]
	require.NotNil(t, redrivePolicyJSON, "Redrive policy should exist")

	var redrivePolicy map[string]interface{}
	err = json.Unmarshal([]byte(*redrivePolicyJSON), &redrivePolicy)
	require.NoError(t, err, "Should parse redrive policy JSON")

	// Verify DLQ ARN
	assert.Equal(t, dlqARN, redrivePolicy["deadLetterTargetArn"],
		"Redrive policy should reference correct DLQ")

	// Verify maxReceiveCount
	expectedMaxReceiveCount := float64(terraformOptions.Vars["max_receive_count"].(int))
	assert.Equal(t, expectedMaxReceiveCount, redrivePolicy["maxReceiveCount"],
		"maxReceiveCount should match input")

	// Verify maxReceiveCount is in allowed range (3-5 per OPA policy)
	maxReceiveCount := redrivePolicy["maxReceiveCount"].(float64)
	assert.GreaterOrEqual(t, maxReceiveCount, float64(3), "maxReceiveCount should be >= 3")
	assert.LessOrEqual(t, maxReceiveCount, float64(5), "maxReceiveCount should be <= 5")
}

// testQueueAttributes verifies queue configuration attributes
func testQueueAttributes(t *testing.T, terraformOptions *terraform.Options) {
	queueURL := terraform.Output(t, terraformOptions, "queue_url")

	// Get all queue attributes
	sqsClient := createSQSClient(t)
	result, err := sqsClient.GetQueueAttributes(&sqs.GetQueueAttributesInput{
		QueueUrl:       aws.String(queueURL),
		AttributeNames: []*string{aws.String("All")},
	})
	require.NoError(t, err, "Should get queue attributes")

	attrs := result.Attributes

	// Verify visibility timeout
	expectedTimeout := fmt.Sprintf("%d", terraformOptions.Vars["visibility_timeout_seconds"].(int))
	assert.Equal(t, expectedTimeout, *attrs["VisibilityTimeout"],
		"Visibility timeout should match input")

	// Verify visibility timeout >= 60s (OPA policy requirement)
	visibilityTimeout := *attrs["VisibilityTimeout"]
	assert.GreaterOrEqual(t, visibilityTimeout, "60",
		"Visibility timeout should be >= 60s per OPA policy")

	// Verify message retention
	expectedRetention := fmt.Sprintf("%d", terraformOptions.Vars["message_retention_seconds"].(int))
	assert.Equal(t, expectedRetention, *attrs["MessageRetentionPeriod"],
		"Message retention should match input")

	// Verify message retention >= 1 day (OPA policy requirement)
	messageRetention := *attrs["MessageRetentionPeriod"]
	assert.GreaterOrEqual(t, messageRetention, "86400",
		"Message retention should be >= 1 day (86400s) per OPA policy")

	// Verify long polling enabled (receive_wait_time > 0)
	receiveWaitTime := *attrs["ReceiveMessageWaitTimeSeconds"]
	assert.Greater(t, receiveWaitTime, "0",
		"Long polling should be enabled (receive_wait_time > 0)")
}

// testEncryption verifies queue encryption is enabled
func testEncryption(t *testing.T, terraformOptions *terraform.Options) {
	queueURL := terraform.Output(t, terraformOptions, "queue_url")

	sqsClient := createSQSClient(t)
	result, err := sqsClient.GetQueueAttributes(&sqs.GetQueueAttributesInput{
		QueueUrl:       aws.String(queueURL),
		AttributeNames: []*string{aws.String("SqsManagedSseEnabled")},
	})
	require.NoError(t, err, "Should get queue attributes")

	// Verify SSE-SQS encryption is enabled
	sseEnabled := result.Attributes["SqsManagedSseEnabled"]
	assert.Equal(t, "true", *sseEnabled,
		"SSE-SQS encryption should be enabled per OPA policy")
}

// testCloudWatchAlarms verifies CloudWatch alarms were created
func testCloudWatchAlarms(t *testing.T, terraformOptions *terraform.Options) {
	// Get alarm ARNs from outputs
	dlqAlarmARN := terraform.Output(t, terraformOptions, "dlq_alarm_arn")
	queueDepthAlarmARN := terraform.Output(t, terraformOptions, "queue_depth_alarm_arn")
	messageAgeAlarmARN := terraform.Output(t, terraformOptions, "message_age_alarm_arn")

	require.NotEmpty(t, dlqAlarmARN, "DLQ alarm ARN should not be empty")
	require.NotEmpty(t, queueDepthAlarmARN, "Queue depth alarm ARN should not be empty")
	require.NotEmpty(t, messageAgeAlarmARN, "Message age alarm ARN should not be empty")

	// Verify alarms exist in CloudWatch
	cwClient := createCloudWatchClient(t)
	queueName := terraformOptions.Vars["queue_name"].(string)

	// DLQ alarm
	dlqAlarmName := fmt.Sprintf("%s-dlq-messages", queueName)
	verifyAlarmExists(t, cwClient, dlqAlarmName)

	// Queue depth alarm
	depthAlarmName := fmt.Sprintf("%s-depth", queueName)
	verifyAlarmExists(t, cwClient, depthAlarmName)

	// Message age alarm
	ageAlarmName := fmt.Sprintf("%s-message-age", queueName)
	verifyAlarmExists(t, cwClient, ageAlarmName)
}

// testMessageFlow verifies messages can be sent and received
func testMessageFlow(t *testing.T, terraformOptions *terraform.Options) {
	queueURL := terraform.Output(t, terraformOptions, "queue_url")
	sqsClient := createSQSClient(t)

	// Send test message
	testMessage := fmt.Sprintf("Test message %d", time.Now().Unix())
	_, err := sqsClient.SendMessage(&sqs.SendMessageInput{
		QueueUrl:    aws.String(queueURL),
		MessageBody: aws.String(testMessage),
	})
	require.NoError(t, err, "Should send message")

	// Receive message (with timeout)
	result, err := sqsClient.ReceiveMessage(&sqs.ReceiveMessageInput{
		QueueUrl:            aws.String(queueURL),
		MaxNumberOfMessages: aws.Int64(1),
		WaitTimeSeconds:     aws.Int64(10), // Long polling
	})
	require.NoError(t, err, "Should receive message")

	// Verify message received
	require.Len(t, result.Messages, 1, "Should receive exactly 1 message")
	assert.Equal(t, testMessage, *result.Messages[0].Body, "Message body should match")

	// Clean up: Delete message
	_, err = sqsClient.DeleteMessage(&sqs.DeleteMessageInput{
		QueueUrl:      aws.String(queueURL),
		ReceiptHandle: result.Messages[0].ReceiptHandle,
	})
	require.NoError(t, err, "Should delete message")
}

// testDLQBehavior verifies messages move to DLQ after max receive count
func testDLQBehavior(t *testing.T, terraformOptions *terraform.Options) {
	queueURL := terraform.Output(t, terraformOptions, "queue_url")
	dlqURL := terraform.Output(t, terraformOptions, "dlq_url")
	sqsClient := createSQSClient(t)

	maxReceiveCount := terraformOptions.Vars["max_receive_count"].(int)

	// Send poison message
	poisonMessage := fmt.Sprintf("Poison message %d", time.Now().Unix())
	_, err := sqsClient.SendMessage(&sqs.SendMessageInput{
		QueueUrl:    aws.String(queueURL),
		MessageBody: aws.String(poisonMessage),
	})
	require.NoError(t, err, "Should send poison message")

	// Receive message maxReceiveCount times without deleting
	for i := 0; i < maxReceiveCount; i++ {
		result, err := sqsClient.ReceiveMessage(&sqs.ReceiveMessageInput{
			QueueUrl:            aws.String(queueURL),
			MaxNumberOfMessages: aws.Int64(1),
			WaitTimeSeconds:     aws.Int64(10),
			VisibilityTimeout:   aws.Int64(1), // Short timeout for test
		})
		require.NoError(t, err, "Should receive message on attempt %d", i+1)

		if len(result.Messages) == 0 {
			// Message moved to DLQ
			break
		}

		// Don't delete - simulate processing failure
		t.Logf("Received message attempt %d/%d", i+1, maxReceiveCount)

		// Wait for visibility timeout
		time.Sleep(2 * time.Second)
	}

	// Wait for message to move to DLQ
	time.Sleep(5 * time.Second)

	// Verify message is in DLQ
	dlqResult, err := sqsClient.ReceiveMessage(&sqs.ReceiveMessageInput{
		QueueUrl:            aws.String(dlqURL),
		MaxNumberOfMessages: aws.Int64(1),
		WaitTimeSeconds:     aws.Int64(10),
	})
	require.NoError(t, err, "Should receive message from DLQ")
	require.Len(t, dlqResult.Messages, 1, "Poison message should be in DLQ")

	// Clean up: Delete from DLQ
	_, err = sqsClient.DeleteMessage(&sqs.DeleteMessageInput{
		QueueUrl:      aws.String(dlqURL),
		ReceiptHandle: dlqResult.Messages[0].ReceiptHandle,
	})
	require.NoError(t, err, "Should delete message from DLQ")
}

// Helper functions

func createSQSClient(t *testing.T) *sqs.SQS {
	// AWS SDK will use default credential chain (env vars, ~/.aws/credentials, IAM role)
	client := sqs.New(createAWSSession(t))
	return client
}

func createCloudWatchClient(t *testing.T) *cloudwatch.CloudWatch {
	client := cloudwatch.New(createAWSSession(t))
	return client
}

func createAWSSession(t *testing.T) *session.Session {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String("ap-southeast-1"), // Match your region
	})
	require.NoError(t, err, "Should create AWS session")
	return sess
}

func verifyAlarmExists(t *testing.T, cwClient *cloudwatch.CloudWatch, alarmName string) {
	result, err := cwClient.DescribeAlarms(&cloudwatch.DescribeAlarmsInput{
		AlarmNames: []*string{aws.String(alarmName)},
	})
	require.NoError(t, err, "Should describe alarm")
	require.Len(t, result.MetricAlarms, 1, "Alarm %s should exist", alarmName)

	alarm := result.MetricAlarms[0]
	assert.Equal(t, alarmName, *alarm.AlarmName, "Alarm name should match")
	assert.Equal(t, "AWS/SQS", *alarm.Namespace, "Alarm should monitor SQS namespace")
}
