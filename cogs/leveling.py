"""
Leveling Cog for Logiq (Stoat-only)
User level and XP system
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from adapters.cog_base import AdaptedCog, app_command, listener
from utils.embeds import EmbedFactory, EmbedColor
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class Leveling(AdaptedCog):
    """Leveling system cog (Stoat-only)"""

    def __init__(self, adapter, db: DatabaseManager, config: dict):
        super().__init__(adapter, db, config)
        self.module_config = config.get('modules', {}).get('leveling', {})
        self.xp_per_message = self.module_config.get('xp_per_message', 10)
        self.xp_cooldown = self.module_config.get('xp_cooldown', 60)

    @listener("message_create")
    async def on_message(self, payload: Dict[str, Any]):
        """Add XP on message (Stoat)"""
        user_id = payload.get("author_id") or payload.get("user_id")
        guild_id = payload.get("server_id") or payload.get("guild_id")
        channel_id = payload.get("channel_id")

        if not user_id or not guild_id or user_id == "bot":
            return

        try:
            user_data = await self.db.get_user(user_id, guild_id)
            if not user_data:
                user_data = await self.db.create_user(user_id, guild_id)

            # Check cooldown
            last_xp = user_data.get("last_xp_time")
            if last_xp:
                from datetime import datetime, timedelta
                last_xp_dt = datetime.fromisoformat(last_xp)
                if (datetime.utcnow() - last_xp_dt).seconds < self.xp_cooldown:
                    return

            # Add XP
            old_level = user_data.get("level", 0)
            new_xp = user_data.get("xp", 0) + self.xp_per_message

            # Calculate level (100 XP per level)
            new_level = int(new_xp / 100)
            level_up = new_level > old_level

            await self.db.update_user(user_id, guild_id, {
                "xp": new_xp,
                "level": new_level,
                "last_xp_time": datetime.utcnow().isoformat()
            })

            # Level up notification
            if level_up:
                embed = EmbedFactory.level_up(user_id, f"User {user_id}", new_level, new_xp)
                await self.send_message(channel_id, embed=embed)
                logger.info(f"User {user_id} leveled up to {new_level}")

        except Exception as e:
            logger.error(f"On message XP error: {e}")

    @app_command(name="rank", description="View your rank")
    async def rank(self, interaction: Dict[str, Any], user_id: Optional[str] = None):
        """View rank card (Stoat format)"""
        channel_id = interaction.get("channel_id")
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        target_id = user_id or interaction.get("user_id")

        try:
            user_data = await self.db.get_user(target_id, guild_id)
            if not user_data:
                await self.send_embed(
                    channel_id,
                    "No Data",
                    f"<@{target_id}> has no rank data yet",
                    color=EmbedColor.INFO
                )
                return

            level = user_data.get("level", 0)
            xp = user_data.get("xp", 0)

            # Get rank (count users with higher XP)
            all_users = await self.db.db.users.find({"guild_id": guild_id}).to_list(length=None)
            rank = sum(1 for u in all_users if u.get("xp", 0) > xp) + 1

            next_level_xp = (level + 1) * 100

            embed = EmbedFactory.rank_card(
                target_id,
                f"User {target_id}",
                level,
                xp,
                rank,
                next_level_xp
            )

            await self.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"Rank command error: {e}")
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)

    @app_command(name="leaderboard", description="View level leaderboard")
    async def leaderboard(self, interaction: Dict[str, Any]):
        """View level leaderboard (Stoat)"""
        channel_id = interaction.get("channel_id")
        guild_id = interaction.get("server_id") or interaction.get("guild_id")

        try:
            top_users = await self.db.get_leaderboard(guild_id, limit=10)

            embed = EmbedFactory.leaderboard(
                "Level Leaderboard",
                top_users,
                field_name="level",
                color=EmbedColor.LEVELING
            )

            await self.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"Leaderboard error: {e}")
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)


async def setup(adapter, db, config):
    """Setup function for cog loading"""
    return Leveling(adapter, db, config)
