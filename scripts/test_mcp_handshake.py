#!/usr/bin/env python3
"""
Test script for AWS MCP server handshake.
This script tests the MCP protocol initialization handshake.
"""

import json
import sys
import subprocess
import os
import time

def test_mcp_handshake():
    """Test MCP server handshake by sending initialize request."""
    
    print("🧪 Testing AWS MCP Server Handshake...")
    print()
    
    # Check if uv is available
    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ uv is installed: {result.stdout.strip()}")
        else:
            print("❌ uv is not installed. Run: just setup-mcp")
            return False
    except FileNotFoundError:
        print("❌ uv is not installed. Run: just setup-mcp")
        return False
    except Exception as e:
        print(f"⚠️  Could not check uv: {e}")
    
    # Check AWS credentials
    try:
        result = subprocess.run(["aws", "sts", "get-caller-identity"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            identity = json.loads(result.stdout)
            print("✅ AWS credentials configured")
            print(f"   Account: {identity.get('Account', 'N/A')}")
            print(f"   User ARN: {identity.get('Arn', 'N/A')}")
        else:
            print("⚠️  AWS credentials not found. MCP server may still work for some operations.")
            print("   Configure with: aws configure")
    except FileNotFoundError:
        print("⚠️  AWS CLI not found. MCP server may still work.")
    except Exception as e:
        print(f"⚠️  Could not check AWS credentials: {e}")
    
    print()
    print("📡 Starting MCP server test...")
    
    # Set environment variables
    env = os.environ.copy()
    env["AWS_REGION"] = "ap-southeast-1"
    env["FASTMCP_LOG_LEVEL"] = "ERROR"
    env["UV_HTTP_TIMEOUT"] = "60"
    
    # MCP Initialize request (JSON-RPC 2.0)
    initialize_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "mcp-handshake-test",
                "version": "1.0.0"
            }
        }
    }
    
    # Start MCP server process
    print("Starting AWS MCP server...")
    try:
        process = subprocess.Popen(
            ["uvx", "awslabs.core-mcp-server@latest"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env
        )
        
        # Send initialize request
        print("Sending initialize request...")
        request_json = json.dumps(initialize_request) + "\n"
        process.stdin.write(request_json)
        process.stdin.flush()
        
        # Wait for response (with timeout)
        print("Waiting for response (this may take a while on first run as dependencies download)...")
        process.stdin.close()
        
        # Read response with timeout
        try:
            stdout, stderr = process.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            print("❌ Timeout waiting for server response (60s)")
            process.kill()
            return False
        
        if stdout:
            print("\n✅ Server Response Received:")
            print("-" * 60)
            
            # Try to parse response
            try:
                for line in stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            response = json.loads(line)
                            if response.get("result"):
                                print("\n✅ Handshake successful!")
                                result = response.get("result", {})
                                print(f"   Protocol Version: {result.get('protocolVersion', 'N/A')}")
                                server_info = result.get("serverInfo", {})
                                print(f"   Server Name: {server_info.get('name', 'N/A')}")
                                print(f"   Server Version: {server_info.get('version', 'N/A')}")
                                
                                # Check for tools capability
                                capabilities = result.get("capabilities", {})
                                tools_cap = capabilities.get("tools", {})
                                if tools_cap:
                                    print(f"   Tools Supported: Yes")
                                    if "listChanged" in tools_cap:
                                        print(f"   Tools List Changed: {tools_cap.get('listChanged', False)}")
                                
                                print()
                                print("✅ MCP Handshake Test PASSED!")
                                print()
                                print("📋 Next steps:")
                                print("   1. Restart Cursor IDE")
                                print("   2. Ask Cursor: 'What AWS MCP tools are available?'")
                                print("   3. Test: 'List all Lambda functions in ap-southeast-1'")
                                
                                process.terminate()
                                return True
                            elif response.get("error"):
                                print(f"\n❌ Server returned error:")
                                print(f"   Code: {response['error'].get('code', 'N/A')}")
                                print(f"   Message: {response['error'].get('message', 'N/A')}")
                                process.terminate()
                                return False
                        except json.JSONDecodeError:
                            # Not JSON, might be progress output
                            if "Preparing" in line or "Downloading" in line or "Installing" in line:
                                print(f"   {line}")
                            continue
                
                # If we got here, we didn't find a valid response
                print("\n⚠️  Received response but could not parse valid MCP response")
                print("   Raw output:")
                print(stdout[:500])  # First 500 chars
                process.terminate()
                return False
                
            except Exception as e:
                print(f"\n❌ Error parsing response: {e}")
                print("   Raw output:")
                print(stdout[:500])
                process.terminate()
                return False
        
        if stderr:
            print("\n⚠️  Server stderr:")
            print(stderr[:500])
        
        process.terminate()
        return False
        
    except FileNotFoundError:
        print("❌ uvx command not found. Make sure uv is installed and in PATH.")
        print("   Run: just setup-mcp")
        return False
    except Exception as e:
        print(f"\n❌ Error running MCP server: {e}")
        return False

if __name__ == "__main__":
    success = test_mcp_handshake()
    sys.exit(0 if success else 1)

