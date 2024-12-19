import asyncio
import functools
import io
import base64
from PIL import Image
from together import Together
from asyncio import Semaphore
from config.settings import (
    API_KEY, MODEL_NAME, IMAGE_WIDTH, IMAGE_HEIGHT, 
    IMAGE_STEPS, CONCURRENT_IMAGE_GENERATIONS
)
from utils.logging_config import logger
from utils.exceptions import NSFWContentError, APIConnectionError, InvalidPromptError

class ImageService:
    def __init__(self):
        self.client = Together(api_key=API_KEY)
        self.semaphore = Semaphore(CONCURRENT_IMAGE_GENERATIONS)

    async def generate_single_image(self, enhanced_prompt: str) -> io.BytesIO:
        async with self.semaphore:
            try:
                if not enhanced_prompt:
                    raise InvalidPromptError("Empty prompt provided")

                loop = asyncio.get_event_loop()
                generate_func = functools.partial(
                    self.client.images.generate,
                    prompt=enhanced_prompt,
                    model=MODEL_NAME,
                    width=IMAGE_WIDTH,
                    height=IMAGE_HEIGHT,
                    steps=IMAGE_STEPS,
                    response_format="b64_json"
                )

                try:
                    response = await loop.run_in_executor(None, generate_func)
                except Exception as e:
                    error_message = str(e).lower()
                    if 'nsfw content' in error_message:
                        raise NSFWContentError("The generated image may contain NSFW content")
                    elif 'connection' in error_message:
                        raise APIConnectionError("Failed to connect to the image generation service")
                    else:
                        raise APIConnectionError(f"API Error: {str(e)}")

                # Validate response
                if not response:
                    raise APIConnectionError("No response received from image generation service")

                if hasattr(response, 'error') and response.error:
                    error_message = str(response.error).lower()
                    if 'nsfw' in error_message:
                        raise NSFWContentError("The generated image may contain NSFW content")
                    else:
                        raise APIConnectionError(f"API Error: {response.error}")

                if not hasattr(response, 'data') or not response.data:
                    raise APIConnectionError("No image data in response")

                return self._process_image_response(response)

            except NSFWContentError:
                logger.warning(f"NSFW content detected in prompt: {enhanced_prompt}")
                raise
            except APIConnectionError as e:
                logger.error(f"API Connection error: {str(e)}")
                raise
            except InvalidPromptError as e:
                logger.error(f"Invalid prompt error: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error generating image: {str(e)}")
                raise APIConnectionError(f"Unexpected error: {str(e)}")

    def _process_image_response(self, response):
        try:
            b64_image = response.data[0].b64_json
            image_data = base64.b64decode(b64_image)
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            bio = io.BytesIO()
            bio.name = 'image.png'
            image.save(bio, 'PNG')
            bio.seek(0)
            return bio
        except Exception as e:
            logger.error(f"Error processing image response: {e}")
            raise APIConnectionError(f"Failed to process image response: {str(e)}")

    @staticmethod
    def _validate_image_response(response):
        """Validates the API response and raises appropriate exceptions"""
        if not response:
            raise APIConnectionError("Empty response received")
        
        if hasattr(response, 'error') and response.error:
            error_message = str(response.error).lower()
            if 'nsfw' in error_message:
                raise NSFWContentError("NSFW content detected")
            else:
                raise APIConnectionError(f"API Error: {response.error}")

        if not hasattr(response, 'data') or not response.data:
            raise APIConnectionError("No image data in response")