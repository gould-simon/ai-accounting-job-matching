#!/usr/bin/env python3
"""Minimal synchronous bot for debugging."""
import logging
import os
from dotenv import load_dotenv
import telebot

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
logger.info(f"Using token: {TOKEN[:8]}...")

# Initialize bot
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Handle /start command."""
    logger.info(f"Received /start from user {message.from_user.id}")
    bot.reply_to(message, "Hi! I'm a test bot.")

if __name__ == '__main__':
    logger.info("Starting bot...")
    bot.infinity_polling()
