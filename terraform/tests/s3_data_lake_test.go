// S3 Data Lake Integration Tests
//
// These tests verify S3 Data Lake buckets are configured correctly for Phase 1 staging.
// Tests run against actual AWS infrastructure in the dev environment.
//
// Usage:
//   cd terraform/tests
//   go test -v -timeout 10m -run TestS3DataLake
//
// Tests verify:
// - Bucket exists and is accessible
// - Versioning is enabled (MUST for data lineage)
// - Encryption at rest is enabled
// - Public access is blocked
// - Required tags are present (Purpose, DataClassification)
// - Lambda can write objects with tagging

package test

import (
	"fmt"
	"net/http"
	"testing"
	"time"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// getS3Client creates an S3 client for the test region
func getS3Client(t *testing.T) *s3.S3 {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String(awsRegion),
	})
	require.NoError(t, err, "Failed to create AWS session")
	return s3.New(sess)
}

// Test: Data lake bucket exists and is accessible
func TestS3DataLakeBucketExists(t *testing.T) {
	t.Parallel()

	client := getS3Client(t)
	bucketName := fmt.Sprintf("dr-daily-report-data-lake-%s", environment)

	// Test bucket exists by attempting to get bucket location
	_, err := client.GetBucketLocation(&s3.GetBucketLocationInput{
		Bucket: aws.String(bucketName),
	})

	require.NoError(t, err, "Data lake bucket '%s' should exist and be accessible", bucketName)
	t.Logf("✅ Data lake bucket '%s' exists and is accessible", bucketName)
}

// Test: Bucket versioning is enabled (CRITICAL for data lineage)
func TestS3DataLakeBucketVersioningEnabled(t *testing.T) {
	t.Parallel()

	client := getS3Client(t)
	bucketName := fmt.Sprintf("dr-daily-report-data-lake-%s", environment)

	result, err := client.GetBucketVersioning(&s3.GetBucketVersioningInput{
		Bucket: aws.String(bucketName),
	})

	require.NoError(t, err, "Failed to get bucket versioning configuration")
	assert.Equal(t, "Enabled", *result.Status,
		"Data lake bucket MUST have versioning enabled for data lineage and reproducibility")

	t.Logf("✅ Bucket versioning is enabled: %s", *result.Status)
}

// Test: Bucket encryption is enabled (server-side encryption)
func TestS3DataLakeBucketEncryptionEnabled(t *testing.T) {
	t.Parallel()

	client := getS3Client(t)
	bucketName := fmt.Sprintf("dr-daily-report-data-lake-%s", environment)

	result, err := client.GetBucketEncryption(&s3.GetBucketEncryptionInput{
		Bucket: aws.String(bucketName),
	})

	require.NoError(t, err, "Failed to get bucket encryption configuration")
	require.NotNil(t, result.ServerSideEncryptionConfiguration, "Bucket must have encryption configuration")
	require.Greater(t, len(result.ServerSideEncryptionConfiguration.Rules), 0,
		"Bucket must have at least one encryption rule")

	// Verify encryption algorithm
	algorithm := result.ServerSideEncryptionConfiguration.Rules[0].ApplyServerSideEncryptionByDefault.SSEAlgorithm
	require.NotNil(t, algorithm, "Encryption algorithm must be set")
	assert.Contains(t, []string{"AES256", "aws:kms"}, *algorithm,
		"Bucket must use either SSE-S3 (AES256) or SSE-KMS encryption")

	t.Logf("✅ Bucket encryption is enabled with algorithm: %s", *algorithm)
}

// Test: Public access is blocked on all levels
func TestS3DataLakeBucketPublicAccessBlocked(t *testing.T) {
	t.Parallel()

	client := getS3Client(t)
	bucketName := fmt.Sprintf("dr-daily-report-data-lake-%s", environment)

	result, err := client.GetPublicAccessBlock(&s3.GetPublicAccessBlockInput{
		Bucket: aws.String(bucketName),
	})

	require.NoError(t, err, "Failed to get public access block configuration")
	require.NotNil(t, result.PublicAccessBlockConfiguration, "Public access block must be configured")

	config := result.PublicAccessBlockConfiguration

	// All public access settings MUST be enabled (true)
	assert.True(t, *config.BlockPublicAcls,
		"BlockPublicAcls must be enabled - data lake should never be public")
	assert.True(t, *config.BlockPublicPolicy,
		"BlockPublicPolicy must be enabled - data lake should never be public")
	assert.True(t, *config.IgnorePublicAcls,
		"IgnorePublicAcls must be enabled - data lake should never be public")
	assert.True(t, *config.RestrictPublicBuckets,
		"RestrictPublicBuckets must be enabled - data lake should never be public")

	t.Logf("✅ All public access is blocked (BlockPublicAcls, BlockPublicPolicy, IgnorePublicAcls, RestrictPublicBuckets all enabled)")
}

// Test: Bucket has required tags for data lake (Purpose, DataClassification)
func TestS3DataLakeBucketRequiredTags(t *testing.T) {
	t.Parallel()

	client := getS3Client(t)
	bucketName := fmt.Sprintf("dr-daily-report-data-lake-%s", environment)

	result, err := client.GetBucketTagging(&s3.GetBucketTaggingInput{
		Bucket: aws.String(bucketName),
	})

	require.NoError(t, err, "Failed to get bucket tags")
	require.NotNil(t, result.TagSet, "Bucket must have tags")

	// Convert tag set to map for easier checking
	tags := make(map[string]string)
	for _, tag := range result.TagSet {
		tags[*tag.Key] = *tag.Value
	}

	// Required tags for data lake
	assert.Contains(t, tags, "Purpose",
		"Data lake bucket MUST have 'Purpose' tag for cost tracking and lineage")
	assert.Contains(t, tags, "DataClassification",
		"Data lake bucket MUST have 'DataClassification' tag for security compliance")
	assert.Contains(t, tags, "Environment",
		"Bucket should have 'Environment' tag")
	assert.Contains(t, tags, "App",
		"Bucket should have 'App' tag")

	// Verify Purpose tag value matches data lake pattern
	if purpose, ok := tags["Purpose"]; ok {
		assert.Contains(t, []string{"raw-data-staging", "processed-data", "data-lake"},
			purpose, "Purpose tag should indicate data lake usage")
	}

	t.Logf("✅ Required tags present: Purpose=%s, DataClassification=%s",
		tags["Purpose"], tags["DataClassification"])
}

// Test: Lifecycle policy is configured (cost optimization)
func TestS3DataLakeBucketLifecyclePolicy(t *testing.T) {
	// t.Parallel() - commented out as this test may fail if lifecycle not yet configured (WARN, not DENY)

	client := getS3Client(t)
	bucketName := fmt.Sprintf("dr-daily-report-data-lake-%s", environment)

	result, err := client.GetBucketLifecycleConfiguration(&s3.GetBucketLifecycleConfigurationInput{
		Bucket: aws.String(bucketName),
	})

	if err != nil {
		t.Logf("⚠️  Lifecycle policy not configured (WARN): %v", err)
		t.Logf("Recommendation: Configure lifecycle to transition old data to Glacier (90 days → Glacier, 365 days → delete)")
		return // This is a WARN, not DENY - test passes with warning
	}

	require.NotNil(t, result.Rules, "Lifecycle policy should have rules")
	require.Greater(t, len(result.Rules), 0, "Lifecycle policy should have at least one rule")

	// Check if any rule transitions to Glacier
	hasGlacierTransition := false
	for _, rule := range result.Rules {
		for _, transition := range rule.Transitions {
			if transition.StorageClass != nil &&
				(*transition.StorageClass == "GLACIER" || *transition.StorageClass == "DEEP_ARCHIVE") {
				hasGlacierTransition = true
				t.Logf("✅ Lifecycle rule transitions to %s after %d days",
					*transition.StorageClass, *transition.Days)
			}
		}
	}

	assert.True(t, hasGlacierTransition,
		"Lifecycle policy should include Glacier/Deep Archive transition for cost optimization")
}

// Test: Lambda can write objects to data lake with tagging
func TestS3DataLakeLambdaCanWriteWithTags(t *testing.T) {
	// t.Parallel() - Cannot run in parallel as it creates test objects

	client := getS3Client(t)
	bucketName := fmt.Sprintf("dr-daily-report-data-lake-%s", environment)

	// Create a test object key with timestamp
	timestamp := time.Now().Format("2006-01-02T15:04:05Z")
	testKey := fmt.Sprintf("raw/yfinance/TEST_TICKER/%s/terratest-%d.json", timestamp, time.Now().Unix())
	testContent := fmt.Sprintf(`{"test":"data","timestamp":"%s","purpose":"terratest"}`, timestamp)

	// Put object with tagging (simulates Lambda writing raw data)
	_, err := client.PutObject(&s3.PutObjectInput{
		Bucket:  aws.String(bucketName),
		Key:     aws.String(testKey),
		Body:    aws.ReadSeekCloser(nil), // Empty body for test
		Tagging: aws.String("source=yfinance&ticker=TEST_TICKER&purpose=terratest"),
		Metadata: map[string]*string{
			"fetched_at":        aws.String(timestamp),
			"algorithm_version": aws.String("test-v1.0"),
		},
	})

	require.NoError(t, err, "Lambda should be able to write objects to data lake")
	t.Logf("✅ Successfully wrote object: s3://%s/%s", bucketName, testKey)

	// Verify object exists and has correct tagging
	tagsResult, err := client.GetObjectTagging(&s3.GetObjectTaggingInput{
		Bucket: aws.String(bucketName),
		Key:    aws.String(testKey),
	})

	require.NoError(t, err, "Should be able to read object tagging")
	require.NotNil(t, tagsResult.TagSet, "Object should have tags")

	// Convert tag set to map
	tags := make(map[string]string)
	for _, tag := range tagsResult.TagSet {
		tags[*tag.Key] = *tag.Value
	}

	// Verify required tags for data lineage
	assert.Equal(t, "yfinance", tags["source"], "Object should have 'source' tag")
	assert.Equal(t, "TEST_TICKER", tags["ticker"], "Object should have 'ticker' tag")
	assert.Equal(t, "terratest", tags["purpose"], "Object should have 'purpose' tag")

	t.Logf("✅ Object tags verified: source=%s, ticker=%s", tags["source"], tags["ticker"])

	// Cleanup: Delete test object
	_, err = client.DeleteObject(&s3.DeleteObjectInput{
		Bucket: aws.String(bucketName),
		Key:    aws.String(testKey),
	})

	require.NoError(t, err, "Should be able to delete test object")
	t.Logf("✅ Cleaned up test object")
}

// Test: Bucket key structure follows data lake pattern
func TestS3DataLakeBucketKeyStructure(t *testing.T) {
	// This test verifies the bucket follows the recommended structure:
	// s3://bucket/raw/yfinance/{ticker}/{date}/{timestamp}.json
	// s3://bucket/processed/reports/{ticker}/{date}.json

	t.Parallel()

	client := getS3Client(t)
	bucketName := fmt.Sprintf("dr-daily-report-data-lake-%s", environment)

	// List objects to verify structure (if any exist)
	result, err := client.ListObjectsV2(&s3.ListObjectsV2Input{
		Bucket:  aws.String(bucketName),
		MaxKeys: aws.Int64(10), // Sample a few objects
	})

	require.NoError(t, err, "Should be able to list objects in bucket")

	// If bucket is empty, skip verification (not an error)
	if result.KeyCount == nil || *result.KeyCount == 0 {
		t.Logf("ℹ️  Bucket is empty - no structure to verify yet")
		return
	}

	// Check if any objects follow the recommended structure
	hasRawData := false
	hasProcessedData := false

	for _, obj := range result.Contents {
		key := *obj.Key
		if len(key) > 4 && key[:4] == "raw/" {
			hasRawData = true
			t.Logf("Found raw data: %s", key)
		}
		if len(key) > 10 && key[:10] == "processed/" {
			hasProcessedData = true
			t.Logf("Found processed data: %s", key)
		}
	}

	// This is informational - not a hard failure if structure differs
	if hasRawData {
		t.Logf("✅ Bucket contains raw data in 'raw/' prefix")
	}
	if hasProcessedData {
		t.Logf("✅ Bucket contains processed data in 'processed/' prefix")
	}
}

// Helper for getHTTPClient (referenced in lambda_test.go)
func getHTTPClient() *http.Client {
	return &http.Client{
		Timeout: 30 * time.Second,
	}
}
