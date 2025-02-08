"""Run Telegram bot in polling mode for development."""
import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.core.logging import setup_logging
from app.database import init_db, close_db
from app.services.manager import service_manager
from app.telegram_bot import bot

logger = logging.getLogger(__name__)


async def init_services() -> None:
    """Initialize all required services."""
    try:
        # Initialize database first
        logger.info("Initializing database")
        await init_db()
        
        # Initialize all services
        logger.info("Initializing services")
        await service_manager.init_services()
        
    except Exception as e:
        logger.error("Failed to initialize services", exc_info=True)
        raise


async def cleanup_services() -> None:
    """Cleanup all services."""
    try:
        logger.info("Cleaning up services")
        await service_manager.close_services()
        await close_db()
        
    except Exception as e:
        logger.error("Error during cleanup", exc_info=True)
        raise


async def main() -> None:
    """Run the bot."""
    try:
        # Set up logging
        setup_logging()
        
        # Initialize services
        await init_services()
        
        # Set up signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(cleanup_services()))
        
        # Start bot
        logger.info("Starting bot")
        await bot.initialize()
        await bot.run_polling()
        
    except Exception as e:
        logger.error("Bot crashed", exc_info=True)
        raise
        
    finally:
        await cleanup_services()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error("Bot failed", exc_info=True)
        sys.exit(1)
