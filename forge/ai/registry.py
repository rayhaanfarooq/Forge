"""AI provider registry and resolution"""

from typing import Optional, Type, Dict
from forge.ai.base import AIProvider, AIConfig
from forge.ai.openai import OpenAIProvider
from forge.ai.gemini import GeminiProvider

# Registry of available providers
PROVIDERS: Dict[str, Type[AIProvider]] = {
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
}


def register_provider(name: str, provider_class: Type[AIProvider]) -> None:
    """Register a new AI provider"""
    PROVIDERS[name] = provider_class


def get_provider(name: str) -> Optional[Type[AIProvider]]:
    """Get a provider class by name"""
    return PROVIDERS.get(name.lower())


def resolve_provider(config: AIConfig) -> AIProvider:
    """
    Resolve and instantiate an AI provider from configuration
    
    Args:
        config: AI configuration
    
    Returns:
        Instantiated AI provider
    
    Raises:
        ValueError: If provider is not found or invalid
    """
    provider_class = get_provider(config.provider)
    
    if provider_class is None:
        available = ", ".join(PROVIDERS.keys())
        raise ValueError(
            f"Unknown AI provider: {config.provider}. "
            f"Available providers: {available}"
        )
    
    try:
        return provider_class(config)
    except Exception as e:
        raise ValueError(f"Failed to initialize provider {config.provider}: {e}")


def get_available_providers() -> list[str]:
    """Get list of available provider names"""
    return list(PROVIDERS.keys())

