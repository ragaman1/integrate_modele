# utils/helpers.py

import asyncio
import logging
from telegram.error import RetryAfter, BadRequest

logger = logging.getLogger(__name__)

async def send_or_edit_message(context, update, message, text, message_sent):
    max_retries = 5
    for attempt in range(max_retries):
        try:
            if not message_sent:
                message = await update.message.reply_text(
                    text,
                    disable_web_page_preview=True,
                    parse_mode='MarkdownV2'
                )
                return message
            else:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=message.message_id,
                    text=text,
                    disable_web_page_preview=True,
                    parse_mode='MarkdownV2'
                )
                return
        except RetryAfter as e:
            if attempt < max_retries - 1:
                logger.warning(f"Rate limit hit. Waiting for {e.retry_after} seconds.")
                await asyncio.sleep(e.retry_after)
            else:
                logger.error("Max retries reached due to rate limits.")
                raise
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                logger.error(f"BadRequest error while editing message: {e}")
            break  # Don't retry for this error
        except Exception as e:
            logger.error(f"Error in send_or_edit_message (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                logger.error("Max retries reached due to unexpected errors.")
                raise
            await asyncio.sleep(5)