#!/usr/bin/env python3
"""Comprehensive MCP server connectivity validation script."""
import json
import subprocess
import sys
import os
import time
from pathlib import Path

def check_command(cmd):
    try:
        result = subprocess.run(["which", cmd], capture_output=True, text=True, timeout=2)
        return result.returncode == 0, result.stdout.strip() if result.returncode == 0 else ""
    except:
        return False, ""

def test_doppler_config(project=None, config=None):
    cmd = ["doppler", "run"]
    if project:
        cmd.extend(["--project", project])
    if config:
        cmd.extend(["--config", config])
    cmd.extend(["--", "printenv", "DOPPLER_PROJECT", "DOPPLER_CONFIG"])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def test_mcp_server(server_name, command, args, timeout=15):
    full_cmd = [command] + args
    try:
        process = subprocess.Popen(full_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE, text=True, env=os.environ.copy())
        init_request = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                       "params": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                                 "clientInfo": {"name": "test", "version": "1.0"}}}
        request_json = json.dumps(init_request) + "\n"
        process.stdin.write(request_json)
        process.stdin.flush()
        time.sleep(3)
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=2)
        stdout, stderr = process.communicate()
        for line in stdout.split('\n'):
            if line.strip():
                try:
                    resp = json.loads(line)
                    if "result" in resp:
                        return True, json.dumps(resp, indent=2), stderr[:300]
                    if "error" in resp:
                        return False, json.dumps(resp, indent=2), stderr[:300]
                except:
                    pass
        return False, stdout[:300], stderr[:300]
    except Exception as e:
        return False, "", str(e)

def main():
    print("=" * 70)
    print("🔍 MCP Server Connectivity Validation")
    print("=" * 70)
    print()
    
    config_path = Path(".cursor/mcp.json")
    if not config_path.exists():
        print(f"❌ MCP config not found")
        return 1
    
    with open(config_path) as f:
        config = json.load(f)
    
    print("✅ MCP config loaded\n")
    
    print("📋 Step 1: Checking commands...")
    for cmd in ["doppler", "uvx", "npx"]:
        avail, path = check_command(cmd)
        print(f"  {'✅' if avail else '❌'} {cmd}" + (f" ({path})" if avail else ""))
    
    print("\n📋 Step 2: Testing Doppler configs...")
    for cfg, proj in [("dev", None), ("dev_personal", "rag-chatbot-worktree")]:
        ok, _, err = test_doppler_config(project=proj, config=cfg)
        print(f"  {'✅' if ok else '❌'} {cfg}" + (f" (project: {proj})" if proj else ""))
        if not ok and err:
            print(f"     Error: {err[:100]}")
    
    print("\n📋 Step 3: Testing MCP servers...\n")
    results = {}
    for name, srv in config.get("mcpServers", {}).items():
        print(f"🔧 {name}...")
        cmd = srv.get("command", "")
        args = srv.get("args", [])
        ok, stdout, stderr = test_mcp_server(name, cmd, args)
        print(f"  {'✅' if ok else '❌'} {'Success' if ok else 'Failed'}")
        if not ok:
            print(f"     Error: {(stderr or stdout)[:150]}")
        results[name] = ok
    
    print("\n" + "=" * 70)
    print("📋 SUMMARY")
    print("=" * 70)
    for name, ok in results.items():
        print(f"{'✅' if ok else '❌'} {name}")
    
    return 0 if all(results.values()) else 1

if __name__ == "__main__":
    sys.exit(main())
