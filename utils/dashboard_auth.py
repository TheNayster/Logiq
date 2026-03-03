"""
utils/dashboard_auth.py
=======================
Signed-token helpers for the !dashboard link flow.

Tokens are HMAC-SHA256 signed, URL-safe base64 encoded, and carry:
  - server_id  : Stoat server / guild ID
  - user_id    : who requested the link
  - exp        : Unix timestamp (UTC) — hard-capped to 15 minutes

Environment variable required:
  DASHBOARD_SECRET  — arbitrary secret string (≥32 chars recommended)

Usage:
  token = generate_dashboard_token(server_id, user_id)
  payload = verify_dashboard_token(token)   # raises ValueError on failure
"""

import hashlib
import hmac
import json
import logging
import os
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Token lifetime — 15 minutes
_TOKEN_TTL_SECONDS = 15 * 60


def _get_secret() -> bytes:
    """Read DASHBOARD_SECRET from environment; raise clearly if missing."""
    secret = os.environ.get("DASHBOARD_SECRET", "").strip()
    if not secret:
        raise EnvironmentError(
            "DASHBOARD_SECRET is not set. "
            "Add it to your .env before using !dashboard link."
        )
    return secret.encode()


def _b64_encode(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64_decode(s: str) -> bytes:
    # Restore padding
    s += "=" * (-len(s) % 4)
    return urlsafe_b64decode(s)


def generate_dashboard_token(server_id: str, user_id: str) -> str:
    """
    Create a short-lived signed token for the dashboard.

    Returns a string of the form:
        <base64-payload>.<base64-signature>
    """
    secret = _get_secret()
    payload: Dict[str, Any] = {
        "server_id": server_id,
        "user_id": user_id,
        "exp": int(time.time()) + _TOKEN_TTL_SECONDS,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    payload_b64 = _b64_encode(payload_bytes)

    sig = hmac.new(secret, payload_b64.encode(), hashlib.sha256).digest()
    sig_b64 = _b64_encode(sig)

    token = f"{payload_b64}.{sig_b64}"
    logger.debug(f"[dashboard_auth] Token generated for server={server_id} user={user_id}")
    return token


def verify_dashboard_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a dashboard token.

    Returns the payload dict on success.
    Raises ValueError with a human-readable reason on failure.
    """
    secret = _get_secret()

    try:
        payload_b64, sig_b64 = token.split(".", 1)
    except ValueError:
        raise ValueError("Malformed token — expected <payload>.<signature>")

    # ── Signature verification (constant-time) ──────────────────────────────
    expected_sig = hmac.new(secret, payload_b64.encode(), hashlib.sha256).digest()
    try:
        provided_sig = _b64_decode(sig_b64)
    except Exception:
        raise ValueError("Invalid base64 in token signature")

    if not hmac.compare_digest(expected_sig, provided_sig):
        raise ValueError("Token signature is invalid")

    # ── Decode payload ──────────────────────────────────────────────────────
    try:
        payload_bytes = _b64_decode(payload_b64)
        payload: Dict[str, Any] = json.loads(payload_bytes)
    except Exception:
        raise ValueError("Could not decode token payload")

    # ── Expiry check ────────────────────────────────────────────────────────
    exp = payload.get("exp", 0)
    if int(time.time()) > exp:
        raise ValueError("Token has expired")

    required = {"server_id", "user_id", "exp"}
    if not required.issubset(payload.keys()):
        raise ValueError("Token payload is missing required fields")

    return payload
