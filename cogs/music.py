"""
Music Cog for Logiq (Stoat-only - Text-based queue)
YouTube music queue without voice channels
"""

import logging
from typing import Dict, Any, List, Optional

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedFactory, EmbedColor
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class MusicQueue:
    """Text-based music queue (no voice)"""

    def __init__(self, guild_id: str):
        self.guild_id = guild_id
        self.queue: List[Dict[str, Any]] = []
        self.current = None
        self.paused = False

    def add(self, track: Dict[str, Any]):
        """Add track to queue"""
        self.queue.append(track)

    def remove(self, index: int):
        """Remove track from queue"""
        if 0 <= index < len(self.queue):
            self.queue.pop(index)

    def clear(self):
        """Clear queue"""
        self.queue.clear()

    def get_queue_embed(self, limit: int = 10) -> Dict[str, Any]:
        """Get queue as embed"""
        embed = {
            "title": "🎵 Music Queue",
            "description": f"**Current:** {self.current.get('title', 'None')}" if self.current else "**Current:** None",
            "fields": []
        }

        for i, track in enumerate(self.queue[:limit], 1):
            embed["fields"].append({
                "name": f"{i}. {track.get('title', 'Unknown')}",
                "value": f"Duration: {track.get('duration', 'Unknown')}",
                "inline": False
            })

        if len(self.queue) > limit:
            embed["fields"].append({
                "name": "...",
                "value": f"+{len(self.queue) - limit} more tracks",
                "inline": False
            })

        return embed


class Music(AdaptedCog):
    """Music system cog (Stoat - text-only queue)"""

    def __init__(self, adapter, db: DatabaseManager, config: dict):
        super().__init__(adapter, db, config)
        self.module_config = config.get('modules', {}).get('music', {})
        self.queues: Dict[str, MusicQueue] = {}

    def get_queue(self, guild_id: str) -> MusicQueue:
        """Get or create queue for guild"""
        if guild_id not in self.queues:
            self.queues[guild_id] = MusicQueue(guild_id)
        return self.queues[guild_id]

    @app_command(name="play", description="Add music to queue (YouTube URL or query)")
    async def play(self, interaction: Dict[str, Any], query: str):
        """Add track to queue"""
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        channel_id = interaction.get("channel_id")

        try:
            queue = self.get_queue(guild_id)

            # Simulate adding track (real implementation: fetch from YouTube)
            track = {
                "title": query,
                "duration": "3:45",
                "url": f"https://youtube.com/results?search_query={query}"
            }

            queue.add(track)

            embed = {
                "title": "🎵 Added to Queue",
                "description": f"**{track['title']}**\nPosition: #{len(queue.queue)}",
                "color": EmbedColor.SUCCESS
            }

            await self.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"Play error: {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)

    @app_command(name="queue", description="View music queue")
    async def queue_cmd(self, interaction: Dict[str, Any]):
        """View music queue"""
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        channel_id = interaction.get("channel_id")

        try:
            q = self.get_queue(guild_id)
            embed_data = q.get_queue_embed(limit=10)

            await self.send_message(channel_id, embed=embed_data)

        except Exception as e:
            logger.error(f"Queue command error: {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)

    @app_command(name="skip", description="Skip current track")
    async def skip(self, interaction: Dict[str, Any]):
        """Skip current track"""
        guild_id = interaction.get("server_id") or interaction.get("guild_id")
        channel_id = interaction.get("channel_id")

        try:
            queue = self.get_queue(guild_id)

            if not queue.queue:
                await self.send_embed(
                    channel_id,
                    "Queue Empty",
                    "No tracks in queue",
                    color=EmbedColor.ERROR
                )
                return

            queue.current = queue.queue.pop(0)

            embed = {
                "title": "⏭️ Skipped",
                "description": f"Now playing: **{queue.current.get('title', 'Unknown')}**",
                "color": EmbedColor.SUCCESS
            }

            await self.send_message(channel_id, embed=embed)

        except Exception as e:
            logger.error(f"Skip error: {e}", exc_info=True)
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)


async def setup(adapter, db, config):
    """Setup function for cog loading"""
    return Music(adapter, db, config)
