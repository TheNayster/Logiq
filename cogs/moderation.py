"""
Moderation Cog — StoatMod
AutoMod-style moderation commands for Stoat.chat.

All commands require Moderator or Admin role unless noted.
Usage syntax matches AutoMod conventions:
  !ban <user_id> [duration] [reason]
  !kick <user_id> [reason]
  !warn <user_id> [reason]
  !unban <user_id> [reason]
  !timeout <user_id> <duration> [reason]
  !mute <user_id> [duration] [reason]
  !unmute <user_id>
  !nick <user_id> <nickname>
  !purge <amount> [user_id]
  !infractions <user_id>
  !case <case_number>
  !reason <case_number> <reason>
  !history <user_id>

Aliases:
  !ban   → !eject
  !kick  → !boot
  !warn  → !strike
"""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedFactory, EmbedColor
from utils.converters import TimeConverter, UserConverter
import database.supabase as supa

logger = logging.getLogger(__name__)


class Moderation(AdaptedCog):
    """Moderation commands — Stoat-only, AutoMod-compatible"""

    def __init__(self, adapter, db, config: dict):
        super().__init__(adapter, db, config)
        self.module_config = config.get("modules", {}).get("moderation", {})

    # ── permission helpers ─────────────────────────────────────────────────────

    async def _is_mod(self, server_id: str, user_id: str) -> bool:
        owner_id = os.getenv("BOT_OWNER_ID")
        if owner_id and user_id == owner_id:
            return True
        try:
            sb = await supa.get_client()
            res = await (sb.table("server_members")
                          .select("is_mod,is_admin,is_owner")
                          .eq("server_id", server_id)
                          .eq("user_id", user_id)
                          .maybe_single()
                          .execute())
            if res and res.data:
                return any([res.data.get("is_mod"), res.data.get("is_admin"), res.data.get("is_owner")])
        except Exception as e:
            logger.error(f"Mod check error: {e}")
        return False

    # ── ban ────────────────────────────────────────────────────────────────────

    @app_command(
        name="ban",
        description="Ban a user from the server",
        usage="!ban <user_id> [duration] [reason]  e.g. !ban 01KHXXX 7d Harassment"
    )
    async def ban(self, interaction: Dict[str, Any],
                  user_id: str, duration: str = "", reason: str = "No reason provided"):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        mod_id     = interaction["user_id"]

        # resolve mentions like <@01KH...>
        user_id = UserConverter.parse_user_id(user_id) or user_id

        if not await self._is_mod(server_id, mod_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                         "You need **Moderator** to use this command.", EmbedColor.ERROR)

        # parse optional duration
        secs = TimeConverter.parse(duration) if duration else None
        full_reason = f"{reason} (duration: {duration})" if secs else reason

        await supa.on_member_ban(server_id, user_id, mod_id, full_reason)

        embed = EmbedFactory.moderation_action("Banned", user_id, user_id, mod_id, mod_id, full_reason)
        if secs:
            embed.setdefault("fields", []).append(
                {"name": "Duration", "value": duration, "inline": True}
            )
        await self.send_message(channel_id, embed=embed)
        logger.info(f"[ban] {user_id} by {mod_id} in {server_id}")

    # alias
    @app_command(name="eject", description="Alias for !ban",
                 usage="!eject <user_id> [duration] [reason]")
    async def eject(self, interaction: Dict[str, Any],
                    user_id: str, duration: str = "", reason: str = "No reason provided"):
        await self.ban(interaction, user_id, duration, reason)

    # ── unban ──────────────────────────────────────────────────────────────────

    @app_command(name="unban", description="Unban a user",
                 usage="!unban <user_id> [reason]")
    async def unban(self, interaction: Dict[str, Any],
                    user_id: str, reason: str = "Ban lifted"):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        mod_id     = interaction["user_id"]
        user_id    = UserConverter.parse_user_id(user_id) or user_id

        if not await self._is_mod(server_id, mod_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                         "You need **Moderator** to use this command.", EmbedColor.ERROR)

        await supa.on_member_unban(server_id, user_id, mod_id, reason)
        await self.send_embed(channel_id, "✅ Unbanned",
                               f"<@{user_id}> has been unbanned.\n**Reason:** {reason}",
                               EmbedColor.SUCCESS)

    # ── kick ───────────────────────────────────────────────────────────────────

    @app_command(name="kick", description="Kick a user from the server",
                 usage="!kick <user_id> [reason]")
    async def kick(self, interaction: Dict[str, Any],
                   user_id: str, reason: str = "No reason provided"):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        mod_id     = interaction["user_id"]
        user_id    = UserConverter.parse_user_id(user_id) or user_id

        if not await self._is_mod(server_id, mod_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                         "You need **Moderator** to use this command.", EmbedColor.ERROR)

        await supa.on_member_leave(server_id, user_id)
        await supa.on_mod_action(server_id, user_id, mod_id, "kick", reason)
        embed = EmbedFactory.moderation_action("Kicked", user_id, user_id, mod_id, mod_id, reason)
        await self.send_message(channel_id, embed=embed)
        logger.info(f"[kick] {user_id} by {mod_id} in {server_id}")

    @app_command(name="boot", description="Alias for !kick",
                 usage="!boot <user_id> [reason]")
    async def boot(self, interaction: Dict[str, Any],
                   user_id: str, reason: str = "No reason provided"):
        await self.kick(interaction, user_id, reason)

    # ── warn ───────────────────────────────────────────────────────────────────

    @app_command(name="warn", description="Warn a user",
                 usage="!warn <user_id> [reason]")
    async def warn(self, interaction: Dict[str, Any],
                   user_id: str, reason: str = "No reason provided"):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        mod_id     = interaction["user_id"]
        user_id    = UserConverter.parse_user_id(user_id) or user_id

        if not await self._is_mod(server_id, mod_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                         "You need **Moderator** to use this command.", EmbedColor.ERROR)

        row = await supa.on_warning_add(server_id, user_id, mod_id, reason)
        # get current active warning count
        try:
            sb = await supa.get_client()
            count_res = await sb.rpc("get_warning_count",
                                     {"p_server_id": server_id, "p_user_id": user_id}).execute()
            warn_count = count_res.data or 1
        except Exception:
            warn_count = "?"

        await self.send_embed(
            channel_id, "⚠️ Warning Issued",
            f"<@{user_id}> has been warned (total active warnings: **{warn_count}**).\n**Reason:** {reason}",
            EmbedColor.WARNING
        )

    @app_command(name="strike", description="Alias for !warn",
                 usage="!strike <user_id> [reason]")
    async def strike(self, interaction: Dict[str, Any],
                     user_id: str, reason: str = "No reason provided"):
        await self.warn(interaction, user_id, reason)

    # ── timeout ────────────────────────────────────────────────────────────────

    @app_command(name="timeout", description="Timeout a user (mute for a duration)",
                 usage="!timeout <user_id> <duration> [reason]  e.g. !timeout 01KHXXX 10m Spamming")
    async def timeout(self, interaction: Dict[str, Any],
                      user_id: str, duration: str = "10m",
                      reason: str = "No reason provided"):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        mod_id     = interaction["user_id"]
        user_id    = UserConverter.parse_user_id(user_id) or user_id

        if not await self._is_mod(server_id, mod_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                         "You need **Moderator** to use this command.", EmbedColor.ERROR)

        secs = TimeConverter.parse(duration)
        if not secs:
            return await self.send_embed(channel_id, "Invalid Duration",
                                         "Use format: `30s`, `5m`, `1h`, `2d`", EmbedColor.ERROR)

        await supa.on_mod_action(server_id, user_id, mod_id, "timeout", reason, duration_secs=secs)
        await self.send_embed(
            channel_id, "🔇 Timeout Applied",
            f"<@{user_id}> timed out for **{duration}**.\n**Reason:** {reason}",
            EmbedColor.WARNING
        )

    # ── mute / unmute ──────────────────────────────────────────────────────────

    @app_command(name="mute", description="Mute a user",
                 usage="!mute <user_id> [duration] [reason]  e.g. !mute 01KHXXX 1h Arguing")
    async def mute(self, interaction: Dict[str, Any],
                   user_id: str, duration: str = "", reason: str = "No reason provided"):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        mod_id     = interaction["user_id"]
        user_id    = UserConverter.parse_user_id(user_id) or user_id

        if not await self._is_mod(server_id, mod_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                         "You need **Moderator** to use this command.", EmbedColor.ERROR)

        secs = TimeConverter.parse(duration) if duration else None
        await supa.on_mod_action(server_id, user_id, mod_id, "mute", reason,
                                  duration_secs=secs)
        sb = await supa.get_client()
        await (sb.table("server_members")
                 .update({"is_muted": True})
                 .eq("server_id", server_id)
                 .eq("user_id", user_id)
                 .execute())

        dur_str = f" for **{duration}**" if duration else " indefinitely"
        await self.send_embed(
            channel_id, "🔇 User Muted",
            f"<@{user_id}> has been muted{dur_str}.\n**Reason:** {reason}",
            EmbedColor.WARNING
        )

    @app_command(name="unmute", description="Unmute a user",
                 usage="!unmute <user_id>")
    async def unmute(self, interaction: Dict[str, Any], user_id: str):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        mod_id     = interaction["user_id"]
        user_id    = UserConverter.parse_user_id(user_id) or user_id

        if not await self._is_mod(server_id, mod_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                         "You need **Moderator** to use this command.", EmbedColor.ERROR)

        sb = await supa.get_client()
        await (sb.table("server_members")
                 .update({"is_muted": False})
                 .eq("server_id", server_id)
                 .eq("user_id", user_id)
                 .execute())
        await supa.on_mod_action(server_id, user_id, mod_id, "unmute", "Unmuted")
        await self.send_embed(channel_id, "🔊 Unmuted",
                               f"<@{user_id}> has been unmuted.", EmbedColor.SUCCESS)

    # ── nick ───────────────────────────────────────────────────────────────────

    @app_command(name="nick", description="Change a user's nickname",
                 usage="!nick <user_id> <new_nickname>  — use 'reset' to clear")
    async def nick(self, interaction: Dict[str, Any],
                   user_id: str, nickname: str):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        mod_id     = interaction["user_id"]
        user_id    = UserConverter.parse_user_id(user_id) or user_id

        if not await self._is_mod(server_id, mod_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                         "You need **Moderator** to use this command.", EmbedColor.ERROR)

        new_nick = None if nickname.lower() == "reset" else nickname

        ok = await self.adapter.set_member_nickname(server_id, user_id, new_nick)
        if not ok:
            return await self.send_embed(channel_id, "Failed",
                                         "Could not change the nickname — the platform API rejected the request.",
                                         EmbedColor.ERROR)

        sb = await supa.get_client()
        await (sb.table("server_members")
                 .update({"display_name": new_nick})
                 .eq("server_id", server_id)
                 .eq("user_id", user_id)
                 .execute())
        await supa.on_audit_log(server_id, mod_id, "nick_change",
                                 "user", user_id, new_value={"display_name": new_nick})

        msg = f"Nickname reset for <@{user_id}>." if not new_nick else \
              f"Nickname for <@{user_id}> set to **{new_nick}**."
        await self.send_embed(channel_id, "✏️ Nickname Changed", msg, EmbedColor.SUCCESS)

    # ── purge ──────────────────────────────────────────────────────────────────

    @app_command(name="purge", description="Delete recent messages in this channel",
                 usage="!purge <amount 1-100> [user_id]  — filters by user if provided")
    async def purge(self, interaction: Dict[str, Any],
                    amount: int, user_id: Optional[str] = None):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        mod_id     = interaction["user_id"]

        if not await self._is_mod(server_id, mod_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                         "You need **Moderator** to use this command.", EmbedColor.ERROR)

        if not 1 <= amount <= 100:
            return await self.send_embed(channel_id, "Invalid Amount",
                                         "Amount must be between **1** and **100**.", EmbedColor.ERROR)

        # Fetch recent messages then bulk-delete via Stoat API
        try:
            messages = await self.adapter.fetch_messages(channel_id, limit=amount + 1)
            to_delete = []
            for msg in messages:
                msg_id   = msg.get("_id") or msg.get("id")
                msg_auth = msg.get("author", "")
                if user_id and msg_auth != user_id:
                    continue
                to_delete.append(msg_id)
                if len(to_delete) >= amount:
                    break

            # Stoat bulk-delete endpoint
            if to_delete:
                headers = {"X-Bot-Token": self.adapter.token}
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.delete(
                        f"{self.adapter.api_base}/channels/{channel_id}/messages/bulk",
                        json={"ids": to_delete},
                        headers=headers
                    ) as resp:
                        deleted = len(to_delete) if resp.status in (200, 204) else 0
            else:
                deleted = 0

            await supa.on_audit_log(server_id, mod_id, "purge", "channel", channel_id,
                                     new_value={"deleted": deleted, "filter_user": user_id})
            await self.send_embed(channel_id, "🗑️ Purge Complete",
                                   f"Deleted **{deleted}** message(s).", EmbedColor.SUCCESS)
        except Exception as e:
            logger.error(f"[purge] error: {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── infractions ────────────────────────────────────────────────────────────

    @app_command(name="infractions", description="List infractions for a user",
                 usage="!infractions <user_id>")
    async def infractions(self, interaction: Dict[str, Any], user_id: str):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        mod_id     = interaction["user_id"]
        user_id    = UserConverter.parse_user_id(user_id) or user_id

        if not await self._is_mod(server_id, mod_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                         "You need **Moderator** to use this command.", EmbedColor.ERROR)

        try:
            sb = await supa.get_client()
            res = await (sb.table("mod_actions")
                           .select("case_number,action_type,reason,created_at,moderator_id")
                           .eq("server_id", server_id)
                           .eq("target_id", user_id)
                           .order("case_number", desc=False)
                           .limit(15)
                           .execute())
            rows = (res.data if res else None) or []

            if not rows:
                return await self.send_embed(channel_id, "📋 Infractions",
                                              f"<@{user_id}> has no infractions.", EmbedColor.INFO)

            lines = []
            for r in rows:
                ts = r["created_at"][:10]
                lines.append(
                    f"**Case #{r['case_number']}** `{r['action_type'].upper()}` — "
                    f"{r['reason'][:60]} *(by <@{r['moderator_id']}> on {ts})*"
                )

            await self.send_embed(
                channel_id, f"📋 Infractions — <@{user_id}>",
                "\n".join(lines), EmbedColor.WARNING
            )
        except Exception as e:
            logger.error(f"[infractions] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── history (alias for infractions) ───────────────────────────────────────

    @app_command(name="history", description="View moderation history for a user",
                 usage="!history <user_id>")
    async def history(self, interaction: Dict[str, Any], user_id: str):
        await self.infractions(interaction, user_id)

    # ── case ───────────────────────────────────────────────────────────────────

    @app_command(name="case", description="View a specific mod case by number",
                 usage="!case <case_number>")
    async def case(self, interaction: Dict[str, Any], case_number: int):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        mod_id     = interaction["user_id"]

        if not await self._is_mod(server_id, mod_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                         "You need **Moderator** to use this command.", EmbedColor.ERROR)
        try:
            sb = await supa.get_client()
            res = await (sb.table("mod_actions")
                           .select("*")
                           .eq("server_id", server_id)
                           .eq("case_number", case_number)
                           .maybe_single()
                           .execute())
            if not res or not res.data:
                return await self.send_embed(channel_id, "Not Found",
                                              f"Case #{case_number} not found.", EmbedColor.ERROR)
            r = (res.data if res else None)
            fields = [
                {"name": "Action",    "value": r["action_type"].upper(), "inline": True},
                {"name": "Target",    "value": f"<@{r['target_id']}>",   "inline": True},
                {"name": "Moderator", "value": f"<@{r['moderator_id']}>","inline": True},
                {"name": "Reason",    "value": r["reason"],              "inline": False},
                {"name": "Date",      "value": r["created_at"][:19],     "inline": True},
            ]
            if r.get("duration_secs"):
                fields.append({"name": "Duration",
                                "value": f"{r['duration_secs']}s", "inline": True})
            embed = EmbedFactory.create(
                title=f"📋 Case #{case_number}",
                color=EmbedColor.INFO,
                fields=fields
            )
            await self.send_message(channel_id, embed=embed)
        except Exception as e:
            logger.error(f"[case] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── reason ─────────────────────────────────────────────────────────────────

    @app_command(name="reason", description="Edit the reason on a mod case",
                 usage="!reason <case_number> <new reason>")
    async def reason(self, interaction: Dict[str, Any],
                     case_number: int, new_reason: str):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        mod_id     = interaction["user_id"]

        if not await self._is_mod(server_id, mod_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                         "You need **Moderator** to use this command.", EmbedColor.ERROR)
        try:
            sb = await supa.get_client()
            res = await (sb.table("mod_actions")
                           .update({"reason": new_reason})
                           .eq("server_id", server_id)
                           .eq("case_number", case_number)
                           .execute())
            await self.send_embed(channel_id, "✅ Reason Updated",
                                   f"Case #{case_number} reason set to: {new_reason}",
                                   EmbedColor.SUCCESS)
        except Exception as e:
            logger.error(f"[reason] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── clear (kept for compatibility) ─────────────────────────────────────────

    @app_command(name="clear", description="Alias for !purge",
                 usage="!clear <amount> [user_id]")
    async def clear(self, interaction: Dict[str, Any],
                    amount: int, user_id: Optional[str] = None):
        await self.purge(interaction, amount, user_id)


async def setup(adapter, db, config):
    return Moderation(adapter, db, config)
