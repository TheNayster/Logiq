"""
Health Check Server - Stoat bot health monitoring
"""

import json
import logging
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

bot_instance = None


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP request handler for health checks"""

    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/health':
            self.handle_health_check()
        elif self.path == '/info':
            self.handle_info()
        else:
            self.send_response(404)
            self.end_headers()

    def handle_health_check(self):
        """Handle /health endpoint"""
        try:
            health_status = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "checks": {
                    "bot": self._check_bot(),
                    "database": self._check_database(),
                    "adapter": self._check_adapter(),
                    "cogs": self._check_cogs()
                }
            }

            # Determine overall health
            all_checks = health_status["checks"].values()
            if all(check["status"] == "healthy" for check in all_checks):
                health_status["status"] = "healthy"
                status_code = 200
            else:
                health_status["status"] = "degraded"
                status_code = 503

            self.send_response(status_code)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(health_status, indent=2).encode())

        except Exception as e:
            logger.error(f"Health check error: {e}")
            self.send_response(500)
            self.end_headers()

    def handle_info(self):
        """Handle /info endpoint (service info)"""
        try:
            uptime = None
            cogs_count = 0

            if bot_instance:
                if hasattr(bot_instance, 'start_time'):
                    uptime = (
                        datetime.utcnow() - bot_instance.start_time
                    ).total_seconds()
                if hasattr(bot_instance, 'loaded_cogs'):
                    cogs_count = len(bot_instance.loaded_cogs)

            info = {
                "service": "Logiq Stoat Bot",
                "version": "1.0.0",
                "environment": os.getenv("ENVIRONMENT", "development"),
                "platform": "Stoat.chat",
                "uptime_seconds": uptime,
                "cogs_loaded": cogs_count,
                "timestamp": datetime.utcnow().isoformat()
            }

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(info, indent=2).encode())

        except Exception as e:
            logger.error(f"Info check error: {e}")
            self.send_response(500)
            self.end_headers()

    def _check_bot(self) -> dict:
        """Check bot status"""
        if bot_instance and hasattr(bot_instance, 'adapter'):
            connected = bot_instance.adapter and bot_instance.adapter.is_connected()
            return {
                "status": "healthy" if connected else "unhealthy",
                "connected": connected
            }
        return {"status": "unhealthy", "error": "Bot not initialized"}

    def _check_database(self) -> dict:
        """Check database connection"""
        if bot_instance and hasattr(bot_instance, 'db'):
            connected = bot_instance.db.is_connected
            return {
                "status": "healthy" if connected else "unhealthy",
                "connected": connected
            }
        return {"status": "unhealthy", "error": "Database not initialized"}

    def _check_adapter(self) -> dict:
        """Check Stoat adapter"""
        if bot_instance and hasattr(bot_instance, 'adapter'):
            adapter_status = "healthy" if bot_instance.adapter else "unhealthy"
            return {
                "status": adapter_status,
                "adapter": "Stoat"
            }
        return {"status": "unhealthy", "error": "No adapter"}

    def _check_cogs(self) -> dict:
        """Check cogs status"""
        if bot_instance and hasattr(bot_instance, 'loaded_cogs'):
            return {
                "status": "healthy",
                "cogs_loaded": len(bot_instance.loaded_cogs)
            }
        return {"status": "unknown", "cogs_loaded": 0}

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


def start_health_check(bot):
    """Start health check HTTP server"""
    global bot_instance
    bot_instance = bot

    try:
        server = HTTPServer(('0.0.0.0', 8080), HealthCheckHandler)
        logger.info("Health check server started on :8080")
        return server
    except Exception as e:
        logger.error(f"Failed to start health check server: {e}")
        return None
