#!/usr/bin/env bash
# kaggle-compete — Check notebook/kernel execution status
# Usage: ./skills/kaggle-compete/check-status.sh <kernel_slug> [--poll] [--logs]

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
POLL="false"
SHOW_LOGS="false"
POLL_INTERVAL="15"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --poll)
            POLL="true"
            shift
            ;;
        --logs)
            SHOW_LOGS="true"
            shift
            ;;
        --interval)
            POLL_INTERVAL="${2:-15}"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 <kernel_ref> [OPTIONS]"
            echo ""
            echo "Check notebook/kernel execution status on Kaggle."
            echo ""
            echo "Arguments:"
            echo "  <kernel_ref>        Kernel reference: username/kernel-slug or URL"
            echo ""
            echo "Options:"
            echo "  --poll              Poll until kernel completes or errors"
            echo "  --interval <sec>    Poll interval in seconds (default: 15)"
            echo "  --logs              Show execution logs"
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
    echo "Usage: $0 <kernel_ref> [--poll] [--logs]" >&2
    echo "Example: $0 username/my-notebook --poll --logs" >&2
    exit 1
fi

# Validate Kaggle credentials
if [[ -z "${KAGGLE_USERNAME:-}" ]] || [[ -z "${KAGGLE_KEY:-}" ]]; then
    echo "Error: KAGGLE_USERNAME and KAGGLE_KEY must be set in .env" >&2
    exit 1
fi

export KAGGLE_USERNAME
export KAGGLE_KEY

python3 - "$KERNEL_REF" "$POLL" "$SHOW_LOGS" "$POLL_INTERVAL" <<'PYEOF'
import sys
import os
import re
import time

kernel_ref = sys.argv[1]
poll = sys.argv[2] == "true"
show_logs = sys.argv[3] == "true"
poll_interval = int(sys.argv[4])

from kagglehub import auth
from kagglehub.clients import build_kaggle_client
from kagglesdk.kernels.types.kernels_api_service import (
    ApiGetKernelSessionStatusRequest,
    ApiListKernelSessionOutputRequest,
)

kaggle_key = os.environ.get("KAGGLE_KEY", "")
username = os.environ.get("KAGGLE_USERNAME", "")
if kaggle_key.startswith("KGAT_"):
    auth.set_kaggle_api_token(kaggle_key)
else:
    auth.set_kaggle_credentials(username, kaggle_key)

client = build_kaggle_client()

# Parse kernel reference
# Formats: username/kernel-slug, URL
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

def check_status():
    req = ApiGetKernelSessionStatusRequest()
    req.user_name = owner
    req.kernel_slug = kernel_slug
    resp = client.kernels.kernels_api_client.get_kernel_session_status(req)
    return resp

def get_logs():
    try:
        req = ApiListKernelSessionOutputRequest()
        req.user_name = owner
        req.kernel_slug = kernel_slug
        resp = client.kernels.kernels_api_client.list_kernel_session_output(req)
        return resp
    except Exception as e:
        return None

print(f"Checking status for: {owner}/{kernel_slug}")
print()

terminal_states = {"complete", "error", "cancelAcknowledged", "cancelled"}

while True:
    try:
        resp = check_status()
        status = resp.status or "unknown"

        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] Status: {status}")

        if resp.failure_message:
            print(f"  Failure: {resp.failure_message}")

        if show_logs or status in terminal_states:
            log_resp = get_logs()
            if log_resp:
                if log_resp.log:
                    print("\n--- Execution Log ---")
                    print(log_resp.log[-2000:] if len(log_resp.log or "") > 2000 else log_resp.log)
                    print("--- End Log ---\n")

                if log_resp.files:
                    print("Output files:")
                    for f in log_resp.files:
                        name = f.file_name if hasattr(f, 'file_name') else str(f)
                        url = f.url if hasattr(f, 'url') else ""
                        print(f"  - {name}")

        if status in terminal_states:
            if status == "complete":
                print("\nKernel execution completed successfully.")
            elif status == "error":
                print("\nKernel execution failed.")
                sys.exit(1)
            else:
                print(f"\nKernel execution ended with status: {status}")
            break

        if not poll:
            if status not in terminal_states:
                print("\nKernel is still running. Use --poll to wait for completion.")
            break

        time.sleep(poll_interval)

    except Exception as e:
        print(f"Error checking status: {e}", file=sys.stderr)
        if not poll:
            sys.exit(1)
        time.sleep(poll_interval)
PYEOF
