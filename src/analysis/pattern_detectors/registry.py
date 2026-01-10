# -*- coding: utf-8 -*-
"""
Pattern Detector Registry

Registry pattern for managing multiple pattern detection implementations.
Allows selection between external libraries (stock-pattern) and custom
implementations at runtime.

Usage:
    # Register implementations
    registry = PatternDetectorRegistry()
    registry.register('bullish_flag', 'stock_pattern', stock_pattern_detector, priority=10)
    registry.register('bullish_flag', 'custom', custom_detector, priority=5)

    # Get preferred implementation
    detector = registry.get('bullish_flag')  # Returns highest priority

    # Get specific implementation
    detector = registry.get('bullish_flag', impl_name='custom')

    # List available implementations
    impls = registry.list_implementations('bullish_flag')
    # Returns: [('stock_pattern', 10), ('custom', 5)]

Follows:
- Principle #1: Defensive Programming (validate inputs, fail fast)
- Principle #14: Centralization (single registry for all pattern detectors)
- Principle #18: Logging Discipline (narrative logging)
"""

import logging
from typing import Callable, Dict, List, Optional, Tuple, Any
from abc import ABC, abstractmethod
import pandas as pd

logger = logging.getLogger(__name__)


class PatternDetectorInterface(ABC):
    """
    Abstract interface for pattern detectors.

    All pattern detector implementations must implement this interface
    to be registered in the registry.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Implementation name (e.g., 'stock_pattern', 'custom', 'ta_lib')"""
        ...

    @property
    @abstractmethod
    def supported_patterns(self) -> List[str]:
        """List of pattern types this detector can detect"""
        ...

    @abstractmethod
    def detect(
        self,
        pattern_type: str,
        ticker: str,
        df: pd.DataFrame,
        pivots: pd.DataFrame,
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Detect a specific pattern type.

        Args:
            pattern_type: Type of pattern to detect (e.g., 'bullish_flag')
            ticker: Stock ticker symbol
            df: OHLC DataFrame
            pivots: Pivot points DataFrame
            config: Detection configuration

        Returns:
            Pattern data dict if detected, None otherwise
        """
        ...

    def is_available(self) -> bool:
        """Check if this detector is available (dependencies installed)"""
        return True


class PatternDetectorRegistry:
    """
    Registry for pattern detection implementations.

    Supports:
    - Multiple implementations per pattern type
    - Priority-based selection (highest priority = preferred)
    - Graceful fallback when preferred implementation unavailable
    - Runtime registration of new implementations
    """

    def __init__(self):
        # {pattern_type: [(priority, impl_name, detector)]}
        self._detectors: Dict[str, List[Tuple[int, str, PatternDetectorInterface]]] = {}
        self._default_impl: Dict[str, str] = {}  # {pattern_type: impl_name}

    def register(
        self,
        pattern_type: str,
        detector: PatternDetectorInterface,
        priority: int = 0
    ) -> None:
        """
        Register a pattern detector implementation.

        Args:
            pattern_type: Type of pattern (e.g., 'bullish_flag', 'head_shoulders')
            detector: Detector implementing PatternDetectorInterface
            priority: Higher = preferred (default: 0)

        Raises:
            ValueError: If detector doesn't support the pattern type
        """
        # Defensive validation (Principle #1)
        if pattern_type not in detector.supported_patterns:
            raise ValueError(
                f"Detector '{detector.name}' doesn't support pattern type '{pattern_type}'. "
                f"Supported: {detector.supported_patterns}"
            )

        if pattern_type not in self._detectors:
            self._detectors[pattern_type] = []

        # Check for duplicate registration
        existing = [d for d in self._detectors[pattern_type] if d[1] == detector.name]
        if existing:
            logger.warning(
                f"Detector '{detector.name}' already registered for '{pattern_type}'. "
                f"Updating priority: {existing[0][0]} -> {priority}"
            )
            self._detectors[pattern_type] = [
                d for d in self._detectors[pattern_type] if d[1] != detector.name
            ]

        self._detectors[pattern_type].append((priority, detector.name, detector))
        # Sort by priority (highest first)
        self._detectors[pattern_type].sort(key=lambda x: -x[0])

        logger.debug(
            f"Registered detector '{detector.name}' for '{pattern_type}' "
            f"(priority: {priority})"
        )

    def register_detector(self, detector: PatternDetectorInterface, priority: int = 0) -> None:
        """
        Register a detector for all its supported pattern types.

        Args:
            detector: Detector implementing PatternDetectorInterface
            priority: Higher = preferred (default: 0)
        """
        for pattern_type in detector.supported_patterns:
            self.register(pattern_type, detector, priority)

        logger.info(
            f"Registered detector '{detector.name}' for {len(detector.supported_patterns)} "
            f"pattern types (priority: {priority})"
        )

    def set_default(self, pattern_type: str, impl_name: str) -> None:
        """
        Set default implementation for a pattern type.

        Args:
            pattern_type: Pattern type
            impl_name: Implementation name to use as default

        Raises:
            ValueError: If implementation not registered
        """
        if pattern_type not in self._detectors:
            raise ValueError(f"No detectors registered for pattern type '{pattern_type}'")

        impl_names = [d[1] for d in self._detectors[pattern_type]]
        if impl_name not in impl_names:
            raise ValueError(
                f"Implementation '{impl_name}' not registered for '{pattern_type}'. "
                f"Available: {impl_names}"
            )

        self._default_impl[pattern_type] = impl_name
        logger.info(f"Set default implementation for '{pattern_type}': {impl_name}")

    def get(
        self,
        pattern_type: str,
        impl_name: Optional[str] = None
    ) -> Optional[PatternDetectorInterface]:
        """
        Get detector for a pattern type.

        Args:
            pattern_type: Pattern type to detect
            impl_name: Specific implementation (None = use priority/default)

        Returns:
            PatternDetectorInterface or None if not found

        Selection order:
        1. If impl_name specified, return that implementation
        2. If default set for pattern_type, return default
        3. Return highest priority available implementation
        """
        if pattern_type not in self._detectors:
            logger.warning(f"No detectors registered for pattern type '{pattern_type}'")
            return None

        detectors = self._detectors[pattern_type]

        # Specific implementation requested
        if impl_name:
            for _, name, detector in detectors:
                if name == impl_name:
                    if detector.is_available():
                        return detector
                    else:
                        logger.warning(
                            f"Requested implementation '{impl_name}' not available"
                        )
                        return None
            logger.warning(f"Implementation '{impl_name}' not found for '{pattern_type}'")
            return None

        # Check default
        if pattern_type in self._default_impl:
            default_name = self._default_impl[pattern_type]
            for _, name, detector in detectors:
                if name == default_name and detector.is_available():
                    return detector

        # Return highest priority available
        for _, name, detector in detectors:
            if detector.is_available():
                return detector

        logger.warning(f"No available detectors for pattern type '{pattern_type}'")
        return None

    def detect(
        self,
        pattern_type: str,
        ticker: str,
        df: pd.DataFrame,
        pivots: pd.DataFrame,
        config: Dict[str, Any],
        impl_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Detect a pattern using registered detector.

        Args:
            pattern_type: Type of pattern to detect
            ticker: Stock ticker symbol
            df: OHLC DataFrame
            pivots: Pivot points DataFrame
            config: Detection configuration
            impl_name: Specific implementation (None = auto-select)

        Returns:
            Pattern data dict with 'implementation' field added, or None
        """
        detector = self.get(pattern_type, impl_name)
        if not detector:
            return None

        try:
            result = detector.detect(pattern_type, ticker, df, pivots, config)
            if result:
                result['implementation'] = detector.name
            return result
        except Exception as e:
            logger.error(
                f"Detector '{detector.name}' failed for '{pattern_type}': {e}",
                exc_info=True
            )
            return None

    def detect_with_fallback(
        self,
        pattern_type: str,
        ticker: str,
        df: pd.DataFrame,
        pivots: pd.DataFrame,
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Detect pattern, falling back through implementations on failure.

        Tries each registered implementation in priority order until one succeeds.

        Args:
            pattern_type: Type of pattern to detect
            ticker: Stock ticker symbol
            df: OHLC DataFrame
            pivots: Pivot points DataFrame
            config: Detection configuration

        Returns:
            Pattern data dict with 'implementation' field, or None if all fail
        """
        if pattern_type not in self._detectors:
            return None

        for priority, name, detector in self._detectors[pattern_type]:
            if not detector.is_available():
                logger.debug(f"Skipping unavailable detector '{name}'")
                continue

            try:
                result = detector.detect(pattern_type, ticker, df, pivots, config)
                if result:
                    result['implementation'] = name
                    logger.debug(f"Pattern detected by '{name}' (priority: {priority})")
                    return result
            except Exception as e:
                logger.warning(f"Detector '{name}' failed, trying next: {e}")
                continue

        return None

    def list_implementations(self, pattern_type: str) -> List[Tuple[str, int, bool]]:
        """
        List registered implementations for a pattern type.

        Args:
            pattern_type: Pattern type

        Returns:
            List of (impl_name, priority, is_available) tuples, sorted by priority
        """
        if pattern_type not in self._detectors:
            return []

        return [
            (name, priority, detector.is_available())
            for priority, name, detector in self._detectors[pattern_type]
        ]

    def list_pattern_types(self) -> List[str]:
        """List all registered pattern types."""
        return list(self._detectors.keys())

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        total_detectors = sum(len(d) for d in self._detectors.values())
        available_detectors = sum(
            sum(1 for _, _, det in dets if det.is_available())
            for dets in self._detectors.values()
        )

        return {
            'pattern_types': len(self._detectors),
            'total_implementations': total_detectors,
            'available_implementations': available_detectors,
            'patterns': {
                pt: {
                    'implementations': len(dets),
                    'available': sum(1 for _, _, d in dets if d.is_available()),
                    'default': self._default_impl.get(pt)
                }
                for pt, dets in self._detectors.items()
            }
        }


# Singleton instance
_registry: Optional[PatternDetectorRegistry] = None


def get_pattern_registry() -> PatternDetectorRegistry:
    """Get or create singleton pattern detector registry."""
    global _registry
    if _registry is None:
        _registry = PatternDetectorRegistry()
    return _registry
