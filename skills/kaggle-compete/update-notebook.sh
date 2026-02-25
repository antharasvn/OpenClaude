#!/usr/bin/env bash
# kaggle-compete — Update an existing Kaggle notebook/kernel
# Usage: ./skills/kaggle-compete/update-notebook.sh <kernel_ref> [--notebook <path>] [--title <t>] [--gpu] [--no-gpu] [--private] [--public]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source workspace .env (user credentials)
if [[ -f "$PWD/.env" ]]; then
    set -a
    source "$PWD/.env"
    set +a
fi

# Parse arguments
KERNEL_REF=""
NOTEBOOK_PATH=""
NEW_TITLE=""
SET_GPU=""
SET_INTERNET=""
SET_PRIVACY=""
COMPETITION=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --notebook)
            NOTEBOOK_PATH="${2:-}"
            shift 2
            ;;
        --title)
            NEW_TITLE="${2:-}"
            shift 2
            ;;
        --gpu)
            SET_GPU="true"
            shift
            ;;
        --no-gpu)
            SET_GPU="false"
            shift
            ;;
        --internet)
            SET_INTERNET="true"
            shift
            ;;
        --no-internet)
            SET_INTERNET="false"
            shift
            ;;
        --private)
            SET_PRIVACY="true"
            shift
            ;;
        --public)
            SET_PRIVACY="false"
            shift
            ;;
        --competition)
            COMPETITION="${2:-}"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 <kernel_ref> [OPTIONS]"
            echo ""
            echo "Update an existing Kaggle notebook/kernel."
            echo ""
            echo "Arguments:"
            echo "  <kernel_ref>          Kernel reference: username/kernel-slug or URL"
            echo ""
            echo "Options:"
            echo "  --notebook <path>     Update notebook source code"
            echo "  --title <title>       Set new title"
            echo "  --gpu / --no-gpu      Enable/disable GPU"
            echo "  --internet / --no-internet  Enable/disable internet"
            echo "  --private / --public  Set visibility"
            echo "  --competition <slug>  Set competition data source"
            echo "  --help                Show this help"
            echo ""
            echo "At least one update option is required."
            exit 0
            ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            if [[ -z "$KERNEL_REF" ]]; then
                KERNEL_REF="$1"
            else
                echo "Error: unexpected argument: $1" >&2
                exit 1
            fi
            shift
            ;;
    esac
done

if [[ -z "$KERNEL_REF" ]]; then
    echo "Usage: $0 <kernel_ref> [--notebook <path>] [--title <t>] [--gpu] [--private]" >&2
    echo "Use --help for details." >&2
    exit 1
fi

if [[ -n "$NOTEBOOK_PATH" ]] && [[ ! -f "$NOTEBOOK_PATH" ]]; then
    echo "Error: Notebook not found: $NOTEBOOK_PATH" >&2
    exit 1
fi

# Validate Kaggle credentials
if [[ -z "${KAGGLE_USERNAME:-}" ]] || [[ -z "${KAGGLE_KEY:-}" ]]; then
    echo "Error: KAGGLE_USERNAME and KAGGLE_KEY must be set in .env" >&2
    exit 1
fi

export KAGGLE_USERNAME
export KAGGLE_KEY

python3 - "$KERNEL_REF" "$NOTEBOOK_PATH" "$NEW_TITLE" "$SET_GPU" "$SET_INTERNET" "$SET_PRIVACY" "$COMPETITION" <<'PYEOF'
import sys
import os
import re
import json

kernel_ref = sys.argv[1]
notebook_path = sys.argv[2] or None
new_title = sys.argv[3] or None
set_gpu = sys.argv[4] or None  # "true", "false", or ""
set_internet = sys.argv[5] or None
set_privacy = sys.argv[6] or None
competition = sys.argv[7] or None

from kagglehub import auth
from kagglehub.clients import build_kaggle_client
from kagglesdk.kernels.types.kernels_api_service import (
    ApiGetKernelRequest,
    ApiSaveKernelRequest,
)

kaggle_key = os.environ.get("KAGGLE_KEY", "")
username = os.environ.get("KAGGLE_USERNAME", "")
if kaggle_key.startswith("KGAT_"):
    auth.set_kaggle_api_token(kaggle_key)
else:
    auth.set_kaggle_credentials(username, kaggle_key)

client = build_kaggle_client()

# Parse kernel reference
owner = username
kernel_slug = kernel_ref

m = re.match(r'https?://.*kaggle\.com/code/([^/]+)/([^/]+)', kernel_ref)
if m:
    owner = m.group(1)
    kernel_slug = m.group(2)
elif '/' in kernel_ref:
    parts = kernel_ref.split('/')
    if len(parts) == 2:
        owner = parts[0]
        kernel_slug = parts[1]

print(f"Updating kernel: {owner}/{kernel_slug}")

# Get current kernel metadata
try:
    get_req = ApiGetKernelRequest()
    get_req.user_name = owner
    get_req.kernel_slug = kernel_slug
    current = client.kernels.kernels_api_client.get_kernel(get_req)
except Exception as e:
    print(f"Error fetching kernel: {e}", file=sys.stderr)
    sys.exit(1)

metadata = current.metadata if hasattr(current, 'metadata') else None
if not metadata:
    print("Error: Could not retrieve kernel metadata.", file=sys.stderr)
    sys.exit(1)

# Build update request preserving existing settings
req = ApiSaveKernelRequest()
req.slug = f"{owner}/{kernel_slug}"
req.new_title = new_title if new_title else metadata.title
req.language = metadata.language or "python"
req.kernel_type = metadata.kernel_type or "notebook"

# GPU
if set_gpu == "true":
    req.enable_gpu = True
elif set_gpu == "false":
    req.enable_gpu = False
else:
    req.enable_gpu = metadata.enable_gpu if hasattr(metadata, 'enable_gpu') else False

# Internet
if set_internet == "true":
    req.enable_internet = True
elif set_internet == "false":
    req.enable_internet = False
else:
    req.enable_internet = metadata.enable_internet if hasattr(metadata, 'enable_internet') else True

# Privacy
if set_privacy == "true":
    req.is_private = True
elif set_privacy == "false":
    req.is_private = False
else:
    req.is_private = metadata.is_private if hasattr(metadata, 'is_private') else True

# Competition data sources
if competition:
    req.competition_data_sources = [competition]
elif metadata.competition_data_sources:
    req.competition_data_sources = metadata.competition_data_sources

# Dataset data sources
if metadata.dataset_data_sources:
    req.dataset_data_sources = metadata.dataset_data_sources

# Notebook source code
if notebook_path:
    with open(notebook_path, "r") as f:
        notebook_text = f.read()
    try:
        json.loads(notebook_text)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid notebook JSON: {e}", file=sys.stderr)
        sys.exit(1)
    req.text = notebook_text
    print(f"  Updating source from: {os.path.basename(notebook_path)}")

# Show what's being updated
changes = []
if notebook_path:
    changes.append("source code")
if new_title:
    changes.append(f"title → '{new_title}'")
if set_gpu:
    changes.append(f"GPU → {set_gpu}")
if set_internet:
    changes.append(f"internet → {set_internet}")
if set_privacy:
    changes.append(f"private → {set_privacy}")
if competition:
    changes.append(f"competition → {competition}")

if not changes:
    print("No changes specified. Use --help to see options.", file=sys.stderr)
    sys.exit(1)

print(f"  Changes: {', '.join(changes)}")

# Save
response = client.kernels.kernels_api_client.save_kernel(req)

if response.error:
    print(f"Error from Kaggle API: {response.error}", file=sys.stderr)
    sys.exit(1)

notebook_url = response.url or f"https://www.kaggle.com/code/{owner}/{kernel_slug}"

print()
print("Notebook updated successfully!")
print(f"URL: {notebook_url}")
if response.version_number:
    print(f"Version: {response.version_number}")
PYEOF
