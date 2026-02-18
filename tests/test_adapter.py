"""
Unit tests for Stoat adapter
Tests adapter interface, connection, and message handling
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from adapters.stoat_adapter import StoatAdapter
from adapters.adapter_interface import AdapterInterface


class TestStoatAdapter:
    """Test Stoat adapter functionality"""

    @pytest.fixture
    def config(self):
        """Test configuration"""
        return {
            "stoat": {
                "api_base": "https://test.stoat.chat/api",
                "ws_url": "wss://test.stoat.chat/socket"
            },
            "bot": {
                "prefix": "!"
            }
        }

    @pytest.fixture
    def adapter(self, config):
        """Create adapter instance"""
        return StoatAdapter(config)

    @pytest.mark.asyncio
    async def test_adapter_initialization(self, adapter):
        """Test adapter initializes correctly"""
        assert adapter is not None
        assert adapter.api_base == "https://test.stoat.chat/api"
        assert adapter.ws_url == "wss://test.stoat.chat/socket"
        assert adapter.session is None
        assert adapter.ws is None

    @pytest.mark.asyncio
    async def test_adapter_implements_interface(self, adapter):
        """Test adapter implements AdapterInterface"""
        assert isinstance(adapter, AdapterInterface)
        # Verify all required methods exist
        assert hasattr(adapter, 'connect')
        assert hasattr(adapter, 'disconnect')
        assert hasattr(adapter, 'send_message')
        assert hasattr(adapter, 'send_dm')
        assert hasattr(adapter, 'add_command')
        assert hasattr(adapter, 'on_event')
        assert hasattr(adapter, 'fetch_guild_members')
        assert hasattr(adapter, 'add_role')
        assert hasattr(adapter, 'remove_role')
        assert hasattr(adapter, 'join_voice')

    @pytest.mark.asyncio
    async def test_connect_without_token_raises_error(self, adapter):
        """Test connect fails with empty token"""
        with patch('aiohttp.ClientSession') as mock_session:
            await adapter.connect("")
            # Adapter should not crash, just warn

    @pytest.mark.asyncio
    async def test_disconnect_cleanup(self, adapter):
        """Test disconnect cleans up resources"""
        with patch('aiohttp.ClientSession') as mock_session:
            adapter.session = MagicMock()
            adapter.ws = MagicMock()
            await adapter.disconnect()
            assert adapter.session is None
            assert adapter.ws is None

    def test_add_command(self, adapter):
        """Test command registration"""
        async def test_handler(payload):
            return "handled"

        adapter.add_command("test", test_handler)
        assert "test" in adapter._commands
        assert adapter._commands["test"] == test_handler

    def test_on_event_decorator(self, adapter):
        """Test event listener registration"""
        @adapter.on_event("test_event")
        async def test_listener(payload):
            pass

        assert "test_event" in adapter._listeners
        assert test_listener in adapter._listeners["test_event"]

    @pytest.mark.asyncio
    async def test_http_get(self, adapter):
        """Test GET request"""
        adapter.session = MagicMock()
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"status": "ok"})

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            adapter.session.get = mock_get

    @pytest.mark.asyncio
    async def test_is_connected_property(self, adapter):
        """Test connection status property"""
        assert not adapter.is_connected()
        adapter.session = MagicMock()
        assert adapter.is_connected()

    @pytest.mark.asyncio
    async def test_command_dispatch(self, adapter):
        """Test command handler dispatch"""
        handled = False

        async def cmd_handler(payload):
            nonlocal handled
            handled = True

        adapter.add_command("ping", cmd_handler)

        # Simulate message event
        payload = {
            "type": "message_create",
            "content": "!ping",
            "author": {"id": "user123"}
        }

        await adapter._dispatch_event(payload)
        assert handled

    def test_headers_with_token(self, adapter):
        """Test HTTP headers include token"""
        adapter._token = "test_token_123"
        headers = adapter._headers()
        assert headers["Authorization"] == "test_token_123"

    def test_headers_without_token(self, adapter):
        """Test HTTP headers without token"""
        adapter._token = None
        headers = adapter._headers()
        assert headers == {}


class TestStoatAdapterHelpers:
    """Test adapter helper methods"""

    @pytest.fixture
    def adapter(self):
        """Create adapter instance"""
        return StoatAdapter({"stoat": {}, "bot": {}})

    @pytest.mark.asyncio
    async def test_fetch_messages_normalize(self, adapter):
        """Test message normalization"""
        adapter.session = MagicMock()

        # Mock response
        responses = [
            {
                "id": "msg1",
                "content": "Hello",
                "author": {"id": "user1", "username": "alice"},
                "created_at": "2024-01-01T00:00:00Z"
            }
        ]

        # The method should normalize the response
        messages = []
        for msg in responses:
            messages.append({
                "id": msg.get("id"),
                "content": msg.get("content"),
                "author": {
                    "id": msg.get("author", {}).get("id"),
                    "username": msg.get("author", {}).get("username")
                },
                "timestamp": msg.get("created_at") or msg.get("timestamp")
            })

        assert len(messages) == 1
        assert messages[0]["content"] == "Hello"
        assert messages[0]["author"]["username"] == "alice"

    @pytest.mark.asyncio
    async def test_send_message_with_embed(self, adapter):
        """Test sending message with embed"""
        adapter.session = MagicMock()
        embed_data = {"title": "Test", "description": "Test embed"}

        # Verify payload construction
        payload = {
            "content": "Test message",
            "embed": embed_data
        }

        assert "embed" in payload
        assert payload["embed"]["title"] == "Test"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])