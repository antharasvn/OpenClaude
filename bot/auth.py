"""Authorization helpers and handler decorators."""

from functools import wraps

from .config import get_settings


def is_authorized(user_id: int) -> bool:
    """Check if a user is authorized to use the bot."""
    settings = get_settings()
    return user_id in settings.allowed_users_set


def is_admin(user_id: int) -> bool:
    """Check if a user is the admin (first in ALLOWED_USERS)."""
    settings = get_settings()
    if not settings.allowed_users_list:
        return False
    return user_id == settings.allowed_users_list[0]


# ---------------------------------------------------------------------------
# Handler decorators — reduce auth boilerplate in command/media handlers
# ---------------------------------------------------------------------------

def authorized(func):
    """Decorator: require authorized user and should_respond check."""
    @wraps(func)
    async def wrapper(update, context, **kwargs):
        if not is_authorized(update.effective_user.id):
            return
        from bot.routing import should_respond
        if not should_respond(update):
            return
        return await func(update, context, **kwargs)
    return wrapper


def authorized_only(func):
    """Decorator: require authorized user (no should_respond check).

    Use for commands that should work regardless of respond mode.
    """
    @wraps(func)
    async def wrapper(update, context, **kwargs):
        if not is_authorized(update.effective_user.id):
            return
        return await func(update, context, **kwargs)
    return wrapper


def admin_only(func):
    """Decorator: require admin user."""
    @wraps(func)
    async def wrapper(update, context, **kwargs):
        if not is_admin(update.effective_user.id):
            await update.message.reply_text("Admin only.")
            return
        return await func(update, context, **kwargs)
    return wrapper
