"""OpenAI provider implementation"""

import os
from typing import Optional
import openai
from forge.ai.base import AIProvider, AIConfig


class OpenAIProvider(AIProvider):
    """OpenAI provider for test generation"""
    
    SUPPORTED_MODELS = [
        "gpt-4-turbo-preview",
        "gpt-4",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-mini",  # Alias for gpt-4o-mini
        "gpt-3.5-turbo",
    ]
    
    def __init__(self, config: AIConfig):
        """Initialize OpenAI provider"""
        super().__init__(config)
        
        api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found. "
                "Set it as an environment variable or in config."
            )
        
        self.client = openai.OpenAI(api_key=api_key)
    
    def _validate_config(self) -> None:
        """Validate OpenAI-specific configuration"""
        if not self.validate_model(self.config.model):
            raise ValueError(
                f"Unsupported model: {self.config.model}. "
                f"Supported models: {', '.join(self.SUPPORTED_MODELS)}"
            )
    
    def generate_tests(self, prompt: str) -> str:
        """Generate tests using OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Python testing expert. Generate minimal, readable pytest tests.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            return response.choices[0].message.content.strip()
        except openai.OpenAIError as e:
            raise RuntimeError(f"OpenAI API error: {e}")
    
    def get_supported_models(self) -> list[str]:
        """Get list of supported OpenAI models"""
        return self.SUPPORTED_MODELS.copy()

