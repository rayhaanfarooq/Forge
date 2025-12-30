"""Validation utilities for Forge"""

from pathlib import Path
from typing import Optional
from forge.core.git_ops import is_git_repo, run_git_command, is_clean_working_tree


def assert_git_repo(repo_root: Optional[Path] = None) -> Path:
    """Assert that we're in a Git repository, return repo root"""
    if repo_root is None:
        repo_root = Path.cwd()
    
    if not is_git_repo(repo_root):
        raise ValueError(
            "Not in a Git repository. "
            "Please run this command from within a Git repository."
        )
    
    # Find actual repo root
    current = Path(repo_root).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    
    raise ValueError("Could not find Git repository root")


def assert_no_rebase(repo_root: Path) -> None:
    """Assert that no rebase or merge is in progress"""
    git_dir = repo_root / ".git"
    
    # Check for rebase
    rebase_files = [
        git_dir / "rebase-apply",
        git_dir / "rebase-merge",
        git_dir / "REBASE_HEAD",
    ]
    
    for rebase_file in rebase_files:
        if rebase_file.exists():
            raise RuntimeError(
                "A rebase is in progress. "
                "Please complete or abort the rebase before creating a new branch."
            )
    
    # Check for merge
    merge_files = [
        git_dir / "MERGE_HEAD",
        git_dir / "MERGE_MODE",
    ]
    
    for merge_file in merge_files:
        if merge_file.exists():
            raise RuntimeError(
                "A merge is in progress. "
                "Please complete or abort the merge before creating a new branch."
            )


def assert_clean_working_tree(repo_root: Path, require_clean: bool = True) -> None:
    """Assert that working tree is clean (if required)"""
    if not require_clean:
        return
    
    if not is_clean_working_tree(repo_root):
        raise RuntimeError(
            "Working tree has uncommitted changes. "
            "Please commit or stash your changes before creating a new branch."
        )


def normalize_branch_name(name: str, prefix: str = "fg/") -> str:
    """
    Normalize branch name:
    - Lowercase
    - Replace spaces with hyphens
    - Remove special characters (keep alphanumeric, hyphens, underscores)
    - Add prefix if not present
    
    Args:
        name: Raw branch name
        prefix: Prefix to add (default: "fg/")
    
    Returns:
        Normalized branch name
    """
    import re
    
    # Lowercase
    normalized = name.lower()
    
    # Replace spaces and multiple hyphens/underscores with single hyphen
    normalized = re.sub(r'[\s_]+', '-', normalized)
    
    # Remove invalid characters (keep alphanumeric, hyphens, forward slashes)
    normalized = re.sub(r'[^a-z0-9/-]', '', normalized)
    
    # Remove multiple consecutive hyphens
    normalized = re.sub(r'-+', '-', normalized)
    
    # Remove leading/trailing hyphens
    normalized = normalized.strip('-')
    
    # Add prefix if not already present
    if not normalized.startswith(prefix):
        normalized = prefix + normalized
    
    # Remove duplicate slashes
    normalized = re.sub(r'/+', '/', normalized)
    
    if not normalized or normalized == prefix:
        raise ValueError(f"Invalid branch name: '{name}'")
    
    return normalized


def validate_branch_name(name: str) -> bool:
    """Validate that branch name follows Git conventions"""
    import re
    
    # Git branch name rules:
    # - Cannot contain consecutive dots (..)
    # - Cannot end with .lock
    # - Cannot contain certain special characters
    # - Cannot be empty
    
    if not name or len(name) > 255:
        return False
    
    if '..' in name:
        return False
    
    if name.endswith('.lock'):
        return False
    
    if name.endswith('.'):
        return False
    
    # Check for invalid characters (Git allows most, but we're conservative)
    if re.search(r'[~^:?*\[\]\\]', name):
        return False
    
    return True

