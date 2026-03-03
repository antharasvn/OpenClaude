#!/usr/bin/env python3
"""
Telegram Lead Monitor — watches all chats for software development lead requests.

Uses Telethon (User API) to listen to messages and keyword matching to classify them.
Sends notifications via telegram-sender skill when a lead is detected.
"""

import argparse
import asyncio
import logging
import os
import re
import signal
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from telethon import TelegramClient, events
from telethon.tl.types import (
    Channel,
    Chat,
    User,
    PeerChannel,
    PeerChat,
    PeerUser,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_ID = int(os.environ.get("TG_MONITOR_API_ID", 0))
API_HASH = os.environ.get("TG_MONITOR_API_HASH", "")
PHONE = os.environ.get("TG_MONITOR_PHONE", "")
ADMIN_CHAT_ID = int(os.environ.get("TG_MONITOR_ADMIN_CHAT_ID", 0))

# Skip messages shorter than this (unlikely to be a lead)
MIN_MESSAGE_LENGTH = 20

# Project directory (for telegram-sender path)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent.parent

# ---------------------------------------------------------------------------
# Keyword-based lead detection
# ---------------------------------------------------------------------------

# Keywords/phrases that indicate someone is looking for a developer.
# Order: longer phrases first (checked via regex alternation, first match wins for context).
LEAD_KEYWORDS = [
    # Russian phrases
    "нужен разработчик",
    "ищу программист",
    "ищу разработчик",
    "заказ сайта",
    "разработка под ключ",
    "сделать сайт",
    "сделать приложени",
    "нужен программист",
    "ищу фрилансер",
    "нужен фрилансер",
    "требуется разработ",
    "требуется программист",
    "кто может сделать",
    "кто сделает",
    "нужно разработать",
    "нужно сделать сайт",
    "нужно сделать приложени",
    "заказать разработ",
    "заказать сайт",
    "заказать приложени",
    # Russian stems (partial match)
    "разработ",
    "фриланс",
    "заказать",
    "программист",
    # English phrases
    "need developer",
    "need a developer",
    "looking for programmer",
    "looking for developer",
    "looking for a developer",
    "looking for a programmer",
    "website order",
    "app development",
    "create app",
    "create a website",
    "create website",
    "make website",
    "make a website",
    "make an app",
    "build a website",
    "build an app",
    "hire developer",
    "hire a developer",
    "hire programmer",
    "hire a programmer",
    "need programmer",
    "need a programmer",
    # English stems
    "freelance",
    "freelancer",
]

# Build a single compiled regex for fast matching.
# Uses word-boundary-like matching where possible but allows partial stems.
_escaped = [re.escape(kw) for kw in LEAD_KEYWORDS]
LEAD_PATTERN = re.compile("|".join(_escaped), re.IGNORECASE)


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging(workspace_dir: str) -> logging.Logger:
    """Configure logging to file and stderr."""
    log_dir = Path(workspace_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "lead-monitor.log"

    logger = logging.getLogger("lead-monitor")
    logger.setLevel(logging.INFO)

    # File handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(fh)

    # Stderr handler (for nohup/journalctl)
    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.WARNING)
    sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(sh)

    return logger


# ---------------------------------------------------------------------------
# SQLite dedup database
# ---------------------------------------------------------------------------

class MessageDB:
    """Track processed message IDs to prevent duplicates."""

    def __init__(self, workspace_dir: str):
        db_path = Path(workspace_dir) / "lead-monitor.db"
        self.conn = sqlite3.connect(str(db_path))
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_messages (
                chat_id INTEGER,
                message_id INTEGER,
                processed_at TEXT,
                is_lead INTEGER DEFAULT 0,
                PRIMARY KEY (chat_id, message_id)
            )
        """)
        # Clean up old entries (keep last 7 days)
        self.conn.execute("""
            DELETE FROM processed_messages
            WHERE processed_at < datetime('now', '-7 days')
        """)
        self.conn.commit()

    def is_processed(self, chat_id: int, message_id: int) -> bool:
        cur = self.conn.execute(
            "SELECT 1 FROM processed_messages WHERE chat_id=? AND message_id=?",
            (chat_id, message_id),
        )
        return cur.fetchone() is not None

    def mark_processed(self, chat_id: int, message_id: int, is_lead: bool = False):
        self.conn.execute(
            "INSERT OR IGNORE INTO processed_messages (chat_id, message_id, processed_at, is_lead) VALUES (?, ?, ?, ?)",
            (chat_id, message_id, datetime.utcnow().isoformat(), int(is_lead)),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()


# ---------------------------------------------------------------------------
# Keyword-based lead analyzer
# ---------------------------------------------------------------------------

class LeadAnalyzer:
    """Analyze messages using keyword matching."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    async def analyze(self, message_text: str, chat_name: str, chat_type: str) -> tuple[bool, str]:
        """
        Analyze a message for lead potential using keyword matching.
        Returns (is_lead, description).
        """
        match = LEAD_PATTERN.search(message_text)
        if not match:
            return False, ""

        # Extract ~100 chars around the matched keyword as description
        start = max(0, match.start() - 50)
        end = min(len(message_text), match.end() + 50)
        snippet = message_text[start:end].strip()

        # Clean up: replace newlines with spaces, collapse whitespace
        snippet = re.sub(r"\s+", " ", snippet)

        # Add ellipsis if we trimmed
        if start > 0:
            snippet = "..." + snippet
        if end < len(message_text):
            snippet = snippet + "..."

        description = f"[{match.group()}] {snippet}"
        return True, description


# ---------------------------------------------------------------------------
# Notification sender
# ---------------------------------------------------------------------------

def send_notification(chat_name: str, description: str, message_link: str, admin_chat_id: int):
    """Send lead notification via telegram-sender skill."""
    text = (
        f"🎯 <b>Ищут разработчика:</b>\n\n"
        f"{description}\n\n"
        f"💬 Chat: {chat_name}\n"
        f"🔗 Link: {message_link}"
    )

    sender_script = PROJECT_DIR / "skills" / "telegram-sender" / "send.sh"
    if not sender_script.exists():
        logging.getLogger("lead-monitor").error(
            f"telegram-sender not found at {sender_script}"
        )
        return

    try:
        subprocess.run(
            [
                str(sender_script),
                "--text", text,
                "--chat", str(admin_chat_id),
                "--html",
            ],
            timeout=30,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        logging.getLogger("lead-monitor").error(
            f"Failed to send notification: {e.stderr.decode()}"
        )
    except subprocess.TimeoutExpired:
        logging.getLogger("lead-monitor").error("telegram-sender timed out")


# ---------------------------------------------------------------------------
# Message link builder
# ---------------------------------------------------------------------------

def build_message_link(chat, message_id: int) -> str:
    """Build a t.me link for the message."""
    if hasattr(chat, "username") and chat.username:
        return f"https://t.me/{chat.username}/{message_id}"
    # For private chats/groups without username, use c/ format
    chat_id = getattr(chat, "id", 0)
    return f"https://t.me/c/{chat_id}/{message_id}"


def get_chat_type(chat) -> str:
    """Return human-readable chat type."""
    if isinstance(chat, Channel):
        return "channel/supergroup"
    elif isinstance(chat, Chat):
        return "group"
    elif isinstance(chat, User):
        return "private"
    return "unknown"


def get_chat_name(chat) -> str:
    """Return a display name for the chat."""
    if hasattr(chat, "title") and chat.title:
        return chat.title
    if isinstance(chat, User):
        parts = [chat.first_name or "", chat.last_name or ""]
        return " ".join(p for p in parts if p) or "Unknown User"
    return "Unknown Chat"


# ---------------------------------------------------------------------------
# Main monitor
# ---------------------------------------------------------------------------

async def run_monitor(workspace_dir: str, auth_only: bool = False):
    """Main monitoring loop."""
    logger = setup_logging(workspace_dir)
    logger.info("=" * 60)
    logger.info("Lead monitor starting up")

    # Validate config
    if not API_ID or not API_HASH or not PHONE:
        logger.error("Missing TG_MONITOR_API_ID, TG_MONITOR_API_HASH, or TG_MONITOR_PHONE")
        sys.exit(1)

    if not auth_only and not ADMIN_CHAT_ID:
        logger.error("Missing TG_MONITOR_ADMIN_CHAT_ID")
        sys.exit(1)

    # Session file in workspace
    session_path = Path(workspace_dir) / "lead-monitor-session"
    client = TelegramClient(str(session_path), API_ID, API_HASH)

    await client.start(phone=PHONE)
    logger.info("Telegram client connected")

    me = await client.get_me()
    logger.info(f"Logged in as: {me.first_name} (ID: {me.id})")

    if auth_only:
        print(f"Authentication successful! Logged in as {me.first_name} (ID: {me.id})")
        print(f"Session saved to: {session_path}.session")
        await client.disconnect()
        return

    # Initialize components
    db = MessageDB(workspace_dir)
    analyzer = LeadAnalyzer(logger)
    my_id = me.id

    @client.on(events.NewMessage)
    async def handler(event):
        """Process each new message."""
        try:
            # Skip own messages
            if event.sender_id == my_id:
                return

            # Skip empty or very short messages
            text = event.raw_text or ""
            if len(text) < MIN_MESSAGE_LENGTH:
                return

            chat_id = event.chat_id
            message_id = event.id

            # Skip already processed
            if db.is_processed(chat_id, message_id):
                return

            # Get chat info
            chat = await event.get_chat()
            chat_name = get_chat_name(chat)
            chat_type = get_chat_type(chat)

            logger.info(f"Checking message from '{chat_name}' ({chat_type}): {text[:80]}...")

            # Analyze with keyword matching
            is_lead, description = await analyzer.analyze(text, chat_name, chat_type)

            # Mark as processed
            db.mark_processed(chat_id, message_id, is_lead)

            if is_lead:
                logger.info(f"LEAD FOUND in '{chat_name}': {description}")
                message_link = build_message_link(chat, message_id)

                # Send notification in a thread to not block the event loop
                await asyncio.to_thread(
                    send_notification, chat_name, description, message_link, ADMIN_CHAT_ID
                )
            else:
                logger.info(f"Not a lead ('{chat_name}')")

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

    logger.info(f"Monitoring started (keyword mode). Notifications go to chat {ADMIN_CHAT_ID}")
    print(f"Lead monitor running (keyword mode). Watching for development leads...")
    print(f"Notifications will be sent to chat ID: {ADMIN_CHAT_ID}")

    # Graceful shutdown handling
    stop_event = asyncio.Event()

    def shutdown_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        stop_event.set()

    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)

    # Run until stopped
    try:
        await stop_event.wait()
    finally:
        logger.info("Shutting down gracefully...")
        db.close()
        await client.disconnect()
        logger.info("Lead monitor stopped.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Telegram Lead Monitor")
    parser.add_argument(
        "--workspace", default=os.getcwd(),
        help="Workspace directory for session, DB, and logs",
    )
    parser.add_argument(
        "--auth-only", action="store_true",
        help="Only authenticate and save session, then exit",
    )
    args = parser.parse_args()

    asyncio.run(run_monitor(args.workspace, args.auth_only))


if __name__ == "__main__":
    main()
