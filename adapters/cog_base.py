"""
Adapted Cog Base - Stoat-only cog pattern
(NO Discord.py inheritance)
"""

import logging
from typing import Dict, Any, Optional, Callable, List
from abc import ABC

logger = logging.getLogger(__name__)


class AdaptedCog(ABC):
    """Base class for Stoat-only cogs"""

    def __init__(self, adapter, db, config: Dict[str, Any]):
        self.adapter = adapter
        self.db = db
        self.config = config
        self._commands: Dict[str, Callable] = {}
        self._listeners: Dict[str, List[Callable]] = {}

    def add_command(self, name: str, handler: Callable) -> None:
        """Register command handler"""
        self._commands[name.lower()] = handler
        logger.debug(f"Command registered: {name}")

    def on_event(self, event_name: str):
        """Register event listener decorator"""
        def decorator(handler):
            if event_name not in self._listeners:
                self._listeners[event_name] = []
            self._listeners[event_name].append(handler)
            logger.debug(f"Event listener registered: {event_name}")
            return handler
        return decorator

    async def send_message(
        self,
        channel_id: str,
        content: Optional[str] = None,
        embed: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[str]:
        """Send message via adapter"""
        return await self.adapter.send_message(channel_id, content, embed, **kwargs)

    async def send_embed(
        self,
        channel_id: str,
        title: str = "",
        description: str = "",
        color: int = 0x2F3136,
        **kwargs
    ) -> Optional[str]:
        """Send message with embed"""
        embed = {
            "title": title,
            "description": description,
            "color": color
        }
        if "fields" in kwargs:
            embed["fields"] = kwargs["fields"]
        return await self.send_message(channel_id, embed=embed)


def app_command(name: str, description: str = ""):
    """Decorator for application commands (Stoat-only)"""
    def decorator(func):
        func._command_name = name
        func._description = description
        return func
    return decorator


def listener(event_name: str):
    """Decorator for event listeners (Stoat-only)"""
    def decorator(func):
        func._event_name = event_name
        return func
    return decorator