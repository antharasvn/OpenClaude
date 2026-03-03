"""Authorization helpers."""

from .config import get_settings


def is_authorized(user_id: int) -> bool:
    """Check if a user is authorized to use the bot."""
    settings = get_settings()
    return user_id in settings.allowed_users


def is_admin(user_id: int) -> bool:
    """Check if a user is the admin (first in ALLOWED_USERS)."""
    settings = get_settings()
    if not settings.allowed_users_list:
        return False
    return user_id == settings.allowed_users_list[0]
