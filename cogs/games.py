"""
Games Cog for Logiq (Stoat-only)
Interactive mini-games for users
"""

import logging
import random
from typing import Dict, Any, Optional

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedFactory, EmbedColor
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class Games(AdaptedCog):
    """Games and entertainment cog (Stoat-only, text-based)"""

    def __init__(self, adapter, db: DatabaseManager, config: dict):
        super().__init__(adapter, db, config)
        self.module_config = config.get('modules', {}).get('games', {})

    @app_command(name="dice", description="Roll a dice")
    async def dice(self, interaction: Dict[str, Any], sides: int = 6):
        """Roll a dice"""
        channel_id = interaction.get("channel_id")
        user_id = interaction.get("user_id")

        if sides < 2 or sides > 100:
            await self.send_embed(
                channel_id,
                "Invalid Sides",
                "Dice must have 2-100 sides",
                color=EmbedColor.ERROR
            )
            return

        result = random.randint(1, sides)

        embed = {
            "title": "🎲 Dice Roll",
            "description": f"<@{user_id}> rolled a **{result}** on a {sides}-sided dice!",
            "color": EmbedColor.SUCCESS
        }

        await self.send_message(channel_id, embed=embed)

    @app_command(name="coinflip", description="Flip a coin")
    async def coinflip(self, interaction: Dict[str, Any]):
        """Flip a coin"""
        channel_id = interaction.get("channel_id")
        user_id = interaction.get("user_id")

        result = random.choice(["Heads", "Tails"])

        embed = {
            "title": "🪙 Coin Flip",
            "description": f"<@{user_id}> flipped a coin and got **{result}**!",
            "color": EmbedColor.SUCCESS
        }

        await self.send_message(channel_id, embed=embed)

    @app_command(name="8ball", description="Ask the magic 8-ball")
    async def eightball(self, interaction: Dict[str, Any], question: str):
        """Ask the magic 8-ball"""
        channel_id = interaction.get("channel_id")
        user_id = interaction.get("user_id")

        responses = [
            "Yes, definitely!", "It is certain.", "Without a doubt.",
            "Most likely.", "Outlook good.", "Signs point to yes.",
            "Reply hazy, try again.", "Ask again later.",
            "Cannot predict now.", "Don't count on it.",
            "My reply is no.", "Outlook not so good.", "Very doubtful."
        ]

        response = random.choice(responses)

        embed = {
            "title": "🔮 Magic 8-Ball",
            "description": f"<@{user_id}> asked: **{question}**\n\n**Answer:** {response}",
            "color": EmbedColor.INFO
        }

        await self.send_message(channel_id, embed=embed)

    @app_command(name="trivia", description="Play trivia")
    async def trivia(self, interaction: Dict[str, Any]):
        """Play trivia"""
        channel_id = interaction.get("channel_id")

        questions = [
            {"q": "What is 2+2?", "a": "4"},
            {"q": "What year was Python created?", "a": "1991"},
            {"q": "What is the capital of France?", "a": "Paris"},
        ]

        question = random.choice(questions)

        embed = {
            "title": "🧠 Trivia",
            "description": question["q"],
            "color": EmbedColor.INFO
        }

        await self.send_message(channel_id, embed=embed)

    @app_command(name="balance", description="Check your balance")
    async def balance(self, interaction: Dict[str, Any], user_id: Optional[str] = None):
        """Check balance"""
        channel_id = interaction.get("channel_id")
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        target_id = user_id or interaction.get("user_id")

        try:
            user_data = await self.db.get_user(target_id, guild_id)
            if not user_data:
                user_data = await self.db.create_user(target_id, guild_id)

            balance = user_data.get('balance', 0)

            embed = {
                "title": "💎 Balance",
                "description": f"<@{target_id}> has **{balance}** coins",
                "color": EmbedColor.SUCCESS
            }

            await self.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"Balance error: {e}")
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)


async def setup(adapter, db, config):
    """Setup function for cog loading"""
    return Games(adapter, db, config)
