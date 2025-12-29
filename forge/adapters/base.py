"""Base adapter interface for language-specific test generation"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class LanguageAdapter(ABC):
    """Base class for language-specific adapters"""
    
    @abstractmethod
    def detect(self, repo_root: Path) -> bool:
        """Detect if this adapter applies to the repository"""
        pass
    
    @abstractmethod
    def get_changed_files(
        self,
        repo_root: Path,
        base_branch: str,
    ) -> list[str]:
        """Get changed source files for this language"""
        pass
    
    @abstractmethod
    def generate_tests(
        self,
        file_path: str,
        code: str,
        test_dir: Path,
    ) -> str:
        """Generate test code for a given file"""
        pass
    
    @abstractmethod
    def run_tests(self, repo_root: Path, test_dir: Path) -> bool:
        """Run tests and return True if all pass"""
        pass
    
    @abstractmethod
    def get_test_file_path(
        self,
        source_file: str,
        test_dir: Path,
    ) -> Path:
        """Get the path where test file should be written"""
        pass

