#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETL Script Scheduler

Runs any Python script on a daily schedule at 4 AM Bangkok time.

Usage:
    # Run specific script
    python scheduler_wrapper.py --script path/to/fund_data_etl.py

    # Run with custom schedule
    python scheduler_wrapper.py --script path/to/script.py --time "04:00"

    # Run once immediately (testing)
    python scheduler_wrapper.py --script path/to/script.py --run-once

Requirements:
    Python 3.9+ (uses standard library only - no pip install needed)

Design Principles (from CLAUDE.md):
- Defensive programming: Validate configuration at startup
- Fail fast: Explicit error messages for missing files
- Loud logging: Clear visibility into execution
- Zero external dependencies: Uses only Python stdlib
"""

import argparse
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Timezone handling (Python 3.9+)
try:
    from zoneinfo import ZoneInfo
    BANGKOK_TZ = ZoneInfo('Asia/Bangkok')
except (ImportError, Exception):
    # Fallback: Manual UTC+7 offset
    # ImportError: Python < 3.9 (zoneinfo module missing)
    # ZoneInfoNotFoundError: Windows (tzdata package missing)
    from datetime import timezone
    BANGKOK_TZ = timezone(timedelta(hours=7))
    print("⚠️  Using manual UTC+7 offset (Bangkok timezone data not available)")
    print("   For proper timezone support: pip install tzdata")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ScriptScheduler:
    """Scheduler for running Python scripts at specified times."""

    def __init__(self, script_path: str, schedule_time: str = "04:00"):
        """Initialize scheduler.

        Args:
            script_path: Path to Python script to run
            schedule_time: Time to run in HH:MM format (Bangkok time)

        Raises:
            ValueError: If script doesn't exist or time format invalid
        """
        # Defensive: Validate at startup (not on first use)
        self.script_path = self._validate_script_path(script_path)
        self.schedule_time = self._validate_time_format(schedule_time)
        self.python_executable = sys.executable

        logger.info("=" * 80)
        logger.info("[SCHEDULER] ETL Script Scheduler Initialized")
        logger.info("=" * 80)
        logger.info(f"Script: {self.script_path}")
        logger.info(f"Schedule: {self.schedule_time} Bangkok time (UTC+7)")
        logger.info(f"Python: {self.python_executable}")
        logger.info(f"Timezone: {BANGKOK_TZ}")
        logger.info("=" * 80)

    def _validate_script_path(self, script_path: str) -> Path:
        """Validate script exists and is a Python file.

        Defensive programming: Fail fast at startup if script missing.

        Args:
            script_path: Path to script

        Returns:
            Absolute Path to script

        Raises:
            ValueError: If script doesn't exist or isn't .py file
        """
        path = Path(script_path).resolve()

        if not path.exists():
            raise ValueError(
                f"Script not found: {script_path}\n"
                f"Absolute path checked: {path}\n"
                f"Current directory: {os.getcwd()}"
            )

        if not path.suffix == '.py':
            raise ValueError(
                f"Script must be a Python file (.py): {script_path}\n"
                f"Got: {path.suffix}"
            )

        return path

    def _validate_time_format(self, time_str: str) -> str:
        """Validate time format is HH:MM.

        Args:
            time_str: Time string

        Returns:
            Validated time string

        Raises:
            ValueError: If format invalid
        """
        try:
            datetime.strptime(time_str, "%H:%M")
            return time_str
        except ValueError as e:
            raise ValueError(
                f"Invalid time format: {time_str}\n"
                f"Expected format: HH:MM (e.g., '04:00')\n"
                f"Error: {e}"
            )

    def run_script(self) -> bool:
        """Execute the scheduled script.

        Returns:
            True if script succeeded, False otherwise
        """
        bangkok_now = datetime.now(BANGKOK_TZ)
        logger.info("=" * 80)
        logger.info(f"[EXECUTE] Starting scheduled execution at {bangkok_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info("=" * 80)

        start_time = time.time()

        try:
            # Run script as subprocess for isolation
            result = subprocess.run(
                [self.python_executable, str(self.script_path)],
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )

            duration = time.time() - start_time

            # Log output
            if result.stdout:
                logger.info("Script output:")
                logger.info(result.stdout)

            if result.stderr:
                logger.warning("Script stderr:")
                logger.warning(result.stderr)

            # Check exit code
            if result.returncode == 0:
                logger.info("=" * 80)
                logger.info(f"[SUCCESS] Script completed successfully in {duration:.2f}s")
                logger.info("=" * 80)
                return True
            else:
                logger.error("=" * 80)
                logger.error(f"[FAILED] Script failed with exit code {result.returncode}")
                logger.error(f"Duration: {duration:.2f}s")
                logger.error("=" * 80)
                return False

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            logger.error("=" * 80)
            logger.error(f"[TIMEOUT] Script timeout after {duration:.2f}s (limit: 3600s)")
            logger.error("=" * 80)
            return False

        except Exception as e:
            duration = time.time() - start_time
            logger.error("=" * 80)
            logger.error(f"[ERROR] Unexpected error running script: {e}")
            logger.error(f"Duration: {duration:.2f}s")
            logger.error("=" * 80)
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _calculate_next_run(self) -> datetime:
        """Calculate next run time in Bangkok timezone.

        Returns:
            datetime object of next scheduled run
        """
        # Get current time in Bangkok timezone
        now = datetime.now(BANGKOK_TZ)

        # Parse target time
        target_hour, target_minute = map(int, self.schedule_time.split(':'))

        # Create target datetime for today
        next_run = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

        # If target time already passed today, schedule for tomorrow
        if next_run <= now:
            next_run += timedelta(days=1)

        return next_run

    def schedule_daily(self):
        """Schedule script to run daily at specified time (Bangkok time).

        Uses manual scheduling with sleep - no external dependencies.
        """
        logger.info(f"[SCHEDULE] Running daily at {self.schedule_time} Bangkok time")
        logger.info("[RUNNING] Scheduler is now running. Press Ctrl+C to stop.")
        logger.info("")

        try:
            while True:
                # Calculate next run time
                next_run = self._calculate_next_run()
                now = datetime.now(BANGKOK_TZ)
                time_until = next_run - now

                hours = int(time_until.total_seconds() // 3600)
                minutes = int((time_until.total_seconds() % 3600) // 60)

                logger.info(
                    f"[WAITING] Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')} | "
                    f"Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S')} | "
                    f"In: {hours}h {minutes}m"
                )

                # Sleep until next run time
                sleep_seconds = time_until.total_seconds()

                # Wake up periodically to log progress (every 10 minutes)
                while sleep_seconds > 0:
                    if sleep_seconds > 600:  # More than 10 minutes left
                        time.sleep(600)  # Sleep 10 minutes
                        sleep_seconds -= 600

                        # Log progress
                        now = datetime.now(BANGKOK_TZ)
                        time_until = next_run - now
                        hours = int(time_until.total_seconds() // 3600)
                        minutes = int((time_until.total_seconds() % 3600) // 60)
                        logger.info(
                            f"[WAITING] Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')} | "
                            f"Next run in: {hours}h {minutes}m"
                        )
                    else:
                        # Final sleep
                        time.sleep(sleep_seconds)
                        sleep_seconds = 0

                # Time to run the script
                self.run_script()

        except KeyboardInterrupt:
            logger.info("")
            logger.info("=" * 80)
            logger.info("[STOPPED] Scheduler stopped by user")
            logger.info("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Schedule Python scripts to run at specific times (Bangkok timezone)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Schedule fund_data ETL to run at 4 AM daily
  python scheduler_wrapper.py --script ../src/data/etl/fund_data_sync.py

  # Custom time (6:30 AM)
  python scheduler_wrapper.py --script my_script.py --time "06:30"

  # Run once immediately (testing)
  python scheduler_wrapper.py --script my_script.py --run-once

Notes:
  - All times are in Bangkok timezone (UTC+7)
  - Script runs in a subprocess (isolated from scheduler)
  - Logs to both scheduler.log and console
  - Press Ctrl+C to stop the scheduler
  - Zero external dependencies - uses only Python stdlib (3.9+)
        """
    )

    parser.add_argument(
        '--script',
        required=True,
        help='Path to Python script to run'
    )

    parser.add_argument(
        '--time',
        default='04:00',
        help='Time to run in HH:MM format (Bangkok time). Default: 04:00'
    )

    parser.add_argument(
        '--run-once',
        action='store_true',
        help='Run script once immediately and exit (for testing)'
    )

    args = parser.parse_args()

    try:
        # Initialize scheduler (validates script at startup)
        scheduler = ScriptScheduler(
            script_path=args.script,
            schedule_time=args.time
        )

        if args.run_once:
            # Test mode: run once and exit
            logger.info("[TEST] Test mode: Running script once")
            success = scheduler.run_script()
            sys.exit(0 if success else 1)
        else:
            # Production mode: schedule and run forever
            scheduler.schedule_daily()

    except ValueError as e:
        logger.error("=" * 80)
        logger.error("[CONFIG ERROR] Configuration Error")
        logger.error("=" * 80)
        logger.error(str(e))
        logger.error("=" * 80)
        sys.exit(1)

    except Exception as e:
        logger.error("=" * 80)
        logger.error("[UNEXPECTED ERROR] Unexpected Error")
        logger.error("=" * 80)
        logger.error(str(e))
        logger.error("=" * 80)
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
