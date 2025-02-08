"""Bot configuration."""
from typing import Dict, List

# Available seniority levels
SENIORITY_LEVELS: List[str] = [
    "Entry Level",
    "Junior",
    "Mid Level",
    "Senior",
    "Manager",
    "Director",
    "Partner"
]

# Available service areas
SERVICE_AREAS: List[str] = [
    "Audit",
    "Tax",
    "Advisory",
    "Consulting",
    "Corporate Finance",
    "Risk Advisory",
    "Business Services",
    "Forensic",
    "Deal Advisory",
    "Technology Consulting"
]

# Job search filters
JOB_FILTERS: Dict[str, List[str]] = {
    "seniority": SENIORITY_LEVELS,
    "service": SERVICE_AREAS,
    "employment": [
        "Full Time",
        "Part Time",
        "Contract",
        "Temporary",
        "Internship"
    ]
}

# Bot messages
MESSAGES = {
    "welcome": (
        "👋 Welcome {name}!\n\n"
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
    ),
    "help": (
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
    ),
    "start_cv_upload": (
        "Please send me your CV (PDF or DOCX format).\n"
        "I'll analyze it and help you find matching jobs.\n\n"
        "Type /cancel to cancel."
    ),
    "cv_invalid_type": (
        "❌ Sorry, I can only process PDF and DOCX files.\n"
        "Please send a supported file format."
    ),
    "cv_processing": "🔄 Processing your CV... This may take a minute.",
    "cv_success": (
        "✅ CV processed successfully!\n\n"
        "📊 Analysis Results:\n"
        "• Skills: {skills}\n"
        "• Experience: {experience} positions\n"
        "• Education: {education} qualifications\n\n"
        "Would you like to:\n"
        "1. /search for jobs now\n"
        "2. /preferences to set your preferences\n"
        "3. /matches to see matching jobs"
    ),
    "cv_error": (
        "❌ Sorry, I couldn't process your CV.\n"
        "Please try again or contact support if the problem persists."
    ),
    "start_search": (
        "Let's find your perfect accounting job! 🔍\n\n"
        "What kind of role are you looking for?\n"
        "For example:\n"
        "• Senior Auditor in London\n"
        "• Tax Manager with 5 years experience\n"
        "• Junior Accountant KPMG\n\n"
        "Type /cancel to cancel."
    ),
    "searching": "🔍 Searching for matching jobs...",
    "no_results": (
        "😕 No jobs found matching your criteria.\n\n"
        "Try:\n"
        "• Using different keywords\n"
        "• Broadening your search\n"
        "• Setting your preferences with /preferences"
    ),
    "search_error": (
        "❌ Sorry, something went wrong with the search.\n"
        "Please try again later."
    ),
    "job_not_found": "❌ Sorry, this job is no longer available.",
    "general_error": (
        "❌ Sorry, something went wrong.\n"
        "Please try again later or contact support if the problem persists."
    ),
    "operation_cancelled": (
        "Operation cancelled. What would you like to do next?\n\n"
        "/search - Search for jobs\n"
        "/upload_cv - Upload your CV\n"
        "/preferences - Set your preferences"
    )
}

# Rate limits (per user)
RATE_LIMITS = {
    "cv_upload": {
        "limit": 5,
        "window": 3600  # 1 hour
    },
    "job_search": {
        "limit": 60,
        "window": 3600  # 1 hour
    },
    "preferences": {
        "limit": 30,
        "window": 3600  # 1 hour
    }
}

# File size limits (in bytes)
FILE_SIZE_LIMITS = {
    "cv": 10 * 1024 * 1024  # 10MB
}

# Command timeouts (in seconds)
COMMAND_TIMEOUTS = {
    "cv_processing": 300,  # 5 minutes
    "job_search": 60,      # 1 minute
    "preferences": 60      # 1 minute
}
