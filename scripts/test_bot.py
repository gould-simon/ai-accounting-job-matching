#!/usr/bin/env python3
"""Test bot to verify Telegram connectivity."""
import asyncio
import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
token = os.getenv("TELEGRAM_BOT_TOKEN")
logger.info(f"Using bot token: {token[:8]}...")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    logger.info("Received /start command")
    await update.message.reply_text('Hi! I am a test bot.')

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates."""
    logger.error("Exception while handling an update:", exc_info=context.error)

async def main() -> None:
    """Start the bot."""
    try:
        # Create the Application
        logger.info("Creating application...")
        application = Application.builder().token(token).build()

        # Add handlers
        logger.info("Adding handlers...")
        application.add_handler(CommandHandler("start", start_command))
        application.add_error_handler(error_handler)

        # Start the bot
        logger.info("Starting bot...")
        await application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error("Error running bot:", exc_info=e)
        raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error("Fatal error:", exc_info=e)
