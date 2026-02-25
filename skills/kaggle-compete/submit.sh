#!/usr/bin/env bash
# kaggle-compete — Submit predictions to a Kaggle competition
# Usage: ./skills/kaggle-compete/submit.sh <competition> --file <submission.csv> [--message <msg>]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source workspace .env (user credentials)
if [[ -f "$PWD/.env" ]]; then
    set -a
    source "$PWD/.env"
    set +a
fi

# Parse arguments
COMPETITION=""
SUBMISSION_FILE=""
MESSAGE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --file|-f)
            SUBMISSION_FILE="${2:-}"
            shift 2
            ;;
        --message|-m)
            MESSAGE="${2:-}"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 <competition> --file <submission.csv> [--message <msg>]"
            echo ""
            echo "Submit predictions to a Kaggle competition."
            echo ""
            echo "Arguments:"
            echo "  <competition>       Competition URL or slug"
            echo ""
            echo "Options:"
            echo "  --file <path>       Path to submission file (required)"
            echo "  --message <msg>     Submission description message"
            echo "  --help              Show this help"
            exit 0
            ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            if [[ -z "$COMPETITION" ]]; then
                COMPETITION="$1"
            else
                echo "Error: unexpected argument: $1" >&2
                exit 1
            fi
            shift
            ;;
    esac
done

if [[ -z "$COMPETITION" ]]; then
    echo "Usage: $0 <competition> --file <submission.csv> [--message <msg>]" >&2
    exit 1
fi

if [[ -z "$SUBMISSION_FILE" ]]; then
    echo "Error: --file <path> is required." >&2
    exit 1
fi

if [[ ! -f "$SUBMISSION_FILE" ]]; then
    echo "Error: Submission file not found: $SUBMISSION_FILE" >&2
    exit 1
fi

# Validate Kaggle credentials
if [[ -z "${KAGGLE_USERNAME:-}" ]] || [[ -z "${KAGGLE_KEY:-}" ]]; then
    echo "Error: KAGGLE_USERNAME and KAGGLE_KEY must be set in .env" >&2
    exit 1
fi

export KAGGLE_USERNAME
export KAGGLE_KEY

python3 - "$COMPETITION" "$SUBMISSION_FILE" "$MESSAGE" <<'PYEOF'
import sys
import os
import re
import time

competition_arg = sys.argv[1]
submission_file = sys.argv[2]
message = sys.argv[3] or f"Submission {time.strftime('%Y-%m-%d %H:%M')}"

from kagglehub import auth
from kagglehub.clients import build_kaggle_client
from kagglesdk.competitions.types.competition_api_service import (
    ApiStartSubmissionUploadRequest,
    ApiCreateSubmissionRequest,
    ApiListSubmissionsRequest,
)

kaggle_key = os.environ.get("KAGGLE_KEY", "")
username = os.environ.get("KAGGLE_USERNAME", "")
if kaggle_key.startswith("KGAT_"):
    auth.set_kaggle_api_token(kaggle_key)
else:
    auth.set_kaggle_credentials(username, kaggle_key)

client = build_kaggle_client()

# Extract competition slug
slug = competition_arg
m = re.match(r'https?://.*kaggle\.com/competitions/([^/]+)', competition_arg)
if m:
    slug = m.group(1)
else:
    m = re.match(r'https?://.*kaggle\.com/c/([^/]+)', competition_arg)
    if m:
        slug = m.group(1)

file_name = os.path.basename(submission_file)
file_size = os.path.getsize(submission_file)

print(f"Submitting to competition: {slug}")
print(f"File: {file_name} ({file_size:,} bytes)")
print(f"Message: {message}")
print()

# Step 1: Start submission upload to get upload URL and token
print("Starting upload...")
start_req = ApiStartSubmissionUploadRequest()
start_req.competition_name = slug
start_req.file_name = file_name
start_req.content_length = file_size
start_req.last_modified_epoch_seconds = int(os.path.getmtime(submission_file))

start_resp = client.competitions.competition_api_client.start_submission_upload(start_req)

if not start_resp.create_url or not start_resp.token:
    print("Error: Failed to get upload URL from Kaggle.", file=sys.stderr)
    sys.exit(1)

# Step 2: Upload file to the provided URL
print("Uploading file...")
import urllib.request

with open(submission_file, 'rb') as f:
    file_data = f.read()

req = urllib.request.Request(
    start_resp.create_url,
    data=file_data,
    method='PUT'
)
req.add_header('Content-Type', 'application/octet-stream')
req.add_header('Content-Length', str(file_size))

try:
    urllib.request.urlopen(req)
except Exception as e:
    print(f"Error uploading file: {e}", file=sys.stderr)
    sys.exit(1)

# Step 3: Create the submission with the upload token
print("Creating submission...")
create_req = ApiCreateSubmissionRequest()
create_req.competition_name = slug
create_req.blob_file_tokens = start_resp.token
create_req.submission_description = message

create_resp = client.competitions.competition_api_client.create_submission(create_req)

if create_resp.message:
    print(f"Kaggle: {create_resp.message}")

print()
print("Submission uploaded successfully!")
print(f"Reference: {create_resp.ref}")

# Step 4: Wait briefly and check for score
print("\nChecking submission status (this may take a moment)...")
time.sleep(5)

try:
    list_req = ApiListSubmissionsRequest()
    list_req.competition_name = slug
    list_req.page = 1
    list_req.page_size = 5

    list_resp = client.competitions.competition_api_client.list_submissions(list_req)
    submissions = list_resp.submissions if hasattr(list_resp, 'submissions') and list_resp.submissions else []

    if submissions:
        latest = submissions[0]
        status = latest.status or "unknown"
        print(f"Status: {status}")
        if latest.public_score:
            print(f"Public Score: {latest.public_score}")
        if latest.private_score:
            print(f"Private Score: {latest.private_score}")
        if latest.error_description:
            print(f"Error: {latest.error_description}")
        if status == "pending":
            print("\nSubmission is still being scored. Check again with check-status.sh")
except Exception as e:
    print(f"Could not check status: {e}")
    print("Use list-submissions or the Kaggle web UI to check your score.")
PYEOF
