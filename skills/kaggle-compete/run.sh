#!/usr/bin/env bash
# kaggle-compete — Upload a Kaggle notebook to a competition
# Usage: ./skills/kaggle-compete/run.sh <competition_url> [--notebook <path>]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source workspace .env (user credentials)
if [[ -f "$PWD/.env" ]]; then
    set -a
    source "$PWD/.env"
    set +a
fi

# Parse arguments
COMPETITION_URL=""
NOTEBOOK_PATH=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --notebook)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --notebook requires a path argument" >&2
                exit 1
            fi
            NOTEBOOK_PATH="$2"
            shift 2
            ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            if [[ -z "$COMPETITION_URL" ]]; then
                COMPETITION_URL="$1"
            else
                echo "Error: unexpected argument: $1" >&2
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate required arguments
if [[ -z "$COMPETITION_URL" ]]; then
    echo "Usage: $0 <competition_url> [--notebook <path>]" >&2
    echo "Example: $0 https://www.kaggle.com/competitions/titanic --notebook solution.ipynb" >&2
    exit 1
fi

# Validate Kaggle credentials
if [[ -z "${KAGGLE_USERNAME:-}" ]] || [[ -z "${KAGGLE_KEY:-}" ]]; then
    echo "Error: KAGGLE_USERNAME and KAGGLE_KEY must be set in .env" >&2
    exit 1
fi

# Export for kagglehub / kagglesdk
export KAGGLE_USERNAME
export KAGGLE_KEY

# Extract competition slug from URL
# Handles:
#   https://www.kaggle.com/competitions/{slug}
#   https://www.kaggle.com/competitions/{slug}/overview
#   https://www.kaggle.com/c/{slug}
SLUG=""
if [[ "$COMPETITION_URL" =~ kaggle\.com/competitions/([^/]+) ]]; then
    SLUG="${BASH_REMATCH[1]}"
elif [[ "$COMPETITION_URL" =~ kaggle\.com/c/([^/]+) ]]; then
    SLUG="${BASH_REMATCH[1]}"
else
    echo "Error: Could not extract competition slug from URL." >&2
    echo "Expected format: https://www.kaggle.com/competitions/{slug}" >&2
    echo "If using an invite link (kaggle.com/t/...), resolve it to a competition URL first." >&2
    exit 1
fi

echo "Competition slug: $SLUG"

# Validate notebook
if [[ -z "$NOTEBOOK_PATH" ]]; then
    echo "Error: --notebook <path> is required. Provide a .ipynb notebook to upload." >&2
    echo "Example: $0 $COMPETITION_URL --notebook solution.ipynb" >&2
    exit 1
fi

if [[ ! -f "$NOTEBOOK_PATH" ]]; then
    echo "Error: Notebook not found: $NOTEBOOK_PATH" >&2
    exit 1
fi

# Generate a unique kernel slug (lowercase, alphanumeric + hyphens)
KERNEL_SLUG="${SLUG}-solution-$(date +%s)"

echo "Pushing notebook to Kaggle via kagglehub..."
echo "  Kernel slug: ${KAGGLE_USERNAME}/${KERNEL_SLUG}"
echo "  Notebook: $(basename "$NOTEBOOK_PATH")"
echo "  Competition: ${SLUG}"

# Use kagglehub's kagglesdk to push the notebook
python3 - "$NOTEBOOK_PATH" "$KAGGLE_USERNAME" "$KERNEL_SLUG" "$SLUG" "$PWD" <<'PYEOF'
import sys
import json
import os

notebook_path = sys.argv[1]
username = sys.argv[2]
kernel_slug = sys.argv[3]
competition_slug = sys.argv[4]
workspace_dir = sys.argv[5]

# Read notebook content as JSON text
with open(notebook_path, "r") as f:
    notebook_text = f.read()

# Validate it's valid JSON (ipynb format)
try:
    json.loads(notebook_text)
except json.JSONDecodeError as e:
    print(f"Error: Invalid notebook JSON: {e}", file=sys.stderr)
    sys.exit(1)

# Build and send the SaveKernel request via kagglesdk
from kagglehub import auth
from kagglehub.clients import build_kaggle_client
from kagglesdk.kernels.types.kernels_api_service import ApiSaveKernelRequest

# Set credentials explicitly (required for KGAT tokens)
kaggle_key = os.environ.get("KAGGLE_KEY", "")
if kaggle_key.startswith("KGAT_"):
    # New token format - use set_kaggle_api_token
    auth.set_kaggle_api_token(kaggle_key)
else:
    # Legacy format - use set_kaggle_credentials
    auth.set_kaggle_credentials(username, kaggle_key)

client = build_kaggle_client()

req = ApiSaveKernelRequest()
req.slug = f"{username}/{kernel_slug}"
req.new_title = f"{competition_slug} solution"
req.text = notebook_text
req.language = "python"
req.kernel_type = "notebook"
req.is_private = True
req.enable_gpu = True
req.enable_internet = True
req.competition_data_sources = [competition_slug]

response = client.kernels.kernels_api_client.save_kernel(req)

if response.error:
    print(f"Error from Kaggle API: {response.error}", file=sys.stderr)
    sys.exit(1)

notebook_url = response.url
if not notebook_url:
    notebook_url = f"https://www.kaggle.com/code/{username}/{kernel_slug}"

# Save URL for downstream use
os.makedirs(os.path.join(workspace_dir, "temp"), exist_ok=True)
with open(os.path.join(workspace_dir, "temp", "notebook_url.txt"), "w") as f:
    f.write(notebook_url + "\n")

print()
print("Notebook uploaded successfully!")
print(f"URL: {notebook_url}")
if response.version_number:
    print(f"Version: {response.version_number}")
print()
print("Note: The notebook may take a few minutes to appear on Kaggle.")
print("It will run automatically once processed.")
PYEOF
