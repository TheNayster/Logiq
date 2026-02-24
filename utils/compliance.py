"""
Stoat/Revolt Acceptable Use Policy (AUP) Compliance Module
============================================================
Implements all requirements from:
  - https://stoat.chat/legal/community-guidelines
  - https://support.revolt.chat/kb/safety/discover-guidelines
  - https://revolt.chat/aup

Key rules enforced here:
  1. No PII scraping without explicit user consent
  2. No automated activity on user accounts
  3. Rate limiting — must not abuse API / cause DoS
  4. No content that violates AUP (hate speech, CSAM, etc.)
  5. Accurate bot description — no misleading claims
  6. Moderation responsibility — must act on reported violations
"""

import re
import logging
import time
from collections import defaultdict, deque
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. CONTENT FILTER — AUP §Prohibited Content
# ---------------------------------------------------------------------------
# Covers: hate speech, slurs, CSAM indicators, self-harm promotion,
# extremist content, doxxing attempts, spam/phishing patterns.
# This is a first-pass filter; AI automod adds a second layer.

_PROHIBITED_PATTERNS = [
    # Hate speech / slurs (common forms — extend as needed)
    r'\bn[i1]gg[ae3]r\b', r'\bf[a@]gg[o0]t\b', r'\bch[i1]nk\b',
    r'\bsp[i1]c\b', r'\bk[i1]ke\b', r'\btr[a@]nny\b',
    # Doxxing / PII solicitation
    r'\b(home\s*address|phone\s*number|social\s*security|ssn|dox(x)?ing)\b',
    # CSAM indicators
    r'\b(cp|c\.p\.|child\s*porn|loli\s*porn|shota\s*porn)\b',
    # Phishing / scam patterns
    r'(discord\s*nitro\s*free|free\s*robux|claim\s*your\s*prize)',
    # Self-harm promotion
    r'\b(how\s*to\s*(kill\s*yourself|commit\s*suicide))\b',
    # Mass-ping / raid indicators
    r'@everyone.*@everyone',
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _PROHIBITED_PATTERNS]


def check_content_aup(content: str) -> Optional[str]:
    """
    Returns a violation reason string if content breaches AUP, else None.
    Call before sending or acting on any user-generated content.
    """
    if not content:
        return None
    for pattern in _COMPILED_PATTERNS:
        if pattern.search(content):
            return f"AUP violation detected: prohibited content pattern matched"
    # Excessive mention spam (>5 unique mentions = potential raid tool abuse)
    mention_count = len(re.findall(r'<@!?[0-9A-Z]+>', content))
    if mention_count > 5:
        return f"AUP violation: excessive mentions ({mention_count}) — potential spam/raid"
    return None


# ---------------------------------------------------------------------------
# 2. RATE LIMITER — AUP §No DoS / Reasonable API Usage
# ---------------------------------------------------------------------------
# Stoat's API has per-route rate limits. We must not hammer them.
# This in-process limiter enforces a conservative per-user, per-command limit
# on top of the adapter's HTTP calls, preventing bots from being used as
# DoS amplifiers against the Stoat API.

class RateLimiter:
    """
    Sliding-window rate limiter.
    Default: 5 commands per 60 seconds per user (matches constants.py RATE_LIMITS).
    """

    def __init__(self, rate: int = 5, per: int = 60):
        self.rate = rate          # max calls
        self.per = per            # window in seconds
        self._windows: Dict[str, deque] = defaultdict(deque)

    def is_allowed(self, key: str) -> bool:
        """Returns True if the action is within rate limit, False if exceeded."""
        now = time.monotonic()
        window = self._windows[key]

        # Evict timestamps outside the window
        while window and window[0] < now - self.per:
            window.popleft()

        if len(window) >= self.rate:
            return False

        window.append(now)
        return True

    def time_until_reset(self, key: str) -> float:
        """Seconds until the oldest entry in the window expires."""
        window = self._windows[key]
        if not window:
            return 0.0
        now = time.monotonic()
        return max(0.0, (window[0] + self.per) - now)


# Shared instances — import these in the adapter and cogs
command_limiter = RateLimiter(rate=5, per=60)    # 5 cmds / 60s per user
message_limiter = RateLimiter(rate=10, per=10)   # 10 msgs / 10s per user (anti-spam)
api_limiter = RateLimiter(rate=50, per=10)       # 50 API calls / 10s globally


# ---------------------------------------------------------------------------
# 3. PII GUARD — AUP §Non-Consensual PII Gathering
# ---------------------------------------------------------------------------
# The bot must NOT scrape, store, or forward PII without consent.
# Patterns below detect when user input looks like it's submitting PII that
# the bot should NOT be processing or logging.

_PII_PATTERNS = [
    r'\b\d{3}-\d{2}-\d{4}\b',              # SSN
    r'\b\d{16}\b',                          # Credit card (16 digits)
    r'\b[A-Z]{2}\d{6}[A-Z]\b',             # Passport number (common format)
    r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',  # IP address (log but don't store)
    r'[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}',      # Email address
    r'\b\d{10,11}\b',                       # Phone number (10-11 digits)
]

_COMPILED_PII = [re.compile(p) for p in _PII_PATTERNS]


def contains_pii(text: str) -> bool:
    """Returns True if text appears to contain PII that should not be stored."""
    for pattern in _COMPILED_PII:
        if pattern.search(text):
            return True
    return False


def redact_pii(text: str) -> str:
    """Replaces detected PII with [REDACTED] for safe logging."""
    for pattern in _COMPILED_PII:
        text = pattern.sub('[REDACTED]', text)
    return text


# ---------------------------------------------------------------------------
# 4. DISCOVER LISTING REQUIREMENTS
# ---------------------------------------------------------------------------
# From https://support.revolt.chat/kb/safety/discover-guidelines:
#   - Bot must not be listed solely to promote an external service
#   - Bot must enforce AUP within servers it operates in
#   - Bot must respond to moderation reports within a reasonable timeframe
#   - Bot profile must accurately describe what it does (no false advertising)

DISCOVER_REQUIREMENTS = {
    "display_name": "StoatMod",
    "description": (
        "StoatMod is a community moderation and management bot for Stoat.chat. "
        "Features include: automated moderation, custom commands, XP leveling, "
        "welcome messages, audit logs, tickets, and giveaways. "
        "All data handling complies with Stoat's Acceptable Use Policy."
    ),
    "tags": ["moderation", "automod", "leveling", "utility", "stoat", "bot"],
    "support_server": None,   # Set to your rvlt.gg invite once created
    "website": "https://stoatmod.vercel.app",
}


# ---------------------------------------------------------------------------
# 5. BOT BEHAVIOUR CHECKLIST (enforced in code, documented here)
# ---------------------------------------------------------------------------
# ✅ Bot never responds to its own messages (adapter.py:327)
# ✅ Bot only operates on explicit user commands (not automated user-account actions)
# ✅ Bot does not scrape member lists for PII (fetch_guild_members is mod-only)
# ✅ Bot rate-limits itself (command_limiter above)
# ✅ Bot logs mod actions to DB audit trail (moderation.py)
# ✅ Bot does not artificially inflate server metrics
# ✅ Bot description is accurate — no false claims about server counts
# ✅ Bot does not distribute or link to malware/phishing
# ✅ AI features (ai_chat, automod) operate on content only — no PII retention
# ✅ Social alerts only monitor public platform APIs — no scraping DMs/profiles

AUP_VERSION = "2025-02-23"
AUP_URL = "https://stoat.chat/legal/community-guidelines"
