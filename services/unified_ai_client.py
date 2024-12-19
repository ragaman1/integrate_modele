# unified_ai_client.py

import os
import logging
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv
from g4f.models import Model

from services.openai_client import OpenAIClient
from services.g4f_client import G4FClient

load_dotenv()
logger = logging.getLogger(__name__)

from typing import List, Dict, Any, Optional, Union
from g4f.models import Model
from g4f.Provider import DDG, Pizzagpt, ChatgptFree, IterListProvider

class UnifiedAIClient:
    # Define your models
    OPENAI_MODELS = {
        "Meta-Llama-3.3-70B-Instruct": "Meta-Llama-3.3-70B-Instruct",
        "Qwen2.5-Coder-32B-Instruct": "Qwen2.5-Coder-32B-Instruct"
    }

    G4F_MODEL = Model(
        name='gpt-4o-min',
        base_provider='OpenAI',
        best_provider=IterListProvider([
            DDG, Pizzagpt, ChatgptFree,
        ])
    )

    def __init__(self, backend: Optional[str] = None):
        self._backend = backend or os.getenv("AI_BACKEND", "g4f").lower()
        
        # Only initialize the specified backend
        if self._backend in ['openai', 'auto']:
            self.openai_client = OpenAIClient()
        if self._backend in ['g4f', 'auto']:
            self.g4f_client = G4FClient()
            
        logger.info(f"Initialized UnifiedAIClient with backend: {self._backend}")

    def _get_appropriate_model(self, model: Union[str, Model], backend: str) -> Union[str, Model]:
        """Get the appropriate model based on the backend"""
        if backend == 'openai':
            if isinstance(model, str):
                if model in self.OPENAI_MODELS:
                    return model
                logger.warning(f"Unknown OpenAI model: {model}, using default Qwen2.5-Coder-32B-Instruct")
                return "Qwen2.5-Coder-32B-Instruct"
            return "Meta-Llama-3.3-70B-Instruct"
            
        elif backend == 'g4f':
            if isinstance(model, Model):
                return model
            return self.G4F_MODEL

    async def generate_response(
        self,
        model: Union[str, Model],
        messages: List[Dict[str, Any]],
        temperature: float = 0.75,
        max_tokens: int = 900,
        top_p: float = 0.60,
        stop: Optional[List[str]] = None
    ):
        backends_tried = []
        
        # Determine which backends to try based on initialization
        if self._backend == "openai":
            backends = ["openai"]
        elif self._backend == "g4f":
            backends = ["g4f"]
        else:  # auto
            backends = ["openai", "g4f"]

        for backend in backends:
            try:
                if backend == "openai":
                    logger.info("Using OpenAI backend.")
                    model_name = self._get_appropriate_model(model, 'openai')
                    async for chunk in self.openai_client.generate_response(
                        model=model_name,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        top_p=top_p
                    ):
                        yield chunk
                    return

                elif backend == "g4f":
                    logger.info("Using G4F backend.")
                    g4f_model = self._get_appropriate_model(model, 'g4f')
                    async for chunk in self.g4f_client.generate_response(
                        model=g4f_model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        top_p=top_p,
                        stop=stop or ["<|eot_id|>", "<|eom_id|>"]
                    ):
                        yield chunk
                    return

            except Exception as e:
                logger.error(f"Error with backend '{backend}': {e}", exc_info=True)
                backends_tried.append(backend)
                continue

        logger.error(f"All backends failed. Backends attempted: {backends_tried}")
        raise RuntimeError("Failed to generate response using all available backends.")

    async def close(self):
        if hasattr(self, 'openai_client'):
            await self.openai_client.close()
        if hasattr(self, 'g4f_client'):
            await self.g4f_client.close()