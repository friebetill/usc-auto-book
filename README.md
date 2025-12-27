# USC Auto-Book Tool

Automatically book Urban Sports Club classes in advance. Books classes up to 2 weeks ahead (configurable) based on your preferences with advanced filtering options.

## Features

- **Automatic class booking** at configured venue(s) up to 14 days in advance
- **Advanced filtering** by class type, instructor name, and time range
- **Retry logic** with exponential backoff for network resilience
- **Structured logging** for monitoring and debugging
- **Secure credential management** via environment variables
- **Cron job support** for scheduled execution
- **Legacy config fallback** for easy migration

## Requirements

- Python 3.7 or higher
- Urban Sports Club account
- macOS, Linux, or Windows

## Installation

### 1. Clone and Setup Virtual Environment

```bash
git clone <repository-url>
cd usc-auto-book

# Create virtual environment
python3 -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Test API Compatibility

Before configuring, verify that USC API v5 still works:

```bash
./test_api.py
```

Expected output: At least the "Courses Endpoint" test should PASS.

### 4. Configure Environment Variables

```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

**Minimum required settings in .env:**
```bash
USC_EMAIL=your.email@example.com
USC_PASSWORD=your_password
USC_LOCATION_ID=15238  # See below for how to find this
```

## Configuration

### Finding Your Location ID

Location IDs are venue-specific identifiers used by the USC API:

**Method 1 - Browser DevTools:**
1. Open USC website and log in
2. Open browser DevTools (F12)
3. Go to Network tab
4. Search for classes at your desired venue
5. Look for API calls to `/courses` endpoint
6. Find the `locationId` parameter in the request

**Method 2 - Mobile App:**
1. Use a network traffic inspector (e.g., Charles Proxy, mitmproxy)
2. Open USC app and browse venues
3. Capture API requests to find location IDs

Common location IDs (examples only - verify for your area):
- `15238` - Example venue (from original code)

### Environment Variables Reference

See `.env.example` for all available options:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `USC_EMAIL` | ✓ | - | Your USC account email |
| `USC_PASSWORD` | ✓ | - | Your USC account password |
| `USC_LOCATION_ID` | ✓ | - | Venue location ID |
| `USC_ADVANCE_DAYS` | | 14 | How many days ahead to book |
| `USC_POLL_INTERVAL` | | 1800 | Seconds between checks (1800 = 30 min) |
| `USC_CLASS_TITLE_FILTER` | | "" | Filter by class title |
| `USC_INSTRUCTOR_FILTER` | | "" | Filter by instructor name |
| `USC_TIME_RANGE_START` | | "" | Earliest class time (HH:MM) |
| `USC_TIME_RANGE_END` | | "" | Latest class time (HH:MM) |
| `USC_LOG_LEVEL` | | INFO | DEBUG, INFO, WARNING, ERROR |
| `USC_LOG_FILE` | | "" | Path to log file (empty = console only) |

## Usage

### Manual Execution

```bash
# Activate virtual environment
source venv/bin/activate

# Run the tool
./uscApiTool.py
```

The tool will:
1. Poll every 30 minutes (configurable) for available classes
2. Book the first class matching your filters
3. Exit when class is booked or deadline reached

### Cron Job Setup (Recommended)

**For macOS/Linux:**

```bash
# Edit crontab
crontab -e

# Add this line (runs every Tuesday and Friday at 7:00 AM)
0 7 * * TUE,FRI cd /path/to/usc-auto-book && /path/to/usc-auto-book/venv/bin/python3 /path/to/usc-auto-book/uscApiTool.py >> /path/to/usc-auto-book.log 2>&1
```

**Important for macOS:**
- Grant cron Full Disk Access in System Settings > Privacy & Security > Full Disk Access
- Add `/usr/sbin/cron` to the list

**Environment variables in cron:**

Option 1 - Set in crontab:
```cron
# At top of crontab
USC_EMAIL=your@email.com
USC_PASSWORD=yourpass
USC_LOCATION_ID=15238
USC_LOG_FILE=/path/to/usc-auto-book.log

# Then the job
0 7 * * TUE,FRI cd /path/to/usc-auto-book && ./venv/bin/python3 uscApiTool.py
```

Option 2 - Use .env file (recommended):
```cron
# Cron will automatically load .env via python-dotenv
0 7 * * TUE,FRI cd /path/to/usc-auto-book && ./venv/bin/python3 uscApiTool.py >> /path/to/logs/usc.log 2>&1
```

**Cron schedule examples:**
- `0 7 * * TUE,FRI` - Every Tuesday and Friday at 7:00 AM
- `0 */6 * * *` - Every 6 hours
- `30 8 * * 1-5` - Weekdays at 8:30 AM

See [crontab.guru](https://crontab.guru/) for help with schedules.

## Filtering Examples

### Example 1: Book only Yoga classes

```bash
# In .env
USC_CLASS_TITLE_FILTER=yoga
```

This will match any class with "yoga" in the title (case-insensitive):
- "Hatha Yoga"
- "Power Yoga Flow"
- "Yogalates"

### Example 2: Book only morning classes (before 12:00)

```bash
# In .env
USC_TIME_RANGE_START=06:00
USC_TIME_RANGE_END=12:00
```

### Example 3: Book specific instructor

```bash
# In .env
USC_INSTRUCTOR_FILTER=John Smith
```

### Example 4: Combine multiple filters

```bash
# In .env (only evening pilates classes)
USC_CLASS_TITLE_FILTER=pilates
USC_TIME_RANGE_START=18:00
USC_TIME_RANGE_END=21:00
```

**Note:** All filters are AND conditions - classes must match ALL specified filters.

## Logging

### Log Levels

- **DEBUG**: Detailed diagnostic information (API calls, filter matching, response data)
- **INFO**: Confirmation messages (class found, booking progress) - **recommended**
- **WARNING**: Something unexpected but handled
- **ERROR**: Serious problems

### Enable Debug Logging

Useful for troubleshooting filter issues:

```bash
# In .env
USC_LOG_LEVEL=DEBUG
```

### Log to File

Recommended for cron jobs:

```bash
# In .env
USC_LOG_FILE=/Users/yourname/usc-auto-book/usc.log
```

The directory must exist and be writable.

## Troubleshooting

### "Missing required environment variables"

**Cause:** `.env` file not found or incomplete

**Solution:**
1. Ensure `.env` file exists: `ls -la .env`
2. Check it contains all required variables
3. Verify file is named exactly `.env` (not `.env.txt`)

### "Login failed: Invalid credentials"

**Cause:** Incorrect email or password

**Solution:**
1. Verify credentials in `.env` file
2. Try logging into USC app/website to confirm credentials work
3. Check for special characters that might need escaping

### "No classes found"

**Possible causes:**
- `USC_LOCATION_ID` is incorrect
- No classes available on that date
- Filters are too restrictive

**Solution:**
1. Enable DEBUG logging: `USC_LOG_LEVEL=DEBUG`
2. Check logs for "Found X classes" message
3. If 0 classes, verify location ID
4. If classes found but none bookable, check filter debug messages

### "API compatibility issues"

**Cause:** USC may have updated their API

**Solution:**
1. Run `./test_api.py` to check API status
2. Check for tool updates in this repository
3. Open an issue with test results

### "Booking failed: Class already booked or full"

**Cause:** Someone else booked the class first, or you already have a booking

**Solution:**
- This is expected behavior when classes are popular
- Consider running more frequently (reduce `USC_POLL_INTERVAL`)
- Check USC app to see if you already have a booking

### Cron job not running

**macOS specific:**
1. Check cron has Full Disk Access (System Settings > Privacy & Security)
2. Verify paths are absolute (not relative)
3. Test the command manually first
4. Check `/var/mail/yourusername` for cron error emails

## Security Notes

- **Never commit `.env` or `usc_api.config`** to version control
- `.env` is in `.gitignore` by default
- Keep your virtual environment (`venv/`) local only
- OAuth client credentials are from the Android app (publicly known, not secret)
- Use strong, unique passwords for your USC account

## Migration from Legacy Version

If you're upgrading from the old config file version:

### Automatic Migration (Recommended)

The tool will automatically detect and use `usc_api.config` if no `.env` exists, with a deprecation warning.

### Manual Migration

1. **Create `.env` file:**
   ```bash
   cp .env.example .env
   ```

2. **Copy credentials** from `usc_api.config` to `.env`:
   ```bash
   # Old format (usc_api.config)
   email = usc@example.com
   password = uscpassword1

   # New format (.env)
   USC_EMAIL=usc@example.com
   USC_PASSWORD=uscpassword1
   USC_LOCATION_ID=15238
   ```

3. **Test new configuration:**
   ```bash
   source venv/bin/activate
   ./uscApiTool.py
   ```

4. **Remove old config** (once confirmed working):
   ```bash
   rm usc_api.config
   ```

## Known Issues & Limitations

- **API v5 compatibility**: Last verified in 2024. If USC updates their API, the tool may need updates.
- **Single venue only**: Currently books from one location at a time.
- **No waitlist support**: Cannot join waitlists for full classes.
- **Rate limiting**: Excessive polling may trigger USC rate limits (use default 30-min interval).

## Disclaimer

**Use at your own risk.** The author is not responsible for any damage to your USC account or violations of USC's Terms of Service.

**Terms of Service:** Ensure your use of this tool complies with Urban Sports Club's Terms of Service. This tool is intended for **personal use only** to automate your own bookings.

**Important:** Do not use this tool if you don't have the approval of USC to access their API. This tool reverse-engineers the Android app's API access - use responsibly.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with clear description

## License

[MIT License](LICENSE)

## Changelog

### v2.0.0 (2024) - Modernization Update
- ✅ Updated dependencies (fixed security CVEs)
- ✅ Migrated to environment variables (.env support)
- ✅ Added structured logging with file output
- ✅ Implemented retry logic with exponential backoff
- ✅ Added class filtering (title, instructor, time range)
- ✅ Improved error handling and messages
- ✅ Fixed URL bug (duplicate "courses?" in API call)
- ✅ Legacy config file backward compatibility
- ✅ Comprehensive documentation

### v1.0.0 (2019)
- Initial release with basic booking functionality
- API v5 support
