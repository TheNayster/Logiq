"""
Logiq - Main Entry Point
Stoat.chat-compatible bot (Stoat-only, NO Discord)
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
import importlib
import inspect
import yaml
from dotenv import load_dotenv
from datetime import datetime
from adapters.adapter_interface import AdapterInterface
from healthcheck import start_health_check

from database.db_manager import DatabaseManager
from utils.logger import BotLogger
from utils.embeds import EmbedColor

# Load environment variables
load_dotenv()


class Logiq:
    """Custom bot class (Stoat adapter only)"""

    def __init__(self, config: dict):
        self.config = config
        self.start_time = datetime.utcnow()
        self.logger = BotLogger(config.get('logging', {}))

        db_config = config.get('database', {})
        mongodb_uri = os.getenv('MONGODB_URI', db_config.get('mongodb_uri', 'mongodb://localhost:27017'))
        database_name = db_config.get('database_name', 'Logiq')
        pool_size = db_config.get('pool_size', 10)
        self.db = DatabaseManager(mongodb_uri, database_name, pool_size)

        self.adapter: Optional[AdapterInterface] = None
        self.health_server = None

        # Load Stoat adapter (ONLY adapter - no Discord)
        try:
            mod = importlib.import_module('adapters.stoat_adapter')
            StoatAdapter = getattr(mod, 'StoatAdapter')
            self.adapter = StoatAdapter(self.config)
            self.logger.info("✅ Stoat adapter loaded")
        except (ImportError, AttributeError) as e:
            self.logger.warning(f"Stoat adapter not found: {e}")
            self.adapter = None

        self.loaded_cogs = []

    async def setup(self, token: str):
        """Setup bot and services"""
        # Start health check server
        self.health_server = start_health_check(self)

        self.logger.info("🚀 Starting Logiq (Stoat-only)...")

        try:
            await self.db.connect()
            self.logger.info("✅ Database connected")
        except Exception as e:
            self.logger.error(f"❌ Database connection failed: {e}", exc_info=True)
            sys.exit(1)

        if self.adapter:
            try:
                await self.adapter.connect(token)
                self.logger.info("✅ Connected to Stoat.chat")
            except Exception as e:
                self.logger.error(f"❌ Stoat connection failed: {e}", exc_info=True)
                sys.exit(1)
        else:
            self.logger.error("❌ No adapter available")
            sys.exit(1)

        await self.load_cogs()

    async def load_cogs(self):
        """Dynamically import cogs and call their setup(adapter, db, config)"""
        cogs_dir = Path(__file__).parent / 'cogs'
        cog_files = [f.stem for f in cogs_dir.glob('*.py') if f.stem != '__init__']

        self.logger.info(f"📦 Loading {len(cog_files)} cogs...")

        for cog in cog_files:
            try:
                module = importlib.import_module(f'cogs.{cog}')
                setup = getattr(module, 'setup', None)
                if callable(setup):
                    if inspect.iscoroutinefunction(setup):
                        cog_instance = await setup(self.adapter, self.db, self.config)
                    else:
                        cog_instance = setup(self.adapter, self.db, self.config)

                    # Register cog commands/listeners
                    if cog_instance:
                        for cmd_name, cmd_handler in cog_instance._commands.items():
                            self.adapter.add_command(cmd_name, cmd_handler)

                    self.loaded_cogs.append(cog)
                    self.logger.info(f"  ✅ {cog}")
            except Exception as e:
                self.logger.error(f"  ❌ Failed to load {cog}: {e}", exc_info=True)

        self.logger.info(f"✅ Loaded {len(self.loaded_cogs)}/{len(cog_files)} cogs")

    async def run_forever(self):
        """Keep the process alive until cancelled"""
        self.logger.info("🎮 Bot is running (Stoat)")
        await asyncio.Event().wait()

    async def close(self):
        """Cleanup when bot is shutting down"""
        self.logger.info("🛑 Shutting down bot...")
        if self.health_server:
            self.health_server.shutdown()
        try:
            await self.db.disconnect()
        except Exception:
            pass
        if self.adapter and hasattr(self.adapter, 'disconnect'):
            try:
                await self.adapter.disconnect()
            except Exception:
                pass


def load_config(config_path: str = 'config.yaml') -> dict:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config: {e}")


async def start_web_server(bot: Logiq):
    """Start web dashboard (if enabled)"""
    from web.api import create_app
    from fastapi.applications import Starlette
    import uvicorn

    config = bot.config.get('web', {})
    host = config.get('host', '0.0.0.0')
    port = config.get('port', 8000)

    app = create_app(bot)

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    """Main entry point (Stoat-only)"""
    config = load_config()

    token = os.getenv('STOAT_BOT_TOKEN', config['bot'].get('token'))
    if not token or token.startswith('${'):
        print("❌ Error: STOAT_BOT_TOKEN not set")
        print("   Set in .env: STOAT_BOT_TOKEN=your_token_here")
        sys.exit(1)

    bot = Logiq(config)

    try:
        await bot.setup(token)

        if config.get('web', {}).get('enabled', False):
            asyncio.create_task(start_web_server(bot))

        await bot.run_forever()

    except KeyboardInterrupt:
        print("\n⏸️ Bot interrupted by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await bot.close()


if __name__ == '__main__':
    asyncio.run(main())