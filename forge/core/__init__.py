"""Core Forge functionality"""

from forge.core.config import (
    ForgeConfig,
    find_repo_root,
    load_config,
    save_config,
    detect_language,
    get_config_path,
    load_env_file,
)
from forge.core.git_ops import (
    is_git_repo,
    get_current_branch,
    sync_branch,
    stage_files,
    commit_changes,
    push_branch,
    is_clean_working_tree,
    run_git_command,
    create_branch,
    branch_exists,
    switch_branch,
    list_branches,
    detect_main_branch,
    branch_exists_local,
)
from forge.core.diff import get_changed_source_files

__all__ = [
    "ForgeConfig",
    "find_repo_root",
    "load_config",
    "save_config",
    "detect_language",
    "get_config_path",
    "load_env_file",
    "is_git_repo",
    "get_current_branch",
    "sync_branch",
    "stage_files",
    "commit_changes",
    "push_branch",
    "is_clean_working_tree",
    "run_git_command",
    "create_branch",
    "branch_exists",
    "switch_branch",
    "list_branches",
    "detect_main_branch",
    "branch_exists_local",
    "get_changed_source_files",
]

