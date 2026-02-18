"""
Database Manager - Stoat-only MongoDB manager
Pure async with Motor (no Discord)
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from motor.motor_asyncio import AsyncClient, AsyncDatabase
import pymongo

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Async MongoDB database manager with Stoat schema support"""

    def __init__(self, uri: str, database_name: str, pool_size: int = 10):
        self.uri = uri
        self.database_name = database_name
        self.pool_size = pool_size
        self.client: Optional[AsyncClient] = None
        self.db: Optional[AsyncDatabase] = None

    async def connect(self) -> None:
        """Establish database connection"""
        try:
            self.client = AsyncClient(
                self.uri,
                maxPoolSize=self.pool_size,
                minPoolSize=1
            )
            self.db = self.client[self.database_name]

            # Test connection
            await self.client.admin.command('ping')
            logger.info(f"✅ Connected to MongoDB: {self.database_name}")

            # Create indexes
            await self._create_indexes()

        except Exception as e:
            logger.error(f"Database connection failed: {e}", exc_info=True)
            raise

    async def _create_indexes(self) -> None:
        """Create database indexes for Stoat schema"""
        try:
            # Users collection
            await self.db.users.create_index([("user_id", 1), ("guild_id", 1)], unique=True)
            await self.db.users.create_index([("guild_id", 1)])

            # Guilds collection
            await self.db.guilds.create_index([("guild_id", 1)], unique=True)

            # Members collection
            await self.db.members.create_index([("guild_id", 1), ("user_id", 1)], unique=True)

            # Moderation logs
            await self.db.moderation_actions.create_index([("guild_id", 1)])
            await self.db.moderation_actions.create_index([("target_id", 1)])

            # Tickets
            await self.db.tickets.create_index([("guild_id", 1)])
            await self.db.tickets.create_index([("creator_id", 1)])

            # Giveaways
            await self.db.giveaways.create_index([("guild_id", 1)])

            logger.info("Database indexes created")

        except Exception as e:
            logger.error(f"Index creation error: {e}")

    async def disconnect(self) -> None:
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("Database disconnected")

    @property
    def is_connected(self) -> bool:
        return self.client is not None

    # ========== USER OPERATIONS ==========
    async def get_user(self, user_id: str, guild_id: str) -> Optional[Dict[str, Any]]:
        """Get user document (Stoat schema with string IDs)"""
        return await self.db.users.find_one({
            "user_id": user_id,
            "guild_id": guild_id
        })

    async def create_user(self, user_id: str, guild_id: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create new user document"""
        user_doc = {
            "user_id": user_id,
            "guild_id": guild_id,
            "balance": 0,
            "xp": 0,
            "level": 0,
            "created_at": datetime.utcnow().isoformat(),
            "last_daily": None,
            **(data or {})
        }

        await self.db.users.insert_one(user_doc)
        return user_doc

    async def update_user(self, user_id: str, guild_id: str, data: Dict[str, Any]) -> bool:
        """Update user document"""
        result = await self.db.users.update_one(
            {"user_id": user_id, "guild_id": guild_id},
            {"$set": data}
        )
        return result.modified_count > 0

    async def add_balance(self, user_id: str, guild_id: str, amount: int) -> bool:
        """Add to user balance"""
        result = await self.db.users.update_one(
            {"user_id": user_id, "guild_id": guild_id},
            {"$inc": {"balance": amount}}
        )
        return result.modified_count > 0

    async def add_xp(self, user_id: str, guild_id: str, amount: int) -> bool:
        """Add XP to user"""
        result = await self.db.users.update_one(
            {"user_id": user_id, "guild_id": guild_id},
            {"$inc": {"xp": amount}}
        )
        return result.modified_count > 0

    async def get_leaderboard(self, guild_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top users by balance"""
        return await self.db.users.find({"guild_id": guild_id}).sort("balance", -1).limit(limit).to_list(length=limit)

    # ========== MEMBER OPERATIONS ==========
    async def get_member(self, guild_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get member document"""
        return await self.db.members.find_one({
            "guild_id": guild_id,
            "user_id": user_id
        })

    async def create_member(self, guild_id: str, user_id: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create member document"""
        member_doc = {
            "guild_id": guild_id,
            "user_id": user_id,
            "roles": [],
            "is_admin": False,
            "is_mod": False,
            "created_at": datetime.utcnow().isoformat(),
            **(data or {})
        }

        await self.db.members.insert_one(member_doc)
        return member_doc

    async def update_member(self, guild_id: str, user_id: str, data: Dict[str, Any]) -> bool:
        """Update member document"""
        result = await self.db.members.update_one(
            {"guild_id": guild_id, "user_id": user_id},
            {"$set": data}
        )
        return result.modified_count > 0

    async def add_member_role(self, guild_id: str, user_id: str, role_id: str) -> bool:
        """Add role to member"""
        result = await self.db.members.update_one(
            {"guild_id": guild_id, "user_id": user_id},
            {"$addToSet": {"roles": role_id}}
        )
        return result.modified_count > 0

    async def remove_member_role(self, guild_id: str, user_id: str, role_id: str) -> bool:
        """Remove role from member"""
        result = await self.db.members.update_one(
            {"guild_id": guild_id, "user_id": user_id},
            {"$pull": {"roles": role_id}}
        )
        return result.modified_count > 0

    # ========== GUILD OPERATIONS ==========
    async def get_guild(self, guild_id: str) -> Optional[Dict[str, Any]]:
        """Get guild configuration"""
        return await self.db.guilds.find_one({"guild_id": guild_id})

    async def get_guild_data(self, guild_id: str) -> Dict[str, Any]:
        """Alias for get_guild"""
        return await self.get_guild(guild_id)

    async def create_guild(self, guild_id: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create guild configuration"""
        guild_doc = {
            "guild_id": guild_id,
            "name": f"Guild {guild_id}",
            "created_at": datetime.utcnow().isoformat(),
            "prefix": "!",
            **(data or {})
        }

        await self.db.guilds.insert_one(guild_doc)
        return guild_doc

    async def update_guild(self, guild_id: str, data: Dict[str, Any]) -> bool:
        """Update guild configuration"""
        result = await self.db.guilds.update_one(
            {"guild_id": guild_id},
            {"$set": data}
        )
        return result.modified_count > 0

    # ========== ROLE OPERATIONS ==========
    async def get_role(self, guild_id: str, role_id: str) -> Optional[Dict[str, Any]]:
        """Get role configuration"""
        return await self.db.roles.find_one({
            "guild_id": guild_id,
            "role_id": role_id
        })

    async def create_role(self, guild_id: str, role_id: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create role"""
        role_doc = {
            "guild_id": guild_id,
            "role_id": role_id,
            "created_at": datetime.utcnow().isoformat(),
            **(data or {})
        }

        await self.db.roles.insert_one(role_doc)
        return role_doc

    # ========== MODERATION OPERATIONS ==========
    async def add_action(
        self,
        action_type: str,
        target_id: str,
        guild_id: str,
        moderator_id: str,
        reason: str,
        timestamp: datetime
    ) -> bool:
        """Log moderation action"""
        action_doc = {
            "type": action_type,
            "target_id": target_id,
            "guild_id": guild_id,
            "moderator_id": moderator_id,
            "reason": reason,
            "timestamp": timestamp.isoformat()
        }

        result = await self.db.moderation_actions.insert_one(action_doc)
        return result.inserted_id is not None

    async def get_user_actions(
        self,
        guild_id: str,
        user_id: str,
        action_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get moderation actions for user"""
        query = {"guild_id": guild_id, "target_id": user_id}
        if action_type:
            query["type"] = action_type

        return await self.db.moderation_actions.find(query).sort("timestamp", -1).to_list(length=100)

    # ========== TICKET OPERATIONS ==========
    async def create_ticket(self, guild_id: str, creator_id: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create support ticket"""
        ticket_doc = {
            "guild_id": guild_id,
            "creator_id": creator_id,
            "status": "open",
            "created_at": datetime.utcnow().isoformat(),
            **(data or {})
        }

        result = await self.db.tickets.insert_one(ticket_doc)
        ticket_doc["_id"] = result.inserted_id
        return ticket_doc

    async def close_ticket(self, ticket_id) -> bool:
        """Close ticket"""
        result = await self.db.tickets.update_one(
            {"_id": ticket_id},
            {"$set": {"status": "closed", "closed_at": datetime.utcnow().isoformat()}}
        )
        return result.modified_count > 0
