"""
Centralized Mock Registry - All production code mocks registered here.

IMPORTANT: This file lists ALL mocks active in working code.
Before deploying to production, verify MOCK_MODE is disabled.

Loud Mock Pattern:
- Centralized: All mocks registered in ACTIVE_MOCKS dict
- Loud: validate_mocks() logs warnings at startup
- Explicit: Environment-gated, no silent defaults
- Documented: Each mock has reason/owner/date
"""

import os
import logging
from datetime import date

logger = logging.getLogger(__name__)

# Central registry - Single source of truth for all mocks
ACTIVE_MOCKS = {
    'strategy_backtester': {
        'enabled': True,  # Always stubbed (feature incomplete)
        'location': 'src/utils/strategy.py',
        'reason': 'Backtesting not implemented yet',
        'added': '2024-12-01',
        'owner': '@team',
        'notes': 'Returns None for all backtest methods. Transparency footer informs users.'
    },
    'line_bot_test_signature': {
        'enabled': os.getenv('LINE_TEST_MODE') == 'true',
        'location': 'src/integrations/line_bot.py',
        'reason': 'Allow manual testing without valid LINE signature',
        'added': '2025-01-16',
        'owner': '@developer',
        'notes': 'Security bypass - only enable in local dev, never in production'
    },
    # Example: Aurora queries mock (disabled by default)
    'aurora_queries': {
        'enabled': os.getenv('MOCK_AURORA') == 'true',
        'location': 'src/mocks/aurora_mocks.py',
        'reason': 'Speed up local dev, avoid Aurora SSM tunnel',
        'added': '2025-01-16',
        'owner': '@developer',
        'notes': 'Returns cached/static data for Aurora queries. Use for local development only.'
    },
}


def validate_mocks() -> None:
    """
    Called at application startup - logs all active mocks loudly.

    Raises:
        RuntimeError: If unexpected mocks are active in production environment

    Examples:
        >>> # In src/agent.py __init__()
        >>> from src.mocks import validate_mocks
        >>> validate_mocks()  # Logs warnings if mocks active
    """
    active = {k: v for k, v in ACTIVE_MOCKS.items() if v['enabled']}

    if not active:
        logger.info("✅ No mocks active - using real data")
        return

    # LOUD WARNING - Impossible to miss in logs
    logger.warning("=" * 70)
    logger.warning("⚠️  MOCK DATA ACTIVE - NOT USING REAL DATA")
    logger.warning("=" * 70)

    for name, config in active.items():
        logger.warning(f"  🔧 {name}")
        logger.warning(f"     Location: {config['location']}")
        logger.warning(f"     Reason: {config['reason']}")
        logger.warning(f"     Added: {config['added']} by {config['owner']}")
        if config.get('notes'):
            logger.warning(f"     Notes: {config['notes']}")

    logger.warning("=" * 70)

    # FAIL in production if unexpected mocks active
    env = os.getenv('ENV', 'development')
    if env == 'production':
        # Whitelist: Mocks allowed in production
        production_whitelist = ['strategy_backtester']  # Stub implementation, not a dev mock

        forbidden_mocks = [k for k in active.keys()
                          if k not in production_whitelist]

        if forbidden_mocks:
            error_msg = (
                f"❌ Production deployment with development mocks: {forbidden_mocks}\n"
                f"   Disable these mocks before deploying to production:\n"
            )
            for mock in forbidden_mocks:
                error_msg += f"   - {mock}: Set {config.get('env_var', 'environment variable')} to false\n"

            raise RuntimeError(error_msg)

    logger.warning(f"🔧 Running with {len(active)} mock(s) active in {env} environment")


def get_mock_status(mock_name: str) -> bool:
    """
    Check if a specific mock is enabled.

    Args:
        mock_name: Name of mock in ACTIVE_MOCKS registry

    Returns:
        True if mock is enabled, False otherwise

    Examples:
        >>> if get_mock_status('aurora_queries'):
        ...     return MOCK_DATA
        >>> return real_aurora_query()
    """
    if mock_name not in ACTIVE_MOCKS:
        logger.warning(f"Unknown mock: {mock_name}. Add to ACTIVE_MOCKS registry.")
        return False

    return ACTIVE_MOCKS[mock_name]['enabled']
