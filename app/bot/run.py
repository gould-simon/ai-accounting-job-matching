"""Run the Telegram bot."""
import asyncio
import logging
import signal
import sys
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from telegram.ext import Application

from app.bot.handler import JobMatchingBot
from app.core.config import settings
from app.core.logging import configure_logging
from app.database import get_db

logger = logging.getLogger(__name__)


async def init_db() -> AsyncSession:
    """Initialize database connection.
    
    Returns:
        Database session
    """
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.SQL_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW
    )
    return AsyncSession(engine)


async def shutdown(application: Application) -> None:
    """Shut down the bot gracefully.
    
    Args:
        application: Bot application
    """
    logger.info("Shutting down bot...")
    await application.stop()
    await application.shutdown()
    logger.info("Bot shutdown complete")


async def main() -> None:
    """Run the bot."""
    try:
        # Configure logging
        configure_logging()
        logger.info("Starting bot...")

        # Initialize database
        logger.info("Initializing database connection...")
        db = await init_db()

        # Create and run bot
        bot = JobMatchingBot(settings.TELEGRAM_BOT_TOKEN)
        bot.application.bot_data["db"] = db

        # Set up signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(
                    shutdown(bot.application)
                )
            )

        logger.info("Bot is ready!")
        await bot.application.initialize()
        await bot.application.start()
        await bot.application.run_polling()

    except Exception as e:
        logger.exception("Fatal error running bot")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
