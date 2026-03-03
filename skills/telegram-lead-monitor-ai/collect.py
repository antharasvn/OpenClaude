#!/usr/bin/env python3
"""
Telegram Message Collector — fetches recent messages from all group chats
and saves them to a JSON file for analysis by the Claude coordinator.

This script does NO analysis. It only collects and saves messages.
Designed for cron invocation every hour.
"""

import argparse
import asyncio
import json
import logging
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from telethon import TelegramClient
from telethon.tl.types import User

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_ID = int(os.environ.get("TG_MONITOR_API_ID", 0))
API_HASH = os.environ.get("TG_MONITOR_API_HASH", "")
PHONE = os.environ.get("TG_MONITOR_PHONE", "")

# Time window: fetch messages from the last N minutes
FETCH_WINDOW_MINUTES = 65  # slightly more than 60 to avoid gaps between cron runs
MAX_MESSAGES_PER_CHAT = 100
MIN_MESSAGE_LENGTH = 20

SCRIPT_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(workspace_dir: str) -> logging.Logger:
    log_dir = Path(workspace_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("lead-collector")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        fh = logging.FileHandler(log_dir / "lead-monitor-ai.log", encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(fh)

        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(logging.INFO)
        sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(sh)

    return logger


# ---------------------------------------------------------------------------
# SQLite state tracking (minimal — only tracks last processed message IDs)
# ---------------------------------------------------------------------------

class StateDB:
    """Track per-chat last processed message IDs."""

    def __init__(self, workspace_dir: str):
        db_path = Path(workspace_dir) / "lead-monitor-ai.db"
        self.conn = sqlite3.connect(str(db_path))
        self._init_tables()

    def _init_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS state (
                chat_id INTEGER PRIMARY KEY,
                last_message_id INTEGER,
                last_run_time TEXT
            )
        """)
        # Keep leads table for dedup (coordinator will use it)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                message_id INTEGER,
                text TEXT,
                score INTEGER,
                priority TEXT,
                sent_at TEXT,
                text_hash TEXT,
                UNIQUE(chat_id, message_id)
            )
        """)
        self.conn.commit()

    def get_last_message_id(self, chat_id: int) -> int:
        cur = self.conn.execute(
            "SELECT last_message_id FROM state WHERE chat_id = ?",
            (chat_id,),
        )
        row = cur.fetchone()
        return row[0] if row and row[0] else 0

    def update_state(self, chat_id: int, last_message_id: int):
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """INSERT INTO state (chat_id, last_message_id, last_run_time)
               VALUES (?, ?, ?)
               ON CONFLICT(chat_id)
               DO UPDATE SET last_message_id = MAX(last_message_id, ?), last_run_time = ?""",
            (chat_id, last_message_id, now, last_message_id, now),
        )
        self.conn.commit()

    def cleanup_old_leads(self):
        """Remove leads older than 7 days."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        self.conn.execute("DELETE FROM leads WHERE sent_at < ?", (cutoff,))
        self.conn.commit()

    def close(self):
        self.conn.close()


# ---------------------------------------------------------------------------
# Chat/message helpers
# ---------------------------------------------------------------------------

def build_message_link(chat, message_id: int) -> str:
    if hasattr(chat, "username") and chat.username:
        return f"https://t.me/{chat.username}/{message_id}"
    chat_id = getattr(chat, "id", 0)
    return f"https://t.me/c/{chat_id}/{message_id}"


def get_chat_name(chat) -> str:
    if hasattr(chat, "title") and chat.title:
        return chat.title
    if isinstance(chat, User):
        parts = [chat.first_name or "", chat.last_name or ""]
        return " ".join(p for p in parts if p) or "Unknown User"
    return "Unknown Chat"


# ---------------------------------------------------------------------------
# Main collector
# ---------------------------------------------------------------------------

async def collect_messages(workspace_dir: str) -> str | None:
    """Collect recent messages from all group chats and save to JSON.

    Returns the path to the JSON file if messages were found, None otherwise.
    """
    logger = setup_logging(workspace_dir)
    logger.info("=" * 50)
    logger.info("Message Collector — starting")

    # Validate config
    if not API_ID or not API_HASH or not PHONE:
        logger.error("Missing TG_MONITOR_API_ID, TG_MONITOR_API_HASH, or TG_MONITOR_PHONE")
        sys.exit(1)

    # Initialize
    session_path = Path(workspace_dir) / "lead-monitor-session"
    tg_client = TelegramClient(str(session_path), API_ID, API_HASH)
    db = StateDB(workspace_dir)
    db.cleanup_old_leads()

    collected_messages = []

    try:
        await tg_client.start(phone=PHONE)
        me = await tg_client.get_me()
        logger.info(f"Connected as: {me.first_name} (ID: {me.id})")

        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=FETCH_WINDOW_MINUTES)
        chats_checked = 0

        async for dialog in tg_client.iter_dialogs():
            chat = dialog.entity
            chat_id = dialog.id
            chat_name = get_chat_name(chat)

            # Monitor all chats (groups, channels, and private chats)

            last_processed_id = db.get_last_message_id(chat_id)
            max_msg_id = last_processed_id

            try:
                async for msg in tg_client.iter_messages(
                    chat,
                    offset_date=cutoff_time,
                    reverse=True,
                    limit=MAX_MESSAGES_PER_CHAT,
                ):
                    if msg.id <= last_processed_id:
                        continue
                    if msg.id > max_msg_id:
                        max_msg_id = msg.id
                    if not msg.text or len(msg.text) < MIN_MESSAGE_LENGTH:
                        continue
                    if msg.sender_id == me.id:
                        continue

                    # Collect the message
                    collected_messages.append({
                        "chat_id": chat_id,
                        "chat_name": chat_name,
                        "message_id": msg.id,
                        "sender_id": msg.sender_id,
                        "text": msg.text,
                        "date": msg.date.isoformat() if msg.date else None,
                        "link": build_message_link(chat, msg.id),
                    })

            except Exception as e:
                logger.debug(f"Could not fetch from '{chat_name}': {e}")
                continue

            if max_msg_id > last_processed_id:
                db.update_state(chat_id, max_msg_id)
                chats_checked += 1

        logger.info(f"Collected {len(collected_messages)} messages from {chats_checked} chats")

        if not collected_messages:
            logger.info("No new messages to analyze")
            return None

        # Save to JSON with timestamp in filename
        temp_dir = Path(workspace_dir) / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        output_path = temp_dir / f"pending-messages-{timestamp}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(collected_messages, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved messages to {output_path}")
        return str(output_path)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()
        await tg_client.disconnect()
        logger.info("Disconnected")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Telegram Message Collector")
    parser.add_argument(
        "--workspace",
        default=os.environ.get("OPENCLAUDE_WORKSPACE_DIR", os.getcwd()),
        help="Workspace directory for session, DB, and logs",
    )
    args = parser.parse_args()
    result = asyncio.run(collect_messages(args.workspace))

    # Print the output path so run.sh can capture it
    if result:
        print(f"OUTPUT_FILE={result}")
    else:
        print("OUTPUT_FILE=")


if __name__ == "__main__":
    main()
