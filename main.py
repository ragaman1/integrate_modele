#main.py
import asyncio
import logging
from telegram.ext import Application
from config.settings import BOT_TOKEN, MONGO_URI
from utils.logging_config import setup_logging
from initializers import initialize_services, run_startup_tasks
from handler_registry import register_handlers
from handlers.dispatchers import mode_dispatcher

setup_logging()
logger = logging.getLogger(__name__)

# main.py
def main():
    # Initialize services with correct order of unpacking
    db, openai_client, unified_ai_client, rate_limiter, bot_handler = initialize_services(MONGO_URI)

    # Run startup tasks
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_startup_tasks(db))

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

    # Start the Bot
    logger.info("Bot is running...")
    application.run_polling()
    
if __name__ == "__main__":
    main()