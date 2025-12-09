#!/usr/bin/env python3
"""
Test script for MCP servers configured with Doppler.
Verifies that Doppler injection works correctly for all configured MCP servers.
"""

import json
import subprocess
import os
import sys
from pathlib import Path

def check_doppler():
    """Check if Doppler is installed and configured."""
    try:
        result = subprocess.run(
            ["doppler", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ Doppler installed: {version}")
            return True
        else:
            print("❌ Doppler not found")
            return False
    except FileNotFoundError:
        print("❌ Doppler not installed. Install from: https://docs.doppler.com/docs/install-cli")
        return False
    except Exception as e:
        print(f"⚠️  Error checking Doppler: {e}")
        return False

def check_doppler_config():
    """Check if Doppler is configured for dev environment."""
    try:
        result = subprocess.run(
            ["doppler", "secrets", "--config", "dev", "--only-names"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            secrets = [s.strip() for s in result.stdout.strip().split('\n') if s.strip()]
            print(f"✅ Doppler config 'dev' accessible ({len(secrets)} secrets found)")
            return True
        else:
            print(f"⚠️  Doppler config 'dev' may not be set up")
            print(f"   Run: doppler setup --config dev")
            return False
    except Exception as e:
        print(f"⚠️  Error checking Doppler config: {e}")
        return False

def check_github_token():
    """Check if GitHub token exists in Doppler."""
    try:
        result = subprocess.run(
            ["doppler", "secrets", "get", "GITHUB_PERSONAL_ACCESS_TOKEN", "--config", "dev", "--plain"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            token = result.stdout.strip()
            if len(token) > 10:  # Basic validation
                print(f"✅ GitHub token found in Doppler (length: {len(token)})")
                return True
            else:
                print("⚠️  GitHub token exists but appears invalid")
                return False
        else:
            print("⚠️  GitHub token not found in Doppler")
            print("   Add it with: doppler secrets set GITHUB_PERSONAL_ACCESS_TOKEN=your_token --config dev")
            return False
    except Exception as e:
        print(f"⚠️  Error checking GitHub token: {e}")
        return False

def load_mcp_config():
    """Load MCP configuration from .cursor/mcp.json."""
    config_path = Path(".cursor/mcp.json")
    if not config_path.exists():
        print(f"❌ MCP config not found: {config_path}")
        return None
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"✅ MCP config loaded from {config_path}")
        return config
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in MCP config: {e}")
        return None
    except Exception as e:
        print(f"❌ Error loading MCP config: {e}")
        return None

def verify_doppler_pattern(config):
    """Verify all MCP servers use Doppler pattern."""
    servers = config.get("mcpServers", {})
    if not servers:
        print("❌ No MCP servers configured")
        return False
    
    print(f"\n📦 Checking {len(servers)} MCP server(s)...")
    print()
    
    all_using_doppler = True
    for server_name, server_config in servers.items():
        command = server_config.get("command", "")
        args = server_config.get("args", [])
        
        print(f"  {server_name}:")
        print(f"    Command: {command}")
        
        if command == "doppler":
            # Check if args follow Doppler pattern
            if "--config" in args and "dev" in args and "--" in args:
                print(f"    ✅ Using Doppler with 'dev' config")
            else:
                print(f"    ⚠️  Using Doppler but missing '--config dev' or '--' separator")
                all_using_doppler = False
        else:
            print(f"    ⚠️  Not using Doppler (should use Doppler per .cursor/principles.md)")
            all_using_doppler = False
        
        # Extract actual command
        try:
            dash_index = args.index("--")
            actual_cmd = args[dash_index + 1:]
            print(f"    Actual command: {' '.join(actual_cmd[:2])}")
        except ValueError:
            print(f"    ⚠️  Missing '--' separator in args")
    
    return all_using_doppler

def test_doppler_env_injection():
    """Test that Doppler can inject environment variables."""
    print("\n🧪 Testing Doppler environment variable injection...")
    
    # Test with a simple command
    test_env_var = "MCP_TEST_VAR"
    test_value = "test_value_12345"
    
    try:
        # Set a test secret
        subprocess.run(
            ["doppler", "secrets", "set", f"{test_env_var}={test_value}", "--config", "dev"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # Test reading it back via doppler run
        result = subprocess.run(
            ["doppler", "run", "--config", "dev", "--", "printenv", test_env_var],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and test_value in result.stdout:
            print(f"✅ Doppler environment injection works")
            
            # Clean up test secret
            subprocess.run(
                ["doppler", "secrets", "delete", test_env_var, "--config", "dev", "--yes"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return True
        else:
            print(f"⚠️  Doppler environment injection test failed")
            return False
    except Exception as e:
        print(f"⚠️  Error testing Doppler injection: {e}")
        return False

def main():
    """Run all verification checks."""
    print("=" * 70)
    print("🔍 MCP Configuration Verification (Doppler-based)")
    print("=" * 70)
    print()
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    checks = {
        "Doppler installed": check_doppler(),
        "Doppler config 'dev'": check_doppler_config(),
        "GitHub token in Doppler": check_github_token(),
    }
    
    config = load_mcp_config()
    if config:
        checks["MCP config uses Doppler"] = verify_doppler_pattern(config)
        checks["Doppler env injection"] = test_doppler_env_injection()
    
    print()
    print("=" * 70)
    print("📋 SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for check_name, passed in checks.items():
        status = "✅" if passed else "⚠️"
        print(f"{status} {check_name}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("✅ All checks passed! MCP configuration is ready.")
        print()
        print("🚀 Next steps:")
        print("   1. Restart Cursor IDE")
        print("   2. Ask: 'What MCP tools are available?'")
    else:
        print("⚠️  Some checks failed. Fix issues above before using MCP servers.")
        print()
        if not checks.get("GitHub token in Doppler"):
            print("💡 To add GitHub token:")
            print("   doppler secrets set GITHUB_PERSONAL_ACCESS_TOKEN=your_token --config dev")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
