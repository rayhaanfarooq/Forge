"""FastAPI backend for Forge dashboard."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from forge.adapters.python.pytest_adapter import PythonPytestAdapter
from forge.core.config import ForgeConfig, load_config
from forge.core.git_ops import get_current_branch, run_git_command, switch_branch
from forge.database.models import Branch, Commit, Repository, TestEvent, get_session, init_db
from forge.database.scanner import scan_repository
from forge.database.tracker import ensure_repo_tracked, mark_branch_synced
from forge.utils.ast_parser import extract_public_functions, get_untested_functions

app = FastAPI(title="Forge API", version="0.1.0")

FORGE_PROJECT_ROOT = Path(__file__).resolve().parents[2]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RepositoryResponse(BaseModel):
    id: int
    name: str
    local_path: str
    base_branch: str
    date_added: datetime
    last_scanned_at: Optional[datetime]

    class Config:
        from_attributes = True


class BranchResponse(BaseModel):
    id: int
    repo_id: int
    branch_name: str
    parent_branch: Optional[str]
    base_branch: str
    created_at: datetime
    last_synced_at: Optional[datetime]
    status: str

    class Config:
        from_attributes = True


class CommitResponse(BaseModel):
    id: int
    commit_hash: str
    repo_id: int
    branch_id: int
    author: str
    timestamp: datetime
    message: str
    files_changed_count: int
    lines_added: int
    lines_removed: int

    class Config:
        from_attributes = True


class TestEventResponse(BaseModel):
    id: int
    repo_id: int
    branch_id: Optional[int]
    command_used: str
    ai_provider: Optional[str]
    model: Optional[str]
    timestamp: datetime
    status: str

    class Config:
        from_attributes = True


class BranchMetrics(BaseModel):
    commits_behind_base: int
    days_since_last_sync: Optional[float]
    has_generated_tests: bool


class AddRepositoryRequest(BaseModel):
    local_path: str


class SwitchBranchRequest(BaseModel):
    branch_name: str


class TimelineCommitResponse(BaseModel):
    commit_hash: str
    author: str
    timestamp: datetime
    message: str
    files_changed_count: int
    lines_added: int
    lines_removed: int


class CoverageAreaResponse(BaseModel):
    path: str
    untested_functions: int


class CoverageSummaryResponse(BaseModel):
    coverage_percent: int
    total_public_functions: int
    tested_public_functions: int
    generated_test_files: int
    source_files_scanned: int
    untested_areas: List[CoverageAreaResponse]


class ReadinessResponse(BaseModel):
    synced_with_base: bool
    tests_passing: bool
    coverage_sufficient: bool
    no_conflicts: bool
    ready_to_submit: bool


class ActivityItemResponse(BaseModel):
    kind: str
    title: str
    detail: str
    status: str
    timestamp: datetime


class BranchNodeResponse(BaseModel):
    id: int
    branch_name: str
    parent_branch: Optional[str]
    base_branch: str
    status: str
    health: str
    is_current: bool
    commits_ahead: int
    commits_behind: int
    last_synced_at: Optional[datetime]
    latest_activity_at: Optional[datetime]
    latest_commit_message: Optional[str]
    latest_commit_hash: Optional[str]
    latest_commit_author: Optional[str]
    test_status: str
    pr_status: str


class RepositoryDashboardResponse(BaseModel):
    repository: RepositoryResponse
    current_branch: str
    selected_branch: str
    sync_status: str
    branch_graph: List[BranchNodeResponse]
    commit_timeline: List[TimelineCommitResponse]
    coverage: CoverageSummaryResponse
    readiness: ReadinessResponse
    activity_feed: List[ActivityItemResponse]


class RepoCommandResponse(BaseModel):
    action: str
    success: bool
    output: str


class StatsResponse(BaseModel):
    total_repos: int
    total_branches: int
    total_commits: int
    total_test_events: int
    successful_tests: int
    failed_tests: int
    active_branches: int
    recent_activity: int


def get_db():
    session = get_session()
    try:
        yield session
    finally:
        session.close()


def _require_repo(repo_id: int, db: Session) -> Repository:
    repo = db.query(Repository).filter_by(id=repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


def _load_repo_config(repo_path: Path, base_branch: str) -> ForgeConfig:
    try:
        return load_config(repo_path)
    except FileNotFoundError:
        return ForgeConfig(base_branch=base_branch)


def _safe_run_git(args: List[str], repo_path: Path) -> str:
    try:
        return run_git_command(args, repo_root=repo_path).stdout.strip()
    except Exception:
        return ""


def _parse_iso_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        parsed = datetime.now(timezone.utc)
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _get_git_commits(
    repo_path: Path,
    branch_name: str,
    limit: int = 8,
) -> List[TimelineCommitResponse]:
    result = _safe_run_git(
        [
            "log",
            branch_name,
            f"-{limit}",
            "--pretty=format:%H%x1f%an%x1f%aI%x1f%s",
            "--numstat",
        ],
        repo_path,
    )
    if not result:
        return []

    commits: List[TimelineCommitResponse] = []
    current: Optional[dict] = None

    def flush_current() -> None:
        nonlocal current
        if not current:
            return
        commits.append(TimelineCommitResponse(**current))
        current = None

    for line in result.splitlines():
        if "\x1f" in line:
            flush_current()
            commit_hash, author, timestamp, message = line.split("\x1f", 3)
            current = {
                "commit_hash": commit_hash,
                "author": author,
                "timestamp": _parse_iso_datetime(timestamp),
                "message": message,
                "files_changed_count": 0,
                "lines_added": 0,
                "lines_removed": 0,
            }
            continue

        if current is None:
            continue

        parts = line.split("\t")
        if len(parts) != 3:
            continue

        added = int(parts[0]) if parts[0].isdigit() else 0
        removed = int(parts[1]) if parts[1].isdigit() else 0
        current["files_changed_count"] += 1
        current["lines_added"] += added
        current["lines_removed"] += removed

    flush_current()
    return commits


def _get_branch_divergence(repo_path: Path, base_branch: str, branch_name: str) -> tuple[int, int]:
    if branch_name == base_branch:
        return 0, 0

    raw = _safe_run_git(
        ["rev-list", "--left-right", "--count", f"{base_branch}...{branch_name}"],
        repo_path,
    )
    if not raw:
        return 0, 0

    parts = raw.split()
    if len(parts) != 2:
        return 0, 0

    behind = int(parts[0])
    ahead = int(parts[1])
    return ahead, behind


def _branch_has_conflicts(repo_path: Path, base_branch: str, branch_name: str) -> bool:
    if branch_name == base_branch:
        return False

    merge_base = _safe_run_git(["merge-base", base_branch, branch_name], repo_path)
    if not merge_base:
        return False

    output = _safe_run_git(["merge-tree", merge_base, base_branch, branch_name], repo_path)
    return "<<<<<<<" in output or "changed in both" in output or "CONFLICT" in output


def _get_branch_test_status(latest_event: Optional[TestEvent]) -> str:
    if latest_event is None:
        return "unknown"
    return "passing" if latest_event.status == "success" else "failing"


def _choose_health(
    is_current: bool,
    branch_status: str,
    test_status: str,
    commits_behind: int,
    latest_activity_at: Optional[datetime],
    has_conflicts: bool,
) -> str:
    if is_current:
        return "current"

    if branch_status == "stale":
        return "stale"

    if latest_activity_at:
        latest_activity_utc = latest_activity_at
        if latest_activity_utc.tzinfo is not None:
            latest_activity_utc = latest_activity_utc.astimezone(timezone.utc).replace(tzinfo=None)
        if latest_activity_utc < datetime.utcnow() - timedelta(days=21):
            return "stale"

    if has_conflicts or test_status == "failing" or commits_behind > 0:
        return "issues"

    if test_status == "passing":
        return "healthy"

    return "neutral"


def _summarize_coverage(repo: Repository) -> CoverageSummaryResponse:
    repo_path = Path(repo.local_path)
    config = _load_repo_config(repo_path, repo.base_branch)
    adapter = PythonPytestAdapter()
    test_dir = repo_path / config.test_dir

    total_public_functions = 0
    tested_public_functions = 0
    generated_test_files = 0
    untested_areas: List[CoverageAreaResponse] = []

    try:
        source_files = adapter.get_all_source_files(
            repo_path,
            include_patterns=config.include or [],
            exclude_patterns=config.exclude or [],
        )
    except Exception:
        source_files = []

    for source_file in source_files:
        source_path = repo_path / source_file
        if not source_path.exists():
            continue

        try:
            source_code = source_path.read_text()
        except Exception:
            continue

        public_functions = extract_public_functions(source_code)
        if not public_functions:
            continue

        test_file_path = adapter.get_test_file_path(source_file, test_dir)
        test_code = ""
        if test_file_path.exists():
            generated_test_files += 1
            try:
                test_code = test_file_path.read_text()
            except Exception:
                test_code = ""

        untested = get_untested_functions(source_code, test_code)
        total_public_functions += len(public_functions)
        tested_public_functions += len(public_functions) - len(untested)

        if untested:
            untested_areas.append(
                CoverageAreaResponse(
                    path=source_file,
                    untested_functions=len(untested),
                )
            )

    coverage_percent = 100
    if total_public_functions:
        coverage_percent = round((tested_public_functions / total_public_functions) * 100)

    untested_areas.sort(key=lambda area: (-area.untested_functions, area.path))

    return CoverageSummaryResponse(
        coverage_percent=coverage_percent,
        total_public_functions=total_public_functions,
        tested_public_functions=tested_public_functions,
        generated_test_files=generated_test_files,
        source_files_scanned=len(source_files),
        untested_areas=untested_areas[:5],
    )


def _build_activity_feed(
    repo: Repository,
    branches_by_id: Dict[int, Branch],
    events: List[TestEvent],
) -> List[ActivityItemResponse]:
    items: List[ActivityItemResponse] = []

    if repo.last_scanned_at:
        items.append(
            ActivityItemResponse(
                kind="scan",
                title="Repository scanned",
                detail=f"{repo.name} was refreshed from local Git metadata.",
                status="info",
                timestamp=repo.last_scanned_at,
            )
        )

    for branch in branches_by_id.values():
        if branch.last_synced_at:
            items.append(
                ActivityItemResponse(
                    kind="sync",
                    title=f"{branch.branch_name} synced",
                    detail=f"Latest successful sync onto {branch.base_branch}.",
                    status="success",
                    timestamp=branch.last_synced_at,
                )
            )

    for event in events:
        branch_name = None
        if event.branch_id and event.branch_id in branches_by_id:
            branch_name = branches_by_id[event.branch_id].branch_name

        title = f"{event.command_used} {event.status}"
        if branch_name:
            title = f"{branch_name}: {event.command_used} {event.status}"

        provider = event.ai_provider or "Local"
        detail = f"{provider}"
        if event.model:
            detail = f"{detail} · {event.model}"

        kind = "submit" if event.command_used == "submit" else "test"
        items.append(
            ActivityItemResponse(
                kind=kind,
                title=title,
                detail=detail,
                status="success" if event.status == "success" else "danger",
                timestamp=event.timestamp,
            )
        )

    items.sort(key=lambda item: item.timestamp, reverse=True)
    return items[:8]


def _run_forge_command(action: str, repo_path: Path) -> RepoCommandResponse:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{FORGE_PROJECT_ROOT}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else str(FORGE_PROJECT_ROOT)
    )

    result = subprocess.run(
        [sys.executable, "-m", "forge.cli", action],
        cwd=repo_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    output_parts = [result.stdout.strip(), result.stderr.strip()]
    output = "\n\n".join(part for part in output_parts if part)
    return RepoCommandResponse(
        action=action,
        success=result.returncode == 0,
        output=output,
    )


def _build_repository_dashboard(
    repo: Repository,
    db: Session,
    branch_name: Optional[str] = None,
) -> RepositoryDashboardResponse:
    repo_path = Path(repo.local_path)
    if not repo_path.exists():
        raise HTTPException(status_code=400, detail="Tracked repository path no longer exists")

    ensure_repo_tracked(repo_path)
    scan_repository(repo_path, db)
    db.refresh(repo)

    current_branch = get_current_branch(repo_path)
    selected_branch = branch_name or current_branch

    branches = (
        db.query(Branch)
        .filter_by(repo_id=repo.id)
        .order_by(Branch.created_at.asc())
        .all()
    )
    branches_by_id = {branch.id: branch for branch in branches}
    branches_by_name = {branch.branch_name: branch for branch in branches}

    if selected_branch not in branches_by_name:
        selected_branch = current_branch

    events = (
        db.query(TestEvent)
        .filter_by(repo_id=repo.id)
        .order_by(TestEvent.timestamp.desc())
        .limit(50)
        .all()
    )

    latest_event_by_branch: Dict[int, TestEvent] = {}
    latest_submit_by_branch: Dict[int, TestEvent] = {}
    for event in events:
        if event.branch_id and event.branch_id not in latest_event_by_branch:
            latest_event_by_branch[event.branch_id] = event
        if (
            event.branch_id
            and event.command_used == "submit"
            and event.branch_id not in latest_submit_by_branch
        ):
            latest_submit_by_branch[event.branch_id] = event

    branch_nodes: List[BranchNodeResponse] = []
    selected_node: Optional[BranchNodeResponse] = None

    for branch in branches:
        timeline = _get_git_commits(repo_path, branch.branch_name, limit=1)
        latest_commit = timeline[0] if timeline else None
        latest_event = latest_event_by_branch.get(branch.id)
        latest_submit = latest_submit_by_branch.get(branch.id)
        commits_ahead, commits_behind = _get_branch_divergence(
            repo_path,
            branch.base_branch,
            branch.branch_name,
        )
        conflict_risk = _branch_has_conflicts(
            repo_path,
            branch.base_branch,
            branch.branch_name,
        )

        latest_activity_at = branch.last_synced_at
        for candidate in (
            latest_commit.timestamp if latest_commit else None,
            latest_event.timestamp if latest_event else None,
            repo.last_scanned_at,
        ):
            if candidate and (latest_activity_at is None or candidate > latest_activity_at):
                latest_activity_at = candidate

        test_status = _get_branch_test_status(latest_event)
        pr_status = "none"
        if branch.status == "merged":
            pr_status = "merged"
        elif latest_submit and latest_submit.status == "success":
            pr_status = "open"

        node = BranchNodeResponse(
            id=branch.id,
            branch_name=branch.branch_name,
            parent_branch=branch.parent_branch,
            base_branch=branch.base_branch,
            status=branch.status,
            health=_choose_health(
                is_current=branch.branch_name == current_branch,
                branch_status=branch.status,
                test_status=test_status,
                commits_behind=commits_behind,
                latest_activity_at=latest_activity_at,
                has_conflicts=conflict_risk,
            ),
            is_current=branch.branch_name == current_branch,
            commits_ahead=commits_ahead,
            commits_behind=commits_behind,
            last_synced_at=branch.last_synced_at,
            latest_activity_at=latest_activity_at,
            latest_commit_message=latest_commit.message if latest_commit else None,
            latest_commit_hash=latest_commit.commit_hash if latest_commit else None,
            latest_commit_author=latest_commit.author if latest_commit else None,
            test_status=test_status,
            pr_status=pr_status,
        )
        branch_nodes.append(node)

        if branch.branch_name == selected_branch:
            selected_node = node

    if selected_node is None and branch_nodes:
        selected_node = branch_nodes[0]
        selected_branch = selected_node.branch_name

    coverage = _summarize_coverage(repo)
    timeline = _get_git_commits(repo_path, selected_branch, limit=8) if selected_branch else []

    has_conflicts = False
    synced_with_base = True
    tests_passing = False
    if selected_node:
        has_conflicts = _branch_has_conflicts(
            repo_path,
            selected_node.base_branch,
            selected_node.branch_name,
        )
        synced_with_base = selected_node.commits_behind == 0
        tests_passing = selected_node.test_status == "passing"

    coverage_sufficient = (
        coverage.coverage_percent >= 70 or coverage.total_public_functions == 0
    )
    no_conflicts = not has_conflicts
    ready_to_submit = (
        selected_node is not None
        and selected_node.branch_name != repo.base_branch
        and synced_with_base
        and tests_passing
        and coverage_sufficient
        and no_conflicts
        and selected_node.commits_ahead > 0
    )

    sync_status = "Synced"
    if selected_node and selected_node.commits_behind > 0:
        sync_status = "Needs sync" if selected_node.commits_behind < 5 else "Out of date"

    return RepositoryDashboardResponse(
        repository=RepositoryResponse.model_validate(repo),
        current_branch=current_branch,
        selected_branch=selected_branch,
        sync_status=sync_status,
        branch_graph=branch_nodes,
        commit_timeline=timeline,
        coverage=coverage,
        readiness=ReadinessResponse(
            synced_with_base=synced_with_base,
            tests_passing=tests_passing,
            coverage_sufficient=coverage_sufficient,
            no_conflicts=no_conflicts,
            ready_to_submit=ready_to_submit,
        ),
        activity_feed=_build_activity_feed(repo, branches_by_id, events),
    )


@app.on_event("startup")
def startup_event():
    """Initialize database on startup."""
    init_db()


@app.get("/")
def root():
    return {"message": "Forge API", "version": "0.1.0"}


@app.get("/repos", response_model=List[RepositoryResponse])
def get_repos(db: Session = Depends(get_db)):
    """Get all tracked repositories."""
    return db.query(Repository).order_by(Repository.name.asc()).all()


@app.post("/repos", response_model=RepositoryResponse)
def add_repo(request: AddRepositoryRequest, db: Session = Depends(get_db)):
    """Add a new repository to track."""
    repo_path = Path(request.local_path)
    if not repo_path.exists():
        raise HTTPException(status_code=400, detail="Repository path does not exist")

    existing = db.query(Repository).filter_by(local_path=str(repo_path)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Repository already tracked")

    try:
        return scan_repository(repo_path, db)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/repos/{repo_id}/scan")
def scan_repo(repo_id: int, db: Session = Depends(get_db)):
    """Manually scan a repository to update branches and commits."""
    repo = _require_repo(repo_id, db)
    try:
        scan_repository(Path(repo.local_path), db)
        return {"message": "Repository scanned successfully"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/repos/{repo_id}/branches/switch")
def switch_repo_branch(
    repo_id: int,
    request: SwitchBranchRequest,
    db: Session = Depends(get_db),
):
    """Switch the repository working tree to a different branch."""
    repo = _require_repo(repo_id, db)
    repo_path = Path(repo.local_path)

    try:
        switch_branch(request.branch_name, repo_path)
        ensure_repo_tracked(repo_path)
        scan_repository(repo_path, db)
        return {"message": f"Switched to {request.branch_name}"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/repos/{repo_id}/actions/{action}", response_model=RepoCommandResponse)
def run_repo_action(action: str, repo_id: int, db: Session = Depends(get_db)):
    """Run a Forge workflow command for a tracked repository."""
    if action not in {"sync", "test", "submit"}:
        raise HTTPException(status_code=404, detail="Unknown action")

    repo = _require_repo(repo_id, db)
    repo_path = Path(repo.local_path)

    response = _run_forge_command(action, repo_path)

    if response.success:
        ensure_repo_tracked(repo_path)
        if action in {"sync", "submit"}:
            try:
                current_branch = get_current_branch(repo_path)
                mark_branch_synced(current_branch, repo_path)
            except Exception:
                pass
        try:
            scan_repository(repo_path, db)
        except Exception:
            pass

    return response


@app.get("/repos/{repo_id}/dashboard", response_model=RepositoryDashboardResponse)
def get_repo_dashboard(
    repo_id: int,
    branch: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get a repository-centric workflow snapshot for the dashboard."""
    repo = _require_repo(repo_id, db)
    try:
        return _build_repository_dashboard(repo, db, branch_name=branch)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/repos/{repo_id}/branches", response_model=List[BranchResponse])
def get_repo_branches(repo_id: int, db: Session = Depends(get_db)):
    """Get all branches for a repository."""
    repo = _require_repo(repo_id, db)
    try:
        scan_repository(Path(repo.local_path), db)
    except Exception:
        pass
    return db.query(Branch).filter_by(repo_id=repo_id).order_by(Branch.branch_name.asc()).all()


@app.get("/branches/{branch_id}/commits", response_model=List[CommitResponse])
def get_branch_commits(branch_id: int, db: Session = Depends(get_db)):
    """Get commits for a specific branch."""
    branch = db.query(Branch).filter_by(id=branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    return (
        db.query(Commit)
        .filter_by(branch_id=branch_id)
        .order_by(Commit.timestamp.desc())
        .all()
    )


@app.get("/branches/{branch_id}/metrics", response_model=BranchMetrics)
def get_branch_metrics(branch_id: int, db: Session = Depends(get_db)):
    """Get metrics for a specific branch."""
    branch = db.query(Branch).filter_by(id=branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    commits_behind = 0
    repo = db.query(Repository).filter_by(id=branch.repo_id).first()
    if repo:
        _, commits_behind = _get_branch_divergence(
            Path(repo.local_path),
            branch.base_branch,
            branch.branch_name,
        )

    days_since_sync = None
    if branch.last_synced_at:
        delta = datetime.utcnow() - branch.last_synced_at
        days_since_sync = delta.total_seconds() / 86400

    has_tests = (
        db.query(TestEvent)
        .filter_by(branch_id=branch_id, status="success")
        .first()
        is not None
    )

    return BranchMetrics(
        commits_behind_base=commits_behind,
        days_since_last_sync=days_since_sync,
        has_generated_tests=has_tests,
    )


@app.get("/test-events", response_model=List[TestEventResponse])
def get_test_events(
    repo_id: Optional[int] = None,
    branch_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Get test generation events, optionally filtered by repo or branch."""
    query = db.query(TestEvent)
    if repo_id:
        query = query.filter_by(repo_id=repo_id)
    if branch_id:
        query = query.filter_by(branch_id=branch_id)
    return query.order_by(TestEvent.timestamp.desc()).limit(100).all()


@app.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """Get overall statistics for the dashboard."""
    total_repos = db.query(Repository).count()
    total_branches = db.query(Branch).count()
    total_commits = db.query(Commit).count()
    total_test_events = db.query(TestEvent).count()
    successful_tests = db.query(TestEvent).filter_by(status="success").count()
    failed_tests = db.query(TestEvent).filter_by(status="failure").count()
    active_branches = db.query(Branch).filter_by(status="active").count()
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_activity = db.query(TestEvent).filter(TestEvent.timestamp >= seven_days_ago).count()

    return StatsResponse(
        total_repos=total_repos,
        total_branches=total_branches,
        total_commits=total_commits,
        total_test_events=total_test_events,
        successful_tests=successful_tests,
        failed_tests=failed_tests,
        active_branches=active_branches,
        recent_activity=recent_activity,
    )
