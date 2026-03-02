"""
Games Cog for Logiq (Stoat-only)
Interactive mini-games for users
"""

import logging
import random
from typing import Dict, Any

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedColor
logger = logging.getLogger(__name__)

FUN_FACTS = [
    "Honey never spoils — archaeologists have found 3,000-year-old honey in Egyptian tombs that was still edible.",
    "A group of flamingos is called a 'flamboyance'.",
    "Octopuses have three hearts, blue blood, and nine brains (one central + one per arm).",
    "The shortest war in history lasted 38–45 minutes — between Britain and Zanzibar in 1896.",
    "Cleopatra lived closer in time to the Moon landing than to the construction of the Great Pyramid.",
    "A day on Venus is longer than a year on Venus.",
    "Bananas are berries, but strawberries are not.",
    "The fingerprints of a koala are so similar to human fingerprints they have confused crime scene investigators.",
    "There are more possible iterations of a game of chess than there are atoms in the observable universe.",
    "Wombat poop is cube-shaped — the only known animal to produce cube-shaped droppings.",
    "The Eiffel Tower grows about 15 cm taller in summer due to thermal expansion of the iron.",
    "A bolt of lightning is five times hotter than the surface of the Sun.",
    "Crows can recognise and remember individual human faces.",
    "The word 'nerd' was first coined by Dr. Seuss in 'If I Ran the Zoo' (1950).",
    "Oxford University is older than the Aztec Empire.",
    "Sharks are older than trees — sharks have existed for around 450 million years, trees only ~350 million.",
    "There are more stars in the universe than grains of sand on all of Earth's beaches.",
    "A snail can sleep for up to three years.",
    "The average person walks about 100,000 miles in their lifetime — roughly four times around the Earth.",
    "Pineapples take about two years to fully grow.",
    "The dot over a lowercase 'i' or 'j' is called a tittle.",
    "Humans share about 60% of their DNA with bananas.",
    "Sea otters hold hands while sleeping so they don't drift apart.",
    "The first computer bug was an actual bug — a moth found in a Harvard Mark II computer in 1947.",
    "Hot water freezes faster than cold water under certain conditions — this is called the Mpemba effect.",
]


class Games(AdaptedCog):
    """Games and entertainment cog (Stoat-only, text-based)"""

    def __init__(self, adapter, db, config: dict):
        super().__init__(adapter, db, config)
        self.module_config = config.get('modules', {}).get('games', {})

    @app_command(name="dice", description="Roll a dice", usage="!dice [sides]")
    async def dice(self, interaction: Dict[str, Any], sides: int = 6):
        """Roll a dice"""
        channel_id = interaction.get("channel_id")
        user_id = interaction.get("user_id")

        if sides < 2 or sides > 100:
            await self.send_embed(
                channel_id,
                "Invalid Sides",
                "Dice must have 2-100 sides.",
                color=EmbedColor.ERROR
            )
            return

        result = random.randint(1, sides)
        embed = {
            "title": "🎲 Dice Roll",
            "description": f"<@{user_id}> rolled a **{result}** on a {sides}-sided die!",
            "color": EmbedColor.SUCCESS,
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
            "color": EmbedColor.SUCCESS,
        }
        await self.send_message(channel_id, embed=embed)

    @app_command(name="8ball", description="Ask the magic 8-ball", usage="!8ball <question>")
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
            "color": EmbedColor.INFO,
        }
        await self.send_message(channel_id, embed=embed)

    @app_command(name="trivia", description="Get a random fun fact")
    async def trivia(self, interaction: Dict[str, Any]):
        """Post a random fun fact"""
        channel_id = interaction.get("channel_id")

        fact = random.choice(FUN_FACTS)
        embed = {
            "title": "🧠 Fun Fact",
            "description": fact,
            "color": EmbedColor.INFO,
        }
        await self.send_message(channel_id, embed=embed)


async def setup(adapter, db, config):
    """Setup function for cog loading"""
    return Games(adapter, db, config)
