"""
Unit tests for database manager
Tests Stoat schema operations
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from database.db_manager import DatabaseManager


class TestDatabaseManager:
    """Test database manager"""

    @pytest.fixture
    async def db(self):
        """Create database instance (mock MongoDB)"""
        with patch('motor.motor_asyncio.AsyncMotorClient'):
            db = DatabaseManager(
                "mongodb://localhost:27017",
                "test_db",
                pool_size=5
            )
            db.db = AsyncMock()
            return db

    @pytest.mark.asyncio
    async def test_db_initialization(self, db):
        """Test database initializes"""
        assert db.database_name == "test_db"
        assert db.pool_size == 5

    @pytest.mark.asyncio
    async def test_get_user(self, db):
        """Test get_user query"""
        mock_user = {
            "user_id": "user123",
            "guild_id": "guild456",
            "xp": 100,
            "level": 5
        }

        db.db.users = AsyncMock()
        db.db.users.find_one = AsyncMock(return_value=mock_user)

        user = await db.get_user("user123", "guild456")

        db.db.users.find_one.assert_called_once_with({
            "user_id": "user123",
            "guild_id": "guild456"
        })

    @pytest.mark.asyncio
    async def test_create_user(self, db):
        """Test create_user inserts document"""
        db.db.users = AsyncMock()
        db.db.users.insert_one = AsyncMock()

        result = await db.create_user("user123", "guild456", {"balance": 500})

        db.db.users.insert_one.assert_called_once()
        call_args = db.db.users.insert_one.call_args[0][0]
        assert call_args["user_id"] == "user123"
        assert call_args["guild_id"] == "guild456"
        assert call_args["balance"] == 500

    @pytest.mark.asyncio
    async def test_update_user(self, db):
        """Test update_user modifies document"""
        db.db.users = AsyncMock()
        mock_result = Mock()
        mock_result.modified_count = 1
        db.db.users.update_one = AsyncMock(return_value=mock_result)

        result = await db.update_user("user123", "guild456", {"xp": 200})

        assert result is True
        db.db.users.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_increment_user_field(self, db):
        """Test increment_user_field"""
        db.db.users = AsyncMock()
        mock_result = Mock()
        mock_result.modified_count = 1
        db.db.users.update_one = AsyncMock(return_value=mock_result)

        result = await db.increment_user_field("user123", "guild456", "xp", 50)

        assert result is True
        db.db.users.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_balance(self, db):
        """Test add_balance"""
        db.db.users = AsyncMock()
        mock_result = Mock()
        mock_result.modified_count = 1
        db.db.users.update_one = AsyncMock(return_value=mock_result)

        result = await db.add_balance("user123", "guild456", 100)

        assert result is True

    @pytest.mark.asyncio
    async def test_remove_balance_sufficient_funds(self, db):
        """Test remove_balance with sufficient funds"""
        db.db.users = AsyncMock()

        # Mock get_user returns user with balance
        mock_user = {"balance": 500}
        db.get_user = AsyncMock(return_value=mock_user)

        # Mock increment_user_field
        db.increment_user_field = AsyncMock(return_value=True)

        result = await db.remove_balance("user123", "guild456", 100)

        assert result is True

    @pytest.mark.asyncio
    async def test_remove_balance_insufficient_funds(self, db):
        """Test remove_balance with insufficient funds"""
        db.db.users = AsyncMock()
        mock_user = {"balance": 50}
        db.get_user = AsyncMock(return_value=mock_user)

        result = await db.remove_balance("user123", "guild456", 100)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_guild(self, db):
        """Test get_guild"""
        mock_guild = {"guild_id": "guild123", "name": "Test Server"}
        db.db.guilds = AsyncMock()
        db.db.guilds.find_one = AsyncMock(return_value=mock_guild)

        guild = await db.get_guild("guild123")

        assert guild["name"] == "Test Server"

    @pytest.mark.asyncio
    async def test_add_action(self, db):
        """Test add_action logs moderation"""
        db.db.moderation_actions = AsyncMock()
        mock_result = Mock()
        mock_result.inserted_id = "action123"
        db.db.moderation_actions.insert_one = AsyncMock(return_value=mock_result)

        action_id = await db.add_action(
            "ban",
            "user123",
            "guild456",
            "mod789",
            "Spam",
            datetime.utcnow()
        )

        assert action_id == "action123"
        db.db.moderation_actions.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_leaderboard(self, db):
        """Test get_leaderboard returns top users"""
        mock_users = [
            {"user_id": "user1", "xp": 1000},
            {"user_id": "user2", "xp": 800},
            {"user_id": "user3", "xp": 600}
        ]

        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=mock_users)

        db.db.users = AsyncMock()
        db.db.users.find = Mock(return_value=mock_cursor)
        mock_cursor.sort = Mock(return_value=mock_cursor)
        mock_cursor.limit = Mock(return_value=mock_cursor)

        leaderboard = await db.get_leaderboard("guild123", limit=3)

        assert len(leaderboard) == 3
        assert leaderboard[0]["xp"] == 1000

    @pytest.mark.asyncio
    async def test_add_member_role(self, db):
        """Test add_member_role adds role to member"""
        db.db.members = AsyncMock()
        mock_result = Mock()
        mock_result.modified_count = 1
        db.db.members.update_one = AsyncMock(return_value=mock_result)

        result = await db.add_member_role("guild123", "user456", "role789")

        assert result is True
        db.db.members.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_member_role(self, db):
        """Test remove_member_role removes role from member"""
        db.db.members = AsyncMock()
        mock_result = Mock()
        mock_result.modified_count = 1
        db.db.members.update_one = AsyncMock(return_value=mock_result)

        result = await db.remove_member_role("guild123", "user456", "role789")

        assert result is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])