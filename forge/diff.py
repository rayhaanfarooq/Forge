"""File diff and change detection utilities"""

from pathlib import Path
from typing import Optional
from forge.config import load_config, find_repo_root
from forge.git_ops import get_changed_files_since_base


def filter_source_files(
    files: list[str],
    include_patterns: list[str],
    exclude_patterns: list[str],
    extensions: list[str],
) -> list[str]:
    """Filter files based on include/exclude patterns and extensions"""
    filtered = []
    
    for file_path in files:
        path = Path(file_path)
        
        # Check extension
        if path.suffix not in extensions:
            continue
        
        # Check exclude patterns
        excluded = False
        for pattern in exclude_patterns:
            if pattern in str(path):
                excluded = True
                break
        if excluded:
            continue
        
        # Check include patterns (if any specified)
        if include_patterns:
            included = False
            for pattern in include_patterns:
                if pattern in str(path):
                    included = True
                    break
            if not included:
                continue
        
        filtered.append(file_path)
    
    return filtered


def get_changed_source_files(
    repo_root: Optional[Path] = None,
    config=None,
) -> list[str]:
    """Get changed source files since base branch"""
    if repo_root is None:
        repo_root = find_repo_root()
        if repo_root is None:
            raise ValueError("Not in a Git repository")
    
    if config is None:
        config = load_config(repo_root)
    
    # Get all changed files
    changed_files = get_changed_files_since_base(config.base_branch, repo_root)
    
    # Filter based on language
    if config.language == "python":
        extensions = [".py"]
    else:
        extensions = [".py"]  # Default to Python for MVP
    
    # Filter source files
    source_files = filter_source_files(
        changed_files,
        config.include,
        config.exclude,
        extensions,
    )
    
    return source_files

