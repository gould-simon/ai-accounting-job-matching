"""Telegram bot conversation handlers for job matching."""
import logging
from typing import Dict, List, Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters
)

from app.core.config import settings
from app.repositories.cv import CVRepository
from app.repositories.job import JobRepository
from app.services.vector_search import VectorSearchService

logger = logging.getLogger(__name__)

# Conversation states
(
    AWAITING_MATCH_TYPE,
    SHOWING_MATCHES,
    VIEWING_JOB
) = range(3)

# Page size for job listings
PAGE_SIZE = 5


async def start_matching(update: Update, context: CallbackContext) -> int:
    """Start job matching conversation.
    
    Args:
        update: Telegram update
        context: Callback context
        
    Returns:
        Next conversation state
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "Find Jobs Matching My CV",
                callback_data="cv_match"
            )
        ],
        [
            InlineKeyboardButton(
                "Search Jobs",
                callback_data="search"
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "How would you like to find jobs?",
        reply_markup=reply_markup
    )
    
    return AWAITING_MATCH_TYPE


async def handle_cv_match(update: Update, context: CallbackContext) -> int:
    """Handle CV-based job matching.
    
    Args:
        update: Telegram update
        context: Callback context
        
    Returns:
        Next conversation state
    """
    cv_repo = CVRepository(context.db_session)
    cv = await cv_repo.get_latest_cv(update.effective_user.id)
    
    if not cv:
        await update.callback_query.message.reply_text(
            "You haven't uploaded a CV yet! Use /upload_cv to upload one."
        )
        return ConversationHandler.END
        
    if cv.status != "processed":
        await update.callback_query.message.reply_text(
            "Your CV is still being processed. Please try again in a few minutes."
        )
        return ConversationHandler.END
    
    # Find matching jobs
    vector_search = VectorSearchService(context.db_session)
    matches = await vector_search.find_matching_jobs(
        cv_id=cv.id,
        min_score=0.7,
        limit=50  # Get more than we show per page
    )
    
    if not matches:
        await update.callback_query.message.reply_text(
            "No matching jobs found at the moment. Try again later or "
            "use /search to search manually."
        )
        return ConversationHandler.END
    
    # Store matches in context
    context.user_data["matches"] = matches
    context.user_data["page"] = 0
    
    # Show first page
    await show_job_matches(update.callback_query.message, context)
    
    return SHOWING_MATCHES


async def show_job_matches(message: Update, context: CallbackContext) -> None:
    """Show page of job matches.
    
    Args:
        message: Telegram message
        context: Callback context
    """
    matches = context.user_data["matches"]
    page = context.user_data["page"]
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    current_matches = matches[start:end]
    
    # Build message text
    text = "🎯 Here are your matching jobs:\n\n"
    for i, match in enumerate(current_matches, start=1):
        job = match["job"]
        score = match["score"]
        text += (
            f"{i}. {job['title']}\n"
            f"🏢 {job['company_name']}\n"
            f"📍 {job['location']}\n"
            f"Match Score: {score:.0%}\n\n"
        )
    
    # Build keyboard
    keyboard = []
    for i, match in enumerate(current_matches, start=1):
        keyboard.append([
            InlineKeyboardButton(
                f"View Job {i}",
                callback_data=f"view_{match['job']['id']}"
            )
        ])
    
    # Add navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("◀️ Previous", callback_data="prev")
        )
    if end < len(matches):
        nav_buttons.append(
            InlineKeyboardButton("Next ▶️", callback_data="next")
        )
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("Done", callback_data="done")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(text, reply_markup=reply_markup)


async def handle_job_navigation(update: Update, context: CallbackContext) -> int:
    """Handle job list navigation.
    
    Args:
        update: Telegram update
        context: Callback context
        
    Returns:
        Next conversation state
    """
    query = update.callback_query
    
    if query.data == "done":
        await query.message.reply_text(
            "Job search complete! Use /matches to search again or "
            "/help to see all commands."
        )
        return ConversationHandler.END
        
    if query.data == "next":
        context.user_data["page"] += 1
    elif query.data == "prev":
        context.user_data["page"] -= 1
    elif query.data.startswith("view_"):
        job_id = int(query.data.split("_")[1])
        return await show_job_details(update, context, job_id)
    
    await show_job_matches(query.message, context)
    return SHOWING_MATCHES


async def show_job_details(
    update: Update,
    context: CallbackContext,
    job_id: int
) -> int:
    """Show detailed job information.
    
    Args:
        update: Telegram update
        context: Callback context
        job_id: Job ID to show
        
    Returns:
        Next conversation state
    """
    job_repo = JobRepository(context.db_session)
    job = await job_repo.get(job_id)
    
    if not job:
        await update.callback_query.message.reply_text(
            "Sorry, this job is no longer available."
        )
        return SHOWING_MATCHES
    
    # Format job details
    text = (
        f"🔍 {job.title}\n\n"
        f"🏢 Company: {job.company_name}\n"
        f"📍 Location: {job.location}\n"
        f"💰 Salary: {job.salary or 'Not specified'}\n\n"
        f"📝 Description:\n{job.description}\n\n"
        f"📋 Requirements:\n{job.requirements}\n\n"
        f"📅 Posted: {job.posted_at.strftime('%Y-%m-%d')}\n\n"
        f"To apply for this job, visit: {job.url}"
    )
    
    keyboard = [
        [InlineKeyboardButton("Back to List", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.reply_text(
        text,
        reply_markup=reply_markup
    )
    
    return VIEWING_JOB


def get_matching_handler() -> ConversationHandler:
    """Get job matching conversation handler.
    
    Returns:
        Configured conversation handler
    """
    return ConversationHandler(
        entry_points=[CommandHandler("matches", start_matching)],
        states={
            AWAITING_MATCH_TYPE: [
                CallbackQueryHandler(handle_cv_match, pattern="^cv_match$"),
                CallbackQueryHandler(
                    lambda u, c: u.callback_query.message.reply_text(
                        "Use /search to search for jobs"
                    ),
                    pattern="^search$"
                )
            ],
            SHOWING_MATCHES: [
                CallbackQueryHandler(handle_job_navigation)
            ],
            VIEWING_JOB: [
                CallbackQueryHandler(
                    lambda u, c: show_job_matches(u.callback_query.message, c),
                    pattern="^back$"
                )
            ]
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    )
