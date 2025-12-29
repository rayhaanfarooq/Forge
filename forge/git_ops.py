"""Git operations for Forge"""

import subprocess
import sys
from pathlib import Path
from typing import Optional


def run_git_command(
    args: list[str],
    repo_root: Optional[Path] = None,
    check: bool = True,
    capture_output: bool = True,
) -> subprocess.CompletedProcess:
    """Run a git command and return the result"""
    if repo_root is None:
        repo_root = Path.cwd()
    
    cmd = ["git"] + args
    
    try:
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            check=check,
            capture_output=capture_output,
            text=True,
        )
        return result
    except subprocess.CalledProcessError as e:
        if capture_output:
            error_msg = e.stderr or e.stdout or "Unknown git error"
            raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{error_msg}")
        raise


def is_git_repo(path: Optional[Path] = None) -> bool:
    """Check if the current directory is a Git repository"""
    if path is None:
        path = Path.cwd()
    
    return (path / ".git").exists()


def get_current_branch(repo_root: Optional[Path] = None) -> str:
    """Get the current Git branch name"""
    result = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"], repo_root=repo_root)
    return result.stdout.strip()


def fetch_origin(repo_root: Optional[Path] = None) -> None:
    """Fetch latest changes from origin"""
    run_git_command(["fetch", "origin"], repo_root=repo_root)


def sync_branch(base_branch: str, repo_root: Optional[Path] = None) -> None:
    """Rebase current branch onto base branch"""
    current_branch = get_current_branch(repo_root)
    
    if current_branch == base_branch:
        raise ValueError(
            f"Cannot sync {base_branch} onto itself. "
            f"Switch to a feature branch first."
        )
    
    # Fetch latest changes
    fetch_origin(repo_root)
    
    # Rebase onto origin/base_branch
    try:
        run_git_command(
            ["rebase", f"origin/{base_branch}"],
            repo_root=repo_root,
            check=True,
        )
    except RuntimeError as e:
        raise RuntimeError(
            f"Rebase failed. Please resolve conflicts manually:\n{e}"
        )


def get_changed_files_since_base(
    base_branch: str,
    repo_root: Optional[Path] = None,
) -> list[str]:
    """Get list of files changed since base branch"""
    try:
        result = run_git_command(
            ["diff", "--name-only", f"origin/{base_branch}...HEAD"],
            repo_root=repo_root,
            check=True,
        )
        files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        return files
    except RuntimeError:
        # If base branch doesn't exist remotely, try local
        result = run_git_command(
            ["diff", "--name-only", base_branch + "...HEAD"],
            repo_root=repo_root,
            check=True,
        )
        files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        return files


def stage_files(files: list[str], repo_root: Optional[Path] = None) -> None:
    """Stage files for commit"""
    if not files:
        return
    
    run_git_command(["add"] + files, repo_root=repo_root)


def commit_changes(message: str, repo_root: Optional[Path] = None) -> None:
    """Commit staged changes"""
    run_git_command(["commit", "-m", message], repo_root=repo_root)


def push_branch(branch: Optional[str] = None, repo_root: Optional[Path] = None) -> None:
    """Push branch to remote"""
    if branch is None:
        branch = get_current_branch(repo_root)
    
    run_git_command(
        ["push", "-u", "origin", branch],
        repo_root=repo_root,
        check=True,
    )


def is_clean_working_tree(repo_root: Optional[Path] = None) -> bool:
    """Check if working tree is clean"""
    result = run_git_command(
        ["status", "--porcelain"],
        repo_root=repo_root,
        check=False,
    )
    return result.stdout.strip() == ""


def branch_exists(branch_name: str, repo_root: Optional[Path] = None) -> bool:
    """Check if a branch exists (local or remote)"""
    try:
        # Check local branches
        result = run_git_command(
            ["show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
            repo_root=repo_root,
            check=False,
        )
        if result.returncode == 0:
            return True
        
        # Check remote branches
        result = run_git_command(
            ["show-ref", "--verify", "--quiet", f"refs/remotes/origin/{branch_name}"],
            repo_root=repo_root,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def create_branch(
    branch_name: str,
    base_branch: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> None:
    """
    Create a new branch from base branch and switch to it
    
    Args:
        branch_name: Name of the new branch
        base_branch: Base branch to create from (default: current branch)
        repo_root: Repository root path
    """
    if base_branch is None:
        base_branch = get_current_branch(repo_root)
    
    # Check if branch already exists
    if branch_exists(branch_name, repo_root):
        raise ValueError(f"Branch '{branch_name}' already exists")
    
    # Create and switch to new branch
    run_git_command(
        ["checkout", "-b", branch_name, base_branch],
        repo_root=repo_root,
        check=True,
    )

