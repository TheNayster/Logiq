"""
Utility Cog for Logiq (Stoat-only)
General utility commands
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedFactory, EmbedColor
from utils.converters import TimeConverter
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class Utility(AdaptedCog):
    """Utility commands cog (Stoat-only)"""

    def __init__(self, adapter, db: DatabaseManager, config: dict):
        super().__init__(adapter, db, config)
        self.reminders: Dict[str, list] = {}

    @app_command(name="poll", description="Create a poll (Admin)")
    async def poll(
        self,
        interaction: Dict[str, Any],
        question: str,
        option1: str,
        option2: str,
        option3: Optional[str] = None,
        duration: int = 60
    ):
        """Create a poll"""
        channel_id = interaction.get("channel_id")
        user_id = interaction.get("user_id")
        guild_id = interaction.get("server_id") or interaction.get("guild_id")

        if not await self._check_admin(guild_id, user_id):
            await self.send_embed(
                channel_id,
                "Permission Denied",
                "Only admins can create polls",
                color=EmbedColor.ERROR
            )
            return

        options = [option1, option2]
        if option3:
            options.append(option3)

        poll_data = {
            "guild_id": guild_id,
            "channel_id": channel_id,
            "question": question,
            "options": options,
            "votes": {opt: 0 for opt in options},
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(minutes=duration)).isoformat()
        }

        await self.db.db.polls.insert_one(poll_data)

        options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])

        embed = {
            "title": f"📊 Poll: {question}",
            "description": options_text,
            "color": EmbedColor.INFO
        }

        await self.send_message(channel_id, embed=embed)

    @app_command(name="remind", description="Set a reminder (Admin)")
    async def remind(self, interaction: Dict[str, Any], duration: str, message: str):
        """Set a reminder"""
        channel_id = interaction.get("channel_id")
        user_id = interaction.get("user_id")

        seconds = TimeConverter.parse(duration)
        if not seconds or seconds < 60:
            await self.send_embed(
                channel_id,
                "Invalid Duration",
                "Reminder must be at least 1 minute",
                color=EmbedColor.ERROR
            )
            return

        await self.send_embed(
            channel_id,
            "⏰ Reminder Set",
            f"Reminder set for {duration}",
            color=EmbedColor.SUCCESS
        )

        await asyncio.sleep(seconds)

        embed = {
            "title": "⏰ Reminder",
            "description": f"<@{user_id}> - {message}",
            "color": EmbedColor.INFO
        }

        await self.send_message(channel_id, embed=embed)

    @app_command(name="serverinfo", description="View server information")
    async def serverinfo(self, interaction: Dict[str, Any]):
        """View server info"""
        channel_id = interaction.get("channel_id")
        guild_id = interaction.get("server_id") or interaction.get("guild_id")

        try:
            guild = await self.db.get_guild(guild_id)
            member_count = await self.db.db.members.count_documents({"guild_id": guild_id})

            embed = {
                "title": f"📊 Server Information",
                "description": guild.get("name", "Unknown"),
                "fields": [
                    {"name": "Server ID", "value": guild_id, "inline": True},
                    {"name": "Members", "value": str(member_count), "inline": True},
                    {"name": "Created", "value": guild.get("created_at", "Unknown"), "inline": False},
                ],
                "color": EmbedColor.INFO
            }

            await self.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"Serverinfo error: {e}")
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)

    @app_command(name="userinfo", description="Get user information")
    async def userinfo(self, interaction: Dict[str, Any], user_id: Optional[str] = None):
        """Get user information"""
        channel_id = interaction.get("channel_id")
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        target_id = user_id or interaction.get("user_id")

        try:
            user_data = await self.db.get_user(target_id, guild_id)
            if not user_data:
                await self.send_embed(
                    channel_id,
                    "User Not Found",
                    "This user has no data on this server",
                    color=EmbedColor.ERROR
                )
                return

            embed = {
                "title": f"User Information",
                "description": f"<@{target_id}>",
                "fields": [
                    {"name": "User ID", "value": target_id, "inline": True},
                    {"name": "Level", "value": str(user_data.get("level", 0)), "inline": True},
                    {"name": "XP", "value": str(user_data.get("xp", 0)), "inline": True},
                    {"name": "Balance", "value": str(user_data.get("balance", 0)), "inline": True},
                    {"name": "Joined", "value": user_data.get("created_at", "Unknown"), "inline": False},
                ],
                "color": EmbedColor.INFO
            }

            await self.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"Userinfo error: {e}")
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
    return Utility(adapter, db, config)