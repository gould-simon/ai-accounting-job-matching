"""Telegram bot handler for job matching service."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.core.logging import get_logger
from app.repositories.cv import CVRepository
from app.repositories.job import JobRepository
from app.repositories.user import UserRepository
from app.services.cv_processor import CVProcessor
from app.bot.conversations.preferences import get_preferences_handler
from app.bot.conversations.matching import get_matching_handler

logger = get_logger(__name__)

# Conversation states
(
    AWAITING_CV,
    AWAITING_LOCATION,
    AWAITING_SENIORITY,
    AWAITING_SERVICE,
    AWAITING_SEARCH_QUERY,
    AWAITING_PREFERENCE_TYPE,
    AWAITING_PREFERENCE_VALUE
) = range(7)

# Callback data
CALLBACK_NEXT_JOBS = "next_jobs"
CALLBACK_PREV_JOBS = "prev_jobs"
CALLBACK_VIEW_JOB = "view_job"
CALLBACK_APPLY_JOB = "apply_job"
CALLBACK_SAVE_JOB = "save_job"


class JobMatchingBot:
    """Telegram bot for job matching service."""

    def __init__(self, token: str) -> None:
        """Initialize bot.
        
        Args:
            token: Telegram bot token
        """
        self.application = Application.builder().token(token).build()
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Set up bot command and conversation handlers."""
        # Basic commands
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        
        # CV upload conversation
        cv_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("upload_cv", self.start_cv_upload)],
            states={
                AWAITING_CV: [
                    MessageHandler(
                        filters.Document.ALL,
                        self.process_cv
                    )
                ]
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        self.application.add_handler(cv_conv_handler)

        # Add preferences handler
        self.application.add_handler(get_preferences_handler())
        
        # Add matching handler
        self.application.add_handler(get_matching_handler())

        # Job search conversation
        search_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("search", self.start_search)],
            states={
                AWAITING_SEARCH_QUERY: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.handle_search_query
                    )
                ],
                AWAITING_LOCATION: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.handle_location
                    )
                ],
                AWAITING_SENIORITY: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.handle_seniority
                    )
                ],
                AWAITING_SERVICE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.handle_service
                    )
                ]
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        self.application.add_handler(search_conv_handler)

        # Preference management conversation
        pref_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("preferences", self.start_preferences)],
            states={
                AWAITING_PREFERENCE_TYPE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.handle_preference_type
                    )
                ],
                AWAITING_PREFERENCE_VALUE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.handle_preference_value
                    )
                ]
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        self.application.add_handler(pref_conv_handler)

        # Callback queries
        self.application.add_handler(
            CallbackQueryHandler(self.handle_callback)
        )

        # Error handler
        self.application.add_error_handler(self.error_handler)

    async def start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /start command.
        
        Args:
            update: Telegram update
            context: Callback context
        """
        try:
            # Get or create user
            user_repo = UserRepository(context.bot_data["db"])
            user = await user_repo.get_by_telegram_id(
                update.effective_user.id
            )

            if not user:
                user = await user_repo.create_user(
                    telegram_id=update.effective_user.id,
                    username=update.effective_user.username,
                    first_name=update.effective_user.first_name,
                    last_name=update.effective_user.last_name
                )

            # Welcome message
            welcome_text = (
                f"👋 Welcome {update.effective_user.first_name}!\n\n"
                "I'm your AI-powered accounting job matching assistant. "
                "I can help you:\n"
                "• Upload and analyze your CV 📄\n"
                "• Search for accounting jobs 🔍\n"
                "• Get personalized job matches ✨\n"
                "• Manage your preferences ⚙️\n\n"
                "To get started, try one of these commands:\n"
                "/upload_cv - Upload your CV\n"
                "/search - Search for jobs\n"
                "/preferences - Set your preferences\n"
                "/help - See all commands"
            )

            await update.message.reply_text(welcome_text)

        except Exception as e:
            logger.error(
                "Error in start command",
                extra={
                    "user_id": update.effective_user.id,
                    "error": str(e)
                }
            )
            await update.message.reply_text(
                "Sorry, something went wrong. Please try again later."
            )

    async def help(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /help command.
        
        Args:
            update: Telegram update
            context: Callback context
        """
        help_text = (
            "🤖 Available Commands:\n\n"
            "CV Management:\n"
            "/upload_cv - Upload your CV\n"
            "/view_cv - View your current CV\n"
            "/delete_cv - Delete your CV\n\n"
            "Job Search:\n"
            "/search - Search for jobs\n"
            "/matches - Get personalized job matches\n"
            "/saved - View saved jobs\n\n"
            "Preferences:\n"
            "/preferences - Manage your preferences\n"
            "/location - Set preferred location\n"
            "/seniority - Set experience level\n"
            "/service - Set service area\n\n"
            "Other:\n"
            "/help - Show this help message\n"
            "/cancel - Cancel current operation"
        )
        await update.message.reply_text(help_text)

    async def start_cv_upload(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Start CV upload conversation.
        
        Args:
            update: Telegram update
            context: Callback context
            
        Returns:
            Next conversation state
        """
        await update.message.reply_text(
            "Please send me your CV (PDF or DOCX format).\n"
            "I'll analyze it and help you find matching jobs.\n\n"
            "Type /cancel to cancel."
        )
        return AWAITING_CV

    async def process_cv(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Process uploaded CV document.
        
        Args:
            update: Telegram update
            context: Callback context
            
        Returns:
            Next conversation state
        """
        try:
            # Get document
            doc = update.message.document
            if not doc.mime_type in [
                "application/pdf",
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ]:
                await update.message.reply_text(
                    "❌ Sorry, I can only process PDF and DOCX files.\n"
                    "Please send a supported file format."
                )
                return AWAITING_CV

            # Download file
            file = await context.bot.get_file(doc.file_id)
            file_path = f"{settings.UPLOAD_DIR}/{doc.file_id}_{doc.file_name}"
            await file.download_to_drive(file_path)

            # Process CV
            processing_msg = await update.message.reply_text(
                "🔄 Processing your CV... This may take a minute."
            )

            cv_processor = CVProcessor(context.bot_data["db"])
            cv = await cv_processor.process_cv(
                user_id=update.effective_user.id,
                file_path=file_path,
                original_filename=doc.file_name,
                content_type=doc.mime_type,
                file_size=doc.file_size
            )

            # Send analysis results
            await processing_msg.edit_text(
                "✅ CV processed successfully!\n\n"
                f"📊 Analysis Results:\n"
                f"• Skills: {', '.join(cv.skills[:5])}{'...' if len(cv.skills) > 5 else ''}\n"
                f"• Experience: {len(cv.experiences)} positions\n"
                f"• Education: {len(cv.education)} qualifications\n\n"
                "Would you like to:\n"
                "1. /search for jobs now\n"
                "2. /preferences to set your preferences\n"
                "3. /matches to see matching jobs"
            )

            return ConversationHandler.END

        except Exception as e:
            logger.error(
                "Error processing CV",
                extra={
                    "user_id": update.effective_user.id,
                    "filename": doc.file_name,
                    "error": str(e)
                }
            )
            await update.message.reply_text(
                "❌ Sorry, I couldn't process your CV.\n"
                "Please try again or contact support if the problem persists."
            )
            return ConversationHandler.END

    async def start_search(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Start job search conversation.
        
        Args:
            update: Telegram update
            context: Callback context
            
        Returns:
            Next conversation state
        """
        await update.message.reply_text(
            "Let's find your perfect accounting job! 🔍\n\n"
            "What kind of role are you looking for?\n"
            "For example:\n"
            "• Senior Auditor in London\n"
            "• Tax Manager with 5 years experience\n"
            "• Junior Accountant KPMG\n\n"
            "Type /cancel to cancel."
        )
        return AWAITING_SEARCH_QUERY

    async def handle_search_query(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle job search query.
        
        Args:
            update: Telegram update
            context: Callback context
            
        Returns:
            Next conversation state
        """
        try:
            query = update.message.text
            context.user_data["search_query"] = query

            # Get user's preferences
            user_repo = UserRepository(context.bot_data["db"])
            user = await user_repo.get_with_preferences(
                update.effective_user.id
            )

            # Search jobs
            searching_msg = await update.message.reply_text(
                "🔍 Searching for matching jobs..."
            )

            job_repo = JobRepository(context.bot_data["db"])
            jobs = await job_repo.search_jobs(
                title=query,
                location=user.preferences.get("location"),
                seniority=user.preferences.get("seniority"),
                service=user.preferences.get("service"),
                limit=5
            )

            if not jobs:
                await searching_msg.edit_text(
                    "😕 No jobs found matching your criteria.\n\n"
                    "Try:\n"
                    "• Using different keywords\n"
                    "• Broadening your search\n"
                    "• Setting your preferences with /preferences"
                )
                return ConversationHandler.END

            # Format results
            results_text = "🎯 Here are some matching jobs:\n\n"
            keyboard = []

            for i, job in enumerate(jobs, 1):
                results_text += (
                    f"{i}. {job.job_title}\n"
                    f"📍 {job.location}\n"
                    f"💼 {job.firm.name}\n"
                    f"💰 {job.salary}\n\n"
                )
                keyboard.append([
                    InlineKeyboardButton(
                        f"View Job {i}",
                        callback_data=f"{CALLBACK_VIEW_JOB}:{job.id}"
                    )
                ])

            keyboard.append([
                InlineKeyboardButton(
                    "🔍 New Search",
                    callback_data="new_search"
                ),
                InlineKeyboardButton(
                    "⚙️ Preferences",
                    callback_data="preferences"
                )
            ])

            await searching_msg.edit_text(
                results_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

            return ConversationHandler.END

        except Exception as e:
            logger.error(
                "Error handling search query",
                extra={
                    "user_id": update.effective_user.id,
                    "query": query,
                    "error": str(e)
                }
            )
            await update.message.reply_text(
                "❌ Sorry, something went wrong with the search.\n"
                "Please try again later."
            )
            return ConversationHandler.END

    async def handle_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle callback queries from inline keyboards.
        
        Args:
            update: Telegram update
            context: Callback context
        """
        query = update.callback_query
        await query.answer()

        try:
            if query.data.startswith(CALLBACK_VIEW_JOB):
                # Get job details
                job_id = int(query.data.split(":")[1])
                job_repo = JobRepository(context.bot_data["db"])
                job = await job_repo.get_with_firm(job_id)

                if not job:
                    await query.message.edit_text(
                        "❌ Sorry, this job is no longer available."
                    )
                    return

                # Format job details
                details = (
                    f"🎯 {job.job_title}\n\n"
                    f"Company: {job.firm.name}\n"
                    f"Location: {job.location}\n"
                    f"Salary: {job.salary}\n"
                    f"Seniority: {job.seniority}\n"
                    f"Service: {job.service}\n\n"
                    f"Description:\n{job.description[:500]}...\n\n"
                    f"Requirements:\n{job.requirements[:500]}..."
                )

                keyboard = [
                    [
                        InlineKeyboardButton(
                            "🌐 Apply Online",
                            url=job.link
                        ),
                        InlineKeyboardButton(
                            "💾 Save Job",
                            callback_data=f"{CALLBACK_SAVE_JOB}:{job.id}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "◀️ Back to Results",
                            callback_data="back_to_results"
                        )
                    ]
                ]

                await query.message.edit_text(
                    details,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

            elif query.data == "new_search":
                await self.start_search(update, context)

            elif query.data == "preferences":
                await self.start_preferences(update, context)

            elif query.data == "back_to_results":
                # Re-run last search
                if "search_query" in context.user_data:
                    await self.handle_search_query(update, context)
                else:
                    await query.message.edit_text(
                        "Previous search expired. Please start a new search with /search"
                    )

        except Exception as e:
            logger.error(
                "Error handling callback query",
                extra={
                    "user_id": update.effective_user.id,
                    "callback_data": query.data,
                    "error": str(e)
                }
            )
            await query.message.edit_text(
                "❌ Sorry, something went wrong.\n"
                "Please try again later."
            )

    async def cancel(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Cancel current conversation.
        
        Args:
            update: Telegram update
            context: Callback context
            
        Returns:
            ConversationHandler.END
        """
        await update.message.reply_text(
            "Operation cancelled. What would you like to do next?\n\n"
            "/search - Search for jobs\n"
            "/upload_cv - Upload your CV\n"
            "/preferences - Set your preferences"
        )
        return ConversationHandler.END

    async def error_handler(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle errors in bot updates.
        
        Args:
            update: Telegram update
            context: Callback context
        """
        logger.error(
            "Error handling update",
            extra={
                "update": update.to_dict() if update else None,
                "error": str(context.error)
            }
        )

        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ Sorry, something went wrong.\n"
                    "Please try again later or contact support if the problem persists."
                )
        except Exception as e:
            logger.error(
                "Error sending error message",
                extra={"error": str(e)}
            )

    def run(self) -> None:
        """Run the bot."""
        self.application.run_polling()
