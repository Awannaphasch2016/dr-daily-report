// DynamoDB Integration Tests
//
// These tests verify DynamoDB tables are deployed correctly with proper configuration.
// Tests run against actual AWS infrastructure in the dev environment.
//
// Usage:
//   cd terraform/tests
//   go test -v -timeout 10m -run TestDynamoDB

package test

import (
	"testing"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/dynamodb"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// DynamoDB table names
// NOTE: cache table was removed (never used) - caching moved to Aurora
var (
	watchlistTable = "dr-daily-report-telegram-watchlist-" + environment
	jobsTable      = "dr-daily-report-telegram-jobs-" + environment
)

// getDynamoDBClient creates a DynamoDB client for the test region
func getDynamoDBClient(t *testing.T) *dynamodb.DynamoDB {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String(awsRegion),
	})
	require.NoError(t, err, "Failed to create AWS session")
	return dynamodb.New(sess)
}

// TestWatchlistTableExists verifies the watchlist table exists and is active
func TestWatchlistTableExists(t *testing.T) {
	t.Parallel()

	client := getDynamoDBClient(t)

	result, err := client.DescribeTable(&dynamodb.DescribeTableInput{
		TableName: aws.String(watchlistTable),
	})
	require.NoError(t, err, "Watchlist table should exist")

	table := result.Table
	assert.Equal(t, "ACTIVE", *table.TableStatus, "Table should be active")
}

// TestWatchlistTableSchema verifies the watchlist table has correct schema
func TestWatchlistTableSchema(t *testing.T) {
	t.Parallel()

	client := getDynamoDBClient(t)

	result, err := client.DescribeTable(&dynamodb.DescribeTableInput{
		TableName: aws.String(watchlistTable),
	})
	require.NoError(t, err, "Failed to describe watchlist table")

	table := result.Table

	// Check key schema
	keySchema := table.KeySchema
	require.Len(t, keySchema, 2, "Watchlist table should have partition and sort key")

	// Verify partition key (user_id)
	var partitionKey, sortKey *dynamodb.KeySchemaElement
	for _, key := range keySchema {
		if *key.KeyType == "HASH" {
			partitionKey = key
		} else if *key.KeyType == "RANGE" {
			sortKey = key
		}
	}

	assert.NotNil(t, partitionKey, "Table should have partition key")
	assert.Equal(t, "user_id", *partitionKey.AttributeName, "Partition key should be user_id")

	assert.NotNil(t, sortKey, "Table should have sort key")
	assert.Equal(t, "ticker", *sortKey.AttributeName, "Sort key should be ticker")
}

// TestJobsTableExists verifies the jobs table exists and is active
func TestJobsTableExists(t *testing.T) {
	t.Parallel()

	client := getDynamoDBClient(t)

	result, err := client.DescribeTable(&dynamodb.DescribeTableInput{
		TableName: aws.String(jobsTable),
	})
	require.NoError(t, err, "Jobs table should exist")

	table := result.Table
	assert.Equal(t, "ACTIVE", *table.TableStatus, "Table should be active")
}

// TestJobsTableTTL verifies the jobs table has TTL enabled
func TestJobsTableTTL(t *testing.T) {
	t.Parallel()

	client := getDynamoDBClient(t)

	result, err := client.DescribeTimeToLive(&dynamodb.DescribeTimeToLiveInput{
		TableName: aws.String(jobsTable),
	})
	require.NoError(t, err, "Failed to describe TTL for jobs table")

	ttlDescription := result.TimeToLiveDescription
	assert.Equal(t, "ENABLED", *ttlDescription.TimeToLiveStatus, "Jobs table should have TTL enabled")
	assert.Equal(t, "ttl", *ttlDescription.AttributeName, "TTL attribute should be 'ttl'")
}

// NOTE: TestCacheTableExists removed - cache table deprecated (using Aurora instead)

// TestDynamoDBBillingMode verifies tables use PAY_PER_REQUEST billing
func TestDynamoDBBillingMode(t *testing.T) {
	t.Parallel()

	client := getDynamoDBClient(t)

	tables := []string{watchlistTable, jobsTable}

	for _, tableName := range tables {
		t.Run(tableName, func(t *testing.T) {
			result, err := client.DescribeTable(&dynamodb.DescribeTableInput{
				TableName: aws.String(tableName),
			})
			require.NoError(t, err, "Failed to describe table %s", tableName)

			// PAY_PER_REQUEST tables don't have provisioned throughput set
			table := result.Table
			billingMode := table.BillingModeSummary
			if billingMode != nil {
				assert.Equal(t, "PAY_PER_REQUEST", *billingMode.BillingMode,
					"Table %s should use PAY_PER_REQUEST billing", tableName)
			}
		})
	}
}

// TestDynamoDBReadWriteOperations tests basic read/write operations
func TestDynamoDBReadWriteOperations(t *testing.T) {
	t.Parallel()

	client := getDynamoDBClient(t)

	// Test write operation
	testItem := map[string]*dynamodb.AttributeValue{
		"user_id": {S: aws.String("test-user-terratest")},
		"ticker":  {S: aws.String("TEST-TICKER")},
		"ttl":     {N: aws.String("9999999999")}, // Far future
	}

	_, err := client.PutItem(&dynamodb.PutItemInput{
		TableName: aws.String(watchlistTable),
		Item:      testItem,
	})
	require.NoError(t, err, "Should be able to write to watchlist table")

	// Test read operation
	result, err := client.GetItem(&dynamodb.GetItemInput{
		TableName: aws.String(watchlistTable),
		Key: map[string]*dynamodb.AttributeValue{
			"user_id": {S: aws.String("test-user-terratest")},
			"ticker":  {S: aws.String("TEST-TICKER")},
		},
	})
	require.NoError(t, err, "Should be able to read from watchlist table")
	assert.NotNil(t, result.Item, "Should find the test item")

	// Clean up test item
	_, err = client.DeleteItem(&dynamodb.DeleteItemInput{
		TableName: aws.String(watchlistTable),
		Key: map[string]*dynamodb.AttributeValue{
			"user_id": {S: aws.String("test-user-terratest")},
			"ticker":  {S: aws.String("TEST-TICKER")},
		},
	})
	require.NoError(t, err, "Should be able to delete test item")
}
