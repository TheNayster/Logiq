"""
database/supabase/events.py
===========================
All parameterised upserts / inserts / deletes triggered by Stoat lifecycle
events.  Every SQL-touching call goes through the Supabase client using its
PostgREST builder — no raw SQL strings, no injection surface.

Events covered (MEE6 parity + Stoat extras):
  on_server_add          – bot added to a new server
  on_server_remove       – bot removed / kicked from a server
  on_member_join         – user joins a server
  on_member_leave        – user leaves / is kicked from a server
  on_member_ban          – user is banned
  on_member_unban        – user is unbanned
  on_account_create      – global user profile bootstrapped on first interaction
  on_account_delete      – user requests data deletion (GDPR)
  on_xp_gain             – message XP increment + level-up check
  on_balance_change      – economy transaction ledger entry
  on_mod_action          – warn / kick / ban / mute / timeout / note
  on_warning_add         – dedicated warning counter
  on_warning_remove      – pardon a warning
  on_custom_command_use  – increment use_count
  on_ticket_open         – create ticket row
  on_ticket_close        – close ticket row + store transcript
  on_giveaway_enter      – add entry
  on_giveaway_end        – mark ended + write winners
  on_reaction_role       – add/remove role assignment
  on_reminder_fire       – mark reminder completed
  on_analytics_event     – generic event sink for dashboard
  on_audit_log           – internal audit trail entry
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database.supabase.client import get_client

logger = logging.getLogger(__name__)


# ── helpers ────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _upsert(table: str, data: Dict[str, Any], on_conflict: str = "id") -> Optional[Dict]:
    """
    Thin wrapper: upsert a single row.
    Uses PostgREST builder — all values are parameterised by the library.
    """
    try:
        sb = await get_client()
        res = await sb.table(table).upsert(data, on_conflict=on_conflict).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"[supabase] upsert {table} failed: {e}", exc_info=True)
        return None


async def _insert(table: str, data: Dict[str, Any]) -> Optional[Dict]:
    try:
        sb = await get_client()
        res = await sb.table(table).insert(data).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"[supabase] insert {table} failed: {e}", exc_info=True)
        return None


async def _update(table: str, match: Dict[str, Any], data: Dict[str, Any]) -> bool:
    try:
        sb = await get_client()
        q = sb.table(table).update(data)
        for col, val in match.items():
            q = q.eq(col, val)
        await q.execute()
        return True
    except Exception as e:
        logger.error(f"[supabase] update {table} failed: {e}", exc_info=True)
        return False


# =============================================================================
# SERVER LIFECYCLE
# =============================================================================

async def on_server_add(server_id: str, name: str, owner_id: str) -> None:
    """Bot added to a new Stoat server — create servers row."""
    await _upsert("servers", {
        "id": server_id,
        "name": name,
        "owner_id": owner_id,
        "bot_joined_at": _now(),
    }, on_conflict="id")
    await on_audit_log(server_id=server_id, actor_id="system",
                       action="server_add", target_type="server", target_id=server_id)
    logger.info(f"[event] server_add: {server_id} ({name})")


async def on_server_remove(server_id: str) -> None:
    """Bot removed from a server — we keep the data but log the departure."""
    await on_audit_log(server_id=server_id, actor_id="system",
                       action="server_remove", target_type="server", target_id=server_id)
    # Optionally soft-delete; for now just log.
    logger.info(f"[event] server_remove: {server_id}")


# =============================================================================
# MEMBER LIFECYCLE
# =============================================================================

async def on_member_join(server_id: str, user_id: str,
                          display_name: str = "", avatar_url: str = "") -> None:
    """
    User joins a Stoat server.
    - Upserts server_members (handles rejoin: increments rejoin_count, clears left_at).
    - Bootstraps global users row.
    - Logs analytics event.
    """
    sb = await get_client()

    # Check for existing row (rejoin scenario)
    try:
        existing = await (
            sb.table("server_members")
              .select("id, rejoin_count")
              .eq("server_id", server_id)
              .eq("user_id", user_id)
              .maybe_single()
              .execute()
        )
    except Exception:
        existing = None

    if existing and existing.data:
        await _update("server_members",
                      {"server_id": server_id, "user_id": user_id},
                      {
                          "left_at": None,
                          "joined_at": _now(),
                          "is_banned": False,
                          "rejoin_count": (existing.data.get("rejoin_count") or 0) + 1,
                          "display_name": display_name or existing.data.get("display_name"),
                          "avatar_url": avatar_url or existing.data.get("avatar_url"),
                          "updated_at": _now(),
                      })
    else:
        await _insert("server_members", {
            "server_id": server_id,
            "user_id": user_id,
            "display_name": display_name,
            "avatar_url": avatar_url,
            "joined_at": _now(),
        })

    # Global user bootstrap
    await on_account_create(user_id, display_name, avatar_url)

    await on_analytics_event(server_id, user_id, "member_join")
    logger.info(f"[event] member_join: {user_id} -> {server_id}")


async def on_member_leave(server_id: str, user_id: str) -> None:
    """
    User leaves a Stoat server (voluntary or kicked).
    Sets left_at; data is preserved for history.
    """
    await _update("server_members",
                  {"server_id": server_id, "user_id": user_id},
                  {"left_at": _now(), "updated_at": _now()})
    await on_analytics_event(server_id, user_id, "member_leave")
    logger.info(f"[event] member_leave: {user_id} <- {server_id}")


async def on_member_ban(server_id: str, user_id: str,
                         moderator_id: str, reason: str = "No reason provided") -> None:
    """User banned — update member row + write mod_action."""
    await _update("server_members",
                  {"server_id": server_id, "user_id": user_id},
                  {"is_banned": True, "left_at": _now(), "updated_at": _now()})
    await on_mod_action(server_id, user_id, moderator_id, "ban", reason)
    await on_analytics_event(server_id, user_id, "member_ban", {"reason": reason})
    logger.info(f"[event] member_ban: {user_id} from {server_id}")


async def on_member_unban(server_id: str, user_id: str,
                           moderator_id: str, reason: str = "") -> None:
    """User unbanned."""
    await _update("server_members",
                  {"server_id": server_id, "user_id": user_id},
                  {"is_banned": False, "updated_at": _now()})
    await on_mod_action(server_id, user_id, moderator_id, "unban", reason or "Unbanned")
    logger.info(f"[event] member_unban: {user_id} in {server_id}")


# =============================================================================
# ACCOUNT LIFECYCLE
# =============================================================================

async def on_account_create(user_id: str, username: str = "",
                              avatar_url: str = "") -> None:
    """
    Bootstrap global users row on first interaction.
    Safe to call on every join — upsert is idempotent.
    """
    await _upsert("users", {
        "id": user_id,
        "username": username,
        "display_name": username,
        "avatar_url": avatar_url,
        "last_seen_at": _now(),
    }, on_conflict="id")


async def on_account_delete(user_id: str) -> None:
    """
    GDPR erasure request — delete all personal data rows for this user.
    server_members rows are cascade-handled by the DB for server-scoped data.
    Global users row is removed.
    """
    try:
        sb = await get_client()
        # Delete global profile
        await sb.table("users").delete().eq("id", user_id).execute()
        # Delete server_members rows (not cascade-deleted since no FK to users)
        await sb.table("server_members").delete().eq("user_id", user_id).execute()
        # Anonymise mod_actions (keep record, remove identity)
        await sb.table("mod_actions").update({"target_id": "[deleted]"}).eq("target_id", user_id).execute()
        await sb.table("warnings").update({"user_id": "[deleted]"}).eq("user_id", user_id).execute()
        logger.info(f"[event] account_delete: {user_id} — data erased")
    except Exception as e:
        logger.error(f"[event] account_delete failed for {user_id}: {e}", exc_info=True)


# =============================================================================
# LEVELING / XP  (MEE6 leveling plugin)
# =============================================================================

async def on_xp_gain(server_id: str, user_id: str, xp_amount: int,
                      level_up: bool = False, new_level: int = 0) -> None:
    """
    Increment XP and total_messages for a member.
    If level_up=True, also update level and log analytics.
    Uses a conditional update rather than RPC to avoid raw SQL.
    """
    update_data: Dict[str, Any] = {
        "xp": None,          # handled via increment below
        "total_messages": None,
        "last_xp_at": _now(),
        "updated_at": _now(),
    }

    # PostgREST doesn't support column += natively; use rpc increment helper
    try:
        sb = await get_client()
        await sb.rpc("increment_xp", {
            "p_server_id": server_id,
            "p_user_id": user_id,
            "p_xp": xp_amount,
        }).execute()

        if level_up and new_level:
            await _update("server_members",
                          {"server_id": server_id, "user_id": user_id},
                          {"level": new_level, "updated_at": _now()})
            await on_analytics_event(server_id, user_id, "level_up",
                                     {"level": new_level, "xp": xp_amount})
    except Exception as e:
        logger.error(f"[event] xp_gain failed: {e}", exc_info=True)


# =============================================================================
# ECONOMY
# =============================================================================

async def on_balance_change(server_id: str, user_id: str, amount: int,
                              balance_after: int, tx_type: str,
                              description: str = "", ref_id: str = "") -> None:
    """Write an economy transaction ledger entry and update member balance."""
    await _insert("economy_transactions", {
        "server_id": server_id,
        "user_id": user_id,
        "amount": amount,
        "balance_after": balance_after,
        "type": tx_type,
        "description": description,
        "ref_id": ref_id or None,
        "created_at": _now(),
    })
    await _update("server_members",
                  {"server_id": server_id, "user_id": user_id},
                  {"balance": balance_after, "updated_at": _now()})


# =============================================================================
# MODERATION  (MEE6 moderation plugin)
# =============================================================================

async def on_mod_action(server_id: str, target_id: str, moderator_id: str,
                         action_type: str, reason: str = "No reason provided",
                         duration_secs: Optional[int] = None) -> Optional[Dict]:
    """
    Log a moderation action (warn/kick/ban/unban/mute/unmute/timeout/note).
    case_number is auto-assigned by the DB trigger.
    """
    data: Dict[str, Any] = {
        "server_id": server_id,
        "target_id": target_id,
        "moderator_id": moderator_id,
        "action_type": action_type,
        "reason": reason,
        "created_at": _now(),
    }
    if duration_secs:
        data["duration_secs"] = duration_secs
    return await _insert("mod_actions", data)


async def on_warning_add(server_id: str, user_id: str,
                          moderator_id: str, reason: str) -> Optional[Dict]:
    """Add a warning record (MEE6 !warn)."""
    row = await _insert("warnings", {
        "server_id": server_id,
        "user_id": user_id,
        "moderator_id": moderator_id,
        "reason": reason,
        "created_at": _now(),
    })
    await on_mod_action(server_id, user_id, moderator_id, "warn", reason)
    return row


async def on_warning_remove(warning_id: str, moderator_id: str) -> bool:
    """Pardon / remove a specific warning by UUID."""
    return await _update("warnings", {"id": warning_id}, {"active": False})


# =============================================================================
# CUSTOM COMMANDS
# =============================================================================

async def on_custom_command_use(server_id: str, trigger: str) -> None:
    """Increment use_count for a custom command (fire-and-forget)."""
    try:
        sb = await get_client()
        await sb.rpc("increment_command_use", {
            "p_server_id": server_id,
            "p_trigger": trigger,
        }).execute()
    except Exception as e:
        logger.warning(f"[event] custom_command_use rpc failed: {e}")


# =============================================================================
# TICKETS
# =============================================================================

async def on_ticket_open(server_id: str, creator_id: str,
                          category: str = "General Support",
                          subject: str = "",
                          channel_id: str = "") -> Optional[Dict]:
    """Create a new support ticket."""
    return await _insert("tickets", {
        "server_id": server_id,
        "creator_id": creator_id,
        "channel_id": channel_id or None,
        "category": category,
        "subject": subject or None,
        "status": "open",
        "created_at": _now(),
    })


async def on_ticket_close(ticket_id: str, closed_by: str = "",
                           transcript_url: str = "") -> bool:
    """Close a ticket and optionally save a transcript URL."""
    return await _update("tickets", {"id": ticket_id}, {
        "status": "closed",
        "closed_at": _now(),
        "claimed_by": closed_by or None,
        "transcript_url": transcript_url or None,
        "updated_at": _now(),
    })


# =============================================================================
# GIVEAWAYS
# =============================================================================

async def on_giveaway_enter(giveaway_id: str, user_id: str) -> bool:
    """Add a giveaway entry (unique constraint handles duplicate prevention)."""
    row = await _insert("giveaway_entries", {
        "giveaway_id": giveaway_id,
        "user_id": user_id,
        "entered_at": _now(),
    })
    return row is not None


async def on_giveaway_end(giveaway_id: str, winners: List[str]) -> bool:
    """Mark giveaway ended and record winners."""
    return await _update("giveaways", {"id": giveaway_id}, {
        "status": "ended",
        "winners": winners,
        "ended_at": _now(),
    })


# =============================================================================
# REACTION ROLES
# =============================================================================

async def on_reaction_role_add(server_id: str, channel_id: str,
                                message_id: str, emoji: str,
                                role_id: str, mode: str = "multiple") -> None:
    """Register a reaction-role mapping."""
    await _upsert("reaction_roles", {
        "server_id": server_id,
        "channel_id": channel_id,
        "message_id": message_id,
        "emoji": emoji,
        "role_id": role_id,
        "mode": mode,
    }, on_conflict="server_id,message_id,emoji")


async def on_reaction_role_remove(server_id: str, message_id: str, emoji: str) -> bool:
    """Remove a reaction-role mapping."""
    try:
        sb = await get_client()
        await (sb.table("reaction_roles")
                 .delete()
                 .eq("server_id", server_id)
                 .eq("message_id", message_id)
                 .eq("emoji", emoji)
                 .execute())
        return True
    except Exception as e:
        logger.error(f"[event] reaction_role_remove failed: {e}")
        return False


# =============================================================================
# REMINDERS
# =============================================================================

async def on_reminder_fire(reminder_id: str) -> bool:
    """Mark a reminder as completed after it fires."""
    return await _update("reminders", {"id": reminder_id}, {"completed": True})


# =============================================================================
# ANALYTICS
# =============================================================================

async def on_analytics_event(server_id: str, user_id: Optional[str],
                               event_type: str,
                               data: Optional[Dict[str, Any]] = None) -> None:
    """Generic analytics event sink — fire-and-forget, never blocks bot logic."""
    try:
        await _insert("analytics_events", {
            "server_id": server_id,
            "user_id": user_id,
            "event_type": event_type,
            "data": data or {},
            "created_at": _now(),
        })
    except Exception:
        pass   # analytics must never crash the bot


# =============================================================================
# AUDIT LOG
# =============================================================================

async def on_audit_log(server_id: Optional[str], actor_id: str,
                        action: str, target_type: Optional[str] = None,
                        target_id: Optional[str] = None,
                        old_value: Optional[Dict] = None,
                        new_value: Optional[Dict] = None) -> None:
    """Internal bot audit trail — separate from Stoat's platform audit log."""
    await _insert("audit_log", {
        "server_id": server_id,
        "actor_id": actor_id,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "old_value": old_value,
        "new_value": new_value,
        "created_at": _now(),
    })
