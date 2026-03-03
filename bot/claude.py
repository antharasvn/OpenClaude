"""Claude integration (stream_claude, SDK/subprocess)."""

import asyncio
import json
import os
import shutil
import time
from pathlib import Path

from bot.config import (
    ADMIN_USER_ID, ALL_TOOLS, CLAUDE_MODEL, CLAUDE_TIMEOUT, WORKING_DIR,
    WORKSPACES_DIR,
)
from bot.logging_setup import logger, get_workspace_logger, _summarize_input
from bot.sessions import session_key, get_session_id, set_session_id
from bot.streams import add_active_stream, remove_active_stream, set_stream_session_id
from bot.permissions import build_env, build_sdk_options
from bot.sdk_session import (
    HAS_SDK, SDKSession, sdk_sessions,
    AssistantMessage, ResultMessage, StreamEvent,
    TextBlock, ToolUseBlock, ToolResultBlock,
)

# Re-export from new modules for backward compatibility
from bot.process import _active_procs, kill_active_proc  # noqa: F401
from bot.formatting import format_tool_status, finished_line  # noqa: F401
from bot.prompts import (  # noqa: F401
    _restart_context_path, _append_restart_context,
    _clear_restart_context, _read_restart_context,
    _build_preamble,
)


async def stream_claude(message: str, chat_id: int, thread_id: int, user_id: int,
                        working_dir: str | None = None, verbose: bool = False,
                        stop_event: asyncio.Event | None = None,
                        real_user_id: int | None = None):
    """Stream Claude output and yield events as they arrive.

    Yields dicts with keys:
      - {"type": "tool_use", "status": "..."}
      - {"type": "tool_result"}
      - {"type": "partial", "text": "..."} (only when verbose=True)
      - {"type": "result", "text": "...", "session_id": "..."}
      - {"type": "error", "text": "..."}
      - {"type": "stopped"}  (generation cancelled via /stop)
    """
    if HAS_SDK:
        async for event in _stream_claude_sdk(message, chat_id, thread_id, user_id,
                                               working_dir=working_dir, verbose=verbose,
                                               stop_event=stop_event,
                                               real_user_id=real_user_id):
            yield event
    else:
        async for event in _stream_claude_subprocess(message, chat_id, thread_id, user_id,
                                                      working_dir=working_dir, verbose=verbose,
                                                      stop_event=stop_event,
                                                      real_user_id=real_user_id):
            yield event


async def _stream_claude_sdk(message: str, chat_id: int, thread_id: int, user_id: int,
                              working_dir: str | None = None, verbose: bool = False,
                              stop_event: asyncio.Event | None = None,
                              real_user_id: int | None = None):
    """SDK-based streaming."""
    cwd = working_dir or WORKING_DIR
    sid = get_session_id(chat_id, thread_id, user_id)
    ws_log = get_workspace_logger(chat_id)
    ws_log.info("Claude SDK invocation \u2014 user=%d, session=%s", user_id, sid or "new")

    add_active_stream(chat_id, thread_id, user_id, user_message=message[:300])

    # Restart context breadcrumbs
    _clear_restart_context(chat_id)
    _append_restart_context(chat_id, f"User message: {message[:200]}")

    try:
        is_admin = ADMIN_USER_ID and (real_user_id or user_id) == ADMIN_USER_ID
        skey = session_key(chat_id, thread_id, user_id)

        preamble = _build_preamble(is_admin, sid)
        if preamble:
            message = preamble + message

        sdk_session = sdk_sessions.get(skey)
        if sdk_session is None:
            sdk_session = SDKSession()
            sdk_session.session_id = sid
            sdk_sessions[skey] = sdk_session

        options = build_sdk_options(is_admin, cwd, thread_id, sid, verbose)

        try:
            await sdk_session.ensure_connected(options)
        except Exception as e:
            logger.error("SDK connect failed: %s", e)
            await sdk_session.disconnect()
            sdk_session = SDKSession()
            sdk_session.session_id = sid
            sdk_sessions[skey] = sdk_session
            try:
                await sdk_session.ensure_connected(options)
            except Exception as e2:
                logger.exception("SDK connect retry failed: %s", e2)
                yield {"type": "error", "text": f"Failed to connect to Claude: {e2}"}
                return

        logger.info(
            "Calling Claude (SDK) for user %d (session: %s)",
            user_id, sid or "new",
        )

        result_text = None
        new_session_id = None
        early_session_id = None  # captured from StreamEvent before ResultMessage
        tool_active_count = 0  # incremented per tool start, decremented per result

        try:
            await sdk_session.client.query(message)
            sdk_session.last_activity = time.time()
            sdk_deadline = asyncio.get_event_loop().time() + CLAUDE_TIMEOUT

            async for msg in sdk_session.client.receive_response():
                now = asyncio.get_event_loop().time()
                if stop_event and stop_event.is_set():
                    logger.info("Stop event set — aborting SDK stream for user %d", user_id)
                    await sdk_session.disconnect()
                    sdk_sessions.pop(skey, None)
                    yield {"type": "stopped"}
                    return
                # Skip deadline check while a tool is running (e.g. long Bash)
                if tool_active_count == 0 and now > sdk_deadline:
                    logger.error("SDK stream timed out after %ds for user %d", CLAUDE_TIMEOUT, user_id)
                    await sdk_session.disconnect()
                    sdk_sessions.pop(skey, None)
                    yield {"type": "error", "text": "Claude took too long to respond. Try again or /new to start fresh."}
                    return
                # Keep session alive and reset deadline after checks pass
                sdk_session.last_activity = time.time()
                sdk_deadline = now + CLAUDE_TIMEOUT
                if msg is None:
                    continue
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, ToolUseBlock):
                            tool_active_count += 1
                            ws_log.info("Tool: %s \u2014 %s", block.name, _summarize_input(block.input))
                            status = format_tool_status(block.name, block.input)
                            _append_restart_context(chat_id, f"Tool: {status}")
                            yield {"type": "tool_use", "status": status}
                        elif isinstance(block, ToolResultBlock):
                            tool_active_count -= 1
                            _append_restart_context(chat_id, "Tool completed")
                            yield {"type": "tool_result"}
                        elif isinstance(block, TextBlock):
                            if block.text:
                                _append_restart_context(chat_id, f"Output started: {block.text[:100]}")
                                yield {"type": "text_block", "text": block.text}

                elif isinstance(msg, StreamEvent):
                    # Save session_id early — don't wait for ResultMessage
                    if not early_session_id and msg.session_id:
                        early_session_id = msg.session_id
                        set_session_id(chat_id, thread_id, user_id, early_session_id)
                        set_stream_session_id(chat_id, thread_id, user_id, early_session_id)
                        sdk_session.session_id = early_session_id
                        logger.info("Session ID captured early for user %d: %s", user_id, early_session_id)
                    if verbose:
                        delta = msg.event.get("delta", {})
                        if delta.get("type") == "text_delta":
                            chunk = delta.get("text", "")
                            if chunk:
                                yield {"type": "partial", "text": chunk}

                elif isinstance(msg, ResultMessage):
                    _clear_restart_context(chat_id)
                    new_session_id = msg.session_id
                    result_text = msg.result or ""
                    if new_session_id:
                        set_session_id(chat_id, thread_id, user_id, new_session_id)
                        set_stream_session_id(chat_id, thread_id, user_id, new_session_id)
                        sdk_session.session_id = new_session_id
                        logger.info("Session updated for user %d: %s", user_id, new_session_id)
                    ws_log.info("Result \u2014 session=%s, len=%d", new_session_id, len(result_text))
                    yield {"type": "result", "text": result_text, "session_id": new_session_id,
                           "usage": getattr(msg, "usage", None),
                           "cost": getattr(msg, "total_cost_usd", None),
                           "num_turns": getattr(msg, "num_turns", None),
                           "duration_ms": getattr(msg, "duration_ms", None),
                           "duration_api_ms": getattr(msg, "duration_api_ms", None)}

        except Exception as e:
            # Stop event triggered — /stop hard-killed the process
            if stop_event and stop_event.is_set():
                logger.info("SDK stream interrupted by /stop for user %d", user_id)
                yield {"type": "stopped"}
                return
            err_str = str(e)
            # SIGTERM/SIGKILL during restart — not a real error
            if any(s in err_str for s in ("exit code -15", "exit code: -15",
                                           "exit code -9", "exit code: -9")):
                logger.info("SDK process killed by signal (likely bot restart)")
                await sdk_session.disconnect()
                sdk_sessions.pop(skey, None)
                yield {"type": "silent"}
                return
            logger.exception("SDK streaming error")
            await sdk_session.disconnect()
            sdk_sessions.pop(skey, None)
            if result_text is None:
                yield {"type": "error", "text": f"Claude error: {e}"}
            return

        if result_text is None:
            logger.warning("No result message received from SDK")
            yield {"type": "error", "text": "Claude returned no result."}

    except Exception as e:
        logger.exception("Unexpected error in SDK stream_claude")
        yield {"type": "error", "text": f"Unexpected error: {e}"}
    finally:
        remove_active_stream(chat_id, thread_id, user_id)


async def _stream_claude_subprocess(message: str, chat_id: int, thread_id: int, user_id: int,
                                     working_dir: str | None = None, verbose: bool = False,
                                     stop_event: asyncio.Event | None = None,
                                     real_user_id: int | None = None):
    """Legacy subprocess-based streaming."""
    cwd = working_dir or WORKING_DIR
    sid = get_session_id(chat_id, thread_id, user_id)
    ws_log = get_workspace_logger(chat_id)
    ws_log.info("Claude invocation (subprocess) \u2014 user=%d, session=%s", user_id, sid or "new")

    add_active_stream(chat_id, thread_id, user_id, user_message=message[:300])

    # Restart context breadcrumbs
    _clear_restart_context(chat_id)
    _append_restart_context(chat_id, f"User message: {message[:200]}")

    try:
        is_admin = ADMIN_USER_ID and (real_user_id or user_id) == ADMIN_USER_ID

        preamble = _build_preamble(is_admin, sid)
        if preamble:
            message = preamble + message

        claude_bin = shutil.which("claude") or "/root/.local/bin/claude"
        logger.info("Using claude binary: %s (exists: %s)", claude_bin, os.path.isfile(claude_bin))
        cmd = [
            claude_bin,
            "-p", message,
            "--output-format", "stream-json",
            "--verbose",
            "--dangerously-skip-permissions",
            "--allowedTools", ALL_TOOLS,
        ]

        if verbose:
            cmd.append("--include-partial-messages")

        if sid:
            cmd.extend(["--resume", sid])

        if CLAUDE_MODEL:
            cmd.extend(["--model", CLAUDE_MODEL])

        logger.info(
            "Calling Claude (subprocess) for user %d (session: %s)",
            user_id, sid or "new",
        )

        env = build_env(is_admin, cwd, thread_id)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            cwd=cwd,
            env=env,
            limit=10 * 1024 * 1024,
        )

        skey = session_key(chat_id, thread_id, user_id)
        _active_procs[skey] = proc

        result_text = None
        new_session_id = None
        deadline = asyncio.get_event_loop().time() + CLAUDE_TIMEOUT

        try:
            while True:
                if stop_event and stop_event.is_set():
                    logger.info("Stop event set — killing subprocess for user %d", user_id)
                    proc.kill()
                    await proc.communicate()
                    yield {"type": "stopped"}
                    return

                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    proc.kill()
                    await proc.communicate()
                    logger.error("Claude CLI timed out after %ds for user %d", CLAUDE_TIMEOUT, user_id)
                    yield {"type": "error", "text": "Claude took too long to respond. Try again or /new to start fresh."}
                    return

                try:
                    line = await asyncio.wait_for(proc.stdout.readline(), timeout=min(remaining, 1.0))
                except asyncio.TimeoutError:
                    if stop_event and stop_event.is_set():
                        logger.info("Stop event set during readline — killing subprocess for user %d", user_id)
                        proc.kill()
                        await proc.communicate()
                        yield {"type": "stopped"}
                        return
                    if remaining <= 1.0:
                        proc.kill()
                        await proc.communicate()
                        logger.error("Claude CLI timed out after %ds for user %d", CLAUDE_TIMEOUT, user_id)
                        yield {"type": "error", "text": "Claude took too long to respond. Try again or /new to start fresh."}
                        return
                    continue

                if not line:
                    break

                decoded = line.decode().strip()
                if not decoded:
                    continue

                try:
                    event = json.loads(decoded)
                except json.JSONDecodeError:
                    logger.debug("Non-JSON line from Claude: %s", decoded[:200])
                    continue

                event_type = event.get("type")

                if event_type == "assistant":
                    msg_data = event.get("message", {})
                    content = msg_data.get("content", [])
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_name = block.get("name", "")
                            tool_input = block.get("input", {})
                            ws_log.info("Tool: %s \u2014 %s", tool_name, _summarize_input(tool_input))
                            status = format_tool_status(tool_name, tool_input)
                            _append_restart_context(chat_id, f"Tool: {status}")
                            yield {"type": "tool_use", "status": status}
                elif event_type == "tool_result":
                    _append_restart_context(chat_id, "Tool completed")
                    yield {"type": "tool_result"}

                elif event_type == "stream_event" and verbose:
                    delta = event.get("event", {}).get("delta", {})
                    if delta.get("type") == "text_delta":
                        chunk = delta.get("text", "")
                        if chunk:
                            yield {"type": "partial", "text": chunk}

                elif event_type == "result":
                    _clear_restart_context(chat_id)
                    result_text = event.get("result", "")
                    new_session_id = event.get("session_id")
                    if new_session_id:
                        set_session_id(chat_id, thread_id, user_id, new_session_id)
                        set_stream_session_id(chat_id, thread_id, user_id, new_session_id)
                        logger.info("Session updated for user %d: %s", user_id, new_session_id)
                    ws_log.info("Result \u2014 session=%s, len=%d", new_session_id, len(result_text or ""))
                    yield {"type": "result", "text": result_text, "session_id": new_session_id,
                           "usage": event.get("usage"),
                           "cost": event.get("total_cost_usd"),
                           "num_turns": event.get("num_turns"),
                           "duration_ms": event.get("duration_ms"),
                           "duration_api_ms": event.get("duration_api_ms")}

            # Capture returncode from natural exit (before finally may kill it)
            await proc.wait()
            natural_rc = proc.returncode
        finally:
            _active_procs.pop(skey, None)
            # Ensure process is terminated if still running
            if proc.returncode is None:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                await proc.wait()

        if natural_rc != 0:
            if natural_rc < 0:
                sig = -natural_rc
                logger.info("Claude CLI killed by signal %d (likely bot restart)", sig)
                if result_text is None:
                    yield {"type": "silent"}
                return
            logger.error("Claude CLI error (rc=%d)", natural_rc)
            ws_log.error("CLI error rc=%d", natural_rc)
            if result_text is None:
                yield {"type": "error", "text": f"Claude CLI error (exit code {natural_rc})"}
            return

        if result_text is None:
            logger.warning("No result event received from stream")
            yield {"type": "error", "text": "Claude returned no result."}

    except FileNotFoundError as e:
        logger.exception("FileNotFoundError in stream_claude: %s", e)
        yield {
            "type": "error",
            "text": "Error: Claude CLI not found. "
                    "Make sure 'claude' is installed and available in PATH.",
        }
    except Exception as e:
        logger.exception("Unexpected error streaming Claude")
        yield {"type": "error", "text": f"Unexpected error: {e}"}
    finally:
        remove_active_stream(chat_id, thread_id, user_id)
