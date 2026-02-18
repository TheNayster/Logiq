"""
Type Converters - Stoat-only utilities
"""

import re
from typing import Optional


class TimeConverter:
    """Convert time strings to seconds"""

    @staticmethod
    def parse(duration: str) -> Optional[int]:
        """Parse duration string to seconds
        
        Examples:
            "5m" -> 300
            "1h" -> 3600
            "2d" -> 172800
        """
        duration = duration.lower().strip()

        # Match pattern: number + unit
        match = re.match(r'(\d+)([smhd])', duration)
        if not match:
            return None

        amount, unit = match.groups()
        amount = int(amount)

        units = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400
        }

        return amount * units.get(unit, 0)


class RoleConverter:
    """Parse role mentions"""

    @staticmethod
    def parse_role_id(mention: str) -> Optional[str]:
        """Extract role ID from <@&123> format"""
        match = re.match(r'<@&(\d+)>', mention)
        return match.group(1) if match else None


class ChannelConverter:
    """Parse channel mentions"""

    @staticmethod
    def parse_channel_id(mention: str) -> Optional[str]:
        """Extract channel ID from <#123> format"""
        match = re.match(r'<#(\d+)>', mention)
        return match.group(1) if match else None


class UserConverter:
    """Parse user mentions"""

    @staticmethod
    def parse_user_id(mention: str) -> Optional[str]:
        """Extract user ID from <@123> format"""
        match = re.match(r'<@!?(\d+)>', mention)
        return match.group(1) if match else None
