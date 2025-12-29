"""Google Gemini provider implementation"""

import os
from typing import Optional
from google import genai
from forge.ai.base import AIProvider, AIConfig


class GeminiProvider(AIProvider):
    """Google Gemini provider for test generation"""
    
    SUPPORTED_MODELS = [
        "gemini-2.0-flash-lite",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-pro",
        "gemini-1.0-pro",
        "gemini-2.0-flash-exp",
    ]
    
    def __init__(self, config: AIConfig):
        """Initialize Gemini provider"""
        super().__init__(config)
        
        api_key = config.api_key or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY not found. "
                "Set it as an environment variable or in config."
            )
        
        self.client = genai.Client(api_key=api_key)
    
    def _validate_config(self) -> None:
        """Validate Gemini-specific configuration"""
        if not self.validate_model(self.config.model):
            raise ValueError(
                f"Unsupported model: {self.config.model}. "
                f"Supported models: {', '.join(self.SUPPORTED_MODELS)}"
            )
    
    def generate_tests(self, prompt: str) -> str:
        """Generate tests using Gemini API"""
        try:
            # Build the full prompt with system instructions
            full_prompt = f"""You are a Python testing expert. Generate minimal, readable pytest tests.

{prompt}"""
            
            # Build generation config with optional parameters
            # Note: GenerateContentConfig uses camelCase for parameter names
            config_params = {}
            if self.config.temperature is not None:
                config_params["temperature"] = self.config.temperature
            if self.config.max_tokens:
                config_params["maxOutputTokens"] = self.config.max_tokens
            
            # Use the new API - temperature and other params go in config
            if config_params:
                generation_config = genai.types.GenerateContentConfig(**config_params)
                response = self.client.models.generate_content(
                    model=self.config.model,
                    contents=full_prompt,
                    config=generation_config,
                )
            else:
                response = self.client.models.generate_content(
                    model=self.config.model,
                    contents=full_prompt,
                )
            
            return response.text.strip()
        except Exception as e:
            raise RuntimeError(f"Gemini API error: {e}")
    
    def get_supported_models(self) -> list[str]:
        """Get list of supported Gemini models"""
        return self.SUPPORTED_MODELS.copy()

