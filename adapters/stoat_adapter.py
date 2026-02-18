"""
Stoat Adapter - Core implementation for Stoat.chat platform
Handles all Stoat-specific API calls and WebSocket connections
"""

import logging
import aiohttp
import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

from adapters.adapter_interface import AdapterInterface

logger = logging.getLogger(__name__)


class StoatAdapter(AdapterInterface):
    """Adapter for Stoat.chat API (Stoat-only)"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Stoat adapter"""
        self.config = config
        self.stoat_config = config.get('stoat', {})
        self.api_base = self.stoat_config.get('api_base', 'https://stoat.chat/api')
        self.ws_url = self.stoat_config.get('ws_url', 'wss://stoat.chat/socket')
        self.timeout = self.stoat_config.get('timeout', 30)

        self.session: Optional[aiohttp.ClientSession] = None
        self.token: Optional[str] = None
        self._connected = False
        self._commands: Dict[str, Callable] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}

        logger.info("🔧 Stoat Adapter initialized")

    async def connect(self, token: str) -> None:
        """Connect to Stoat API"""
        self.token = token
        self.session = aiohttp.ClientSession()

        try:
            # Test connection to Stoat API
            headers = {"Authorization": f"Bearer {token}"}
            async with self.session.get(
                f"{self.api_base}/auth/me",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"✅ Connected to Stoat as: {data.get('username', 'Unknown')}")
                    self._connected = True
                else:
                    raise ConnectionError(f"Stoat API returned {resp.status}")

        except Exception as e:
            logger.error(f"❌ Failed to connect to Stoat: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Stoat"""
        if self.session:
            await self.session.close()
            self._connected = False
            logger.info("Stoat adapter disconnected")

    async def send_message(
        self,
        channel_id: str,
        content: Optional[str] = None,
        embed: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[str]:
        """Send message to Stoat channel"""
        if not self._connected or not self.session:
            logger.error("Not connected to Stoat")
            return None

        try:
            payload: Dict[str, Any] = {}

            if content:
                payload["content"] = content

            if embed:
                payload["embed"] = embed

            headers = {"Authorization": f"Bearer {self.token}"}

            async with self.session.post(
                f"{self.api_base}/channels/{channel_id}/messages",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                if resp.status in (200, 201):
                    data = await resp.json()
                    msg_id = data.get('id')
                    logger.debug(f"Message sent to {channel_id}: {msg_id}")
                    return msg_id
                else:
                    error_text = await resp.text()
                    logger.error(f"Failed to send message: {resp.status} - {error_text}")
                    return None

        except Exception as e:
            logger.error(f"Send message error: {e}", exc_info=True)
            return None

    async def send_dm(
        self,
        user_id: str,
        content: Optional[str] = None,
        embed: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[str]:
        """Send DM to Stoat user"""
        if not self._connected or not self.session:
            logger.error("Not connected to Stoat")
            return None

        try:
            # Create DM channel first
            payload = {"recipient_id": user_id}
            headers = {"Authorization": f"Bearer {self.token}"}

            async with self.session.post(
                f"{self.api_base}/users/@me/channels",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                if resp.status in (200, 201):
                    dm_data = await resp.json()
                    dm_channel_id = dm_data.get('id')

                    # Send message to DM channel
                    return await self.send_message(
                        dm_channel_id,
                        content=content,
                        embed=embed,
                        **kwargs
                    )
                else:
                    logger.error(f"Failed to create DM channel: {resp.status}")
                    return None

        except Exception as e:
            logger.error(f"Send DM error: {e}")
            return None

    def is_connected(self) -> bool:
        """Check if connected to Stoat"""
        return self._connected

    def add_command(self, name: str, handler: Callable) -> None:
        """Register command handler"""
        self._commands[name.lower()] = handler
        logger.debug(f"Command registered: {name}")

    def on_event(self, event_name: str):
        """Register event listener decorator"""
        def decorator(handler):
            if event_name not in self._event_handlers:
                self._event_handlers[event_name] = []
            self._event_handlers[event_name].append(handler)
            logger.debug(f"Event listener registered: {event_name}")
            return handler
        return decorator

    async def fetch_guild_members(self, guild_id: str) -> List[Dict[str, Any]]:
        """Fetch all members of a guild"""
        if not self._connected or not self.session:
            return []

        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            members = []

            async with self.session.get(
                f"{self.api_base}/guilds/{guild_id}/members",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    members = data.get('members', [])
                    logger.debug(f"Fetched {len(members)} members from {guild_id}")
                    return members

        except Exception as e:
            logger.error(f"Fetch guild members error: {e}")
            return []

    async def add_role(self, guild_id: str, user_id: str, role_id: str) -> bool:
        """Add role to user in guild"""
        if not self._connected or not self.session:
            return False

        try:
            headers = {"Authorization": f"Bearer {self.token}"}

            async with self.session.put(
                f"{self.api_base}/guilds/{guild_id}/members/{user_id}/roles/{role_id}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                success = resp.status in (200, 204)
                if success:
                    logger.debug(f"Role {role_id} added to {user_id}")
                return success

        except Exception as e:
            logger.error(f"Add role error: {e}")
            return False

    async def remove_role(self, guild_id: str, user_id: str, role_id: str) -> bool:
        """Remove role from user"""
        if not self._connected or not self.session:
            return False

        try:
            headers = {"Authorization": f"Bearer {self.token}"}

            async with self.session.delete(
                f"{self.api_base}/guilds/{guild_id}/members/{user_id}/roles/{role_id}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                success = resp.status in (200, 204)
                if success:
                    logger.debug(f"Role {role_id} removed from {user_id}")
                return success

        except Exception as e:
            logger.error(f"Remove role error: {e}")
            return False

    async def fetch_messages(
        self,
        channel_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch messages from channel"""
        if not self._connected or not self.session:
            return []

        try:
            headers = {"Authorization": f"Bearer {self.token}"}

            async with self.session.get(
                f"{self.api_base}/channels/{channel_id}/messages",
                params={"limit": min(limit, 100)},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                if resp.status == 200:
                    messages = await resp.json()
                    logger.debug(f"Fetched {len(messages)} messages from {channel_id}")
                    return messages

        except Exception as e:
            logger.error(f"Fetch messages error: {e}")
            return []