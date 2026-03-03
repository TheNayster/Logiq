"""
REST API for Logiq (Stoat-only)
Exposes read-only endpoints consumed by the stoatmod.vercel.app website.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime


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
        allow_methods=["GET"],
        allow_headers=["*"],
    )

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

    return app
