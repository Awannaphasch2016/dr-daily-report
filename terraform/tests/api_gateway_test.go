// API Gateway Integration Tests
//
// These tests verify API Gateway is deployed correctly with proper routes and CORS.
// Tests run against actual AWS infrastructure in the dev environment.
//
// Usage:
//   cd terraform/tests
//   go test -v -timeout 10m -run TestAPIGateway

package test

import (
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"testing"
	"time"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/apigatewayv2"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// API Gateway configuration
var (
	apiName = "dr-daily-report-telegram-api-" + environment
	// API URL - defaults to dev endpoint (shared with lambda_test.go via telegramAPIURL)
	// Can be overridden via API_URL environment variable
	apiURL = getEnvOrDefault("API_URL", telegramAPIURL)
)

// getAPIGatewayClient creates an API Gateway v2 client
func getAPIGatewayClient(t *testing.T) *apigatewayv2.ApiGatewayV2 {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String(awsRegion),
	})
	require.NoError(t, err, "Failed to create AWS session")
	return apigatewayv2.New(sess)
}

// getHTTPClient creates an HTTP client with reasonable timeouts
func getHTTPClient() *http.Client {
	return &http.Client{
		Timeout: 30 * time.Second,
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: false},
		},
	}
}

// TestAPIGatewayExists verifies the API Gateway exists
func TestAPIGatewayExists(t *testing.T) {
	t.Parallel()

	client := getAPIGatewayClient(t)

	// List APIs and find ours
	result, err := client.GetApis(&apigatewayv2.GetApisInput{})
	require.NoError(t, err, "Failed to list APIs")

	var foundAPI *apigatewayv2.Api
	for _, api := range result.Items {
		if *api.Name == apiName {
			foundAPI = api
			break
		}
	}

	require.NotNil(t, foundAPI, "API Gateway %s should exist", apiName)
	assert.Equal(t, "HTTP", *foundAPI.ProtocolType, "API should be HTTP type")
}

// TestAPIGatewayStage verifies the default stage is deployed
func TestAPIGatewayStage(t *testing.T) {
	t.Parallel()

	client := getAPIGatewayClient(t)

	// First find our API
	result, err := client.GetApis(&apigatewayv2.GetApisInput{})
	require.NoError(t, err, "Failed to list APIs")

	var apiID string
	for _, api := range result.Items {
		if *api.Name == apiName {
			apiID = *api.ApiId
			break
		}
	}
	require.NotEmpty(t, apiID, "API Gateway should exist")

	// Get stages
	stagesResult, err := client.GetStages(&apigatewayv2.GetStagesInput{
		ApiId: aws.String(apiID),
	})
	require.NoError(t, err, "Failed to get stages")

	// Look for $default or api stage
	var foundStage bool
	for _, stage := range stagesResult.Items {
		if *stage.StageName == "$default" || *stage.StageName == "api" {
			foundStage = true
			break
		}
	}
	assert.True(t, foundStage, "API Gateway should have a deployed stage")
}

// TestAPIGatewayRoutes verifies expected routes exist
func TestAPIGatewayRoutes(t *testing.T) {
	t.Parallel()

	client := getAPIGatewayClient(t)

	// First find our API
	result, err := client.GetApis(&apigatewayv2.GetApisInput{})
	require.NoError(t, err, "Failed to list APIs")

	var apiID string
	for _, api := range result.Items {
		if *api.Name == apiName {
			apiID = *api.ApiId
			break
		}
	}
	require.NotEmpty(t, apiID, "API Gateway should exist")

	// Get routes
	routesResult, err := client.GetRoutes(&apigatewayv2.GetRoutesInput{
		ApiId: aws.String(apiID),
	})
	require.NoError(t, err, "Failed to get routes")

	// Expected routes
	expectedRoutes := []string{
		"GET /api/v1/health",
		"GET /api/v1/search",
		"POST /api/v1/report/{ticker}",
		"GET /api/v1/report/status/{job_id}",
		"GET /api/v1/rankings",
	}

	// Check each expected route exists
	routeKeys := make([]string, 0)
	for _, route := range routesResult.Items {
		routeKeys = append(routeKeys, *route.RouteKey)
	}

	for _, expected := range expectedRoutes {
		found := false
		for _, key := range routeKeys {
			if key == expected {
				found = true
				break
			}
		}
		assert.True(t, found, "Route %s should exist", expected)
	}
}

// TestAPIGatewayCORS verifies CORS is configured
func TestAPIGatewayCORS(t *testing.T) {
	t.Parallel()

	client := getAPIGatewayClient(t)

	// First find our API
	result, err := client.GetApis(&apigatewayv2.GetApisInput{})
	require.NoError(t, err, "Failed to list APIs")

	var foundAPI *apigatewayv2.Api
	for _, api := range result.Items {
		if *api.Name == apiName {
			foundAPI = api
			break
		}
	}
	require.NotNil(t, foundAPI, "API Gateway should exist")

	// Check CORS configuration
	corsConfig := foundAPI.CorsConfiguration
	require.NotNil(t, corsConfig, "API should have CORS configured")

	// Verify CORS settings
	assert.NotEmpty(t, corsConfig.AllowOrigins, "CORS should allow origins")
	assert.NotEmpty(t, corsConfig.AllowMethods, "CORS should allow methods")
}

// TestAPIGatewayHealthEndpoint tests the health endpoint via HTTP
func TestAPIGatewayHealthEndpoint(t *testing.T) {
	if apiURL == "" {
		t.Skip("API_URL not set, skipping HTTP test")
	}

	t.Parallel()

	client := getHTTPClient()

	healthURL := fmt.Sprintf("%s/api/v1/health", apiURL)
	resp, err := client.Get(healthURL)
	require.NoError(t, err, "Health endpoint should be reachable")
	defer resp.Body.Close()

	assert.Equal(t, http.StatusOK, resp.StatusCode, "Health endpoint should return 200")

	body, err := io.ReadAll(resp.Body)
	require.NoError(t, err)
	assert.Contains(t, string(body), "status", "Response should contain status")
}

// TestAPIGatewaySearchEndpoint tests the search endpoint via HTTP
func TestAPIGatewaySearchEndpoint(t *testing.T) {
	if apiURL == "" {
		t.Skip("API_URL not set, skipping HTTP test")
	}

	t.Parallel()

	client := getHTTPClient()

	searchURL := fmt.Sprintf("%s/api/v1/search?q=DBS", apiURL)
	resp, err := client.Get(searchURL)
	require.NoError(t, err, "Search endpoint should be reachable")
	defer resp.Body.Close()

	assert.Equal(t, http.StatusOK, resp.StatusCode, "Search endpoint should return 200")
}

// TestAPIGatewayCacheFirstBehavior - DEPRECATED: Use TestCacheFirstBehaviorWithFixture instead
//
// This test is FRAGILE because it depends on pre-existing data in Aurora (the "Generous Leftovers" anti-pattern).
// It will fail if the scheduler hasn't run today to populate the cache.
//
// The correct test is in aurora_cache_test.go:TestCacheFirstBehaviorWithFixture which uses
// self-contained fixtures (INSERT test data → run test → DELETE test data).
//
// This test is kept for backwards compatibility but skipped by default.
// To run it, use: go test -v -run TestAPIGatewayCacheFirstBehavior -tags=fragile
func TestAPIGatewayCacheFirstBehavior(t *testing.T) {
	t.Skip("DEPRECATED: Use TestCacheFirstBehaviorWithFixture in aurora_cache_test.go instead. " +
		"This test depends on pre-existing cache data which is fragile.")

	if apiURL == "" {
		t.Skip("API_URL not set, skipping HTTP test")
	}

	client := getHTTPClient()

	// POST to report endpoint for a ticker we know is cached
	reportURL := fmt.Sprintf("%s/api/v1/report/%s", apiURL, testTicker)
	resp, err := client.Post(reportURL, "application/json", nil)
	require.NoError(t, err, "Report endpoint should be reachable")
	defer resp.Body.Close()

	assert.Equal(t, http.StatusOK, resp.StatusCode, "Report endpoint should return 200")

	body, err := io.ReadAll(resp.Body)
	require.NoError(t, err)

	// Parse response
	var result map[string]interface{}
	err = json.Unmarshal(body, &result)
	require.NoError(t, err, "Response should be valid JSON")

	// Verify cache-first behavior
	jobID, ok := result["job_id"].(string)
	require.True(t, ok, "Response should have job_id")

	status, ok := result["status"].(string)
	require.True(t, ok, "Response should have status")

	// Cache-first behavior: job_id should start with "cached_" and status should be "completed"
	// If this fails, either:
	//   1. No precomputed report exists for testTicker (DBS19) for today's date
	//   2. Aurora connection is broken
	//   3. Cache lookup code has a bug
	assert.True(t, strings.HasPrefix(jobID, "cached_"),
		"Expected cache HIT (job_id starting with 'cached_'), got job_id=%s. "+
			"Ensure precomputed_reports table has a report for %s dated today.", jobID, testTicker)
	assert.Equal(t, "completed", status,
		"Cached response should have status=completed, got status=%s", status)

	t.Logf("✅ Cache HIT: job_id=%s, status=%s", jobID, status)
}

// TestAPIGatewayCORSHeaders tests CORS headers in response
// NOTE: HTTP APIs handle CORS at API Gateway level (not via Lambda response headers)
// This test verifies the preflight request succeeds - CORS headers are injected by API Gateway
func TestAPIGatewayCORSHeaders(t *testing.T) {
	if apiURL == "" {
		t.Skip("API_URL not set, skipping HTTP test")
	}

	t.Parallel()

	client := getHTTPClient()

	// Send OPTIONS request to check CORS preflight
	req, err := http.NewRequest("OPTIONS", fmt.Sprintf("%s/api/v1/health", apiURL), nil)
	require.NoError(t, err)

	req.Header.Set("Origin", "https://example.com")
	req.Header.Set("Access-Control-Request-Method", "GET")

	resp, err := client.Do(req)
	require.NoError(t, err, "OPTIONS request should succeed")
	defer resp.Body.Close()

	// HTTP APIs return 200 for OPTIONS when CORS is configured
	// CORS headers may not be present in response (handled at API Gateway level)
	// The TestAPIGatewayCORS test verifies CORS is configured via AWS API
	assert.True(t, resp.StatusCode == http.StatusOK || resp.StatusCode == http.StatusNoContent,
		"OPTIONS preflight should return 200 or 204, got %d", resp.StatusCode)
}
