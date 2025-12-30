"""FastAPI backend for Forge dashboard"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from forge.database.models import (
    Repository,
    Branch,
    Commit,
    TestEvent,
    get_session,
    init_db,
)
from forge.database.scanner import scan_repository

app = FastAPI(title="Forge API", version="0.1.0")

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API responses
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


# Dependency to get database session
def get_db():
    session = get_session()
    try:
        yield session
    finally:
        session.close()


@app.on_event("startup")
def startup_event():
    """Initialize database on startup"""
    init_db()


@app.get("/")
def root():
    return {"message": "Forge API", "version": "0.1.0"}


@app.get("/repos", response_model=List[RepositoryResponse])
def get_repos(db: Session = Depends(get_db)):
    """Get all tracked repositories"""
    repos = db.query(Repository).all()
    return repos


@app.post("/repos", response_model=RepositoryResponse)
def add_repo(request: AddRepositoryRequest, db: Session = Depends(get_db)):
    """Add a new repository to track"""
    repo_path = Path(request.local_path)
    if not repo_path.exists():
        raise HTTPException(status_code=400, detail="Repository path does not exist")

    # Check if already exists
    existing = db.query(Repository).filter_by(local_path=str(repo_path)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Repository already tracked")

    # Scan and add repository
    try:
        repo = scan_repository(repo_path, db)
        return repo
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/repos/{repo_id}/scan")
def scan_repo(repo_id: int, db: Session = Depends(get_db)):
    """Manually scan a repository to update branches and commits"""
    repo = db.query(Repository).filter_by(id=repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        repo_path = Path(repo.local_path)
        scan_repository(repo_path, db)
        return {"message": "Repository scanned successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/repos/{repo_id}/branches", response_model=List[BranchResponse])
def get_repo_branches(repo_id: int, db: Session = Depends(get_db)):
    """Get all branches for a repository"""
    repo = db.query(Repository).filter_by(id=repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    branches = db.query(Branch).filter_by(repo_id=repo_id).all()
    return branches


@app.get("/branches/{branch_id}/commits", response_model=List[CommitResponse])
def get_branch_commits(branch_id: int, db: Session = Depends(get_db)):
    """Get commits for a specific branch"""
    branch = db.query(Branch).filter_by(id=branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    commits = (
        db.query(Commit)
        .filter_by(branch_id=branch_id)
        .order_by(Commit.timestamp.desc())
        .all()
    )
    return commits


@app.get("/branches/{branch_id}/metrics", response_model=BranchMetrics)
def get_branch_metrics(branch_id: int, db: Session = Depends(get_db)):
    """Get metrics for a specific branch"""
    branch = db.query(Branch).filter_by(id=branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    # Commits behind base (simplified - count commits not in base branch)
    commits_behind = 0  # TODO: Implement proper calculation

    # Days since last sync
    days_since_sync = None
    if branch.last_synced_at:
        delta = datetime.utcnow() - branch.last_synced_at
        days_since_sync = delta.total_seconds() / 86400

    # Has generated tests
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
    """Get test generation events, optionally filtered by repo or branch"""
    query = db.query(TestEvent)

    if repo_id:
        query = query.filter_by(repo_id=repo_id)
    if branch_id:
        query = query.filter_by(branch_id=branch_id)

    events = query.order_by(TestEvent.timestamp.desc()).limit(100).all()
    return events
