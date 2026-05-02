#!/usr/bin/env python3
"""
DSL Validation Tests

Prevents Structurizr DSL parser errors by validating:
1. Container name uniqueness within software systems
2. Valid DSL syntax and structure
3. Reference consistency (no broken relationships)
4. Naming convention compliance

This test suite prevents errors like:
'com.structurizr.dsl.StructurizrDslParserException: A container named
'dr-daily-report-telegram-api-dev' already exists for this software system'
"""

import pytest
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass


@dataclass
class DSLContainer:
    """Represents a container definition in DSL"""
    name: str
    display_name: str
    container_type: str
    line_number: int
    full_line: str


@dataclass
class DSLValidationResult:
    """Results of DSL validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    containers: List[DSLContainer]


class StructurizrDSLValidator:
    """Validates Structurizr DSL files for common issues"""

    def __init__(self, dsl_file_path: str):
        self.dsl_file_path = Path(dsl_file_path)
        self.content = ""
        self.lines = []

    def load_dsl_file(self) -> bool:
        """Load and parse the DSL file"""
        try:
            self.content = self.dsl_file_path.read_text(encoding='utf-8')
            self.lines = self.content.splitlines()
            return True
        except Exception as e:
            pytest.fail(f"Failed to load DSL file {self.dsl_file_path}: {e}")
            return False

    def extract_containers(self) -> List[DSLContainer]:
        """Extract all container definitions from DSL"""
        # Ensure DSL file is loaded
        if not self.lines:
            self.load_dsl_file()

        containers = []

        # Pattern to match container definitions
        # Format: variable_name = container "Display Name" "Type" {
        container_pattern = r'^\s*(\w+)\s*=\s*container\s+"([^"]+)"\s+"([^"]+)"\s*\{'

        for line_num, line in enumerate(self.lines, 1):
            match = re.match(container_pattern, line)
            if match:
                variable_name, display_name, container_type = match.groups()
                containers.append(DSLContainer(
                    name=variable_name,
                    display_name=display_name,
                    container_type=container_type,
                    line_number=line_num,
                    full_line=line.strip()
                ))

        return containers

    def validate_container_uniqueness(self, containers: List[DSLContainer]) -> List[str]:
        """Validate that container names and display names are unique"""
        errors = []

        # Check variable name uniqueness
        name_counts = {}
        display_name_counts = {}

        for container in containers:
            # Check variable name duplicates
            if container.name in name_counts:
                name_counts[container.name].append(container)
            else:
                name_counts[container.name] = [container]

            # Check display name duplicates
            if container.display_name in display_name_counts:
                display_name_counts[container.display_name].append(container)
            else:
                display_name_counts[container.display_name] = [container]

        # Report variable name duplicates
        for name, instances in name_counts.items():
            if len(instances) > 1:
                lines = [str(c.line_number) for c in instances]
                errors.append(
                    f"Duplicate container variable name '{name}' found at lines: {', '.join(lines)}"
                )

        # Report display name duplicates
        for display_name, instances in display_name_counts.items():
            if len(instances) > 1:
                lines = [str(c.line_number) for c in instances]
                errors.append(
                    f"Duplicate container display name '{display_name}' found at lines: {', '.join(lines)}"
                )

        return errors

    def validate_naming_conventions(self, containers: List[DSLContainer]) -> List[str]:
        """Validate naming conventions for containers"""
        warnings = []

        for container in containers:
            # Variable names should use snake_case
            if not re.match(r'^[a-z][a-z0-9_]*$', container.name):
                warnings.append(
                    f"Line {container.line_number}: Variable name '{container.name}' "
                    f"should use snake_case convention"
                )

            # Display names should not be empty
            if not container.display_name.strip():
                warnings.append(
                    f"Line {container.line_number}: Container display name is empty"
                )

            # Container type should not be empty
            if not container.container_type.strip():
                warnings.append(
                    f"Line {container.line_number}: Container type is empty"
                )

        return warnings

    def validate_infrastructure_resource_mapping(self, containers: List[DSLContainer]) -> List[str]:
        """Validate that infrastructure resources are properly mapped"""
        errors = []

        # Group containers by type to check for proper mapping
        lambda_containers = [c for c in containers if 'lambda' in c.container_type.lower()]
        api_containers = [c for c in containers if 'api gateway' in c.container_type.lower()]

        # Check for AWS resource naming conflicts that cause the original error
        aws_resource_names = {}
        for container in containers:
            # Extract AWS resource name from display name
            aws_name = container.display_name

            if aws_name in aws_resource_names:
                # This is the exact scenario that caused the original error
                existing = aws_resource_names[aws_name]
                errors.append(
                    f"AWS resource name conflict: '{aws_name}' is used for both "
                    f"'{existing.container_type}' (line {existing.line_number}) and "
                    f"'{container.container_type}' (line {container.line_number}). "
                    f"Consider using different variable names like '{container.name}_lambda' "
                    f"and '{container.name}_gateway'"
                )
            else:
                aws_resource_names[aws_name] = container

        return errors

    def validate_relationships(self) -> List[str]:
        """Validate that all relationships reference valid containers"""
        errors = []

        # Extract container variable names
        containers = self.extract_containers()
        container_names = {c.name for c in containers}

        # Extract system names from DSL
        system_names = set()
        system_pattern = r'^\s*(\w+)\s*=\s*(?:person|softwareSystem)\s+'
        for line in self.lines:
            match = re.match(system_pattern, line)
            if match:
                system_names.add(match.group(1))

        # Pattern to match relationships
        # Format: container1 -> container2 "Description"
        # Also: systemName.containerName -> otherSystem.containerName "Description"
        relationship_pattern = r'^\s*(\w+(?:\.\w+)?)\s*->\s*(\w+(?:\.\w+)?)\s+"([^"]+)"'

        for line_num, line in enumerate(self.lines, 1):
            match = re.match(relationship_pattern, line)
            if match:
                source, target, description = match.groups()

                # Extract container name (remove system prefix if present)
                source_container = source.split('.')[-1] if '.' in source else source
                target_container = target.split('.')[-1] if '.' in target else target

                # Valid references include containers, systems, and known external entities
                valid_references = container_names | system_names | {
                    'telegramUsers', 'telegramPlatform', 'openRouter', 'yahooFinance', 'langfuse'
                }

                # Check if references are valid
                if source not in valid_references and source_container not in valid_references:
                    errors.append(f"Line {line_num}: Unknown source container '{source}' in relationship")

                if target not in valid_references and target_container not in valid_references:
                    errors.append(f"Line {line_num}: Unknown target container '{target}' in relationship")

        return errors

    def validate(self) -> DSLValidationResult:
        """Perform comprehensive DSL validation"""
        if not self.load_dsl_file():
            return DSLValidationResult(
                is_valid=False,
                errors=["Failed to load DSL file"],
                warnings=[],
                containers=[]
            )

        containers = self.extract_containers()
        errors = []
        warnings = []

        # Run all validations
        errors.extend(self.validate_container_uniqueness(containers))
        errors.extend(self.validate_infrastructure_resource_mapping(containers))
        errors.extend(self.validate_relationships())
        warnings.extend(self.validate_naming_conventions(containers))

        return DSLValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            containers=containers
        )


class TestStructurizrDSLValidation:
    """Test suite for Structurizr DSL validation"""

    @pytest.fixture
    def dsl_file_path(self):
        """Path to the main workspace DSL file"""
        return "docs/architecture/workspace.dsl"

    @pytest.fixture
    def validator(self, dsl_file_path):
        """Create validator instance"""
        return StructurizrDSLValidator(dsl_file_path)

    def test_dsl_file_exists(self, dsl_file_path):
        """Test that the DSL file exists"""
        assert Path(dsl_file_path).exists(), f"DSL file not found: {dsl_file_path}"

    def test_dsl_file_syntax_valid(self, validator):
        """Test basic DSL file syntax"""
        result = validator.validate()

        if not result.is_valid:
            error_msg = "DSL validation failed:\n"
            for error in result.errors:
                error_msg += f"  ERROR: {error}\n"
            for warning in result.warnings:
                error_msg += f"  WARNING: {warning}\n"
            pytest.fail(error_msg)

        assert result.is_valid, "DSL file should pass validation"

    def test_container_names_unique(self, validator):
        """Test that container variable names are unique (prevents the original error)"""
        containers = validator.extract_containers()

        # Check for duplicate variable names
        name_counts = {}
        for container in containers:
            if container.name in name_counts:
                name_counts[container.name].append(container)
            else:
                name_counts[container.name] = [container]

        duplicates = {name: instances for name, instances in name_counts.items() if len(instances) > 1}

        if duplicates:
            error_msg = "Found duplicate container variable names:\n"
            for name, instances in duplicates.items():
                lines = [f"line {c.line_number}" for c in instances]
                error_msg += f"  '{name}': {', '.join(lines)}\n"
                error_msg += "    This causes: 'A container named '...' already exists for this software system'\n"
            pytest.fail(error_msg)

    def test_aws_resource_name_conflicts(self, validator):
        """Test for AWS resource name conflicts that cause parser errors"""
        containers = validator.extract_containers()

        # Group by display name (AWS resource name)
        display_name_groups = {}
        for container in containers:
            if container.display_name in display_name_groups:
                display_name_groups[container.display_name].append(container)
            else:
                display_name_groups[container.display_name] = [container]

        conflicts = {name: instances for name, instances in display_name_groups.items() if len(instances) > 1}

        if conflicts:
            error_msg = "Found AWS resource name conflicts:\n"
            for aws_name, instances in conflicts.items():
                types = [f"{c.container_type} (line {c.line_number})" for c in instances]
                error_msg += f"  '{aws_name}': {', '.join(types)}\n"
                error_msg += f"    Suggested fix: Use different variable names like '{instances[0].name}_lambda', '{instances[0].name}_gateway'\n"
            pytest.fail(error_msg)

    def test_relationship_references_valid(self, validator):
        """Test that all relationships reference valid containers"""
        errors = validator.validate_relationships()

        if errors:
            error_msg = "Found invalid container references:\n"
            for error in errors:
                error_msg += f"  {error}\n"
            pytest.fail(error_msg)

    def test_container_count_reasonable(self, validator):
        """Test that we have a reasonable number of containers"""
        containers = validator.extract_containers()

        # We should have at least a few containers (Lambda functions, database, etc.)
        assert len(containers) >= 3, f"Expected at least 3 containers, found {len(containers)}"

        # But not too many (might indicate duplication issues)
        assert len(containers) <= 50, f"Found {len(containers)} containers, check for duplicates"

    def test_naming_conventions(self, validator):
        """Test that naming conventions are followed"""
        containers = validator.extract_containers()

        warnings = validator.validate_naming_conventions(containers)

        # For now, just log warnings but don't fail
        if warnings:
            print("\nNaming convention warnings:")
            for warning in warnings:
                print(f"  {warning}")

    @pytest.mark.integration
    def test_structurizr_validation_via_docker(self, dsl_file_path):
        """Test DSL validation using Structurizr CLI Docker container"""
        import subprocess

        try:
            # Run Structurizr CLI validation
            result = subprocess.run([
                "docker", "run", "--rm",
                "-v", f"{Path.cwd()}/docs/architecture:/workspace",
                "structurizr/cli",
                "validate",
                "-workspace", "/workspace/workspace.dsl"
            ], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                pytest.fail(f"Structurizr validation failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")

        except subprocess.TimeoutExpired:
            pytest.fail("Structurizr validation timed out")
        except FileNotFoundError:
            pytest.skip("Docker not available for Structurizr validation")


if __name__ == "__main__":
    # Allow running this test file directly
    validator = StructurizrDSLValidator("docs/architecture/workspace.dsl")
    result = validator.validate()

    print("DSL Validation Report")
    print("=" * 40)
    print(f"Valid: {result.is_valid}")
    print(f"Containers found: {len(result.containers)}")

    if result.errors:
        print("\nERRORS:")
        for error in result.errors:
            print(f"  ❌ {error}")

    if result.warnings:
        print("\nWARNINGS:")
        for warning in result.warnings:
            print(f"  ⚠️  {warning}")

    if result.is_valid:
        print("\n✅ DSL file is valid!")
    else:
        print(f"\n❌ DSL file has {len(result.errors)} errors")