"""
AI Chat Cog for Logiq (Stoat-only)
AI-powered chatbot — supports OpenAI and Anthropic providers.
"""

import logging
from typing import Dict, List, Optional, Any
import aiohttp
import os

from adapters.cog_base import AdaptedCog, app_command
from utils.embeds import EmbedFactory, EmbedColor
from utils.compliance import contains_pii, redact_pii

logger = logging.getLogger(__name__)


class AIChat(AdaptedCog):
    """AI chat cog (Stoat-only)"""

    def __init__(self, adapter, db, config: dict):
        super().__init__(adapter, db, config)
        self.module_config = config.get('modules', {}).get('ai_chat', {})
        self.provider = self.module_config.get('provider', 'openai')
        self.model_openai     = self.module_config.get('model_openai',     'gpt-3.5-turbo')
        self.model_anthropic  = self.module_config.get('model_anthropic',  'claude-haiku-4-5-20251001')
        self.conversation_history: Dict[str, List[Dict]] = {}
        self.max_history = 10

    # ── OpenAI ────────────────────────────────────────────────────────────────

    async def call_openai(self, messages: List[Dict], max_tokens: int = 500) -> Optional[str]:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return "OpenAI not configured — set OPENAI_API_KEY in .env"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type":  "application/json",
                    },
                    json={
                        "model":       self.model_openai,
                        "messages":    messages,
                        "max_tokens":  max_tokens,
                        "temperature": 0.7,
                    },
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result['choices'][0]['message']['content']
                    logger.warning(f"[openai] {resp.status}: {await resp.text()}")
                    return None
        except Exception as e:
            logger.error(f"[openai] call error: {e}")
            return None

    # ── Anthropic ─────────────────────────────────────────────────────────────

    async def call_anthropic(self, messages: List[Dict], max_tokens: int = 500) -> Optional[str]:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            return "Anthropic not configured — set ANTHROPIC_API_KEY in .env"

        # Anthropic uses a separate system field; extract it from messages if present
        system = "You are Logiq, a helpful AI assistant for Stoat communities."
        user_messages = [m for m in messages if m["role"] != "system"]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key":         api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type":      "application/json",
                    },
                    json={
                        "model":      self.model_anthropic,
                        "max_tokens": max_tokens,
                        "system":     system,
                        "messages":   user_messages,
                    },
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result['content'][0]['text']
                    logger.warning(f"[anthropic] {resp.status}: {await resp.text()}")
                    return None
        except Exception as e:
            logger.error(f"[anthropic] call error: {e}")
            return None

    # ── Commands ──────────────────────────────────────────────────────────────

    @app_command(name="ask", description="Ask AI a question")
    async def ask(self, interaction: Dict[str, Any], question: str):
        channel_id = interaction.get("channel_id")
        user_id    = interaction.get("user_id")

        try:
            if contains_pii(question):
                await self.send_embed(
                    channel_id,
                    "⚠️ Privacy Notice",
                    "Your message appears to contain personal information (email, phone, etc.). "
                    "Please don't share PII with the bot. Message not processed.",
                    color=EmbedColor.WARNING
                )
                return

            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []

            self.conversation_history[user_id].append({"role": "user", "content": question})
            self.conversation_history[user_id] = self.conversation_history[user_id][-self.max_history:]

            messages = [
                {"role": "system", "content": "You are Logiq, a helpful AI assistant for Stoat communities."}
            ] + self.conversation_history[user_id]

            if self.provider == "anthropic":
                response = await self.call_anthropic(messages, max_tokens=500)
            else:
                response = await self.call_openai(messages, max_tokens=500)

            if response:
                self.conversation_history[user_id].append({"role": "assistant", "content": response})
                await self.send_message(channel_id, embed={
                    "title":       "🤖 AI Assistant",
                    "description": response[:2000],
                    "color":       EmbedColor.INFO,
                })
            else:
                await self.send_embed(channel_id, "Error", "Could not get AI response", color=EmbedColor.ERROR)

        except Exception as e:
            logger.error(f"[ask] {e}")
            await self.send_embed(channel_id, "Error", str(e), color=EmbedColor.ERROR)

    @app_command(name="clear-conversation", description="Clear AI conversation history")
    async def clear_conversation(self, interaction: Dict[str, Any]):
        channel_id = interaction.get("channel_id")
        user_id    = interaction.get("user_id")

        self.conversation_history.pop(user_id, None)
        await self.send_embed(channel_id, "✅ Cleared", "Conversation history cleared", color=EmbedColor.SUCCESS)


async def setup(adapter, db, config):
    return AIChat(adapter, db, config)
