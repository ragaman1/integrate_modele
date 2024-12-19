# rate_limiter.py
import asyncio
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from services.database import Database
import logging

logger = logging.getLogger(__name__)

def rate_limiter(max_messages: int, window_seconds: int):
    """
    Decorator to apply rate limiting to Telegram handlers.

    Args:
        max_messages (int): Maximum number of messages allowed within the window.
        window_seconds (int): Time window in seconds.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user = update.effective_user
            if not user:
                # If there's no user information, allow the message
                return await func(update, context, *args, **kwargs)

            user_id = user.id
            current_timestamp = asyncio.get_event_loop().time()

            db: Database = context.bot_data.get('db')  # Access the Database instance from bot_data

            if not db:
                logger.error("Database instance not found in bot_data.")
                await update.message.reply_text("Internal error. Please try again later.")
                return

            allowed = await db.check_and_increment_rate_limit(user_id, current_timestamp, max_messages, window_seconds)

            if allowed:
                return await func(update, context, *args, **kwargs)
            else:
                # Rate limit exceeded, notify the user
                await update.message.reply_text(
                    f"🚫 Rate limit exceeded.You have sent 40 messages Please wait 12 hours before sending more messages."
                )
        return wrapper
    return decorator