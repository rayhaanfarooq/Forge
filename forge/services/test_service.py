"""Test generation service using AI"""

from pathlib import Path
from typing import Optional, List
from forge.ai.base import AIProvider, AIConfig
from forge.ai.registry import resolve_provider
from forge.ai.config import parse_ai_config
from forge.core.config import ForgeConfig
from forge.utils.ast_parser import (
    get_untested_functions_with_info,
    extract_code_for_functions,
)


class TestService:
    """Service for generating tests using AI"""
    
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
        forge_config: Optional[ForgeConfig] = None,
    ):
        """
        Initialize test service with AI provider
        
        Args:
            provider: AI provider name (overrides config)
            model: Model name (overrides config)
            temperature: Temperature setting (overrides config)
            max_tokens: Max tokens (overrides config)
            api_key: API key (overrides env var)
            forge_config: Forge configuration (for reading AI settings)
        """
        # Parse AI configuration with overrides
        if forge_config is None:
            from forge.core.config import load_config, find_repo_root, load_env_file
            try:
                repo_root = find_repo_root()
                if repo_root:
                    load_env_file(repo_root)  # Load .env file before parsing config
                    forge_config = load_config(repo_root)
            except (FileNotFoundError, ValueError):
                forge_config = None
                # Still try to load .env even if config doesn't exist
                repo_root = find_repo_root()
                if repo_root:
                    load_env_file(repo_root)
        else:
            # If forge_config is provided, we still need to load .env file
            # for API keys (forge_config doesn't contain API keys for security)
            from forge.core.config import find_repo_root, load_env_file
            repo_root = find_repo_root()
            if repo_root:
                load_env_file(repo_root)
        
        ai_config = parse_ai_config(
            forge_config or ForgeConfig(),
            provider_override=provider,
            model_override=model,
            temperature_override=temperature,
            max_tokens_override=max_tokens,
        )
        
        # Override API key if provided
        if api_key:
            ai_config.api_key = api_key
        
        # Resolve and initialize provider
        self.provider: AIProvider = resolve_provider(ai_config)
        self.config = ai_config
    
    def generate_tests_for_file(
        self,
        file_path: str,
        code: str,
        test_file_path: Path,
        existing_test_code: Optional[str] = None,
        incremental: bool = False,
    ) -> str:
        """
        Generate pytest tests for a Python file
        
        Args:
            file_path: Path to source file
            code: Source code content
            test_file_path: Path where test file should be written
            existing_test_code: Existing test file content (for incremental updates)
            incremental: If True, only generate tests for untested functions
        
        Returns:
            Generated test code
        """
        if incremental and existing_test_code:
            # Find untested functions
            untested_funcs = get_untested_functions_with_info(code, existing_test_code)
            if not untested_funcs:
                # All functions already tested, return empty string
                return ""
            
            # Extract code for only untested functions
            function_names = [f.name for f in untested_funcs]
            function_code = extract_code_for_functions(code, function_names)
            
            if not function_code or not function_code.strip():
                return ""
            
            prompt = self._build_prompt_for_functions(file_path, function_code, function_names)
        else:
            prompt = self._build_prompt(file_path, code)
        
        return self.provider.generate_tests(prompt)
    
    def _build_prompt(self, file_path: str, code: str) -> str:
        """Build the prompt for test generation"""
        return f"""Generate pytest tests for the following Python file.

Rules:
- Only test public functions and methods (those not starting with _)
- Do not invent imports - only use imports that are actually in the file or standard library
- Use pytest
- Keep tests minimal and readable
- Test file should be named test_{Path(file_path).stem}.py
- Import the module/function being tested correctly based on the file path
- Do not generate tests for private methods (starting with _)
- Focus on testing the public API

File: {file_path}

```python
{code}
```

Generate only the test code, without any explanations or markdown formatting."""
    
    def _build_prompt_for_functions(self, file_path: str, function_code: str, function_names: List[str]) -> str:
        """Build the prompt for generating tests for specific functions only"""
        func_list = ", ".join(function_names)
        return f"""Generate pytest tests for the following functions from {file_path}.

Functions to test: {func_list}

Rules:
- Only test the specified functions (do not generate tests for functions not shown)
- Do not invent imports - only use imports that are actually in the file or standard library
- Use pytest
- Keep tests minimal and readable
- Import the module/function being tested correctly based on the file path
- Focus on testing the public API of these specific functions

```python
{function_code}
```

Generate only the test code for these functions, without any explanations or markdown formatting."""

