# Skill: moodle

## Purpose
Log into Innopolis University Moodle via SSO and fetch upcoming deadlines.
Uses a headless Chrome browser (via CDP) to authenticate and query the Moodle calendar API.

## Usage
```bash
./skills/moodle/run.sh [deadlines|courses]
```

### Commands
- `deadlines` (default) — show upcoming deadlines from Moodle calendar
- `courses` — list enrolled S26 (current semester) courses

## Required .env Variables
Add these to your workspace `.env`:
```
MOODLE_USERNAME=a.yourname@innopolis.university
MOODLE_PASSWORD=yourpassword
```

## Examples
```bash
# Show upcoming deadlines
./skills/moodle/run.sh

# Explicitly
./skills/moodle/run.sh deadlines

# List current courses
./skills/moodle/run.sh courses
```

## Notes
- Starts Chrome automatically if not already running (port 9222)
- Authenticates via Innopolis SSO (ADFS OAuth2)
- Reads credentials from `$PWD/.env` only — never from project root
