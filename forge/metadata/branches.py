"""Branch metadata management for Forge"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel


class BranchMetadata(BaseModel):
    """Metadata for a single branch"""
    base: str
    status: str = "in-progress"
    created_at: str
    tests_generated: bool = False
    tests_passing: bool = False
    updated_at: Optional[str] = None


class BranchesMetadata(BaseModel):
    """Container for all branch metadata"""
    branches: Dict[str, BranchMetadata] = {}


METADATA_DIR = ".forge"
BRANCHES_FILE = "branches.json"


def get_metadata_dir(repo_root: Path) -> Path:
    """Get the Forge metadata directory path"""
    return repo_root / METADATA_DIR


def get_branches_file(repo_root: Path) -> Path:
    """Get the branches metadata file path"""
    return get_metadata_dir(repo_root) / BRANCHES_FILE


def load_branches_metadata(repo_root: Path) -> BranchesMetadata:
    """Load branch metadata from file"""
    branches_file = get_branches_file(repo_root)
    
    if not branches_file.exists():
        return BranchesMetadata()
    
    try:
        with open(branches_file, "r") as f:
            data = json.load(f)
        return BranchesMetadata(**data)
    except (json.JSONDecodeError, Exception):
        # If file is corrupted, return empty metadata
        return BranchesMetadata()


def save_branches_metadata(metadata: BranchesMetadata, repo_root: Path) -> None:
    """Save branch metadata to file"""
    metadata_dir = get_metadata_dir(repo_root)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    
    branches_file = get_branches_file(repo_root)
    
    with open(branches_file, "w") as f:
        json.dump(metadata.model_dump(), f, indent=2)


def register_branch(
    branch_name: str,
    base_branch: str,
    repo_root: Path,
) -> None:
    """Register a new branch in metadata"""
    metadata = load_branches_metadata(repo_root)
    
    now = datetime.utcnow().isoformat() + "Z"
    
    branch_meta = BranchMetadata(
        base=base_branch,
        status="in-progress",
        created_at=now,
        tests_generated=False,
        tests_passing=False,
    )
    
    metadata.branches[branch_name] = branch_meta
    
    save_branches_metadata(metadata, repo_root)


def update_branch_status(
    branch_name: str,
    repo_root: Path,
    status: Optional[str] = None,
    tests_generated: Optional[bool] = None,
    tests_passing: Optional[bool] = None,
) -> None:
    """Update branch metadata"""
    metadata = load_branches_metadata(repo_root)
    
    if branch_name not in metadata.branches:
        # Branch not registered, create it
        register_branch(branch_name, "main", repo_root)
        metadata = load_branches_metadata(repo_root)
    
    branch_meta = metadata.branches[branch_name]
    
    if status is not None:
        branch_meta.status = status
    
    if tests_generated is not None:
        branch_meta.tests_generated = tests_generated
    
    if tests_passing is not None:
        branch_meta.tests_passing = tests_passing
    
    branch_meta.updated_at = datetime.utcnow().isoformat() + "Z"
    
    save_branches_metadata(metadata, repo_root)


def get_branch_metadata(
    branch_name: str,
    repo_root: Path,
) -> Optional[BranchMetadata]:
    """Get metadata for a specific branch"""
    metadata = load_branches_metadata(repo_root)
    return metadata.branches.get(branch_name)


def branch_exists_in_metadata(branch_name: str, repo_root: Path) -> bool:
    """Check if branch exists in metadata"""
    metadata = load_branches_metadata(repo_root)
    return branch_name in metadata.branches

