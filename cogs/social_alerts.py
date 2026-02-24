"""
Social Alerts Cog — StoatMod
Twitch / YouTube / Twitter feed subscriptions stored in Supabase.

Commands (Admin only):
  !alert-add <platform> <account> <channel_id>  — Subscribe to an account
  !alert-remove <platform> <account>             — Unsubscribe
  !alert-list                                    — List all alerts for this server
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedFactory, EmbedColor
import database.supabase as supa

logger = logging.getLogger(__name__)

PLATFORM_COLORS = {
    "twitch":  0x9146FF,
    "youtube": 0xFF0000,
    "twitter": 0x000000,
}
PLATFORM_ICONS = {
    "twitch":  "🟣",
    "youtube": "🔴",
    "twitter": "𝕏",
}


class SocialAlerts(AdaptedCog):
    """Social media alerts — Stoat-only, Supabase-backed"""

    def __init__(self, adapter, db, config: dict):
        super().__init__(adapter, db, config)
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        self._task = asyncio.create_task(self._check_loop())

    async def _check_loop(self):
        """Poll Supabase every 5 minutes for alerts to fire."""
        while True:
            await asyncio.sleep(300)
            try:
                await self._process_alerts()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[social_alerts] loop error: {e}", exc_info=True)

    async def _process_alerts(self):
        """Stub: real platform API calls would go here."""
        sb  = await supa.get_client()
        res = await sb.table("social_alerts").select("*").execute()
        for alert in (res.data or []):
            platform = alert.get("platform", "")
            # TODO: integrate real Twitch/YouTube/Twitter API checks per alert
            logger.debug(f"[social_alerts] would check {platform}:{alert.get('account')}")

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

    # ── alert-add ─────────────────────────────────────────────────────────────

    @app_command(
        name="alert-add",
        description="Subscribe to a social media account (Admin)",
        usage="!alert-add <platform> <account> <channel_id>  "
              "e.g. !alert-add twitch shroud 01KHXXXXXXXX  (platforms: twitch, youtube, twitter)"
    )
    async def alert_add(self, interaction: Dict[str, Any],
                         platform: str, account: str, channel_id_arg: str):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        user_id    = interaction["user_id"]

        if not await self._is_admin(server_id, user_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                          "Only **Admins** can add alerts.", EmbedColor.ERROR)

        platform = platform.lower()
        if platform not in ("twitch", "youtube", "twitter"):
            return await self.send_embed(
                channel_id, "Invalid Platform",
                "Supported platforms: `twitch`, `youtube`, `twitter`", EmbedColor.ERROR
            )

        try:
            await supa.on_analytics_event(server_id, user_id, "alert_add",
                                           {"platform": platform, "account": account})

            sb = await supa.get_client()
            # Upsert so re-adding the same alert is idempotent
            await (sb.table("social_alerts")
                     .upsert({
                         "server_id":   server_id,
                         "channel_id":  channel_id_arg,
                         "platform":    platform,
                         "account":     account,
                         "added_by":    user_id,
                     }, on_conflict="server_id,platform,account")
                     .execute())

            icon  = PLATFORM_ICONS.get(platform, "📡")
            color = PLATFORM_COLORS.get(platform, EmbedColor.INFO)
            await self.send_embed(
                channel_id, f"{icon} Alert Added",
                f"Now monitoring **{platform}** account `{account}`.\n"
                f"Posts will go to <#{channel_id_arg}>.",
                color
            )
            logger.info(f"[alert-add] {platform}:{account} → {channel_id_arg} in {server_id}")

        except Exception as e:
            logger.error(f"[alert-add] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── alert-remove ──────────────────────────────────────────────────────────

    @app_command(name="alert-remove", description="Remove a social media alert (Admin)",
                 usage="!alert-remove <platform> <account>")
    async def alert_remove(self, interaction: Dict[str, Any], platform: str, account: str):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        user_id    = interaction["user_id"]

        if not await self._is_admin(server_id, user_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                          "Only **Admins** can remove alerts.", EmbedColor.ERROR)
        try:
            sb = await supa.get_client()
            await (sb.table("social_alerts")
                     .delete()
                     .eq("server_id", server_id)
                     .eq("platform",  platform.lower())
                     .eq("account",   account)
                     .execute())
            await self.send_embed(channel_id, "✅ Alert Removed",
                                   f"Stopped monitoring `{platform}:{account}`.",
                                   EmbedColor.SUCCESS)
        except Exception as e:
            logger.error(f"[alert-remove] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)

    # ── alert-list ────────────────────────────────────────────────────────────

    @app_command(name="alert-list", description="List all social alerts for this server")
    async def alert_list(self, interaction: Dict[str, Any]):
        channel_id = interaction["channel_id"]
        server_id  = interaction.get("server_id") or interaction.get("guild_id")
        user_id    = interaction["user_id"]

        if not await self._is_admin(server_id, user_id):
            return await self.send_embed(channel_id, "Permission Denied",
                                          "Only **Admins** can view alerts.", EmbedColor.ERROR)
        try:
            sb  = await supa.get_client()
            res = await (sb.table("social_alerts")
                           .select("platform,account,channel_id")
                           .eq("server_id", server_id)
                           .order("platform")
                           .execute())
            rows = res.data or []

            if not rows:
                return await self.send_embed(channel_id, "📡 Social Alerts",
                                              "No alerts configured.\n"
                                              "Use `!alert-add` to subscribe.", EmbedColor.INFO)

            lines = [
                f"{PLATFORM_ICONS.get(r['platform'],'📡')} **{r['platform']}** "
                f"`{r['account']}` → <#{r['channel_id']}>"
                for r in rows
            ]
            await self.send_embed(channel_id, "📡 Social Alerts",
                                   "\n".join(lines), EmbedColor.INFO)

        except Exception as e:
            logger.error(f"[alert-list] {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), EmbedColor.ERROR)


async def setup(adapter, db, config):
    cog = SocialAlerts(adapter, db, config)
    await cog.start()
    return cog
