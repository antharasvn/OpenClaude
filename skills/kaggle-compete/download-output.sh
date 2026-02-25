#!/usr/bin/env bash
# kaggle-compete — Download notebook output files
# Usage: ./skills/kaggle-compete/download-output.sh <kernel_ref> [--output <dir>] [--file <name>]

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
OUTPUT_DIR=""
FILE_NAME=""
LIST_ONLY="false"

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
            LIST_ONLY="true"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 <kernel_ref> [OPTIONS]"
            echo ""
            echo "Download output files from a Kaggle notebook/kernel."
            echo ""
            echo "Arguments:"
            echo "  <kernel_ref>        Kernel reference: username/kernel-slug or URL"
            echo ""
            echo "Options:"
            echo "  --output <dir>      Download directory (default: current dir)"
            echo "  --file <name>       Download specific file only"
            echo "  --list              List output files without downloading"
            echo "  --help              Show this help"
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
    echo "Usage: $0 <kernel_ref> [--output <dir>] [--file <name>] [--list]" >&2
    echo "Example: $0 username/my-notebook --output ./results/" >&2
    exit 1
fi

# Validate Kaggle credentials
if [[ -z "${KAGGLE_USERNAME:-}" ]] || [[ -z "${KAGGLE_KEY:-}" ]]; then
    echo "Error: KAGGLE_USERNAME and KAGGLE_KEY must be set in .env" >&2
    exit 1
fi

export KAGGLE_USERNAME
export KAGGLE_KEY

if [[ -z "$OUTPUT_DIR" ]]; then
    OUTPUT_DIR="$PWD"
fi
mkdir -p "$OUTPUT_DIR"

python3 - "$KERNEL_REF" "$OUTPUT_DIR" "$FILE_NAME" "$LIST_ONLY" <<'PYEOF'
import sys
import os
import re
import urllib.request

kernel_ref = sys.argv[1]
output_dir = sys.argv[2]
target_file = sys.argv[3] or None
list_only = sys.argv[4] == "true"

from kagglehub import auth
from kagglehub.clients import build_kaggle_client
from kagglesdk.kernels.types.kernels_api_service import (
    ApiListKernelSessionOutputRequest,
    ApiDownloadKernelOutputRequest,
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

print(f"Kernel: {owner}/{kernel_slug}")

# List output files
req = ApiListKernelSessionOutputRequest()
req.user_name = owner
req.kernel_slug = kernel_slug

try:
    resp = client.kernels.kernels_api_client.list_kernel_session_output(req)
except Exception as e:
    print(f"Error listing output: {e}", file=sys.stderr)
    print("Make sure the kernel has finished running.", file=sys.stderr)
    sys.exit(1)

files = resp.files if resp.files else []

if not files:
    print("No output files found.")
    if resp.log:
        print("\nExecution log (last 500 chars):")
        print(resp.log[-500:])
    sys.exit(0)

if list_only:
    print(f"\nOutput files ({len(files)}):")
    for f in files:
        name = f.file_name if hasattr(f, 'file_name') else str(f)
        print(f"  - {name}")
    sys.exit(0)

# Download files
downloaded = 0
for f in files:
    name = f.file_name if hasattr(f, 'file_name') else None
    url = f.url if hasattr(f, 'url') else None

    if not name or not url:
        continue

    if target_file and name != target_file:
        continue

    dest = os.path.join(output_dir, name)
    print(f"Downloading: {name}...", end=" ", flush=True)

    try:
        urllib.request.urlretrieve(url, dest)
        size = os.path.getsize(dest)
        print(f"OK ({size:,} bytes)")
        downloaded += 1
    except Exception as e:
        print(f"FAILED: {e}")

if target_file and downloaded == 0:
    print(f"\nFile '{target_file}' not found in output files.")
    print("Available files:")
    for f in files:
        name = f.file_name if hasattr(f, 'file_name') else str(f)
        print(f"  - {name}")
    sys.exit(1)

print(f"\nDownloaded {downloaded} file(s) to: {output_dir}")
PYEOF
