"""
database/supabase/client.py
===========================
Async Supabase client singleton.
Uses the service-role key so the bot bypasses RLS and has full table access.
Dashboard / user-facing calls should use the anon key with JWT from Supabase Auth.
"""

import logging
import os
from typing import Optional
from supabase import create_async_client, AsyncClient

logger = logging.getLogger(__name__)

_client: Optional[AsyncClient] = None


async def get_client() -> AsyncClient:
    """Return (and lazily create) the shared async Supabase client."""
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_KEY"]   # service-role — never expose to frontend
        _client = await create_async_client(url, key)
        logger.info("✅ Supabase async client initialised")
    return _client


async def close_client() -> None:
    """Close the client on shutdown (best-effort)."""
    global _client
    if _client is not None:
        try:
            await _client.auth.sign_out()
        except Exception:
            pass
        _client = None
        logger.info("Supabase client closed")
