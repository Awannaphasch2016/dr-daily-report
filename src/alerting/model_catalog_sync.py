"""OpenRouter model catalog sync Lambda handler.

Fetches the full model catalog from OpenRouter's free /api/v1/models
endpoint and upserts into Aurora model_catalog table.

Environment Variables:
    AURORA_HOST: Aurora MySQL host (required)
    AURORA_PORT: Aurora MySQL port (default: 3306)
    AURORA_DATABASE: Aurora database name (required)
    AURORA_USER: Aurora username (required)
    AURORA_PASSWORD: Aurora password (required)
    ENVIRONMENT: Environment name - dev, staging, prod (required)

Triggered by: EventBridge Scheduler (daily 4 AM Bangkok)
"""

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Environment configuration
ENVIRONMENT = os.environ.get("ENVIRONMENT", "unknown")

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


def _validate_config():
    """Validate required configuration at startup (Principle #1: Defensive Programming)."""
    missing = []
    for var in ("AURORA_HOST", "AURORA_DATABASE", "AURORA_USER", "AURORA_PASSWORD"):
        if not os.environ.get(var):
            missing.append(var)
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")


def _fetch_openrouter_models() -> List[Dict]:
    """Fetch model catalog from OpenRouter API (free, no API key required).

    Returns:
        List of raw model dicts from the API response.

    Raises:
        urllib.error.URLError: On connection failure.
        urllib.error.HTTPError: On HTTP error response.
    """
    req = urllib.request.Request(
        OPENROUTER_MODELS_URL,
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    models = data.get("data", [])
    if not models:
        raise ValueError("OpenRouter API returned empty model list")

    logger.info(f"Fetched {len(models)} models from OpenRouter")
    return models


def _parse_price(price_str: Optional[str]) -> Optional[Decimal]:
    """Parse price string to Decimal, returning None on failure."""
    if price_str is None:
        return None
    try:
        return Decimal(str(price_str))
    except (InvalidOperation, ValueError):
        return None


def _extract_provider(model_id: str) -> Optional[str]:
    """Extract provider from model_id (e.g. 'openai/gpt-4o' -> 'openai')."""
    if "/" in model_id:
        return model_id.split("/")[0]
    return None


def _parse_created_at(timestamp: Optional[int]) -> Optional[str]:
    """Parse Unix timestamp to MySQL TIMESTAMP string."""
    if timestamp is None:
        return None
    try:
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError, OSError):
        return None


def _transform_models(raw_models: List[Dict]) -> List[Dict]:
    """Transform raw OpenRouter models into typed dicts for upsert.

    Args:
        raw_models: Raw model dicts from OpenRouter API.

    Returns:
        List of transformed model dicts ready for upsert.
    """
    transformed = []
    skipped = 0

    for raw in raw_models:
        model_id = raw.get("id")
        if not model_id:
            skipped += 1
            continue

        pricing = raw.get("pricing", {})

        model = {
            "model_id": model_id,
            "name": raw.get("name"),
            "context_length": raw.get("context_length"),
            "input_price_per_token": _parse_price(pricing.get("prompt")),
            "output_price_per_token": _parse_price(pricing.get("completion")),
            "modality": raw.get("architecture", {}).get("modality"),
            "tokenizer": raw.get("architecture", {}).get("tokenizer"),
            "provider": _extract_provider(model_id),
            "is_free": _parse_price(pricing.get("prompt")) == Decimal("0"),
            "created_at_source": _parse_created_at(raw.get("created")),
            "raw_json": raw,
        }

        transformed.append(model)

    if skipped:
        logger.warning(f"Skipped {skipped} models without ID")

    return transformed


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for OpenRouter model catalog sync.

    Narrative flow (Principle #18):
    BEGIN → validate config → fetch models → transform → upsert → END
    """
    logger.info(f"🔄 Model catalog sync starting (env={ENVIRONMENT})")

    # Step 1: Validate configuration
    try:
        _validate_config()
    except RuntimeError as e:
        logger.error(f"❌ Configuration error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

    # Step 2: Fetch models from OpenRouter
    try:
        raw_models = _fetch_openrouter_models()
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
        logger.error(f"❌ Failed to fetch models from OpenRouter: {e}")
        return {"statusCode": 502, "body": json.dumps({"error": f"OpenRouter API failed: {e}"})}

    # Step 3: Transform models
    transformed = _transform_models(raw_models)
    logger.info(f"Transformed {len(transformed)} models from {len(raw_models)} raw entries")

    # Step 4: Upsert into Aurora
    try:
        from src.data.aurora.model_catalog_repository import get_model_catalog_repository

        repo = get_model_catalog_repository()
        affected = repo.upsert_models(transformed)
    except Exception as e:
        logger.error(f"❌ Database upsert failed: {e}", exc_info=True)
        return {"statusCode": 500, "body": json.dumps({"error": f"Database upsert failed: {e}"})}

    # Step 5: Summary (Principle #18: narrative end)
    logger.info(
        f"✅ Model catalog sync complete: "
        f"fetched={len(raw_models)}, transformed={len(transformed)}, "
        f"db_affected={affected}"
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "fetched": len(raw_models),
            "transformed": len(transformed),
            "db_affected": affected,
            "environment": ENVIRONMENT,
        }),
    }
