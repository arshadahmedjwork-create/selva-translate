import logging
from fastapi import FastAPI, Request, Response, status
from telegram import Update
from src.config import settings
from src.services.telegram import bot_app

# Configure Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Stateless Tamil-English Translation Bot API")

@app.on_event("startup")
async def startup_event():
    # Initialize Telegram Bot Application
    logger.info("Initializing Telegram Bot...")
    await bot_app.initialize()
    await bot_app.start()

    if settings.WEBHOOK_URL:
        webhook_url = f"{settings.WEBHOOK_URL.rstrip('/')}/webhook"
        logger.info(f"Setting Telegram Webhook to: {webhook_url}")
        await bot_app.bot.set_webhook(url=webhook_url)
    else:
        logger.info("WEBHOOK_URL is not set. Starting Telegram Bot in Polling Mode...")
        await bot_app.updater.start_polling()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Stopping Telegram Bot...")
    if not settings.WEBHOOK_URL:
        await bot_app.updater.stop()
    await bot_app.stop()
    await bot_app.shutdown()

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Endpoint for receiving Telegram webhook updates.
    """
    if not settings.WEBHOOK_URL:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    try:
        payload = await request.json()
        update = Update.de_json(payload, bot_app.bot)
        # Process update asynchronously
        await bot_app.process_update(update)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error processing webhook update: {e}")
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.get("/health")
def health_check():
    return {"status": "healthy"}
