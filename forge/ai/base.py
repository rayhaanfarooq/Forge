"""Base AI provider interface"""

from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel


class AIConfig(BaseModel):
    """Configuration for AI provider"""
    provider: str
    model: str
    temperature: float = 0.3
    max_tokens: Optional[int] = None
    api_key: Optional[str] = None


class AIProvider(ABC):
    """Base class for AI providers"""
    
    def __init__(self, config: AIConfig):
        """Initialize provider with configuration"""
        self.config = config
        self._validate_config()
    
    @abstractmethod
    def _validate_config(self) -> None:
        """Validate provider-specific configuration"""
        pass
    
    @abstractmethod
    def generate_tests(self, prompt: str) -> str:
        """
        Generate test code from a prompt
        
        Args:
            prompt: The prompt containing code and instructions
        
        Returns:
            Generated test code
        """
        pass
    
    @abstractmethod
    def get_supported_models(self) -> list[str]:
        """Get list of supported models for this provider"""
        pass
    
    def validate_model(self, model: str) -> bool:
        """Validate that the model is supported"""
        return model in self.get_supported_models()

