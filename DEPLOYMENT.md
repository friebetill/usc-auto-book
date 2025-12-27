# USC Auto-Book Deployment Checklist

Complete checklist for deploying and maintaining the USC Auto-Book tool.

## Pre-Deployment

### 1. System Requirements
- [ ] Python 3.7+ installed: `python3 --version`
- [ ] pip installed: `pip3 --version`
- [ ] Git installed (optional, for updates): `git --version`
- [ ] Urban Sports Club account active and accessible

### 2. Initial Setup
- [ ] Repository cloned or downloaded
- [ ] Virtual environment created: `python3 -m venv venv`
- [ ] Virtual environment activated: `source venv/bin/activate`
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] No errors during dependency installation

### 3. API Compatibility Test
- [ ] API test script is executable: `chmod +x test_api.py`
- [ ] API tests run successfully: `./test_api.py`
- [ ] At least "Courses Endpoint" test passes (✅ PASS)
- [ ] If tests fail, investigate API changes before proceeding

## Configuration

### 1. Environment File Setup
- [ ] `.env.example` copied to `.env`: `cp .env.example .env`
- [ ] `.env` file has correct permissions (readable by user only): `chmod 600 .env`
- [ ] `.env` file is in `.gitignore` (verify: `git check-ignore .env` returns `.env`)

### 2. Required Configuration
- [ ] `USC_EMAIL` set to your USC account email
- [ ] `USC_PASSWORD` set to your USC account password
- [ ] `USC_LOCATION_ID` set to your preferred venue ID
  - [ ] Location ID verified via browser DevTools or app network inspector

### 3. Optional Configuration (if needed)
- [ ] `USC_ADVANCE_DAYS` configured (default: 14)
- [ ] `USC_POLL_INTERVAL` configured (default: 1800 seconds = 30 min)
- [ ] Class filters configured:
  - [ ] `USC_CLASS_TITLE_FILTER` (if filtering by class type)
  - [ ] `USC_INSTRUCTOR_FILTER` (if filtering by instructor)
  - [ ] `USC_TIME_RANGE_START` (if filtering by time)
  - [ ] `USC_TIME_RANGE_END` (if filtering by time)
- [ ] Logging configured:
  - [ ] `USC_LOG_LEVEL` set (DEBUG for testing, INFO for production)
  - [ ] `USC_LOG_FILE` set (if logging to file)
  - [ ] Log directory exists and is writable: `mkdir -p logs && touch logs/test.log`

### 4. Security Verification
- [ ] `.env` file NOT committed to git: `git status` should not show `.env`
- [ ] `usc_api.config` backed up if migrating: `cp usc_api.config usc_api.config.backup`
- [ ] Old `usc_api.config` removed after successful migration (optional)
- [ ] Password is strong and unique
- [ ] No credentials visible in terminal history (use `HISTCONTROL=ignorespace`)

## Testing

### 1. Configuration Test
- [ ] Config loads without errors: `python3 -c "import uscApi; uscApi.loadConfig()"`
- [ ] No "Missing required environment variables" error
- [ ] Log level is appropriate (INFO for production, DEBUG for testing)

### 2. Manual Run Test
- [ ] Script is executable: `chmod +x uscApiTool.py`
- [ ] Manual run starts without errors: `./uscApiTool.py`
- [ ] Tool shows startup banner with configuration summary
- [ ] Filters are correctly displayed (if configured)
- [ ] Can interrupt with Ctrl+C cleanly (exit code 130)

### 3. Dry Run with Test Credentials (Optional)
- [ ] Create test `.env.test` with INFO logging
- [ ] Run: `cp .env .env.backup && cp .env.test .env`
- [ ] Verify tool behavior with test config
- [ ] Restore: `cp .env.backup .env`

### 4. Filter Verification (if using filters)
- [ ] Enable DEBUG logging: `USC_LOG_LEVEL=DEBUG`
- [ ] Run tool and check logs for filter matching
- [ ] Verify correct classes are matched/filtered
- [ ] Restore INFO logging after verification

### 5. Network Resilience Test
- [ ] Run with intentionally wrong password
- [ ] Verify retry logic activates
- [ ] Verify exponential backoff (2s, 4s, 8s delays)
- [ ] Verify tool exits gracefully after max retries

## Cron Setup (macOS)

### 1. Prepare Environment
- [ ] Absolute paths determined:
  - [ ] Project path: `/full/path/to/usc-auto-book`
  - [ ] Python path: `/full/path/to/usc-auto-book/venv/bin/python3`
  - [ ] Script path: `/full/path/to/usc-auto-book/uscApiTool.py`
  - [ ] Log path: `/full/path/to/logs/usc-auto-book.log`
- [ ] Log directory exists: `mkdir -p /path/to/logs`
- [ ] Log file is writable: `touch /path/to/logs/usc-auto-book.log`

### 2. Cron Job Configuration
- [ ] Crontab opened: `crontab -e`
- [ ] Schedule determined (e.g., every Tuesday/Friday at 7 AM)
- [ ] Environment variables configured in crontab (or relying on .env)
- [ ] Cron job added with absolute paths
- [ ] Output redirected to log file: `>> /path/to/log.log 2>&1`
- [ ] Crontab saved and verified: `crontab -l`

### 3. macOS-Specific Setup
- [ ] Full Disk Access granted to cron:
  1. [ ] System Settings > Privacy & Security > Full Disk Access
  2. [ ] Click '+' to add application
  3. [ ] Navigate to `/usr/sbin/cron` (Cmd+Shift+G)
  4. [ ] Toggle ON for cron
- [ ] Terminal app has Full Disk Access (if running cron from Terminal)

### 4. Cron Job Testing
- [ ] Set test job to run in 5 minutes: `*/5 * * * *`
- [ ] Wait for execution
- [ ] Check log file for output: `tail -f /path/to/log.log`
- [ ] Verify tool ran successfully
- [ ] Check for any permission errors
- [ ] Restore actual schedule after successful test
- [ ] Verify cron job: `crontab -l | grep usc`

### 5. Cron Job Monitoring
- [ ] Check cron is running: `ps aux | grep cron`
- [ ] Verify crontab syntax: `crontab -l | grep -v '^#'`
- [ ] Check system logs: `tail -f /var/log/system.log | grep cron`
- [ ] Check mail for cron errors: `mail` (if mail configured)

## Monitoring & Maintenance

### 1. Log File Management
- [ ] Log file location documented
- [ ] Log rotation configured (if needed):
  ```bash
  # Add to /etc/newsyslog.d/usc-auto-book.conf
  /path/to/usc-auto-book.log  644  7  *  @daily  G
  ```
- [ ] Log file size monitored: `ls -lh /path/to/log.log`
- [ ] Old logs archived if needed

### 2. Success Verification
- [ ] Check USC app for booked classes
- [ ] Verify booking confirmation emails from USC
- [ ] Review logs for "BOOKING SUCCESSFUL" message
- [ ] Cross-reference log timestamps with USC booking times

### 3. Regular Checks (Weekly)
- [ ] Review log file for errors: `grep ERROR /path/to/log.log`
- [ ] Check for failed bookings: `grep "BOOKING FAILED" /path/to/log.log`
- [ ] Verify cron job is running: `crontab -l`
- [ ] Check log file size: `du -h /path/to/log.log`

### 4. Monthly Maintenance
- [ ] Review booking success rate
- [ ] Update dependencies if needed: `pip install -r requirements.txt --upgrade`
- [ ] Run API compatibility test: `./test_api.py`
- [ ] Check for tool updates: `git pull` (if using git)
- [ ] Rotate logs manually if not automated

### 5. Quarterly Review
- [ ] Review USC Terms of Service for changes
- [ ] Check for USC API updates
- [ ] Verify location IDs still correct
- [ ] Update Python version if needed
- [ ] Backup configuration: `cp .env .env.backup-$(date +%Y%m%d)`

## Troubleshooting Reference

### Common Issues

| Issue | Check | Solution |
|-------|-------|----------|
| Cron not running | `ps aux \| grep cron` | Restart: `sudo launchctl start com.vix.cron` |
| Permission denied | `ls -la /path/to/script` | Fix perms: `chmod +x uscApiTool.py` |
| Module not found | `which python3` in cron | Use absolute path to venv python |
| Env vars not loaded | Cron environment | Set vars in crontab or use .env |
| API errors | `./test_api.py` | Check API compatibility |
| Login failed | USC app login | Verify credentials |

### Emergency Contacts

- [ ] Repository URL documented: _______________
- [ ] Issue tracker URL documented: _______________
- [ ] USC support contact: _______________

## Post-Deployment Checklist

- [ ] Tool ran successfully at least once
- [ ] Booking confirmed in USC app
- [ ] Cron job scheduled and tested
- [ ] Logs are readable and informative
- [ ] No credentials exposed in logs or git
- [ ] Documentation read and understood
- [ ] Monitoring schedule established
- [ ] Team members notified (if applicable)

## Rollback Plan

If tool is not working as expected:

1. [ ] Stop cron job: `crontab -e` and comment out the line
2. [ ] Restore old config: `cp usc_api.config.backup usc_api.config`
3. [ ] Restore old code: `git checkout <previous-commit>` or restore backup
4. [ ] Restore old dependencies: `pip install -r requirements.txt --force-reinstall`
5. [ ] Test old version: `./uscApiTool.py`
6. [ ] Re-enable cron once stable

---

## Deployment Sign-off

- **Deployed by:** ________________
- **Date:** ________________
- **Environment:** Production / Staging / Test
- **First successful booking:** ________________
- **Notes:**
  -
  -
  -

## Next Review Date

**Scheduled for:** ________________ (recommended: 1 month from deployment)
