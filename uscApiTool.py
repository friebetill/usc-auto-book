#!/usr/bin/env python3
"""
USC Auto-Book Tool
Automatically books Urban Sports Club classes in advance.
"""

import uscApi as usc
import time
import sys
import logging
from datetime import datetime, timedelta

logger = logging.getLogger('usc_auto_book')


def main():
    """Main booking loop."""
    # Load configuration (initializes logging)
    try:
        config = usc.loadConfig()
    except SystemExit:
        return 1

    logger.info("="*60)
    logger.info("USC Auto-Book Tool Started")
    logger.info("="*60)

    # Calculate target date
    advance_days = config.get('advanceDays', 14)
    target_date = datetime.today() + timedelta(days=advance_days)
    target_date_str = target_date.strftime('%Y-%m-%d')

    logger.info(f"Target booking date: {target_date_str} ({advance_days} days in advance)")
    logger.info(f"Location ID: {config['locationId']}")
    logger.info(f"Poll interval: {config['pollInterval']}s")

    # Log active filters
    filters = []
    if config.get('classTitleFilter'):
        filters.append(f"title='{config['classTitleFilter']}'")
    if config.get('instructorFilter'):
        filters.append(f"instructor='{config['instructorFilter']}'")
    if config.get('timeRangeStart'):
        filters.append(f"after={config['timeRangeStart']}")
    if config.get('timeRangeEnd'):
        filters.append(f"before={config['timeRangeEnd']}")

    if filters:
        logger.info(f"Active filters: {', '.join(filters)}")
    else:
        logger.info("No filters active (will book first available class)")

    # Polling loop
    class_id = None
    poll_interval = config['pollInterval']
    deadline = target_date + timedelta(days=1)
    attempt = 0

    logger.info(f"Polling will continue until {deadline.strftime('%Y-%m-%d %H:%M:%S')}")

    while datetime.today() < deadline:
        attempt += 1
        logger.info(f"[Attempt {attempt}] Searching for classes at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            class_id = usc.findClass(config, date=target_date)

            if class_id is not None:
                logger.info(f"✓ Found class! Class ID: {class_id}")
                break

            logger.info(f"No matching classes found. Waiting {poll_interval}s before next check...")
            time.sleep(poll_interval)

        except KeyboardInterrupt:
            logger.info("\n" + "="*60)
            logger.info("Interrupted by user. Exiting...")
            logger.info("="*60)
            return 130  # Standard exit code for SIGINT
        except Exception as e:
            logger.error(f"Error during class search: {e}", exc_info=True)
            logger.info(f"Retrying in {poll_interval}s...")
            time.sleep(poll_interval)

    # Check if we found a class
    if class_id is None:
        logger.warning("="*60)
        logger.warning("Deadline reached. No suitable class found.")
        logger.warning("Possible reasons:")
        logger.warning("  - No classes available at this location/date")
        logger.warning("  - Filters too restrictive")
        logger.warning("  - Classes booked by others")
        logger.warning("="*60)
        return 1

    # Login and book
    logger.info("="*60)
    logger.info(f"Proceeding to book class {class_id}")
    logger.info("="*60)

    try:
        # Login
        token = usc.login(config)
        if token is None:
            logger.error("="*60)
            logger.error("Login failed. Cannot proceed with booking.")
            logger.error("Please check your credentials in .env file")
            logger.error("="*60)
            return 1

        # Book the class
        success = usc.bookEvent(class_id, token, config)

        if success:
            logger.info("="*60)
            logger.info("✓ BOOKING SUCCESSFUL!")
            logger.info(f"Class {class_id} has been booked.")
            logger.info("Check your USC app to confirm.")
            logger.info("="*60)
            return 0
        else:
            logger.error("="*60)
            logger.error("✗ BOOKING FAILED")
            logger.error("Check the error messages above for details.")
            logger.error("="*60)
            return 1

    except Exception as e:
        logger.error("="*60)
        logger.error(f"Unexpected error during login/booking: {e}")
        logger.error("="*60)
        logger.debug("Full traceback:", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
