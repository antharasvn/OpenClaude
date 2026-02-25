#!/usr/bin/env bash
# kaggle-compete — List available Kaggle competitions
# Usage: ./skills/kaggle-compete/list-competitions.sh [--search <query>] [--category <cat>] [--sort <sort>] [--page <n>] [--json]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source workspace .env (user credentials)
if [[ -f "$PWD/.env" ]]; then
    set -a
    source "$PWD/.env"
    set +a
fi

# Parse arguments
SEARCH=""
CATEGORY=""
SORT_BY=""
PAGE="1"
PAGE_SIZE="20"
JSON_OUTPUT="false"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --search)
            SEARCH="${2:-}"
            shift 2
            ;;
        --category)
            CATEGORY="${2:-}"
            shift 2
            ;;
        --sort)
            SORT_BY="${2:-}"
            shift 2
            ;;
        --page)
            PAGE="${2:-1}"
            shift 2
            ;;
        --page-size)
            PAGE_SIZE="${2:-20}"
            shift 2
            ;;
        --json)
            JSON_OUTPUT="true"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "List available Kaggle competitions."
            echo ""
            echo "Options:"
            echo "  --search <query>    Search competitions by keyword"
            echo "  --category <cat>    Filter by category (featured, research, playground, getting-started, masters, community)"
            echo "  --sort <sort>       Sort by (grouped, prize, earliestDeadline, latestDeadline, numberOfTeams, recentlyCreated)"
            echo "  --page <n>          Page number (default: 1)"
            echo "  --page-size <n>     Results per page (default: 20)"
            echo "  --json              Output as JSON"
            echo "  --help              Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Use --help for usage information." >&2
            exit 1
            ;;
    esac
done

# Validate Kaggle credentials
if [[ -z "${KAGGLE_USERNAME:-}" ]] || [[ -z "${KAGGLE_KEY:-}" ]]; then
    echo "Error: KAGGLE_USERNAME and KAGGLE_KEY must be set in .env" >&2
    exit 1
fi

export KAGGLE_USERNAME
export KAGGLE_KEY

python3 - "$SEARCH" "$CATEGORY" "$SORT_BY" "$PAGE" "$PAGE_SIZE" "$JSON_OUTPUT" <<'PYEOF'
import sys
import os
import json

search = sys.argv[1] or None
category = sys.argv[2] or None
sort_by = sys.argv[3] or None
page = int(sys.argv[4])
page_size = int(sys.argv[5])
json_output = sys.argv[6] == "true"

from kagglehub import auth
from kagglehub.clients import build_kaggle_client
from kagglesdk.competitions.types.competition_api_service import ApiListCompetitionsRequest

kaggle_key = os.environ.get("KAGGLE_KEY", "")
username = os.environ.get("KAGGLE_USERNAME", "")
if kaggle_key.startswith("KGAT_"):
    auth.set_kaggle_api_token(kaggle_key)
else:
    auth.set_kaggle_credentials(username, kaggle_key)

client = build_kaggle_client()

req = ApiListCompetitionsRequest()
if search:
    req.search = search
if category:
    req.category = category
if sort_by:
    req.sort_by = sort_by
req.page = page
req.page_size = page_size

response = client.competitions.competition_api_client.list_competitions(req)

competitions = response.competitions if hasattr(response, 'competitions') else []

if not competitions:
    print("No competitions found.")
    sys.exit(0)

if json_output:
    results = []
    for c in competitions:
        results.append({
            "title": c.title,
            "ref": c.ref,
            "deadline": str(c.deadline) if c.deadline else None,
            "reward": c.reward,
            "teams": c.team_count,
            "kernels": c.kernel_count,
            "category": c.category,
            "url": c.url,
        })
    print(json.dumps(results, indent=2))
else:
    # Table output
    print(f"{'Title':<45} {'Deadline':<12} {'Reward':<15} {'Teams':<8}")
    print("-" * 82)
    for c in competitions:
        title = (c.title or "")[:44]
        deadline = str(c.deadline)[:10] if c.deadline else "N/A"
        reward = str(c.reward or "N/A")[:14]
        teams = str(c.team_count or 0)
        print(f"{title:<45} {deadline:<12} {reward:<15} {teams:<8}")

    print(f"\nPage {page} ({len(competitions)} results)")
PYEOF
