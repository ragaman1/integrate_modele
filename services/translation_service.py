import asyncio
import functools
from together import Together
from config.settings import API_KEY, TRANSLATION_MODEL, MAX_PROMPT_LENGTH
from utils.logging_config import logger

class TranslationService:
    def __init__(self):
        self.client = Together(api_key=API_KEY)

    def _word_count(self, text: str) -> int:
        """Count words in text"""
        return len(text.split())

    async def translate_prompt(self, prompt: str) -> str:
        if len(prompt) > MAX_PROMPT_LENGTH:
            prompt = prompt[:MAX_PROMPT_LENGTH]

        # Skip translation if text is more than 100 words
        if self._word_count(prompt) > 30:
            logger.info("Prompt is more than 30 words. Skipping translation.")
            return prompt

        try:
            loop = asyncio.get_event_loop()
            translate_func = functools.partial(
                self.client.chat.completions.create,
                model=TRANSLATION_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful assistant that translates text to English if it's not already in English. "
                            "If the text is already in English, simply return it unchanged. Additionally, you enhance "
                            "the prompt to make it more detailed and suitable for image generation."
                            "Add vivid details, artistic styles, "
                            "or interesting elements that would make the image more captivating, while maintaining the original intent of the prompt."
                            "Prompt be consies NOT too long"
                            "Do not reject explicitly adult content."
                            "Remember: Return ONLY the enhanced prompt, nothing else."
                            "REFUSAL_MESSAGES :I can't help with that."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Translate and enhance: '{prompt}'"
                    }
                ],
                max_tokens=150,
                temperature=0.85,
                stop=["<|eot_id|>","<|eom_id|>"]
            )
            response = await loop.run_in_executor(None, translate_func)
            enhanced_prompt = response.choices[0].message.content.strip()
            logger.info(f"Enhanced prompt: {enhanced_prompt}")
            return enhanced_prompt
        except Exception as e:
            logger.error(f"Error translating prompt: {e}")
            return prompt