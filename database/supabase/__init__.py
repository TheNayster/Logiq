"""
database/supabase/__init__.py
Public API for the Supabase layer.
"""
from database.supabase.client import get_client, close_client
from database.supabase.events import (
    on_server_add,
    on_server_remove,
    on_member_join,
    on_member_leave,
    on_member_ban,
    on_member_unban,
    on_account_create,
    on_account_delete,
    on_xp_gain,
    on_balance_change,
    on_mod_action,
    on_warning_add,
    on_warning_remove,
    on_custom_command_use,
    on_ticket_open,
    on_ticket_close,
    on_giveaway_enter,
    on_giveaway_end,
    on_reaction_role_add,
    on_reaction_role_remove,
    on_reminder_fire,
    on_analytics_event,
    on_audit_log,
)

__all__ = [
    "get_client", "close_client",
    "on_server_add", "on_server_remove",
    "on_member_join", "on_member_leave",
    "on_member_ban", "on_member_unban",
    "on_account_create", "on_account_delete",
    "on_xp_gain", "on_balance_change",
    "on_mod_action", "on_warning_add", "on_warning_remove",
    "on_custom_command_use",
    "on_ticket_open", "on_ticket_close",
    "on_giveaway_enter", "on_giveaway_end",
    "on_reaction_role_add", "on_reaction_role_remove",
    "on_reminder_fire",
    "on_analytics_event", "on_audit_log",
]
