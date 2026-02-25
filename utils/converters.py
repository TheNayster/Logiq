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
    """Parse Stoat user mentions and ULIDs"""

    # Stoat ULIDs: 26 chars, Crockford base32 (digits + most uppercase letters)
    _ULID_RE = re.compile(r'^[0-9A-HJKMNP-TV-Z]{26}$')
    # Mention format: <@ULID> or legacy <@!numeric>
    _MENTION_RE = re.compile(r'<@!?([0-9A-HJKMNP-TV-Z]{26}|\d+)>')

    @staticmethod
    def parse_user_id(value: Optional[str]) -> Optional[str]:
        """
        Extract a valid Stoat user ID from:
          - <@01KHXXX...> mention format
          - a raw ULID string
        Returns None if the value is not a valid mention or ULID.
        """
        if not value:
            return None
        # Try mention format first
        match = UserConverter._MENTION_RE.match(value.strip())
        if match:
            return match.group(1)
        # Try raw ULID
        if UserConverter._ULID_RE.match(value.strip()):
            return value.strip()
        return None
