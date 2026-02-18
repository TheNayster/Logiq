"""
Verification Cog for Logiq (Stoat-only)
User verification system without Discord.py
"""

import logging
from typing import Dict, Any, Optional

from adapters.cog_base import AdaptedCog, app_command, listener
from utils.embeds import EmbedFactory, EmbedColor
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class Verification(AdaptedCog):
    """Verification system cog (Stoat-only)"""

    def __init__(self, adapter, db: DatabaseManager, config: dict):
        super().__init__(adapter, db, config)
        self.module_config = config.get('modules', {}).get('verification', {})

    @app_command(name="setup-verification", description="Setup verification system (Admin)")
    async def setup_verification(
        self,
        interaction: Dict[str, Any],
        role_id: str,
        welcome_channel_id: str,
        method: str = "dm",
        verify_channel_id: Optional[str] = None,
        verification_type: str = "button"
    ):
        """Setup verification system (ADMIN ONLY)"""
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        channel_id = interaction.get("channel_id")
        user_id = interaction.get("user_id")

        # Check admin permission
        if not await self._check_admin(guild_id, user_id):
            await self.send_embed(
                channel_id,
                "Permission Denied",
                "Only admins can setup verification",
                color=EmbedColor.ERROR
            )
            return

        method = method.lower()
        if method not in ['dm', 'channel']:
            await self.send_embed(
                channel_id,
                "Invalid Method",
                "Method must be 'dm' or 'channel'",
                color=EmbedColor.ERROR
            )
            return

        try:
            guild_config = await self.db.get_guild(guild_id)
            if not guild_config:
                guild_config = await self.db.create_guild(guild_id)

            # Update verification settings
            await self.db.update_guild(guild_id, {
                "verified_role": role_id,
                "welcome_channel": welcome_channel_id,
                "verification_method": method,
                "verify_channel": verify_channel_id,
                "verification_type": verification_type
            })

            embed = {
                "title": "✅ Verification Setup Complete",
                "description": (
                    f"**Role:** <@&{role_id}>\n"
                    f"**Welcome Channel:** <#{welcome_channel_id}>\n"
                    f"**Method:** {method}\n"
                    f"**Type:** {verification_type}"
                ),
                "color": EmbedColor.SUCCESS
            }

            await self.send_message(channel_id, embed=embed)
            logger.info(f"Verification setup in {guild_id}")

        except Exception as e:
            logger.error(f"Setup verification error: {e}", exc_info=True)
            await self.send_embed(
                channel_id,
                "Error",
                str(e),
                color=EmbedColor.ERROR
            )

    @app_command(name="send-verification", description="Send verification button in current channel (Admin)")
    async def send_verification(self, interaction: Dict[str, Any]):
        """Manually send verification button"""
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        channel_id = interaction.get("channel_id")
        user_id = interaction.get("user_id")

        if not await self._check_admin(guild_id, user_id):
            await self.send_embed(
                channel_id,
                "Permission Denied",
                "Only admins can send verification",
                color=EmbedColor.ERROR
            )
            return

        guild_config = await self.db.get_guild(guild_id)
        if not guild_config or not guild_config.get('verified_role'):
            await self.send_embed(
                channel_id,
                "Not Configured",
                "Please setup verification first with /setup-verification",
                color=EmbedColor.ERROR
            )
            return

        try:
            embed = EmbedFactory.verification_prompt()
            await self.adapter.send_message(channel_id, embed=embed)

            await self.send_embed(
                channel_id,
                "✅ Sent",
                "Verification button sent to this channel!",
                color=EmbedColor.SUCCESS
            )

            logger.info(f"Verification panel sent in {channel_id}")

        except Exception as e:
            logger.error(f"Send verification error: {e}", exc_info=True)
            await self.send_embed(
                channel_id,
                "Error",
                str(e),
                color=EmbedColor.ERROR
            )

    @listener("member_join")
    async def on_member_join(self, payload: Dict[str, Any]):
        """Handle new member join"""
        guild_id = payload.get("server_id") or payload.get("guild_id")
        user_id = payload.get("user_id")
        member = payload.get("member", {})

        guild_config = await self.db.get_guild(guild_id)
        if not guild_config or not guild_config.get('verified_role'):
            return

        method = guild_config.get('verification_method', 'dm')

        try:
            embed = EmbedFactory.verification_prompt()

            if method == "dm":
                # Send DM to user
                await self.adapter.send_dm(user_id, embed=embed)
            else:
                # Send to verification channel
                verify_channel = guild_config.get('verify_channel')
                if verify_channel:
                    msg = f"<@{user_id}> Please verify yourself!"
                    await self.adapter.send_message(verify_channel, msg, embed=embed)

            logger.info(f"Verification sent to {user_id} in {guild_id}")

        except Exception as e:
            logger.error(f"Member join verification error: {e}")

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
    return Verification(adapter, db, config)
