"""Configuration management for Forge"""

import os
from pathlib import Path
from typing import Optional
import yaml
from pydantic import BaseModel
from typing import Optional, Dict, Any

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


class AIConfigSection(BaseModel):
    """AI configuration section in .gt.yml"""
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class ForgeConfig(BaseModel):
    """Forge configuration model"""
    base_branch: str = "main"
    language: str = "python"
    test_framework: str = "pytest"
    test_dir: str = "tests/"
    include: list[str] = ["src/"]
    exclude: list[str] = ["venv/", "node_modules/"]
    ai: Optional[Dict[str, Any]] = None  # AI configuration section


CONFIG_FILE = ".gt.yml"


def find_repo_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """Find the Git repository root by looking for .git directory"""
    if start_path is None:
        start_path = Path.cwd()
    
    current = Path(start_path).resolve()
    
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    
    return None


def get_config_path(repo_root: Optional[Path] = None) -> Path:
    """Get the path to the Forge config file"""
    if repo_root is None:
        repo_root = find_repo_root()
        if repo_root is None:
            raise ValueError("Not in a Git repository")
    
    return repo_root / CONFIG_FILE


def load_config(repo_root: Optional[Path] = None) -> ForgeConfig:
    """Load Forge configuration from .gt.yml"""
    config_path = get_config_path(repo_root)
    
    if not config_path.exists():
        raise FileNotFoundError(
            f"Forge not initialized. Run 'fg init' first. "
            f"Expected config at {config_path}"
        )
    
    with open(config_path, "r") as f:
        data = yaml.safe_load(f) or {}
    
    # Handle AI config section if present
    if "ai" in data and isinstance(data["ai"], dict):
        # Keep as dict for parsing in ai/config.py
        pass
    
    return ForgeConfig(**data)


def save_config(config: ForgeConfig, repo_root: Optional[Path] = None) -> None:
    """Save Forge configuration to .gt.yml"""
    config_path = get_config_path(repo_root)
    
    config_dict = config.model_dump()
    
    with open(config_path, "w") as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
    
    # Ensure config file is in .gitignore if it exists
    repo_root = repo_root or find_repo_root()
    if repo_root:
        gitignore_path = repo_root / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path, "r") as f:
                content = f.read()
            if CONFIG_FILE not in content:
                with open(gitignore_path, "a") as f:
                    f.write(f"\n{CONFIG_FILE}\n")


def load_env_file(repo_root: Optional[Path] = None) -> None:
    """Load .env file from repository root if it exists"""
    if load_dotenv is None:
        return  # python-dotenv not installed
    
    if repo_root is None:
        repo_root = find_repo_root()
    
    if repo_root:
        env_file = repo_root / ".env"
        if env_file.exists():
            # Load .env file - override=False means don't override existing env vars
            # This will load env vars from .env if they don't already exist in environment
            # load_dotenv can take the path as first positional argument or as dotenv_path keyword
            load_dotenv(str(env_file), override=False)
        # Note: We don't raise an error if .env doesn't exist - API keys can be set via environment variables


def detect_language(repo_root: Path) -> str:
    """Detect the primary language of the repository"""
    # Check for Python files
    python_files = list(repo_root.rglob("*.py"))
    if python_files:
        return "python"
    
    # Future: Add detection for other languages
    return "python"  # Default to Python for MVP

