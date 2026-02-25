#!/usr/bin/env bash
# kaggle-compete — Download competition or public dataset files
# Usage: ./skills/kaggle-compete/download-dataset.sh <competition_or_dataset> [--output <dir>] [--file <filename>]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source workspace .env (user credentials)
if [[ -f "$PWD/.env" ]]; then
    set -a
    source "$PWD/.env"
    set +a
fi

# Parse arguments
TARGET=""
OUTPUT_DIR=""
FILE_NAME=""
LIST_FILES="false"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output|-o)
            OUTPUT_DIR="${2:-}"
            shift 2
            ;;
        --file|-f)
            FILE_NAME="${2:-}"
            shift 2
            ;;
        --list)
            LIST_FILES="true"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 <target> [OPTIONS]"
            echo ""
            echo "Download competition or dataset files from Kaggle."
            echo ""
            echo "Target formats:"
            echo "  Competition URL:  https://www.kaggle.com/competitions/<slug>"
            echo "  Competition slug: <slug> (e.g., titanic)"
            echo "  Dataset ref:      <owner>/<dataset-slug> (e.g., zillow/zecon)"
            echo ""
            echo "Options:"
            echo "  --output <dir>    Download directory (default: current dir)"
            echo "  --file <name>     Download specific file only"
            echo "  --list            List available files without downloading"
            echo "  --help            Show this help"
            exit 0
            ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            if [[ -z "$TARGET" ]]; then
                TARGET="$1"
            else
                echo "Error: unexpected argument: $1" >&2
                exit 1
            fi
            shift
            ;;
    esac
done

if [[ -z "$TARGET" ]]; then
    echo "Usage: $0 <competition_or_dataset> [--output <dir>] [--file <filename>] [--list]" >&2
    echo "Use --help for more details." >&2
    exit 1
fi

# Validate Kaggle credentials
if [[ -z "${KAGGLE_USERNAME:-}" ]] || [[ -z "${KAGGLE_KEY:-}" ]]; then
    echo "Error: KAGGLE_USERNAME and KAGGLE_KEY must be set in .env" >&2
    exit 1
fi

export KAGGLE_USERNAME
export KAGGLE_KEY

# Default output dir
if [[ -z "$OUTPUT_DIR" ]]; then
    OUTPUT_DIR="$PWD"
fi
mkdir -p "$OUTPUT_DIR"

python3 - "$TARGET" "$OUTPUT_DIR" "$FILE_NAME" "$LIST_FILES" <<'PYEOF'
import sys
import os
import re

target = sys.argv[1]
output_dir = sys.argv[2]
file_name = sys.argv[3] or None
list_files = sys.argv[4] == "true"

from kagglehub import auth
from kagglehub.clients import build_kaggle_client
from kagglesdk.competitions.types.competition_api_service import (
    ApiListDataFilesRequest, ApiDownloadDataFilesRequest, ApiDownloadDataFileRequest
)
from kagglesdk.datasets.types.dataset_api_service import (
    ApiDownloadDatasetRequest, ApiListDatasetFilesRequest
)

kaggle_key = os.environ.get("KAGGLE_KEY", "")
username = os.environ.get("KAGGLE_USERNAME", "")
if kaggle_key.startswith("KGAT_"):
    auth.set_kaggle_api_token(kaggle_key)
else:
    auth.set_kaggle_credentials(username, kaggle_key)

client = build_kaggle_client()

# Determine if target is competition or dataset
# Dataset: owner/slug format
# Competition: URL or plain slug
is_dataset = False
competition_slug = None
dataset_owner = None
dataset_slug = None

# Check for competition URL
m = re.match(r'https?://.*kaggle\.com/competitions/([^/]+)', target)
if m:
    competition_slug = m.group(1)
elif re.match(r'https?://.*kaggle\.com/c/([^/]+)', target):
    m = re.match(r'https?://.*kaggle\.com/c/([^/]+)', target)
    competition_slug = m.group(1)
elif '/' in target:
    # Dataset ref: owner/slug
    parts = target.split('/')
    if len(parts) == 2:
        is_dataset = True
        dataset_owner = parts[0]
        dataset_slug = parts[1]
    else:
        # Could be dataset URL
        m = re.match(r'https?://.*kaggle\.com/datasets/([^/]+)/([^/]+)', target)
        if m:
            is_dataset = True
            dataset_owner = m.group(1)
            dataset_slug = m.group(2)
        else:
            print(f"Error: Could not parse target: {target}", file=sys.stderr)
            sys.exit(1)
else:
    # Plain competition slug
    competition_slug = target

if is_dataset:
    if list_files:
        req = ApiListDatasetFilesRequest()
        req.owner_slug = dataset_owner
        req.dataset_slug = dataset_slug
        resp = client.datasets.dataset_api_client.list_dataset_files(req)
        files = resp.files if hasattr(resp, 'files') and resp.files else []
        if not files:
            print("No files found.")
        else:
            print(f"Files in dataset {dataset_owner}/{dataset_slug}:")
            for f in files:
                name = f.name if hasattr(f, 'name') else f.file_name if hasattr(f, 'file_name') else str(f)
                size = f.total_bytes if hasattr(f, 'total_bytes') else ""
                print(f"  {name}  ({size} bytes)" if size else f"  {name}")
    else:
        print(f"Downloading dataset {dataset_owner}/{dataset_slug}...")
        # Use kagglehub for dataset download (simpler API)
        import kagglehub
        path = kagglehub.dataset_download(f"{dataset_owner}/{dataset_slug}")
        print(f"Downloaded to: {path}")
        # Copy to output dir if different
        if os.path.abspath(path) != os.path.abspath(output_dir):
            import shutil
            if os.path.isdir(path):
                for item in os.listdir(path):
                    src = os.path.join(path, item)
                    dst = os.path.join(output_dir, item)
                    if os.path.isfile(src):
                        shutil.copy2(src, dst)
                        print(f"  Copied: {item}")
                    elif os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                        print(f"  Copied: {item}/")
            else:
                shutil.copy2(path, output_dir)
            print(f"Files saved to: {output_dir}")
else:
    if list_files:
        req = ApiListDataFilesRequest()
        req.competition_name = competition_slug
        resp = client.competitions.competition_api_client.list_data_files(req)
        files = resp.files if hasattr(resp, 'files') and resp.files else []
        if not files:
            print("No files found. Make sure you have joined the competition.")
        else:
            print(f"Files in competition {competition_slug}:")
            for f in files:
                name = f.name if hasattr(f, 'name') else f.ref if hasattr(f, 'ref') else str(f)
                size = f.total_bytes if hasattr(f, 'total_bytes') else ""
                print(f"  {name}  ({size} bytes)" if size else f"  {name}")
    else:
        print(f"Downloading competition data for {competition_slug}...")
        # Use kagglehub for competition download
        import kagglehub
        path = kagglehub.competition_download(competition_slug)
        print(f"Downloaded to: {path}")
        if os.path.abspath(path) != os.path.abspath(output_dir):
            import shutil
            if os.path.isdir(path):
                for item in os.listdir(path):
                    src = os.path.join(path, item)
                    dst = os.path.join(output_dir, item)
                    if os.path.isfile(src):
                        shutil.copy2(src, dst)
                        print(f"  Copied: {item}")
                    elif os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                        print(f"  Copied: {item}/")
            else:
                shutil.copy2(path, output_dir)
            print(f"Files saved to: {output_dir}")
PYEOF
