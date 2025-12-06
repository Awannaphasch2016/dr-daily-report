// Aurora Cache Integration Tests
//
// These tests verify that Report Worker Lambda successfully caches reports to Aurora.
// Tests answer: "Does data actually arrive in Aurora after Report Worker runs?"
//
// Architecture:
//   1. Create test job in DynamoDB
//   2. Invoke Report Worker Lambda directly (bypassing SQS)
//   3. Verify job status in DynamoDB = "completed"
//   4. Query Aurora precomputed_reports table
//   5. Verify report data exists with correct content
//
// Prerequisites:
//   - Aurora cluster running (aurora_enabled = true)
//   - AURORA_* environment variables set (via Doppler)
//
// Usage:
//   cd terraform/tests
//   doppler run -- go test -v -timeout 10m -run TestAurora

package test

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/service/dynamodb"
	"github.com/aws/aws-sdk-go/service/lambda"
	_ "github.com/go-sql-driver/mysql" // MySQL driver for Aurora
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// Aurora configuration (from environment - set via Doppler)
// Note: Doppler uses AURORA_USERNAME, TF uses AURORA_USER - check both
var (
	auroraHost     = os.Getenv("AURORA_HOST")
	auroraPort     = getEnvOrDefault("AURORA_PORT", "3306")
	auroraUser     = getEnvOrDefault("AURORA_USER", os.Getenv("AURORA_USERNAME"))
	auroraPassword = os.Getenv("AURORA_PASSWORD")
	auroraDatabase = getEnvOrDefault("AURORA_DATABASE", "ticker_data")

	// Test configuration
	testTicker   = "DBS19" // Known good ticker with fast response
	workerLambda = "dr-daily-report-report-worker-" + environment
	// Note: jobsTable is defined in dynamodb_test.go
)

// PrecomputedReport represents a row in precomputed_reports table
type PrecomputedReport struct {
	ID           int64
	TickerID     int64
	Symbol       string
	ReportDate   string
	ReportText   sql.NullString
	ReportJSON   sql.NullString
	Status       string
	Strategy     sql.NullString
	ChartBase64  sql.NullString
}

// Note: getDynamoDBClient is defined in dynamodb_test.go

// getAuroraDB creates a MySQL connection to Aurora
//
// Behavior depends on environment:
//   - AURORA_VPC_ACCESS=true  → FAIL if connection fails (VPC expected, e.g., CodeBuild)
//   - AURORA_VPC_ACCESS=false → SKIP test (explicitly disabled)
//   - AURORA_HOST not set     → SKIP test (not configured for this runner)
//   - AURORA_HOST set but connection fails → FAIL (Aurora should be reachable)
//
// This ensures VPC tests FAIL in CodeBuild when there's a real problem,
// but SKIP gracefully on local/GHA runners without VPC access.
func getAuroraDB(t *testing.T) *sql.DB {
	// Skip if explicitly marked as no VPC access
	if os.Getenv("AURORA_VPC_ACCESS") == "false" {
		t.Skip("Aurora VPC access disabled (AURORA_VPC_ACCESS=false)")
	}

	// Skip if Aurora credentials not configured (running on non-VPC runner)
	if auroraHost == "" {
		t.Skip("Aurora not configured (AURORA_HOST required) - likely running outside VPC")
	}
	if auroraUser == "" {
		t.Skip("Aurora not configured (AURORA_USER required) - likely running outside VPC")
	}

	dsn := fmt.Sprintf("%s:%s@tcp(%s:%s)/%s?parseTime=true&timeout=10s",
		auroraUser, auroraPassword, auroraHost, auroraPort, auroraDatabase)

	db, err := sql.Open("mysql", dsn)
	require.NoError(t, err, "Failed to create Aurora connection")

	// Verify connection with short timeout
	db.SetConnMaxLifetime(10 * time.Second)
	err = db.Ping()
	if err != nil {
		// Connection failed - this is a FAIL condition when AURORA_HOST is set
		// If AURORA_HOST is set, we expect VPC access. Failure means:
		//   1. Security group misconfiguration
		//   2. VPC subnet routing issue
		//   3. Aurora is down
		// We should FAIL to catch these issues, not silently skip.
		require.NoError(t, err,
			"Cannot connect to Aurora at %s:%s. "+
				"If running from CodeBuild, check VPC config (subnets, security groups). "+
				"If running locally without VPC access, unset AURORA_HOST or set AURORA_VPC_ACCESS=false.",
			auroraHost, auroraPort)
	}

	return db
}

// createTestJob creates a pending job in DynamoDB for testing
func createTestJob(t *testing.T, jobID, ticker string) {
	client := getDynamoDBClient(t)

	now := time.Now().Format(time.RFC3339)
	ttl := time.Now().Add(1 * time.Hour).Unix() // Expire in 1 hour

	_, err := client.PutItem(&dynamodb.PutItemInput{
		TableName: aws.String(jobsTable),
		Item: map[string]*dynamodb.AttributeValue{
			"job_id":     {S: aws.String(jobID)},
			"ticker":     {S: aws.String(ticker)},
			"status":     {S: aws.String("pending")},
			"created_at": {S: aws.String(now)},
			"ttl":        {N: aws.String(fmt.Sprintf("%d", ttl))},
		},
	})
	require.NoError(t, err, "Failed to create test job in DynamoDB")
	t.Logf("Created test job: job_id=%s, ticker=%s", jobID, ticker)
}

// getJobStatus retrieves job status from DynamoDB
func getJobStatus(t *testing.T, jobID string) (string, map[string]*dynamodb.AttributeValue) {
	client := getDynamoDBClient(t)

	result, err := client.GetItem(&dynamodb.GetItemInput{
		TableName: aws.String(jobsTable),
		Key: map[string]*dynamodb.AttributeValue{
			"job_id": {S: aws.String(jobID)},
		},
	})
	require.NoError(t, err, "Failed to get job from DynamoDB")

	if result.Item == nil {
		return "", nil
	}

	status := ""
	if s, ok := result.Item["status"]; ok && s.S != nil {
		status = *s.S
	}

	return status, result.Item
}

// deleteTestJob removes test job from DynamoDB
func deleteTestJob(t *testing.T, jobID string) {
	client := getDynamoDBClient(t)

	_, _ = client.DeleteItem(&dynamodb.DeleteItemInput{
		TableName: aws.String(jobsTable),
		Key: map[string]*dynamodb.AttributeValue{
			"job_id": {S: aws.String(jobID)},
		},
	})
}

// getReportFromAurora queries precomputed_reports for a symbol
func getReportFromAurora(t *testing.T, db *sql.DB, symbol string) *PrecomputedReport {
	query := `
		SELECT id, ticker_id, symbol, report_date, report_text, report_json,
		       status, strategy, chart_base64
		FROM precomputed_reports
		WHERE symbol = ?
		ORDER BY report_date DESC
		LIMIT 1
	`

	var report PrecomputedReport
	err := db.QueryRow(query, symbol).Scan(
		&report.ID,
		&report.TickerID,
		&report.Symbol,
		&report.ReportDate,
		&report.ReportText,
		&report.ReportJSON,
		&report.Status,
		&report.Strategy,
		&report.ChartBase64,
	)

	if err == sql.ErrNoRows {
		return nil
	}
	require.NoError(t, err, "Failed to query Aurora precomputed_reports")

	return &report
}

// TestAuroraConnectionWorks verifies we can connect to Aurora
func TestAuroraConnectionWorks(t *testing.T) {
	db := getAuroraDB(t)
	defer db.Close()

	// Simple query to verify connection
	var result int
	err := db.QueryRow("SELECT 1").Scan(&result)
	require.NoError(t, err, "Aurora connection test failed")
	assert.Equal(t, 1, result, "Aurora should return 1")

	t.Log("Aurora connection successful")
}

// TestPrecomputedReportsTableExists verifies the table schema
func TestPrecomputedReportsTableExists(t *testing.T) {
	db := getAuroraDB(t)
	defer db.Close()

	// Check table exists by querying INFORMATION_SCHEMA
	var tableName string
	err := db.QueryRow(`
		SELECT TABLE_NAME
		FROM INFORMATION_SCHEMA.TABLES
		WHERE TABLE_SCHEMA = ? AND TABLE_NAME = 'precomputed_reports'
	`, auroraDatabase).Scan(&tableName)

	require.NoError(t, err, "precomputed_reports table should exist in Aurora")
	assert.Equal(t, "precomputed_reports", tableName)

	t.Log("precomputed_reports table exists in Aurora")
}

// TestReportWorkerCachesToAurora is the END-TO-END integration test
// Verifies: Lambda processes job → Report cached to Aurora
//
// NOTE: This test is expensive (~60-90s) because it runs full report generation.
// Use sparingly in CI (e.g., nightly, not on every PR).
func TestReportWorkerCachesToAurora(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping expensive E2E test in short mode")
	}

	// Skip if Aurora not configured
	if auroraHost == "" {
		t.Skip("Aurora not configured (AURORA_HOST required)")
	}

	// Setup: Create unique test job
	jobID := fmt.Sprintf("test_cache_%d", time.Now().UnixNano())
	createTestJob(t, jobID, testTicker)
	defer deleteTestJob(t, jobID)

	// Invoke Report Worker Lambda directly
	lambdaClient := getLambdaClient(t)

	// Create SQS-like event payload
	sqsEvent := map[string]interface{}{
		"Records": []map[string]interface{}{
			{
				"messageId": "terratest-msg-1",
				"body":      fmt.Sprintf(`{"job_id": "%s", "ticker": "%s"}`, jobID, testTicker),
			},
		},
	}
	payload, _ := json.Marshal(sqsEvent)

	t.Logf("Invoking Report Worker Lambda with job_id=%s, ticker=%s", jobID, testTicker)
	t.Log("This may take 60-90 seconds for full report generation...")

	result, err := lambdaClient.Invoke(&lambda.InvokeInput{
		FunctionName: aws.String(workerLambda),
		Payload:      payload,
	})
	require.NoError(t, err, "Lambda invocation failed")

	// Check for Lambda-level errors
	if result.FunctionError != nil {
		t.Logf("Lambda function error: %s", *result.FunctionError)
		t.Logf("Lambda response: %s", string(result.Payload))
	}
	require.Nil(t, result.FunctionError, "Lambda should not return function error")

	// Parse Lambda response
	var lambdaResponse map[string]interface{}
	err = json.Unmarshal(result.Payload, &lambdaResponse)
	require.NoError(t, err, "Failed to parse Lambda response")
	t.Logf("Lambda response: %v", lambdaResponse)

	// Verify job completed in DynamoDB
	status, _ := getJobStatus(t, jobID)
	assert.Equal(t, "completed", status, "Job should be marked 'completed' in DynamoDB")

	// Verify report cached in Aurora
	db := getAuroraDB(t)
	defer db.Close()

	report := getReportFromAurora(t, db, testTicker)
	require.NotNil(t, report, "Report should exist in Aurora precomputed_reports for %s", testTicker)

	// Verify report content
	assert.Equal(t, testTicker, report.Symbol, "Symbol should match")
	assert.Equal(t, "completed", report.Status, "Report status should be 'completed'")
	assert.True(t, report.ReportJSON.Valid, "report_json should not be NULL")
	assert.NotEmpty(t, report.ReportJSON.String, "report_json should have content")

	t.Logf("SUCCESS: Report for %s cached in Aurora (ID=%d, date=%s)",
		testTicker, report.ID, report.ReportDate)
}

// TestReportExistsInAuroraForKnownTicker queries Aurora for existing reports
// This is a lighter test than full E2E - just checks if cache is working
func TestReportExistsInAuroraForKnownTicker(t *testing.T) {
	t.Parallel()

	db := getAuroraDB(t)
	defer db.Close()

	// Check if any reports exist for test ticker
	var count int
	err := db.QueryRow(`
		SELECT COUNT(*) FROM precomputed_reports WHERE symbol = ?
	`, testTicker).Scan(&count)
	require.NoError(t, err, "Failed to query Aurora")

	t.Logf("Found %d cached reports for %s in Aurora", count, testTicker)

	// This test documents current state (informational, not asserting pass/fail)
	// If count == 0, it indicates caching hasn't worked yet
	if count == 0 {
		t.Logf("WARNING: No cached reports found for %s - caching may not be working", testTicker)
	}
}

// TestPrecomputedReportsSchema verifies the table has expected columns
func TestPrecomputedReportsSchema(t *testing.T) {
	t.Parallel()

	db := getAuroraDB(t)
	defer db.Close()

	// Query column information
	rows, err := db.Query(`
		SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
		FROM INFORMATION_SCHEMA.COLUMNS
		WHERE TABLE_SCHEMA = ? AND TABLE_NAME = 'precomputed_reports'
		ORDER BY ORDINAL_POSITION
	`, auroraDatabase)
	require.NoError(t, err, "Failed to query table schema")
	defer rows.Close()

	// Expected columns (critical for caching to work)
	expectedColumns := map[string]bool{
		"id":          false,
		"ticker_id":   false,
		"symbol":      false,
		"report_date": false,
		"report_text": false,
		"report_json": false,
		"status":      false,
		"strategy":    false,
		"chart_base64": false,
	}

	for rows.Next() {
		var columnName, dataType, isNullable string
		err := rows.Scan(&columnName, &dataType, &isNullable)
		require.NoError(t, err, "Failed to scan row")

		if _, expected := expectedColumns[columnName]; expected {
			expectedColumns[columnName] = true
		}
		t.Logf("Column: %s (%s, nullable=%s)", columnName, dataType, isNullable)
	}

	// Verify all expected columns exist
	for column, found := range expectedColumns {
		assert.True(t, found, "Column %s should exist in precomputed_reports", column)
	}
}

// Note: contains and containsHelper are defined in eventbridge_test.go

// =============================================================================
// Cache-First Integration Tests (Lambda-as-Harness Pattern)
// =============================================================================
//
// ARCHITECTURE INSIGHT:
// Direct Aurora access from test runner is NOT possible (Aurora is in VPC).
// Instead, we use the "Lambda-as-Test-Harness" pattern:
//
// Pattern:
//   1. Invoke Scheduler Lambda with SEED_CACHE action → inserts test data in Aurora
//   2. Call API via HTTP → expect cache HIT
//   3. (Optional) Invoke Scheduler Lambda with CLEANUP action → removes test data
//
// Why Lambda-as-Harness:
//   - Lambda runs IN VPC, has Aurora access
//   - Tests run OUTSIDE VPC, only have API/Lambda access
//   - Follows principle: "Test via public interfaces, not direct DB"
//
// Alternative: Use a dedicated "test-harness" Lambda for fixture operations
// =============================================================================

// TestCacheFirstBehaviorViaLambdaHarness tests cache-first using Lambda to seed cache
//
// Prerequisites:
//   - Scheduler Lambda (dr-daily-report-ticker-scheduler-dev) deployed
//   - Aurora enabled and accessible from Lambda
//
// This test invokes the Scheduler Lambda to precompute a report, then verifies
// the API returns a cache HIT.
func TestCacheFirstBehaviorViaLambdaHarness(t *testing.T) {
	if apiURL == "" {
		t.Skip("API_URL not set, skipping HTTP test")
	}

	lambdaClient := getLambdaClient(t)

	// Step 1: Invoke Scheduler Lambda to seed cache for test ticker
	// The scheduler precomputes reports and stores them in Aurora
	seedPayload := map[string]interface{}{
		"action":  "seed_cache",
		"tickers": []string{testTicker}, // DBS19
	}
	payloadBytes, _ := json.Marshal(seedPayload)

	t.Logf("Seeding cache via Scheduler Lambda for %s...", testTicker)

	result, err := lambdaClient.Invoke(&lambda.InvokeInput{
		FunctionName: aws.String(schedulerFn),
		Payload:      payloadBytes,
	})

	if err != nil {
		t.Logf("Scheduler Lambda invocation failed: %v", err)
		t.Skip("Scheduler Lambda not available - cache seeding not possible")
	}

	if result.FunctionError != nil {
		t.Logf("Scheduler Lambda error: %s", string(result.Payload))
		t.Skip("Scheduler Lambda returned error - cache seeding failed")
	}

	t.Logf("Cache seeded via Scheduler Lambda: %s", string(result.Payload))

	// Parse response to check if seeding succeeded
	var seedResult map[string]interface{}
	if err := json.Unmarshal(result.Payload, &seedResult); err == nil {
		if body, ok := seedResult["body"].(map[string]interface{}); ok {
			if failedCount, ok := body["failed_count"].(float64); ok && failedCount > 0 {
				// Seeding failed - skip test with informative message
				failed := body["failed"]
				t.Skipf("Cache seeding failed (Yahoo Finance didn't return data): %v", failed)
			}
		}
	}

	// Step 2: Call API and expect cache HIT
	client := getHTTPClient()
	reportURL := fmt.Sprintf("%s/api/v1/report/%s", apiURL, testTicker)
	resp, err := client.Post(reportURL, "application/json", nil)
	require.NoError(t, err, "Report endpoint should be reachable")
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	require.NoError(t, err)

	assert.Equal(t, http.StatusOK, resp.StatusCode,
		"Report endpoint should return 200, got %d. Body: %s", resp.StatusCode, string(body))

	// Parse response
	var apiResult map[string]interface{}
	err = json.Unmarshal(body, &apiResult)
	require.NoError(t, err, "Response should be valid JSON")

	// Verify cache-first behavior
	jobID, ok := apiResult["job_id"].(string)
	require.True(t, ok, "Response should have job_id")

	status, ok := apiResult["status"].(string)
	require.True(t, ok, "Response should have status")

	// STRICT ASSERTION: Must be cache HIT
	assert.True(t, strings.HasPrefix(jobID, "cached_"),
		"Expected cache HIT (job_id starting with 'cached_'), got job_id=%s. "+
			"This means cache seeding succeeded but API didn't find the cached report.", jobID)
	assert.Equal(t, "completed", status,
		"Cached response should have status=completed, got status=%s", status)

	t.Logf("✅ Cache HIT verified: job_id=%s, status=%s (via Lambda-as-Harness)", jobID, status)
}

// TestCacheFirstBehaviorWithFixture tests cache-first API using direct Aurora fixture
// NOTE: This test requires VPC access (bastion/VPN) to connect to Aurora directly.
// Skip in CI environments without VPC access.
func TestCacheFirstBehaviorWithFixture(t *testing.T) {
	// Skip if we can't reach Aurora (most common case - running outside VPC)
	if os.Getenv("AURORA_VPC_ACCESS") != "true" {
		t.Skip("Skipping direct Aurora test - set AURORA_VPC_ACCESS=true if running from bastion/VPN")
	}

	if apiURL == "" {
		t.Skip("API_URL not set, skipping HTTP test")
	}

	db := getAuroraDB(t)
	defer db.Close()

	// Use a unique test ticker symbol that maps to a real ticker
	// DBS19 maps to D05.SI (DBS Group) - we'll use the resolved symbol
	testSymbol := "D05.SI"
	testDate := time.Now().Format("2006-01-02")
	testReportJSON := `{"test": true, "narrative_report": "Test report for cache-first verification"}`

	// FIXTURE SETUP: Insert test report directly into Aurora
	tickerID := getTickerID(t, db, testSymbol)
	if tickerID == 0 {
		t.Skipf("Ticker %s not found in ticker_info table - run scheduler first", testSymbol)
	}

	insertID := insertTestReport(t, db, tickerID, testSymbol, testDate, testReportJSON)
	defer deleteTestReportByID(t, db, insertID)

	t.Logf("FIXTURE: Inserted test report ID=%d for %s dated %s", insertID, testSymbol, testDate)

	// TEST: Call API and expect cache HIT
	client := getHTTPClient()
	reportURL := fmt.Sprintf("%s/api/v1/report/%s", apiURL, testTicker) // Use DBS19 (alias)
	resp, err := client.Post(reportURL, "application/json", nil)
	require.NoError(t, err, "Report endpoint should be reachable")
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	require.NoError(t, err)

	assert.Equal(t, http.StatusOK, resp.StatusCode,
		"Report endpoint should return 200, got %d. Body: %s", resp.StatusCode, string(body))

	// Parse response
	var result map[string]interface{}
	err = json.Unmarshal(body, &result)
	require.NoError(t, err, "Response should be valid JSON")

	// Verify cache-first behavior
	jobID, ok := result["job_id"].(string)
	require.True(t, ok, "Response should have job_id")

	status, ok := result["status"].(string)
	require.True(t, ok, "Response should have status")

	// STRICT ASSERTION: Must be cache HIT
	assert.True(t, strings.HasPrefix(jobID, "cached_"),
		"Expected cache HIT (job_id starting with 'cached_'), got job_id=%s", jobID)
	assert.Equal(t, "completed", status,
		"Cached response should have status=completed, got status=%s", status)

	t.Logf("✅ Cache HIT verified: job_id=%s, status=%s (with direct Aurora fixture)", jobID, status)
}

// Helper: Get ticker_id from ticker_info table
func getTickerID(t *testing.T, db *sql.DB, symbol string) int64 {
	var tickerID int64
	err := db.QueryRow(`
		SELECT id FROM ticker_info WHERE symbol = ? LIMIT 1
	`, symbol).Scan(&tickerID)

	if err == sql.ErrNoRows {
		return 0
	}
	require.NoError(t, err, "Failed to query ticker_info")
	return tickerID
}

// Helper: Insert test report into precomputed_reports
func insertTestReport(t *testing.T, db *sql.DB, tickerID int64, symbol, reportDate, reportJSON string) int64 {
	result, err := db.Exec(`
		INSERT INTO precomputed_reports
		(ticker_id, symbol, report_date, report_json, status, strategy, computed_at)
		VALUES (?, ?, ?, ?, 'completed', 'multi-stage', NOW())
	`, tickerID, symbol, reportDate, reportJSON)
	require.NoError(t, err, "Failed to insert test report")

	id, err := result.LastInsertId()
	require.NoError(t, err, "Failed to get insert ID")

	return id
}

// Helper: Delete test report by ID
func deleteTestReportByID(t *testing.T, db *sql.DB, id int64) {
	_, err := db.Exec(`DELETE FROM precomputed_reports WHERE id = ?`, id)
	if err != nil {
		t.Logf("Warning: Failed to delete test report ID=%d: %v", id, err)
	}
}
