"""Main application module."""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes import router as api_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.database import engine, init_db, close_db
from app.services.embeddings import embedding_service
from app.services.job_matching import job_matching_service
from app.telegram_bot import bot

# Set up logging first
setup_logging(log_level=settings.LOG_LEVEL)
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    try:
        logger.debug("Starting application initialization")
        
        # Initialize database
        logger.debug("Initializing database")
        await init_db()
        logger.info("Database initialized")
        
        # Initialize services
        logger.debug("Initializing embedding service")
        await embedding_service.init()
        logger.info("Embedding service initialized")
        
        logger.debug("Initializing job matching service")
        await job_matching_service.init()
        logger.info("Job matching service initialized")
        
        # Initialize bot only in production mode
        if settings.BOT_ENV == "production" and settings.TELEGRAM_BOT_TOKEN:
            logger.debug("Initializing Telegram bot for production")
            await bot.init()
            
            if settings.TELEGRAM_WEBHOOK_URL:
                logger.debug("Setting up webhook")
                webhook_url = f"{settings.TELEGRAM_WEBHOOK_URL}/webhook/{settings.TELEGRAM_BOT_TOKEN}"
                await bot.application.bot.set_webhook(
                    url=webhook_url,
                    allowed_updates=settings.TELEGRAM_ALLOWED_UPDATES,
                    max_connections=settings.TELEGRAM_MAX_CONNECTIONS
                )
                logger.info(f"Webhook configured at {webhook_url}")
            else:
                logger.warning("TELEGRAM_WEBHOOK_URL not set in production mode")
        
        logger.info("Application startup complete")
        yield
        
    except Exception as e:
        logger.error("Error during startup", exc_info=True)
        raise
    finally:
        # Cleanup
        logger.info("Starting application shutdown")
        
        # Cleanup bot in production mode
        if settings.BOT_ENV == "production" and settings.TELEGRAM_BOT_TOKEN and bot.application:
            logger.debug("Removing webhook")
            await bot.application.bot.delete_webhook()
            logger.debug("Stopping Telegram bot")
            await bot.stop()
            
        # Close database
        logger.debug("Closing database")
        await close_db()
        logger.info("Database closed")
        
        logger.info("Application shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="AI Accounting Job Matching",
    description="API for matching accounting jobs with candidates using AI",
    version=settings.VERSION,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure this properly
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add API routes
app.include_router(api_router, prefix="/api")

# Add webhook route for Telegram updates in production mode
@app.post("/webhook/{bot_token}")
async def webhook(bot_token: str, request: Request) -> Response:
    """Handle Telegram webhook updates."""
    # Only process webhooks in production mode
    if settings.BOT_ENV != "production":
        logger.warning("Received webhook in non-production mode")
        return Response(status_code=404)
        
    if bot_token != settings.TELEGRAM_BOT_TOKEN:
        logger.warning("Received webhook with invalid token")
        return Response(status_code=403)
        
    # Get update data
    update_data = await request.json()
    
    # Process update
    if bot.application:
        await bot.application.update_queue.put(update_data)
        return Response(status_code=200)
    else:
        logger.error("Bot application not initialized")
        return Response(status_code=500)
