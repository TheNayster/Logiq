"""
Stoat permission system (pure Stoat, no Discord conversion)
Database-driven permissions for Stoat.chat
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class StoatPermissions:
    """Stoat permission flags (as per Stoat API)"""
    
    # Server permissions
    ADMINISTRATOR = "administrator"
    MANAGE_SERVER = "manage_server"
    MANAGE_ROLES = "manage_roles"
    MANAGE_CHANNELS = "manage_channels"
    KICK_MEMBERS = "kick_members"
    BAN_MEMBERS = "ban_members"
    CREATE_INVITES = "create_invites"
    MANAGE_GUILD = "manage_guild"
    AUDIT_LOG = "audit_log"
    
    # Channel permissions
    VIEW_CHANNEL = "view_channel"
    SEND_MESSAGES = "send_messages"
    MANAGE_MESSAGES = "manage_messages"
    EMBED_LINKS = "embed_links"
    ATTACH_FILES = "attach_files"
    READ_MESSAGE_HISTORY = "read_message_history"
    MENTION_EVERYONE = "mention_everyone"
    USE_EXTERNAL_EMOJIS = "use_external_emojis"


class PermissionChecker:
    """Check Stoat permissions (database-driven)"""

    def __init__(self, db):
        self.db = db

    async def check_permission(
        self,
        guild_id: str,
        user_id: str,
        permission: str
    ) -> bool:
        """Check if user has specific permission on Stoat"""
        try:
            member = await self.db.get_member(guild_id, user_id)
            if not member:
                return False

            # Check admin first (has all permissions)
            if member.get("is_admin", False):
                return True

            # Check specific permission
            permissions = member.get("permissions", [])
            return permission in permissions

        except Exception as e:
            logger.error(f"Permission check error: {e}")
            return False

    async def check_any_permission(
        self,
        guild_id: str,
        user_id: str,
        permissions: List[str]
    ) -> bool:
        """Check if user has any of the permissions"""
        for perm in permissions:
            if await self.check_permission(guild_id, user_id, perm):
                return True
        return False

    async def check_all_permissions(
        self,
        guild_id: str,
        user_id: str,
        permissions: List[str]
    ) -> bool:
        """Check if user has all permissions"""
        for perm in permissions:
            if not await self.check_permission(guild_id, user_id, perm):
                return False
        return True

    async def get_user_permissions(
        self,
        guild_id: str,
        user_id: str
    ) -> List[str]:
        """Get all permissions for user"""
        try:
            member = await self.db.get_member(guild_id, user_id)
            if not member:
                return []

            permissions = member.get("permissions", [])
            
            # Admins have all permissions
            if member.get("is_admin", False):
                return [perm for perm in dir(StoatPermissions) if not perm.startswith('_')]

            return permissions

        except Exception as e:
            logger.error(f"Get permissions error: {e}")
            return []


class RoleHierarchy:
    """Manage role hierarchy in Stoat (pure Stoat schema)"""

    def __init__(self, db):
        self.db = db

    async def can_manage_role(
        self,
        executor_id: str,
        target_role_id: str,
        guild_id: str
    ) -> bool:
        """Check if executor can manage target role"""
        try:
            executor = await self.db.get_member(guild_id, executor_id)
            target_role = await self.db.get_role(guild_id, target_role_id)

            if not executor or not target_role:
                return False

            # Server owner can manage any role
            guild = await self.db.get_guild(guild_id)
            if executor_id == guild.get("owner_id"):
                return True

            # Admin can manage roles
            if executor.get("is_admin", False):
                executor_roles = executor.get("roles", [])
                executor_top_role = await self._get_top_role(guild_id, executor_roles)
                return executor_top_role.get("position", 0) > target_role.get("position", 0)

            return False

        except Exception as e:
            logger.error(f"Can manage role error: {e}")
            return False

    async def can_moderate_member(
        self,
        moderator_id: str,
        target_id: str,
        guild_id: str
    ) -> tuple[bool, Optional[str]]:
        """Check if moderator can act on target (Stoat)"""
        try:
            if moderator_id == target_id:
                return False, "Cannot moderate yourself"

            moderator = await self.db.get_member(guild_id, moderator_id)
            target = await self.db.get_member(guild_id, target_id)
            guild = await self.db.get_guild(guild_id)

            if not moderator or not target:
                return False, "Member not found"

            # Server owner can moderate anyone
            if moderator_id == guild.get("owner_id"):
                return True, None

            # Target is server owner
            if target_id == guild.get("owner_id"):
                return False, "Cannot moderate server owner"

            # Check moderation permissions
            has_kick = await self._check_permission(guild_id, moderator_id, "kick_members")
            has_ban = await self._check_permission(guild_id, moderator_id, "ban_members")

            if not (has_kick or has_ban):
                return False, "You don't have permission to moderate"

            # Check role hierarchy
            mod_roles = moderator.get("roles", [])
            target_roles = target.get("roles", [])

            mod_top = await self._get_top_role(guild_id, mod_roles)
            target_top = await self._get_top_role(guild_id, target_roles)

            if mod_top.get("position", 0) <= target_top.get("position", 0):
                return False, "Target has equal or higher role"

            return True, None

        except Exception as e:
            logger.error(f"Can moderate member error: {e}")
            return False, "Permission check failed"

    async def _get_top_role(self, guild_id: str, role_ids: List[str]) -> Dict[str, Any]:
        """Get highest role from list"""
        roles = []
        for role_id in role_ids:
            role = await self.db.get_role(guild_id, role_id)
            if role:
                roles.append(role)

        return max(roles, key=lambda r: r.get("position", 0)) if roles else {"position": -1}

    async def _check_permission(
        self,
        guild_id: str,
        user_id: str,
        permission: str
    ) -> bool:
        """Check specific permission"""
        member = await self.db.get_member(guild_id, user_id)
        if not member:
            return False
        return member.get("is_admin", False) or permission in member.get("permissions", [])