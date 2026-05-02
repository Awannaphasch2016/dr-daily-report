#!/usr/bin/env python3
"""
C4 Architecture Diagram Generator for Daily Report System
Generates interactive C4 diagrams using IcePanel API from deployed AWS infrastructure.

Usage:
    python scripts/generate_c4_diagrams.py

Requirements:
    - ICEPANEL_API_KEY in Doppler (--project openclaw --config dev)
    - Terraform state accessible for infrastructure discovery
"""

import os
import json
import logging
import subprocess
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class C4ObjectType(Enum):
    """C4 model object types supported by IcePanel"""
    PERSON = "person"
    SYSTEM = "system"
    CONTAINER = "container"
    COMPONENT = "component"

class C4DiagramType(Enum):
    """C4 diagram levels"""
    CONTEXT = "context"
    CONTAINER = "container"
    COMPONENT = "component"

@dataclass
class C4Object:
    """Represents a C4 model object"""
    name: str
    description: str
    type: C4ObjectType
    technology: Optional[str] = None
    tags: Optional[List[str]] = None

@dataclass
class C4Relationship:
    """Represents a relationship between C4 objects"""
    source: str
    target: str
    description: str
    protocol: Optional[str] = None

class AwsInfrastructureDiscovery:
    """Discovers AWS infrastructure from Terraform state and configurations"""

    def __init__(self):
        self.terraform_dir = "terraform"

    def discover_infrastructure(self) -> Dict[str, Any]:
        """Discover deployed AWS infrastructure"""
        logger.info("Discovering AWS infrastructure from Terraform...")

        # Get Terraform state for deployed resources
        infrastructure = {
            "lambdas": self._discover_lambdas(),
            "databases": self._discover_databases(),
            "api_gateways": self._discover_api_gateways(),
            "s3_buckets": self._discover_s3_buckets(),
            "cloudfront": self._discover_cloudfront(),
            "step_functions": self._discover_step_functions(),
            "external_systems": self._discover_external_systems()
        }

        logger.info(f"Discovered infrastructure: {len(infrastructure['lambdas'])} Lambdas, "
                   f"{len(infrastructure['databases'])} databases, "
                   f"{len(infrastructure['api_gateways'])} API Gateways")

        return infrastructure

    def _discover_lambdas(self) -> List[Dict[str, Any]]:
        """Discover Lambda functions from Terraform files"""
        lambdas = []

        # Key Lambda functions from our analysis
        lambda_configs = [
            {
                "name": "telegram-api",
                "description": "Telegram Mini App REST API - handles user requests, watchlist management, async report generation",
                "file": "telegram_api.tf",
                "handler": "telegram_lambda_handler.handler",
                "memory": 512,
                "timeout": 120,
                "vpc": True,
                "app": "telegram-api"
            },
            {
                "name": "report-worker",
                "description": "Async report generation worker - processes report requests, generates PDF reports using LLM",
                "file": "async_report.tf",
                "handler": "report_worker_handler.handler",
                "memory": 1024,
                "timeout": 120,
                "vpc": True,
                "app": "telegram-api"
            },
            {
                "name": "ticker-fetcher",
                "description": "Scheduled ticker data fetcher - fetches market data from Yahoo Finance API",
                "file": "ticker_fetcher.tf",
                "handler": "ticker_fetcher_handler.handler",
                "vpc": True,
                "app": "shared"
            }
        ]

        for config in lambda_configs:
            lambdas.append({
                "name": f"dr-daily-report-{config['name']}-dev",
                "description": config["description"],
                "runtime": "Container (Python)",
                "memory_mb": config.get("memory", 512),
                "timeout_seconds": config.get("timeout", 60),
                "vpc_enabled": config.get("vpc", False),
                "app": config.get("app", "shared"),
                "triggers": self._get_lambda_triggers(config["name"])
            })

        return lambdas

    def _get_lambda_triggers(self, lambda_name: str) -> List[str]:
        """Get triggers for a Lambda function"""
        triggers = {
            "telegram-api": ["API Gateway HTTP API"],
            "report-worker": ["Direct Lambda Invocation"],
            "ticker-fetcher": ["EventBridge Schedule (daily)"]
        }
        return triggers.get(lambda_name, [])

    def _discover_databases(self) -> List[Dict[str, Any]]:
        """Discover databases from Terraform configuration"""
        return [{
            "name": "Aurora MySQL Serverless v2",
            "description": "Primary data store - ticker data, cache, user watchlists",
            "engine": "MySQL 8.0",
            "capacity": "0.5-2 ACU",
            "vpc": True,
            "databases": ["ticker_data"],
            "tables": [
                "daily_prices", "ticker_info", "ticker_data_cache",
                "telegram_watchlist", "fund_data", "fund_holdings"
            ]
        }]

    def _discover_api_gateways(self) -> List[Dict[str, Any]]:
        """Discover API Gateway configurations"""
        return [{
            "name": "Telegram HTTP API",
            "description": "REST API for Telegram Mini App - user authentication, watchlist, reports",
            "type": "HTTP API Gateway",
            "cors_origins": [
                "https://web.telegram.org",
                "https://t.me",
                "CloudFront distributions (dev/staging/prod)"
            ]
        }]

    def _discover_s3_buckets(self) -> List[Dict[str, Any]]:
        """Discover S3 buckets from Terraform"""
        return [
            {
                "name": "PDF Reports Storage",
                "description": "Generated PDF ticker reports with 24h presigned URLs",
                "bucket_pattern": "dr-daily-report-pdf-*-dev",
                "access": "Private with presigned URLs"
            },
            {
                "name": "Data Lake",
                "description": "Raw market data staging, pipeline payloads, ETL processing",
                "bucket_pattern": "dr-daily-report-data-lake-*-dev",
                "folders": ["raw/", "processed/", "pipeline/"]
            }
        ]

    def _discover_cloudfront(self) -> List[Dict[str, Any]]:
        """Discover CloudFront distributions"""
        return [
            {
                "name": "Telegram Web App (APP)",
                "description": "Serves Telegram Mini App frontend to users",
                "domain": "demjoigiw6myp.cloudfront.net",
                "origin": "S3 Static Website",
                "purpose": "Production user traffic"
            },
            {
                "name": "Telegram Web App (TEST)",
                "description": "E2E testing environment for automated tests",
                "domain": "Dynamic (generated)",
                "origin": "S3 Static Website",
                "purpose": "Automated testing"
            }
        ]

    def _discover_step_functions(self) -> List[Dict[str, Any]]:
        """Discover Step Functions workflows"""
        return [
            {
                "name": "Report Pipeline",
                "description": "Express workflow for split report generation (preprocess → LLM → postprocess)",
                "type": "EXPRESS",
                "trigger": "report-worker Lambda (when use_report_pipeline=true)"
            },
            {
                "name": "Precompute Workflow",
                "description": "Scheduled workflow for precomputing popular ticker analysis",
                "type": "STANDARD",
                "schedule": "Daily execution"
            }
        ]

    def _discover_external_systems(self) -> List[Dict[str, Any]]:
        """Discover external systems and APIs"""
        return [
            {
                "name": "Telegram Bot API",
                "description": "Official Telegram API for bot operations and WebApp integration",
                "protocol": "HTTPS REST",
                "authentication": "Bot Token"
            },
            {
                "name": "OpenRouter API",
                "description": "LLM API proxy for GPT-4/Claude models used in report generation",
                "protocol": "HTTPS REST",
                "authentication": "API Key"
            },
            {
                "name": "Yahoo Finance API",
                "description": "Market data source for ticker information and historical prices",
                "protocol": "HTTPS REST",
                "authentication": "None (public)"
            },
            {
                "name": "Langfuse",
                "description": "LLM observability platform for tracing and monitoring AI operations",
                "protocol": "HTTPS REST",
                "authentication": "API Keys"
            }
        ]

class C4ModelMapper:
    """Maps AWS infrastructure to C4 model objects and relationships"""

    def __init__(self, infrastructure: Dict[str, Any]):
        self.infrastructure = infrastructure

    def generate_c4_model(self) -> Dict[str, Any]:
        """Generate complete C4 model from infrastructure"""
        logger.info("Mapping infrastructure to C4 model...")

        return {
            "objects": self._create_c4_objects(),
            "relationships": self._create_c4_relationships(),
            "diagrams": self._define_diagram_hierarchy()
        }

    def _create_c4_objects(self) -> List[C4Object]:
        """Create C4 objects for all infrastructure components"""
        objects = []

        # Level 1: External actors and systems
        objects.extend([
            C4Object("Telegram Bot Users", "End users using Telegram Mini App for ticker analysis", C4ObjectType.PERSON),
            C4Object("Telegram Platform", "Official Telegram Bot API and WebApp infrastructure", C4ObjectType.SYSTEM),
            C4Object("Daily Report System", "Comprehensive ticker analysis and reporting platform", C4ObjectType.SYSTEM, tags=["aws", "main-system"]),
            C4Object("OpenRouter", "LLM API gateway providing access to GPT-4/Claude models", C4ObjectType.SYSTEM),
            C4Object("Yahoo Finance", "Market data provider for real-time and historical ticker information", C4ObjectType.SYSTEM),
            C4Object("Langfuse", "LLM observability and tracing platform", C4ObjectType.SYSTEM)
        ])

        # Level 2: Containers (main services)
        objects.extend([
            C4Object("Telegram API Gateway", "HTTP REST API for Telegram Mini App interactions", C4ObjectType.CONTAINER, "AWS API Gateway"),
            C4Object("Telegram API Service", "Main application logic for user requests and watchlist management", C4ObjectType.CONTAINER, "AWS Lambda (Container)"),
            C4Object("Report Worker Service", "Async report generation with LLM integration", C4ObjectType.CONTAINER, "AWS Lambda (Container)"),
            C4Object("Ticker Data Service", "Scheduled market data fetching and processing", C4ObjectType.CONTAINER, "AWS Lambda (Container)"),
            C4Object("Aurora Database", "Primary data store for ticker data and user information", C4ObjectType.CONTAINER, "Aurora MySQL Serverless v2"),
            C4Object("PDF Storage", "Generated report storage with secure access", C4ObjectType.CONTAINER, "AWS S3"),
            C4Object("Data Lake", "Raw market data and pipeline artifact storage", C4ObjectType.CONTAINER, "AWS S3"),
            C4Object("Web App Distribution", "Content delivery for Telegram Mini App frontend", C4ObjectType.CONTAINER, "AWS CloudFront"),
            C4Object("Report Pipeline", "Orchestrated report generation workflow", C4ObjectType.CONTAINER, "AWS Step Functions"),
            C4Object("Precompute Pipeline", "Scheduled analysis and cache warming", C4ObjectType.CONTAINER, "AWS Step Functions")
        ])

        # Level 3: Components (within main services)
        objects.extend([
            # Telegram API Service components
            C4Object("Authentication Handler", "Validates Telegram user data and sessions", C4ObjectType.COMPONENT, "FastAPI"),
            C4Object("Watchlist Manager", "CRUD operations for user ticker watchlists", C4ObjectType.COMPONENT, "FastAPI"),
            C4Object("Report Request Handler", "Initiates async report generation jobs", C4ObjectType.COMPONENT, "FastAPI"),
            C4Object("Cache Manager", "Hybrid caching (S3 + Aurora) for report data", C4ObjectType.COMPONENT, "Python"),

            # Report Worker components
            C4Object("LLM Report Generator", "Orchestrates AI-powered financial analysis", C4ObjectType.COMPONENT, "LangGraph"),
            C4Object("Market Data Analyzer", "Processes ticker data for insights", C4ObjectType.COMPONENT, "Python/yfinance"),
            C4Object("PDF Generator", "Creates formatted PDF reports", C4ObjectType.COMPONENT, "ReportLab"),
            C4Object("Job Status Manager", "Tracks async job progress and completion", C4ObjectType.COMPONENT, "DynamoDB Client")
        ])

        return objects

    def _create_c4_relationships(self) -> List[C4Relationship]:
        """Create relationships between C4 objects"""
        relationships = []

        # External user flows
        relationships.extend([
            C4Relationship("Telegram Bot Users", "Telegram Platform", "Interacts with Mini App", "HTTPS"),
            C4Relationship("Telegram Platform", "Web App Distribution", "Loads Mini App frontend", "HTTPS"),
            C4Relationship("Web App Distribution", "Telegram API Gateway", "Makes API requests", "HTTPS/REST"),
            C4Relationship("Telegram API Gateway", "Telegram API Service", "Routes requests", "AWS Integration")
        ])

        # Internal service flows
        relationships.extend([
            C4Relationship("Telegram API Service", "Aurora Database", "Reads/writes user data", "MySQL"),
            C4Relationship("Telegram API Service", "Report Worker Service", "Invokes async report generation", "Direct Lambda"),
            C4Relationship("Report Worker Service", "Aurora Database", "Caches report data", "MySQL"),
            C4Relationship("Report Worker Service", "PDF Storage", "Stores generated reports", "S3 API"),
            C4Relationship("Ticker Data Service", "Aurora Database", "Stores market data", "MySQL"),
            C4Relationship("Ticker Data Service", "Data Lake", "Archives raw data", "S3 API")
        ])

        # External system integrations
        relationships.extend([
            C4Relationship("Telegram API Service", "Telegram Platform", "Validates user auth", "HTTPS/REST"),
            C4Relationship("Report Worker Service", "OpenRouter", "Generates AI analysis", "HTTPS/REST"),
            C4Relationship("Report Worker Service", "Langfuse", "Traces LLM operations", "HTTPS/REST"),
            C4Relationship("Ticker Data Service", "Yahoo Finance", "Fetches market data", "HTTPS/REST"),
            C4Relationship("Report Worker Service", "Report Pipeline", "Executes split pipeline", "Step Functions")
        ])

        return relationships

    def _define_diagram_hierarchy(self) -> Dict[str, Any]:
        """Define the hierarchy of C4 diagrams to generate"""
        return {
            "context": {
                "name": "Daily Report System - Context",
                "description": "High-level view showing users and external systems",
                "focus_objects": ["Telegram Bot Users", "Daily Report System", "Telegram Platform", "OpenRouter", "Yahoo Finance", "Langfuse"]
            },
            "container": {
                "name": "Daily Report System - Containers",
                "description": "Internal services and data stores",
                "focus_objects": [
                    "Telegram API Gateway", "Telegram API Service", "Report Worker Service",
                    "Aurora Database", "PDF Storage", "Web App Distribution", "Report Pipeline"
                ]
            },
            "telegram_api_components": {
                "name": "Telegram API Service - Components",
                "description": "Internal structure of the main API service",
                "focus_objects": [
                    "Authentication Handler", "Watchlist Manager", "Report Request Handler", "Cache Manager"
                ]
            },
            "report_worker_components": {
                "name": "Report Worker Service - Components",
                "description": "Internal structure of the report generation service",
                "focus_objects": [
                    "LLM Report Generator", "Market Data Analyzer", "PDF Generator", "Job Status Manager"
                ]
            }
        }

class IcePanelClient:
    """Client for IcePanel REST API"""

    def __init__(self):
        self.api_key = self._get_api_key()
        self.base_url = "https://api.icepanel.io"
        self.headers = {
            "Authorization": f"ApiKey {self.api_key}",
            "Content-Type": "application/json"
        }
        self.landscape_id = None
        self.organization_id = None

    def _get_api_key(self) -> str:
        """Get IcePanel API key from Doppler"""
        try:
            result = subprocess.run(
                ["doppler", "secrets", "get", "ICEPANEL_API_KEY", "--project", "openclaw", "--config", "dev", "--plain"],
                capture_output=True,
                text=True,
                check=True
            )
            api_key = result.stdout.strip()
            if not api_key:
                raise ValueError("ICEPANEL_API_KEY is empty")
            return api_key
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get ICEPANEL_API_KEY from Doppler: {e}")

    def get_or_create_organization(self) -> str:
        """Get organization ID (required for API calls)"""
        # First, try to get organizations
        response = requests.get(
            f"{self.base_url}/v1/organizations",
            headers=self.headers
        )

        if response.status_code == 200:
            orgs_data = response.json()
            orgs = orgs_data.get("organizations", [])
            if orgs and len(orgs) > 0:
                self.organization_id = orgs[0]["id"]
                logger.info(f"Using organization: {orgs[0]['name']} ({self.organization_id})")
                return self.organization_id
            else:
                raise RuntimeError("No organizations found. Please create one in IcePanel first.")
        else:
            raise RuntimeError(f"Failed to get organizations: {response.status_code} {response.text}")

    def create_landscape(self, name: str, description: str) -> str:
        """Create a new landscape for our architecture"""
        if not self.organization_id:
            self.get_or_create_organization()

        payload = {
            "name": name,
            "description": description
        }

        response = requests.post(
            f"{self.base_url}/v1/organizations/{self.organization_id}/landscapes",
            headers=self.headers,
            json=payload
        )

        if response.status_code in [200, 201]:
            response_data = response.json()
            landscape = response_data.get("landscape", response_data)
            self.landscape_id = landscape["id"]
            logger.info(f"Created landscape: {landscape['name']} ({self.landscape_id})")
            return self.landscape_id
        else:
            raise RuntimeError(f"Failed to create landscape: {response.status_code} {response.text}")

    def create_objects_via_import(self, c4_model: Dict[str, Any]) -> Dict[str, str]:
        """Create C4 objects using IcePanel's import API"""
        if not self.landscape_id:
            raise RuntimeError("No landscape created. Call create_landscape() first.")

        # Convert C4 objects to IcePanel import format
        model_objects = []
        model_connections = []
        object_ids = {}

        # Map C4 types to IcePanel types
        type_mapping = {
            C4ObjectType.PERSON: "actor",
            C4ObjectType.SYSTEM: "system",
            C4ObjectType.CONTAINER: "app",  # or "store" for databases
            C4ObjectType.COMPONENT: "component"
        }

        # Create objects
        for i, obj in enumerate(c4_model["objects"]):
            obj_id = f"obj-{i}"
            icepanel_type = type_mapping.get(obj.type, "system")

            # Special handling for databases
            if obj.technology and any(db in obj.technology.lower() for db in ["mysql", "postgres", "database", "aurora"]):
                icepanel_type = "store"

            model_object = {
                "id": obj_id,
                "name": obj.name,
                "description": obj.description,
                "type": icepanel_type
            }

            if obj.technology:
                model_object["technology"] = obj.technology

            if obj.tags:
                model_object["tags"] = obj.tags

            model_objects.append(model_object)
            object_ids[obj.name] = obj_id

        # Create connections
        for i, rel in enumerate(c4_model["relationships"]):
            if rel.source in object_ids and rel.target in object_ids:
                connection = {
                    "id": f"conn-{i}",
                    "name": rel.description,
                    "originId": object_ids[rel.source],
                    "targetId": object_ids[rel.target],
                    "direction": "outgoing"
                }

                if rel.protocol:
                    connection["technology"] = rel.protocol

                model_connections.append(connection)

        # Create import payload
        import_payload = {
            "modelObjects": model_objects,
            "modelConnections": model_connections
        }

        # Import via API
        response = requests.post(
            f"{self.base_url}/v1/landscapes/{self.landscape_id}/import",
            headers=self.headers,
            json=import_payload
        )

        if response.status_code in [200, 201]:
            logger.info(f"Successfully imported {len(model_objects)} objects and {len(model_connections)} connections")
            return object_ids
        else:
            raise RuntimeError(f"Failed to import objects: {response.status_code} {response.text}")

    def create_relationships(self, relationships: List[C4Relationship], object_ids: Dict[str, str]):
        """Create relationships between objects"""
        created_count = 0

        for rel in relationships:
            if rel.source not in object_ids or rel.target not in object_ids:
                logger.warning(f"Skipping relationship {rel.source} -> {rel.target}: object not found")
                continue

            payload = {
                "source_id": object_ids[rel.source],
                "target_id": object_ids[rel.target],
                "description": rel.description,
                "protocol": rel.protocol
            }

            response = requests.post(
                f"{self.base_url}/landscapes/{self.landscape_id}/relationships",
                headers=self.headers,
                json=payload
            )

            if response.status_code == 201:
                created_count += 1
                logger.debug(f"Created relationship: {rel.source} -> {rel.target}")
            else:
                logger.error(f"Failed to create relationship: {response.status_code} {response.text}")

        logger.info(f"Created {created_count} relationships")

    def create_diagrams(self, diagram_specs: Dict[str, Any], object_ids: Dict[str, str]) -> Dict[str, str]:
        """Create C4 diagrams with specified object focus"""
        diagram_ids = {}

        for diagram_key, spec in diagram_specs.items():
            # Filter to only include objects that exist
            focus_object_ids = []
            for obj_name in spec["focus_objects"]:
                if obj_name in object_ids:
                    focus_object_ids.append(object_ids[obj_name])
                else:
                    logger.warning(f"Object {obj_name} not found for diagram {diagram_key}")

            payload = {
                "name": spec["name"],
                "description": spec["description"],
                "type": self._get_diagram_type(diagram_key),
                "object_ids": focus_object_ids
            }

            response = requests.post(
                f"{self.base_url}/landscapes/{self.landscape_id}/diagrams",
                headers=self.headers,
                json=payload
            )

            if response.status_code == 201:
                diagram = response.json()
                diagram_ids[diagram_key] = diagram["id"]
                logger.info(f"Created diagram: {spec['name']}")
            else:
                logger.error(f"Failed to create diagram {diagram_key}: {response.status_code} {response.text}")

        return diagram_ids

    def _get_diagram_type(self, diagram_key: str) -> str:
        """Map diagram key to IcePanel diagram type"""
        type_mapping = {
            "context": "system_context",
            "container": "container",
            "telegram_api_components": "component",
            "report_worker_components": "component"
        }
        return type_mapping.get(diagram_key, "system_context")

def main():
    """Main execution function"""
    logger.info("Starting C4 diagram generation for Daily Report System...")

    try:
        # Phase 1: Discover infrastructure
        discovery = AwsInfrastructureDiscovery()
        infrastructure = discovery.discover_infrastructure()

        # Phase 2: Map to C4 model
        mapper = C4ModelMapper(infrastructure)
        c4_model = mapper.generate_c4_model()

        # Phase 3: Generate diagrams via IcePanel API
        client = IcePanelClient()

        # Create landscape
        landscape_id = client.create_landscape(
            "Daily Report System Architecture",
            "Complete AWS cloud architecture for the Daily Report Telegram Mini App and LINE Bot system"
        )

        # Create objects and relationships via import
        object_ids = client.create_objects_via_import(c4_model)

        # Create diagrams
        diagram_ids = client.create_diagrams(c4_model["diagrams"], object_ids)

        logger.info("✅ C4 diagram generation completed successfully!")
        logger.info(f"📊 Created landscape: {landscape_id}")
        logger.info(f"🔗 Created {len(object_ids)} objects")
        logger.info(f"📈 Created {len(diagram_ids)} diagrams")

        # Output summary
        print("\n" + "="*60)
        print("📋 DIAGRAM GENERATION SUMMARY")
        print("="*60)
        print(f"🏛️  Landscape ID: {landscape_id}")
        print(f"📦 Objects Created: {len(object_ids)}")
        print(f"🔗 Relationships: {len(c4_model['relationships'])}")
        print(f"📊 Diagrams Created: {len(diagram_ids)}")
        print("\n📈 Generated Diagrams:")
        for name, diagram_id in diagram_ids.items():
            print(f"  • {c4_model['diagrams'][name]['name']}: {diagram_id}")
        print(f"\n🌐 Access your diagrams at: https://app.icepanel.io/landscapes/{landscape_id}")
        print("="*60)

    except Exception as e:
        logger.error(f"❌ Failed to generate C4 diagrams: {e}")
        raise

if __name__ == "__main__":
    main()