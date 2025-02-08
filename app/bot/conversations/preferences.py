"""Telegram bot conversation handlers for user preferences."""
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
from app.repositories.user import UserRepository
from app.schemas.preferences import (
    JobPreferences,
    NotificationPreferences,
    SearchPreferences,
    JobType,
    WorkLocation,
    SeniorityLevel,
    NotificationType
)

logger = logging.getLogger(__name__)

# Conversation states
(
    AWAITING_PREFERENCE_TYPE,
    AWAITING_JOB_TYPE,
    AWAITING_WORK_LOCATION,
    AWAITING_SENIORITY,
    AWAITING_SALARY_MIN,
    AWAITING_SALARY_MAX,
    AWAITING_LOCATIONS,
    AWAITING_COMMUTE,
    AWAITING_SKILLS,
    AWAITING_INDUSTRIES,
    AWAITING_EXCLUDED_COMPANIES,
    AWAITING_NOTIFICATION_TYPE,
    AWAITING_EMAIL_FREQUENCY,
    AWAITING_MATCH_SCORE,
    AWAITING_QUIET_HOURS,
    AWAITING_SEARCH_RADIUS,
    AWAITING_SORT_ORDER,
    AWAITING_RESULTS_PER_PAGE
) = range(18)


async def start_preferences(update: Update, context: CallbackContext) -> int:
    """Start preferences conversation.
    
    Args:
        update: Telegram update
        context: Callback context
        
    Returns:
        Next conversation state
    """
    keyboard = [
        [InlineKeyboardButton("Job Preferences", callback_data="job_prefs")],
        [InlineKeyboardButton("Notification Settings", callback_data="notif_prefs")],
        [InlineKeyboardButton("Search Settings", callback_data="search_prefs")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "What preferences would you like to update?",
        reply_markup=reply_markup
    )
    
    return AWAITING_PREFERENCE_TYPE


async def handle_job_preferences(update: Update, context: CallbackContext) -> int:
    """Handle job preferences selection.
    
    Args:
        update: Telegram update
        context: Callback context
        
    Returns:
        Next conversation state
    """
    keyboard = [
        [k.value for k in JobType],
        ["Done"]
    ]
    reply_markup = InlineKeyboardMarkup([[b] for b in keyboard[0]] + [keyboard[1]])
    
    await update.callback_query.message.reply_text(
        "Select your preferred job types (you can select multiple):",
        reply_markup=reply_markup
    )
    
    return AWAITING_JOB_TYPE


async def handle_job_type(update: Update, context: CallbackContext) -> int:
    """Handle job type selection.
    
    Args:
        update: Telegram update
        context: Callback context
        
    Returns:
        Next conversation state
    """
    if not hasattr(context.user_data, "job_types"):
        context.user_data["job_types"] = []
        
    choice = update.callback_query.data
    if choice == "Done":
        keyboard = [
            [k.value for k in WorkLocation],
            ["Done"]
        ]
        reply_markup = InlineKeyboardMarkup(
            [[b] for b in keyboard[0]] + [keyboard[1]]
        )
        
        await update.callback_query.message.reply_text(
            "Select your preferred work locations:",
            reply_markup=reply_markup
        )
        return AWAITING_WORK_LOCATION
        
    context.user_data["job_types"].append(choice)
    await update.callback_query.answer(f"Added {choice}")
    return AWAITING_JOB_TYPE


async def handle_notification_preferences(
    update: Update,
    context: CallbackContext
) -> int:
    """Handle notification preferences selection.
    
    Args:
        update: Telegram update
        context: Callback context
        
    Returns:
        Next conversation state
    """
    keyboard = [
        [k.value for k in NotificationType],
    ]
    reply_markup = InlineKeyboardMarkup([[b] for b in keyboard[0]])
    
    await update.callback_query.message.reply_text(
        "How would you like to receive notifications?",
        reply_markup=reply_markup
    )
    
    return AWAITING_NOTIFICATION_TYPE


async def handle_search_preferences(update: Update, context: CallbackContext) -> int:
    """Handle search preferences selection.
    
    Args:
        update: Telegram update
        context: Callback context
        
    Returns:
        Next conversation state
    """
    await update.callback_query.message.reply_text(
        "What should be the default search radius (in miles)?"
    )
    
    return AWAITING_SEARCH_RADIUS


async def save_preferences(update: Update, context: CallbackContext) -> int:
    """Save user preferences.
    
    Args:
        update: Telegram update
        context: Callback context
        
    Returns:
        ConversationHandler.END
    """
    user_repo = UserRepository(context.db_session)
    
    if "job_types" in context.user_data:
        job_prefs = JobPreferences(
            job_types=context.user_data["job_types"],
            work_locations=context.user_data.get("work_locations", []),
            seniority_levels=context.user_data.get("seniority_levels", []),
            min_salary=context.user_data.get("min_salary"),
            max_salary=context.user_data.get("max_salary"),
            preferred_locations=context.user_data.get("locations", []),
            max_commute_distance=context.user_data.get("commute_distance"),
            skills=context.user_data.get("skills", []),
            industries=context.user_data.get("industries", []),
            excluded_companies=context.user_data.get("excluded_companies", [])
        )
        await user_repo.update_job_preferences(
            user_id=update.effective_user.id,
            preferences=job_prefs.model_dump()
        )
        
    if "notification_type" in context.user_data:
        notif_prefs = NotificationPreferences(
            notification_type=context.user_data["notification_type"],
            email_frequency=context.user_data.get("email_frequency", "daily"),
            min_match_score=context.user_data.get("min_match_score", 0.7),
            notify_new_jobs=context.user_data.get("notify_new_jobs", True),
            notify_expiring_jobs=context.user_data.get(
                "notify_expiring_jobs",
                True
            ),
            notify_salary_updates=context.user_data.get(
                "notify_salary_updates",
                True
            ),
            quiet_hours_start=context.user_data.get("quiet_hours_start"),
            quiet_hours_end=context.user_data.get("quiet_hours_end")
        )
        await user_repo.update_notification_preferences(
            user_id=update.effective_user.id,
            preferences=notif_prefs.model_dump()
        )
        
    if "search_radius" in context.user_data:
        search_prefs = SearchPreferences(
            default_search_radius=context.user_data["search_radius"],
            default_sort=context.user_data.get("sort_order", "relevance"),
            results_per_page=context.user_data.get("results_per_page", 10),
            save_search_history=context.user_data.get(
                "save_search_history",
                True
            ),
            include_similar_roles=context.user_data.get(
                "include_similar_roles",
                True
            ),
            highlight_new_jobs=context.user_data.get("highlight_new_jobs", True)
        )
        await user_repo.update_search_preferences(
            user_id=update.effective_user.id,
            preferences=search_prefs.model_dump()
        )
    
    await update.message.reply_text(
        "Your preferences have been saved! 👍\n"
        "Use /search to find jobs or /help to see all commands."
    )
    
    # Clear conversation data
    context.user_data.clear()
    
    return ConversationHandler.END


async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancel preference update.
    
    Args:
        update: Telegram update
        context: Callback context
        
    Returns:
        ConversationHandler.END
    """
    await update.message.reply_text(
        "Preference update cancelled.\n"
        "Use /preferences to try again or /help to see all commands."
    )
    
    # Clear conversation data
    context.user_data.clear()
    
    return ConversationHandler.END


def get_preferences_handler() -> ConversationHandler:
    """Get preferences conversation handler.
    
    Returns:
        Configured conversation handler
    """
    return ConversationHandler(
        entry_points=[CommandHandler("preferences", start_preferences)],
        states={
            AWAITING_PREFERENCE_TYPE: [
                CallbackQueryHandler(
                    handle_job_preferences,
                    pattern="^job_prefs$"
                ),
                CallbackQueryHandler(
                    handle_notification_preferences,
                    pattern="^notif_prefs$"
                ),
                CallbackQueryHandler(
                    handle_search_preferences,
                    pattern="^search_prefs$"
                )
            ],
            AWAITING_JOB_TYPE: [
                CallbackQueryHandler(handle_job_type)
            ],
            AWAITING_WORK_LOCATION: [
                CallbackQueryHandler(handle_work_location)
            ],
            AWAITING_SENIORITY: [
                CallbackQueryHandler(handle_seniority)
            ],
            AWAITING_SALARY_MIN: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_salary_min
                )
            ],
            AWAITING_SALARY_MAX: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_salary_max
                )
            ],
            AWAITING_LOCATIONS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_locations
                )
            ],
            AWAITING_COMMUTE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_commute
                )
            ],
            AWAITING_SKILLS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_skills
                )
            ],
            AWAITING_INDUSTRIES: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_industries
                )
            ],
            AWAITING_EXCLUDED_COMPANIES: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_excluded_companies
                )
            ],
            AWAITING_NOTIFICATION_TYPE: [
                CallbackQueryHandler(handle_notification_type)
            ],
            AWAITING_EMAIL_FREQUENCY: [
                CallbackQueryHandler(handle_email_frequency)
            ],
            AWAITING_MATCH_SCORE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_match_score
                )
            ],
            AWAITING_QUIET_HOURS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_quiet_hours
                )
            ],
            AWAITING_SEARCH_RADIUS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_search_radius
                )
            ],
            AWAITING_SORT_ORDER: [
                CallbackQueryHandler(handle_sort_order)
            ],
            AWAITING_RESULTS_PER_PAGE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_results_per_page
                )
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
