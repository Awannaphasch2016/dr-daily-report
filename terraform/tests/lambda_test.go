// Lambda Integration Tests
//
// These tests verify Lambda functions are deployed correctly and can be invoked.
// Tests run against actual AWS infrastructure in the dev environment.
//
// Usage:
//   cd terraform/tests
//   go test -v -timeout 10m -run TestLambda
//
// Note: API endpoint tests use HTTP requests through API Gateway (not direct Lambda invocation)
// because the Lambda uses Mangum adapter which expects HTTP API v2 event format.

package test

import (
	"encoding/json"
	"io"
	"net/http"
	"os"
	"testing"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/lambda"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// Test configuration
var (
	awsRegion     = getEnvOrDefault("AWS_REGION", "ap-southeast-1")
	environment   = getEnvOrDefault("ENVIRONMENT", "dev")
	// Lambda function names
	telegramAPIFn = "dr-daily-report-telegram-api-" + environment
	schedulerFn   = "dr-daily-report-ticker-scheduler-" + environment
	// API Gateway endpoint URL (used for HTTP tests)
	// Set via TELEGRAM_API_URL env var or default to dev endpoint
	telegramAPIURL = getEnvOrDefault("TELEGRAM_API_URL", "https://ou0ivives1.execute-api.ap-southeast-1.amazonaws.com")
)

func getEnvOrDefault(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// getLambdaClient creates a Lambda client for the test region
func getLambdaClient(t *testing.T) *lambda.Lambda {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String(awsRegion),
	})
	require.NoError(t, err, "Failed to create AWS session")
	return lambda.New(sess)
}

// TestTelegramAPIHealthCheck tests the Telegram API health endpoint via HTTP
// Uses actual API Gateway endpoint to test full integration
func TestTelegramAPIHealthCheck(t *testing.T) {
	t.Parallel()

	client := getHTTPClient()
	url := telegramAPIURL + "/api/v1/health"

	resp, err := client.Get(url)
	require.NoError(t, err, "HTTP request failed")
	defer resp.Body.Close()

	// Read response body
	body, err := io.ReadAll(resp.Body)
	require.NoError(t, err, "Failed to read response body")

	// Verify HTTP status
	assert.Equal(t, http.StatusOK, resp.StatusCode,
		"Health check should return 200, got %d. Body: %s", resp.StatusCode, string(body))

	// Parse JSON response
	var response map[string]interface{}
	err = json.Unmarshal(body, &response)
	require.NoError(t, err, "Failed to parse JSON response")

	// Check response contains status field
	_, hasStatus := response["status"]
	assert.True(t, hasStatus, "Response should have 'status' field. Got: %v", response)

	t.Logf("Health check response: %s", string(body))
}

// TestTelegramAPISearchEndpoint tests the ticker search endpoint via HTTP
// Uses actual API Gateway endpoint to test full integration
func TestTelegramAPISearchEndpoint(t *testing.T) {
	t.Parallel()

	client := getHTTPClient()
	url := telegramAPIURL + "/api/v1/search?q=DBS"

	resp, err := client.Get(url)
	require.NoError(t, err, "HTTP request failed")
	defer resp.Body.Close()

	// Read response body
	body, err := io.ReadAll(resp.Body)
	require.NoError(t, err, "Failed to read response body")

	// Verify HTTP status
	assert.Equal(t, http.StatusOK, resp.StatusCode,
		"Search should return 200, got %d. Body: %s", resp.StatusCode, string(body))

	// Parse JSON response
	var response map[string]interface{}
	err = json.Unmarshal(body, &response)
	require.NoError(t, err, "Failed to parse JSON response")

	// Check response contains results (array)
	results, hasResults := response["results"]
	assert.True(t, hasResults, "Response should have 'results' field. Got: %v", response)

	// Results should be an array
	resultsArr, ok := results.([]interface{})
	assert.True(t, ok, "Results should be an array")
	assert.NotEmpty(t, resultsArr, "Search for 'DBS' should return results")

	t.Logf("Search returned %d results", len(resultsArr))
}

// TestSchedulerLambdaExists tests that the scheduler Lambda exists and can be invoked
func TestSchedulerLambdaExists(t *testing.T) {
	t.Parallel()

	client := getLambdaClient(t)

	// Get function configuration
	result, err := client.GetFunction(&lambda.GetFunctionInput{
		FunctionName: aws.String(schedulerFn),
	})
	require.NoError(t, err, "Scheduler Lambda should exist")

	// Verify configuration
	config := result.Configuration
	assert.Equal(t, "Active", *config.State, "Lambda should be in Active state")
	assert.NotNil(t, config.MemorySize, "Lambda should have memory configured")
	assert.NotNil(t, config.Timeout, "Lambda should have timeout configured")
}

// TestLambdaVPCConfiguration tests that Lambda functions are in VPC (if required)
func TestLambdaVPCConfiguration(t *testing.T) {
	t.Parallel()

	client := getLambdaClient(t)

	// Get function configuration
	result, err := client.GetFunction(&lambda.GetFunctionInput{
		FunctionName: aws.String(schedulerFn),
	})
	require.NoError(t, err, "Failed to get Lambda configuration")

	// Scheduler Lambda should be in VPC (for Aurora access)
	vpcConfig := result.Configuration.VpcConfig
	assert.NotNil(t, vpcConfig, "Scheduler Lambda should have VPC config for Aurora access")

	if vpcConfig != nil {
		assert.NotEmpty(t, vpcConfig.SubnetIds, "Lambda should have subnet IDs")
		assert.NotEmpty(t, vpcConfig.SecurityGroupIds, "Lambda should have security group IDs")
	}
}

// TestTelegramAPILambdaExists tests that the Telegram API Lambda exists with live alias
func TestTelegramAPILambdaExists(t *testing.T) {
	t.Parallel()

	client := getLambdaClient(t)

	// Check base function exists
	result, err := client.GetFunction(&lambda.GetFunctionInput{
		FunctionName: aws.String(telegramAPIFn),
	})
	require.NoError(t, err, "Telegram API Lambda %s should exist", telegramAPIFn)

	config := result.Configuration
	assert.Equal(t, "Active", *config.State, "Lambda should be in Active state")

	// Check "live" alias exists
	aliasResult, err := client.GetAlias(&lambda.GetAliasInput{
		FunctionName: aws.String(telegramAPIFn),
		Name:         aws.String("live"),
	})
	require.NoError(t, err, "Lambda should have 'live' alias")
	assert.NotEmpty(t, *aliasResult.FunctionVersion, "Live alias should point to a version")

	t.Logf("Lambda %s has 'live' alias pointing to version %s", telegramAPIFn, *aliasResult.FunctionVersion)
}

// TestSchedulerLambdaLiveAlias verifies Scheduler Lambda has 'live' alias for zero-downtime deployment.
// EventBridge invokes via this alias, not $LATEST.
func TestSchedulerLambdaLiveAlias(t *testing.T) {
	t.Parallel()

	client := getLambdaClient(t)

	// Check "live" alias exists
	aliasResult, err := client.GetAlias(&lambda.GetAliasInput{
		FunctionName: aws.String(schedulerFn),
		Name:         aws.String("live"),
	})
	require.NoError(t, err, "Scheduler Lambda should have 'live' alias")
	assert.NotEmpty(t, *aliasResult.FunctionVersion, "Live alias should point to a version")

	// Alias should point to a numbered version, not $LATEST
	assert.NotEqual(t, "$LATEST", *aliasResult.FunctionVersion,
		"Live alias should point to a published version, not $LATEST")

	t.Logf("Scheduler Lambda 'live' alias points to version %s", *aliasResult.FunctionVersion)
}

// TestSchedulerLambdaEnvironmentVariables verifies Scheduler has required env vars for parallel precompute.
// This catches the bug where REPORT_JOBS_QUEUE_URL was missing.
func TestSchedulerLambdaEnvironmentVariables(t *testing.T) {
	t.Parallel()

	client := getLambdaClient(t)

	result, err := client.GetFunction(&lambda.GetFunctionInput{
		FunctionName: aws.String(schedulerFn),
	})
	require.NoError(t, err, "Failed to get Scheduler Lambda configuration")

	envVars := result.Configuration.Environment
	require.NotNil(t, envVars, "Lambda should have environment variables")
	require.NotNil(t, envVars.Variables, "Lambda should have environment variables map")

	// Required env vars for parallel precompute
	requiredVars := []string{
		"REPORT_JOBS_QUEUE_URL", // SQS queue for fan-out
		"JOBS_TABLE_NAME",       // DynamoDB for job tracking
		"ENVIRONMENT",
	}
	for _, varName := range requiredVars {
		value, exists := envVars.Variables[varName]
		assert.True(t, exists, "Scheduler Lambda should have %s environment variable", varName)
		if exists {
			assert.NotEmpty(t, *value, "%s should not be empty", varName)
		}
	}

	t.Logf("✅ Scheduler Lambda has required env vars for parallel precompute")
}

// TestLambdaEnvironmentVariables tests that required environment variables are set
func TestLambdaEnvironmentVariables(t *testing.T) {
	t.Parallel()

	client := getLambdaClient(t)

	// Get function configuration (base function, not alias)
	result, err := client.GetFunction(&lambda.GetFunctionInput{
		FunctionName: aws.String(telegramAPIFn),
	})
	require.NoError(t, err, "Failed to get Lambda configuration")

	// Check environment variables exist (not their values for security)
	envVars := result.Configuration.Environment
	assert.NotNil(t, envVars, "Lambda should have environment variables")

	if envVars != nil && envVars.Variables != nil {
		// Check for required environment variables
		requiredVars := []string{"ENVIRONMENT"}
		for _, varName := range requiredVars {
			_, exists := envVars.Variables[varName]
			assert.True(t, exists, "Lambda should have %s environment variable", varName)
		}
	}
}

// TestTelegramAPIAuroraConfiguration verifies Telegram API Lambda has Aurora config
// for cache-first report lookup. This catches the bug where Lambda couldn't connect
// to Aurora because it was missing AURORA_HOST env var and VPC config.
//
// Prerequisites:
//   - aurora_enabled = true in terraform.tfvars
//
// TDD: This test GUARDS against cache-first failures due to missing Aurora config.
func TestTelegramAPIAuroraConfiguration(t *testing.T) {
	t.Parallel()

	client := getLambdaClient(t)

	// Get function configuration
	result, err := client.GetFunction(&lambda.GetFunctionInput{
		FunctionName: aws.String(telegramAPIFn),
	})
	require.NoError(t, err, "Failed to get Telegram API Lambda configuration")

	config := result.Configuration
	envVars := config.Environment

	// Check Aurora environment variables
	require.NotNil(t, envVars, "Lambda should have environment variables")
	require.NotNil(t, envVars.Variables, "Lambda should have environment variables map")

	// Required Aurora env vars for cache-first behavior
	auroraEnvVars := []string{"AURORA_HOST", "AURORA_USER", "AURORA_DATABASE", "AURORA_PORT"}
	for _, varName := range auroraEnvVars {
		value, exists := envVars.Variables[varName]
		assert.True(t, exists, "Lambda should have %s environment variable for Aurora cache access", varName)
		if exists {
			assert.NotEmpty(t, *value, "%s should not be empty", varName)
		}
	}

	// AURORA_PASSWORD should exist (but we don't log its value)
	_, hasPassword := envVars.Variables["AURORA_PASSWORD"]
	assert.True(t, hasPassword, "Lambda should have AURORA_PASSWORD environment variable")

	// Check VPC configuration (required to reach Aurora in VPC)
	vpcConfig := config.VpcConfig
	require.NotNil(t, vpcConfig, "Lambda must have VPC config to access Aurora")
	assert.NotEmpty(t, vpcConfig.SubnetIds, "Lambda VPC config must have subnet IDs")
	assert.NotEmpty(t, vpcConfig.SecurityGroupIds, "Lambda VPC config must have security group IDs")

	t.Logf("✅ Telegram API Lambda has Aurora config:")
	t.Logf("   AURORA_HOST: %s", *envVars.Variables["AURORA_HOST"])
	t.Logf("   AURORA_DATABASE: %s", *envVars.Variables["AURORA_DATABASE"])
	t.Logf("   VPC Subnets: %d", len(vpcConfig.SubnetIds))
	t.Logf("   Security Groups: %d", len(vpcConfig.SecurityGroupIds))
}
