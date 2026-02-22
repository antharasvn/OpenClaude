# Skill: moodle

## Purpose
Log into Innopolis University Moodle via SSO and interact with courses:
fetch deadlines, list courses, browse resources, and download files.
Uses a headless Chrome browser (via CDP) to authenticate and call the Moodle API.

## Usage
```bash
./skills/moodle/run.sh [command] [args]
```

### Commands
- `deadlines` (default) — show upcoming deadlines (next 90 days)
- `courses` — list enrolled [S26] (current semester) courses
- `lectures [course_id]` — list all resources for a course (default: NLP, id=3440)
- `download <resource_id> [outdir]` — download a file resource; prints the saved path to stdout

## Required .env Variables
Add these to your workspace `.env`:
```
MOODLE_USERNAME=a.yourname@innopolis.university
MOODLE_PASSWORD=yourpassword
```

## Examples
```bash
# Upcoming deadlines
./skills/moodle/run.sh

# List NLP course resources
./skills/moodle/run.sh lectures

# List resources for a specific course
./skills/moodle/run.sh lectures 3445

# Download a resource by its Moodle ID
./skills/moodle/run.sh download 146398

# Download to a specific directory
./skills/moodle/run.sh download 146398 /tmp/nlp
```

## Notes
- Starts Chrome automatically if not already running (port 9222)
- Authenticates via Innopolis SSO (ADFS OAuth2)
- `download` prints the saved file path to stdout (for piping)
- Credentials read from `$PWD/.env` only — never from project root
