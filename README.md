# Forge

**Opinionated Git workflows with AI-generated tests**

Forge is a local-first developer platform that simplifies Git branch workflows and automates test generation using AI.

## Quick Start

1. **Install dependencies:**

   ```bash
   pip install -e .
   ```

2. **Set up your AI provider API key** in a `.env` file:

   ```bash
   FORGE_PROVIDER=gemini  # or openai
   GOOGLE_API_KEY=your-api-key-here  # for Gemini
   # OR
   # OPENAI_API_KEY=your-api-key-here  # for OpenAI
   ```

3. **Activate your virtual environment** (if using one):

   ```bash
   source venv/bin/activate  # or your venv path
   ```

4. **Initialize Forge** in your Git repository:

   ```bash
   forge init
   ```

5. **Start using Forge commands:**
   ```bash
   forge --help  # See all available commands
   ```

## Commands

### `forge init`

Initialize Forge in the current Git repository. Creates `.fg.yml` configuration file.

```bash
forge init
forge init --base-branch main --test-dir tests/
```

### `forge branch`

Create a new branch or list all branches.

```bash
forge branch                    # List all branches
forge branch feature/my-change  # Create new branch
```

### `forge switch`

Switch to an existing branch.

```bash
forge switch feature/my-change
```

### `forge sync`

Rebase current branch onto the base branch.

```bash
forge sync
```

### `forge create-tests`

Generate AI-powered tests for changed files.

```bash
forge create-tests
forge create-tests --provider gemini --model gemini-2.0-flash-lite
forge create-tests --update  # Regenerate existing tests
```

### `forge test`

Run existing tests.

```bash
forge test
```

### `forge submit`

Complete workflow: sync, create-tests, test, commit, and push.

```bash
forge submit
forge submit --provider gemini --skip-tests
```

## Workflow Example

```bash
# Create a feature branch
forge branch feature/my-change

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
  provider: gemini
  model: gemini-2.0-flash-lite
  temperature: 0.3
  max_tokens: 2048
```

**Configuration priority:**

1. CLI flags (highest priority)
2. `.fg.yml` configuration
3. Environment variables from `.env` file
4. Defaults

## AI Providers

**Supported:**

- `openai`: OpenAI GPT models (gpt-4-turbo-preview, gpt-4o-mini, etc.)
- `gemini`: Google Gemini models (gemini-2.0-flash-lite, etc.)

Set your provider in `.env`:

```bash
FORGE_PROVIDER=gemini
GOOGLE_API_KEY=your-key-here
```

## In Progress

🚧 **Multi-Repository Tracking with SQLite Database**

- SQLite database to track multiple repositories
- Centralized metadata and test history
- Cross-repo analytics and insights

🚧 **Dashboard**

- Web-based dashboard for visualizing repository metrics
- Test coverage visualization
- Branch management interface
- Historical test generation tracking

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
│  ├─ gemini.py        # GeminiProvider
│  └─ registry.py      # Provider registry
├─ adapters/
│  └─ python/
│     └─ pytest_adapter.py
└─ backend/
   └─ app.py          # FastAPI (for future dashboard)
```

## Safety Features

- ✅ Never auto-commits failing tests
- ✅ Never modifies the base branch
- ✅ All Git failures surface clearly
- ✅ Respects `.gitignore`
- ✅ Aborts on partial failures
- ✅ API keys never stored in config files

## License

MIT
