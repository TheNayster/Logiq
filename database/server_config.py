"""
database/server_config.py
=========================
Server configuration helpers — thin wrappers around the `servers` table
that is already used by the rest of the bot (see cogs/admin.py).

All functions take a Supabase AsyncClient (from database.supabase.client).
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Fields we allow the dashboard to read / write.
# Anything not in this set is silently ignored on save.
_ALLOWED_FIELDS = {
    # General
    "prefix",
    "language",
    "nickname",
    # Channels
    "log_channel_id",
    "mod_log_channel_id",
    "welcome_channel_id",
    "bot_output_channel_id",
    "ignored_channels",
    # Modules (booleans)
    "slash_commands_enabled",
    "dm_notifications_enabled",
    "audit_logging_enabled",
    "moderation_enabled",
    "leveling_enabled",
    "economy_enabled",
    "tickets_enabled",
    "giveaways_enabled",
    "welcome_enabled",
    "automod_enabled",
    "reaction_roles_enabled",
    # Welcome
    "welcome_message",
    # Automod
    "automod_anti_spam",
    "automod_anti_links",
    "automod_bad_words",
    "automod_bad_words_list",
    # Moderation
    "mute_role_id",
    "mod_role_id",
}


async def get_server_config(sb, server_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch the server row from Supabase.
    Returns None if the server has not been set up yet.
    """
    try:
        res = await (
            sb.table("servers")
            .select("*")
            .eq("id", server_id)
            .maybe_single()
            .execute()
        )
        return res.data if res else None
    except Exception as e:
        logger.error(f"[server_config] get error server={server_id}: {e}", exc_info=True)
        return None


async def save_server_config(sb, server_id: str, data: Dict[str, Any]) -> bool:
    """
    Upsert server config.  Only fields in _ALLOWED_FIELDS are persisted.
    Returns True on success, False on failure.
    """
    # Filter to safe fields only
    safe = {k: v for k, v in data.items() if k in _ALLOWED_FIELDS}
    if not safe:
        logger.warning(f"[server_config] save called with no valid fields for server={server_id}")
        return False

    try:
        safe["id"] = server_id
        await (
            sb.table("servers")
            .upsert(safe, on_conflict="id")
            .execute()
        )
        logger.info(f"[server_config] Saved {list(safe.keys())} for server={server_id}")
        return True
    except Exception as e:
        logger.error(f"[server_config] save error server={server_id}: {e}", exc_info=True)
        return False
