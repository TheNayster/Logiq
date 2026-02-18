"""
AI Chat Cog for Logiq (Stoat-only)
AI-powered chatbot
"""

import logging
from typing import Dict, List, Optional, Any
import aiohttp

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedFactory, EmbedColor
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class AIChat(AdaptedCog):
    """AI chat cog (Stoat-only)"""

    def __init__(self, adapter, db: DatabaseManager, config: dict):
        super().__init__(adapter, db, config)
        self.module_config = config.get('modules', {}).get('ai_chat', {})
        self.provider = self.module_config.get('provider', 'openai')
        self.model = self.module_config.get('model', 'gpt-3.5-turbo')
        self.conversation_history: Dict[str, List[Dict]] = {}
        self.max_history = 10

    async def call_openai(self, messages: List[Dict], max_tokens: int = 500) -> Optional[str]:
        """Call OpenAI API"""
        try:
            import os
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return "AI not configured"

            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }

                data = {
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.7
                }

                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    json=data,
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result['choices'][0]['message']['content']
                    return None

        except Exception as e:
            logger.error(f"OpenAI call error: {e}")
            return None

    @app_command(name="ask", description="Ask AI a question")
    async def ask(self, interaction: Dict[str, Any], question: str):
        """Ask AI a question"""
        channel_id = interaction.get("channel_id")
        user_id = interaction.get("user_id")

        try:
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []

            self.conversation_history[user_id].append({
                "role": "user",
                "content": question
            })

            # Trim history
            self.conversation_history[user_id] = self.conversation_history[user_id][-self.max_history:]

            messages = [
                {
                    "role": "system",
                    "content": "You are Logiq, a helpful AI assistant for Stoat communities."
                }
            ] + self.conversation_history[user_id]

            response = await self.call_openai(messages, max_tokens=500)

            if response:
                self.conversation_history[user_id].append({
                    "role": "assistant",
                    "content": response
                })

                embed = {
                    "title": "🤖 AI Assistant",
                    "description": response[:2000],
                    "color": EmbedColor.INFO
                }

                await self.send_message(channel_id, embed=embed)
            else:
                await self.send_embed(
                    channel_id,
                    "Error",
                    "Could not get AI response",
                    color=EmbedColor.ERROR
                )

        except Exception as e:
            logger.error(f"Ask error: {e}")
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)

    @app_command(name="clear-conversation", description="Clear AI conversation history")
    async def clear_conversation(self, interaction: Dict[str, Any]):
        """Clear conversation"""
        channel_id = interaction.get("channel_id")
        user_id = interaction.get("user_id")

        if user_id in self.conversation_history:
            del self.conversation_history[user_id]

        await self.send_embed(
            channel_id,
            "✅ Cleared",
            "Conversation history cleared",
            color=EmbedColor.SUCCESS
        )


async def setup(adapter, db, config):
    """Setup function for cog loading"""
    return AIChat(adapter, db, config)
