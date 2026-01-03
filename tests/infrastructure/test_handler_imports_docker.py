"""Docker-based Lambda handler import tests.

This test layer validates Lambda handlers work in ACTUAL Lambda runtime environment,
not just in local development environment. Tests catch phase boundary violations
(Development → Lambda Runtime) BEFORE deployment.

Background:
-----------
Dec 2025: LINE bot 7-day outage - ImportError in production, tests passed locally
Jan 2026: query_tool_handler import error blocked deployment

Root cause: Local import tests passed, but Lambda container imports failed.

Why Docker testing matters:
---------------------------
1. **Runtime Fidelity**: Tests in exact Lambda Python 3.11 environment
2. **Filesystem Layout**: Validates code works in /var/task structure
3. **Phase Boundary**: Tests Development → Lambda Runtime transition
4. **Deployment Artifacts**: Tests what Lambda actually runs, not source code

Test Pattern (Principle #19 - Cross-Boundary Contract Testing):
---------------------------------------------------------------
Phase boundary: Development → Lambda Runtime

Tests that imports work when crossing from local filesystem to Lambda container.
Simulates: Fresh Lambda deployment with new code.

Integration with existing tests:
---------------------------------
- test_handler_imports.py: Tests local imports (fast, Tier 0)
- test_handler_imports_docker.py: Tests container imports (slower, Tier 1)
- Both required: Local catches syntax, Docker catches deployment issues

Runtime: ~30-60s first run (builds image), ~10s subsequent runs

Tier 1 test - runs in PR checks before merge (blocks deployment if fails)
"""

import subprocess
import pytest
from pathlib import Path


class TestHandlerImportsDocker:
    """Validate handlers import successfully in Lambda container environment."""

    # All Lambda handlers that need Docker import validation
    HANDLERS = [
        ("src.lambda_handler", "lambda_handler"),
        ("src.report_worker_handler", "handler"),
        ("src.telegram_lambda_handler", "handler"),
        ("src.scheduler.ticker_fetcher_handler", "lambda_handler"),
        ("src.scheduler.query_tool_handler", "lambda_handler"),
        ("src.scheduler.precompute_controller_handler", "lambda_handler"),
    ]

    @classmethod
    def setup_class(cls):
        """Build Docker image once for all tests."""
        print("\n" + "=" * 70)
        print("Docker Import Test - Building Lambda Container")
        print("=" * 70)

        repo_root = Path(__file__).parent.parent.parent
        dockerfile = repo_root / "Dockerfile"

        if not dockerfile.exists():
            pytest.skip("Dockerfile not found - cannot run Docker tests")

        # Build Docker image (same as production)
        print("\nBuilding Docker image from Dockerfile...")
        result = subprocess.run(
            ["docker", "build", "-t", "dr-lambda-test", "-f", str(dockerfile), str(repo_root)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.fail(f"Docker build failed:\n{result.stderr}")

        print("✓ Docker image built successfully\n")

    @pytest.mark.parametrize("module_name,handler_name", HANDLERS)
    def test_handler_imports_in_docker(self, module_name, handler_name):
        """
        Phase boundary: Development → Lambda Runtime

        GIVEN Lambda handler code deployed to container
        WHEN attempting to import in Lambda Python 3.11 environment
        THEN import should succeed and handler function should exist

        Simulates: Fresh Lambda deployment where code must work in /var/task filesystem.

        This test would have caught:
        - Dec 2025: LINE bot "cannot import handle_webhook" (7-day outage)
        - Jan 2026: query_tool_handler import error (deployment blocker)
        """
        import_test_script = f"""
import sys
try:
    # Import handler module
    mod = __import__('{module_name}', fromlist=['{handler_name}'])

    # Verify handler function exists
    if not hasattr(mod, '{handler_name}'):
        print(f'❌ Module imported but {handler_name}() function missing', file=sys.stderr)
        sys.exit(1)

    # Verify handler is callable
    handler_func = getattr(mod, '{handler_name}')
    if not callable(handler_func):
        print(f'❌ {handler_name} exists but is not callable', file=sys.stderr)
        sys.exit(1)

    print(f'✓ Successfully imported {module_name}.{handler_name}()', file=sys.stderr)
    sys.exit(0)

except ImportError as e:
    print(f'❌ Import failed: {{e}}', file=sys.stderr)
    print(f'   Module: {module_name}', file=sys.stderr)
    print(f'   Handler: {handler_name}', file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f'❌ Unexpected error: {{e}}', file=sys.stderr)
    sys.exit(1)
"""

        # Run import test inside Lambda container
        result = subprocess.run(
            ["docker", "run", "--rm", "--entrypoint", "python3", "dr-lambda-test", "-c", import_test_script],
            capture_output=True,
            text=True,
        )

        # Assert import succeeded
        assert result.returncode == 0, (
            f"Docker import test failed for {module_name}.{handler_name}\n"
            f"Exit code: {result.returncode}\n"
            f"Stdout: {result.stdout}\n"
            f"Stderr: {result.stderr}\n"
            f"\n"
            f"This failure indicates a phase boundary violation:\n"
            f"- Code works in development environment\n"
            f"- Code fails in Lambda container environment\n"
            f"\n"
            f"Common causes:\n"
            f"- Missing file in COPY directive (Dockerfile)\n"
            f"- Import path assumes local structure (not /var/task)\n"
            f"- Dependency missing from requirements.txt\n"
            f"- Module __init__.py missing\n"
            f"\n"
            f"To debug:\n"
            f"1. Check Dockerfile COPY directives include this handler\n"
            f"2. Verify import paths are relative to /var/task\n"
            f"3. Run: docker run -it --entrypoint bash dr-lambda-test\n"
            f"4. Inside container: python3 -c \"import {module_name}\"\n"
        )

    def test_all_handlers_have_validation_functions(self):
        """
        GIVEN all Lambda handlers
        WHEN checking for startup validation
        THEN handlers should validate required config at startup

        Integrates with Principle #1 (Defensive Programming) and #15 (Infrastructure-Application Contract).

        This test ensures handlers fail fast when environment variables missing,
        preventing silent failures in production.
        """
        handlers_with_validation = [
            "src.report_worker_handler",
            "src.scheduler.precompute_controller_handler",
        ]

        for module_name in handlers_with_validation:
            validation_test_script = f"""
import sys
try:
    mod = __import__('{module_name}', fromlist=['_validate_required_config'])

    if not hasattr(mod, '_validate_required_config'):
        print(f'❌ {module_name} missing _validate_required_config()', file=sys.stderr)
        sys.exit(1)

    validate_func = getattr(mod, '_validate_required_config')
    if not callable(validate_func):
        print(f'❌ _validate_required_config exists but not callable', file=sys.stderr)
        sys.exit(1)

    print(f'✓ {module_name} has _validate_required_config()', file=sys.stderr)
    sys.exit(0)

except ImportError as e:
    print(f'❌ Import failed: {{e}}', file=sys.stderr)
    sys.exit(1)
"""

            result = subprocess.run(
                ["docker", "run", "--rm", "--entrypoint", "python3", "dr-lambda-test", "-c", validation_test_script],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0, (
                f"Validation function check failed for {module_name}\n"
                f"Stderr: {result.stderr}\n"
                f"\n"
                f"Handler should have _validate_required_config() function that:\n"
                f"- Checks required environment variables at startup\n"
                f"- Raises RuntimeError if configuration missing\n"
                f"- Is called FIRST in lambda_handler() or handler()\n"
                f"\n"
                f"See Principle #1 (Defensive Programming) and #15 (Infrastructure-Application Contract)\n"
            )

    def test_docker_image_has_all_handler_files(self):
        """
        GIVEN Dockerfile COPY directives
        WHEN checking container filesystem
        THEN all handler files should exist in /var/task

        This test validates Dockerfile includes all handlers in COPY directives.
        Missing COPY = import error in Lambda.
        """
        required_files = [
            "/var/task/lambda_handler.py",
            "/var/task/report_worker_handler.py",
            "/var/task/telegram_lambda_handler.py",
            "/var/task/migration_handler.py",
            "/var/task/src/scheduler/query_tool_handler.py",
            "/var/task/src/scheduler/ticker_fetcher_handler.py",
            "/var/task/src/scheduler/precompute_controller_handler.py",
        ]

        for file_path in required_files:
            check_script = f"""
import os
import sys

if not os.path.exists('{file_path}'):
    print(f'❌ File missing: {file_path}', file=sys.stderr)
    sys.exit(1)

if os.path.getsize('{file_path}') == 0:
    print(f'❌ File empty: {file_path}', file=sys.stderr)
    sys.exit(1)

print(f'✓ File exists: {file_path}', file=sys.stderr)
sys.exit(0)
"""

            result = subprocess.run(
                ["docker", "run", "--rm", "--entrypoint", "python3", "dr-lambda-test", "-c", check_script],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0, (
                f"Handler file missing in Docker container: {file_path}\n"
                f"Stderr: {result.stderr}\n"
                f"\n"
                f"Fix: Update Dockerfile COPY directive to include this file\n"
                f"Example: COPY {file_path.replace('/var/task/', '')} ${{LAMBDA_TASK_ROOT}}/\n"
            )


class TestDockerEnvironmentParity:
    """Validate Docker environment matches Lambda runtime expectations."""

    def test_python_version_matches_lambda(self):
        """
        GIVEN Lambda uses Python 3.11
        WHEN checking Docker container Python version
        THEN should match exactly (3.11.x)
        """
        result = subprocess.run(
            ["docker", "run", "--rm", "--entrypoint", "python3", "dr-lambda-test", "--version"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, "Failed to get Python version from container"
        assert "Python 3.11" in result.stdout, (
            f"Python version mismatch!\n"
            f"Container: {result.stdout.strip()}\n"
            f"Expected: Python 3.11.x\n"
            f"\n"
            f"Fix: Update Dockerfile FROM to use correct Lambda base image\n"
        )

    def test_working_directory_is_var_task(self):
        """
        GIVEN Lambda code runs in /var/task
        WHEN checking Docker container working directory
        THEN should be /var/task
        """
        result = subprocess.run(
            ["docker", "run", "--rm", "--entrypoint", "pwd", "dr-lambda-test"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, "Failed to get working directory"
        assert result.stdout.strip() == "/var/task", (
            f"Working directory mismatch!\n"
            f"Container: {result.stdout.strip()}\n"
            f"Expected: /var/task\n"
            f"\n"
            f"This means import paths may differ between container and Lambda\n"
        )
