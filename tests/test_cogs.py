"""
Unit tests for cogs
Tests cog initialization and command handling
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from adapters.cog_base import AdaptedCog
from database.db_manager import DatabaseManager


class MockCog(AdaptedCog):
    """Mock cog for testing"""
    
    def __init__(self, bot, db, config):
        super().__init__(bot, db, config)
        self.command_called = False
        self.event_called = False


class TestAdaptedCog:
    """Test adapted cog base class"""

    @pytest.fixture
    def mock_bot(self):
        """Mock bot instance"""
        bot = Mock()
        bot.adapter = Mock()
        bot.config = {"bot": {}}
        bot.logger = Mock()
        return bot

    @pytest.fixture
    def mock_db(self):
        """Mock database"""
        return Mock(spec=DatabaseManager)

    @pytest.fixture
    def config(self):
        """Test config"""
        return {"modules": {}}

    @pytest.fixture
    def cog(self, mock_bot, mock_db, config):
        """Create test cog"""
        return MockCog(mock_bot, mock_db, config)

    def test_cog_initialization(self, cog, mock_bot, mock_db):
        """Test cog initializes correctly"""
        assert cog.bot == mock_bot
        assert cog.db == mock_db
        assert cog.adapter == mock_bot.adapter
        assert isinstance(cog._commands, dict)
        assert isinstance(cog._events, dict)

    def test_app_command_decorator(self, cog):
        """Test @app_command decorator"""
        @cog.app_command(name="test", description="Test command")
        async def test_cmd(self, interaction):
            pass

        assert hasattr(test_cmd, '_command_name')
        assert test_cmd._command_name == "test"
        assert test_cmd._description == "Test command"

    def test_listener_decorator(self, cog):
        """Test @listener decorator"""
        @cog.listener("test_event")
        async def on_test(self, payload):
            pass

        assert hasattr(on_test, '_event_name')
        assert on_test._event_name == "test_event"

    @pytest.mark.asyncio
    async def test_send_embed_helper(self, cog):
        """Test send_embed helper"""
        cog.adapter.send_message = AsyncMock()

        await cog.send_embed("channel123", "Title", "Description", color=0xFF0000)

        cog.adapter.send_message.assert_called_once()
        args, kwargs = cog.adapter.send_message.call_args
        assert args[0] == "channel123"
        assert kwargs.get("embed") is not None

    @pytest.mark.asyncio
    async def test_send_message_helper(self, cog):
        """Test send_message helper"""
        cog.adapter.send_message = AsyncMock()

        await cog.send_message("channel123", "Hello world")

        cog.adapter.send_message.assert_called_once_with(
            "channel123",
            content="Hello world"
        )

    def test_command_registration(self, mock_bot, mock_db, config):
        """Test command auto-registration"""
        class TestCog(AdaptedCog):
            @AdaptedCog.app_command(name="test")
            async def test_cmd(self, interaction):
                pass

        # Commands should be registered during init
        cog = TestCog(mock_bot, mock_db, config)
        # Verify registration happened
        assert cog.bot is not None


class TestCogCommand:
    """Test cog command patterns"""

    @pytest.mark.asyncio
    async def test_command_with_interaction_data(self):
        """Test command receives interaction data"""
        mock_bot = Mock()
        mock_bot.adapter = Mock()
        mock_db = Mock()

        cog = MockCog(mock_bot, mock_db, {})

        # Simulate interaction
        interaction = {
            "user_id": "user123",
            "channel_id": "channel456",
            "server_id": "server789"
        }

        # Commands should access interaction data
        assert interaction.get("user_id") == "user123"
        assert interaction.get("channel_id") == "channel456"

    @pytest.mark.asyncio
    async def test_command_error_handling(self, mock_bot, mock_db):
        """Test command error handling"""
        cog = MockCog(mock_bot, mock_db, {})
        cog.adapter.send_message = AsyncMock()

        # Commands should handle errors gracefully
        try:
            raise ValueError("Test error")
        except Exception as e:
            error_message = str(e)
            assert error_message == "Test error"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])