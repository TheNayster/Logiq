"""
Stoat Adapter - Core implementation for Stoat.chat platform
Handles all Stoat-specific API calls and WebSocket connections
"""

import difflib
import json
import logging
import aiohttp
import asyncio
import websockets
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
        self.bot_id: Optional[str] = None
        self._channel_server_map: Dict[str, str] = {}  # channel_id -> server_id

        logger.info("🔧 Stoat Adapter initialized")

    async def connect(self, token: str) -> None:
        """Connect to Stoat API"""
        self.token = token
        self.session = aiohttp.ClientSession()

        try:
            headers = {"X-Bot-Token": token}

            async with self.session.get(
                f"{self.api_base}/users/@me",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.bot_id = data.get('_id') or data.get('id')
                    logger.info(f"✅ Connected to Stoat as: {data.get('username', 'Unknown')} (id={self.bot_id})")
                    self._connected = True
                else:
                    text = await resp.text()
                    raise ConnectionError(f"Stoat API returned {resp.status}: {text}")

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
                payload["embeds"] = [embed]

            headers = {"X-Bot-Token": self.token}

            async with self.session.post(
                f"{self.api_base}/channels/{channel_id}/messages",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                if resp.status in (200, 201):
                    data = await resp.json()
                    msg_id = data.get('_id') or data.get('id')
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
            headers = {"X-Bot-Token": self.token}

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
            headers = {"X-Bot-Token": self.token}
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
            headers = {"X-Bot-Token": self.token}

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
            headers = {"X-Bot-Token": self.token}

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

    async def listen(self) -> None:
        """Connect to the Stoat WebSocket and dispatch incoming events indefinitely.

        Authenticates immediately after connecting, then routes every Message
        event through _dispatch_message() and forwards all event types to any
        registered _event_handlers.  Reconnects automatically after any
        disconnect or error.
        """
        reconnect_delay = 5  # seconds between reconnection attempts

        while True:
            try:
                logger.info(f"🔌 Connecting to WebSocket: {self.ws_url}")
                async with websockets.connect(self.ws_url) as ws:
                    # Authenticate immediately after opening the socket
                    await ws.send(json.dumps({
                        "type": "Authenticate",
                        "token": self.token
                    }))

                    async for raw in ws:
                        try:
                            event = json.loads(raw)
                        except (json.JSONDecodeError, TypeError):
                            continue

                        event_type = event.get("type")

                        if event_type == "Authenticated":
                            logger.info("✅ WebSocket authenticated")

                        elif event_type == "Ready":
                            # Cache channel → server mapping so _dispatch_message
                            # can populate server_id / guild_id in the interaction.
                            for ch in event.get("channels", []):
                                ch_id = ch.get("_id") or ch.get("id")
                                sv_id = ch.get("server")
                                if ch_id and sv_id:
                                    self._channel_server_map[ch_id] = sv_id
                            logger.info(
                                f"✅ WebSocket ready — "
                                f"{len(self._channel_server_map)} channels cached"
                            )

                        elif event_type == "Message":
                            await self._dispatch_message(event)

                        # Forward every event type to registered listeners
                        for handler in self._event_handlers.get(event_type, []):
                            try:
                                await handler(event)
                            except Exception as e:
                                logger.error(
                                    f"Event handler error ({event_type}): {e}",
                                    exc_info=True
                                )

            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"WebSocket closed ({e}), reconnecting in {reconnect_delay}s...")
            except Exception as e:
                logger.error(f"WebSocket error: {e}, reconnecting in {reconnect_delay}s...")

            await asyncio.sleep(reconnect_delay)

    async def _dispatch_message(self, event: Dict[str, Any]) -> None:
        """Parse a Message event and route it to command handlers / on_message listeners.

        Builds an interaction dict (matching what cog handlers expect) then:
        1. Ignores messages sent by the bot itself.
        2. If the message starts with the configured prefix, extracts the command
           name and args and calls the matching registered command handler.
        3. Calls every registered 'on_message' event handler regardless.
        """
        content: str = event.get("content") or ""
        channel_id: str = event.get("channel", "")
        author_id: str = event.get("author", "")
        mentions: list = event.get("mentions") or []

        logger.info(f"📨 Message received — author={author_id} channel={channel_id} content={content!r}")

        # Never respond to the bot's own messages
        if author_id == self.bot_id:
            logger.info("   ↩ Ignoring own message")
            return

        server_id = self._channel_server_map.get(channel_id)

        interaction: Dict[str, Any] = {
            "channel_id": channel_id,
            "user_id": author_id,
            "server_id": server_id,
            "guild_id": server_id,   # alias used by some cogs
            "content": content,
            "mentions": mentions,
            "message": event,
        }

        # Route prefix-based commands
        prefix: str = self.config.get("bot", {}).get("prefix", "!")
        case_insensitive: bool = self.config.get("bot", {}).get("case_insensitive", True)

        cmp = content.lower() if case_insensitive else content
        if cmp.startswith(prefix):
            parts = content[len(prefix):].split()
            if parts:
                cmd_name = parts[0].lower() if case_insensitive else parts[0]
                interaction["command"] = cmd_name
                interaction["args"] = parts[1:]

                handler = self._commands.get(cmd_name)
                if handler:
                    logger.info(f"   ▶ Dispatching command: {cmd_name} args={parts[1:]}")
                    try:
                        await handler(interaction, *parts[1:])
                    except TypeError as e:
                        if "argument" in str(e):
                            usage = getattr(handler, '_usage', None)
                            hint = f"Usage: `{usage}`" if usage else f"Missing required arguments for `!{cmd_name}`."
                            await self.send_message(channel_id, content=hint)
                        else:
                            logger.error(
                                f"Command handler '{cmd_name}' raised: {e}",
                                exc_info=True
                            )
                    except Exception as e:
                        logger.error(
                            f"Command handler '{cmd_name}' raised: {e}",
                            exc_info=True
                        )
                else:
                    logger.info(f"   ✗ Unknown command: {cmd_name} (registered: {list(self._commands.keys())})")
                    close = difflib.get_close_matches(cmd_name, self._commands.keys(), n=1, cutoff=0.6)
                    if close:
                        await self.send_message(channel_id, content=f'Unknown command `!{cmd_name}`. Did you mean `!{close[0]}`?')
                    else:
                        await self.send_message(channel_id, content=f'Unknown command `!{cmd_name}`.')

        # Notify on_message listeners (e.g. leveling cog)
        for handler in self._event_handlers.get("on_message", []):
            try:
                await handler(interaction)
            except Exception as e:
                logger.error(f"on_message handler error: {e}", exc_info=True)

    async def fetch_messages(
        self,
        channel_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch messages from channel"""
        if not self._connected or not self.session:
            return []

        try:
            headers = {"X-Bot-Token": self.token}

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