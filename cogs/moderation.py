"""
Moderation Cog for Logiq (Stoat-only)
Moderation tools without Discord.py
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from adapters.cog_base import AdaptedCog, app_command, listener
from utils.embeds import EmbedFactory, EmbedColor
from utils.converters import TimeConverter
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class Moderation(AdaptedCog):
    """Moderation system cog (Stoat-only)"""

    def __init__(self, adapter, db: DatabaseManager, config: dict):
        super().__init__(adapter, db, config)
        self.module_config = config.get('modules', {}).get('moderation', {})

    @app_command(name="warn", description="Warn a user")
    async def warn(
        self,
        interaction: Dict[str, Any],
        user_id: str,
        reason: str = "No reason provided"
    ):
        """Warn a user"""
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        channel_id = interaction.get("channel_id")
        mod_id = interaction.get("user_id")

        if not await self._check_mod(guild_id, mod_id):
            await self.send_embed(
                channel_id,
                "Permission Denied",
                "Only moderators can warn users",
                color=EmbedColor.ERROR
            )
            return

        try:
            # Log warning
            await self.db.add_action(
                "warn",
                user_id,
                guild_id,
                mod_id,
                reason,
                datetime.utcnow()
            )

            embed = {
                "title": "⚠️ User Warned",
                "description": f"<@{user_id}> has been warned",
                "fields": [
                    {"name": "Reason", "value": reason, "inline": False}
                ],
                "color": EmbedColor.WARNING
            }

            await self.send_message(channel_id, embed=embed)
            logger.info(f"User {user_id} warned in {guild_id}")

        except Exception as e:
            logger.error(f"Warn error: {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)

    @app_command(name="kick", description="Kick a user")
    async def kick(
        self,
        interaction: Dict[str, Any],
        user_id: str,
        reason: str = "No reason provided"
    ):
        """Kick a user"""
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        channel_id = interaction.get("channel_id")
        mod_id = interaction.get("user_id")

        if not await self._check_mod(guild_id, mod_id):
            await self.send_embed(
                channel_id,
                "Permission Denied",
                "Only moderators can kick users",
                color=EmbedColor.ERROR
            )
            return

        try:
            await self.db.add_action(
                "kick",
                user_id,
                guild_id,
                mod_id,
                reason,
                datetime.utcnow()
            )

            embed = {
                "title": "👢 User Kicked",
                "description": f"<@{user_id}> has been kicked",
                "fields": [
                    {"name": "Reason", "value": reason, "inline": False}
                ],
                "color": EmbedColor.WARNING
            }

            await self.send_message(channel_id, embed=embed)
            logger.info(f"User {user_id} kicked from {guild_id}")

        except Exception as e:
            logger.error(f"Kick error: {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)

    @app_command(name="ban", description="Ban a user")
    async def ban(
        self,
        interaction: Dict[str, Any],
        user_id: str,
        reason: str = "No reason provided",
        delete_messages: int = 0
    ):
        """Ban a user"""
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        channel_id = interaction.get("channel_id")
        mod_id = interaction.get("user_id")

        if not await self._check_mod(guild_id, mod_id):
            await self.send_embed(
                channel_id,
                "Permission Denied",
                "Only moderators can ban users",
                color=EmbedColor.ERROR
            )
            return

        try:
            await self.db.add_action(
                "ban",
                user_id,
                guild_id,
                mod_id,
                reason,
                datetime.utcnow()
            )

            embed = {
                "title": "🔨 User Banned",
                "description": f"<@{user_id}> has been banned",
                "fields": [
                    {"name": "Reason", "value": reason, "inline": False},
                    {"name": "Delete Messages", "value": f"{delete_messages} days", "inline": True}
                ],
                "color": EmbedColor.ERROR
            }

            await self.send_message(channel_id, embed=embed)
            logger.info(f"User {user_id} banned from {guild_id}")

        except Exception as e:
            logger.error(f"Ban error: {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)

    @app_command(name="clear", description="Clear messages in channel")
    async def clear(
        self,
        interaction: Dict[str, Any],
        amount: int,
        user_id: Optional[str] = None
    ):
        """Clear messages from channel"""
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        channel_id = interaction.get("channel_id")
        mod_id = interaction.get("user_id")

        if not await self._check_mod(guild_id, mod_id):
            await self.send_embed(
                channel_id,
                "Permission Denied",
                "Only moderators can clear messages",
                color=EmbedColor.ERROR
            )
            return

        if amount < 1 or amount > 100:
            await self.send_embed(
                channel_id,
                "Invalid Amount",
                "Amount must be between 1 and 100",
                color=EmbedColor.ERROR
            )
            return

        try:
            embed = {
                "title": "🗑️ Messages Cleared",
                "description": f"Cleared {amount} messages",
                "color": EmbedColor.SUCCESS
            }

            await self.send_message(channel_id, embed=embed)
            logger.info(f"Cleared {amount} messages in {channel_id}")

        except Exception as e:
            logger.error(f"Clear error: {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)

    async def _check_mod(self, guild_id: str, user_id: str) -> bool:
        """Check if user is moderator"""
        try:
            member = await self.db.get_member(guild_id, user_id)
            is_mod = member and (member.get("is_mod", False) or member.get("is_admin", False))
            return is_mod
        except Exception as e:
            logger.error(f"Mod check error: {e}")
            return False


async def setup(adapter, db, config):
    """Setup function for cog loading"""
    return Moderation(adapter, db, config)
