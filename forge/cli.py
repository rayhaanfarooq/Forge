"""CLI interface for Forge"""

import os
import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from forge.config import (
    ForgeConfig,
    find_repo_root,
    load_config,
    save_config,
    detect_language,
    get_config_path,
)
from forge.git_ops import (
    is_git_repo,
    get_current_branch,
    sync_branch,
    stage_files,
    commit_changes,
    push_branch,
    is_clean_working_tree,
    run_git_command,
)
from forge.diff import get_changed_source_files
from forge.test_service import TestService
from forge.adapters.python.pytest_adapter import PythonPytestAdapter
from forge.utils.validation import (
    assert_git_repo,
    assert_no_rebase,
    assert_clean_working_tree,
    normalize_branch_name,
    validate_branch_name,
)
from forge.metadata.branches import register_branch
from forge.git_ops import create_branch, get_current_branch, branch_exists

app = typer.Typer(help="Forge - Opinionated Git workflows with AI-generated tests")
console = Console()


@app.command()
def init(
    base_branch: str = typer.Option("main", help="Base branch name"),
    language: Optional[str] = typer.Option(None, help="Project language (auto-detected if not specified)"),
    test_dir: str = typer.Option("tests/", help="Directory for test files"),
):
    """Initialize Forge in the current Git repository"""
    repo_root = find_repo_root()
    
    if repo_root is None:
        console.print("[red]Error: Not in a Git repository[/red]")
        console.print("Please run this command from within a Git repository.")
        raise typer.Exit(1)
    
    config_path = get_config_path(repo_root)
    
    if config_path.exists():
        console.print(f"[yellow]Forge is already initialized at {config_path}[/yellow]")
        if not typer.confirm("Overwrite existing configuration?"):
            raise typer.Exit(0)
    
    # Detect language if not provided
    if language is None:
        language = detect_language(repo_root)
        console.print(f"[green]Detected language: {language}[/green]")
    
    # Create config
    config = ForgeConfig(
        base_branch=base_branch,
        language=language,
        test_framework="pytest" if language == "python" else "pytest",
        test_dir=test_dir,
        include=["src/"] if language == "python" else [],
        exclude=["venv/", "node_modules/", "__pycache__/"],
    )
    
    save_config(config, repo_root)
    
    # Create test directory if it doesn't exist
    test_path = repo_root / test_dir
    test_path.mkdir(parents=True, exist_ok=True)
    
    # Create __init__.py in test directory
    init_file = test_path / "__init__.py"
    init_file.touch(exist_ok=True)
    
    console.print(f"[green]✓ Forge initialized successfully![/green]")
    console.print(f"  Config: {config_path}")
    console.print(f"  Base branch: {base_branch}")
    console.print(f"  Language: {language}")
    console.print(f"  Test directory: {test_dir}")


@app.command()
def branch(
    branch_name: str = typer.Argument(..., help="Name of the branch to create"),
    base: Optional[str] = typer.Option(None, help="Base branch (default: main if on main, otherwise current branch)"),
    require_clean: bool = typer.Option(True, help="Require clean working tree"),
):
    """Create a new Forge-managed branch"""
    try:
        # Validate repository
        repo_root = assert_git_repo()
        
        # Check for rebase/merge in progress
        assert_no_rebase(repo_root)
        
        # Check working tree
        try:
            assert_clean_working_tree(repo_root, require_clean=require_clean)
        except RuntimeError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)
        
        # Normalize branch name
        try:
            normalized_name = normalize_branch_name(branch_name)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)
        
        # Validate normalized name
        if not validate_branch_name(normalized_name):
            console.print(f"[red]Error: Invalid branch name: {normalized_name}[/red]")
            raise typer.Exit(1)
        
        # Check if branch already exists
        if branch_exists(normalized_name, repo_root):
            console.print(f"[red]Error: Branch '{normalized_name}' already exists[/red]")
            raise typer.Exit(1)
        
        # Determine base branch
        if base is None:
            current = get_current_branch(repo_root)
            # PRD FR-4: Default base branch is main
            # If current branch ≠ main, use current branch as base
            if current == "main":
                base = "main"
            else:
                base = current
        
        # Create branch
        try:
            create_branch(normalized_name, base, repo_root)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)
        except RuntimeError as e:
            console.print(f"[red]Error creating branch: {e}[/red]")
            raise typer.Exit(1)
        
        # Register branch metadata
        try:
            register_branch(normalized_name, base, repo_root)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not register branch metadata: {e}[/yellow]")
            # Don't fail the command if metadata registration fails
        
        # Success message
        console.print(f"[green]✓ Created branch {normalized_name}[/green]")
        console.print(f"[green]✓ Base branch: {base}[/green]")
        console.print(f"[green]✓ Switched to {normalized_name}[/green]")
        
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def sync():
    """Rebase current branch onto base branch"""
    repo_root = find_repo_root()
    
    if repo_root is None:
        console.print("[red]Error: Not in a Git repository[/red]")
        raise typer.Exit(1)
    
    try:
        config = load_config(repo_root)
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    
    current_branch = get_current_branch(repo_root)
    
    if current_branch == config.base_branch:
        console.print(
            f"[yellow]Warning: Cannot sync {config.base_branch} onto itself[/yellow]"
        )
        console.print("Switch to a feature branch first.")
        raise typer.Exit(1)
    
    console.print(f"[cyan]Syncing {current_branch} onto {config.base_branch}...[/cyan]")
    
    try:
        sync_branch(config.base_branch, repo_root)
        console.print("[green]✓ Branch synced successfully![/green]")
    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def create_tests(
    provider: Optional[str] = typer.Option(None, help="AI provider (openai, anthropic, etc.)"),
    model: Optional[str] = typer.Option(None, help="AI model name"),
    temperature: Optional[float] = typer.Option(None, help="Temperature setting (0.0-1.0)"),
    max_tokens: Optional[int] = typer.Option(None, help="Maximum tokens for generation"),
    api_key: Optional[str] = typer.Option(None, help="API key (or use environment variable)"),
    update: bool = typer.Option(False, help="Update existing test files"),
):
    """Generate and update tests for changed files"""
    repo_root = find_repo_root()
    
    if repo_root is None:
        console.print("[red]Error: Not in a Git repository[/red]")
        raise typer.Exit(1)
    
    try:
        config = load_config(repo_root)
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    
    # Get adapter for language
    if config.language == "python":
        adapter = PythonPytestAdapter()
    else:
        console.print(f"[red]Error: Language {config.language} not supported yet[/red]")
        raise typer.Exit(1)
    
    # Get changed files
    console.print("[cyan]Detecting changed files...[/cyan]")
    try:
        changed_files = adapter.get_changed_files(
            repo_root,
            config.base_branch,
        )
    except Exception as e:
        console.print(f"[red]Error detecting changed files: {e}[/red]")
        raise typer.Exit(1)
    
    if not changed_files:
        console.print("[yellow]No changed source files found[/yellow]")
        raise typer.Exit(0)
    
    console.print(f"[green]Found {len(changed_files)} changed file(s):[/green]")
    for f in changed_files:
        console.print(f"  - {f}")
    
    # Initialize test service with provider/model overrides
    try:
        test_service = TestService(
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
            forge_config=config,
        )
        
        # Display AI provider info
        console.print(f"[cyan]Using AI provider: {test_service.config.provider}[/cyan]")
        console.print(f"[cyan]Using model: {test_service.config.model}[/cyan]")
        
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    
    # Generate tests
    test_dir = repo_root / config.test_dir
    test_dir.mkdir(parents=True, exist_ok=True)
    
    generated_tests = []
    updated_tests = []
    failed_files = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for file_path in changed_files:
            task = progress.add_task(f"Generating tests for {file_path}...", total=None)
            
            try:
                # Read source file
                source_path = repo_root / file_path
                if not source_path.exists():
                    console.print(f"[yellow]Warning: {file_path} does not exist, skipping[/yellow]")
                    progress.remove_task(task)
                    continue
                
                code = source_path.read_text()
                
                # Get test file path
                test_file_path = adapter.get_test_file_path(file_path, test_dir)
                
                # Check if test already exists
                if test_file_path.exists() and not update:
                    console.print(f"[yellow]Test file already exists: {test_file_path}, skipping (use --update to regenerate)[/yellow]")
                    progress.remove_task(task)
                    continue
                
                # Generate tests
                test_code = test_service.generate_tests_for_file(
                    file_path,
                    code,
                    test_file_path,
                )
                
                # Write test file
                test_file_path.parent.mkdir(parents=True, exist_ok=True)
                test_file_path.write_text(test_code)
                
                if test_file_path.exists() and update:
                    updated_tests.append(str(test_file_path))
                    progress.update(task, description=f"✓ Updated tests for {file_path}")
                else:
                    generated_tests.append(str(test_file_path))
                    progress.update(task, description=f"✓ Generated tests for {file_path}")
                
            except Exception as e:
                console.print(f"[red]Error generating tests for {file_path}: {e}[/red]")
                failed_files.append(file_path)
                progress.remove_task(task)
    
    if failed_files:
        console.print(f"[red]Failed to generate tests for {len(failed_files)} file(s)[/red]")
        raise typer.Exit(1)
    
    if not generated_tests and not updated_tests:
        console.print("[yellow]No tests generated or updated[/yellow]")
        raise typer.Exit(0)
    
    if generated_tests:
        console.print(f"[green]✓ Generated {len(generated_tests)} new test file(s)[/green]")
    if updated_tests:
        console.print(f"[green]✓ Updated {len(updated_tests)} existing test file(s)[/green]")


@app.command()
def test():
    """Run existing tests"""
    repo_root = find_repo_root()
    
    if repo_root is None:
        console.print("[red]Error: Not in a Git repository[/red]")
        raise typer.Exit(1)
    
    try:
        config = load_config(repo_root)
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    
    # Get adapter for language
    if config.language == "python":
        adapter = PythonPytestAdapter()
    else:
        console.print(f"[red]Error: Language {config.language} not supported yet[/red]")
        raise typer.Exit(1)
    
    # Run tests
    test_dir = repo_root / config.test_dir
    if not test_dir.exists():
        console.print(f"[yellow]Test directory {test_dir} does not exist[/yellow]")
        console.print("Run 'fg create-tests' first to generate tests.")
        raise typer.Exit(1)
    
    console.print("[cyan]Running tests...[/cyan]")
    success = adapter.run_tests(repo_root, test_dir)
    
    if success:
        console.print("[green]✓ All tests passed![/green]")
    else:
        console.print("[red]✗ Some tests failed[/red]")
        console.print("Please fix the failing tests before submitting.")
        raise typer.Exit(1)


@app.command()
def submit(
    provider: Optional[str] = typer.Option(None, help="AI provider (openai, anthropic, etc.)"),
    model: Optional[str] = typer.Option(None, help="AI model name"),
    temperature: Optional[float] = typer.Option(None, help="Temperature setting (0.0-1.0)"),
    max_tokens: Optional[int] = typer.Option(None, help="Maximum tokens for generation"),
    api_key: Optional[str] = typer.Option(None, help="API key (or use environment variable)"),
    skip_tests: bool = typer.Option(False, help="Skip test generation and validation"),
):
    """Sync, test, commit, and push branch"""
    repo_root = find_repo_root()
    
    if repo_root is None:
        console.print("[red]Error: Not in a Git repository[/red]")
        raise typer.Exit(1)
    
    try:
        config = load_config(repo_root)
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    
    current_branch = get_current_branch(repo_root)
    
    if current_branch == config.base_branch:
        console.print(
            f"[red]Error: Cannot submit {config.base_branch} branch[/red]"
        )
        console.print("Switch to a feature branch first.")
        raise typer.Exit(1)
    
    console.print(f"[cyan]Submitting branch: {current_branch}[/cyan]")
    
    # Step 1: Sync
    console.print("\n[bold]Step 1: Syncing branch...[/bold]")
    try:
        sync_branch(config.base_branch, repo_root)
        console.print("[green]✓ Branch synced[/green]")
    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    
    # Step 2: Create and run tests
    if not skip_tests:
        console.print("\n[bold]Step 2: Creating and running tests...[/bold]")
        try:
            # Create tests
            if config.language == "python":
                adapter = PythonPytestAdapter()
            else:
                console.print(f"[red]Error: Language {config.language} not supported yet[/red]")
                raise typer.Exit(1)
            
            changed_files = adapter.get_changed_files(repo_root, config.base_branch)
            
            if changed_files:
                test_service = TestService(
                    provider=provider,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    api_key=api_key,
                    forge_config=config,
                )
                
                # Display AI provider info
                console.print(f"[cyan]Using AI provider: {test_service.config.provider}[/cyan]")
                console.print(f"[cyan]Using model: {test_service.config.model}[/cyan]")
                
                test_dir = repo_root / config.test_dir
                test_dir.mkdir(parents=True, exist_ok=True)
                
                generated_tests = []
                for file_path in changed_files:
                    source_path = repo_root / file_path
                    if not source_path.exists():
                        continue
                    
                    test_file_path = adapter.get_test_file_path(file_path, test_dir)
                    if test_file_path.exists():
                        continue
                    
                    code = source_path.read_text()
                    test_code = test_service.generate_tests_for_file(
                        file_path, code, test_file_path
                    )
                    test_file_path.parent.mkdir(parents=True, exist_ok=True)
                    test_file_path.write_text(test_code)
                    generated_tests.append(str(test_file_path))
                
                if generated_tests:
                    console.print(f"[green]✓ Generated {len(generated_tests)} test file(s)[/green]")
                
                # Run tests
                success = adapter.run_tests(repo_root, test_dir)
                if not success:
                    console.print("[red]✗ Tests failed. Aborting submission.[/red]")
                    raise typer.Exit(1)
                console.print("[green]✓ All tests passed[/green]")
            else:
                console.print("[yellow]No changed files to test[/yellow]")
        except Exception as e:
            console.print(f"[red]Error during testing: {e}[/red]")
            raise typer.Exit(1)
    else:
        console.print("[yellow]Skipping tests (--skip-tests flag)[/yellow]")
    
    # Step 3: Stage and commit
    console.print("\n[bold]Step 3: Staging and committing changes...[/bold]")
    
    if not is_clean_working_tree(repo_root):
        # Stage all changes including generated tests
        try:
            stage_files(["."], repo_root)
            commit_changes("fg: add generated tests", repo_root)
            console.print("[green]✓ Changes committed[/green]")
        except RuntimeError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)
    else:
        console.print("[yellow]No changes to commit[/yellow]")
    
    # Step 4: Push
    console.print("\n[bold]Step 4: Pushing branch...[/bold]")
    try:
        push_branch(current_branch, repo_root)
        console.print("[green]✓ Branch pushed successfully![/green]")
    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    
    console.print(f"\n[bold green]✓ Submission complete![/bold green]")
    console.print(f"Branch {current_branch} is ready for review.")


if __name__ == "__main__":
    app()

