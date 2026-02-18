"""
REST API for Logiq (Stoat-only)
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

    cors_origins = bot.config.get('web', {}).get('cors_origins', ['http://localhost:3000'])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": "Logiq Stoat Bot API",
            "version": "1.0.0",
            "platform": "Stoat.chat"
        }

    @app.get("/stats")
    async def get_stats():
        """Get bot statistics"""
        guilds_count = await bot.db.db.guilds.count_documents({})
        users_count = await bot.db.db.users.count_documents({})

        return {
            "guilds": guilds_count,
            "users": users_count,
            "platform": "Stoat.chat",
            "uptime": str(datetime.utcnow() - bot.start_time).split('.')[0] if hasattr(bot, 'start_time') else "Unknown",
        }

    @app.get("/guilds")
    async def get_guilds():
        """Get list of guilds"""
        guilds = await bot.db.db.guilds.find({}).to_list(length=100)
        return {"guilds": [dict(g) for g in guilds], "count": len(guilds)}

    @app.get("/health")
    async def health():
        """Health check endpoint"""
        return {"status": "healthy", "platform": "Stoat.chat"}

    return app
