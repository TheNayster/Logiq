"""
Tickets Cog for Logiq (Stoat-only)
Support ticket system
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedFactory, EmbedColor
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class Tickets(AdaptedCog):
    """Support tickets cog (Stoat-only)"""

    def __init__(self, adapter, db: DatabaseManager, config: dict):
        super().__init__(adapter, db, config)
        self.module_config = config.get('modules', {}).get('tickets', {})
        self.max_open = self.module_config.get('max_open_per_user', 3)

    @app_command(name="ticket-create", description="Create a support ticket")
    async def ticket_create(self, interaction: Dict[str, Any], topic: str):
        """Create support ticket (Stoat)"""
        channel_id = interaction.get("channel_id")
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        user_id = interaction.get("user_id")

        try:
            # Check open tickets
            open_tickets = await self.db.db.tickets.count_documents({
                "guild_id": guild_id,
                "creator_id": user_id,
                "status": "open"
            })

            if open_tickets >= self.max_open:
                await self.send_embed(
                    channel_id,
                    "Too Many Tickets",
                    f"You can only have {self.max_open} open tickets at a time",
                    color=EmbedColor.ERROR
                )
                return

            # Create ticket
            ticket = await self.db.create_ticket(guild_id, user_id, {
                "topic": topic,
                "messages": []
            })

            ticket_id = str(ticket.get("_id"))

            embed = EmbedFactory.ticket_created(ticket_id, topic)
            await self.send_message(channel_id, embed=embed)

            logger.info(f"Ticket {ticket_id} created by {user_id}")

        except Exception as e:
            logger.error(f"Ticket create error: {e}")
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)

    @app_command(name="ticket-close", description="Close your support ticket")
    async def ticket_close(self, interaction: Dict[str, Any], ticket_id: str):
        """Close support ticket (Stoat)"""
        channel_id = interaction.get("channel_id")
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        user_id = interaction.get("user_id")

        try:
            from bson import ObjectId

            ticket = await self.db.db.tickets.find_one({
                "_id": ObjectId(ticket_id) if len(ticket_id) == 24 else ticket_id,
                "guild_id": guild_id,
                "creator_id": user_id
            })

            if not ticket:
                await self.send_embed(
                    channel_id,
                    "Not Found",
                    "Ticket not found or you don't have permission",
                    color=EmbedColor.ERROR
                )
                return

            await self.db.close_ticket(ticket.get("_id"))

            await self.send_embed(
                channel_id,
                "✅ Ticket Closed",
                f"Ticket {ticket_id} has been closed",
                color=EmbedColor.SUCCESS
            )

            logger.info(f"Ticket {ticket_id} closed by {user_id}")

        except Exception as e:
            logger.error(f"Ticket close error: {e}")
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)

    @app_command(name="ticket-list", description="View your support tickets")
    async def ticket_list(self, interaction: Dict[str, Any]):
        """List user's tickets (Stoat)"""
        channel_id = interaction.get("channel_id")
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        user_id = interaction.get("user_id")

        try:
            tickets = await self.db.db.tickets.find({
                "guild_id": guild_id,
                "creator_id": user_id
            }).to_list(length=10)

            description = ""
            for ticket in tickets:
                status = "🟢 Open" if ticket.get("status") == "open" else "🔴 Closed"
                ticket_id = str(ticket.get("_id"))
                topic = ticket.get("topic", "Unknown")
                description += f"**{ticket_id}** - {topic} {status}\n"

            embed = {
                "title": "🎫 Your Tickets",
                "description": description or "No tickets yet",
                "color": EmbedColor.INFO
            }

            await self.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"Ticket list error: {e}")
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)


async def setup(adapter, db, config):
    """Setup function for cog loading"""
    return Tickets(adapter, db, config)
