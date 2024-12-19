#g4f_client.py
import os
import logging
from typing import List, Dict, Any, Union
from dotenv import load_dotenv
from g4f.client import AsyncClient

from g4f.models import(
    Model, Blackbox, DDG, HuggingChat, Pizzagpt
)
from g4f.Provider import IterListProvider

load_dotenv()
logger = logging.getLogger(__name__)

# g4f_client.py
class G4FClient:
    def __init__(self):
        self.client = AsyncClient()

    async def generate_response(
        self, 
        model: Union[str, Model], 
        messages: List[Dict[str, Any]], 
        temperature: float = 0.75, 
        max_tokens: int = 700, 
        top_p: float = 0.60, 
        stop: List[str] = ["<|eot_id|>", "<|eom_id|>"]
    ):
        try:
            # If model is a Model object, use its provider directly
            if isinstance(model, Model):
                provider = model.best_provider
                model_name = model.name
            else:
                model_name = model
                provider = None

            response = await self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                provider=provider,  # Add the provider parameter
                temperature=temperature,
                stream=True,
                max_tokens=max_tokens,
                top_p=top_p,
                stop=stop
            )

            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Error generating G4F response: {e}")
            raise
    async def close(self):
        # Implement if necessary, depending on AsyncClient implementation
        pass

# Example usage
async def main():
    G4F_MODEL = Model(
        name="gpt-4-mini",
        base_provider='OpenAI',
        best_provider=IterListProvider([
            DDG
        ])
    )
    
    chat_history = []
    print("Welcome to amir gpt 3 🤖\n")

    client = G4FClient()

    while True:
        user_prompt = input("You: ")
        if not user_prompt.strip():
            continue

        chat_history.append({"role": "user", "content": user_prompt})

        try:
            response_stream = await client.generate_response(  # Add await here
                model=G4F_MODEL,
                max_tokens=1024,
                messages=[
                    {"role": "system", "content": "assistant"},
                    *chat_history
                ]
            )

            final_response = ""
            async for chunk in response_stream:
                final_response += chunk
                print(chunk, end='', flush=True)

            chat_history.append({"role": "assistant", "content": final_response})
            print("\n")

        except Exception as e:
            print(f"An error occurred: {e}")

    await client.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())