"""Telegram bot implementation."""
import logging
from typing import Any, Dict, List, Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.core.config import settings
from app.core.exceptions import BotError
from app.services.job_matching import JobMatchingService
from app.services.manager import service_manager

logger = logging.getLogger(__name__)


class Bot:
    """Telegram bot implementation."""

    def __init__(self) -> None:
        """Initialize bot."""
        self.application: Optional[Application] = None
        self.job_matching_service: Optional[JobMatchingService] = None

    async def initialize(self) -> None:
        """Initialize bot and services."""
        try:
            # Create application
            self.application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
            
            # Get services
            service = service_manager.get_service(JobMatchingService)
            if not service:
                raise BotError("JobMatchingService not initialized")
            self.job_matching_service = service
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(CommandHandler("search", self.search_command))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            logger.info("Bot initialized")
            
        except Exception as e:
            logger.error("Failed to initialize bot", exc_info=e)
            raise BotError("Failed to initialize bot") from e

    async def run_polling(self) -> None:
        """Start bot in polling mode."""
        if not self.application:
            raise BotError("Bot not initialized")
            
        try:
            await self.application.initialize()
            await self.application.start()
            await self.application.run_polling()
            
        except Exception as e:
            logger.error("Error running bot", exc_info=e)
            raise BotError("Error running bot") from e
            
        finally:
            if self.application.running:
                await self.application.stop()

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        try:
            await update.message.reply_text(
                "👋 Welcome to the AI Accounting Job Matching Bot!\n\n"
                "I can help you find accounting jobs that match your skills and experience.\n\n"
                "To get started:\n"
                "1. Send me your CV as text\n"
                "2. Use /search to find matching jobs\n"
                "3. Use /help to see all available commands"
            )
        except Exception as e:
            logger.error("Error in start command", exc_info=e)
            await self._handle_error(update, "Failed to process start command")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        try:
            await update.message.reply_text(
                "Available commands:\n\n"
                "/start - Start the bot\n"
                "/help - Show this help message\n"
                "/search - Search for jobs matching your CV\n\n"
                "You can also send me your CV as text and I'll help you find matching jobs!"
            )
        except Exception as e:
            logger.error("Error in help command", exc_info=e)
            await self._handle_error(update, "Failed to process help command")

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /search command."""
        if not self.job_matching_service:
            await self._handle_error(update, "Job matching service not available")
            return
            
        try:
            # Get user's CV
            user = await self.job_matching_service.user_repo.get_by_telegram_id(
                update.effective_user.id
            )
            
            if not user or not user.cv_text:
                await update.message.reply_text(
                    "Please send me your CV first so I can find matching jobs for you!"
                )
                return
                
            # Search for jobs
            jobs = await self.job_matching_service.find_matching_jobs(
                user.cv_text,
                min_similarity=settings.MIN_SIMILARITY_SCORE,
                limit=settings.MAX_JOBS_PER_SEARCH
            )
            
            if not jobs:
                await update.message.reply_text(
                    "I couldn't find any matching jobs at the moment. "
                    "Please try again later or update your CV with more details."
                )
                return
                
            # Format results
            response = "Here are some jobs that match your profile:\n\n"
            for job, score in jobs:
                response += (
                    f"🎯 {job.title}\n"
                    f"📍 {job.location}\n"
                    f"💼 {job.company}\n"
                    f"Match: {score:.0%}\n\n"
                )
                
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error("Error in search command", exc_info=e)
            await self._handle_error(update, "Failed to search for jobs")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming messages."""
        if not self.job_matching_service:
            await self._handle_error(update, "Job matching service not available")
            return
            
        try:
            # Save CV text
            cv_text = update.message.text
            await self.job_matching_service.user_repo.update_cv(
                update.effective_user.id,
                cv_text
            )
            
            await update.message.reply_text(
                "Thanks! I've saved your CV. Use /search to find matching jobs!"
            )
            
        except Exception as e:
            logger.error("Error handling message", exc_info=e)
            await self._handle_error(update, "Failed to process your CV")

    async def _handle_error(self, update: Update, message: str) -> None:
        """Handle errors in bot commands."""
        try:
            await update.message.reply_text(
                f"❌ {message}\n\n"
                "Please try again later or contact support if the problem persists."
            )
        except Exception as e:
            logger.error("Error sending error message", exc_info=e)


# Global bot instance
bot = Bot()
