#config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("tel_imagaibot")
API_KEY = os.getenv('image_api_key')

import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("bot_token")
if not BOT_TOKEN:
    raise ValueError("Bot token not found in environment variables")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

# Additional configuration variables can be added here

# Image Generation Settings
IMAGE_COUNT = int(os.getenv('IMAGE_COUNT', 2))
IMAGE_WIDTH = int(os.getenv('IMAGE_WIDTH', 1120))
IMAGE_HEIGHT = int(os.getenv('IMAGE_HEIGHT', 1424))
IMAGE_STEPS = int(os.getenv('IMAGE_STEPS', 4))
MODEL_NAME = os.getenv('MODEL_NAME', "black-forest-labs/FLUX.1-schnell-Free")
TRANSLATION_MODEL = os.getenv('TRANSLATION_MODEL', "meta-llama/Llama-3.3-70B-Instruct")
MAX_PROMPT_LENGTH = int(os.getenv('MAX_PROMPT_LENGTH', 600))
CONCURRENT_IMAGE_GENERATIONS = int(os.getenv('CONCURRENT_IMAGE_GENERATIONS', 5))

# Validate configurations
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment variables.")
if not API_KEY:
    raise ValueError("API_KEY is not set in environment variables.")