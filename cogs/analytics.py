"""
Analytics Cog for Logiq (Stoat-only - stub)
Server analytics (disabled for now)
"""

import logging
from typing import Dict, Any

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedColor
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class Analytics(AdaptedCog):
    """Analytics stub (Stoat-only)"""

    def __init__(self, adapter, db: DatabaseManager, config: dict):
        super().__init__(adapter, db, config)

    @app_command(name="stats", description="View server analytics (Admin)")
    async def stats(self, interaction: Dict[str, Any]):
        """View stats"""
        channel_id = interaction.get("channel_id")

        await self.send_embed(
            channel_id,
            "📊 Analytics",
            "Analytics coming soon!",
            color=EmbedColor.INFO
        )


async def setup(adapter, db, config):
    """Setup function for cog loading"""
    return Analytics(adapter, db, config)
