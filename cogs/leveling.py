"""
Leveling Cog — StoatMod
XP on messages, rank cards, level-up notifications, level leaderboard.

Commands:
  !rank [user]    — View XP rank card
  !xp-lb [limit] — XP/level leaderboard  (replaces conflicted !leaderboard)
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from adapters.cog_base import AdaptedCog, app_command, listener
from utils.embeds import EmbedFactory, EmbedColor
from utils.converters import UserConverter
import database.supabase as supa

logger = logging.getLogger(__name__)


class Leveling(AdaptedCog):
    """Leveling system — Stoat-only, Supabase-backed"""

    def __init__(self, adapter, db, config: dict):
        super().__init__(adapter, db, config)
        self.module_config  = config.get("modules", {}).get("leveling", {})
        self.xp_per_message = self.module_config.get("xp_per_message",      10)
        self.xp_cooldown    = self.module_config.get("xp_cooldown",          60)   # seconds
        self.multiplier     = self.module_config.get("level_up_multiplier", 1.5)
        self.max_level      = self.module_config.get("max_level",           100)

    # ── XP maths ──────────────────────────────────────────────────────────────

    def _xp_for_level(self, level: int) -> int:
        """XP required to reach `level` from level 0."""
        return int(100 * (level ** self.multiplier)) if level > 0 else 0

    def _level_from_xp(self, xp: int) -> int:
        """Derive current level from total accumulated XP."""
        level = 0
        while level < self.max_level and xp >= self._xp_for_level(level + 1):
            level += 1
        return level

    # ── on_message listener ───────────────────────────────────────────────────

    @listener("on_message")
    async def on_message(self, payload: Dict[str, Any]):
        """Award XP on every message that clears the cooldown."""
        user_id   = payload.get("user_id")
        server_id = payload.get("server_id") or payload.get("guild_id")
        channel_id = payload.get("channel_id")

        if not user_id or not server_id:
            return

        try:
            sb  = await supa.get_client()
            res = await (sb.table("server_members")
                           .select("xp,level,last_xp_at")
                           .eq("server_id", server_id)
                           .eq("user_id",   user_id)
                           .maybe_single()
                           .execute())

            if not res.data:
                # Bootstrap member row on first message
                await supa.on_member_join(server_id, user_id)
                res = await (sb.table("server_members")
                               .select("xp,level,last_xp_at")
                               .eq("server_id", server_id)
                               .eq("user_id",   user_id)
                               .maybe_single()
                               .execute())

            member   = res.data or {}
            last_xp  = member.get("last_xp_at")
            now      = datetime.now(timezone.utc)

            # Enforce cooldown
            if last_xp:
                last_dt = datetime.fromisoformat(last_xp)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                if (now - last_dt).total_seconds() < self.xp_cooldown:
                    return

            old_xp    = member.get("xp",    0)
            old_level = member.get("level", 0)
            new_xp    = old_xp + self.xp_per_message
            new_level = self._level_from_xp(new_xp)
            leveled   = new_level > old_level

            await supa.on_xp_gain(server_id, user_id, self.xp_per_message,
                                   level_up=leveled, new_level=new_level)

            if leveled and channel_id:
                embed = EmbedFactory.level_up(user_id, user_id, new_level, new_xp)
                await self.adapter.send_message(channel_id, embed=embed)
                logger.info(f"[leveling] {user_id} reached level {new_level} in {server_id}")

        except Exception as e:
            logger.error(f"[leveling] on_message error: {e}", exc_info=True)

    # ── rank ──────────────────────────────────────────────────────────────────

    @app_command(name="rank", description="View your XP rank card",
                 usage="!rank [user_id]")
    async def rank(self, interaction: Dict[str, Any], user_id: Optional[str] = None):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        target     = UserConverter.parse_user_id(user_id) or user_id or interaction["user_id"]

        try:
            sb  = await supa.get_client()
            res = await (sb.table("server_members")
                           .select("xp,level,total_messages,display_name")
                           .eq("server_id", server_id)
                           .eq("user_id",   target)
                           .maybe_single()
                           .execute())

            if not res.data:
                return await self.send_embed(
                    channel_id, "No Data",
                    f"<@{target}> hasn't sent any messages yet.", EmbedColor.INFO
                )

            member     = res.data
            xp         = member.get("xp",    0)
            level      = member.get("level", 0)
            msgs       = member.get("total_messages", 0)
            next_xp    = self._xp_for_level(level + 1)
            curr_xp    = self._xp_for_level(level)
            progress   = (xp - curr_xp) / max(next_xp - curr_xp, 1) * 100
            bar        = "█" * int(progress / 10) + "░" * (10 - int(progress / 10))

            # Server rank position
            lb_res  = await sb.rpc("get_leaderboard",
                                    {"p_server_id": server_id, "p_limit": 500}).execute()
            lb_rows = lb_res.data or []
            rank_pos = next((r["rank"] for r in lb_rows if r["user_id"] == target), "?")

            embed = EmbedFactory.create(
                title=f"📊 Rank — {member.get('display_name') or target}",
                color=EmbedColor.LEVELING,
                fields=[
                    {"name": "🏅 Rank",      "value": f"#{rank_pos}",         "inline": True},
                    {"name": "📈 Level",     "value": str(level),              "inline": True},
                    {"name": "✨ XP",        "value": f"{xp:,} / {next_xp:,}", "inline": True},
                    {"name": "💬 Messages",  "value": f"{msgs:,}",             "inline": True},
                    {"name": "Progress",
                     "value": f"{bar} {progress:.1f}%",                        "inline": False},
                ]
            )
            await self.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"[rank] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── xp leaderboard ────────────────────────────────────────────────────────

    @app_command(name="xp-lb", description="XP / level leaderboard",
                 usage="!xp-lb [limit]")
    async def xp_lb(self, interaction: Dict[str, Any], limit: int = 10):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        limit      = max(1, min(limit, 25))

        try:
            sb  = await supa.get_client()
            res = await sb.rpc("get_leaderboard",
                                {"p_server_id": server_id, "p_limit": limit}).execute()
            rows   = res.data or []
            medals = ["🥇", "🥈", "🥉"]
            lines  = []
            for r in rows:
                icon = medals[r["rank"] - 1] if r["rank"] <= 3 else f"**{r['rank']}.**"
                lines.append(
                    f"{icon} <@{r['user_id']}> — Level **{r['level']}** ({r['xp']:,} XP)"
                )

            embed = EmbedFactory.create(
                title="🏆 XP Leaderboard",
                description="\n".join(lines) or "No data yet.",
                color=EmbedColor.LEVELING
            )
            await self.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"[xp-lb] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)


async def setup(adapter, db, config):
    return Leveling(adapter, db, config)
