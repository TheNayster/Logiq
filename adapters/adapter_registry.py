"""
Adapter Registry - Stoat-only adapter management
NO multi-platform support
"""

import logging
from typing import Dict, Type, Optional

from adapters.adapter_interface import AdapterInterface

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """Registry for Stoat adapters (single adapter only)"""

    _adapters: Dict[str, Type[AdapterInterface]] = {}

    @classmethod
    def register(cls, name: str, adapter_class: Type[AdapterInterface]):
        """Register adapter"""
        if name != "stoat":
            raise ValueError("Only Stoat adapter is supported")
        cls._adapters[name] = adapter_class
        logger.info(f"Registered adapter: {name}")

    @classmethod
    def get_adapter(cls, name: str = "stoat") -> Optional[Type[AdapterInterface]]:
        """Get adapter by name (Stoat only)"""
        if name != "stoat":
            raise ValueError("Only Stoat adapter is supported")
        return cls._adapters.get(name)

    @classmethod
    def list_adapters(cls):
        """List available adapters (Stoat only)"""
        return ["stoat"]  # Only Stoat


# Register Stoat adapter
try:
    from adapters.stoat_adapter import StoatAdapter
    AdapterRegistry.register("stoat", StoatAdapter)
except ImportError as e:
    logger.error(f"Failed to import StoatAdapter: {e}")