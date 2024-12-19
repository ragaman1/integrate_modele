# handlers/message_handlers.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import asyncio
from config.settings import MAX_PROMPT_LENGTH
from services.translation_service import TranslationService
from services.image_service import ImageService
from utils.logging_config import logger
from utils.rate_limiter import RateLimiter
from utils.prompt_storage import PromptStorage 
from utils.exceptions import (
    ImageGenerationError,
    NSFWContentError,
    APIConnectionError,
    InvalidPromptError
)
from datetime import datetime, timedelta

class BotMessageHandler:
    REFUSAL_MESSAGES = [
        "I can't create explicit content.",
        "I can't create adult content.",
        "I'm sorry, but I can't assist with that request.",
        "I can't help with that.",
        "I cannot create explicit content.",
        "I can't help with that request.",
        "I can't help you with this request.",
        "I can't help you with that.",
        "I can't help with that",
        "I can't create explicit content.",
    ]

    # Progress bar configuration
    PROGRESS_FULL = "🟩"
    PROGRESS_EMPTY = "⬜️"
    TOTAL_STEPS = 10  # Total progress bar positions
    PROMPT_STEPS = 2  # Steps for prompt enhancement
    IMAGE_STEPS = 4   # Steps per image

    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
        self.translation_service = TranslationService()
        self.image_service = ImageService()
        self.prompt_storage = PromptStorage(max_prompts=5)  # Initialize PromptStorage

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            await update.message.reply_text(
                'Hi! Send me a prompt in any language, and I will generate images for you.'
            )
            logger.info(f"User {update.effective_user.id} started the bot.")
        except Exception as e:
            logger.error(f"Error in start handler: {e}", exc_info=True)
            await update.message.reply_text("An error occurred while processing your request.")

    async def generate_images(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        original_prompt = update.message.text.strip()
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        # Check rate limit
        try:
            if not self.rate_limiter.can_make_request(user_id):
                oldest_request = self.rate_limiter.get_oldest_request_time(user_id)
                if oldest_request:
                    reset_time = oldest_request + timedelta(hours=24)
                    remaining_time = reset_time - datetime.now()
                    hours = remaining_time.total_seconds() / 3600

                    await update.message.reply_text(
                        f"You have reached your daily limit of 5 image generations. "
                        f"Please try again in {hours:.1f} hours.",
                        parse_mode='HTML'
                    )
                    logger.warning(f"User {user_id} exceeded rate limit.")
                    return
        except Exception as e:
            logger.error(f"Rate limiter error for user {user_id}: {e}", exc_info=True)
            await update.message.reply_text("An error occurred while processing your request. Please try again later.")
            return

        # Validate prompt
        if not self._validate_prompt(original_prompt, update):
            return

        logger.info(f"User {user_id} in chat {chat_id} sent prompt: {original_prompt}")
        status_message = await update.message.reply_text('Created by: 纳谢纳斯 \n\n contact me for any error @orionagi')

        try:
            # Initial progress bar
            await asyncio.sleep(2)
            await self._update_progress(status_message, 0)

            await asyncio.sleep(2)
            await self._update_progress(status_message, 1)

            # Prompt enhancement phase (0-20%)
            await asyncio.sleep(2)
            enhanced_prompt = await self.translation_service.translate_prompt(original_prompt)
            await self._update_progress(status_message, 2)

            if not enhanced_prompt:
                await status_message.edit_text("Failed to process your prompt. Please try again.")
                return

            if any(message.lower() in enhanced_prompt.lower() for message in self.REFUSAL_MESSAGES):
                logger.warning(f"User {user_id} provided an unprocessable prompt: {original_prompt}")
                await status_message.edit_text(
                    "Sorry, your prompt contains content that cannot be processed."
                )
                return

            # Store the original and enhanced prompts
            await self.prompt_storage.add_prompt(user_id, original_prompt)
            await self.prompt_storage.add_prompt(user_id, enhanced_prompt)

            # First image generation (20-60%)
            first_image_task = asyncio.create_task(
                self.image_service.generate_single_image(enhanced_prompt)
            )

            # Update progress during first image generation
            for step in range(3, 6):
                await asyncio.sleep(1.3)
                await self._update_progress(status_message, step)

            first_image = await first_image_task
            await self._update_progress(status_message, 6)

            # Second image generation (60-100%)
            second_image_task = asyncio.create_task(
                self.image_service.generate_single_image(enhanced_prompt)
            )

            # Update progress during second image generation
            for step in range(7, 10):
                await asyncio.sleep(1.9)
                await self._update_progress(status_message, step)

            second_image = await second_image_task
            await self._update_progress(status_message, 10)

            # Send images
            images = [first_image, second_image]
            await self._send_images(update.message, context, images, prompt=original_prompt, enhanced_prompt=enhanced_prompt)
            await status_message.delete()

        except NSFWContentError as e:
            logger.error(f"NSFW content detected for user {user_id}: {e}", exc_info=True)
            await status_message.edit_text("Your prompt resulted in content that cannot be processed due to its nature.")
            await update.message.reply_text("Please modify your prompt to avoid NSFW content and try again.")
        except InvalidPromptError as e:
            logger.error(f"Invalid prompt for user {user_id}: {e}", exc_info=True)
            await status_message.edit_text("Your prompt is invalid. Please revise it and try again.")
        except APIConnectionError as e:
            logger.error(f"API connection error for user {user_id}: {e}", exc_info=True)
            await status_message.edit_text("We're experiencing technical difficulties. Please try again later.")
        except ImageGenerationError as e:
            logger.error(f"Image generation error for user {user_id}: {e}", exc_info=True)
            await status_message.edit_text("An error occurred while generating your images. Please try again.")
        except Exception as e:
            logger.error(f"Unexpected error processing request for user {user_id}: {e}", exc_info=True)
            await status_message.edit_text('An unexpected error occurred. Please try again later.')

    async def _update_progress(self, message, steps: int):
        """
        Updates the progress bar message.
        """
        try:
            progress = self._create_progress_bar(steps)
            await message.edit_text(
                f"Generating images, please wait...\n\nJoin our group for the free version:\nhttps://t.me/+dN7qZppVw9w4YjVh\n\n{progress}",
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Error updating progress bar: {e}", exc_info=True)

    def _create_progress_bar(self, completed: int) -> str:
        """
        Creates a 10-position progress bar.
        """
        filled = self.PROGRESS_FULL * completed
        empty = self.PROGRESS_EMPTY * (self.TOTAL_STEPS - completed)
        percentage = (completed / self.TOTAL_STEPS) * 100
        return f"{filled}{empty} {percentage:.0f}%"

    async def _send_images(self, message, context: ContextTypes.DEFAULT_TYPE, images: list, prompt: str = None, enhanced_prompt: str = None):
        """
        Sends generated images to the user with a regenerate button.
        """
        user_id = message.from_user.id
        original_prompt = prompt if prompt else message.text.strip()

        # Store both original and enhanced prompts in user_data
        context.user_data['last_prompt'] = original_prompt
        context.user_data['last_enhanced_prompt'] = enhanced_prompt

        # Create the regenerate button
        keyboard = [[InlineKeyboardButton("🔄 Regenerate", callback_data="regenerate")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        successful_count = 0

        # Send all images
        for i, image_bio in enumerate(images):
            if image_bio:
                try:
                    # For the last image, attach the regenerate button
                    if i == len(images) - 1:
                        await message.reply_photo(
                            photo=image_bio,
                            caption=f"Image {i+1}/2",
                            reply_markup=reply_markup
                        )
                    else:
                        await message.reply_photo(
                            photo=image_bio,
                            caption=f"Image {i+1}/2"
                        )
                    successful_count += 1
                except Exception as e:
                    logger.error(f"Failed to send image {i+1}: {e}", exc_info=True)
                    await message.reply_text(f"Failed to send Image {i+1}.")
            else:
                await message.reply_text(f"Failed to generate Image {i+1}.")

        if successful_count < 2:
            await message.reply_text(
                f"Generated {successful_count} out of 2 images successfully."
            )

        # Inform the user about remaining requests
        try:
            remaining_requests = self.rate_limiter.get_remaining_requests(user_id)
            await message.reply_text(f"You have {remaining_requests} image generations remaining today.")
        except Exception as e:
            logger.error(f"Error fetching remaining requests for user {user_id}: {e}", exc_info=True)

    async def handle_regenerate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handles the regenerate button callback.
        """
        try:
            query = update.callback_query
            user_id = update.effective_user.id

            # Check rate limit
            if not self.rate_limiter.can_make_request(user_id):
                oldest_request = self.rate_limiter.get_oldest_request_time(user_id)
                if oldest_request:
                    reset_time = oldest_request + timedelta(hours=24)
                    remaining_time = reset_time - datetime.now()
                    hours = remaining_time.total_seconds() / 3600

                    await query.answer(
                        f"Daily limit reached. Try again in {hours:.1f} hours.",
                        show_alert=True
                    )
                    logger.warning(f"User {user_id} exceeded rate limit on regeneration.")
                    return

            await query.answer()  # Acknowledge the button click
            logger.info("Regenerate button clicked")

            # Get the stored prompts from user_data
            original_prompt = context.user_data.get('last_prompt')
            enhanced_prompt = context.user_data.get('last_enhanced_prompt')

            if not enhanced_prompt:
                # Fallback to getting prompts from storage if not in user_data
                enhanced_prompts = await self.prompt_storage.get_last_prompts(user_id)
                if not enhanced_prompts:
                    await query.message.reply_text("No previous prompts found to regenerate images.")
                    logger.info(f"No prompts found for user {user_id} to regenerate.")
                    return
                enhanced_prompt = enhanced_prompts[0]

            # Create a status message
            status_message = await query.message.reply_text("Starting to generate new images...")
            chat_id = update.effective_chat.id
            logger.info(f"User {user_id} in chat {chat_id} regenerating with enhanced prompt: {enhanced_prompt}")

            try:
                # Initial progress bar
                await self._update_progress(status_message, 0)
                await asyncio.sleep(2)

                # Skip prompt enhancement phase and use stored enhanced prompt
                await self._update_progress(status_message, 2)

                # Generate both images
                first_image_task = asyncio.create_task(
                    self.image_service.generate_single_image(enhanced_prompt)
                )
                second_image_task = asyncio.create_task(
                    self.image_service.generate_single_image(enhanced_prompt)
                )

                # Update progress while waiting for images
                for step in range(3, 10):
                    await asyncio.sleep(1.5)
                    await self._update_progress(status_message, step)

                # Wait for both images to complete
                images = await asyncio.gather(first_image_task, second_image_task)
                await self._update_progress(status_message, 10)

                # Send the regenerated images
                await self._send_images(
                    message=query.message,
                    context=context,
                    images=images,
                    prompt=original_prompt,
                    enhanced_prompt=enhanced_prompt
                )
                await status_message.delete()

            except Exception as e:
                logger.error(f"Error during regeneration for user {user_id}: {e}", exc_info=True)
                await status_message.edit_text("Failed to regenerate images. Please try again.")

        except Exception as e:
            logger.error(f"Error in handle_regenerate for user {user_id}: {e}", exc_info=True)
            try:
                await query.answer("An error occurred. Please try again.", show_alert=True)
            except Exception:
                logger.error("Failed to send error message to user", exc_info=True)

    async def view_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Allows users to view their last 5 prompts.
        """
        try:
            user_id = update.effective_user.id
            prompts = await self.prompt_storage.get_last_prompts(user_id)

            if not prompts:
                await update.message.reply_text("You have no prompt history.")
                logger.info(f"User {user_id} has no prompt history.")
                return

            history_text = "📝 *Your Last 5 Prompts:*\n\n"
            for idx, prompt in enumerate(prompts, 1):
                history_text += f"{idx}. {prompt}\n"

            await update.message.reply_text(history_text, parse_mode='Markdown')
            logger.info(f"Displayed prompt history for user {user_id}.")
        except Exception as e:
            logger.error(f"Error in view_history handler for user {update.effective_user.id}: {e}", exc_info=True)
            await update.message.reply_text("An error occurred while fetching your history. Please try again later.")

    async def _validate_prompt(self, prompt: str, update: Update) -> bool:
        """
        Validates the user's prompt.
        """
        try:
            if not prompt:
                await update.message.reply_text("Please provide a prompt to generate images.")
                return False

            if len(prompt) > MAX_PROMPT_LENGTH:
                await update.message.reply_text(
                    f"Your prompt is too long. Please limit it to {MAX_PROMPT_LENGTH} characters."
                )
                return False

            return True
        except Exception as e:
            logger.error(f"Error validating prompt for user {update.effective_user.id}: {e}", exc_info=True)
            await update.message.reply_text("An error occurred while validating your prompt. Please try again.")
            return False