#!/usr/bin/env python3
"""
Validate MCP servers as Cursor IDE would use them.
Tests wrapper scripts with proper MCP protocol initialization.
"""

import json
import subprocess
import sys
import os
import time
import select
from pathlib import Path

def test_mcp_server_wrapper(wrapper_script, server_name, timeout=10):
    """Test MCP server wrapper script with proper MCP protocol."""
    print(f"🔧 Testing {server_name} via wrapper script...")
    print(f"   Wrapper: {wrapper_script}")
    
    if not os.path.exists(wrapper_script):
        print(f"   ❌ Wrapper script not found: {wrapper_script}")
        return False, "Wrapper script not found", ""
    
    if not os.access(wrapper_script, os.X_OK):
        print(f"   ❌ Wrapper script not executable: {wrapper_script}")
        return False, "Wrapper script not executable", ""
    
    try:
        # Start the wrapper script
        process = subprocess.Popen(
            [wrapper_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy(),
            bufsize=0  # Unbuffered
        )
        
        # Send MCP initialize request (as Cursor would)
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "cursor-ide",
                    "version": "1.0.0"
                }
            }
        }
        
        request_json = json.dumps(init_request) + "\n"
        print(f"   Sending MCP initialize request...")
        
        process.stdin.write(request_json)
        process.stdin.flush()
        
        # Wait for response with timeout
        start_time = time.time()
        responses = []
        
        while time.time() - start_time < timeout:
            if process.poll() is not None:
                # Process exited
                stdout, stderr = process.communicate()
                if process.returncode != 0:
                    print(f"   ❌ Process exited with code {process.returncode}")
                    return False, stdout[:500], stderr[:500]
                break
            
            # Try to read from stdout (non-blocking)
            if os.name != 'nt':
                ready, _, _ = select.select([process.stdout], [], [], 0.1)
                if ready:
                    line = process.stdout.readline()
                    if line:
                        line = line.strip()
                        responses.append(line)
                        print(f"   Received: {line[:100]}...")
                        
                        # Check if it's a valid JSON response
                        try:
                            response = json.loads(line)
                            if "result" in response:
                                print(f"   ✅ Got valid MCP response!")
                                process.terminate()
                                process.wait(timeout=2)
                                return True, json.dumps(response, indent=2), ""
                            elif "error" in response:
                                print(f"   ❌ Got MCP error response")
                                error_msg = json.dumps(response, indent=2)
                                process.terminate()
                                process.wait(timeout=2)
                                return False, error_msg, ""
                        except json.JSONDecodeError:
                            # Not JSON, might be progress output
                            if any(keyword in line.lower() for keyword in ["installing", "downloading", "preparing"]):
                                print(f"   📦 {line[:80]}")
                            continue
            
            time.sleep(0.1)
        
        # If process still running, terminate it
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
        
        stdout, stderr = process.communicate()
        
        # Check all responses for valid JSON
        for line in responses:
            try:
                response = json.loads(line)
                if "result" in response:
                    return True, json.dumps(response, indent=2), stderr[:300]
                if "error" in response:
                    return False, json.dumps(response, indent=2), stderr[:300]
            except json.JSONDecodeError:
                pass
        
        # Check stdout for JSON responses
        for line in stdout.split('\n'):
            if line.strip():
                try:
                    response = json.loads(line)
                    if "result" in response:
                        return True, json.dumps(response, indent=2), stderr[:300]
                    if "error" in response:
                        return False, json.dumps(response, indent=2), stderr[:300]
                except json.JSONDecodeError:
                    pass
        
        # If we got here, no valid response
        if stderr:
            return False, stdout[:300] if stdout else "", stderr[:300]
        return False, stdout[:300] if stdout else "", "No valid MCP response received"
        
    except Exception as e:
        return False, "", str(e)

def main():
    """Main validation function."""
    print("=" * 70)
    print("🔍 MCP Server Validation (Cursor Session Simulation)")
    print("=" * 70)
    print()
    
    # Get project root
    project_root = Path(__file__).parent.parent.absolute()
    os.chdir(project_root)
    
    # Load MCP config
    config_path = Path(".cursor/mcp.json")
    if not config_path.exists():
        print(f"❌ MCP config not found: {config_path}")
        return 1
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Error loading MCP config: {e}")
        return 1
    
    print("✅ MCP config loaded")
    print()
    
    # Test each MCP server
    print("📋 Testing MCP servers via wrapper scripts...")
    print()
    
    servers = config.get("mcpServers", {})
    if not servers:
        print("❌ No MCP servers configured")
        return 1
    
    results = {}
    for server_name, server_config in servers.items():
        command = server_config.get("command", "")
        
        if not command:
            print(f"❌ {server_name}: No command specified")
            results[server_name] = False
            continue
        
        # Check if it's a wrapper script
        if command.endswith('.sh'):
            wrapper_path = Path(command)
            if not wrapper_path.is_absolute():
                wrapper_path = project_root / command
            
            success, stdout, stderr = test_mcp_server_wrapper(str(wrapper_path), server_name, timeout=15)
            
            if success:
                print(f"   ✅ {server_name} - MCP handshake successful!")
                results[server_name] = True
            else:
                print(f"   ❌ {server_name} - Failed")
                if stderr:
                    print(f"      Error: {stderr[:200]}")
                elif stdout:
                    print(f"      Output: {stdout[:200]}")
                results[server_name] = False
        else:
            print(f"⚠️  {server_name}: Not using wrapper script ({command})")
            print(f"   Consider using wrapper script for proper Doppler integration")
            results[server_name] = None
        
        print()
    
    # Summary
    print("=" * 70)
    print("📋 VALIDATION SUMMARY")
    print("=" * 70)
    print()
    
    passed = []
    failed = []
    skipped = []
    
    for server_name, result in results.items():
        if result is True:
            print(f"✅ {server_name}")
            passed.append(server_name)
        elif result is False:
            print(f"❌ {server_name}")
            failed.append(server_name)
        else:
            print(f"⚠️  {server_name} (not tested - not using wrapper)")
            skipped.append(server_name)
    
    print()
    
    if len(passed) > 0:
        print(f"✅ {len(passed)} server(s) passed: {', '.join(passed)}")
    
    if len(failed) > 0:
        print(f"❌ {len(failed)} server(s) failed: {', '.join(failed)}")
    
    if len(skipped) > 0:
        print(f"⚠️  {len(skipped)} server(s) skipped: {', '.join(skipped)}")
    
    print()
    
    if len(failed) == 0 and len(passed) > 0:
        print("✅ All tested MCP servers are working!")
        print()
        print("🚀 Next steps:")
        print("   1. Restart Cursor IDE completely")
        print("   2. In Cursor, ask: 'What MCP tools are available?'")
        print("   3. Test a specific tool: 'List my AWS Lambda functions'")
        return 0
    elif len(failed) > 0:
        print("❌ Some MCP servers failed validation")
        print()
        print("💡 Troubleshooting:")
        print("   1. Check wrapper scripts are executable: chmod +x scripts/mcp_wrapper_*.sh")
        print("   2. Test wrapper scripts manually:")
        print("      ./scripts/mcp_wrapper_github.sh")
        print("   3. Check Doppler secrets are accessible")
        print("   4. Review error messages above")
        return 1
    else:
        print("⚠️  No servers were tested")
        return 1

if __name__ == "__main__":
    sys.exit(main())
