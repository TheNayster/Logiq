"""
Roles Cog — StoatMod
Role assignment and reaction-role management.

Commands (Admin only):
  !role-assign <user> <role>       — Assign a role
  !role-remove <user> <role>       — Remove a role
  !role-list                       — List server roles
  !role-info <role_id>             — Details on a role
  !rr-add <msg_id> <emoji> <role>  — Add reaction-role mapping
  !rr-remove <msg_id> <emoji>      — Remove reaction-role mapping
  !rr-list                         — List all reaction-role mappings
"""

import logging
import os
from typing import Dict, Any, Optional

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedFactory, EmbedColor
from utils.converters import UserConverter
import database.supabase as supa

logger = logging.getLogger(__name__)


class Roles(AdaptedCog):
    """Role management — Stoat-only, Supabase-backed"""

    def __init__(self, adapter, db, config: dict):
        super().__init__(adapter, db, config)

    async def _is_admin(self, server_id: str, user_id: str) -> bool:
        if user_id == os.getenv("BOT_OWNER_ID", ""):
            return True
        try:
            sb  = await supa.get_client()
            res = await (sb.table("server_members")
                           .select("is_admin,is_owner")
                           .eq("server_id", server_id)
                           .eq("user_id",   user_id)
                           .maybe_single()
                           .execute())
            return bool(res.data and (res.data.get("is_admin") or res.data.get("is_owner")))
        except Exception:
            return False

    # ── role-assign ───────────────────────────────────────────────────────────

    @app_command(name="role-assign", description="Assign a role to a user (Admin)",
                 usage="!role-assign <user_id> <role_id>")
    async def role_assign(self, interaction: Dict[str, Any], user_id: str, role_id: str):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        admin_id   = interaction["user_id"]
        target     = UserConverter.parse_user_id(user_id) or user_id

        if not await self._is_admin(server_id, admin_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                          "Only **Admins** can assign roles.", EmbedColor.ERROR)
        try:
            success = await self.adapter.add_role(server_id, target, role_id)
            if success:
                await supa.on_audit_log(server_id, admin_id, "role_assign",
                                         "user", target, new_value={"role_id": role_id})
                await self.send_embed(channel_id, "✅ Role Assigned",
                                       f"<@&{role_id}> → <@{target}>", EmbedColor.SUCCESS)
            else:
                await self.send_embed(channel_id, "Failed",
                                       "Could not assign role. Check bot permissions.", EmbedColor.ERROR)
        except Exception as e:
            logger.error(f"[role-assign] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── role-remove ───────────────────────────────────────────────────────────

    @app_command(name="role-remove", description="Remove a role from a user (Admin)",
                 usage="!role-remove <user_id> <role_id>")
    async def role_remove(self, interaction: Dict[str, Any], user_id: str, role_id: str):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        admin_id   = interaction["user_id"]
        target     = UserConverter.parse_user_id(user_id) or user_id

        if not await self._is_admin(server_id, admin_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                          "Only **Admins** can remove roles.", EmbedColor.ERROR)
        try:
            success = await self.adapter.remove_role(server_id, target, role_id)
            if success:
                await supa.on_audit_log(server_id, admin_id, "role_remove",
                                         "user", target, new_value={"role_id": role_id})
                await self.send_embed(channel_id, "✅ Role Removed",
                                       f"<@&{role_id}> removed from <@{target}>", EmbedColor.SUCCESS)
            else:
                await self.send_embed(channel_id, "Failed",
                                       "Could not remove role. Check bot permissions.", EmbedColor.ERROR)
        except Exception as e:
            logger.error(f"[role-remove] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── role-list ─────────────────────────────────────────────────────────────

    @app_command(name="role-list", description="List configured reaction roles for this server")
    async def role_list(self, interaction: Dict[str, Any]):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")

        try:
            sb  = await supa.get_client()
            res = await (sb.table("reaction_roles")
                           .select("role_id,emoji,mode,message_id")
                           .eq("server_id", server_id)
                           .limit(25)
                           .execute())
            rows = res.data or []

            if not rows:
                return await self.send_embed(channel_id, "📋 Reaction Roles",
                                              "No reaction roles configured.\n"
                                              "Use `!rr-add` to add one.", EmbedColor.INFO)

            lines = [f"**{r['emoji']}** → <@&{r['role_id']}> `{r['mode']}` "
                     f"(msg `{str(r['message_id'])[:8]}`)" for r in rows]
            await self.send_embed(channel_id, "📋 Reaction Roles",
                                   "\n".join(lines), EmbedColor.INFO)

        except Exception as e:
            logger.error(f"[role-list] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── rr-add ────────────────────────────────────────────────────────────────

    @app_command(name="rr-add",
                 description="Add a reaction-role mapping (Admin)",
                 usage="!rr-add <message_id> <emoji> <role_id> [mode]  "
                       "— mode: single (default), multiple, verify")
    async def rr_add(self, interaction: Dict[str, Any],
                     message_id: str, emoji: str, role_id: str, mode: str = "single"):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        admin_id   = interaction["user_id"]

        if not await self._is_admin(server_id, admin_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                          "Only **Admins** can manage reaction roles.", EmbedColor.ERROR)

        mode = mode.lower()
        if mode not in ("single", "multiple", "verify"):
            return await self.send_embed(channel_id, "Invalid Mode",
                                          "Mode must be `single`, `multiple`, or `verify`.",
                                          EmbedColor.ERROR)
        try:
            await supa.on_reaction_role_add(server_id, channel_id, message_id,
                                             emoji, role_id, mode)
            await self.send_embed(
                channel_id, "✅ Reaction Role Added",
                f"{emoji} → <@&{role_id}> on message `{message_id[:8]}` (mode: `{mode}`)",
                EmbedColor.SUCCESS
            )
        except Exception as e:
            logger.error(f"[rr-add] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── rr-remove ─────────────────────────────────────────────────────────────

    @app_command(name="rr-remove", description="Remove a reaction-role mapping (Admin)",
                 usage="!rr-remove <message_id> <emoji>")
    async def rr_remove(self, interaction: Dict[str, Any], message_id: str, emoji: str):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        admin_id   = interaction["user_id"]

        if not await self._is_admin(server_id, admin_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                          "Only **Admins** can manage reaction roles.", EmbedColor.ERROR)
        try:
            await supa.on_reaction_role_remove(server_id, message_id, emoji)
            await self.send_embed(channel_id, "✅ Removed",
                                   f"Reaction role {emoji} on `{message_id[:8]}` removed.",
                                   EmbedColor.SUCCESS)
        except Exception as e:
            logger.error(f"[rr-remove] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── rr-list ───────────────────────────────────────────────────────────────

    @app_command(name="rr-list", description="List reaction-role mappings (alias for !role-list)")
    async def rr_list(self, interaction: Dict[str, Any]):
        await self.role_list(interaction)


async def setup(adapter, db, config):
    return Roles(adapter, db, config)
