"""Utilities package for Logiq"""

from .logger import setup_logger, BotLogger
from .embeds import EmbedFactory, EmbedColor
from .permissions import (
    is_admin, is_mod, has_role,
    is_guild_owner, PermissionChecker
)
from .converters import TimeConverter, RoleConverter, ChannelConverter, UserConverter
from .constants import *

__all__ = [
    'setup_logger',
    'BotLogger',
    'EmbedFactory',
    'EmbedColor',
    'is_admin',
    'is_mod',
    'has_role',
    'is_guild_owner',
    'PermissionChecker',
    'TimeConverter',
    'RoleConverter',
    'ChannelConverter',
    'UserConverter'
]
def setup_logger(config=None):
    """
    Backwards-compatible helper expected by utils.__init__.
    Returns the configured logger instance.
    """
    return BotLogger(config).logger