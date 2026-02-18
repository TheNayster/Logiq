"""
Temporary Voice Channels Cog for Logiq (Stoat Adapter)
Stub: Voice channels not yet supported on Stoat.
"""

import logging
from typing import Dict, Any

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedFactory, EmbedColor
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class TempVoice(AdaptedCog):
    """Temporary voice channels cog (Stoat adapter - disabled)"""

    def __init__(self, adapter, db: DatabaseManager, config: dict):
        """Initialize with correct signature (adapter, db, config)"""
        super().__init__(adapter, db, config)
        self.module_config = config.get('modules', {}).get('temp_voice', {})
        self.is_enabled = False  # Disabled for Stoat

    @app_command(name="setup-tempvoice", description="[NOT AVAILABLE] Setup temporary voice")
    async def setup_tempvoice(
        self,
        interaction: Dict[str, Any],
        category_id: str,
        creator_name: str = "➕ Create Channel"
    ):
        """Setup temporary voice - NOT SUPPORTED on Stoat"""
        channel_id = interaction.get("channel_id")
        await self.send_embed(
            channel_id,
            "⚠️ Not Available",
            "Temporary voice channels are not yet supported on Stoat.\n"
            "We're working on implementing voice support for future versions.\n\n"
            "**Status:** 🔄 Planned for Stoat v1.1+",
            color=EmbedColor.WARNING
        )
        logger.warning("Temp voice command called but not supported on Stoat")

    @app_command(name="voice-lock", description="[NOT AVAILABLE] Lock voice channel")
    async def voice_lock(self, interaction: Dict[str, Any]):
        """Lock voice channel - NOT SUPPORTED"""
        channel_id = interaction.get("channel_id")
        await self.send_embed(
            channel_id,
            "⚠️ Not Available",
            "Voice channel management is not yet supported on Stoat.",
            color=EmbedColor.WARNING
        )

    @app_command(name="voice-unlock", description="[NOT AVAILABLE] Unlock voice channel")
    async def voice_unlock(self, interaction: Dict[str, Any]):
        """Unlock voice channel - NOT SUPPORTED"""
        channel_id = interaction.get("channel_id")
        await self.send_embed(
            channel_id,
            "⚠️ Not Available",
            "Voice channel management is not yet supported on Stoat.",
            color=EmbedColor.WARNING
        )

    @app_command(name="voice-rename", description="[NOT AVAILABLE] Rename voice channel")
    async def voice_rename(self, interaction: Dict[str, Any], name: str):
        """Rename voice channel - NOT SUPPORTED"""
        channel_id = interaction.get("channel_id")
        await self.send_embed(
            channel_id,
            "⚠️ Not Available",
            "Voice channel management is not yet supported on Stoat.",
            color=EmbedColor.WARNING
        )

    @app_command(name="voice-limit", description="[NOT AVAILABLE] Set voice channel limit")
    async def voice_limit(self, interaction: Dict[str, Any], limit: int):
        """Set voice limit - NOT SUPPORTED"""
        channel_id = interaction.get("channel_id")
        await self.send_embed(
            channel_id,
            "⚠️ Not Available",
            "Voice channel management is not yet supported on Stoat.",
            color=EmbedColor.WARNING
        )

    @app_command(name="voice-claim", description="[NOT AVAILABLE] Claim voice channel")
    async def voice_claim(self, interaction: Dict[str, Any]):
        """Claim voice channel - NOT SUPPORTED"""
        channel_id = interaction.get("channel_id")
        await self.send_embed(
            channel_id,
            "⚠️ Not Available",
            "Voice channel management is not yet supported on Stoat.",
            color=EmbedColor.WARNING
        )


# CRITICAL: Correct setup signature (adapter, db, config)
async def setup(adapter, db, config):
    """Setup function for cog loading"""
    return TempVoice(adapter, db, config)
