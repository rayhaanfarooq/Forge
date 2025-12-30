"""Utilities for tracking Forge events in the database"""

from datetime import datetime
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session

from forge.database.models import Repository, Branch, TestEvent, get_session, init_db
from forge.core.config import find_repo_root


def track_test_event(
    command_used: str,
    status: str,
    ai_provider: Optional[str] = None,
    model: Optional[str] = None,
    repo_path: Optional[Path] = None,
    branch_name: Optional[str] = None,
    session: Optional[Session] = None,
):
    """
    Track a test generation event in the database.
    
    Args:
        command_used: Command that triggered the event (e.g., "create-tests", "submit")
        status: "success" or "failure"
        ai_provider: AI provider used (e.g., "openai", "gemini")
        model: Model used (e.g., "gpt-4o-mini", "gemini-2.0-flash-lite")
        repo_path: Path to repository (auto-detected if not provided)
        branch_name: Branch name (auto-detected if not provided)
        session: Optional database session
    """
    try:
        # Initialize database
        init_db()

        if session is None:
            session = get_session()
            should_close = True
        else:
            should_close = False

        try:
            # Find repository
            if repo_path is None:
                repo_path = find_repo_root()
                if repo_path is None:
                    return  # Not in a Git repo, skip tracking

            repo = (
                session.query(Repository)
                .filter_by(local_path=str(repo_path))
                .first()
            )

            if not repo:
                # Repository not tracked yet, skip
                return

            # Find branch if provided
            branch_id = None
            if branch_name:
                branch = (
                    session.query(Branch)
                    .filter_by(repo_id=repo.id, branch_name=branch_name)
                    .first()
                )
                if branch:
                    branch_id = branch.id

            # Create test event
            event = TestEvent(
                repo_id=repo.id,
                branch_id=branch_id,
                command_used=command_used,
                ai_provider=ai_provider,
                model=model,
                timestamp=datetime.utcnow(),
                status=status,
            )
            session.add(event)
            session.commit()

        finally:
            if should_close:
                session.close()

    except Exception as e:
        # Don't fail the CLI command if tracking fails
        print(f"Warning: Failed to track event: {e}")


def ensure_repo_tracked(repo_path: Optional[Path] = None) -> Optional[Repository]:
    """
    Ensure the current repository is tracked in the database.
    Scans if not already tracked.
    
    Returns:
        Repository model if tracked, None otherwise
    """
    try:
        init_db()

        if repo_path is None:
            repo_path = find_repo_root()
            if repo_path is None:
                return None

        session = get_session()
        try:
            # Check if already tracked
            repo = (
                session.query(Repository)
                .filter_by(local_path=str(repo_path))
                .first()
            )

            if not repo:
                # Scan and add repository
                from forge.database.scanner import scan_repository

                repo = scan_repository(repo_path, session)
                session.commit()

            return repo

        finally:
            session.close()

    except Exception:
        return None

