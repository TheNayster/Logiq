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
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import aiohttp

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
        self._twitch_token: Optional[str] = None
        self._twitch_token_expiry: float = 0.0

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

    # ── Core polling ──────────────────────────────────────────────────────────

    async def _process_alerts(self):
        """Fetch all alerts from Supabase and dispatch to platform-specific checkers."""
        sb  = await supa.get_client()
        res = await sb.table("social_alerts").select("*").eq("enabled", True).execute()
        alerts: List[Dict] = (res.data if res else None) or []

        if not alerts:
            return

        twitch_alerts  = [a for a in alerts if a.get("platform") == "twitch"]
        youtube_alerts = [a for a in alerts if a.get("platform") == "youtube"]
        twitter_alerts = [a for a in alerts if a.get("platform") == "twitter"]

        for checker, bucket in (
            (self._check_twitch,  twitch_alerts),
            (self._check_youtube, youtube_alerts),
            (self._check_twitter, twitter_alerts),
        ):
            if bucket:
                try:
                    await checker(bucket)
                except Exception as e:
                    platform = bucket[0].get("platform", "unknown")
                    logger.error(f"[social_alerts] {platform} check error: {e}", exc_info=True)

    # ── Twitch ────────────────────────────────────────────────────────────────

    async def _get_twitch_token(self) -> Optional[str]:
        """Return a cached app-access token, refreshing if expired."""
        client_id     = os.getenv("TWITCH_CLIENT_ID")
        client_secret = os.getenv("TWITCH_CLIENT_SECRET")
        if not client_id or not client_secret:
            return None

        if self._twitch_token and time.monotonic() < self._twitch_token_expiry:
            return self._twitch_token

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://id.twitch.tv/oauth2/token",
                params={
                    "client_id":     client_id,
                    "client_secret": client_secret,
                    "grant_type":    "client_credentials",
                },
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"[twitch] token request failed: {resp.status}")
                    return None
                data = await resp.json()

        self._twitch_token        = data.get("access_token")
        expires_in                = data.get("expires_in", 3600)
        self._twitch_token_expiry = time.monotonic() + expires_in - 60
        return self._twitch_token

    async def _check_twitch(self, alerts: List[Dict]):
        """Batch-check live streams and notify channels of new stream starts."""
        token = await self._get_twitch_token()
        if not token:
            logger.debug("[twitch] skipped — TWITCH_CLIENT_ID/SECRET not configured")
            return

        client_id = os.getenv("TWITCH_CLIENT_ID")
        accounts  = [a["account"] for a in alerts]

        # Build query string: user_login=a&user_login=b...
        params = "&".join(f"user_login={acc}" for acc in accounts)

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.twitch.tv/helix/streams?{params}",
                headers={
                    "Client-Id":     client_id,
                    "Authorization": f"Bearer {token}",
                },
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"[twitch] streams request failed: {resp.status}")
                    return
                data = await resp.json()

        live_by_login = {s["user_login"].lower(): s for s in data.get("data", [])}

        sb = await supa.get_client()
        for alert in alerts:
            account    = alert["account"].lower()
            stream     = live_by_login.get(account)
            if not stream:
                continue

            stream_id = str(stream["id"])
            if alert.get("last_post_id") == stream_id:
                continue  # already notified for this stream

            # Notify
            icon = PLATFORM_ICONS["twitch"]
            color = PLATFORM_COLORS["twitch"]
            desc = (
                f"**{stream.get('user_name', account)}** is live on Twitch!\n"
                f"**{stream.get('title', '')}**\n"
                f"Playing: {stream.get('game_name', 'Unknown')}\n"
                f"https://twitch.tv/{account}"
            )
            await self.send_embed(alert["channel_id"], f"{icon} Now Live", desc, color)

            # Update last_post_id
            await (sb.table("social_alerts")
                     .update({"last_post_id": stream_id})
                     .eq("id", alert["id"])
                     .execute())
            logger.info(f"[twitch] notified: {account} stream {stream_id}")

    # ── YouTube ───────────────────────────────────────────────────────────────

    async def _check_youtube(self, alerts: List[Dict]):
        """Check for new YouTube uploads and notify."""
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            logger.debug("[youtube] skipped — YOUTUBE_API_KEY not configured")
            return

        sb = await supa.get_client()
        async with aiohttp.ClientSession() as session:
            for alert in alerts:
                channel_id_yt = alert["account"]
                try:
                    async with session.get(
                        "https://www.googleapis.com/youtube/v3/search",
                        params={
                            "part":       "snippet",
                            "channelId":  channel_id_yt,
                            "type":       "video",
                            "order":      "date",
                            "maxResults": 1,
                            "key":        api_key,
                        },
                    ) as resp:
                        if resp.status != 200:
                            logger.warning(f"[youtube] search failed for {channel_id_yt}: {resp.status}")
                            continue
                        data = await resp.json()

                    items = data.get("items", [])
                    if not items:
                        continue

                    video   = items[0]
                    vid_id  = video["id"].get("videoId")
                    snippet = video.get("snippet", {})

                    if not vid_id or alert.get("last_post_id") == vid_id:
                        continue  # already notified

                    # Notify
                    icon  = PLATFORM_ICONS["youtube"]
                    color = PLATFORM_COLORS["youtube"]
                    title = snippet.get("title", "New Video")
                    desc  = (
                        f"**{snippet.get('channelTitle', channel_id_yt)}** uploaded a new video!\n"
                        f"**{title}**\n"
                        f"https://youtu.be/{vid_id}"
                    )
                    await self.send_embed(alert["channel_id"], f"{icon} New Video", desc, color)

                    await (sb.table("social_alerts")
                             .update({"last_post_id": vid_id})
                             .eq("id", alert["id"])
                             .execute())
                    logger.info(f"[youtube] notified: {channel_id_yt} video {vid_id}")

                except Exception as e:
                    logger.error(f"[youtube] error for {channel_id_yt}: {e}", exc_info=True)

    # ── Twitter / X ───────────────────────────────────────────────────────────

    async def _check_twitter(self, alerts: List[Dict]):
        """Check for new tweets and notify."""
        bearer = os.getenv("TWITTER_BEARER_TOKEN")
        if not bearer:
            logger.debug("[twitter] skipped — TWITTER_BEARER_TOKEN not configured")
            return

        sb = await supa.get_client()
        async with aiohttp.ClientSession() as session:
            for alert in alerts:
                account = alert["account"]
                try:
                    params: Dict[str, Any] = {
                        "query":       f"from:{account} -is:retweet",
                        "max_results": 5,
                        "tweet.fields": "created_at,text",
                    }
                    if alert.get("last_post_id"):
                        params["since_id"] = alert["last_post_id"]

                    async with session.get(
                        "https://api.twitter.com/2/tweets/search/recent",
                        params=params,
                        headers={"Authorization": f"Bearer {bearer}"},
                    ) as resp:
                        if resp.status != 200:
                            logger.warning(f"[twitter] search failed for {account}: {resp.status}")
                            continue
                        data = await resp.json()

                    tweets = data.get("data", [])
                    if not tweets:
                        continue

                    # Newest tweet is first in the list
                    latest = tweets[0]
                    tweet_id   = latest["id"]
                    tweet_text = latest.get("text", "")

                    # Notify
                    icon  = PLATFORM_ICONS["twitter"]
                    color = PLATFORM_COLORS["twitter"]
                    desc  = (
                        f"**@{account}** posted:\n"
                        f"{tweet_text[:400]}\n"
                        f"https://x.com/{account}/status/{tweet_id}"
                    )
                    await self.send_embed(alert["channel_id"], f"{icon} New Post", desc, color)

                    await (sb.table("social_alerts")
                             .update({"last_post_id": tweet_id})
                             .eq("id", alert["id"])
                             .execute())
                    logger.info(f"[twitter] notified: @{account} tweet {tweet_id}")

                except Exception as e:
                    logger.error(f"[twitter] error for {account}: {e}", exc_info=True)

    # ── Admin checks ──────────────────────────────────────────────────────────

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
            await (sb.table("social_alerts")
                     .upsert({
                         "server_id":  server_id,
                         "channel_id": channel_id_arg,
                         "platform":   platform,
                         "account":    account,
                         "created_by": user_id,
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
            rows = (res.data if res else None) or []

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
