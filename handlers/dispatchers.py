# handlers/dispatchers.py

import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers.messages import handle_message

logger = logging.getLogger(__name__)

async def mode_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Dispatches messages based on the selected mode and model in context.user_data
    """
    mode = context.user_data.get('mode', 'text')  # Default to text mode
    model = context.user_data.get('model')  # Get selected model if any
    
    logger.debug(f"Dispatcher invoked. Mode: {mode}, Model: {getattr(model, 'name', model)}")
    
    if mode == 'text':
        if not model:
            # If no model is selected, use OPENAI_MODEL1 as default
            from handlers.commands import OPENAI_MODEL1
            context.user_data['model'] = OPENAI_MODEL1
            logger.info("No model selected, using default OPENAI_MODEL1")
        
        await handle_message(update, context)
        
    elif mode == 'image':
        bot_handler = context.bot_data.get('bot_handler')
        if bot_handler:
            try:
                await bot_handler.generate_images(update, context)
            except Exception as e:
                logger.error(f"Error in image generation: {e}", exc_info=True)
                await update.message.reply_text(
                    "Sorry, I encountered an error while generating the image. "
                    "Please try again or use /mode to switch modes."
                )
        else:
            logger.error("BotMessageHandler not found in bot_data")
            await update.message.reply_text(
                "Sorry, image generation is currently unavailable. "
                "Please try again later or use /mode to switch modes."
            )
    else:
        logger.warning(f"Unknown mode '{mode}' detected. Defaulting to text mode.")
        context.user_data['mode'] = 'text'
        from handlers.commands import OPENAI_MODEL1
        context.user_data['model'] = OPENAI_MODEL1
        await update.message.reply_text(
            "Unknown mode detected. Defaulting to text mode with Meta-Llama-3.1-405B.\n"
            "Use /mode to select your preferred mode and model."
        )
        await handle_message(update, context)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in the dispatcher."""
    logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "Sorry, an error occurred while processing your request. "
                "Please try again later or use /mode to switch modes."
            )
    except Exception as e:
        logger.error(f"Error in error handler: {e}", exc_info=True)