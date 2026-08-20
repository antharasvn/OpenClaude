#!/usr/bin/env bash
# telegram-sender — Send messages, files, and photos via Telegram Bot API
# Usage: send.sh --text "message" --chat CHAT_ID
#        send.sh --file /path/to/file --chat CHAT_ID [--caption "text"]
#        send.sh --photo /path/to/image.jpg --chat CHAT_ID [--caption "text"]
#        send.sh --photo-url "https://example.com/img.jpg" --chat CHAT_ID [--caption "text"]

set -euo pipefail

# Every curl below carries --connect-timeout/--max-time (added 2026-08-20 2004z).
# CLAUDE.md's only global rule bans WebFetch *because it hangs* and prescribes
# `curl -sL --max-time 15`; that rule was read as syntax for FETCHING a URL, so
# the fleet's outbound delivery path — four curls, zero timeout flags — was exempt
# from the one rule written to prevent exactly this. curl has no default overall
# timeout: once connected, a stalled read blocks forever. The bot's own .err log
# carries 201 NetworkError / 200 httpx.ConnectError to api.telegram.org, so the
# hang is not hypothetical. A hang here is maximally expensive: sends happen at
# cycle end, so it burns the rest of the 600 s cap and produces rc=124 with a
# heartbeat commit already in-window — which run.sh's 1922z branch now books as
# "truncated success", i.e. no alert. Fail fast and loud instead: on timeout curl
# exits 28 and `set -e` propagates it to the caller.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Load project .env (infrastructure skill — needs TELEGRAM_BOT_TOKEN)
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

# Defaults
BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
CHAT_ID="${TELEGRAM_CHAT_ID:-}"
TEXT=""
FILE=""
PHOTO=""
PHOTO_URL=""
CAPTION=""
PARSE_MODE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --text)
            TEXT="$2"
            shift 2
            ;;
        --file)
            FILE="$2"
            shift 2
            ;;
        --photo)
            PHOTO="$2"
            shift 2
            ;;
        --photo-url)
            PHOTO_URL="$2"
            shift 2
            ;;
        --chat)
            CHAT_ID="$2"
            shift 2
            ;;
        --caption)
            CAPTION="$2"
            shift 2
            ;;
        --html)
            PARSE_MODE="HTML"
            shift
            ;;
        --markdown)
            PARSE_MODE="MarkdownV2"
            shift
            ;;
        --token)
            BOT_TOKEN="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# Validate required params
if [[ -z "$BOT_TOKEN" ]]; then
    echo "Error: TELEGRAM_BOT_TOKEN not set. Pass --token or set in .env" >&2
    exit 1
fi

if [[ -z "$CHAT_ID" ]]; then
    echo "Error: No chat ID. Pass --chat or set TELEGRAM_CHAT_ID in .env" >&2
    exit 1
fi

API_BASE="https://api.telegram.org/bot${BOT_TOKEN}"

# Send text message
if [[ -n "$TEXT" ]]; then
    # Prevent curl from interpreting @ or < as file references
    if [[ "$TEXT" == @* ]] || [[ "$TEXT" == \<* ]]; then
        TEXT=" $TEXT"
    fi
    PAYLOAD=(
        -F "chat_id=$CHAT_ID"
        -F "text=$TEXT"
    )
    if [[ -n "$PARSE_MODE" ]]; then
        PAYLOAD+=(-F "parse_mode=$PARSE_MODE")
    fi

    RESPONSE=$(curl -s --connect-timeout 10 --max-time 20 -w "\n%{http_code}" "${API_BASE}/sendMessage" "${PAYLOAD[@]}")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [[ "$HTTP_CODE" -ne 200 ]]; then
        echo "Error: Telegram API returned HTTP $HTTP_CODE" >&2
        echo "$BODY" >&2
        exit 2
    fi

    echo "Message sent successfully"
    exit 0
fi

# Send photo from file
if [[ -n "$PHOTO" ]]; then
    if [[ ! -f "$PHOTO" ]]; then
        echo "Error: Photo file not found: $PHOTO" >&2
        exit 1
    fi

    PAYLOAD=(
        -F "chat_id=$CHAT_ID"
        -F "photo=@$PHOTO"
    )
    if [[ -n "$CAPTION" ]]; then
        PAYLOAD+=(-F "caption=$CAPTION")
    fi
    if [[ -n "$PARSE_MODE" ]]; then
        PAYLOAD+=(-F "parse_mode=$PARSE_MODE")
    fi

    RESPONSE=$(curl -s --connect-timeout 10 --max-time 120 -w "\n%{http_code}" "${API_BASE}/sendPhoto" "${PAYLOAD[@]}")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [[ "$HTTP_CODE" -ne 200 ]]; then
        echo "Error: Telegram API returned HTTP $HTTP_CODE" >&2
        echo "$BODY" >&2
        exit 2
    fi

    echo "Photo sent successfully"
    exit 0
fi

# Send photo from URL
if [[ -n "$PHOTO_URL" ]]; then
    PAYLOAD=(
        -F "chat_id=$CHAT_ID"
        -F "photo=$PHOTO_URL"
    )
    if [[ -n "$CAPTION" ]]; then
        PAYLOAD+=(-F "caption=$CAPTION")
    fi
    if [[ -n "$PARSE_MODE" ]]; then
        PAYLOAD+=(-F "parse_mode=$PARSE_MODE")
    fi

    RESPONSE=$(curl -s --connect-timeout 10 --max-time 120 -w "\n%{http_code}" "${API_BASE}/sendPhoto" "${PAYLOAD[@]}")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [[ "$HTTP_CODE" -ne 200 ]]; then
        echo "Error: Telegram API returned HTTP $HTTP_CODE" >&2
        echo "$BODY" >&2
        exit 2
    fi

    echo "Photo sent successfully (from URL)"
    exit 0
fi

# Send file
if [[ -n "$FILE" ]]; then
    if [[ ! -f "$FILE" ]]; then
        echo "Error: File not found: $FILE" >&2
        exit 1
    fi

    PAYLOAD=(
        -F "chat_id=$CHAT_ID"
        -F "document=@$FILE"
    )
    if [[ -n "$CAPTION" ]]; then
        PAYLOAD+=(-F "caption=$CAPTION")
    fi
    if [[ -n "$PARSE_MODE" ]]; then
        PAYLOAD+=(-F "parse_mode=$PARSE_MODE")
    fi

    RESPONSE=$(curl -s --connect-timeout 10 --max-time 120 -w "\n%{http_code}" "${API_BASE}/sendDocument" "${PAYLOAD[@]}")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [[ "$HTTP_CODE" -ne 200 ]]; then
        echo "Error: Telegram API returned HTTP $HTTP_CODE" >&2
        echo "$BODY" >&2
        exit 2
    fi

    echo "File sent successfully"
    exit 0
fi

echo "Error: No --text, --file, --photo, or --photo-url provided" >&2
exit 1
