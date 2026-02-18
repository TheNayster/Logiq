"""
Economy Cog for Logiq (Stoat-only)
Virtual currency system with shop and gambling
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedFactory, EmbedColor
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class Economy(AdaptedCog):
    """Economy system cog (Stoat-only)"""

    def __init__(self, adapter, db: DatabaseManager, config: dict):
        super().__init__(adapter, db, config)
        self.module_config = config.get('modules', {}).get('economy', {})
        self.currency_symbol = self.module_config.get('currency_symbol', '💎')
        self.currency_name = self.module_config.get('currency_name', 'Coins')

    @app_command(name="daily", description="Claim your daily reward")
    async def daily(self, interaction: Dict[str, Any]):
        """Claim daily reward"""
        channel_id = interaction.get("channel_id")
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        user_id = interaction.get("user_id")

        try:
            user_data = await self.db.get_user(user_id, guild_id)
            if not user_data:
                user_data = await self.db.create_user(user_id, guild_id)

            last_daily = user_data.get('last_daily')
            now = datetime.utcnow()

            if last_daily:
                last_daily_dt = datetime.fromisoformat(last_daily)
                if (now - last_daily_dt).days < 1:
                    await self.send_embed(
                        channel_id,
                        "Already Claimed",
                        "You already claimed your daily reward. Try again tomorrow!",
                        color=EmbedColor.ERROR
                    )
                    return

            reward = self.module_config.get('daily_reward', 100)
            await self.db.add_balance(user_id, guild_id, reward)
            await self.db.update_user(user_id, guild_id, {'last_daily': now.isoformat()})

            embed = {
                "title": "💰 Daily Reward",
                "description": f"You received {self.currency_symbol} {reward}!",
                "color": EmbedColor.SUCCESS
            }

            await self.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"Daily error: {e}")
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)

    @app_command(name="balance", description="Check your balance")
    async def balance(self, interaction: Dict[str, Any], user_id: Optional[str] = None):
        """Check balance"""
        channel_id = interaction.get("channel_id")
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        target_id = user_id or interaction.get("user_id")

        try:
            user_data = await self.db.get_user(target_id, guild_id)
            if not user_data:
                user_data = await self.db.create_user(target_id, guild_id)

            balance = user_data.get('balance', 0)

            embed = {
                "title": "💰 Balance",
                "description": f"<@{target_id}> has {self.currency_symbol} {balance}",
                "color": EmbedColor.SUCCESS
            }

            await self.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"Balance error: {e}")
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)

    @app_command(name="give", description="Give currency to another user (Admin)")
    async def give(self, interaction: Dict[str, Any], user_id: str, amount: int):
        """Give currency to user"""
        channel_id = interaction.get("channel_id")
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        admin_id = interaction.get("user_id")

        if not await self._check_admin(guild_id, admin_id):
            await self.send_embed(
                channel_id,
                "Permission Denied",
                "Only admins can give currency",
                color=EmbedColor.ERROR
            )
            return

        try:
            target_data = await self.db.get_user(user_id, guild_id)
            if not target_data:
                target_data = await self.db.create_user(user_id, guild_id)

            await self.db.add_balance(user_id, guild_id, amount)

            embed = {
                "title": "🎁 Currency Given",
                "description": f"Gave <@{user_id}> {self.currency_symbol} {amount}",
                "color": EmbedColor.SUCCESS
            }

            await self.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"Give error: {e}")
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)

    @app_command(name="leaderboard", description="View economy leaderboard")
    async def leaderboard(self, interaction: Dict[str, Any]):
        """View leaderboard"""
        channel_id = interaction.get("channel_id")
        guild_id = interaction.get("server_id") or interaction.get("guild_id")

        try:
            top_users = await self.db.get_leaderboard(guild_id, limit=10)

            description = ""
            for i, user in enumerate(top_users, 1):
                balance = user.get("balance", 0)
                description += f"{i}. <@{user.get('user_id')}> - {self.currency_symbol} {balance}\n"

            embed = {
                "title": "💎 Economy Leaderboard",
                "description": description or "No data yet",
                "color": 0x2ECC71
            }

            await self.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"Leaderboard error: {e}")
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)

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
    return Economy(adapter, db, config)
