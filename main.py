import asyncio
import logging
from fastapi import FastAPI, Response, status
from telegram.ext import Application
from config.settings import BOT_TOKEN, MONGO_URI, WEBHOOK_URL, PORT, WEBHOOK_PATH
from utils.logging_config import setup_logging
from initializers import initialize_services, run_startup_tasks
from handler_registry import register_handlers
from handlers.dispatchers import mode_dispatcher
import uvicorn
import os

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI()
application = None

# SSL certificate paths
SSL_CERT = os.path.join("ssl", "cert.pem")
SSL_KEY = os.path.join("ssl", "key.pem")

async def setup_webhook():
    # Initialize services
    db, openai_client, unified_ai_client, rate_limiter, bot_handler = initialize_services(MONGO_URI)

    # Run startup tasks
    await run_startup_tasks(db)

    # Initialize the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Store shared resources
    application.bot_data.update({
        'db': db,
        'openai_client': openai_client,
        'bot_handler': bot_handler,
        'ai_client': unified_ai_client
    })

    # Register handlers
    register_handlers(application, bot_handler, mode_dispatcher)

    # Set webhook with certificate
    with open(SSL_CERT, 'rb') as cert_file:
        await application.bot.set_webhook(
            url=f"{WEBHOOK_URL}{WEBHOOK_PATH}",
            certificate=cert_file.read(),
            allowed_updates=["message", "callback_query"]
        )

    return application

@app.on_event("startup")
async def startup():
    global application
    application = await setup_webhook()
    logger.info("Bot started and webhook set")

@app.on_event("shutdown")
async def shutdown():
    if application:
        await application.bot.delete_webhook()
        await application.shutdown()
    logger.info("Bot shutdown complete")

@app.get("/health")
async def health_check():
    if application:
        return {"status": "healthy", "bot_running": True}
    return Response(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content="Bot not initialized"
    )

@app.post(WEBHOOK_PATH)
async def webhook_handler(update: dict):
    if application:
        await application.update_queue.put(update)
        return {"ok": True}
    return Response(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content="Bot not initialized"
    )

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        ssl_keyfile=SSL_KEY,
        ssl_certfile=SSL_CERT
    )