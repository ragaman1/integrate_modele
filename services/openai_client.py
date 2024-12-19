# openai_client.py
import os
import logging
from typing import List, Dict, Any
import openai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class OpenAIClient:
    def __init__(self):
        api_key = os.getenv("api_key")
        if not api_key:
            raise ValueError("OpenAI API key not found in environment variables")
        
        # Initialize the client with the correct base URL
        self.client = openai.AsyncClient(
            api_key=api_key,
            base_url="https://api.sambanova.ai/v1/"  # Note the trailing slash
        )

    async def generate_response(self, model: str, messages: List[Dict[str, Any]], 
                              temperature: float = 0.75, max_tokens: int = 800, 
                              top_p: float = 0.60):
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                stream=True,
                max_tokens=max_tokens,
                stop=["<|eot_id|>","<|eom_id|>"],
                top_p=top_p
            )

            async for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield delta.content

        except Exception as e:
            logger.error(f"Error generating OpenAI response: {e}")
            raise

    async def close(self):
        await self.client.close()


