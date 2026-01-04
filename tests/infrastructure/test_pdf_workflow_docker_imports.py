"""Docker Container Import Tests for PDF Workflow Handlers

Phase Boundary Tests: Development → Lambda Runtime

These tests verify that PDF workflow Lambda handlers can be imported successfully
in the actual Lambda container environment. This catches deployment issues that
local tests miss (file permissions, missing files, import path problems).

Evidence: Jan 2026 - Two import failures caught during PDF workflow development:
1. ImportModuleError: "No module named 'src.scheduler'"
2. PermissionError: File permissions 600 instead of 644

Related: Principle #10 (Testing Anti-Patterns - Deployment Fidelity Testing)
"""

import subprocess
import pytest


class TestPDFWorkflowDockerImports:
    """Test PDF workflow handlers import correctly in Lambda container.

    Principle #10: Test deployment artifacts (Docker images), not just source code.
    Principle #19: Test phase boundaries (Development → Lambda Runtime).
    """

    def test_get_report_list_handler_imports_in_docker(self):
        """Phase boundary: Development → Lambda Runtime

        Tests that get_report_list_handler can be imported in Lambda container.

        Simulates: Fresh Lambda deployment with new code.

        Catches:
        - Missing src/scheduler/ directory in container
        - File permission issues (600 vs 644)
        - Missing __init__.py files
        - Import path problems
        """
        import_script = "import src.scheduler.get_report_list_handler"

        result = subprocess.run(
            ["docker", "run", "--rm", "--entrypoint", "python3",
             "dr-lambda-test", "-c", import_script],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, (
            f"get_report_list_handler import failed in Lambda container.\n"
            f"This would cause production failure if deployed.\n"
            f"\n"
            f"Error:\n{result.stderr}\n"
            f"\n"
            f"Common causes:\n"
            f"- File permissions (should be 644, not 600)\n"
            f"- Missing src/scheduler/ directory in Docker image\n"
            f"- Missing __init__.py in src/scheduler/\n"
            f"- Dockerfile not copying handler files correctly"
        )

    def test_pdf_worker_handler_imports_in_docker(self):
        """Phase boundary: Development → Lambda Runtime

        Tests that pdf_worker_handler can be imported in Lambda container.

        Simulates: Fresh Lambda deployment with new code.

        Catches:
        - Missing src/pdf_worker_handler.py in container
        - File permission issues
        - Dependency import problems
        """
        import_script = "import src.pdf_worker_handler"

        result = subprocess.run(
            ["docker", "run", "--rm", "--entrypoint", "python3",
             "dr-lambda-test", "-c", import_script],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, (
            f"pdf_worker_handler import failed in Lambda container.\n"
            f"This would cause production failure if deployed.\n"
            f"\n"
            f"Error:\n{result.stderr}\n"
            f"\n"
            f"Common causes:\n"
            f"- File permissions (should be 644, not 600)\n"
            f"- Missing src/pdf_worker_handler.py in Docker image\n"
            f"- Dockerfile not copying handler files correctly"
        )

    def test_get_report_list_handler_has_lambda_handler_function(self):
        """Verify handler has correct entry point function.

        Lambda expects a function named 'lambda_handler' that accepts (event, context).
        This test verifies the function exists and has correct signature.
        """
        import_and_check = """
import src.scheduler.get_report_list_handler
import inspect

# Verify lambda_handler function exists
assert hasattr(src.scheduler.get_report_list_handler, 'lambda_handler'), \
    "Handler missing lambda_handler function"

# Verify function signature
handler = src.scheduler.get_report_list_handler.lambda_handler
sig = inspect.signature(handler)
params = list(sig.parameters.keys())

assert len(params) >= 2, \
    f"lambda_handler should accept (event, context), got {params}"

print("✅ Handler has correct lambda_handler(event, context) signature")
"""

        result = subprocess.run(
            ["docker", "run", "--rm", "--entrypoint", "python3",
             "dr-lambda-test", "-c", import_and_check],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, (
            f"get_report_list_handler missing correct lambda_handler function.\n"
            f"Error:\n{result.stderr}"
        )

    def test_pdf_worker_handler_has_handler_function(self):
        """Verify PDF worker has correct entry point function.

        PDF worker uses 'handler' as entry point (not lambda_handler).
        This matches the ImageConfig.Command in Terraform.
        """
        import_and_check = """
import src.pdf_worker_handler
import inspect

# Verify handler function exists
assert hasattr(src.pdf_worker_handler, 'handler'), \
    "PDF worker missing handler function"

# Verify function signature
handler = src.pdf_worker_handler.handler
sig = inspect.signature(handler)
params = list(sig.parameters.keys())

assert len(params) >= 2, \
    f"handler should accept (event, context), got {params}"

print("✅ PDF worker has correct handler(event, context) signature")
"""

        result = subprocess.run(
            ["docker", "run", "--rm", "--entrypoint", "python3",
             "dr-lambda-test", "-c", import_and_check],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, (
            f"pdf_worker_handler missing correct handler function.\n"
            f"Error:\n{result.stderr}"
        )

    def test_handlers_can_import_dependencies(self):
        """Verify handlers can import required dependencies.

        Tests that all dependencies (Aurora client, PrecomputeService, etc.)
        are available in the container environment.
        """
        import_dependencies = """
# Test get_report_list_handler dependencies
from src.data.aurora.precompute_service import PrecomputeService
from src.scheduler.get_report_list_handler import lambda_handler

# Test pdf_worker_handler dependencies
from src.pdf_worker_handler import handler

print("✅ All handler dependencies import successfully")
"""

        result = subprocess.run(
            ["docker", "run", "--rm", "--entrypoint", "python3",
             "dr-lambda-test", "-c", import_dependencies],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, (
            f"Handler dependencies import failed in Lambda container.\n"
            f"Error:\n{result.stderr}\n"
            f"\n"
            f"This indicates missing dependencies or import path issues."
        )


class TestDockerImageAvailability:
    """Verify Docker test image exists before running import tests."""

    def test_docker_test_image_exists(self):
        """Verify dr-lambda-test Docker image is available.

        The import tests require a Docker image tagged 'dr-lambda-test'.
        This test ensures the image was built before running imports.

        To build: docker build -t dr-lambda-test -f Dockerfile .
        """
        result = subprocess.run(
            ["docker", "images", "dr-lambda-test", "--format", "{{.Repository}}"],
            capture_output=True,
            text=True
        )

        assert "dr-lambda-test" in result.stdout, (
            "Docker test image 'dr-lambda-test' not found.\n"
            "\n"
            "Build the test image first:\n"
            "  docker build -t dr-lambda-test -f Dockerfile .\n"
            "\n"
            "This image is used to test Lambda handler imports in a container\n"
            "environment that matches AWS Lambda runtime."
        )
