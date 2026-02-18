"""
Stoat data converters and normalization utilities.
Stoat-only conversions (NO Discord conversion)
"""

from typing import Any, Dict, Optional
from datetime import datetime


class IDConverter:
    """Convert and normalize IDs to Stoat format (string-based)"""

    @staticmethod
    def normalize_id(value: Any) -> str:
        """Normalize any ID to Stoat string format"""
        if isinstance(value, str):
            return value
        elif isinstance(value, int):
            return str(value)
        else:
            return str(value)

    @staticmethod
    def validate_id(value: str) -> bool:
        """Validate ID format"""
        if not isinstance(value, str):
            return False
        return len(value) > 0 and value.isalnum()


class PayloadConverter:
    """Convert Stoat API payloads to normalized dict format"""

    @staticmethod
    def stoat_user_to_dict(stoat_user: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Stoat user payload to normalized dict"""
        return {
            "id": stoat_user.get("_id") or stoat_user.get("id"),
            "username": stoat_user.get("username"),
            "avatar": stoat_user.get("avatar_url"),
            "display_name": stoat_user.get("display_name") or stoat_user.get("username"),
            "bot": stoat_user.get("bot", False),
            "created_at": stoat_user.get("created_at"),
            "status": stoat_user.get("status", "offline"),
        }

    @staticmethod
    def stoat_member_to_dict(stoat_member: Dict[str, Any], include_user: bool = True) -> Dict[str, Any]:
        """Convert Stoat member payload to normalized dict"""
        member = {
            "guild_id": stoat_member.get("server_id") or stoat_member.get("guild_id"),
            "user_id": stoat_member.get("user_id") or stoat_member.get("_id", {}).get("user"),
            "roles": stoat_member.get("roles", []),
            "nickname": stoat_member.get("nickname"),
            "joined_at": stoat_member.get("joined_at"),
            "permissions": stoat_member.get("permissions", 0),
        }
        if include_user and "user" in stoat_member:
            member["user"] = PayloadConverter.stoat_user_to_dict(stoat_member["user"])
        return member

    @staticmethod
    def stoat_guild_to_dict(stoat_guild: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Stoat guild/server payload to normalized dict"""
        return {
            "id": stoat_guild.get("_id") or stoat_guild.get("id"),
            "name": stoat_guild.get("name"),
            "icon": stoat_guild.get("icon_url"),
            "owner_id": stoat_guild.get("owner"),
            "member_count": stoat_guild.get("member_count", 0),
            "created_at": stoat_guild.get("created_at"),
            "features": stoat_guild.get("features", []),
            "description": stoat_guild.get("description", ""),
        }

    @staticmethod
    def stoat_channel_to_dict(stoat_channel: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Stoat channel payload to normalized dict"""
        return {
            "id": stoat_channel.get("_id") or stoat_channel.get("id"),
            "name": stoat_channel.get("name"),
            "type": stoat_channel.get("channel_type") or stoat_channel.get("type"),
            "guild_id": stoat_channel.get("server") or stoat_channel.get("guild_id"),
            "position": stoat_channel.get("position", 0),
            "topic": stoat_channel.get("topic"),
            "nsfw": stoat_channel.get("nsfw", False),
        }

    @staticmethod
    def stoat_role_to_dict(stoat_role: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Stoat role payload to normalized dict"""
        return {
            "id": stoat_role.get("_id") or stoat_role.get("id"),
            "name": stoat_role.get("name"),
            "color": stoat_role.get("colour") or stoat_role.get("color", 0),
            "position": stoat_role.get("rank", 0),
            "permissions": stoat_role.get("permissions", 0),
            "hoist": stoat_role.get("hoist", False),
            "mentionable": stoat_role.get("mentionable", False),
        }

    @staticmethod
    def stoat_message_to_dict(stoat_msg: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Stoat message payload to normalized dict"""
        return {
            "id": stoat_msg.get("_id") or stoat_msg.get("id"),
            "content": stoat_msg.get("content"),
            "author_id": stoat_msg.get("author"),
            "guild_id": stoat_msg.get("server") or stoat_msg.get("guild_id"),
            "channel_id": stoat_msg.get("channel"),
            "timestamp": stoat_msg.get("timestamp"),
            "edited_timestamp": stoat_msg.get("edited_timestamp"),
            "embeds": stoat_msg.get("embeds", []),
            "attachments": stoat_msg.get("attachments", []),
            "reactions": stoat_msg.get("reactions", {}),
        }


class SchemaHelpers:
    """Helpers for Stoat schema normalization"""

    @staticmethod
    def normalize_guild_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize guild config to Stoat format"""
        return {
            "guild_id": config.get("guild_id"),
            "name": config.get("name", ""),
            "owner_id": config.get("owner_id"),
            "prefix": config.get("prefix", "/"),
            "modules": config.get("modules", {}),
            "log_channel": config.get("log_channel"),
            "welcome_channel": config.get("welcome_channel"),
            "verified_role": config.get("verified_role"),
            "settings": config.get("settings", {}),
        }

    @staticmethod
    def normalize_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize user data to Stoat format"""
        return {
            "user_id": str(user_data.get("user_id")),
            "guild_id": str(user_data.get("guild_id")),
            "xp": user_data.get("xp", 0),
            "level": user_data.get("level", 0),
            "balance": user_data.get("balance", 1000),
            "inventory": user_data.get("inventory", []),
            "warnings": user_data.get("warnings", []),
            "tags": user_data.get("tags", []),
            "created_at": user_data.get("created_at", datetime.utcnow().isoformat()),
        }

    @staticmethod
    def timestamp_to_iso(timestamp: Any) -> str:
        """Convert any timestamp to ISO 8601 format"""
        if isinstance(timestamp, str):
            return timestamp
        elif isinstance(timestamp, datetime):
            return timestamp.isoformat()
        else:
            try:
                return datetime.fromtimestamp(timestamp).isoformat()
            except Exception:
                return datetime.utcnow().isoformat()