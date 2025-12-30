"""AI configuration parsing and resolution"""

import os
from typing import Optional
from forge.ai.base import AIConfig
from forge.config import ForgeConfig


def parse_ai_config(
    forge_config: ForgeConfig,
    provider_override: Optional[str] = None,
    model_override: Optional[str] = None,
    temperature_override: Optional[float] = None,
    max_tokens_override: Optional[int] = None,
) -> AIConfig:
    """
    Parse AI configuration with CLI overrides
    
    Priority order:
    1. CLI flags (highest)
    2. .gt.yml configuration
    3. Environment variables (FORGE_PROVIDER or FORGE_AI_PROVIDER)
    4. Defaults
    
    Args:
        forge_config: Forge configuration from .gt.yml
        provider_override: CLI provider override
        model_override: CLI model override
        temperature_override: CLI temperature override
        max_tokens_override: CLI max_tokens override
    
    Returns:
        Resolved AI configuration
    """
    # Get AI config from forge_config (if present)
    ai_config_dict = getattr(forge_config, "ai", None) or {}
    
    # Resolve provider (CLI > config > env var > default)
    # Support both FORGE_PROVIDER and FORGE_AI_PROVIDER for convenience
    provider = (
        provider_override
        or ai_config_dict.get("provider")
        or os.getenv("FORGE_PROVIDER")
        or os.getenv("FORGE_AI_PROVIDER")
        or "openai"
    )
    
    # Resolve model (CLI > config > default)
    model = (
        model_override
        or ai_config_dict.get("model")
        or _get_default_model(provider)
    )
    
    # Resolve temperature (CLI > config > default)
    temperature = (
        temperature_override
        if temperature_override is not None
        else ai_config_dict.get("temperature", 0.3)
    )
    
    # Resolve max_tokens (CLI > config > default)
    max_tokens = (
        max_tokens_override
        if max_tokens_override is not None
        else ai_config_dict.get("max_tokens")
    )
    
    # Get API key from environment (never from config)
    # Note: .env file should be loaded before this function is called
    api_key = None
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
    elif provider == "gemini":
        api_key = os.getenv("GOOGLE_API_KEY")
    
    return AIConfig(
        provider=provider,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key,
    )


def _get_default_model(provider: str) -> str:
    """Get default model for a provider"""
    defaults = {
        "openai": "gpt-4o-mini",  # Cost-effective default
        "anthropic": "claude-3-opus-20240229",
        "gemini": "gemini-2.0-flash-lite",  # Fast and cost-effective
    }
    return defaults.get(provider.lower(), "gpt-4o-mini")

