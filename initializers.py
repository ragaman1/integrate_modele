#initializers.py
from services.database import Database
from services.openai_client import OpenAIClient
from services.unified_ai_client import UnifiedAIClient  # Ensure the correct import path
from utils.rate_limiter import RateLimiter
from handlers.message_handlers import BotMessageHandler

# initializers.py
def initialize_services(mongo_uri):
    db = Database(mongo_uri)
    openai_client = OpenAIClient()
    unified_ai_client = UnifiedAIClient()
    rate_limiter = RateLimiter(max_requests=50, time_window=24*3600)
    bot_handler = BotMessageHandler(rate_limiter=rate_limiter)
    # Match the order used in main.py:
    return db, openai_client, unified_ai_client, rate_limiter, bot_handler

async def run_startup_tasks(db_instance: Database):
    await db_instance.create_indexes()