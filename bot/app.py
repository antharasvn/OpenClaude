"""Application builder, post_init, post_shutdown, main()."""

import asyncio
import atexit
import sys

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.config import (
    ALLOWED_USERS, SESSION_FILE, TELEGRAM_BOT_TOKEN, WORKING_DIR,
)
import logging

from bot.logging_setup import setup_logging, infra_logger

logger = logging.getLogger(__name__)
from bot.sessions import flush_sessions
from bot.streams import start_streams_flusher, stop_streams_flusher, flush_streams
from bot.renderer import TelegramRenderer
from bot.claude import stream_claude
from bot.process import _active_procs
from bot.restart_recovery import RestartRecoveryService
from bot.sdk_session import HAS_SDK, cleanup_idle_sessions, shutdown_sdk_sessions
from bot import handlers
from commands import register_all, ALL_COMMANDS


def main() -> None:
    """Start the bot."""
    setup_logging()

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
    # Register atexit handlers for cache flush (safety net)
    atexit.register(flush_sessions)
    atexit.register(flush_streams)

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
        handlers._set_bot_username(me.username or "")
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

        # Start streams flusher background task
        start_streams_flusher()

        # Restart recovery — edit "Restarting..." messages & resume interrupted sessions
        recovery = RestartRecoveryService(
            bot=bot,
            renderer=renderer,
            stream_fn=stream_claude,
        )
        await recovery.recover_interrupted_sessions()

    async def post_shutdown(application: Application) -> None:
        """Clean up SDK sessions, caches, and active subprocesses on shutdown."""
        # Kill all active subprocesses
        for skey, proc in list(_active_procs.items()):
            if proc.returncode is None:
                try:
                    proc.kill()
                    infra_logger.info("Killed active subprocess for %s", skey)
                except ProcessLookupError:
                    pass
        _active_procs.clear()

        # Flush caches before shutdown
        flush_sessions()
        await stop_streams_flusher()
        infra_logger.info("Caches flushed on shutdown")

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

    # Global error handler — catch unhandled exceptions in any handler
    async def error_handler(update: Update | None, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.exception("Unhandled exception in handler", exc_info=context.error)
        infra_logger.error("Unhandled exception: %s", context.error)
        if update and update.effective_message:
            try:
                thread_id = getattr(update.effective_message, 'message_thread_id', None)
                await update.effective_message.reply_text(
                    "Something went wrong. Please try again.",
                    message_thread_id=thread_id,
                )
            except Exception:
                pass  # Can't send error message — swallow silently

    app.add_error_handler(error_handler)

    # Start polling
    logger.info("Bot is running. Press Ctrl+C to stop.")
    infra_logger.info("Bot running")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
