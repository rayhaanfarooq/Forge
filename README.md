# Forge

**Opinionated Git workflows with AI-generated tests**

Forge is a local-first developer platform built with Python and FastAPI that simplifies Git branch workflows and automates test generation using AI.

## Features

- **Graphite-style Git commands** (`forge sync`, `forge submit`)
- **Automatic AI-generated tests** for Python files
- **Dynamic AI provider/model switching** via configuration or CLI
- **Deterministic local execution**
- **Backend-ready architecture** for future dashboards and collaboration features

## Installation

### Prerequisites

- Python 3.9+
- Git
- pytest (will be installed as a dependency)

### Setup

1. Clone or download this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

Or install in development mode:

```bash
pip install -e .
```

3. Set up your AI provider API key in a `.env` file in your repository root:

```bash
# Option 1: Using .env file (recommended)
# Create a .env file in your repo root:
FORGE_PROVIDER=gemini  # or openai, anthropic
GOOGLE_API_KEY=your-api-key-here  # for Gemini
# OR
# OPENAI_API_KEY=your-api-key-here  # for OpenAI
# ANTHROPIC_API_KEY=your-api-key-here  # for Anthropic

# Option 2: Using environment variables
export OPENAI_API_KEY="your-api-key-here"
# Or for Anthropic
export ANTHROPIC_API_KEY="your-api-key-here"
# Or for Gemini
export GOOGLE_API_KEY="your-api-key-here"
```

## Usage

### Initialize Forge

Navigate to your Git repository and run:

```bash
forge init
```

This will:
- Detect your repository language (Python in MVP)
- Create a `.fg.yml` configuration file
- Set up the test directory structure

### Workflow

```bash
# Create a feature branch
git checkout -b feature/my-change

# Make your code changes
# ... edit files ...

# Sync your branch with the base branch
forge sync

# Generate tests for changed files
forge create-tests

# Run tests
forge test

# Submit your branch (sync + create-tests + test + commit + push)
forge submit
```

### Commands

#### `forge init`

Initialize Forge in the current Git repository.

Options:
- `--base-branch`: Base branch name (default: `main`)
- `--language`: Project language (auto-detected if not specified)
- `--test-dir`: Directory for test files (default: `tests/`)

#### `forge sync`

Rebase the current branch onto the base branch.

```bash
forge sync
```

#### `forge create-tests`

Generate and update tests for changed Python files.

Options:
- `--provider`: AI provider (`openai`, `anthropic`, etc.)
- `--model`: AI model name (e.g., `gpt-4-turbo-preview`, `gpt-4o-mini`)
- `--temperature`: Temperature setting (0.0-1.0)
- `--max-tokens`: Maximum tokens for generation
- `--api-key`: API key (or use environment variable)
- `--update`: Update existing test files (regenerate them)

```bash
# Generate tests for changed files (skip existing)
forge create-tests

# Generate tests with specific model
forge create-tests --provider openai --model gpt-4o-mini

# Update existing test files
forge create-tests --update
```

#### `forge test`

Run existing tests.

```bash
# Run all tests
forge test
```

#### `forge submit`

Complete workflow: sync, create-tests, test, commit, and push.

Options:
- `--provider`: AI provider (overrides config)
- `--model`: AI model name (overrides config)
- `--temperature`: Temperature setting (overrides config)
- `--max-tokens`: Maximum tokens (overrides config)
- `--api-key`: API key (overrides env var)
- `--skip-tests`: Skip test generation and validation

```bash
forge submit --provider openai --model gpt-4o-mini
```

## Configuration

Forge uses a `.fg.yml` file in your repository root:

```yaml
base_branch: main
language: python
test_framework: pytest
test_dir: tests/
include:
  - src/
exclude:
  - venv/
  - node_modules/

# AI Configuration (optional)
ai:
  provider: openai
  model: gpt-4-turbo-preview
  temperature: 0.3
  max_tokens: 2048
```

### AI Provider Configuration

You can configure the AI provider and model in `.fg.yml`. CLI flags override these settings for that command invocation.

**Priority order:**
1. CLI flags (highest priority)
2. `.fg.yml` configuration
3. Environment variables (`FORGE_PROVIDER` or `FORGE_AI_PROVIDER` from `.env` file)
4. Defaults

**Using `.env` file:**
You can set the default provider in your `.env` file:
```bash
FORGE_PROVIDER=gemini
GOOGLE_API_KEY=your-api-key-here
```

Then simply run:
```bash
forge create-tests
```

No need to specify `--provider gemini` every time!

**Supported Providers (MVP):**
- `openai`: OpenAI GPT models
  - Models: `gpt-4-turbo-preview`, `gpt-4`, `gpt-4-mini`, `gpt-3.5-turbo`

**Future Providers:**
- `anthropic`: Claude models
- `azure-openai`: Azure OpenAI
- Local LLMs (Ollama, LM Studio)

## How It Works

1. **Change Detection**: Forge identifies files changed since the base branch
2. **File Filtering**: Only source files matching your configuration are processed
3. **Test Generation**: AI generates pytest tests for public functions/classes
4. **Test Execution**: Tests are run locally using pytest
5. **Validation**: Submission is blocked if tests fail

## Architecture

```
forge/
├─ cli.py              # CLI interface
├─ config.py           # Configuration management
├─ git_ops.py          # Git operations
├─ diff.py             # Change detection
├─ test_service.py     # AI test generation
├─ ai/                 # AI provider abstraction
│  ├─ base.py          # AIProvider interface
│  ├─ openai.py        # OpenAIProvider
│  ├─ registry.py      # Provider registry
│  └─ config.py        # AI config parsing
├─ adapters/
│  └─ python/
│     └─ pytest_adapter.py
└─ backend/
   └─ app.py          # FastAPI (future)
```

## Dynamic AI Provider Switching

Forge supports dynamic switching of AI providers and models without code changes:

- **Configuration-based**: Set provider/model in `.fg.yml`
- **CLI overrides**: Override settings per command
- **Extensible**: Add new providers by implementing the `AIProvider` interface
- **Model-agnostic**: Core logic is decoupled from specific AI providers

### Adding a New Provider

1. Create a new provider class inheriting from `AIProvider`
2. Implement required methods
3. Register in `forge/ai/registry.py`

Example:

```python
from forge.ai.base import AIProvider, AIConfig

class MyProvider(AIProvider):
    def generate_tests(self, prompt: str) -> str:
        # Implementation
        pass
    
    def get_supported_models(self) -> list[str]:
        return ["model1", "model2"]

# Register
from forge.ai.registry import register_provider
register_provider("myprovider", MyProvider)
```

## Safety Features

- ✅ Never auto-commits failing tests
- ✅ Never modifies the base branch
- ✅ All Git failures surface clearly
- ✅ Respects `.gitignore`
- ✅ Aborts on partial failures
- ✅ API keys never stored in config files

## Limitations (MVP)

- Python support only
- Local execution only
- No automatic conflict resolution
- No PR creation
- No frontend/E2E test generation

## Future Roadmap

- FastAPI backend mode
- TypeScript support
- Test history persistence
- Dashboard (read-only)
- Merge conflict resolution
- PR automation
- Additional AI providers (Anthropic, Azure OpenAI, local models)

## License

MIT

