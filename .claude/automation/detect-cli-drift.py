#!/usr/bin/env python3
"""
Automated CLI/Justfile Drift Detection Script

Purpose: Detect synchronization drift between dr CLI commands and Justfile recipes
Usage: python .claude/automation/detect-cli-drift.py
Exit Codes:
    0 - No drift detected (synchronized)
    1 - Drift detected
    2 - Script error (missing dependencies, invalid paths)

Integration:
    - CI/CD: Add to GitHub Actions to block PRs with drift
    - Pre-commit: Add as git hook to verify before commit
    - Monthly Review: Run via /evolve cli command

See: .claude/processes/cli-justfile-maintenance.md
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import re


class DriftDetector:
    """Detect drift between dr CLI commands and Justfile recipes."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.dr_cli_path = repo_root / "dr_cli" / "commands"
        self.justfile_path = repo_root / "justfile"
        self.modules_path = repo_root / "modules"

    def get_dr_cli_commands(self) -> Set[str]:
        """Extract all dr CLI commands from Click decorators."""
        commands = set()

        if not self.dr_cli_path.exists():
            print(f"❌ ERROR: dr CLI path not found: {self.dr_cli_path}", file=sys.stderr)
            sys.exit(2)

        for py_file in self.dr_cli_path.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            content = py_file.read_text()

            # Match @click.command() or @click.command('name')
            # Captures: @click.command() def command_name():
            #           @click.command('command-name')
            for match in re.finditer(
                r"@click\.command\((.*?)\)\s*\ndef\s+(\w+)\(",
                content,
                re.DOTALL
            ):
                decorator_args = match.group(1).strip()
                function_name = match.group(2)

                # If decorator has explicit name, use it
                if decorator_args and "'" in decorator_args:
                    command_name = re.search(r"'([^']+)'", decorator_args).group(1)
                else:
                    # Convert function_name to kebab-case
                    command_name = function_name.replace("_", "-")

                commands.add(command_name)

        return commands

    def get_justfile_recipes(self) -> Set[str]:
        """Extract all Justfile recipes (excluding module recipes)."""
        recipes = set()

        if not self.justfile_path.exists():
            print(f"❌ ERROR: Justfile not found: {self.justfile_path}", file=sys.stderr)
            sys.exit(2)

        content = self.justfile_path.read_text()

        # Match recipe definitions: <name>: (at start of line, no indentation)
        # Exclude:
        #   - Comments (lines starting with #)
        #   - Variable assignments (lines with := or =)
        #   - Module imports (mod aurora, import)
        for line in content.splitlines():
            # Skip comments, blank lines, variables, imports
            if (
                line.strip().startswith("#")
                or not line.strip()
                or ":=" in line
                or "=" in line
                or line.strip().startswith("mod ")
                or line.strip().startswith("import ")
            ):
                continue

            # Match recipe definition: <name>:
            match = re.match(r"^([a-z0-9_-]+):", line)
            if match:
                recipe_name = match.group(1)
                recipes.add(recipe_name)

        return recipes

    def get_justfile_module_recipes(self) -> Dict[str, Set[str]]:
        """Extract recipes from Justfile modules."""
        module_recipes = {}

        if not self.modules_path.exists():
            return module_recipes

        for just_file in self.modules_path.glob("*.just"):
            module_name = just_file.stem  # e.g., 'aurora' from 'aurora.just'
            recipes = set()

            content = just_file.read_text()

            # Same pattern as main Justfile
            for line in content.splitlines():
                if (
                    line.strip().startswith("#")
                    or not line.strip()
                    or ":=" in line
                    or "=" in line
                ):
                    continue

                match = re.match(r"^([a-z0-9_-]+):", line)
                if match:
                    recipe_name = match.group(1)
                    recipes.add(recipe_name)

            if recipes:
                module_recipes[module_name] = recipes

        return module_recipes

    def analyze_drift(
        self,
        dr_commands: Set[str],
        justfile_recipes: Set[str],
        module_recipes: Dict[str, Set[str]]
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Analyze drift between dr CLI and Justfile.

        Returns:
            Tuple of (commands_without_recipes, recipes_without_commands, notes)
        """
        # Commands without Justfile recipes
        commands_without_recipes = sorted(dr_commands - justfile_recipes)

        # Justfile recipes without dr commands
        # (Exclude module recipes - they may not have dr equivalents)
        all_module_recipe_names = set()
        for recipes in module_recipes.values():
            all_module_recipe_names.update(recipes)

        recipes_without_commands = sorted(
            (justfile_recipes - dr_commands) - all_module_recipe_names
        )

        # Notes on module recipes
        notes = []
        for module, recipes in module_recipes.items():
            notes.append(f"📦 Module '{module}': {len(recipes)} recipes (not checked for dr equivalents)")

        return commands_without_recipes, recipes_without_commands, notes

    def detect(self) -> int:
        """
        Run drift detection.

        Returns:
            0 if synchronized, 1 if drift detected, 2 if error
        """
        print("🔍 CLI/Justfile Drift Detection")
        print("=" * 60)
        print()

        # Extract commands and recipes
        try:
            dr_commands = self.get_dr_cli_commands()
            justfile_recipes = self.get_justfile_recipes()
            module_recipes = self.get_justfile_module_recipes()
        except Exception as e:
            print(f"❌ ERROR: Failed to extract commands/recipes: {e}", file=sys.stderr)
            return 2

        print(f"📊 Found:")
        print(f"   - dr CLI commands: {len(dr_commands)}")
        print(f"   - Justfile recipes: {len(justfile_recipes)}")
        for module, recipes in module_recipes.items():
            print(f"   - Module '{module}': {len(recipes)} recipes")
        print()

        # Analyze drift
        commands_without_recipes, recipes_without_commands, notes = self.analyze_drift(
            dr_commands, justfile_recipes, module_recipes
        )

        # Report findings
        drift_detected = False

        if commands_without_recipes:
            drift_detected = True
            print(f"❌ Commands without Justfile recipes: {len(commands_without_recipes)}")
            for cmd in commands_without_recipes:
                print(f"   - dr <group> {cmd}")
            print()
            print("   💡 Fix: Add Justfile recipe OR document as 'programmatic use only'")
            print("   See: .claude/checklists/adding-cli-command.md")
            print()

        if recipes_without_commands:
            drift_detected = True
            print(f"❌ Justfile recipes without dr commands: {len(recipes_without_commands)}")
            for recipe in recipes_without_commands:
                print(f"   - just {recipe}")
            print()
            print("   💡 Fix: Create dr CLI command OR document as 'Justfile-only'")
            print("   See: .claude/checklists/cli-sync-verification.md")
            print()

        # Notes
        if notes:
            for note in notes:
                print(note)
            print()

        # Summary
        print("=" * 60)
        if drift_detected:
            print("❌ DRIFT DETECTED")
            print()
            print("Next steps:")
            print("1. Review drift items above")
            print("2. Follow fix guidance in checklists")
            print("3. Re-run this script to verify fixes")
            print()
            print("See: .claude/processes/cli-justfile-maintenance.md")
            return 1
        else:
            print("✅ SYNCHRONIZED")
            print()
            print("All dr CLI commands have Justfile recipes (or documented as exceptions).")
            print("All Justfile recipes have dr CLI commands (or documented as exceptions).")
            return 0


def main():
    """Main entry point."""
    # Determine repository root (script is in .claude/automation/)
    script_path = Path(__file__).resolve()
    repo_root = script_path.parent.parent.parent

    detector = DriftDetector(repo_root)
    exit_code = detector.detect()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
