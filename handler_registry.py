# handler_registry.py
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters
from handlers.commands import help_command, start, clear_history, mode, mode_selection
from handlers.dispatchers import mode_dispatcher, error_handler

def register_handlers(application, bot_handler, mode_dispatcher):
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_history))
    application.add_handler(CommandHandler("clear_history", clear_history))  # alias for clear
    
    # Mode selection handlers
    application.add_handler(CommandHandler("mode", mode))
    application.add_handler(CallbackQueryHandler(mode_selection, pattern='^(mode_|model_)'))
    
    # Bot handler specific commands
    application.add_handler(CommandHandler('generate_images', bot_handler.generate_images))
    application.add_handler(CommandHandler('view_history', bot_handler.view_history))
    
    # Regenerate button handler - with higher priority
    application.add_handler(CallbackQueryHandler(
        bot_handler.handle_regenerate,
        pattern='^regenerate$',
        block=False
    ), group=1)
    
    # Message handler for text/image processing - lower priority
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        mode_dispatcher
    ), group=2)
    
    # Error handler
    application.add_error_handler(error_handler)