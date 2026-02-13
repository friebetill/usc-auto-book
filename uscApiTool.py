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


DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def booking_open_day(target_day):
    """
    USC opens bookings at midnight the day after the target weekday, 2 weeks out.
    e.g. Monday class (0) opens Tuesday (1), Thursday class (3) opens Friday (4).
    """
    return (target_day + 1) % 7


def calculate_target_date(target_day, advance_days):
    """
    Calculate the target booking date for a given weekday within the booking window.

    Args:
        target_day: Day of week (0=Monday, 6=Sunday)
        advance_days: How many days ahead the booking window extends

    Returns:
        datetime for the target day on or before the advance_days boundary
    """
    today = datetime.today()
    window_end = today + timedelta(days=advance_days)

    # Find the target weekday on or before window_end
    days_past_target = (window_end.weekday() - target_day) % 7
    target_date = window_end - timedelta(days=days_past_target)

    days_ahead = (target_date - today).days
    logger.debug(
        f"Target date for {DAY_NAMES[target_day]}: "
        f"{target_date.strftime('%Y-%m-%d')} ({days_ahead} days ahead)"
    )
    return target_date


def process_booking(user_name, booking_index, booking, token, config):
    """
    Search and book a single booking job using a pre-authenticated token.

    Args:
        user_name: User display name for logging
        booking_index: 1-based index for logging
        booking: Booking dict with locationId, targetDay, filters
        token: Bearer token from login
        config: Shared config (API settings)

    Returns:
        True if booking succeeded, False otherwise
    """
    log_prefix = f"[{user_name}, Booking {booking_index}]"

    # Merge booking-specific fields into a config overlay for findClass
    booking_config = dict(config)
    booking_config.update(booking)

    target_date = calculate_target_date(
        booking['targetDay'],
        config.get('advanceDays', 14),
    )
    target_date_str = target_date.strftime('%Y-%m-%d')
    day_name = DAY_NAMES[booking['targetDay']]

    logger.info(f"{log_prefix} --- Booking {booking_index} ---")
    logger.info(f"{log_prefix} Target: {target_date_str} ({day_name})")
    logger.info(f"{log_prefix} Location ID: {booking['locationId']}")

    # Log active filters
    filters = []
    if booking.get('classTitleFilter'):
        filters.append(f"title='{booking['classTitleFilter']}'")
    if booking.get('instructorFilter'):
        filters.append(f"instructor='{booking['instructorFilter']}'")
    if booking.get('timeRangeStart'):
        filters.append(f"after={booking['timeRangeStart']}")
    if booking.get('timeRangeEnd'):
        filters.append(f"before={booking['timeRangeEnd']}")

    if filters:
        logger.info(f"{log_prefix} Filters: {', '.join(filters)}")

    # Polling loop with max duration
    class_id = None
    poll_interval = config['pollInterval']
    max_poll_hours = config.get('maxPollHours', 5)
    deadline = datetime.now() + timedelta(hours=max_poll_hours)
    attempt = 0

    logger.info(f"{log_prefix} Polling for up to {max_poll_hours}h (until {deadline.strftime('%H:%M:%S')})")

    while datetime.now() < deadline:
        attempt += 1
        logger.info(
            f"{log_prefix} [Attempt {attempt}] "
            f"Searching at {datetime.now().strftime('%H:%M:%S')}"
        )

        try:
            class_id = usc.findClass(booking_config, date=target_date)

            if class_id is not None:
                logger.info(f"{log_prefix} Found class! Class ID: {class_id}")
                break

            logger.info(f"{log_prefix} No matching classes. Waiting {poll_interval}s...")
            time.sleep(poll_interval)

        except KeyboardInterrupt:
            raise
        except Exception as e:
            logger.error(f"{log_prefix} Error during class search: {e}", exc_info=True)
            logger.info(f"{log_prefix} Retrying in {poll_interval}s...")
            time.sleep(poll_interval)

    if class_id is None:
        logger.warning(f"{log_prefix} No class found within {max_poll_hours}h.")
        return False

    # Book with pre-authenticated token
    try:
        success = usc.bookEvent(class_id, token, config)
        if success:
            logger.info(f"{log_prefix} BOOKED class {class_id}")
            return True
        else:
            logger.error(f"{log_prefix} Booking failed for class {class_id}")
            return False

    except Exception as e:
        logger.error(f"{log_prefix} Unexpected error: {e}")
        logger.debug("Full traceback:", exc_info=True)
        return False


def process_user(user_index, user, config):
    """
    Process all due bookings for a single user.

    Args:
        user_index: 1-based user index
        user: User dict with name, email, password, bookings
        config: Shared config (API settings)

    Returns:
        list of (booking_index, success) tuples, or empty list if nothing due / login failed
    """
    user_name = user['name']
    today_weekday = datetime.today().weekday()

    logger.info(f"[{user_name}] Processing bookings...")

    # Filter to bookings that open today
    due = [
        (i, b) for i, b in enumerate(user['bookings'], 1)
        if booking_open_day(b['targetDay']) == today_weekday
    ]

    if not due:
        logger.info(f"[{user_name}] No bookings due today.")
        for i, b in enumerate(user['bookings'], 1):
            open_day = DAY_NAMES[booking_open_day(b['targetDay'])]
            logger.info(f"  [{user_name}] Booking {i} ({DAY_NAMES[b['targetDay']]} class) opens on {open_day}")
        return []

    logger.info(f"[{user_name}] {len(due)} booking(s) due today:")
    for idx, b in due:
        logger.info(f"  [{user_name}] Booking {idx}: {DAY_NAMES[b['targetDay']]} class at location {b['locationId']}")

    # Login once for this user
    try:
        token = usc.login(config, email=user['email'], password=user['password'])
    except Exception as e:
        logger.error(f"[{user_name}] Login failed with exception: {e}")
        token = None

    if token is None:
        logger.error(f"[{user_name}] Login failed. Skipping all bookings for this user.")
        return [(idx, False) for idx, _ in due]

    # Process each due booking
    results = []
    for idx, booking in due:
        try:
            success = process_booking(user_name, idx, booking, token, config)
            results.append((idx, success))
        except KeyboardInterrupt:
            raise

    return results


def main():
    """Main entry point — runs daily, processes only today's due bookings for all users."""
    # Load configuration (initializes logging)
    try:
        config = usc.loadConfig()
    except SystemExit:
        return 1

    logger.info("="*60)
    logger.info("USC Auto-Book Tool Started")
    logger.info("="*60)

    today_weekday = datetime.today().weekday()
    logger.info(f"Today is {DAY_NAMES[today_weekday]}")

    users = config.get('users', [])
    if not users:
        logger.error("No users configured.")
        return 1

    logger.info(f"Processing {len(users)} user(s)")

    # Process each user in order (User 1 = highest priority)
    all_results = {}  # user_name -> [(booking_idx, success)]
    for user_index, user in enumerate(users, 1):
        try:
            results = process_user(user_index, user, config)
            all_results[user['name']] = results
        except KeyboardInterrupt:
            logger.info("\n" + "="*60)
            logger.info("Interrupted by user. Exiting...")
            logger.info("="*60)
            return 130

    # Summary grouped by user
    logger.info("="*60)
    logger.info("RESULTS SUMMARY")
    any_success = False
    for user_name, results in all_results.items():
        if not results:
            logger.info(f"  [{user_name}] No bookings due today")
            continue
        for idx, success in results:
            status = "BOOKED" if success else "FAILED"
            logger.info(f"  [{user_name}] Booking {idx}: {status}")
            if success:
                any_success = True
    logger.info("="*60)

    return 0 if any_success else 1


if __name__ == "__main__":
    sys.exit(main())
