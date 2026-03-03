"""
REST API for Logiq (Stoat-only)
Exposes read-only endpoints consumed by the stoatmod.vercel.app website,
plus authenticated dashboard read/write endpoints secured by signed tokens.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import database.supabase as supa
from database.server_config import get_server_config, save_server_config
from utils.dashboard_auth import verify_dashboard_token

logger = logging.getLogger(__name__)


def create_app(bot) -> FastAPI:
    """Create FastAPI application"""

    app = FastAPI(
        title="Logiq API",
        description="REST API for Logiq Stoat Bot",
        version="1.0.0"
    )

    # Allow the production website and any local dev origin.
    default_origins = [
        "https://stoatmod.vercel.app",
        "http://localhost:3000",
        "http://localhost:8080",
    ]
    cors_origins = bot.config.get('web', {}).get(
        'cors_origins', default_origins
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # ── Token helper ──────────────────────────────────────────────────────────

    def _require_token(t: str) -> Dict[str, Any]:
        """Validate dashboard token; raise 401/403 on failure."""
        if not t:
            raise HTTPException(status_code=401, detail="Missing token")
        try:
            return verify_dashboard_token(t)
        except ValueError as e:
            raise HTTPException(status_code=403, detail=str(e))

    # ── Public read-only endpoints ────────────────────────────────────────────

    @app.get("/")
    async def root():
        """Service info"""
        return {
            "service": "Logiq Stoat Bot API",
            "version": "1.0.0",
            "platform": "Stoat.chat",
            "docs": "/docs",
        }

    @app.get("/health")
    async def health():
        """Health check — mirrors the health server response for single-port deployments"""
        connected = bool(
            bot.adapter and hasattr(bot.adapter, 'is_connected') and bot.adapter.is_connected()
        )
        cogs_loaded = len(getattr(bot, 'loaded_cogs', []))
        overall = "healthy" if connected else "degraded"
        return {
            "status": overall,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "bot":     {"status": "healthy" if connected else "unhealthy", "connected": connected},
                "adapter": {"status": "healthy" if bot.adapter else "unhealthy", "adapter": "Stoat"},
                "cogs":    {"status": "healthy", "cogs_loaded": cogs_loaded},
                "database": {"status": "healthy"},   # Supabase – checked at startup
            }
        }

    @app.get("/info")
    async def info():
        """Bot metadata — consumed by the website status page"""
        uptime = None
        if hasattr(bot, 'start_time'):
            uptime = (datetime.utcnow() - bot.start_time).total_seconds()
        return {
            "service": "Logiq Stoat Bot",
            "version": "1.0.0",
            "platform": "Stoat.chat",
            "environment": os.getenv("ENVIRONMENT", "production"),
            "uptime_seconds": uptime,
            "cogs_loaded": len(getattr(bot, 'loaded_cogs', [])),
            "timestamp": datetime.utcnow().isoformat(),
        }

    @app.get("/stats")
    async def get_stats():
        """High-level stats (no sensitive data)"""
        uptime_str = "Unknown"
        if hasattr(bot, 'start_time'):
            delta = datetime.utcnow() - bot.start_time
            uptime_str = str(delta).split('.')[0]
        return {
            "platform": "Stoat.chat",
            "uptime": uptime_str,
            "cogs_loaded": len(getattr(bot, 'loaded_cogs', [])),
        }

    # ── Dashboard endpoints (token-protected) ─────────────────────────────────

    @app.get("/dashboard/config")
    async def get_dashboard_config(t: str = Query(default="")):
        """
        Return server config for the dashboard.
        Requires a valid signed token in the `t` query parameter.
        """
        payload = _require_token(t)
        server_id = payload["server_id"]

        try:
            sb = await supa.get_client()
            config = await get_server_config(sb, server_id)
        except Exception as e:
            logger.error(f"[dashboard/config GET] {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to load server config")

        return {
            "ok": True,
            "server_id": server_id,
            "config": config or {},
        }

    class ConfigSaveRequest(BaseModel):
        config: Dict[str, Any]

    @app.post("/dashboard/config")
    async def post_dashboard_config(
        body: ConfigSaveRequest,
        t: str = Query(default=""),
    ):
        """
        Save server config from the dashboard.
        Requires a valid signed token in the `t` query parameter.
        Only fields in the server_config allowlist are persisted.
        """
        payload = _require_token(t)
        server_id = payload["server_id"]

        try:
            sb = await supa.get_client()
            success = await save_server_config(sb, server_id, body.config)
        except Exception as e:
            logger.error(f"[dashboard/config POST] {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to save server config")

        if not success:
            raise HTTPException(status_code=400, detail="No valid fields to save")

        return {"ok": True, "server_id": server_id, "message": "Config saved"}

    return app
