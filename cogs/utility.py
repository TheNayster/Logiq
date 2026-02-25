"""
Utility Cog — StoatMod
General-purpose commands available to all users.

Commands:
  !ping                  — Latency check
  !channelid             — Show current channel ID
  !info                  — Bot information / support links
  !serverinfo            — Server stats from Supabase
  !userinfo [user]       — Member profile
  !poll <q> <a> <b> [c] [minutes] — Create a poll  (Admin)
  !remind <duration> <message>    — Set a personal reminder
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedFactory, EmbedColor
from utils.converters import TimeConverter, UserConverter
import database.supabase as supa

logger = logging.getLogger(__name__)


class Utility(AdaptedCog):
    """Utility commands — Stoat-only, Supabase-backed"""

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
            return bool(res and res.data and (res.data.get("is_admin") or res.data.get("is_owner")))
        except Exception:
            return False

    # ── ping ──────────────────────────────────────────────────────────────────

    @app_command(name="ping", description="Check bot latency")
    async def ping(self, interaction: Dict[str, Any]):
        channel_id = interaction["channel_id"]
        t0 = time.monotonic()
        msg_id = await self.send_embed(channel_id, "🏓 Pong!", "Measuring...", EmbedColor.INFO)
        latency = int((time.monotonic() - t0) * 1000)
        await self.send_embed(channel_id, "🏓 Pong!",
                               f"Response time: **{latency} ms**", EmbedColor.SUCCESS)

    # ── channelid ─────────────────────────────────────────────────────────────

    @app_command(name="channelid", description="Show the ID of the current channel")
    async def channelid(self, interaction: Dict[str, Any]):
        channel_id = interaction["channel_id"]
        await self.send_embed(
            channel_id,
            "Channel ID",
            f"`{channel_id}`",
            color=EmbedColor.INFO,
        )

    # ── info ──────────────────────────────────────────────────────────────────

    @app_command(name="info", description="Bot information and links")
    async def info(self, interaction: Dict[str, Any]):
        channel_id = interaction["channel_id"]
        embed = EmbedFactory.create(
            title="ℹ️ StoatMod",
            description=(
                "A feature-rich moderation and community bot built for Stoat.chat.\n\n"
                "**🌐 Website:** https://stoatmod.vercel.app\n"
                "**📖 Docs:** https://stoatmod.vercel.app/docs\n"
                "**🐛 Issues:** https://github.com/stoatmod\n"
                "**➕ Add Bot:** https://stoat.chat/bot/01KHQGBV9WEQYRBKXWHHENES43\n"
                "**💬 Support:** Use `!support` or join our support server."
            ),
            color=EmbedColor.PRIMARY,
            footer="StoatMod | Stoat.chat"
        )
        await self.send_message(channel_id, embed=embed)

    @app_command(name="support", description="Get support server link")
    async def support(self, interaction: Dict[str, Any]):
        channel_id = interaction["channel_id"]
        await self.send_embed(
            channel_id, "💬 Support",
            "Join our support server or open a GitHub issue.\n"
            "https://stoatmod.vercel.app/support",
            EmbedColor.INFO
        )

    # ── serverinfo ────────────────────────────────────────────────────────────

    @app_command(name="serverinfo", description="View server stats")
    async def serverinfo(self, interaction: Dict[str, Any]):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")

        try:
            sb = await supa.get_client()

            srv_res = await (sb.table("servers")
                               .select("name,owner_id,bot_joined_at,prefix,moderation_enabled,"
                                       "leveling_enabled,economy_enabled")
                               .eq("id", server_id)
                               .maybe_single()
                               .execute())
            srv = srv_res.data or {}

            mem_res = await (sb.table("server_members")
                               .select("id", count="exact")
                               .eq("server_id", server_id)
                               .is_("left_at",  "null")
                               .execute())
            member_count = mem_res.count or 0

            mod_res = await (sb.table("mod_actions")
                               .select("id", count="exact")
                               .eq("server_id", server_id)
                               .execute())
            mod_count = mod_res.count or 0

            modules_on = ", ".join(
                m for m in ["moderation", "leveling", "economy"]
                if srv.get(f"{m}_enabled", True)
            ) or "None"

            joined = (srv.get("bot_joined_at") or "")[:10]

            embed = EmbedFactory.create(
                title=f"📊 {srv.get('name') or server_id}",
                description=(
                    f"**Server ID:** {server_id}\n"
                    f"**Owner:** <@{srv.get('owner_id', '?')}>\n"
                    f"**Prefix:** `{srv.get('prefix', '!')}`\n"
                    f"**Active Members:** {member_count}\n"
                    f"**Total Mod Actions:** {mod_count}\n"
                    f"**Bot Joined:** {joined or 'Unknown'}\n"
                    f"**Active Modules:** {modules_on}"
                ),
                color=EmbedColor.INFO,
            )
            await self.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"[serverinfo] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── userinfo ──────────────────────────────────────────────────────────────

    @app_command(name="userinfo", description="View a member's profile",
                 usage="!userinfo [user_id]")
    async def userinfo(self, interaction: Dict[str, Any], user_id: Optional[str] = None):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        target     = UserConverter.parse_user_id(user_id) or user_id or interaction["user_id"]

        try:
            sb  = await supa.get_client()
            res = await (sb.table("server_members")
                           .select("xp,level,balance,total_messages,is_mod,is_admin,"
                                   "is_muted,is_banned,joined_at,rejoin_count,display_name")
                           .eq("server_id", server_id)
                           .eq("user_id",   target)
                           .maybe_single()
                           .execute())

            if not res or not res.data:
                return await self.send_embed(
                    channel_id, "Not Found",
                    f"<@{target}> has no data in this server.", EmbedColor.ERROR
                )

            m     = (res.data if res else None)
            roles = []
            if m.get("is_admin"):  roles.append("Admin")
            if m.get("is_mod"):    roles.append("Moderator")
            if m.get("is_muted"):  roles.append("🔇 Muted")
            if m.get("is_banned"): roles.append("🚫 Banned")

            # Warning count
            warn_res = await sb.rpc("get_warning_count",
                                     {"p_server_id": server_id, "p_user_id": target}).execute()
            warns = warn_res.data or 0

            joined = (m.get("joined_at") or "")[:10]

            embed = EmbedFactory.create(
                title=f"👤 {m.get('display_name') or target}",
                description=(
                    f"<@{target}>\n\n"
                    f"**User ID:** {target}\n"
                    f"**Joined:** {joined or '?'}\n"
                    f"**Rejoins:** {m.get('rejoin_count', 0)}\n"
                    f"**Level:** {m.get('level', 0)}\n"
                    f"**XP:** {m.get('xp', 0):,}\n"
                    f"**Balance:** 💎 {m.get('balance', 0):,}\n"
                    f"**Messages:** {m.get('total_messages', 0):,}\n"
                    f"**Warnings:** {warns}\n"
                    f"**Roles:** {', '.join(roles) or 'Member'}"
                ),
                color=EmbedColor.INFO,
            )
            await self.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"[userinfo] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── poll ──────────────────────────────────────────────────────────────────

    @app_command(name="poll",
                 description="Create a poll (Admin)",
                 usage="!poll <question> <option1> <option2> [option3] [minutes]  "
                       "— wrap multi-word options in quotes")
    async def poll(self, interaction: Dict[str, Any],
                   question: str, option1: str, option2: str,
                   option3: Optional[str] = None, duration: int = 60):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        user_id    = interaction["user_id"]

        if not await self._is_admin(server_id, user_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                          "Only **Admins** can create polls.", EmbedColor.ERROR)

        options = [option1, option2]
        if option3:
            options.append(option3)

        emojis  = ["1️⃣", "2️⃣", "3️⃣"]
        opt_str = "\n".join(f"{emojis[i]} {opt}" for i, opt in enumerate(options))

        embed = EmbedFactory.create(
            title=f"📊 {question}",
            description=f"{opt_str}\n\n*Poll closes in {duration} minutes.*",
            color=EmbedColor.INFO,
            footer=f"Started by {user_id}"
        )
        await self.send_message(channel_id, embed=embed)

        # Store in Supabase analytics for later tally reference
        await supa.on_analytics_event(server_id, user_id, "poll_created",
                                       {"question": question, "options": options,
                                        "duration_min": duration})

    # ── remind ────────────────────────────────────────────────────────────────

    @app_command(name="remind",
                 description="Set a reminder",
                 usage="!remind <duration> <message>  e.g. !remind 30m Take a break")
    async def remind(self, interaction: Dict[str, Any], duration: str, message: str):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        user_id    = interaction["user_id"]

        secs = TimeConverter.parse(duration)
        if not secs or secs < 30:
            return await self.send_embed(channel_id, "Invalid Duration",
                                          "Minimum reminder time is **30 seconds**.\n"
                                          "Format: `30s`, `5m`, `1h`, `2d`", EmbedColor.ERROR)

        remind_at = (datetime.now(timezone.utc) + timedelta(seconds=secs)).isoformat()

        try:
            sb  = await supa.get_client()
            res = await (sb.table("reminders")
                           .insert({
                               "server_id":  server_id,
                               "user_id":    user_id,
                               "channel_id": channel_id,
                               "message":    message,
                               "remind_at":  remind_at,
                           })
                           .execute())
            reminder_id = res.data[0]["id"] if res.data else None

            await self.send_embed(
                channel_id, "⏰ Reminder Set",
                f"I'll remind you in **{duration}**:\n> {message}",
                EmbedColor.SUCCESS
            )

            # Fire in background — doesn't block the event loop
            if reminder_id:
                asyncio.create_task(
                    self._fire_reminder(reminder_id, channel_id, user_id, message, secs)
                )

        except Exception as e:
            logger.error(f"[remind] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    async def _fire_reminder(self, reminder_id: str, channel_id: str,
                              user_id: str, message: str, secs: int):
        await asyncio.sleep(secs)
        await self.adapter.send_message(
            channel_id,
            embed=EmbedFactory.create(
                title="⏰ Reminder",
                description=f"<@{user_id}> — {message}",
                color=EmbedColor.INFO
            )
        )
        await supa.on_reminder_fire(reminder_id)


async def setup(adapter, db, config):
    return Utility(adapter, db, config)
