import cloudscraper
import os
import sys
import time
import logging
import configparser
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import requests  # Keep for exception types


# ============================================================
# Logging Setup
# ============================================================

def setup_logging(log_level: str = 'INFO', log_file: Optional[str] = None):
    """
    Configure logging with both console and optional file output.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional path to log file
    """
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    handlers = [logging.StreamHandler()]

    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format=log_format,
        handlers=handlers,
        force=True  # Override any existing configuration
    )


logger = logging.getLogger('usc_auto_book')

# Global cloudscraper session for Cloudflare bypass
_scraper = None

def get_scraper():
    """Get or create a cloudscraper session."""
    global _scraper
    if _scraper is None:
        _scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'android',
                'mobile': True
            }
        )
    return _scraper


# ============================================================
# Retry Decorator
# ============================================================

def retry_on_failure(max_retries=3, backoff_factor=2, retry_on=(requests.exceptions.RequestException,)):
    """
    Decorator to retry functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff (seconds)
        retry_on: Tuple of exceptions to retry on
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    if attempt == max_retries:
                        logger.error(f"{func.__name__} failed after {max_retries} retries: {e}")
                        raise

                    wait_time = backoff_factor ** attempt
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)

        return wrapper
    return decorator


# ============================================================
# Configuration Loading
# ============================================================

def loadConfigLegacy(config_name='usc_api.config'):
    """
    DEPRECATED: Load configuration from legacy config file.
    This function is kept for backward compatibility.
    Please migrate to .env file (see .env.example).
    """
    logger.warning("="*60)
    logger.warning("DEPRECATION WARNING:")
    logger.warning("Using legacy usc_api.config file is deprecated!")
    logger.warning("Please migrate to .env file for better security.")
    logger.warning("See .env.example for template.")
    logger.warning("="*60)

    config = configparser.ConfigParser()
    config.readfp(open(config_name))
    return {
        'email':         config.get('Credentials', 'email'),
        'password':      config.get('Credentials', 'password'),
        'clientSecret':  config.get('Client', 'secret'),
        'clientId':      config.get('Client', 'id'),
        'baseURL':       config.get('API', 'baseURL'),
        'headers': {
            'accept-encoding':  config.get('Headers', 'accept-encoding'),
            'user-agent':       config.get('Headers', 'user-agent'),
            'accept-language':  config.get('Headers', 'accept-language'),
        },
        # Legacy mode - use hardcoded defaults for new settings
        'locationId': 15238,
        'advanceDays': 14,
        'pollInterval': 1800,
        'classTitleFilter': '',
        'instructorFilter': '',
        'timeRangeStart': '',
        'timeRangeEnd': '',
    }


def _parse_bookings(prefix, primary_location_id, primary_target_day,
                     primary_class_filter, primary_instructor_filter,
                     primary_time_start, primary_time_end):
    """
    Parse bookings for a user from environment variables.

    The first booking comes from the primary_* parameters.
    Additional bookings are parsed from {prefix}BOOKING_N_* env vars (N=2,3,...).

    Args:
        prefix: Env var prefix, e.g. 'USC_' for User 1 or 'USC_USER_2_' for User 2
        primary_location_id: Location ID for the first booking
        primary_target_day: Target day for the first booking
        primary_class_filter: Class title filter for the first booking
        primary_instructor_filter: Instructor filter for the first booking
        primary_time_start: Time range start for the first booking
        primary_time_end: Time range end for the first booking

    Returns:
        list: List of booking dicts
    """
    booking1 = {
        'locationId': int(primary_location_id),
        'targetDay': int(primary_target_day),
        'classTitleFilter': primary_class_filter,
        'instructorFilter': primary_instructor_filter,
        'timeRangeStart': primary_time_start,
        'timeRangeEnd': primary_time_end,
    }
    bookings = [booking1]

    n = 2
    while True:
        booking_prefix = f'{prefix}BOOKING_{n}_'
        loc_id = os.getenv(f'{booking_prefix}LOCATION_ID')
        if loc_id is None:
            break
        bookings.append({
            'locationId': int(loc_id),
            'targetDay': int(os.getenv(f'{booking_prefix}TARGET_DAY', '0')),
            'classTitleFilter': os.getenv(f'{booking_prefix}CLASS_TITLE_FILTER', '').strip(),
            'instructorFilter': os.getenv(f'{booking_prefix}INSTRUCTOR_FILTER', '').strip(),
            'timeRangeStart': os.getenv(f'{booking_prefix}TIME_RANGE_START', '').strip(),
            'timeRangeEnd': os.getenv(f'{booking_prefix}TIME_RANGE_END', '').strip(),
        })
        n += 1

    return bookings


def loadConfig():
    """
    Load configuration from environment variables.
    Falls back to .env file if environment variables not set.
    Falls back to legacy usc_api.config if .env doesn't exist.

    Supports multiple users:
    - User 1: existing USC_EMAIL, USC_PASSWORD, USC_LOCATION_ID, etc.
    - User N (N=2,3,...): USC_USER_N_EMAIL, USC_USER_N_PASSWORD, etc.

    Returns:
        dict: Configuration dictionary with shared settings and 'users' list

    Raises:
        SystemExit: If required environment variables are missing
    """
    # Load from .env file (if exists)
    load_dotenv()

    # Check if we should use legacy config (for backward compatibility)
    if not os.path.exists('.env') and not os.getenv('USC_EMAIL') and os.path.exists('usc_api.config'):
        config = loadConfigLegacy()
        # Still setup logging even in legacy mode
        log_level = os.getenv('USC_LOG_LEVEL', 'INFO')
        log_file = os.getenv('USC_LOG_FILE', '')
        setup_logging(log_level, log_file if log_file else None)
        # Wrap legacy config into multi-user format
        config['users'] = [{
            'name': 'User 1',
            'email': config['email'],
            'password': config['password'],
            'bookings': config.get('bookings', []),
        }]
        return config

    # Required variables for User 1
    required_vars = ['USC_EMAIL', 'USC_PASSWORD', 'USC_LOCATION_ID']
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        print(f"ERROR: Missing required environment variables: {', '.join(missing)}")
        print("Please create a .env file based on .env.example")
        print("\nQuick start:")
        print("  1. cp .env.example .env")
        print("  2. Edit .env and set your credentials")
        print("  3. Run the script again")
        sys.exit(1)

    # Setup logging first
    log_level = os.getenv('USC_LOG_LEVEL', 'INFO')
    log_file = os.getenv('USC_LOG_FILE', '')
    setup_logging(log_level, log_file if log_file else None)

    # Build shared configuration dictionary
    config = {
        'clientId': os.getenv('USC_CLIENT_ID', '86093282310'),
        'clientSecret': os.getenv('USC_CLIENT_SECRET',
                                 '1BJX3V5HWUYVCZ77S1TY9L1PSWAXA3K95ZMUC3ZRBAP3M696ZF4SD3QW5VBNU81H'),
        'baseURL': os.getenv('USC_API_BASE_URL',
                            'https://api.urbansportsclub.com/api/v6'),
        'headers': {
            'accept-encoding': os.getenv('USC_ACCEPT_ENCODING', 'gzip, deflate'),
            'user-agent': os.getenv('USC_USER_AGENT',
                                   'USCAPP/4.0.8 (android; 28; Scale/2.75)'),
            'accept-language': os.getenv('USC_ACCEPT_LANGUAGE', 'en-US;q=1.0'),
        },
        'advanceDays': int(os.getenv('USC_ADVANCE_DAYS', '14')),
        'pollInterval': int(os.getenv('USC_POLL_INTERVAL', '1800')),
        'maxPollHours': int(os.getenv('USC_MAX_POLL_HOURS', '5')),
    }

    # --- Build users list ---
    users = []

    # User 1: from existing USC_* env vars
    user1_bookings = _parse_bookings(
        prefix='USC_',
        primary_location_id=os.getenv('USC_LOCATION_ID'),
        primary_target_day=os.getenv('USC_TARGET_DAY', '0'),
        primary_class_filter=os.getenv('USC_CLASS_TITLE_FILTER', '').strip(),
        primary_instructor_filter=os.getenv('USC_INSTRUCTOR_FILTER', '').strip(),
        primary_time_start=os.getenv('USC_TIME_RANGE_START', '').strip(),
        primary_time_end=os.getenv('USC_TIME_RANGE_END', '').strip(),
    )
    users.append({
        'name': os.getenv('USC_USER_1_NAME', 'User 1'),
        'email': os.getenv('USC_EMAIL'),
        'password': os.getenv('USC_PASSWORD'),
        'bookings': user1_bookings,
    })

    # User N (N=2,3,...): from USC_USER_N_* env vars
    n = 2
    while True:
        user_prefix = f'USC_USER_{n}_'
        email = os.getenv(f'{user_prefix}EMAIL')
        if email is None:
            break

        password = os.getenv(f'{user_prefix}PASSWORD')
        if password is None:
            logger.error(f"USC_USER_{n}_EMAIL is set but USC_USER_{n}_PASSWORD is missing. Skipping user {n}.")
            n += 1
            continue

        location_id = os.getenv(f'{user_prefix}LOCATION_ID')
        if location_id is None:
            logger.error(f"USC_USER_{n}_EMAIL is set but USC_USER_{n}_LOCATION_ID is missing. Skipping user {n}.")
            n += 1
            continue

        user_bookings = _parse_bookings(
            prefix=user_prefix,
            primary_location_id=location_id,
            primary_target_day=os.getenv(f'{user_prefix}TARGET_DAY', '0'),
            primary_class_filter=os.getenv(f'{user_prefix}CLASS_TITLE_FILTER', '').strip(),
            primary_instructor_filter=os.getenv(f'{user_prefix}INSTRUCTOR_FILTER', '').strip(),
            primary_time_start=os.getenv(f'{user_prefix}TIME_RANGE_START', '').strip(),
            primary_time_end=os.getenv(f'{user_prefix}TIME_RANGE_END', '').strip(),
        )

        users.append({
            'name': os.getenv(f'{user_prefix}NAME', f'User {n}'),
            'email': email,
            'password': password,
            'bookings': user_bookings,
        })
        n += 1

    config['users'] = users

    logger.info("Configuration loaded successfully")
    logger.debug(f"API Base URL: {config['baseURL']}")
    logger.info(f"Configured {len(users)} user(s)")

    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for user in users:
        logger.info(f"  {user['name']}: {len(user['bookings'])} booking(s)")
        for i, b in enumerate(user['bookings'], 1):
            logger.debug(
                f"    Booking {i}: location={b['locationId']}, "
                f"day={day_names[b['targetDay']]}, "
                f"filter='{b['classTitleFilter']}'"
            )

    return config


# ============================================================
# API Functions
# ============================================================

@retry_on_failure(max_retries=3)
def login(config: Dict[str, Any], email: Optional[str] = None,
          password: Optional[str] = None) -> Optional[str]:
    """
    Login with OAuth2 password grant.

    Args:
        config: Configuration dictionary (shared settings)
        email: User email (if None, falls back to config['email'] for legacy compat)
        password: User password (if None, falls back to config['password'])

    Returns:
        Bearer token if successful, None otherwise

    Raises:
        requests.exceptions.RequestException: On network errors after retries
    """
    login_email = email or config.get('email')
    login_password = password or config.get('password')

    request_url = config['baseURL'] + '/auth/token'

    data = {
        'username': login_email,
        'password': login_password,
        'client_secret': config['clientSecret'],
        'client_id': config['clientId'],
        'grant_type': 'password'
    }

    logger.info(f"Logging in as {login_email}")
    logger.debug(f"POST: {request_url}")

    try:
        scraper = get_scraper()
        response = scraper.post(request_url, data=data, headers=config['headers'], timeout=30)

        if response.status_code == 200:
            token = response.json()['data']['access_token']
            logger.info("Login successful")
            return token
        elif response.status_code == 401:
            logger.error("Login failed: Invalid credentials")
            logger.debug(f"Response: {response.text}")
            return None
        elif response.status_code == 403:
            logger.error("Login failed: Access forbidden (check client credentials)")
            logger.debug(f"Response: {response.text}")
            return None
        elif response.status_code == 429:
            logger.error("Login failed: Rate limited. Wait before retrying.")
            return None
        else:
            logger.error(f"Login failed with status {response.status_code}")
            logger.debug(f"Response: {response.text}")
            return None

    except requests.exceptions.Timeout:
        logger.error("Login request timed out")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Login request failed: {e}")
        raise


def is_bookable(course: Dict[str, Any]) -> bool:
    """Check if a course is bookable."""
    return course['bookable'] != 0 and course['freeSpots'] != 0


def matches_filters(cls: Dict[str, Any], config: Dict[str, Any]) -> bool:
    """
    Check if a class matches configured filters.

    Args:
        cls: Class object from API
        config: Configuration with filter settings

    Returns:
        True if class matches all filters (or no filters set)
    """
    # Title filter (case-insensitive substring match)
    title_filter = config.get('classTitleFilter', '').strip()
    if title_filter:
        class_title = cls.get('title', '').lower()
        if title_filter.lower() not in class_title:
            logger.debug(f"Class '{cls['title']}' filtered out by title filter")
            return False

    # Instructor filter (case-insensitive substring match)
    instructor_filter = config.get('instructorFilter', '').strip()
    if instructor_filter:
        # Instructor might be in different fields depending on API version
        instructor = cls.get('instructor', cls.get('instructorName', '')).lower()
        if instructor_filter.lower() not in instructor:
            logger.debug(f"Class '{cls['title']}' filtered out by instructor filter")
            return False

    # Time range filter
    time_start = config.get('timeRangeStart', '').strip()
    time_end = config.get('timeRangeEnd', '').strip()

    if time_start or time_end:
        # Parse class start time (format: ISO 8601)
        try:
            class_time_str = cls.get('startDateTimeUTC', cls.get('startDateTime', ''))
            # Handle ISO 8601 format with or without Z
            class_time_str = class_time_str.replace('Z', '+00:00')
            class_time = datetime.fromisoformat(class_time_str)
            class_hour_min = class_time.strftime('%H:%M')

            if time_start and class_hour_min < time_start:
                logger.debug(
                    f"Class '{cls['title']}' at {class_hour_min} "
                    f"filtered out (before {time_start})"
                )
                return False

            if time_end and class_hour_min > time_end:
                logger.debug(
                    f"Class '{cls['title']}' at {class_hour_min} "
                    f"filtered out (after {time_end})"
                )
                return False

        except (ValueError, KeyError) as e:
            logger.warning(f"Could not parse time for filtering: {e}")
            # Don't filter out if we can't parse time

    return True


@retry_on_failure(max_retries=3)
def findClass(config: Dict[str, Any], date: Optional[datetime] = None) -> Optional[int]:
    """
    Find a bookable class on the given date.

    Args:
        config: Configuration dictionary
        date: Target date (defaults to config['advanceDays'] from today)

    Returns:
        Class ID if bookable class found, None otherwise
    """
    if date is None:
        advance_days = config.get('advanceDays', 14)
        date = datetime.today() + timedelta(days=advance_days)

    str_date = date.strftime('%Y-%m-%d')
    location_id = config['locationId']

    # Fixed: Remove duplicate 'courses?' in URL (bug from original code)
    request_url = (
        f"{config['baseURL']}/courses?"
        f"forDurationOfDays=1&query=&pageSize=100&page=1&"
        f"locationId={location_id}&startDate={str_date}"
    )

    logger.info(f"Searching for classes at location {location_id} on {str_date}")
    logger.debug(f"GET: {request_url}")

    try:
        scraper = get_scraper()
        response = scraper.get(request_url, headers=config['headers'], timeout=30)

        if response.status_code != 200:
            logger.error(f"Failed to fetch classes (status {response.status_code})")
            logger.debug(f"Response: {response.text[:500]}")
            return None

        data = response.json()['data']
        classes = data.get('classes', [])

        if not classes:
            logger.info(f"No classes found on {str_date}")
            return None

        logger.info(f"Found {len(classes)} classes")

        # Find first bookable class that matches filters
        for cls in classes:
            if is_bookable(cls) and matches_filters(cls, config):
                logger.info(
                    f"Found bookable class matching filters: '{cls['title']}' "
                    f"(ID: {cls['id']}) at {cls.get('startDateTimeUTC', 'N/A')}"
                )
                logger.debug(
                    f"Class details - Spots: {cls['freeSpots']}/{cls['maximumNumber']}, "
                    f"Bookable: {cls['bookable']}"
                )
                return cls['id']

        # Log why classes aren't bookable or don't match filters
        logger.warning("No bookable classes matching filters found. Sample classes:")
        for cls in classes[:3]:  # Log first 3
            bookable_status = "✓" if is_bookable(cls) else "✗"
            filter_status = "✓" if matches_filters(cls, config) else "✗"
            logger.debug(
                f"  [{bookable_status} bookable, {filter_status} filters] '{cls['title']}': "
                f"spots={cls['freeSpots']}/{cls['maximumNumber']}, "
                f"bookable={cls['bookable']}"
            )

        return None

    except requests.exceptions.Timeout:
        logger.error("Request timed out while fetching classes")
        raise
    except (KeyError, ValueError) as e:
        logger.error(f"Unexpected API response structure: {e}")
        logger.debug(f"Response: {response.text[:500] if 'response' in locals() else 'N/A'}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch classes: {e}")
        raise


@retry_on_failure(max_retries=2)  # Fewer retries for booking to avoid double-booking
def bookEvent(class_id: int, bearer: str, config: Dict[str, Any]) -> bool:
    """
    Book a class.

    Args:
        class_id: ID of class to book
        bearer: Bearer token from login
        config: Configuration dictionary

    Returns:
        True if booking successful, False otherwise
    """
    request_url = config['baseURL'] + '/bookings'

    data = {'courseId': class_id}
    headers = config['headers'].copy()
    headers['authorization'] = f'Bearer {bearer}'

    logger.info(f"Attempting to book class {class_id}")
    logger.debug(f"POST: {request_url}")

    try:
        scraper = get_scraper()
        response = scraper.post(request_url, data=data, headers=headers, timeout=30)

        if response.status_code == 200:
            booking_id = response.json()['data']['id']
            logger.info(f"Successfully booked class {class_id}! Booking ID: {booking_id}")
            return True
        elif response.status_code == 409:
            logger.error("Booking failed: Class already booked or full")
            logger.debug(f"Response: {response.text}")
            return False
        elif response.status_code == 401:
            logger.error("Booking failed: Authentication token expired")
            return False
        elif response.status_code == 403:
            logger.error("Booking failed: Access forbidden")
            logger.debug(f"Response: {response.text}")
            return False
        else:
            logger.error(f"Booking failed with status {response.status_code}")
            logger.debug(f"Response: {response.text}")
            return False

    except requests.exceptions.Timeout:
        logger.error("Booking request timed out")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Booking request failed: {e}")
        raise
