"""
Permission utilities for Logiq (Stoat-only)
Database-driven permission checking (NO Discord)
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


# ========== STOAT-ONLY PERMISSION CHECKS ==========

async def is_admin(db, guild_id: str, user_id: str) -> bool:
    """Check if user is server admin (Stoat)"""
    try:
        member = await db.get_member(guild_id, user_id)
        if not member:
            return False
        return member.get("is_admin", False)
    except Exception as e:
        logger.error(f"Admin check error: {e}")
        return False


async def is_mod(db, guild_id: str, user_id: str) -> bool:
    """Check if user is moderator (Stoat)"""
    try:
        member = await db.get_member(guild_id, user_id)
        if not member:
            return False
        return member.get("is_mod", False) or member.get("is_admin", False)
    except Exception as e:
        logger.error(f"Mod check error: {e}")
        return False


async def has_role(db, guild_id: str, user_id: str, role_id: str) -> bool:
    """Check if user has role"""
    try:
        member = await db.get_member(guild_id, user_id)
        if not member:
            return False
        roles = member.get("roles", [])
        return role_id in roles
    except Exception as e:
        logger.error(f"Role check error: {e}")
        return False


async def is_guild_owner(db, guild_id: str, user_id: str) -> bool:
    """Check if user is guild owner (Stoat)"""
    try:
        guild = await db.get_guild(guild_id)
        if not guild:
            return False
        return guild.get("owner_id") == user_id
    except Exception as e:
        logger.error(f"Guild owner check error: {e}")
        return False


# ========== PERMISSION CHECKER CLASS ==========

class PermissionChecker:
    """Utility class for permission checking (Stoat-only)"""

    @staticmethod
    async def can_moderate(
        db,
        guild_id: str,
        moderator_id: str,
        target_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if moderator can moderate target (Stoat)

        Args:
            db: Database manager
            guild_id: Guild ID
            moderator_id: Moderator user ID
            target_id: Target user ID

        Returns:
            Tuple of (can_moderate, error_message)
        """
        try:
            # Can't moderate yourself
            if moderator_id == target_id:
                return False, "You cannot moderate yourself"

            # Check if moderator is admin or mod
            mod_member = await db.get_member(guild_id, moderator_id)
            if not mod_member:
                return False, "You have no permissions"

            is_mod_or_admin = mod_member.get("is_mod", False) or mod_member.get("is_admin", False)
            if not is_mod_or_admin:
                return False, "You are not a moderator or admin"

            # Check if target is owner
            guild = await db.get_guild(guild_id)
            if guild and guild.get("owner_id") == target_id:
                return False, "You cannot moderate the server owner"

            return True, None

        except Exception as e:
            logger.error(f"Can moderate check error: {e}")
            return False, "Permission check failed"

    @staticmethod
    async def get_permission_level(db, guild_id: str, user_id: str) -> int:
        """
        Get permission level (Stoat)
        0 = User
        1 = Moderator
        2 = Admin
        3 = Owner

        Args:
            db: Database manager
            guild_id: Guild ID
            user_id: User ID

        Returns:
            Permission level (0-3)
        """
        try:
            guild = await db.get_guild(guild_id)
            if guild and guild.get("owner_id") == user_id:
                return 3

            member = await db.get_member(guild_id, user_id)
            if not member:
                return 0

            if member.get("is_admin", False):
                return 2

            if member.get("is_mod", False):
                return 1

            return 0

        except Exception as e:
            logger.error(f"Get permission level error: {e}")
            return 0

    @staticmethod
    async def check_hierarchy(
        db,
        guild_id: str,
        executor_id: str,
        target_id: str
    ) -> bool:
        """Check if executor is higher in hierarchy than target (Stoat)"""
        try:
            executor_level = await PermissionChecker.get_permission_level(db, guild_id, executor_id)
            target_level = await PermissionChecker.get_permission_level(db, guild_id, target_id)
            return executor_level > target_level
        except Exception as e:
            logger.error(f"Check hierarchy error: {e}")
            return False

    @staticmethod
    async def has_permission(
        db,
        guild_id: str,
        user_id: str,
        permission: str
    ) -> bool:
        """Check if user has specific permission (Stoat)"""
        try:
            permission = permission.lower()

            permissions_map = {
                "ban_members": 2,
                "kick_members": 2,
                "manage_members": 2,
                "manage_roles": 2,
                "manage_channels": 2,
                "manage_messages": 2,
                "mute_members": 1,
                "deafen_members": 1,
                "send_messages": 0,
                "read_messages": 0,
            }

            required_level = permissions_map.get(permission, 0)
            user_level = await PermissionChecker.get_permission_level(db, guild_id, user_id)

            return user_level >= required_level

        except Exception as e:
            logger.error(f"Has permission check error: {e}")
            return False

    @staticmethod
    async def get_members_with_role(
        db,
        guild_id: str,
        role_id: str,
        limit: int = 100
    ) -> list:
        """Get all members with specific role (Stoat)"""
        try:
            return await db.db.members.find({
                "guild_id": guild_id,
                "roles": role_id
            }).to_list(length=limit)
        except Exception as e:
            logger.error(f"Get members with role error: {e}")
            return []