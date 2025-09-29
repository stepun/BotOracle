import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import config
from app.database.connection import db
from app.bot.handlers import setup_handlers
from app.bot.admin import setup_admin_handlers
from app.api.robokassa import router as robokassa_router
from app.api.admin import router as admin_router
from app.scheduler import init_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Global variables
bot = None
dp = None
scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global bot, dp, scheduler

    logger.info("Starting application...")

    # Connect to database
    await db.connect()

    # Initialize bot
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()

    # Setup handlers
    setup_handlers(dp)
    setup_admin_handlers(dp)

    # Initialize scheduler
    scheduler = init_scheduler(bot)
    await scheduler.start()

    # Set webhook if configured
    if config.WEBHOOK_HOST:
        webhook_url = f"{config.WEBHOOK_HOST}{config.WEBHOOK_PATH}"
        await bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set to {webhook_url}")
    else:
        # Start polling for development
        logger.info("Starting bot in polling mode")
        asyncio.create_task(dp.start_polling(bot))

    logger.info("Application startup completed")

    yield

    # Shutdown
    logger.info("Shutting down application...")

    if scheduler:
        await scheduler.stop()

    if bot:
        await bot.session.close()

    await db.disconnect()

    logger.info("Application shutdown completed")

# FastAPI app
app = FastAPI(
    title="AI Consultant Bot API",
    description="Telegram bot with subscription and GPT integration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(robokassa_router)
app.include_router(admin_router)

# Webhook handler
@app.post(config.WEBHOOK_PATH)
async def webhook_handler(request: Request):
    try:
        data = await request.json()
        update = Update(**data)
        await dp.feed_webhook_update(bot, update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing error")

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "AI Consultant Bot",
        "version": "1.0.0",
        "status": "running"
    }

if __name__ == "__main__":
    import uvicorn

    # Check required configuration
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN is not configured")
        exit(1)

    if not config.DATABASE_URL:
        logger.error("DATABASE_URL is not configured")
        exit(1)

    logger.info(f"Starting server on port 8000")
    logger.info(f"Webhook mode: {bool(config.WEBHOOK_HOST)}")
    logger.info(f"Database: {config.DATABASE_URL}")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )