"""
Roles Cog for Logiq (Stoat-only)
Role management and assignment
"""

import logging
from typing import Dict, Any, Optional

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedFactory, EmbedColor
from utils.permissions import is_admin
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class Roles(AdaptedCog):
    """Role management cog (Stoat-only)"""

    def __init__(self, adapter, db: DatabaseManager, config: dict):
        super().__init__(adapter, db, config)
        self.module_config = config.get('modules', {}).get('roles', {})

    @app_command(name="role-assign", description="Assign a role to a user (Admin)")
    async def role_assign(
        self,
        interaction: Dict[str, Any],
        user_id: str,
        role_id: str
    ):
        """Assign role to user (Stoat - Admin only)"""
        channel_id = interaction.get("channel_id")
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        admin_id = interaction.get("user_id")

        if not await is_admin(self.db, guild_id, admin_id):
            await self.send_embed(
                channel_id,
                "Permission Denied",
                "Only admins can assign roles",
                color=EmbedColor.ERROR
            )
            return

        try:
            success = await self.adapter.add_role(guild_id, user_id, role_id)

            if success:
                await self.send_embed(
                    channel_id,
                    "✅ Role Assigned",
                    f"Role <@&{role_id}> assigned to <@{user_id}>",
                    color=EmbedColor.SUCCESS
                )
                logger.info(f"Role {role_id} assigned to {user_id} in {guild_id}")
            else:
                await self.send_embed(
                    channel_id,
                    "Error",
                    "Failed to assign role",
                    color=EmbedColor.ERROR
                )

        except Exception as e:
            logger.error(f"Role assign error: {e}")
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)

    @app_command(name="role-remove", description="Remove a role from a user (Admin)")
    async def role_remove(
        self,
        interaction: Dict[str, Any],
        user_id: str,
        role_id: str
    ):
        """Remove role from user (Stoat - Admin only)"""
        channel_id = interaction.get("channel_id")
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        admin_id = interaction.get("user_id")

        if not await is_admin(self.db, guild_id, admin_id):
            await self.send_embed(
                channel_id,
                "Permission Denied",
                "Only admins can remove roles",
                color=EmbedColor.ERROR
            )
            return

        try:
            success = await self.adapter.remove_role(guild_id, user_id, role_id)

            if success:
                await self.send_embed(
                    channel_id,
                    "✅ Role Removed",
                    f"Role <@&{role_id}> removed from <@{user_id}>",
                    color=EmbedColor.SUCCESS
                )
                logger.info(f"Role {role_id} removed from {user_id} in {guild_id}")
            else:
                await self.send_embed(
                    channel_id,
                    "Error",
                    "Failed to remove role",
                    color=EmbedColor.ERROR
                )

        except Exception as e:
            logger.error(f"Role remove error: {e}")
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)

    @app_command(name="role-list", description="List server roles")
    async def role_list(self, interaction: Dict[str, Any]):
        """List server roles (Stoat)"""
        channel_id = interaction.get("channel_id")
        guild_id = interaction.get("server_id") or interaction.get("guild_id")

        try:
            roles = await self.db.db.roles.find({"guild_id": guild_id}).to_list(length=50)

            description = ""
            for role in roles:
                role_id = role.get("role_id")
                role_name = role.get("name", "Unknown")
                description += f"• **{role_name}** (<@&{role_id}>)\n"

            embed = {
                "title": "📋 Server Roles",
                "description": description or "No roles configured",
                "color": EmbedColor.INFO
            }

            await self.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"Role list error: {e}")
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)


async def setup(adapter, db, config):
    """Setup function for cog loading"""
    return Roles(adapter, db, config)
