"""Google Gemini provider implementation"""

import os
from typing import Optional
import google.generativeai as genai
from forge.ai.base import AIProvider, AIConfig


class GeminiProvider(AIProvider):
    """Google Gemini provider for test generation"""
    
    SUPPORTED_MODELS = [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-pro",
        "gemini-1.0-pro",
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
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(self.config.model)
    
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
            
            generation_config = genai.types.GenerationConfig(
                temperature=self.config.temperature,
            )
            
            if self.config.max_tokens:
                generation_config.max_output_tokens = self.config.max_tokens
            
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config,
            )
            
            return response.text.strip()
        except Exception as e:
            raise RuntimeError(f"Gemini API error: {e}")
    
    def get_supported_models(self) -> list[str]:
        """Get list of supported Gemini models"""
        return self.SUPPORTED_MODELS.copy()

