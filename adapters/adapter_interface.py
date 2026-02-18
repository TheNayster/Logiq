from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine, Dict, List, Optional


class AdapterInterface(ABC):
    """Abstract interface for Stoat adapter"""

    @abstractmethod
    async def connect(self, token: str) -> None:
        """Connect to Stoat"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from Stoat"""
        pass

    @abstractmethod
    async def send_message(
        self,
        channel_id: str,
        content: Optional[str] = None,
        embed: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[str]:
        """Send message to channel"""
        pass

    @abstractmethod
    async def send_dm(
        self,
        user_id: str,
        content: Optional[str] = None,
        embed: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[str]:
        """Send DM to user"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected"""
        pass

    @abstractmethod
    def add_command(self, name: str, handler) -> None:
        """Register command"""
        pass

    @abstractmethod
    def on_event(self, event_name: str):
        """Register event listener"""
        pass

    @abstractmethod
    async def fetch_guild_members(self, guild_id: str) -> List[Dict[str, Any]]:
        """Fetch guild members"""
        pass

    @abstractmethod
    async def add_role(self, guild_id: str, user_id: str, role_id: str) -> bool:
        """Add role to user"""
        pass

    @abstractmethod
    async def remove_role(self, guild_id: str, user_id: str, role_id: str) -> bool:
        """Remove role from user"""
        pass

    @abstractmethod
    async def fetch_messages(
        self,
        channel_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch messages from channel"""
        pass