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


def branch_exists_local(branch_name: str, repo_root: Optional[Path] = None) -> bool:
    """Check if a branch exists locally"""
    try:
        result = run_git_command(
            ["show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
            repo_root=repo_root,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def detect_main_branch(repo_root: Optional[Path] = None) -> str:
    """
    Detect the main branch by trying:
    1. 'main'
    2. 'master'
    3. 'fg/main' (if using Forge-managed branches)
    4. 'fg/master' (if using Forge-managed branches)
    
    Returns:
        The name of the main branch
    
    Raises:
        RuntimeError: If none of the expected main branches exist
    """
    # Try standard branch names first
    candidates = ["main", "master", "fg/main", "fg/master"]
    
    for branch_name in candidates:
        if branch_exists_local(branch_name, repo_root):
            return branch_name
    
    # None of the expected branches exist
    raise RuntimeError(
        "Could not find 'main', 'master', 'fg/main', or 'fg/master' branch. "
        "Please specify a base branch explicitly with --base-branch."
    )


def get_changed_files_since_base(
    base_branch: str,
    repo_root: Optional[Path] = None,
) -> list[str]:
    """Get list of files changed since base branch"""
    current_branch = get_current_branch(repo_root)
    
    # Check if base branch exists
    if not branch_exists_local(base_branch, repo_root):
        # Try to get list of available branches for better error message
        try:
            result = run_git_command(
                ["branch", "--format=%(refname:short)"],
                repo_root=repo_root,
                check=True,
            )
            available_branches = [b.strip() for b in result.stdout.strip().split("\n") if b.strip()]
            raise RuntimeError(
                f"Base branch '{base_branch}' does not exist.\n"
                f"Available branches: {', '.join(available_branches) if available_branches else 'none'}\n"
                f"Use 'forge switch <branch>' to switch branches or update base_branch in .gt.yml"
            )
        except RuntimeError as e:
            if "does not exist" in str(e):
                raise
            # If branch listing fails, just raise the original error
            raise RuntimeError(
                f"Base branch '{base_branch}' does not exist. "
                f"Use 'forge switch <branch>' to switch branches or update base_branch in .gt.yml"
            )
    
    # If we're on the base branch, check for uncommitted changes instead
    if current_branch == base_branch:
        try:
            # Get uncommitted changes (staged + unstaged)
            result = run_git_command(
                ["diff", "--name-only", "HEAD"],
                repo_root=repo_root,
                check=True,
            )
            files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
            
            # Also check staged changes
            result_staged = run_git_command(
                ["diff", "--name-only", "--cached", "HEAD"],
                repo_root=repo_root,
                check=True,
            )
            staged_files = [f.strip() for f in result_staged.stdout.strip().split("\n") if f.strip()]
            
            # Combine and deduplicate
            all_files = list(set(files + staged_files))
            return all_files
        except RuntimeError:
            # If no uncommitted changes, return empty list
            return []
    
    # Compare current branch against base branch
    try:
        result = run_git_command(
            ["diff", "--name-only", f"{base_branch}...HEAD"],
            repo_root=repo_root,
            check=True,
        )
        files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        return files
    except RuntimeError as e:
        # If diff fails, it might be because HEAD is the same as base_branch
        if "ambiguous argument" in str(e).lower() or "unknown revision" in str(e).lower():
            raise RuntimeError(
                f"Cannot compare with base branch '{base_branch}'. "
                f"Make sure the branch exists and you have commits to compare."
            )
        raise


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


def list_branches(repo_root: Optional[Path] = None) -> list[str]:
    """List all local branches"""
    try:
        result = run_git_command(
            ["branch", "--format=%(refname:short)"],
            repo_root=repo_root,
            check=True,
        )
        branches = [b.strip() for b in result.stdout.strip().split("\n") if b.strip()]
        return branches
    except RuntimeError:
        return []


def switch_branch(branch_name: str, repo_root: Optional[Path] = None) -> None:
    """
    Switch to an existing branch
    
    Args:
        branch_name: Name of the branch to switch to
        repo_root: Repository root path
    """
    if not branch_exists_local(branch_name, repo_root):
        # Try to get list of available branches
        try:
            result = run_git_command(
                ["branch", "--format=%(refname:short)"],
                repo_root=repo_root,
                check=True,
            )
            available_branches = [b.strip() for b in result.stdout.strip().split("\n") if b.strip()]
            raise ValueError(
                f"Branch '{branch_name}' does not exist.\n"
                f"Available branches: {', '.join(available_branches) if available_branches else 'none'}"
            )
        except RuntimeError:
            raise ValueError(f"Branch '{branch_name}' does not exist.")
    
    run_git_command(
        ["checkout", branch_name],
        repo_root=repo_root,
        check=True,
    )


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

