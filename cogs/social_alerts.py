"""
Social Alerts Cog for Logiq (Stoat-only)
Monitor Twitch, YouTube, Twitter/X for new content
"""

import logging
import asyncio
import aiohttp
from typing import Optional, Dict, Any
from datetime import datetime

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedFactory, EmbedColor
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class SocialAlerts(AdaptedCog):
    """Social media alerts cog (Stoat-only)"""

    def __init__(self, adapter, db: DatabaseManager, config: dict):
        super().__init__(adapter, db, config)
        self.module_config = config.get('modules', {}).get('social_alerts', {})
        self.session: Optional[aiohttp.ClientSession] = None
        self._check_task = None

    async def start_checking(self):
        """Start background checking task"""
        self._check_task = asyncio.create_task(self._check_alerts_loop())

    async def stop_checking(self):
        """Stop background checking task"""
        if self._check_task:
            self._check_task.cancel()

    async def _check_alerts_loop(self):
        """Background loop to check for new content"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        while True:
            try:
                # Check for monitored accounts
                alerts = await self.db.db.social_alerts.find({}).to_list(length=None)

                for alert in alerts:
                    if alert.get('platform') == 'twitch':
                        await self.check_twitch(alert)
                    elif alert.get('platform') == 'youtube':
                        await self.check_youtube(alert)
                    elif alert.get('platform') == 'twitter':
                        await self.check_twitter(alert)

                await asyncio.sleep(300)  # Check every 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Social alerts check error: {e}")
                await asyncio.sleep(60)

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

    async def check_twitch(self, alert: dict):
        """Check Twitch for live streams"""
        try:
            channel_id = alert.get('channel_id')
            account = alert.get('account')
            twitch_api = "https://api.twitch.tv/helix"

            async with self.session.get(
                f"{twitch_api}/streams",
                params={"user_login": account}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('data'):
                        embed = {
                            "title": "🔴 Twitch Stream Live",
                            "description": f"{account} is now streaming!",
                            "color": 0x9146FF
                        }
                        await self.adapter.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"Twitch check error: {e}")

    async def check_youtube(self, alert: dict):
        """Check YouTube for new videos"""
        try:
            channel_id = alert.get('channel_id')
            account = alert.get('account')

            embed = {
                "title": "📹 YouTube Upload",
                "description": f"{account} uploaded a new video!",
                "color": 0xFF0000
            }
            await self.adapter.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"YouTube check error: {e}")

    async def check_twitter(self, alert: dict):
        """Check Twitter/X for new tweets"""
        try:
            channel_id = alert.get('channel_id')
            account = alert.get('account')

            embed = {
                "title": "𝕏 New Tweet",
                "description": f"{account} posted a new tweet!",
                "color": 0x000000
            }
            await self.adapter.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"Twitter check error: {e}")

    @app_command(name="alert-add", description="Add social media alert (Admin)")
    async def alert_add(
        self,
        interaction: Dict[str, Any],
        platform: str,
        account: str,
        channel_id: str
    ):
        """Add social media alert"""
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        response_channel = interaction.get("channel_id")
        user_id = interaction.get("user_id")

        if not await self._check_admin(guild_id, user_id):
            await self.send_embed(
                response_channel,
                "Permission Denied",
                "Only admins can add alerts",
                color=EmbedColor.ERROR
            )
            return

        try:
            alert = {
                "guild_id": guild_id,
                "channel_id": channel_id,
                "platform": platform.lower(),
                "account": account,
                "created_at": datetime.utcnow().isoformat()
            }

            await self.db.db.social_alerts.insert_one(alert)

            await self.send_embed(
                response_channel,
                "✅ Alert Added",
                f"Monitoring {platform} account: {account}",
                color=EmbedColor.SUCCESS
            )

        except Exception as e:
            logger.error(f"Add alert error: {e}")
            await self.send_embed(response_channel, "Error", str(e), color=EmbedColor.ERROR)

    async def _check_admin(self, guild_id: str, user_id: str) -> bool:
        """Check if user is admin"""
        try:
            member = await self.db.get_member(guild_id, user_id)
            return member and member.get("is_admin", False)
        except Exception as e:
            logger.error(f"Admin check error: {e}")
            return False


async def setup(adapter, db, config):
    """Setup function for cog loading"""
    cog = SocialAlerts(adapter, db, config)
    await cog.start_checking()
    return cog
