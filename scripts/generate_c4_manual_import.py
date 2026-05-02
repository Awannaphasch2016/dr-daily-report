#!/usr/bin/env python3
"""
C4 Architecture Diagram Generator - Manual Import Format
Generates YAML/JSON files for manual import into IcePanel since programmatic API is limited.

Usage:
    python scripts/generate_c4_manual_import.py

This will generate a YAML file that can be imported through IcePanel's UI.
"""

import json
import yaml
import logging
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum
import sys
import os

# Add the parent directory to the Python path to import from the main script
sys.path.append(os.path.dirname(__file__))

# Import infrastructure discovery from main script
try:
    from generate_c4_diagrams import AwsInfrastructureDiscovery, C4ModelMapper
except ImportError:
    print("Error: Could not import from generate_c4_diagrams.py")
    print("Make sure both scripts are in the same directory.")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def convert_to_icepanel_import_format(c4_model: Dict[str, Any]) -> Dict[str, Any]:
    """Convert C4 model to IcePanel import format following the schema"""

    # Map C4 types to IcePanel types
    type_mapping = {
        "PERSON": "actor",
        "SYSTEM": "system",
        "CONTAINER": "app",
        "COMPONENT": "component"
    }

    model_objects = []
    model_connections = []

    # Process objects
    for i, obj in enumerate(c4_model["objects"]):
        obj_id = f"obj-{i:03d}"

        # Determine IcePanel type
        icepanel_type = type_mapping.get(obj.type.name, "system")

        # Special handling for databases/storage
        if obj.technology and any(tech in obj.technology.lower()
                                for tech in ["mysql", "aurora", "database", "s3", "storage"]):
            icepanel_type = "store"

        # Special handling for API gateways
        if "api gateway" in obj.name.lower() or "gateway" in obj.name.lower():
            icepanel_type = "app"

        model_object = {
            "id": obj_id,
            "name": obj.name,
            "description": obj.description,
            "type": icepanel_type
        }

        # Add technology if specified
        if obj.technology:
            model_object["technology"] = obj.technology

        # Add tags if specified
        if obj.tags:
            model_object["tags"] = obj.tags

        model_objects.append(model_object)

    # Create a mapping from object names to IDs for connections
    name_to_id = {obj.name: f"obj-{i:03d}" for i, obj in enumerate(c4_model["objects"])}

    # Process relationships
    for i, rel in enumerate(c4_model["relationships"]):
        if rel.source in name_to_id and rel.target in name_to_id:
            connection = {
                "id": f"conn-{i:03d}",
                "name": rel.description,
                "originId": name_to_id[rel.source],
                "targetId": name_to_id[rel.target],
                "direction": "outgoing"
            }

            # Add protocol/technology if specified
            if rel.protocol:
                connection["technology"] = rel.protocol

            model_connections.append(connection)

    return {
        "modelObjects": model_objects,
        "modelConnections": model_connections
    }

def generate_import_files():
    """Generate YAML and JSON files for IcePanel import"""

    logger.info("Starting C4 model generation for manual import...")

    try:
        # Phase 1: Discover infrastructure
        discovery = AwsInfrastructureDiscovery()
        infrastructure = discovery.discover_infrastructure()

        # Phase 2: Map to C4 model
        mapper = C4ModelMapper(infrastructure)
        c4_model = mapper.generate_c4_model()

        # Phase 3: Convert to IcePanel import format
        import_data = convert_to_icepanel_import_format(c4_model)

        # Generate output files
        output_dir = "generated_c4_diagrams"
        os.makedirs(output_dir, exist_ok=True)

        # Generate YAML file with schema reference
        yaml_content = f"""# yaml-language-server: $schema=https://api.icepanel.io/v1/schemas/LandscapeImportData

# Daily Report System Architecture
# Generated C4 model for import into IcePanel
#
# This file contains:
# - {len(import_data['modelObjects'])} model objects (actors, systems, apps, stores, components)
# - {len(import_data['modelConnections'])} connections between objects
#
# To import:
# 1. Open IcePanel (https://app.icepanel.io)
# 2. Go to your landscape
# 3. Click "Import" in the model section
# 4. Upload this YAML file

{yaml.dump(import_data, default_flow_style=False, sort_keys=False, indent=2)}"""

        yaml_file = os.path.join(output_dir, "daily_report_architecture.yaml")
        with open(yaml_file, 'w') as f:
            f.write(yaml_content)

        # Generate JSON file as backup
        json_file = os.path.join(output_dir, "daily_report_architecture.json")
        with open(json_file, 'w') as f:
            json.dump(import_data, f, indent=2, default=str)

        # Generate summary
        summary = {
            "architecture_summary": {
                "total_objects": len(import_data['modelObjects']),
                "total_connections": len(import_data['modelConnections']),
                "object_types": {},
                "technologies": set(),
                "external_systems": []
            }
        }

        # Analyze objects
        for obj in import_data['modelObjects']:
            obj_type = obj['type']
            summary["architecture_summary"]["object_types"][obj_type] = \
                summary["architecture_summary"]["object_types"].get(obj_type, 0) + 1

            if 'technology' in obj:
                summary["architecture_summary"]["technologies"].add(obj['technology'])

            if obj['type'] == 'system' and any(ext in obj['name'].lower()
                                            for ext in ['telegram', 'openrouter', 'yahoo', 'langfuse']):
                summary["architecture_summary"]["external_systems"].append(obj['name'])

        # Convert set to list for JSON serialization
        summary["architecture_summary"]["technologies"] = list(summary["architecture_summary"]["technologies"])

        summary_file = os.path.join(output_dir, "architecture_summary.json")
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        # Success message
        logger.info("✅ C4 model files generated successfully!")
        print("\n" + "="*70)
        print("📊 C4 DIAGRAM GENERATION COMPLETE")
        print("="*70)
        print(f"📁 Output Directory: {output_dir}/")
        print(f"📄 YAML Import File: {yaml_file}")
        print(f"📄 JSON Backup File: {json_file}")
        print(f"📄 Architecture Summary: {summary_file}")
        print()
        print("📈 Architecture Stats:")
        print(f"  • Total Objects: {summary['architecture_summary']['total_objects']}")
        print(f"  • Total Connections: {summary['architecture_summary']['total_connections']}")
        print("  • Object Types:")
        for obj_type, count in summary['architecture_summary']['object_types'].items():
            print(f"    - {obj_type}: {count}")
        print(f"  • Technologies: {len(summary['architecture_summary']['technologies'])}")
        print(f"  • External Systems: {len(summary['architecture_summary']['external_systems'])}")
        print()
        print("🎯 Next Steps:")
        print("1. Open IcePanel: https://app.icepanel.io")
        print("2. Navigate to your landscape")
        print("3. Click 'Import' in the model section")
        print(f"4. Upload: {yaml_file}")
        print("5. Create diagrams from the imported model")
        print("="*70)

    except Exception as e:
        logger.error(f"❌ Failed to generate import files: {e}")
        raise

if __name__ == "__main__":
    generate_import_files()