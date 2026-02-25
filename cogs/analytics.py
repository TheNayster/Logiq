"""
Analytics Cog — StoatMod
Real server analytics from Supabase.

Commands (Admin only):
  !stats          — Full server analytics dashboard
  !stats mod      — Moderation action breakdown
  !stats economy  — Economy stats
  !stats leveling — Top XP earners summary
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedFactory, EmbedColor
import database.supabase as supa

logger = logging.getLogger(__name__)


class Analytics(AdaptedCog):
    """Server analytics — Stoat-only, Supabase-backed"""

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

    @app_command(name="stats", description="View server analytics (Admin)",
                 usage="!stats [mod|economy|leveling]")
    async def stats(self, interaction: Dict[str, Any], section: Optional[str] = None):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        user_id    = interaction["user_id"]

        if not await self._is_admin(server_id, user_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                          "Only **Admins** can view analytics.", EmbedColor.ERROR)

        section = (section or "").lower()

        try:
            sb  = await supa.get_client()
            now = datetime.now(timezone.utc)
            d30 = (now - timedelta(days=30)).isoformat()

            if section == "mod":
                await self._stats_mod(channel_id, server_id, sb, d30)
            elif section == "economy":
                await self._stats_economy(channel_id, server_id, sb)
            elif section == "leveling":
                await self._stats_leveling(channel_id, server_id, sb)
            else:
                await self._stats_overview(channel_id, server_id, sb, d30)

        except Exception as e:
            logger.error(f"[stats] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    async def _stats_overview(self, channel_id, server_id, sb, d30):
        # Members
        mem_res  = await (sb.table("server_members")
                            .select("id", count="exact")
                            .eq("server_id", server_id)
                            .is_("left_at",  "null")
                            .execute())
        members = mem_res.count or 0

        # New members (30d)
        new_res  = await (sb.table("server_members")
                            .select("id", count="exact")
                            .eq("server_id", server_id)
                            .gte("joined_at", d30)
                            .execute())
        new_members = new_res.count or 0

        # Mod actions (30d)
        mod_res  = await (sb.table("mod_actions")
                            .select("id", count="exact")
                            .eq("server_id",  server_id)
                            .gte("created_at", d30)
                            .execute())
        mod_actions = mod_res.count or 0

        # Open tickets
        tkt_res  = await (sb.table("tickets")
                            .select("id", count="exact")
                            .eq("server_id", server_id)
                            .eq("status",    "open")
                            .execute())
        open_tickets = tkt_res.count or 0

        # Active giveaways
        gw_res   = await (sb.table("giveaways")
                            .select("id", count="exact")
                            .eq("server_id", server_id)
                            .eq("status",    "active")
                            .execute())
        active_gw = gw_res.count or 0

        embed = EmbedFactory.create(
            title="📊 Server Analytics",
            description=(
                f"**👥 Active Members:** {members}\n"
                f"**📈 New (30d):** {new_members}\n"
                f"**🛡️ Mod Actions (30d):** {mod_actions}\n"
                f"**🎫 Open Tickets:** {open_tickets}\n"
                f"**🎉 Active Giveaways:** {active_gw}\n\n"
                "**Sections:** `!stats mod` · `!stats economy` · `!stats leveling`"
            ),
            color=EmbedColor.INFO,
            footer="Last 30 days unless noted"
        )
        await self.send_message(channel_id, embed=embed)

    async def _stats_mod(self, channel_id, server_id, sb, d30):
        res = await (sb.table("mod_actions")
                       .select("action_type")
                       .eq("server_id",  server_id)
                       .gte("created_at", d30)
                       .execute())
        rows = (res.data if res else None) or []
        counts: dict = {}
        for r in rows:
            t = r["action_type"]
            counts[t] = counts.get(t, 0) + 1

        lines = [f"**{k.upper()}**: {v}" for k, v in sorted(counts.items(), key=lambda x: -x[1])]
        await self.send_embed(
            channel_id, "🛡️ Mod Actions — Last 30 Days",
            "\n".join(lines) or "No mod actions in the last 30 days.",
            EmbedColor.WARNING
        )

    async def _stats_economy(self, channel_id, server_id, sb):
        # Total currency in circulation
        res = await (sb.table("server_members")
                       .select("balance")
                       .eq("server_id", server_id)
                       .is_("left_at",  "null")
                       .execute())
        balances = [r.get("balance", 0) for r in ((res.data if res else None) or [])]
        total    = sum(balances)
        avg      = int(total / len(balances)) if balances else 0
        top      = max(balances) if balances else 0

        await self.send_embed(
            channel_id, "💎 Economy Stats",
            f"**Total in circulation:** {total:,}\n"
            f"**Average balance:** {avg:,}\n"
            f"**Highest balance:** {top:,}\n"
            f"**Active wallets:** {len(balances)}",
            EmbedColor.ECONOMY
        )

    async def _stats_leveling(self, channel_id, server_id, sb):
        res = await sb.rpc("get_leaderboard",
                            {"p_server_id": server_id, "p_limit": 5}).execute()
        rows = (res.data if res else None) or []
        lines = [f"**#{r['rank']}** <@{r['user_id']}> — Lv {r['level']} ({r['xp']:,} XP)"
                 for r in rows]
        await self.send_embed(
            channel_id, "📈 Top XP Earners",
            "\n".join(lines) or "No leveling data yet.",
            EmbedColor.LEVELING
        )


async def setup(adapter, db, config):
    return Analytics(adapter, db, config)
