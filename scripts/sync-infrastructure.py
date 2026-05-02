#!/usr/bin/env python3
"""
Infrastructure Sync Tool for Structurizr DSL
Automatically updates architecture diagrams when infrastructure changes.

This tool:
1. Monitors Terraform state for changes
2. Analyzes deployment differences
3. Updates Structurizr DSL files accordingly
4. Maintains architecture-reality alignment

Usage:
    python scripts/sync-infrastructure.py [--watch] [--force]
"""

import os
import json
import subprocess
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class InfrastructureMonitor:
    """Monitor infrastructure changes and sync with DSL"""

    def __init__(self):
        self.project_root = Path.cwd()
        self.terraform_dir = self.project_root / "terraform"
        self.architecture_dir = self.project_root / "docs" / "architecture"
        self.dsl_file = self.architecture_dir / "workspace.dsl"
        self.state_file = self.architecture_dir / ".sync_state.json"

        # Ensure directories exist
        self.architecture_dir.mkdir(parents=True, exist_ok=True)

    def get_terraform_state_hash(self) -> str:
        """Get hash of current Terraform state for change detection"""
        try:
            # Get current Terraform plan
            result = subprocess.run(
                ["terraform", "plan", "-out=/tmp/tfplan"],
                cwd=self.terraform_dir,
                capture_output=True,
                text=True,
                env={**os.environ, "TF_IN_AUTOMATION": "true"}
            )

            if result.returncode != 0:
                logger.warning(f"Terraform plan failed: {result.stderr}")
                return ""

            # Hash the plan output for change detection
            plan_content = result.stdout + result.stderr
            return hashlib.md5(plan_content.encode()).hexdigest()

        except Exception as e:
            logger.error(f"Failed to get Terraform state: {e}")
            return ""

    def get_deployed_infrastructure(self) -> Dict[str, Any]:
        """Extract current infrastructure from Terraform state"""
        try:
            # Get Terraform state
            result = subprocess.run(
                ["terraform", "show", "-json"],
                cwd=self.terraform_dir,
                capture_output=True,
                text=True,
                env={**os.environ, "TF_IN_AUTOMATION": "true"}
            )

            if result.returncode != 0:
                logger.warning(f"Terraform show failed: {result.stderr}")
                return {}

            state = json.loads(result.stdout)

            # Extract relevant resources
            infrastructure = {
                "lambdas": [],
                "databases": [],
                "api_gateways": [],
                "s3_buckets": [],
                "cloudfront": [],
                "step_functions": [],
                "last_updated": datetime.now().isoformat()
            }

            if "values" in state and "root_module" in state["values"]:
                resources = state["values"]["root_module"].get("resources", [])

                for resource in resources:
                    resource_type = resource.get("type", "")
                    resource_name = resource.get("name", "")
                    values = resource.get("values", {})

                    # Lambda functions
                    if resource_type == "aws_lambda_function":
                        infrastructure["lambdas"].append({
                            "name": values.get("function_name", resource_name),
                            "runtime": values.get("runtime", ""),
                            "memory": values.get("memory_size", 0),
                            "timeout": values.get("timeout", 0),
                            "handler": values.get("handler", ""),
                            "environment": values.get("environment", {})
                        })

                    # RDS/Aurora
                    elif resource_type in ["aws_rds_cluster", "aws_db_instance"]:
                        infrastructure["databases"].append({
                            "name": values.get("identifier", resource_name),
                            "engine": values.get("engine", ""),
                            "engine_version": values.get("engine_version", ""),
                            "instance_class": values.get("instance_class", ""),
                            "allocated_storage": values.get("allocated_storage", 0)
                        })

                    # API Gateway
                    elif resource_type == "aws_apigatewayv2_api":
                        infrastructure["api_gateways"].append({
                            "name": values.get("name", resource_name),
                            "protocol_type": values.get("protocol_type", ""),
                            "description": values.get("description", "")
                        })

                    # S3 Buckets
                    elif resource_type == "aws_s3_bucket":
                        infrastructure["s3_buckets"].append({
                            "name": values.get("bucket", resource_name),
                            "region": values.get("region", ""),
                            "versioning": values.get("versioning", {})
                        })

                    # CloudFront
                    elif resource_type == "aws_cloudfront_distribution":
                        infrastructure["cloudfront"].append({
                            "name": resource_name,
                            "domain_name": values.get("domain_name", ""),
                            "status": values.get("status", ""),
                            "comment": values.get("comment", "")
                        })

                    # Step Functions
                    elif resource_type == "aws_sfn_state_machine":
                        infrastructure["step_functions"].append({
                            "name": values.get("name", resource_name),
                            "type": values.get("type", ""),
                            "definition": values.get("definition", "")
                        })

            return infrastructure

        except Exception as e:
            logger.error(f"Failed to get deployed infrastructure: {e}")
            return {}

    def load_sync_state(self) -> Dict[str, Any]:
        """Load previous sync state"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load sync state: {e}")

        return {"last_hash": "", "last_sync": ""}

    def save_sync_state(self, state: Dict[str, Any]):
        """Save current sync state"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save sync state: {e}")

    def detect_infrastructure_changes(self) -> bool:
        """Check if infrastructure has changed since last sync"""
        current_hash = self.get_terraform_state_hash()
        if not current_hash:
            return False

        previous_state = self.load_sync_state()
        return current_hash != previous_state.get("last_hash", "")

    def generate_dsl_update(self, infrastructure: Dict[str, Any]) -> str:
        """Generate updated DSL content based on infrastructure changes"""

        # Track used variable names to prevent conflicts
        used_names = set()

        def make_unique_variable_name(base_name: str, resource_type: str) -> str:
            """Generate unique variable name for DSL containers"""
            # Clean base name
            clean_name = base_name.replace("-", "_").replace(".", "_")

            # Add resource type suffix for uniqueness
            type_suffix = {
                "lambda": "lambda",
                "database": "db",
                "api_gateway": "gateway",
                "storage": "bucket"
            }.get(resource_type, resource_type)

            candidate = f"{clean_name}_{type_suffix}"

            # Ensure uniqueness
            counter = 1
            final_name = candidate
            while final_name in used_names:
                final_name = f"{candidate}_{counter}"
                counter += 1

            used_names.add(final_name)
            return final_name

        # This is a simplified DSL generator
        # In practice, you'd want more sophisticated template handling

        dsl_content = f'''workspace "Daily Report Platform" "Auto-generated architecture from infrastructure sync" {{

    model {{
        # External Actors
        telegramUsers = person "Telegram Bot Users" "End users accessing ticker analysis through Telegram Mini App"

        # External Systems
        telegramPlatform = softwareSystem "Telegram Platform" "Official Telegram Bot API"
        openRouter = softwareSystem "OpenRouter API" "LLM API gateway"
        yahooFinance = softwareSystem "Yahoo Finance API" "Market data provider"
        langfuse = softwareSystem "Langfuse" "LLM observability platform"

        # Main System
        dailyReportSystem = softwareSystem "Daily Report System" "Ticker analysis platform" {{
'''

        # Add Lambda functions as containers
        for lambda_func in infrastructure.get("lambdas", []):
            var_name = make_unique_variable_name(lambda_func["name"], "lambda")
            display_name = f"{lambda_func['name']} (Lambda)"
            dsl_content += f'''
            {var_name} = container "{display_name}" "Lambda function" {{
                technology "AWS Lambda ({lambda_func.get('runtime', 'Container')})"
            }}'''

        # Add databases as containers
        for db in infrastructure.get("databases", []):
            var_name = make_unique_variable_name(db["name"], "database")
            display_name = f"{db['name']} (Database)"
            dsl_content += f'''
            {var_name} = container "{display_name}" "Database" {{
                technology "{db.get('engine', 'MySQL')} Database"
            }}'''

        # Add API Gateways
        for api in infrastructure.get("api_gateways", []):
            var_name = make_unique_variable_name(api["name"], "api_gateway")
            display_name = f"{api['name']} (API Gateway)"
            dsl_content += f'''
            {var_name} = container "{display_name}" "API Gateway" {{
                technology "AWS API Gateway ({api.get('protocol_type', 'HTTP')})"
            }}'''

        # Add S3 buckets
        for bucket in infrastructure.get("s3_buckets", []):
            var_name = make_unique_variable_name(bucket["name"], "storage")
            display_name = f"{bucket['name']} (S3)"
            dsl_content += f'''
            {var_name} = container "{display_name}" "Storage" {{
                technology "AWS S3"
            }}'''

        dsl_content += '''
        }

        # Basic relationships (would be enhanced with actual dependency analysis)
        telegramUsers -> telegramPlatform "Uses"
        telegramPlatform -> dailyReportSystem "Integrates with"
    }

    views {
        systemContext dailyReportSystem "SystemContext" {
            include *
            autoLayout
        }

        container dailyReportSystem "Containers" {
            include *
            autoLayout
        }
    }
}'''

        return dsl_content

    def update_dsl_file(self, new_content: str):
        """Update the DSL file with new content"""
        try:
            # Backup existing file
            if self.dsl_file.exists():
                backup_file = self.dsl_file.with_suffix('.dsl.backup')
                backup_file.write_text(self.dsl_file.read_text())
                logger.info(f"Backed up existing DSL to {backup_file}")

            # Write new content
            self.dsl_file.write_text(new_content)
            logger.info(f"Updated DSL file: {self.dsl_file}")

        except Exception as e:
            logger.error(f"Failed to update DSL file: {e}")

    def sync_once(self, force: bool = False) -> bool:
        """Perform one sync operation"""
        logger.info("🔍 Checking for infrastructure changes...")

        if not force and not self.detect_infrastructure_changes():
            logger.info("No infrastructure changes detected")
            return False

        logger.info("📊 Infrastructure changes detected, updating architecture...")

        # Get current infrastructure
        infrastructure = self.get_deployed_infrastructure()
        if not infrastructure:
            logger.warning("Failed to get infrastructure data")
            return False

        # Generate updated DSL
        new_dsl = self.generate_dsl_update(infrastructure)

        # Update DSL file
        self.update_dsl_file(new_dsl)

        # Update sync state
        current_hash = self.get_terraform_state_hash()
        sync_state = {
            "last_hash": current_hash,
            "last_sync": datetime.now().isoformat(),
            "infrastructure_summary": {
                "lambdas": len(infrastructure.get("lambdas", [])),
                "databases": len(infrastructure.get("databases", [])),
                "api_gateways": len(infrastructure.get("api_gateways", [])),
                "s3_buckets": len(infrastructure.get("s3_buckets", [])),
            }
        }
        self.save_sync_state(sync_state)

        logger.info("✅ Architecture sync completed successfully")
        return True

    def watch_mode(self, interval: int = 60):
        """Run in watch mode, continuously monitoring for changes"""
        logger.info(f"🔄 Starting watch mode (checking every {interval} seconds)")
        logger.info("Press Ctrl+C to stop")

        try:
            while True:
                self.sync_once()
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("\n🛑 Watch mode stopped")

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Sync infrastructure with Structurizr DSL")
    parser.add_argument("--watch", action="store_true", help="Run in watch mode")
    parser.add_argument("--force", action="store_true", help="Force sync even if no changes detected")
    parser.add_argument("--interval", type=int, default=60, help="Watch mode check interval in seconds")

    args = parser.parse_args()

    monitor = InfrastructureMonitor()

    if args.watch:
        monitor.watch_mode(args.interval)
    else:
        monitor.sync_once(args.force)

if __name__ == "__main__":
    main()