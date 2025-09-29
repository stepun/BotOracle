"""
Bot Oracle Main Application
Runs both Telegram bot and FastAPI web server with enhanced CRM functionality
"""
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from fastapi import FastAPI
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import configuration
from app.config import config

# Import database
from app.database.connection import init_db

# Import bot components
from app.bot.onboarding import router as onboarding_router
from app.bot.oracle_handlers import router as oracle_router

# Import API components
from app.api.admin import router as admin_router
from app.api.robokassa import router as robokassa_router

# Import scheduler
from app.scheduler import init_scheduler

# Configuration
BOT_TOKEN = config.BOT_TOKEN
BASE_URL = os.getenv("BASE_URL", "https://consultant.sh3.su")

# Create FastAPI app
app = FastAPI(
    title="Bot Oracle API",
    description="API for Bot Oracle - Telegram bot with Administrator and Oracle personas",
    version="2.0.0"
)

# Include API routers
app.include_router(admin_router)
app.include_router(robokassa_router)

async def create_bot_app():
    """Create and configure bot application"""
    # Initialize bot
    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")

    # Create dispatcher with FSM storage
    dp = Dispatcher(storage=MemoryStorage())

    # Include routers
    dp.include_router(onboarding_router)
    dp.include_router(oracle_router)

    logger.info("Bot configured with onboarding and oracle handlers")

    return bot, dp

# Global bot instance for webhook
bot_instance = None
dp_instance = None

@app.on_event("startup")
async def startup_event():
    """Initialize bot and scheduler on app startup"""
    global bot_instance, dp_instance

    try:
        logger.info("🤖 Bot Oracle starting...")
        logger.info("🎭 Two-persona system: Administrator + Oracle")
        logger.info("🎯 CRM proactive engagement enabled")
        logger.info("👥 Personalized interactions based on user demographics")

        # Initialize database
        await init_db()

        # Create bot and dispatcher
        bot_instance, dp_instance = await create_bot_app()

        # Initialize and start scheduler
        scheduler = init_scheduler(bot_instance)
        await scheduler.start()

        # Set webhook
        webhook_url = f"{BASE_URL}/webhook"
        await bot_instance.set_webhook(webhook_url)

        logger.info(f"Webhook set to {webhook_url}")
        logger.info("Bot Oracle startup completed!")

    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on app shutdown"""
    global bot_instance

    try:
        logger.info("Bot Oracle shutting down...")

        if bot_instance:
            await bot_instance.delete_webhook()
            await bot_instance.session.close()

        logger.info("Bot Oracle shutdown completed")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

@app.post("/webhook")
async def webhook_handler(update: dict):
    """Handle incoming webhook updates"""
    global dp_instance

    if dp_instance:
        from aiogram.types import Update
        telegram_update = Update(**update)
        await dp_instance.feed_update(bot=bot_instance, update=telegram_update)

    return {"status": "ok"}

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "Bot Oracle",
        "version": "2.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)