#!/usr/bin/env bash
# kaggle-compete — Get competition leaderboard
# Usage: ./skills/kaggle-compete/get-leaderboard.sh <competition> [--top <n>] [--json]

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
TOP_N="20"
JSON_OUTPUT="false"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --top|-n)
            TOP_N="${2:-20}"
            shift 2
            ;;
        --json)
            JSON_OUTPUT="true"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 <competition> [OPTIONS]"
            echo ""
            echo "Get competition leaderboard from Kaggle."
            echo ""
            echo "Arguments:"
            echo "  <competition>       Competition URL or slug"
            echo ""
            echo "Options:"
            echo "  --top <n>           Show top N entries (default: 20)"
            echo "  --json              Output as JSON"
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
    echo "Usage: $0 <competition> [--top <n>] [--json]" >&2
    echo "Example: $0 https://www.kaggle.com/competitions/titanic --top 10" >&2
    exit 1
fi

# Validate Kaggle credentials
if [[ -z "${KAGGLE_USERNAME:-}" ]] || [[ -z "${KAGGLE_KEY:-}" ]]; then
    echo "Error: KAGGLE_USERNAME and KAGGLE_KEY must be set in .env" >&2
    exit 1
fi

export KAGGLE_USERNAME
export KAGGLE_KEY

python3 - "$COMPETITION" "$TOP_N" "$JSON_OUTPUT" <<'PYEOF'
import sys
import os
import re
import json

competition_arg = sys.argv[1]
top_n = int(sys.argv[2])
json_output = sys.argv[3] == "true"

from kagglehub import auth
from kagglehub.clients import build_kaggle_client
from kagglesdk.competitions.types.competition_api_service import ApiGetLeaderboardRequest

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

print(f"Leaderboard for: {slug}")
print()

req = ApiGetLeaderboardRequest()
req.competition_name = slug
req.page_size = top_n

try:
    response = client.competitions.competition_api_client.get_leaderboard(req)
except Exception as e:
    print(f"Error fetching leaderboard: {e}", file=sys.stderr)
    sys.exit(1)

submissions = response.submissions if hasattr(response, 'submissions') and response.submissions else []

if not submissions:
    print("No leaderboard entries found.")
    sys.exit(0)

# Check if user is on the leaderboard
user_entry = None
for i, s in enumerate(submissions):
    team = s.team_name if hasattr(s, 'team_name') else ""
    if team and team.lower() == username.lower():
        user_entry = (i + 1, s)

if json_output:
    results = []
    for i, s in enumerate(submissions):
        results.append({
            "rank": i + 1,
            "teamName": s.team_name if hasattr(s, 'team_name') else None,
            "score": s.score if hasattr(s, 'score') else None,
            "submissionDate": str(s.submission_date) if hasattr(s, 'submission_date') and s.submission_date else None,
        })
    output = {"competition": slug, "entries": results}
    if user_entry:
        output["userRank"] = user_entry[0]
    print(json.dumps(output, indent=2))
else:
    print(f"{'Rank':<6} {'Team':<35} {'Score':<15} {'Date':<12}")
    print("-" * 70)
    for i, s in enumerate(submissions):
        rank = str(i + 1)
        team = (s.team_name if hasattr(s, 'team_name') and s.team_name else "Anonymous")[:34]
        score = str(s.score if hasattr(s, 'score') and s.score else "N/A")[:14]
        date = str(s.submission_date)[:10] if hasattr(s, 'submission_date') and s.submission_date else "N/A"
        # Highlight user's entry
        marker = " <-- you" if team.lower() == username.lower() else ""
        print(f"{rank:<6} {team:<35} {score:<15} {date:<12}{marker}")

    print(f"\nShowing top {len(submissions)} entries")

    if user_entry:
        rank, entry = user_entry
        print(f"\nYour position: #{rank}")
        if hasattr(entry, 'score') and entry.score:
            print(f"Your score: {entry.score}")
    else:
        print(f"\nYou ({username}) are not on the visible leaderboard.")
PYEOF
