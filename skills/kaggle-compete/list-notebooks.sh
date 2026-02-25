#!/usr/bin/env bash
# kaggle-compete — List Kaggle notebooks/kernels
# Usage: ./skills/kaggle-compete/list-notebooks.sh [--mine] [--competition <slug>] [--dataset <ref>] [--search <query>] [--json]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source workspace .env (user credentials)
if [[ -f "$PWD/.env" ]]; then
    set -a
    source "$PWD/.env"
    set +a
fi

# Parse arguments
MINE="false"
COMPETITION=""
DATASET=""
SEARCH=""
SORT_BY=""
PAGE="1"
PAGE_SIZE="20"
JSON_OUTPUT="false"
USER_FILTER=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --mine)
            MINE="true"
            shift
            ;;
        --user)
            USER_FILTER="${2:-}"
            shift 2
            ;;
        --competition)
            COMPETITION="${2:-}"
            shift 2
            ;;
        --dataset)
            DATASET="${2:-}"
            shift 2
            ;;
        --search)
            SEARCH="${2:-}"
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
            echo "List Kaggle notebooks/kernels."
            echo ""
            echo "Options:"
            echo "  --mine              List your own notebooks"
            echo "  --user <username>   List notebooks by specific user"
            echo "  --competition <s>   Filter by competition slug"
            echo "  --dataset <ref>     Filter by dataset (owner/slug)"
            echo "  --search <query>    Search by keyword"
            echo "  --sort <sort>       Sort by (hotness, commentCount, dateCreated, dateRun, relevance, scoreAscending, scoreDescending, viewCount, voteCount)"
            echo "  --page <n>          Page number (default: 1)"
            echo "  --page-size <n>     Results per page (default: 20)"
            echo "  --json              Output as JSON"
            echo "  --help              Show this help"
            exit 0
            ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            echo "Error: unexpected argument: $1" >&2
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

python3 - "$MINE" "$USER_FILTER" "$COMPETITION" "$DATASET" "$SEARCH" "$SORT_BY" "$PAGE" "$PAGE_SIZE" "$JSON_OUTPUT" <<'PYEOF'
import sys
import os
import json

mine = sys.argv[1] == "true"
user_filter = sys.argv[2] or None
competition = sys.argv[3] or None
dataset = sys.argv[4] or None
search = sys.argv[5] or None
sort_by = sys.argv[6] or None
page = int(sys.argv[7])
page_size = int(sys.argv[8])
json_output = sys.argv[9] == "true"

from kagglehub import auth
from kagglehub.clients import build_kaggle_client
from kagglesdk.kernels.types.kernels_api_service import ApiListKernelsRequest

kaggle_key = os.environ.get("KAGGLE_KEY", "")
username = os.environ.get("KAGGLE_USERNAME", "")
if kaggle_key.startswith("KGAT_"):
    auth.set_kaggle_api_token(kaggle_key)
else:
    auth.set_kaggle_credentials(username, kaggle_key)

client = build_kaggle_client()

req = ApiListKernelsRequest()

if mine:
    req.user = username
elif user_filter:
    req.user = user_filter

if competition:
    req.competition = competition
if dataset:
    req.dataset = dataset
if search:
    req.search = search
if sort_by:
    req.sort_by = sort_by

req.page = page
req.page_size = page_size

response = client.kernels.kernels_api_client.list_kernels(req)

kernels = response.kernels if hasattr(response, 'kernels') and response.kernels else []

if not kernels:
    print("No notebooks found.")
    sys.exit(0)

if json_output:
    results = []
    for k in kernels:
        results.append({
            "ref": k.ref if hasattr(k, 'ref') else None,
            "title": k.title if hasattr(k, 'title') else None,
            "author": k.author if hasattr(k, 'author') else None,
            "lastRunTime": str(k.last_run_time) if hasattr(k, 'last_run_time') and k.last_run_time else None,
            "totalVotes": k.total_votes if hasattr(k, 'total_votes') else None,
            "language": k.language if hasattr(k, 'language') else None,
            "kernelType": k.kernel_type if hasattr(k, 'kernel_type') else None,
            "isPrivate": k.is_private if hasattr(k, 'is_private') else None,
        })
    print(json.dumps(results, indent=2))
else:
    print(f"{'Title':<40} {'Author':<16} {'Last Run':<12} {'Votes':<7} {'Type':<10}")
    print("-" * 87)
    for k in kernels:
        title = (k.title if hasattr(k, 'title') and k.title else "Untitled")[:39]
        author = (k.author if hasattr(k, 'author') and k.author else "")[:15]
        last_run = str(k.last_run_time)[:10] if hasattr(k, 'last_run_time') and k.last_run_time else "N/A"
        votes = str(k.total_votes if hasattr(k, 'total_votes') and k.total_votes else 0)
        ktype = str(k.kernel_type if hasattr(k, 'kernel_type') else "")[:9]
        print(f"{title:<40} {author:<16} {last_run:<12} {votes:<7} {ktype:<10}")

    print(f"\nPage {page} ({len(kernels)} results)")
PYEOF
