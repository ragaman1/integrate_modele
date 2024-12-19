# handlers/messages.py

import asyncio
import logging
import re
import traceback
from telegram import Update
from telegram.ext import ContextTypes
from g4f.models import(
    Model , Blackbox, DDG , Pizzagpt,
    HuggingChat
)
from g4f.Provider import IterListProvider
from services.unified_ai_client import OpenAIClient,G4FClient,UnifiedAIClient
from services.database import Database
from telegram.error import RetryAfter, BadRequest
from utils.markdown_utils import is_markdown_complete
from utils.helpers import send_or_edit_message
from rate_limit.limiter import rate_limiter

logger = logging.getLogger(__name__)

# Import markdownvn1 if it's a separate module. Assuming it's in utils.
from utils.markdown_utils import escape_markdown_v2  # Update path if different

MAX_WORDS = 2500
MAX_REPLY_TOKENS = 1024
OPENAI_MODEL1 = "Meta-Llama-3.3-70B-Instruct"
OPENAI_MODEL2 = "Meta-Llama-3.1-70B-Instruct"
G4F_MODEL = Model(
    name          = 'gpt-4o-mini',
    base_provider = 'OpenAI',
    best_provider = IterListProvider([
    DDG, Pizzagpt,
    ])
)
# Initialize with specific backend
client_g4f = UnifiedAIClient(backend="g4f")
client_openai = UnifiedAIClient(backend="openai")


CHUNK_UPDATE_THRESHOLD = 200  # Update every 200 words
MIN_UPDATE_INTERVAL = 5       # Minimum 5 seconds between updates
MAX_MESSAGES = 400            # Maximum number of messages
WINDOW_SECONDS = 43200        # 12 hours

OPENAI_MODEL1 = "Meta-Llama-3.3-70B-Instruct"
OPENAI_MODEL2 = "Qwen2.5-Coder-32B-Instruct"
G4F_MODEL = Model(
    name          = 'gpt-4o-mini',
    base_provider = 'OpenAI',
    best_provider = IterListProvider([
    DDG, Pizzagpt,
    ])
)
# Initialize with specific backend
client_g4f = UnifiedAIClient(backend="g4f")
client_openai = UnifiedAIClient(backend="openai")


CHUNK_UPDATE_THRESHOLD = 200  # Update every 200 words
MIN_UPDATE_INTERVAL = 5       # Minimum 5 seconds between updates
MAX_MESSAGES = 400            # Maximum number of messages
WINDOW_SECONDS = 43200        # 12 hours


@rate_limiter(max_messages=MAX_MESSAGES, window_seconds=WINDOW_SECONDS)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db: Database = context.bot_data['db']
    model = context.user_data.get('model')

    logger.info(f"Selected model: {getattr(model, 'name', model)}")
    logger.info(f"Model type: {type(model)}")

    # Get the AI client from bot_data or create a new one with correct backend
    if isinstance(model, Model):  # G4F model
        unified_ai_client = UnifiedAIClient(backend="g4f")
        logger.info("Using G4F backend")
    else:  # OpenAI models
        unified_ai_client = UnifiedAIClient(backend="openai")
        logger.info("Using OpenAI backend")

    try:
        message = update.message
        user_input = message.text
        chat_id = update.effective_chat.id
        user = update.effective_user
        user_first_name = user.first_name if user.first_name else "Unknown"
        user_username = user.username if user.username else "Unknown"

        logger.info(f"Processing message with model: {getattr(model, 'name', model)}")

        # Update chat metadata
        await db.update_chat_metadata(chat_id, user_first_name, user_username)

        # Insert user's message
        timestamp = asyncio.get_event_loop().time()
        await db.insert_message(chat_id, timestamp, "user", user_input)

        # Get history_cleared_at
        history_cleared_at = await db.get_chat_history_cleared_at(chat_id)

        # Get total words and trim if necessary
        total_words = await db.get_total_words(chat_id, history_cleared_at)
        logger.info(f"Total words in chat {chat_id}: {total_words}")

        if total_words > MAX_WORDS:
            logger.info(f"Chat {chat_id} exceeds word limit. Trimming history.")
            await db.trim_chat_history(chat_id, history_cleared_at, MAX_WORDS)

        # Get chat history
        chat_history = await db.get_chat_history(chat_id, history_cleared_at, MAX_WORDS)

        # Indicate typing
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        reply_text = ""
        message_sent = False
        message_obj = None
        chunk_buffer = ""
        word_count = 0
        last_update_time = 0

        async for chunk in unified_ai_client.generate_response(
            model=model,  # Use the selected model
            messages=chat_history,
            temperature=0.75,
            max_tokens=MAX_REPLY_TOKENS,
            top_p=0.60
        ):

            reply_text += chunk
            chunk_buffer += chunk
            word_count += len(re.findall(r'\w+', chunk))
            current_time = asyncio.get_event_loop().time()

            should_update = (
                word_count >= CHUNK_UPDATE_THRESHOLD or
                len(chunk_buffer) >= 200 or  # Increased character limit
                chunk == "" or  # End of response
                (current_time - last_update_time) >= MIN_UPDATE_INTERVAL  # Time-based update
            )

            if should_update and is_markdown_complete(reply_text):
                escaped_text = escape_markdown_v2(reply_text)

                while True:
                    try:
                        if not message_sent:
                            message_obj = await update.message.reply_text(
                                escaped_text,
                                disable_web_page_preview=True,
                                parse_mode='MarkdownV2'
                            )
                            message_sent = True
                        else:
                            await context.bot.edit_message_text(
                                chat_id=update.effective_chat.id,
                                message_id=message_obj.message_id,
                                text=escaped_text,
                                disable_web_page_preview=True,
                                parse_mode='MarkdownV2'
                            )
                        last_update_time = current_time
                        break  # Successful update, exit retry loop
                    except RetryAfter as e:
                        logger.warning(f"Rate limit hit. Waiting for {e.retry_after} seconds.")
                        await asyncio.sleep(e.retry_after)
                    except BadRequest as e:
                        if "Message is not modified" not in str(e):
                            logger.error(f"Error editing message: {e}")
                        break  # Don't retry for this error
                    except Exception as e:
                        logger.error(f"Error sending/editing message: {e}")
                        await asyncio.sleep(5)  # Wait 5 seconds before retrying
                        if (asyncio.get_event_loop().time() - current_time) > 60:
                            logger.error("Failed to update message after 1 minute of retries.")
                            break  # Give up after 1 minute of retries

                chunk_buffer = ""
                word_count = 0

            # Send typing action less frequently
            if (current_time - last_update_time) >= 5:
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        # Ensure the final part is sent if there's any remaining text
        if chunk_buffer and is_markdown_complete(reply_text):
            escaped_text = escape_markdown_v2(reply_text)
            message_obj = await send_or_edit_message(context, update, message_obj, escaped_text, message_sent)

        # Insert bot's response
        await db.insert_message(update.effective_chat.id, asyncio.get_event_loop().time(), "bot", reply_text)

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        traceback.print_exc()
        await update.message.reply_text("An unexpected error occurred. Please try again later.")