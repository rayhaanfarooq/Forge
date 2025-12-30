"""SQLite database models for Forge multi-repo tracking"""

from datetime import datetime
from pathlib import Path
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session

Base = declarative_base()

# Database path - stored in user's home directory
DB_PATH = Path.home() / ".forge" / "forge.db"


def get_db_path() -> Path:
    """Get the database path, creating directory if needed"""
    db_dir = DB_PATH.parent
    db_dir.mkdir(parents=True, exist_ok=True)
    return DB_PATH


def get_engine():
    """Get SQLAlchemy engine"""
    db_path = get_db_path()
    return create_engine(f"sqlite:///{db_path}", echo=False)


def get_session() -> Session:
    """Get a database session"""
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def init_db():
    """Initialize the database (create tables)"""
    engine = get_engine()
    Base.metadata.create_all(engine)


class Repository(Base):
    """Repository tracking model"""

    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    local_path = Column(String, nullable=False, unique=True)
    base_branch = Column(String, nullable=False, default="main")
    date_added = Column(DateTime, default=datetime.utcnow)
    last_scanned_at = Column(DateTime, nullable=True)

    # Relationships
    branches = relationship("Branch", back_populates="repository", cascade="all, delete-orphan")
    commits = relationship("Commit", back_populates="repository", cascade="all, delete-orphan")
    test_events = relationship("TestEvent", back_populates="repository", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Repository(id={self.id}, name='{self.name}', path='{self.local_path}')>"


class Branch(Base):
    """Branch tracking model"""

    __tablename__ = "branches"

    id = Column(Integer, primary_key=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    branch_name = Column(String, nullable=False)
    parent_branch = Column(String, nullable=True)  # nullable for base branches
    base_branch = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_synced_at = Column(DateTime, nullable=True)
    status = Column(String, default="active")  # active | merged | stale

    # Relationships
    repository = relationship("Repository", back_populates="branches")
    commits = relationship("Commit", back_populates="branch", cascade="all, delete-orphan")
    test_events = relationship("TestEvent", back_populates="branch", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Branch(id={self.id}, name='{self.branch_name}', repo_id={self.repo_id})>"


class Commit(Base):
    """Commit history model"""

    __tablename__ = "commits"

    id = Column(Integer, primary_key=True)
    commit_hash = Column(String, nullable=False)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    author = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    message = Column(String, nullable=False)
    files_changed_count = Column(Integer, default=0)
    lines_added = Column(Integer, default=0)
    lines_removed = Column(Integer, default=0)

    # Relationships
    repository = relationship("Repository", back_populates="commits")
    branch = relationship("Branch", back_populates="commits")

    def __repr__(self):
        return f"<Commit(id={self.id}, hash='{self.commit_hash[:8]}', branch_id={self.branch_id})>"


class TestEvent(Base):
    """Test generation event tracking"""

    __tablename__ = "test_events"

    id = Column(Integer, primary_key=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)  # nullable if repo-wide
    command_used = Column(String, nullable=False)  # e.g., "create-tests", "submit"
    ai_provider = Column(String, nullable=True)
    model = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String, nullable=False)  # success | failure

    # Relationships
    repository = relationship("Repository", back_populates="test_events")
    branch = relationship("Branch", back_populates="test_events")

    def __repr__(self):
        return f"<TestEvent(id={self.id}, command='{self.command_used}', status='{self.status}')>"

