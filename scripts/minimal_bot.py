#!/usr/bin/env python3
"""Minimal bot for debugging."""
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
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    logger.info(f"Received /start from user {user.id}")
    await update.message.reply_text(f'Hi {user.first_name}!')

async def main():
    """Run bot."""
    # Log the token we're using
    logger.info(f"Using token: {TOKEN[:8]}...")
    
    # Create application and add handlers
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    # Start polling
    logger.info("Starting polling...")
    await app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
