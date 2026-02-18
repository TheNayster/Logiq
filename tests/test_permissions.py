"""
Unit tests for Stoat permission checking (Stoat-only)
Tests Stoat permission functionality
"""

import pytest
from unittest.mock import Mock, AsyncMock
from utils.permissions import (
    is_admin,
    is_mod,
    has_role,
    is_guild_owner,
    PermissionChecker
)


class TestStoatPermissionChecks:
    """Test Stoat permission checks"""

    @pytest.mark.asyncio
    async def test_is_admin_true(self):
        """Test admin check returns True"""
        mock_db = Mock()
        mock_db.get_member = AsyncMock(return_value={"is_admin": True})

        result = await is_admin(mock_db, "guild1", "user1")
        assert result is True

    @pytest.mark.asyncio
    async def test_is_admin_false(self):
        """Test admin check returns False"""
        mock_db = Mock()
        mock_db.get_member = AsyncMock(return_value={"is_admin": False})

        result = await is_admin(mock_db, "guild1", "user1")
        assert result is False

    @pytest.mark.asyncio
    async def test_is_admin_no_member(self):
        """Test admin check with no member"""
        mock_db = Mock()
        mock_db.get_member = AsyncMock(return_value=None)

        result = await is_admin(mock_db, "guild1", "user1")
        assert result is False

    @pytest.mark.asyncio
    async def test_is_mod_true(self):
        """Test mod check returns True"""
        mock_db = Mock()
        mock_db.get_member = AsyncMock(return_value={"is_mod": True})

        result = await is_mod(mock_db, "guild1", "user1")
        assert result is True

    @pytest.mark.asyncio
    async def test_is_mod_admin_counts(self):
        """Test that admin also counts as mod"""
        mock_db = Mock()
        mock_db.get_member = AsyncMock(return_value={"is_admin": True, "is_mod": False})

        result = await is_mod(mock_db, "guild1", "user1")
        assert result is True

    @pytest.mark.asyncio
    async def test_has_role_true(self):
        """Test has_role returns True"""
        mock_db = Mock()
        mock_db.get_member = AsyncMock(return_value={"roles": ["role1", "role2"]})

        result = await has_role(mock_db, "guild1", "user1", "role1")
        assert result is True

    @pytest.mark.asyncio
    async def test_has_role_false(self):
        """Test has_role returns False"""
        mock_db = Mock()
        mock_db.get_member = AsyncMock(return_value={"roles": ["role1"]})

        result = await has_role(mock_db, "guild1", "user1", "role2")
        assert result is False

    @pytest.mark.asyncio
    async def test_is_guild_owner_true(self):
        """Test is_guild_owner returns True"""
        mock_db = Mock()
        mock_db.get_guild = AsyncMock(return_value={"owner_id": "user1"})

        result = await is_guild_owner(mock_db, "guild1", "user1")
        assert result is True

    @pytest.mark.asyncio
    async def test_is_guild_owner_false(self):
        """Test is_guild_owner returns False"""
        mock_db = Mock()
        mock_db.get_guild = AsyncMock(return_value={"owner_id": "user2"})

        result = await is_guild_owner(mock_db, "guild1", "user1")
        assert result is False


class TestPermissionChecker:
    """Test PermissionChecker class"""

    @pytest.mark.asyncio
    async def test_can_moderate_self_check(self):
        """Test can't moderate yourself"""
        mock_db = Mock()

        result, msg = await PermissionChecker.can_moderate(
            mock_db, "guild1", "user1", "user1"
        )
        assert result is False
        assert "yourself" in msg.lower()

    @pytest.mark.asyncio
    async def test_get_permission_level_owner(self):
        """Test owner has level 3"""
        mock_db = Mock()
        mock_db.get_guild = AsyncMock(return_value={"owner_id": "user1"})
        mock_db.get_member = AsyncMock(return_value={})

        level = await PermissionChecker.get_permission_level(mock_db, "guild1", "user1")
        assert level == 3

    @pytest.mark.asyncio
    async def test_get_permission_level_admin(self):
        """Test admin has level 2"""
        mock_db = Mock()
        mock_db.get_guild = AsyncMock(return_value={"owner_id": "user2"})
        mock_db.get_member = AsyncMock(return_value={"is_admin": True})

        level = await PermissionChecker.get_permission_level(mock_db, "guild1", "user1")
        assert level == 2

    @pytest.mark.asyncio
    async def test_get_permission_level_mod(self):
        """Test mod has level 1"""
        mock_db = Mock()
        mock_db.get_guild = AsyncMock(return_value={"owner_id": "user2"})
        mock_db.get_member = AsyncMock(return_value={"is_mod": True})

        level = await PermissionChecker.get_permission_level(mock_db, "guild1", "user1")
        assert level == 1

    @pytest.mark.asyncio
    async def test_get_permission_level_user(self):
        """Test regular user has level 0"""
        mock_db = Mock()
        mock_db.get_guild = AsyncMock(return_value={"owner_id": "user2"})
        mock_db.get_member = AsyncMock(return_value={})

        level = await PermissionChecker.get_permission_level(mock_db, "guild1", "user1")
        assert level == 0

    @pytest.mark.asyncio
    async def test_check_hierarchy(self):
        """Test role hierarchy check"""
        mock_db = Mock()
        mock_db.get_guild = AsyncMock(return_value={"owner_id": "user2"})

        # Admin checking regular user
        mock_db.get_member = AsyncMock(side_effect=[
            {"is_admin": True},  # executor
            {}                    # target
        ])

        result = await PermissionChecker.check_hierarchy(mock_db, "guild1", "admin1", "user1")
        assert result is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])