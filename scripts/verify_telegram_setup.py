#!/usr/bin/env python3
"""
Verify Telegram Mini App development environment setup

Usage:
    python scripts/verify_telegram_setup.py
    dr dev verify telegram
"""

import os
import sys
import subprocess
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[0;32m'
    BLUE = '\033[0;34m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'  # No Color

def print_header(text):
    print(f"\n{Colors.BLUE}{text}{Colors.NC}")
    print("=" * 60)

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.NC}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.NC}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.NC}")

def print_info(text):
    print(f"ℹ️  {text}")

def run_command(cmd, capture=True):
    """Run shell command and return result"""
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            return result.returncode == 0, result.stdout.strip()
        else:
            result = subprocess.run(cmd, shell=True, timeout=5)
            return result.returncode == 0, ""
    except Exception as e:
        return False, str(e)

def check_docker():
    """Check if Docker is installed and running"""
    print_header("1. Docker")

    # Check Docker installed
    success, output = run_command("docker --version")
    if not success:
        print_error("Docker is not installed")
        print_info("Install from: https://docs.docker.com/get-docker/")
        return False

    version = output.split(',')[0] if output else "unknown"
    print_success(f"Docker installed ({version})")

    # Check Docker running
    success, _ = run_command("docker ps")
    if not success:
        print_error("Docker is not running")
        print_info("Start Docker Desktop or run: sudo systemctl start docker")
        return False

    print_success("Docker is running")
    return True

def check_dynamodb_local():
    """Check if DynamoDB Local container exists and is running"""
    print_header("2. DynamoDB Local")

    # Check if container exists
    success, output = run_command("docker ps -a --filter name=dynamodb-local --format '{{.Names}}'")
    if not success or 'dynamodb-local' not in output:
        print_warning("DynamoDB Local container not found")
        print_info("Run: just setup-local-db")
        return False

    print_success("DynamoDB Local container exists")

    # Check if container is running
    success, output = run_command("docker ps --filter name=dynamodb-local --format '{{.Names}}'")
    if not success or 'dynamodb-local' not in output:
        print_warning("DynamoDB Local container is stopped")
        print_info("Start it: docker start dynamodb-local")
        return False

    print_success("DynamoDB Local is running")

    # Check port 8000 is accessible
    success, _ = run_command("nc -z localhost 8000")
    if not success:
        print_warning("Port 8000 not accessible (may need to wait)")
        return False

    print_success("Port 8000 is accessible")
    return True

def check_dynamodb_tables():
    """Check if required DynamoDB tables exist"""
    print_header("3. DynamoDB Tables")

    try:
        import boto3
        from botocore.exceptions import ClientError

        dynamodb = boto3.client(
            'dynamodb',
            endpoint_url='http://localhost:8000',
            region_name='us-east-1',
            aws_access_key_id='fake',
            aws_secret_access_key='fake'
        )

        response = dynamodb.list_tables()
        tables = response.get('TableNames', [])

        required_tables = [
            'dr-daily-report-telegram-watchlist-dev',
            'dr-daily-report-telegram-cache-dev'
        ]

        all_exist = True
        for table in required_tables:
            if table in tables:
                print_success(f"Table exists: {table}")
            else:
                print_error(f"Table missing: {table}")
                all_exist = False

        if not all_exist:
            print_info("Create tables: python scripts/create_local_dynamodb_tables.py")
            return False

        return True

    except ImportError:
        print_warning("boto3 not installed")
        print_info("Install: pip install boto3")
        return False
    except Exception as e:
        print_error(f"Cannot connect to DynamoDB Local: {e}")
        return False

def check_ports():
    """Check if required ports are available"""
    print_header("4. Port Availability")

    # Port 8000 should be used by DynamoDB (checked above)
    # Port 8001 should be free for FastAPI

    success, _ = run_command("lsof -i :8001 || true")
    # If lsof command succeeds and finds something, port is in use
    # We need to check the output to see if anything is using it
    success, output = run_command("netstat -tuln 2>/dev/null | grep ':8001 ' || ss -tuln 2>/dev/null | grep ':8001 ' || echo 'free'")

    if 'free' in output or not output:
        print_success("Port 8001 available for FastAPI")
    else:
        print_warning("Port 8001 may be in use")
        print_info("If FastAPI fails to start, kill the process using port 8001")

    return True

def check_environment_vars():
    """Check if required environment variables are set"""
    print_header("5. Environment Variables")

    use_doppler = os.getenv('USE_DOPPLER') == 'true'

    if use_doppler:
        print_info("Using Doppler for secrets management")

    # Check USE_LOCAL_DYNAMODB
    local_db = os.getenv('USE_LOCAL_DYNAMODB')
    if local_db == 'true':
        print_success("USE_LOCAL_DYNAMODB=true")
    else:
        print_warning("USE_LOCAL_DYNAMODB not set")
        print_info("Set in script: ./scripts/start_local_api.sh")

    # Check WATCHLIST_TABLE_NAME
    table_name = os.getenv('WATCHLIST_TABLE_NAME')
    if table_name:
        print_success(f"WATCHLIST_TABLE_NAME={table_name}")
    else:
        print_warning("WATCHLIST_TABLE_NAME not set")

    # Check API keys (only if using Doppler)
    if use_doppler:
        if os.getenv('OPENROUTER_API_KEY'):
            print_success("OPENROUTER_API_KEY is set")
        else:
            print_warning("OPENROUTER_API_KEY not found")

        if os.getenv('LANGSMITH_API_KEY'):
            print_success("LANGSMITH_API_KEY is set")
        else:
            print_info("LANGSMITH_API_KEY not set (optional)")

    return True

def check_python_dependencies():
    """Check if required Python packages are installed"""
    print_header("6. Python Dependencies")

    required_packages = [
        'fastapi',
        'uvicorn',
        'boto3',
        'pydantic',
        'yfinance'
    ]

    all_installed = True
    for package in required_packages:
        try:
            __import__(package)
            print_success(f"{package} installed")
        except ImportError:
            print_error(f"{package} not installed")
            all_installed = False

    if not all_installed:
        print_info("Install dependencies: pip install -r requirements.txt")
        return False

    return True

def check_project_structure():
    """Check if project structure is correct"""
    print_header("7. Project Structure")

    required_paths = [
        'src/api/app.py',
        'src/api/watchlist_service.py',
        'src/api/ticker_service.py',
        'scripts/start_local_api.sh',
        'scripts/test_watchlist.sh',
        'terraform/dynamodb.tf'
    ]

    all_exist = True
    for path in required_paths:
        if Path(path).exists():
            print_success(f"{path}")
        else:
            print_error(f"{path} not found")
            all_exist = False

    return all_exist

def print_summary(checks):
    """Print summary and next steps"""
    print_header("Summary")

    passed = sum(checks.values())
    total = len(checks)

    print(f"\n✅ Passed: {passed}/{total} checks")

    if passed == total:
        print(f"\n{Colors.GREEN}🎉 Telegram Mini App environment is ready!{Colors.NC}\n")
        print("Next steps:")
        print("  1. Start API server:")
        print("     just dev-api")
        print("     (or: ./scripts/start_local_api.sh)")
        print()
        print("  2. In another terminal, test watchlist:")
        print("     just test-watchlist")
        print("     (or: ./scripts/test_watchlist.sh)")
        print()
    else:
        print(f"\n{Colors.YELLOW}⚠️  Some checks failed. Please fix the issues above.{Colors.NC}\n")
        print("Quick setup:")
        print("  just setup-local-db    # Setup DynamoDB Local")
        print("  just dev-api           # Start API server")
        print("  just test-watchlist    # Test endpoints")
        print()

def main():
    """Main verification flow"""
    print(f"\n{Colors.BLUE}🔍 Verifying Telegram Mini App Setup{Colors.NC}")
    print("=" * 60)

    checks = {
        'docker': False,
        'dynamodb_local': False,
        'dynamodb_tables': False,
        'ports': False,
        'environment': False,
        'dependencies': False,
        'structure': False
    }

    # Run all checks
    checks['docker'] = check_docker()

    if checks['docker']:
        checks['dynamodb_local'] = check_dynamodb_local()
        if checks['dynamodb_local']:
            checks['dynamodb_tables'] = check_dynamodb_tables()

    checks['ports'] = check_ports()
    checks['environment'] = check_environment_vars()
    checks['dependencies'] = check_python_dependencies()
    checks['structure'] = check_project_structure()

    # Print summary
    print_summary(checks)

    # Exit with appropriate code
    if all(checks.values()):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
