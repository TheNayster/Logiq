"""
Embed utilities for Logiq (Stoat-only)
Creates consistent, themed embeds
Returns dictionaries instead of discord.Embed objects
"""

from typing import Optional, List, Dict, Any
from datetime import datetime


class EmbedColor:
    """Color palette for embeds (Stoat-compatible)"""
    PRIMARY = 0x5865F2      # Blurple
    SUCCESS = 0x57F287      # Green
    WARNING = 0xFEE75C      # Yellow
    ERROR = 0xED4245        # Red
    INFO = 0x3498DB         # Blue
    PREMIUM = 0xF47FFF      # Pink
    LEVELING = 0xFEE75C     # Gold
    ECONOMY = 0x57F287      # Green
    AI = 0x00D9FF           # Cyan
    STOAT = 0x2ECC71        # Green
    STOAT_ERROR = 0xE74C3C  # Red
    STOAT_WARNING = 0xF39C12  # Orange
    STOAT_INFO = 0x3498DB   # Blue
    STOAT_PRIMARY = 0x2F3136  # Dark gray


class EmbedFactory:
    """Factory for creating themed embeds (Stoat-only - returns dicts)"""

    @staticmethod
    def create(
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: int = EmbedColor.PRIMARY,
        footer: Optional[str] = None,
        thumbnail: Optional[str] = None,
        image: Optional[str] = None,
        fields: Optional[List[Dict[str, Any]]] = None,
        timestamp: bool = True
    ) -> Dict[str, Any]:
        """
        Create a custom embed dictionary

        Args:
            title: Embed title
            description: Embed description
            color: Embed color (hex)
            footer: Footer text
            thumbnail: Thumbnail URL
            image: Image URL
            fields: List of field dictionaries
            timestamp: Whether to add timestamp

        Returns:
            Dictionary representing embed
        """
        embed: Dict[str, Any] = {}

        if title:
            embed["title"] = title

        if description:
            embed["description"] = description

        if color:
            embed["color"] = color

        if timestamp:
            embed["timestamp"] = datetime.utcnow().isoformat()

        if footer:
            embed["footer"] = {"text": footer}

        if thumbnail:
            embed["thumbnail"] = {"url": thumbnail}

        if image:
            embed["image"] = {"url": image}

        if fields:
            embed["fields"] = fields

        return embed

    @staticmethod
    def success(title: str, description: str) -> Dict[str, Any]:
        """Create success embed"""
        return EmbedFactory.create(
            title=f"✅ {title}",
            description=description,
            color=EmbedColor.SUCCESS
        )

    @staticmethod
    def error(title: str, description: str) -> Dict[str, Any]:
        """Create error embed"""
        return EmbedFactory.create(
            title=f"❌ {title}",
            description=description,
            color=EmbedColor.ERROR
        )

    @staticmethod
    def warning(title: str, description: str) -> Dict[str, Any]:
        """Create warning embed"""
        return EmbedFactory.create(
            title=f"⚠️ {title}",
            description=description,
            color=EmbedColor.WARNING
        )

    @staticmethod
    def info(title: str, description: str) -> Dict[str, Any]:
        """Create info embed"""
        return EmbedFactory.create(
            title=f"ℹ️ {title}",
            description=description,
            color=EmbedColor.INFO
        )

    @staticmethod
    def ai_response(message: str, model: str = "AI") -> Dict[str, Any]:
        """Create AI response embed"""
        return EmbedFactory.create(
            title="🤖 AI Response",
            description=message,
            color=EmbedColor.AI,
            footer=f"Powered by {model}"
        )

    @staticmethod
    def level_up(user_id: str, username: str, new_level: int, xp: int) -> Dict[str, Any]:
        """Create level up embed (Stoat format)"""
        return EmbedFactory.create(
            title="🎉 Level Up!",
            description=f"<@{user_id}> just reached **Level {new_level}**!",
            color=EmbedColor.LEVELING,
            fields=[
                {"name": "Level", "value": str(new_level), "inline": True},
                {"name": "Total XP", "value": str(xp), "inline": True}
            ]
        )

    @staticmethod
    def rank_card(
        user_id: str,
        username: str,
        level: int,
        xp: int,
        rank: int,
        next_level_xp: int
    ) -> Dict[str, Any]:
        """Create rank card embed (Stoat format)"""
        progress = (xp % next_level_xp) / next_level_xp * 100
        progress_bar = "█" * int(progress / 10) + "░" * (10 - int(progress / 10))

        return EmbedFactory.create(
            title=f"📊 Rank Card - {username}",
            color=EmbedColor.LEVELING,
            fields=[
                {"name": "Rank", "value": f"#{rank}", "inline": True},
                {"name": "Level", "value": str(level), "inline": True},
                {"name": "XP", "value": f"{xp % next_level_xp}/{next_level_xp}", "inline": True},
                {"name": "Progress", "value": f"{progress_bar} {progress:.1f}%", "inline": False}
            ]
        )

    @staticmethod
    def economy_balance(
        user_id: str,
        username: str,
        balance: int,
        currency_symbol: str = "💎"
    ) -> Dict[str, Any]:
        """Create balance embed (Stoat format)"""
        return EmbedFactory.create(
            title=f"{currency_symbol} Balance",
            description=f"<@{user_id}>'s balance",
            color=EmbedColor.ECONOMY,
            fields=[
                {"name": "Amount", "value": f"{currency_symbol} {balance:,}", "inline": False}
            ]
        )

    @staticmethod
    def moderation_action(
        action: str,
        user_id: str,
        username: str,
        moderator_id: str,
        moderator_name: str,
        reason: str
    ) -> Dict[str, Any]:
        """Create moderation action embed (Stoat format)"""
        return EmbedFactory.create(
            title=f"🔨 {action}",
            description=f"<@{user_id}> has been {action.lower()}",
            color=EmbedColor.WARNING,
            fields=[
                {"name": "User", "value": f"<@{user_id}> ({user_id})", "inline": True},
                {"name": "Moderator", "value": f"<@{moderator_id}>", "inline": True},
                {"name": "Reason", "value": reason, "inline": False}
            ]
        )

    @staticmethod
    def verification_prompt() -> Dict[str, Any]:
        """Create verification prompt embed"""
        return EmbedFactory.create(
            title="🔐 Verification Required",
            description="Click the button below to verify and gain access to the server.",
            color=EmbedColor.PRIMARY,
            footer="Complete verification to unlock all channels"
        )

    @staticmethod
    def ticket_created(ticket_id: str, category: str) -> Dict[str, Any]:
        """Create ticket created embed"""
        return EmbedFactory.create(
            title="🎫 Ticket Created",
            description="Your support ticket has been created!",
            color=EmbedColor.SUCCESS,
            fields=[
                {"name": "Ticket ID", "value": ticket_id, "inline": True},
                {"name": "Category", "value": category, "inline": True}
            ]
        )

    @staticmethod
    def leaderboard(
        title: str,
        entries: List[Dict[str, Any]],
        field_name: str = "Rank",
        color: int = EmbedColor.LEVELING
    ) -> Dict[str, Any]:
        """Create leaderboard embed"""
        description = ""
        for i, entry in enumerate(entries[:10], 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            user_id = entry.get('user_id', 'Unknown')
            value = entry.get(field_name, 0)
            description += f"{medal} <@{user_id}> - **{value:,}**\n"

        return EmbedFactory.create(
            title=f"🏆 {title}",
            description=description or "No entries yet",
            color=color
        )

    @staticmethod
    def welcome(username: str, user_id: str) -> Dict[str, Any]:
        """Create welcome embed (Stoat format)"""
        return {
            "title": f"Welcome {username}!",
            "description": f"Thanks for joining our server, <@{user_id}>!",
            "color": EmbedColor.SUCCESS
        }
