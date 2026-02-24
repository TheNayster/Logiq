"""
Giveaways Cog — StoatMod
Giveaway system backed by Supabase.

Commands:
  !giveaway <prize> <duration> [winners]  — Start a giveaway (Admin)
  !enter                                   — Enter active giveaway in channel
  !end-giveaway <giveaway_id>             — End early (Admin)
  !reroll <giveaway_id>                   — Pick new winner (Admin)
"""

import asyncio
import logging
import os
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedFactory, EmbedColor
from utils.converters import TimeConverter
import database.supabase as supa

logger = logging.getLogger(__name__)


class Giveaways(AdaptedCog):
    """Giveaway system — Stoat-only, Supabase-backed"""

    def __init__(self, adapter, db, config: dict):
        super().__init__(adapter, db, config)
        self.module_config = config.get("modules", {}).get("giveaways", {})
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        self._task = asyncio.create_task(self._expiry_loop())

    # ── background expiry loop ────────────────────────────────────────────────

    async def _expiry_loop(self):
        while True:
            await asyncio.sleep(30)
            try:
                await self._check_expired()
            except Exception as e:
                logger.error(f"[giveaways] expiry loop error: {e}", exc_info=True)

    async def _check_expired(self):
        now = datetime.now(timezone.utc).isoformat()
        sb  = await supa.get_client()
        res = await (sb.table("giveaways")
                       .select("*")
                       .eq("status", "active")
                       .lte("ends_at", now)
                       .execute())
        for row in (res.data or []):
            await self._conclude(row)

    # ── conclude ──────────────────────────────────────────────────────────────

    async def _conclude(self, giveaway: dict):
        gw_id      = giveaway["id"]
        channel_id = giveaway.get("channel_id")
        prize      = giveaway.get("prize", "Unknown Prize")
        count      = giveaway.get("winners_count", 1)

        # Idempotent guard — mark ended first
        sb  = await supa.get_client()
        res = await (sb.table("giveaways")
                       .update({"status": "ended"})
                       .eq("id",     gw_id)
                       .eq("status", "active")
                       .execute())
        if not res.data:
            return  # Already concluded

        # Pull entries
        entries_res = await (sb.table("giveaway_entries")
                               .select("user_id")
                               .eq("giveaway_id", gw_id)
                               .execute())
        entries = [r["user_id"] for r in (entries_res.data or [])]

        if not entries:
            if channel_id:
                await self.adapter.send_message(
                    channel_id,
                    embed=EmbedFactory.create(
                        title="🎉 Giveaway Ended — No Winner",
                        description=f"**Prize:** {prize}\n\nNo one entered.",
                        color=EmbedColor.WARNING
                    )
                )
            await supa.on_giveaway_end(gw_id, [])
            return

        winners = random.sample(entries, min(count, len(entries)))
        await supa.on_giveaway_end(gw_id, winners)

        winners_str = " ".join(f"<@{w}>" for w in winners)
        if channel_id:
            await self.adapter.send_message(
                channel_id,
                embed=EmbedFactory.create(
                    title="🎉 Giveaway Ended!",
                    description=f"**Prize:** {prize}\n\n🏆 **Winner(s):** {winners_str}",
                    color=EmbedColor.SUCCESS,
                    footer=f"Giveaway ID: {str(gw_id)[:8]}"
                )
            )
        logger.info(f"[giveaways] {gw_id} ended — winners: {winners}")

    # ── helpers ────────────────────────────────────────────────────────────────

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

    # ── giveaway (start) ──────────────────────────────────────────────────────

    @app_command(
        name="giveaway",
        description="Start a giveaway (Admin)",
        usage="!giveaway <prize> <duration> [winners]  e.g. !giveaway Nitro 1h 3"
    )
    async def start_giveaway(self, interaction: Dict[str, Any],
                              prize: str, duration: str, winners: int = 1):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        user_id    = interaction["user_id"]

        if not await self._is_admin(server_id, user_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                          "Only **Admins** can start giveaways.", EmbedColor.ERROR)
        if not 1 <= winners <= 20:
            return await self.send_embed(channel_id, "Invalid",
                                          "Winners must be between **1** and **20**.", EmbedColor.ERROR)

        secs = TimeConverter.parse(duration)
        if not secs or secs < 60:
            return await self.send_embed(channel_id, "Invalid Duration",
                                          "Minimum duration is **1 minute**.\n"
                                          "Format: `30s`, `5m`, `1h`, `2d`", EmbedColor.ERROR)

        ends_at = (datetime.now(timezone.utc) + timedelta(seconds=secs)).isoformat()

        try:
            sb  = await supa.get_client()
            res = await (sb.table("giveaways")
                           .insert({
                               "server_id":     server_id,
                               "channel_id":    channel_id,
                               "host_id":       user_id,
                               "prize":         prize,
                               "winners_count": winners,
                               "ends_at":       ends_at,
                               "status":        "active",
                           })
                           .execute())
            gw_id = res.data[0]["id"] if res.data else "?"

            embed = EmbedFactory.create(
                title="🎉 GIVEAWAY STARTED",
                description=(
                    f"**Prize:** {prize}\n"
                    f"**Winners:** {winners}\n"
                    f"**Ends in:** {duration}\n\n"
                    f"Type `!enter` in this channel to join!"
                ),
                color=0x2ECC71,
                fields=[
                    {"name": "Hosted by", "value": f"<@{user_id}>",          "inline": True},
                    {"name": "Giveaway ID", "value": f"`{str(gw_id)[:8]}`",  "inline": True},
                ],
                footer="Good luck!"
            )
            await self.send_message(channel_id, embed=embed)
            logger.info(f"[giveaways] {gw_id} started by {user_id}")

        except Exception as e:
            logger.error(f"[giveaway] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── enter ─────────────────────────────────────────────────────────────────

    @app_command(name="enter", description="Enter the active giveaway in this channel")
    async def enter(self, interaction: Dict[str, Any]):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        user_id    = interaction["user_id"]

        try:
            sb  = await supa.get_client()
            gw  = await (sb.table("giveaways")
                           .select("id,prize,ends_at")
                           .eq("server_id",  server_id)
                           .eq("channel_id", channel_id)
                           .eq("status",     "active")
                           .limit(1)
                           .maybe_single()
                           .execute())

            if not gw.data:
                return await self.send_embed(channel_id, "No Active Giveaway",
                                              "There's no active giveaway in this channel.",
                                              EmbedColor.ERROR)

            gw_id = gw.data["id"]
            await supa.on_giveaway_enter(gw_id, user_id)

            # Current entry count
            cnt = await (sb.table("giveaway_entries")
                           .select("id", count="exact")
                           .eq("giveaway_id", gw_id)
                           .execute())
            total = cnt.count or 1

            await self.send_embed(
                channel_id, "✅ Entered!",
                f"You're in the giveaway for **{gw.data['prize']}**!\n"
                f"**{total}** participant(s) so far.",
                EmbedColor.SUCCESS
            )

        except Exception as e:
            # Unique constraint hit = already entered
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                return await self.send_embed(channel_id, "Already Entered",
                                              "You're already in this giveaway!",
                                              EmbedColor.WARNING)
            logger.error(f"[enter] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── end-giveaway (early) ──────────────────────────────────────────────────

    @app_command(name="end-giveaway", description="End a giveaway early (Admin)",
                 usage="!end-giveaway <giveaway_id>  — first 8 chars of the ID is enough")
    async def end_giveaway(self, interaction: Dict[str, Any], giveaway_id: str):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        user_id    = interaction["user_id"]

        if not await self._is_admin(server_id, user_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                          "Only **Admins** can end giveaways.", EmbedColor.ERROR)
        try:
            sb  = await supa.get_client()
            res = await (sb.table("giveaways")
                           .select("*")
                           .eq("server_id", server_id)
                           .ilike("id", f"{giveaway_id}%")
                           .eq("status", "active")
                           .limit(1)
                           .execute())

            if not res.data:
                return await self.send_embed(channel_id, "Not Found",
                                              f"No active giveaway matching `{giveaway_id}`.",
                                              EmbedColor.ERROR)

            await self._conclude(res.data[0])

        except Exception as e:
            logger.error(f"[end-giveaway] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── reroll ────────────────────────────────────────────────────────────────

    @app_command(name="reroll", description="Pick a new winner for an ended giveaway (Admin)",
                 usage="!reroll <giveaway_id>")
    async def reroll(self, interaction: Dict[str, Any], giveaway_id: str):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        user_id    = interaction["user_id"]

        if not await self._is_admin(server_id, user_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                          "Only **Admins** can reroll.", EmbedColor.ERROR)
        try:
            sb  = await supa.get_client()
            gw  = await (sb.table("giveaways")
                           .select("id,prize,winners_count")
                           .eq("server_id", server_id)
                           .ilike("id", f"{giveaway_id}%")
                           .limit(1)
                           .maybe_single()
                           .execute())

            if not gw.data:
                return await self.send_embed(channel_id, "Not Found",
                                              f"No giveaway matching `{giveaway_id}`.",
                                              EmbedColor.ERROR)

            gw_id   = gw.data["id"]
            entries = await (sb.table("giveaway_entries")
                               .select("user_id")
                               .eq("giveaway_id", gw_id)
                               .execute())
            pool = [r["user_id"] for r in (entries.data or [])]
            if not pool:
                return await self.send_embed(channel_id, "No Entries",
                                              "No one entered this giveaway.", EmbedColor.WARNING)

            count   = gw.data.get("winners_count", 1)
            winners = random.sample(pool, min(count, len(pool)))
            await supa.on_giveaway_end(gw_id, winners)

            winners_str = " ".join(f"<@{w}>" for w in winners)
            await self.send_embed(
                channel_id, "🎲 Rerolled!",
                f"New winner(s) for **{gw.data['prize']}**: {winners_str}",
                EmbedColor.SUCCESS
            )

        except Exception as e:
            logger.error(f"[reroll] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)


async def setup(adapter, db, config):
    cog = Giveaways(adapter, db, config)
    await cog.start()
    return cog
