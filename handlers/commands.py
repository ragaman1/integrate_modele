# handlers/commands.py

import asyncio
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from services.database import Database
from g4f.models import Model
from g4f.Provider import DDG, Pizzagpt, ChatgptFree, IterListProvider

logger = logging.getLogger(__name__)

# Define models
OPENAI_MODEL1 = "Meta-Llama-3.3-70B-Instruct"
OPENAI_MODEL2 = "Qwen2.5-Coder-32B-Instruct"
G4F_MODEL = Model(
    name='gpt-4o-mini',
    base_provider='OpenAI',
    best_provider=IterListProvider([
        DDG, Pizzagpt, ChatgptFree,
    ])
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_name = user.first_name if user.first_name else "there"
    welcome_text = (
        f"👋 Hi {user_name}!\n\n"
        "I'm your AI assistant with multiple capabilities:\n\n"
        "🤖 Text Generation Models:\n"
        "• Meta-Llama-3.1-405B (Default)\n"
        "• Meta-Llama-3.1-70B\n"
        "• GPT-4-Mini (G4F)\n\n"
        "🎨 Image Generation\n\n"
        "Use /mode to select your preferred mode and model!"
    )
    await update.message.reply_text(welcome_text)
    logger.info(f"User {user.id} started the bot.")

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db: Database = context.bot_data['db']
    chat_id = update.effective_chat.id
    current_time = asyncio.get_event_loop().time()

    try:
        await db.clear_chat_history(chat_id, current_time)
        await update.message.reply_text(
            "Your chat history has been cleared. The bot will no longer consider previous messages."
        )
        logger.info(f"Chat history cleared for chat_id: {chat_id}")
    except Exception as e:
        await update.message.reply_text("Failed to clear chat history. Please try again later.")
        logger.error(f"Error clearing history for chat_id {chat_id}: {e}")

async def mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Meta-Llama-3.1-405B 🤖", callback_data='model_openai1')],
        [InlineKeyboardButton("Meta-Llama-3.1-70B 🧠", callback_data='model_openai2')],
        [InlineKeyboardButton("GPT-4-Mini (G4F) ⚡", callback_data='model_g4f')],
        [InlineKeyboardButton("Image Generator 🎨", callback_data='mode_image')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Choose your preferred mode:",
        reply_markup=reply_markup
    )

async def mode_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    user_id = query.from_user.id

    if choice == 'mode_image':
        context.user_data['mode'] = 'image'
        context.user_data['model'] = None
        await query.edit_message_text(
            "Mode set to Image Generator 🎨\n"
            "Send me a description of the image you want to create!"
        )
    elif choice.startswith('model_'):
        context.user_data['mode'] = 'text'
        model_choice = choice.split('_')[1]
        
        if model_choice == 'openai1':
            context.user_data['model'] = OPENAI_MODEL1
            model_name = "Meta-Llama-3.1-405B"
            logger.info(f"Set OpenAI Model 1: {OPENAI_MODEL1}")
        elif model_choice == 'openai2':
            context.user_data['model'] = OPENAI_MODEL2
            model_name = "Meta-Llama-3.1-70B"
            logger.info(f"Set OpenAI Model 2: {OPENAI_MODEL2}")
        elif model_choice == 'g4f':
            context.user_data['model'] = G4F_MODEL
            model_name = "GPT-4-Mini (G4F)"
            logger.info(f"Set G4F Model: {G4F_MODEL.name}")
        
        # Debug logging
        logger.info(f"Model set to: {context.user_data['model']}")
        logger.info(f"Model type: {type(context.user_data['model'])}")
        
        await query.edit_message_text(
            f"Model set to: {model_name}\n"
            "You can now start chatting!"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Available commands:\n\n"
        "/start - Start the bot\n"
        "/mode - Select mode and model\n"
        "/clear - Clear chat history\n"
        "/help - Show this help message"
    )
    await update.message.reply_text(help_text)