"""Local HTTP inject server — allows external processes (cron, scripts) to send
messages to the bot as if they came from a user, without a Telegram Update.

POST http://localhost:5001/inject
{
    "chat_id": -1003681585723,
    "thread_id": 43,
    "user_id": 0,
    "message": "text of the message"
}

The bot processes it through the full pipeline (lock, typing, streaming) and sends
the response back to the Telegram thread.
"""

import asyncio
import logging
from typing import TYPE_CHECKING

from aiohttp import web

if TYPE_CHECKING:
    from telegram import Bot

logger = logging.getLogger(__name__)

INJECT_PORT = 5001

# Strong references to fire-and-forget inject tasks.
# Without this, the GC can collect a running task mid-execution, leaving
# acquired locks unreleased and subprocesses orphaned.
_active_inject_tasks: set[asyncio.Task] = set()


class InjectServer:
    """Runs a tiny aiohttp server alongside the Telegram bot."""

    def __init__(self, bot: "Bot") -> None:
        self._bot = bot
        self._app = web.Application()
        self._app.router.add_post("/inject", self._handle_inject)
        self._runner: web.AppRunner | None = None

    async def start(self) -> None:
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "127.0.0.1", INJECT_PORT)
        await site.start()
        logger.info("Inject server listening on http://127.0.0.1:%d", INJECT_PORT)

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()

    async def _handle_inject(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
        except Exception:
            return web.Response(status=400, text="Invalid JSON")

        chat_id = data.get("chat_id")
        thread_id = data.get("thread_id", 0)
        user_id = data.get("user_id", 0)
        message = data.get("message", "").strip()

        if not chat_id or not message:
            return web.Response(status=400, text="chat_id and message are required")

        # Fire-and-forget — keep a strong reference so the GC cannot collect
        # the task mid-execution (which would leave locks held and subprocesses
        # orphaned). The task removes itself from the set when it finishes.
        task = asyncio.create_task(
            self._run_stream(chat_id, thread_id, user_id, message)
        )
        _active_inject_tasks.add(task)
        task.add_done_callback(_active_inject_tasks.discard)
        return web.Response(text="ok")

    async def _run_stream(
        self, chat_id: int, thread_id: int, user_id: int, message: str
    ) -> None:
        """Run full bot pipeline for an injected message."""
        from bot.chat_lock import get_chat_lock, release_chat_lock_ref, set_lock_holder
        from bot.claude import stream_claude
        from bot.commands_core import _stop_events, _streaming_tasks
        from bot.sessions import session_key
        from bot.streaming_session import StreamingSession
        from bot.workspaces import get_working_dir
        from commands.config import get_streaming, get_verbose

        # In group chats the session key always uses user_id=0
        session_user_id = 0
        tg_thread_id = thread_id or None
        skey = session_key(chat_id, thread_id, session_user_id)
        chat_working_dir = get_working_dir(chat_id)
        streaming = get_streaming(chat_id, thread_id)
        show_tools = get_verbose(chat_id, thread_id)

        session = StreamingSession(
            bot=self._bot,
            chat_id=chat_id,
            thread_id=thread_id,
            tg_thread_id=tg_thread_id,
            streaming=streaming,
            show_tools=show_tools,
        )
        session.session_user_id = session_user_id

        lock = get_chat_lock(skey)
        try:
            await asyncio.wait_for(lock.acquire(), timeout=60)
        except (TimeoutError, asyncio.TimeoutError):
            logger.error("Inject: lock timeout for skey=%s", skey)
            release_chat_lock_ref(skey)
            return

        # Register in _streaming_tasks/_stop_events so /stop works and
        # concurrent inject requests for the same chat are coordinated.
        stop_event = asyncio.Event()
        try:
            set_lock_holder(skey)
            _streaming_tasks[skey] = asyncio.current_task()
            _stop_events[skey] = stop_event

            typing_task = asyncio.create_task(self._typing_loop(chat_id, tg_thread_id))

            try:
                async for event in stream_claude(
                    message,
                    chat_id,
                    thread_id,
                    session_user_id,
                    working_dir=chat_working_dir,
                    stop_event=stop_event,
                    real_user_id=user_id,
                ):
                    etype = event.get("type")
                    if etype == "partial" and not typing_task.done():
                        typing_task.cancel()
                    await session.handle_event(event)

                await session.flush_live()
            except Exception:
                logger.exception("Inject stream error for skey=%s", skey)
            finally:
                typing_task.cancel()
        finally:
            _streaming_tasks.pop(skey, None)
            _stop_events.pop(skey, None)
            lock.release()
            release_chat_lock_ref(skey)

    async def _typing_loop(self, chat_id: int, thread_id: int | None) -> None:
        try:
            while True:
                with __import__("contextlib").suppress(Exception):
                    await self._bot.send_chat_action(
                        chat_id=chat_id,
                        action="typing",
                        message_thread_id=thread_id,
                    )
                await asyncio.sleep(4)
        except asyncio.CancelledError:
            pass
