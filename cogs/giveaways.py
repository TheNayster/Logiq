"""
Giveaways Cog for Logiq (Stoat-only)
Giveaway system with text-based entry
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedFactory, EmbedColor
from utils.converters import TimeConverter
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class Giveaways(AdaptedCog):
    """Giveaway system cog (Stoat-only, text-based entry)"""

    def __init__(self, adapter, db: DatabaseManager, config: dict):
        super().__init__(adapter, db, config)
        self.module_config = config.get('modules', {}).get('giveaways', {})
        self.active_giveaways: Dict[str, list] = {}  # giveaway_id: [user_ids]

    @app_command(name="giveaway", description="Start a giveaway (Admin)")
    async def start_giveaway(
        self,
        interaction: Dict[str, Any],
        prize: str,
        duration: str,
        winners: int = 1
    ):
        """Start a giveaway"""
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        channel_id = interaction.get("channel_id")
        user_id = interaction.get("user_id")

        if not await self._check_admin(guild_id, user_id):
            await self.send_embed(
                channel_id,
                "Permission Denied",
                "Only admins can start giveaways",
                color=EmbedColor.ERROR
            )
            return

        if winners < 1 or winners > 20:
            await self.send_embed(
                channel_id,
                "Invalid Winners",
                "Winners must be between 1 and 20",
                color=EmbedColor.ERROR
            )
            return

        seconds = TimeConverter.parse(duration)
        if not seconds or seconds < 60:
            await self.send_embed(
                channel_id,
                "Invalid Duration",
                "Duration must be at least 1 minute",
                color=EmbedColor.ERROR
            )
            return

        giveaway_id = f"giveaway_{guild_id}_{int(datetime.utcnow().timestamp())}"

        giveaway_data = {
            "giveaway_id": giveaway_id,
            "guild_id": guild_id,
            "channel_id": channel_id,
            "host_id": user_id,
            "prize": prize,
            "winners_count": winners,
            "participants": [],
            "winners": [],
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(seconds=seconds)).isoformat(),
            "ended": False
        }

        await self.db.db.giveaways.insert_one(giveaway_data)

        embed = {
            "title": "🎉 GIVEAWAY",
            "description": f"**Prize:** {prize}\n**Winners:** {winners}\n**Duration:** {duration}",
            "fields": [
                {"name": "Host", "value": f"<@{user_id}>", "inline": True},
                {"name": "Ends in", "value": duration, "inline": True},
            ],
            "color": 0x2ECC71
        }

        await self.send_message(channel_id, embed=embed)

        self.active_giveaways[giveaway_id] = []

    @app_command(name="end-giveaway", description="End a giveaway early (Admin)")
    async def end_giveaway(self, interaction: Dict[str, Any], giveaway_id: str):
        """End a giveaway"""
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        channel_id = interaction.get("channel_id")
        user_id = interaction.get("user_id")

        if not await self._check_admin(guild_id, user_id):
            await self.send_embed(
                channel_id,
                "Permission Denied",
                "Only admins can end giveaways",
                color=EmbedColor.ERROR
            )
            return

        try:
            giveaway = await self.db.db.giveaways.find_one({"giveaway_id": giveaway_id})

            if not giveaway:
                await self.send_embed(
                    channel_id,
                    "Not Found",
                    "Giveaway not found",
                    color=EmbedColor.ERROR
                )
                return

            participants = self.active_giveaways.get(giveaway_id, [])
            winners_count = giveaway.get("winners_count", 1)

            if not participants:
                await self.send_embed(
                    channel_id,
                    "No Participants",
                    "No one entered the giveaway",
                    color=EmbedColor.ERROR
                )
                return

            winners = random.sample(participants, min(winners_count, len(participants)))

            await self.db.db.giveaways.update_one(
                {"giveaway_id": giveaway_id},
                {"$set": {"winners": winners, "ended": True}}
            )

            winners_text = "\n".join([f"• <@{w}>" for w in winners])

            embed = {
                "title": "🎉 GIVEAWAY ENDED",
                "description": f"**Prize:** {giveaway.get('prize')}\n\n**Winners:**\n{winners_text}",
                "color": 0x2ECC71
            }

            await self.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"End giveaway error: {e}")
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
    return Giveaways(adapter, db, config)
