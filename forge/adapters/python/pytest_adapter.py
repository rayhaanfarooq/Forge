"""Pytest adapter for Python test generation"""

import os
import subprocess
from pathlib import Path
from typing import Optional
from forge.adapters.base import LanguageAdapter
from forge.core.diff import filter_source_files


class PythonPytestAdapter(LanguageAdapter):
    """Adapter for Python projects using pytest"""
    
    def detect(self, repo_root: Path) -> bool:
        """Detect if this is a Python project"""
        python_files = list(repo_root.rglob("*.py"))
        return len(python_files) > 0
    
    def get_changed_files(
        self,
        repo_root: Path,
        base_branch: str,
    ) -> list[str]:
        """Get changed Python files"""
        from forge.core.git_ops import get_changed_files_since_base
        
        changed_files = get_changed_files_since_base(base_branch, repo_root)
        
        # Filter to Python files only
        python_files = filter_source_files(
            changed_files,
            include_patterns=[],
            exclude_patterns=["venv/", "node_modules/", "__pycache__/", ".git/", "tests/"],
            extensions=[".py"],
        )
        
        return python_files
    
    def get_all_source_files(
        self,
        repo_root: Path,
        include_patterns: list[str] = None,
        exclude_patterns: list[str] = None,
    ) -> list[str]:
        """Get all Python source files in the repository"""
        if include_patterns is None:
            include_patterns = []
        if exclude_patterns is None:
            exclude_patterns = ["venv/", "node_modules/", "__pycache__/", ".git/", "tests/", "test/"]
        
        # Find all Python files
        all_python_files = []
        for py_file in repo_root.rglob("*.py"):
            # Get relative path from repo root
            rel_path = str(py_file.relative_to(repo_root))
            
            # Always exclude test directories and test files
            if rel_path.startswith("tests/") or rel_path.startswith("test/"):
                continue
            
            # Check exclude patterns
            excluded = False
            for pattern in exclude_patterns:
                if pattern in rel_path:
                    excluded = True
                    break
            if excluded:
                continue
            
            # Check include patterns (if any specified)
            if include_patterns:
                included = False
                for pattern in include_patterns:
                    if pattern in rel_path:
                        included = True
                        break
                if not included:
                    continue
            
            all_python_files.append(rel_path)
        
        return sorted(all_python_files)
    
    def get_test_file_path(
        self,
        source_file: str,
        test_dir: Path,
    ) -> Path:
        """Convert source file path to test file path"""
        source_path = Path(source_file)
        
        # Remove .py extension and add test_ prefix
        test_name = f"test_{source_path.stem}.py"
        
        # Maintain directory structure in tests/
        if source_path.parent != Path("."):
            # Preserve relative path structure
            relative_path = source_path.parent
            test_path = test_dir / relative_path / test_name
        else:
            test_path = test_dir / test_name
        
        return test_path
    
    def generate_tests(
        self,
        file_path: str,
        code: str,
        test_dir: Path,
    ) -> str:
        """Generate test code (delegates to test_service)"""
        # This is handled by test_service.py
        # The adapter just provides the interface
        raise NotImplementedError("Use test_service.generate_tests_for_file instead")
    
    def run_tests(self, repo_root: Path, test_dir: Path) -> bool:
        """Run pytest tests and display all test results"""
        try:
            # Set PYTHONPATH to include repo root so imports work (e.g., "from src.module import ...")
            env = os.environ.copy()
            current_pythonpath = env.get("PYTHONPATH", "")
            if current_pythonpath:
                env["PYTHONPATH"] = f"{repo_root}{os.pathsep}{current_pythonpath}"
            else:
                env["PYTHONPATH"] = str(repo_root)
            
            # Run pytest with verbose output to show all tests
            # -v: verbose (shows each test)
            # --tb=short: shorter traceback format
            result = subprocess.run(
                ["pytest", str(test_dir), "-v", "--tb=short"],
                cwd=repo_root,
                env=env,
                capture_output=False,  # Don't capture so output is shown immediately
                text=True,
                check=False,
            )
            return result.returncode == 0
        except FileNotFoundError:
            raise RuntimeError(
                "pytest not found. Install it with: pip install pytest"
            )

