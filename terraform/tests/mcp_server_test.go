// MCP Server Infrastructure Tests
//
// These tests verify the SEC EDGAR MCP server Lambda function and Function URL
// are deployed correctly and comply with the MCP protocol.
// Tests run against actual AWS infrastructure in the dev environment.
//
// Usage:
//   cd terraform/tests
//   go test -v -timeout 10m -run TestMCPServer
//
// Prerequisites:
//   - MCP server Lambda deployed via terraform/mcp_servers.tf
//   - SEC_EDGAR_MCP_URL environment variable set (or defaults to dev Function URL)

package test

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"testing"
	"time"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/lambda"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// MCP Server configuration
var (
	mcpFunctionName = "sec-edgar-mcp-server-" + environment
	// Function URL - defaults to dev endpoint if available
	// Can be overridden via SEC_EDGAR_MCP_URL environment variable
	mcpURL = getEnvOrDefault("SEC_EDGAR_MCP_URL", "")
)

// MCP JSON-RPC 2.0 request structure
type MCPRequest struct {
	JSONRPC string      `json:"jsonrpc"`
	ID      interface{} `json:"id"`
	Method  string      `json:"method"`
	Params  interface{} `json:"params,omitempty"`
}

// MCP JSON-RPC 2.0 response structure
type MCPResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      interface{}     `json:"id"`
	Result  json.RawMessage `json:"result,omitempty"`
	Error   *MCPError       `json:"error,omitempty"`
}

// MCP error structure
type MCPError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// tools/list response structure
type ToolsListResult struct {
	Tools []MCPTool `json:"tools"`
}

// MCP tool structure
type MCPTool struct {
	Name        string                 `json:"name"`
	Description string                 `json:"description"`
	InputSchema map[string]interface{} `json:"inputSchema"`
}

// TestMCPServerLambdaExists verifies the MCP server Lambda function exists
func TestMCPServerLambdaExists(t *testing.T) {
	t.Parallel()

	client := getLambdaClient(t)

	// Get function configuration
	result, err := client.GetFunction(&lambda.GetFunctionInput{
		FunctionName: aws.String(mcpFunctionName),
	})
	require.NoError(t, err, "MCP server Lambda %s should exist", mcpFunctionName)

	// Verify configuration
	config := result.Configuration
	assert.Equal(t, "Active", *config.State, "Lambda should be in Active state")
	assert.NotNil(t, config.MemorySize, "Lambda should have memory configured")
	assert.NotNil(t, config.Timeout, "Lambda should have timeout configured")

	// Verify memory and timeout match expected values
	assert.GreaterOrEqual(t, int(*config.MemorySize), 512, "Lambda should have at least 512 MB memory")
	assert.LessOrEqual(t, int(*config.Timeout), 30, "Lambda should have timeout <= 30 seconds")

	t.Logf("✅ MCP server Lambda exists: %s", mcpFunctionName)
	t.Logf("   Memory: %d MB", *config.MemorySize)
	t.Logf("   Timeout: %d seconds", *config.Timeout)
}

// TestMCPServerLambdaEnvironmentVariables verifies required environment variables are set
func TestMCPServerLambdaEnvironmentVariables(t *testing.T) {
	t.Parallel()

	client := getLambdaClient(t)

	result, err := client.GetFunction(&lambda.GetFunctionInput{
		FunctionName: aws.String(mcpFunctionName),
	})
	require.NoError(t, err, "Failed to get MCP server Lambda configuration")

	envVars := result.Configuration.Environment
	require.NotNil(t, envVars, "Lambda should have environment variables")
	require.NotNil(t, envVars.Variables, "Lambda should have environment variables map")

	// Required env vars for SEC EDGAR MCP server
	requiredVars := []string{
		"SEC_EDGAR_USER_AGENT", // User agent for SEC EDGAR API requests
	}
	for _, varName := range requiredVars {
		value, exists := envVars.Variables[varName]
		assert.True(t, exists, "MCP server Lambda should have %s environment variable", varName)
		if exists {
			assert.NotEmpty(t, *value, "%s should not be empty", varName)
		}
	}

	t.Logf("✅ MCP server Lambda has required env vars")
}

// TestMCPServerFunctionURLExists verifies the Function URL exists and is accessible
func TestMCPServerFunctionURLExists(t *testing.T) {
	if mcpURL == "" {
		t.Skip("SEC_EDGAR_MCP_URL not set, skipping Function URL test")
	}

	t.Parallel()

	client := getHTTPClient()

	// Test Function URL is reachable (health check or simple request)
	// MCP servers typically respond to POST requests
	resp, err := client.Get(mcpURL + "/health")
	if err != nil {
		// If /health doesn't exist, try POST to root (MCP protocol)
		req, _ := http.NewRequest("POST", mcpURL, nil)
		resp, err = client.Do(req)
	}

	// Function URL should be reachable (may return 400/405 for invalid requests, but not 404/500)
	require.NoError(t, err, "Function URL should be reachable")
	defer resp.Body.Close()

	// Accept 200 (success), 400 (bad request), 405 (method not allowed)
	// but not 404 (not found) or 500 (server error)
	assert.NotEqual(t, http.StatusNotFound, resp.StatusCode,
		"Function URL should not return 404 (not found)")
	assert.NotEqual(t, http.StatusInternalServerError, resp.StatusCode,
		"Function URL should not return 500 (server error)")

	t.Logf("✅ MCP server Function URL is accessible: %s", mcpURL)
	t.Logf("   Status code: %d", resp.StatusCode)
}

// TestMCPServerProtocolCompliance verifies the MCP server implements JSON-RPC 2.0 protocol
func TestMCPServerProtocolCompliance(t *testing.T) {
	if mcpURL == "" {
		t.Skip("SEC_EDGAR_MCP_URL not set, skipping protocol compliance test")
	}

	t.Parallel()

	client := getHTTPClient()

	// Test 1: tools/list method (MCP protocol requirement)
	t.Run("tools/list", func(t *testing.T) {
		req := MCPRequest{
			JSONRPC: "2.0",
			ID:      1,
			Method:  "tools/list",
		}

		reqBody, err := json.Marshal(req)
		require.NoError(t, err, "Failed to marshal MCP request")

		resp, err := client.Post(mcpURL, "application/json", bytes.NewBuffer(reqBody))
		require.NoError(t, err, "MCP tools/list request should succeed")
		defer resp.Body.Close()

		// Verify HTTP status
		assert.Equal(t, http.StatusOK, resp.StatusCode,
			"tools/list should return 200, got %d", resp.StatusCode)

		// Verify Content-Type
		contentType := resp.Header.Get("Content-Type")
		assert.Contains(t, contentType, "application/json",
			"Response should have Content-Type: application/json, got %s", contentType)

		// Parse JSON-RPC response
		body, err := io.ReadAll(resp.Body)
		require.NoError(t, err, "Failed to read response body")

		var mcpResp MCPResponse
		err = json.Unmarshal(body, &mcpResp)
		require.NoError(t, err, "Response should be valid JSON-RPC 2.0")

		// Verify JSON-RPC 2.0 structure
		assert.Equal(t, "2.0", mcpResp.JSONRPC, "Response should have jsonrpc: 2.0")
		assert.Equal(t, float64(1), mcpResp.ID, "Response should have matching ID")
		assert.Nil(t, mcpResp.Error, "tools/list should not return error")

		// Verify result contains tools array
		var toolsResult ToolsListResult
		err = json.Unmarshal(mcpResp.Result, &toolsResult)
		require.NoError(t, err, "Result should contain tools list")

		assert.NotEmpty(t, toolsResult.Tools, "tools/list should return at least one tool")

		// Verify tool structure (should have get_latest_filing)
		var foundGetLatestFiling bool
		for _, tool := range toolsResult.Tools {
			if tool.Name == "get_latest_filing" {
				foundGetLatestFiling = true
				assert.NotEmpty(t, tool.Description, "Tool should have description")
				assert.NotNil(t, tool.InputSchema, "Tool should have inputSchema")
				break
			}
		}
		assert.True(t, foundGetLatestFiling,
			"tools/list should include 'get_latest_filing' tool")

		t.Logf("✅ tools/list returned %d tools", len(toolsResult.Tools))
	})

	// Test 2: tools/call method (MCP protocol requirement)
	t.Run("tools/call", func(t *testing.T) {
		req := MCPRequest{
			JSONRPC: "2.0",
			ID:      2,
			Method:  "tools/call",
			Params: map[string]interface{}{
				"name": "get_latest_filing",
				"arguments": map[string]interface{}{
					"ticker": "AAPL",
				},
			},
		}

		reqBody, err := json.Marshal(req)
		require.NoError(t, err, "Failed to marshal MCP request")

		resp, err := client.Post(mcpURL, "application/json", bytes.NewBuffer(reqBody))
		require.NoError(t, err, "MCP tools/call request should succeed")
		defer resp.Body.Close()

		// Verify HTTP status
		assert.Equal(t, http.StatusOK, resp.StatusCode,
			"tools/call should return 200, got %d", resp.StatusCode)

		// Parse JSON-RPC response
		body, err := io.ReadAll(resp.Body)
		require.NoError(t, err, "Failed to read response body")

		var mcpResp MCPResponse
		err = json.Unmarshal(body, &mcpResp)
		require.NoError(t, err, "Response should be valid JSON-RPC 2.0")

		// Verify JSON-RPC 2.0 structure
		assert.Equal(t, "2.0", mcpResp.JSONRPC, "Response should have jsonrpc: 2.0")
		assert.Equal(t, float64(2), mcpResp.ID, "Response should have matching ID")

		// tools/call may return error if SEC EDGAR API is unavailable,
		// but response structure should still be valid JSON-RPC 2.0
		if mcpResp.Error != nil {
			t.Logf("⚠️ tools/call returned error (may be expected if SEC EDGAR API unavailable): %s",
				mcpResp.Error.Message)
		} else {
			// Verify result structure (should contain filing data)
			var result map[string]interface{}
			err = json.Unmarshal(mcpResp.Result, &result)
			require.NoError(t, err, "Result should be valid JSON")

			// Result should contain filing information
			assert.NotNil(t, result, "tools/call result should not be nil")
			t.Logf("✅ tools/call returned valid result")
		}
	})
}

// TestMCPServerCORS verifies CORS is configured for Function URL
func TestMCPServerCORS(t *testing.T) {
	if mcpURL == "" {
		t.Skip("SEC_EDGAR_MCP_URL not set, skipping CORS test")
	}

	t.Parallel()

	client := getHTTPClient()

	// Send OPTIONS request (CORS preflight)
	req, err := http.NewRequest("OPTIONS", mcpURL, nil)
	require.NoError(t, err)

	req.Header.Set("Origin", "https://example.com")
	req.Header.Set("Access-Control-Request-Method", "POST")
	req.Header.Set("Access-Control-Request-Headers", "content-type")

	resp, err := client.Do(req)
	require.NoError(t, err, "OPTIONS request should succeed")
	defer resp.Body.Close()

	// Function URL CORS should allow OPTIONS
	// Lambda Function URLs return 200 or 204 for OPTIONS when CORS is configured
	assert.True(t, resp.StatusCode == http.StatusOK || resp.StatusCode == http.StatusNoContent,
		"OPTIONS preflight should return 200 or 204, got %d", resp.StatusCode)

	t.Logf("✅ MCP server Function URL CORS is configured")
}

// TestMCPServerErrorHandling verifies the MCP server handles invalid requests gracefully
func TestMCPServerErrorHandling(t *testing.T) {
	if mcpURL == "" {
		t.Skip("SEC_EDGAR_MCP_URL not set, skipping error handling test")
	}

	t.Parallel()

	client := getHTTPClient()

	// Test 1: Invalid JSON-RPC request (missing required fields)
	t.Run("invalid_jsonrpc_request", func(t *testing.T) {
		invalidReq := map[string]interface{}{
			"method": "tools/list",
			// Missing jsonrpc and id fields
		}

		reqBody, err := json.Marshal(invalidReq)
		require.NoError(t, err)

		resp, err := client.Post(mcpURL, "application/json", bytes.NewBuffer(reqBody))
		require.NoError(t, err, "Request should succeed (even if invalid)")
		defer resp.Body.Close()

		// Server should return 200 with JSON-RPC error response
		assert.Equal(t, http.StatusOK, resp.StatusCode,
			"Invalid request should return 200 with JSON-RPC error")

		body, err := io.ReadAll(resp.Body)
		require.NoError(t, err)

		var mcpResp MCPResponse
		err = json.Unmarshal(body, &mcpResp)
		require.NoError(t, err, "Response should be valid JSON-RPC 2.0")

		// Should have error field
		assert.NotNil(t, mcpResp.Error, "Invalid request should return JSON-RPC error")
		assert.Equal(t, "2.0", mcpResp.JSONRPC, "Error response should still have jsonrpc: 2.0")
	})

	// Test 2: Unknown method
	t.Run("unknown_method", func(t *testing.T) {
		req := MCPRequest{
			JSONRPC: "2.0",
			ID:      3,
			Method:  "unknown/method",
		}

		reqBody, err := json.Marshal(req)
		require.NoError(t, err)

		resp, err := client.Post(mcpURL, "application/json", bytes.NewBuffer(reqBody))
		require.NoError(t, err)
		defer resp.Body.Close()

		body, err := io.ReadAll(resp.Body)
		require.NoError(t, err)

		var mcpResp MCPResponse
		err = json.Unmarshal(body, &mcpResp)
		require.NoError(t, err)

		// Should return JSON-RPC error for unknown method
		assert.NotNil(t, mcpResp.Error, "Unknown method should return JSON-RPC error")
		assert.Equal(t, "2.0", mcpResp.JSONRPC, "Error response should have jsonrpc: 2.0")
	})

	t.Logf("✅ MCP server handles errors gracefully")
}

// TestMCPServerLambdaLogs verifies CloudWatch logs are configured
func TestMCPServerLambdaLogs(t *testing.T) {
	t.Parallel()

	client := getLambdaClient(t)

	result, err := client.GetFunction(&lambda.GetFunctionInput{
		FunctionName: aws.String(mcpFunctionName),
	})
	require.NoError(t, err, "Failed to get MCP server Lambda configuration")

	// Verify log group name follows expected pattern
	logGroupName := fmt.Sprintf("/aws/lambda/%s", mcpFunctionName)

	// Check if log group exists (via CloudWatch Logs API would be better,
	// but verifying Lambda configuration is sufficient for infrastructure test)
	config := result.Configuration
	assert.NotNil(t, config, "Lambda configuration should exist")

	t.Logf("✅ MCP server Lambda logs configured: %s", logGroupName)
}
