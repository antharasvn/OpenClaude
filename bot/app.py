"""Application builder, post_init, post_shutdown, main()."""

import nonexistent_module_for_rollback_test  # INTENTIONAL BREAK: testing rollback

import asyncio
import atexit
import json
import re
import sys

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot.config import (
    ALLOWED_USERS, ACTIVE_STREAMS_FILE, RESTART_MESSAGES_FILE,
    RESTART_STATE_FILE, SESSION_FILE, TELEGRAM_BOT_TOKEN, WORKING_DIR,
)
from bot.logging_setup import logger, infra_logger
from bot.sessions import get_session_id
from bot.streams import load_active_streams
from bot.workspaces import get_working_dir
from bot.renderer import TelegramRenderer, split_message
from bot.claude import stream_claude, _active_procs
from bot.sdk_session import HAS_SDK, cleanup_idle_sessions, shutdown_sdk_sessions
from bot import handlers
from commands import register_all, ALL_COMMANDS


# Monkey-patch asyncio event loop to diagnose tight loop (CPU spike)
_original_run_once = asyncio.BaseEventLoop._run_once
_loop_iteration_count = 0
_loop_iteration_start = None

def _instrumented_run_once(self, timeout=None):
    """Instrumented version of _run_once to detect tight loops."""
    import time
    global _loop_iteration_count, _loop_iteration_start

    if _loop_iteration_start is None:
        _loop_iteration_start = time.time()

    _loop_iteration_count += 1

    # Log every 10000 iterations or every 5 seconds
    now = time.time()
    elapsed = now - _loop_iteration_start
    if _loop_iteration_count >= 10000 or elapsed >= 5.0:
        rate = _loop_iteration_count / elapsed if elapsed > 0 else 0
        if rate > 1000:  # More than 1000 iterations/sec = tight loop
            # Log diagnostic info about ready queue and scheduled callbacks
            ready_len = len(self._ready)
            scheduled_len = len(self._scheduled)
            logger.warning(
                "Event loop tight loop: %d iter in %.2fs (%.0f/sec), "
                "ready=%d, scheduled=%d, timeout=%s",
                _loop_iteration_count, elapsed, rate,
                ready_len, scheduled_len, timeout
            )
        _loop_iteration_count = 0
        _loop_iteration_start = now

    return _original_run_once(self)

asyncio.BaseEventLoop._run_once = _instrumented_run_once


def main() -> None:
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set. Check your .env file.")
        sys.exit(1)

    if not ALLOWED_USERS:
        logger.warning(
            "ALLOWED_USERS is empty. No one will be able to use the bot. "
            "Set ALLOWED_USERS in .env with your Telegram user ID."
        )
        infra_logger.warning("ALLOWED_USERS is empty — no one is authorized")

    logger.info("Starting OpenClaude Telegram bot...")
    logger.info("Allowed users: %s", ALLOWED_USERS)
    logger.info("Working directory: %s", WORKING_DIR)
    logger.info("Session file: %s", SESSION_FILE)
    infra_logger.info("Bot starting — users=%s, workdir=%s", ALLOWED_USERS, WORKING_DIR)

    atexit.register(lambda: infra_logger.info("Bot process exiting"))

    renderer = TelegramRenderer()

    async def _monitor_cpu_usage() -> None:
        """Monitor bot CPU usage and log warnings if it spikes."""
        import os
        import psutil
        bot_pid = os.getpid()
        process = psutil.Process(bot_pid)

        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                loop = asyncio.get_running_loop()
                cpu_percent = await loop.run_in_executor(
                    None, process.cpu_percent, 1.0
                )

                if cpu_percent > 50.0:
                    # Get thread count and memory usage for context
                    num_threads = process.num_threads()
                    mem_mb = process.memory_info().rss / 1024 / 1024

                    logger.warning(
                        "High CPU usage detected: %.1f%% (threads=%d, mem=%.0fMB)",
                        cpu_percent, num_threads, mem_mb
                    )
                    infra_logger.warning(
                        "High CPU: %.1f%% (pid=%d, threads=%d, mem=%.0fMB)",
                        cpu_percent, bot_pid, num_threads, mem_mb
                    )
            except Exception as e:
                logger.error("CPU monitoring error: %s", e)
                await asyncio.sleep(60)  # Back off on error

    async def _cleanup_orphan_claude_processes() -> None:
        """Kill orphan claude processes from previous bot run (not children of this bot)."""
        import os
        import subprocess
        try:
            bot_pid = os.getpid()
            # Find all claude stream-json processes
            result = subprocess.run(
                ["pgrep", "-f", "claude.*stream-json"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return  # No claude processes found

            all_pids = result.stdout.strip().split("\n")
            all_pids = [int(p) for p in all_pids if p.strip().isdigit()]

            # Get children of current bot process (these are legitimate)
            children_result = subprocess.run(
                ["pgrep", "-P", str(bot_pid)],
                capture_output=True,
                text=True,
            )
            child_pids = set()
            if children_result.returncode == 0:
                child_pids = {int(p) for p in children_result.stdout.strip().split("\n") if p.strip().isdigit()}

            # Orphans = all claude pids - children of this bot
            orphans = [p for p in all_pids if p not in child_pids]

            if not orphans:
                return

            # Kill orphans (SIGTERM first, then SIGKILL)
            for pid in orphans:
                try:
                    subprocess.run(["kill", str(pid)], check=False)
                except Exception:
                    pass
            # Give them 2 seconds to gracefully exit
            await asyncio.sleep(2)
            # Force kill any survivors
            for pid in orphans:
                try:
                    subprocess.run(["kill", "-9", str(pid)], check=False)
                except Exception:
                    pass

            infra_logger.info("Cleaned up %d orphan claude process(es)", len(orphans))
            logger.info("Cleaned up %d orphan claude process(es)", len(orphans))
        except Exception as e:
            logger.warning("Failed to cleanup orphan processes: %s", e)

    async def post_init(application: Application) -> None:
        """Fetch bot info at startup and resume interrupted generations."""
        bot = application.bot
        me = await bot.get_me()
        handlers.BOT_USERNAME = me.username or ""
        logger.info("Bot username: @%s", handlers.BOT_USERNAME)
        infra_logger.info("Bot username: @%s", handlers.BOT_USERNAME)

        from telegram import BotCommand
        bot_commands = [
            BotCommand("start", "Show welcome message"),
            BotCommand("new", "Start a new conversation"),
            BotCommand("status", "Show session info"),
            BotCommand("stop", "Stop current generation"),
        ]
        for name, desc in ALL_COMMANDS:
            bot_commands.append(BotCommand(name, desc))
        await bot.set_my_commands(bot_commands)
        logger.info("Registered %d bot commands with Telegram", len(bot_commands))

        # Cleanup orphan claude processes from previous run
        await _cleanup_orphan_claude_processes()

        if HAS_SDK:
            asyncio.create_task(cleanup_idle_sessions())
            logger.info("SDK idle session cleanup task started")

        # Start CPU monitoring task
        try:
            import psutil
            asyncio.create_task(_monitor_cpu_usage())
            logger.info("CPU monitoring task started")
        except ImportError:
            logger.warning("psutil not installed, CPU monitoring disabled")

        # Edit "Restarting..." messages to show success
        if RESTART_MESSAGES_FILE.exists():
            try:
                msgs = json.loads(RESTART_MESSAGES_FILE.read_text())
                for entry in msgs:
                    try:
                        await bot.edit_message_text(
                            chat_id=entry["chat_id"],
                            message_id=entry["message_id"],
                            text="\u2705 Restart complete",
                        )
                    except Exception as e:
                        infra_logger.warning(
                            "Failed to edit restart message %s in chat %s: %s",
                            entry.get("message_id"), entry.get("chat_id"), e,
                        )
            except (json.JSONDecodeError, OSError) as e:
                infra_logger.warning("Failed to read restart messages file: %s", e)
            finally:
                RESTART_MESSAGES_FILE.unlink(missing_ok=True)

        # Collect interrupted chats from restart state and active streams
        interrupted: dict[str, dict] = {}

        for state_file in (RESTART_STATE_FILE, ACTIVE_STREAMS_FILE):
            if not state_file.exists():
                continue
            try:
                data = json.loads(state_file.read_text())
                interrupted.update(data)
            except (json.JSONDecodeError, OSError):
                pass
            finally:
                state_file.unlink(missing_ok=True)

        if not interrupted:
            return

        infra_logger.info("Resuming %d interrupted generation(s)", len(interrupted))

        RESUME_TIMEOUT = 120  # seconds — kill resume if it takes longer

        async def _resume_chat(entry: dict) -> None:
            cid = entry["chat_id"]
            tid = entry["thread_id"]
            uid = entry["user_id"]
            tg_thread_id = tid or None
            try:
                session_id = get_session_id(cid, tid, uid)
                if not session_id:
                    infra_logger.warning(
                        "No session for chat=%d thread=%d user=%d, skipping resume",
                        cid, tid, uid,
                    )
                    # Still notify the user
                    try:
                        await bot.send_message(
                            chat_id=cid,
                            text="\u26a0\ufe0f Bot restarted — no session to resume. Send a new message to continue.",
                            message_thread_id=tg_thread_id,
                        )
                    except Exception:
                        pass
                    return
                resume_msg = (
                    "[System: The bot just restarted. Your previous response was "
                    "interrupted. Briefly summarize what you were doing and ask "
                    "the user if they want you to continue.]"
                )
                chat_working_dir = get_working_dir(cid)
                result_text = None
                stop_event = asyncio.Event()
                async for event in stream_claude(resume_msg, cid, tid, uid,
                                                 working_dir=chat_working_dir,
                                                 stop_event=stop_event):
                    if event.get("type") == "result":
                        result_text = event.get("text", "")
                    elif event.get("type") == "error":
                        result_text = event.get("text", "")
                if result_text:
                    md_chunks = split_message(result_text)
                    for md_chunk in md_chunks:
                        rendered = renderer.render(md_chunk)
                        try:
                            await bot.send_message(
                                chat_id=cid,
                                text=rendered,
                                parse_mode="HTML",
                                disable_web_page_preview=True,
                                message_thread_id=tg_thread_id,
                            )
                        except Exception:
                            plain = re.sub(r"<[^>]+>", "", rendered)
                            for pc in split_message(plain):
                                await bot.send_message(
                                    chat_id=cid,
                                    text=pc,
                                    message_thread_id=tg_thread_id,
                                )
                infra_logger.info("Resumed chat=%d thread=%d user=%d", cid, tid, uid)
            except Exception as e:
                infra_logger.error(
                    "Failed to resume chat=%d thread=%d user=%d: %s", cid, tid, uid, e
                )
                try:
                    await bot.send_message(
                        chat_id=cid,
                        text="\u26a0\ufe0f Bot restarted — couldn't resume your previous task. Send a new message to continue.",
                        message_thread_id=tg_thread_id,
                    )
                except Exception:
                    pass

        async def _resume_with_timeout(entry: dict) -> None:
            try:
                await asyncio.wait_for(_resume_chat(entry), timeout=RESUME_TIMEOUT)
            except asyncio.TimeoutError:
                cid = entry["chat_id"]
                tid = entry["thread_id"]
                uid = entry["user_id"]
                infra_logger.error(
                    "Resume timed out after %ds for chat=%d thread=%d user=%d",
                    RESUME_TIMEOUT, cid, tid, uid,
                )
                try:
                    await bot.send_message(
                        chat_id=cid,
                        text="\u26a0\ufe0f Bot restarted — resume timed out. Send a new message to continue.",
                        message_thread_id=tid or None,
                    )
                except Exception:
                    pass

        # Run resumes in background so the bot can accept new messages immediately
        async def _run_resumes() -> None:
            await asyncio.gather(*[_resume_with_timeout(e) for e in interrupted.values()])
            infra_logger.info("Restart recovery complete")

        asyncio.create_task(_run_resumes())

    async def post_shutdown(application: Application) -> None:
        """Clean up SDK sessions and active subprocesses on shutdown."""
        # Kill all active subprocesses
        for skey, proc in list(_active_procs.items()):
            if proc.returncode is None:
                try:
                    proc.kill()
                    infra_logger.info("Killed active subprocess for %s", skey)
                except ProcessLookupError:
                    pass
        _active_procs.clear()

        if HAS_SDK:
            await shutdown_sdk_sessions()
            infra_logger.info("SDK sessions shut down")

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Register handlers
    app.add_handler(CommandHandler("start", handlers.cmd_start))
    app.add_handler(CommandHandler("new", handlers.cmd_new))
    app.add_handler(CommandHandler("status", handlers.cmd_status))
    app.add_handler(CommandHandler("stop", handlers.cmd_stop))
    register_all(app)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handlers.handle_voice))
    app.add_handler(MessageHandler(filters.VIDEO, handlers.handle_video))
    app.add_handler(MessageHandler(filters.Document.ALL, handlers.handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handlers.handle_photo))

    # Start polling
    logger.info("Bot is running. Press Ctrl+C to stop.")
    infra_logger.info("Bot running")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
