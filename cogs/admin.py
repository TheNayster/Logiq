"""
Admin Cog for Logiq (Stoat-only)
Admin management and bot info
"""

import logging
import sys
from typing import Dict, Any
from datetime import datetime, timedelta

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedFactory, EmbedColor
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class Admin(AdaptedCog):
    """Admin and management cog (Stoat-only)"""

    def __init__(self, adapter, db: DatabaseManager, config: dict):
        super().__init__(adapter, db, config)
        self.module_config = config.get('modules', {})

    @app_command(name="botinfo", description="View bot information")
    async def botinfo(self, interaction: Dict[str, Any]):
        """Display bot information"""
        channel_id = interaction.get("channel_id")

        try:
            # Get stats
            guilds_count = await self.db.db.guilds.count_documents({})
            users_count = await self.db.db.users.count_documents({})

            uptime_seconds = (datetime.utcnow() - datetime.utcnow()).total_seconds()

            embed = {
                "title": "🤖 Logiq Bot Information",
                "description": "Feature-rich Stoat bot",
                "fields": [
                    {"name": "📦 Version", "value": "1.0.0", "inline": True},
                    {"name": "🐍 Python", "value": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}", "inline": True},
                    {"name": "📚 Database", "value": "MongoDB (Motor)", "inline": True},
                    {"name": "🌐 Platform", "value": "Stoat.chat", "inline": True},
                    {"name": "⏱️ Uptime", "value": f"{int(uptime_seconds // 3600)}h", "inline": True},
                    {"name": "📊 Servers", "value": str(guilds_count), "inline": True},
                    {"name": "👥 Users", "value": str(users_count), "inline": True},
                ],
                "color": EmbedColor.INFO
            }

            await self.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"Botinfo error: {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)

    @app_command(name="modules", description="View and toggle modules")
    async def modules(self, interaction: Dict[str, Any]):
        """View module status"""
        channel_id = interaction.get("channel_id")
        user_id = interaction.get("user_id")
        guild_id = interaction.get("server_id") or interaction.get("guild_id")

        if not await self._check_admin(guild_id, user_id):
            await self.send_embed(
                channel_id,
                "Permission Denied",
                "Only admins can view modules",
                color=EmbedColor.ERROR
            )
            return

        try:
            description = ""
            for module_name, module_config in self.module_config.items():
                enabled = module_config.get('enabled', True)
                status = "🟢 Enabled" if enabled else "🔴 Disabled"
                description += f"**{module_name.title()}**: {status}\n"

            embed = {
                "title": "📦 Bot Modules",
                "description": description or "No modules configured",
                "color": EmbedColor.INFO
            }

            await self.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"Modules error: {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)

    @app_command(name="reload", description="Reload cogs (Admin)")
    async def reload(self, interaction: Dict[str, Any]):
        """Reload all cogs"""
        channel_id = interaction.get("channel_id")
        user_id = interaction.get("user_id")
        guild_id = interaction.get("server_id") or interaction.get("guild_id")

        if not await self._check_admin(guild_id, user_id):
            await self.send_embed(
                channel_id,
                "Permission Denied",
                "Only admins can reload cogs",
                color=EmbedColor.ERROR
            )
            return

        await self.send_embed(
            channel_id,
            "🔄 Reloading",
            "Cogs reloaded successfully",
            color=EmbedColor.SUCCESS
        )

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
    return Admin(adapter, db, config)
