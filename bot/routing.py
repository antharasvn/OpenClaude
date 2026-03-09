"""Group chat routing logic — should_respond, strip_bot_mention, reply prefix."""

import re

from telegram import Update

from bot.config import get_thread_id

# Populated at startup via post_init callback
BOT_USERNAME: str = ""


def should_respond(update: Update) -> bool:
    """Decide whether the bot should respond to this message."""
    chat = update.effective_chat
    if chat.type == "private":
        return True

    msg = update.message
    if not msg:
        return False

    thread_id = get_thread_id(update)
    from commands.config import get_respond_mode
    mode = get_respond_mode(chat.id, thread_id)

    if mode == "all":
        return True

    if msg.entities:
        for entity in msg.entities:
            if entity.type == "mention":
                mention = msg.text[entity.offset:entity.offset + entity.length]
                if mention.lower() == f"@{BOT_USERNAME.lower()}":
                    return True

    return bool(
        msg.reply_to_message
        and msg.reply_to_message.from_user
        and msg.reply_to_message.from_user.username
        and msg.reply_to_message.from_user.username.lower() == BOT_USERNAME.lower()
    )


def strip_bot_mention(text: str) -> str:
    """Remove @bot_username from message text."""
    if BOT_USERNAME:
        text = re.sub(rf"@{re.escape(BOT_USERNAME)}\b", "", text, flags=re.IGNORECASE).strip()
    return text


def get_reply_prefix(update: Update) -> str:
    """If the user is replying to a message, return a prefix with the quoted text."""
    reply = update.message.reply_to_message if update.message else None
    if not reply:
        return ""

    # Determine who sent the replied-to message
    from_user = reply.from_user
    if from_user:
        if (
            BOT_USERNAME
            and from_user.username
            and from_user.username.lower() == BOT_USERNAME.lower()
        ):
            sender = "you (the assistant)"
        else:
            sender = from_user.first_name or from_user.username or str(from_user.id)
    else:
        sender = "unknown"

    quoted = reply.text or reply.caption or ""
    if not quoted:
        return f'[User is replying to a message from {sender} (no text content)]\n'

    if len(quoted) > 500:
        quoted = quoted[:500] + "\u2026"

    # Sanitize to reduce prompt injection risk from quoted text
    quoted = quoted.replace("[", "(").replace("]", ")")
    return f'[User is replying to this message from {sender}:\n"{quoted}"]\n'
