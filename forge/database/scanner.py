"""Repository scanning and data ingestion functions"""

from datetime import datetime
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session

from forge.database.models import Repository, Branch, Commit, get_session
from forge.core.git_ops import (
    list_branches,
    detect_main_branch,
    run_git_command,
    is_git_repo,
)
from forge.metadata.branches import get_branch_metadata


def scan_repository(repo_path: Path, session: Optional[Session] = None) -> Repository:
    """
    Scan a Git repository and populate database with branches and commits.
    
    Args:
        repo_path: Path to the Git repository
        session: Optional database session (creates new if not provided)
    
    Returns:
        Repository model instance
    """
    if not is_git_repo(repo_path):
        raise ValueError(f"Not a Git repository: {repo_path}")

    if session is None:
        session = get_session()
        should_close = True
    else:
        should_close = False

    try:
        # Get or create repository
        repo = session.query(Repository).filter_by(local_path=str(repo_path)).first()
        if not repo:
            # Detect base branch
            try:
                base_branch = detect_main_branch(repo_path)
            except RuntimeError:
                base_branch = "main"

            repo = Repository(
                name=repo_path.name,
                local_path=str(repo_path),
                base_branch=base_branch,
                date_added=datetime.utcnow(),
            )
            session.add(repo)
            session.commit()
            session.refresh(repo)

        # Update last scanned timestamp
        repo.last_scanned_at = datetime.utcnow()

        # Scan branches
        try:
            branch_names = list_branches(repo_path)
        except Exception:
            branch_names = []

        for branch_name in branch_names:
            # Get or create branch
            branch = (
                session.query(Branch)
                .filter_by(repo_id=repo.id, branch_name=branch_name)
                .first()
            )

            if not branch:
                # Try to get parent branch from metadata
                parent_branch = None
                try:
                    metadata = get_branch_metadata(branch_name, repo_path)
                    if metadata and metadata.base:
                        parent_branch = metadata.base
                except Exception:
                    pass

                if parent_branch is None and branch_name != repo.base_branch:
                    parent_branch = repo.base_branch

                branch = Branch(
                    repo_id=repo.id,
                    branch_name=branch_name,
                    parent_branch=parent_branch,
                    base_branch=repo.base_branch,
                    created_at=datetime.utcnow(),
                    status="active",
                )
                session.add(branch)
                session.commit()
                session.refresh(branch)

            # Scan commits for this branch
            _scan_branch_commits(repo_path, repo.id, branch.id, branch_name, session)

        session.commit()
        return repo

    finally:
        if should_close:
            session.close()


def _scan_branch_commits(
    repo_path: Path,
    repo_id: int,
    branch_id: int,
    branch_name: str,
    session: Session,
):
    """Scan commits for a specific branch"""
    try:
        # Get commits for this branch
        result = run_git_command(
            [
                "log",
                branch_name,
                "--pretty=format:%H%x1f%an%x1f%aI%x1f%s",
                "--numstat",
            ],
            repo_path,
        )

        if not result.stdout.strip():
            return

        current_hash = None
        current_author = None
        current_timestamp = None
        current_message = None
        files_changed = 0
        lines_added = 0
        lines_removed = 0

        def save_current_commit():
            if not current_hash:
                return

            existing = (
                session.query(Commit)
                .filter_by(commit_hash=current_hash, branch_id=branch_id)
                .first()
            )

            if not existing:
                session.add(
                    Commit(
                        commit_hash=current_hash,
                        repo_id=repo_id,
                        branch_id=branch_id,
                        author=current_author or "Unknown",
                        timestamp=current_timestamp or datetime.utcnow(),
                        message=current_message or "",
                        files_changed_count=files_changed,
                        lines_added=lines_added,
                        lines_removed=lines_removed,
                    )
                )

        for line in result.stdout.splitlines():
            if "\x1f" in line:
                save_current_commit()
                parts = line.split("\x1f", 3)
                if len(parts) == 4:
                    current_hash = parts[0]
                    current_author = parts[1]
                    try:
                        current_timestamp = datetime.fromisoformat(parts[2])
                    except ValueError:
                        current_timestamp = datetime.utcnow()
                    current_message = parts[3]
                    files_changed = 0
                    lines_added = 0
                    lines_removed = 0
            elif line and current_hash:
                parts = line.split("\t")
                if len(parts) == 3:
                    try:
                        added = int(parts[0]) if parts[0] != "-" else 0
                        removed = int(parts[1]) if parts[1] != "-" else 0
                        lines_added += added
                        lines_removed += removed
                        files_changed += 1
                    except ValueError:
                        pass

        save_current_commit()

    except Exception as e:
        # Log error but don't fail
        print(f"Error scanning commits for branch {branch_name}: {e}")
