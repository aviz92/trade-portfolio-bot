# UV: The Fast Python Package Manager

UV is a Rust-based "Cargo for Python" that replaces pip, pip-tools, pipx, poetry, pyenv, and virtualenv with a single tool. Written by Astral (creators of Ruff), it delivers **10-100x performance improvements** — think TensorFlow installs in 25 seconds instead of 3 minutes.

**Installation:** [Download and install UV here](https://docs.astral.sh/uv/getting-started/installation/)

---

## Why developers are switching

- **Speed**: CI/CD pipelines drop from 25+ minutes to seconds
- **Simplicity**: No more juggling multiple tools or activating venvs
- **Modern**: Built-in Python version management and dependency groups
- **Compatible**: Works with existing pip/poetry workflows

---

## About Astral and Ruff

UV comes from [Astral](https://astral.sh/), the same team behind [Ruff](https://docs.astral.sh/ruff/) — the extremely fast Python linter and formatter. Like UV, Ruff is written in Rust and delivers massive performance improvements (100x faster than flake8). It replaces flake8, isort, black, and more with a single blazingly fast tool.

---

## Starting a new Python project

```bash
uv init my-ai-app
cd my-ai-app
```

Project structure:

```
my-ai-app/
├── .gitignore
├── .python-version    # Pins Python version
├── README.md
├── hello.py
└── pyproject.toml     # Modern Python packaging
```

Add dependencies and run:

```bash
uv add openai fastapi
uv run hello.py
```

UV automatically creates the venv, installs dependencies, and generates `uv.lock` for reproducible builds.

---

## Working with existing projects

Clone and sync:

```bash
git clone https://github.com/org/project.git
cd project
uv sync
```

`uv sync` creates the venv and installs exact versions from `uv.lock` for identical team setups.

Production deployments (exclude dev dependencies):

```bash
uv sync --no-dev
```

---

## Python version management

Built-in Python version management (replaces pyenv):

```bash
# Install Python versions
uv python install 3.12
uv python install 3.11 3.12 3.13  # Multiple at once

# Pin project to specific version
uv python pin 3.12  # Creates .python-version

# List available versions
uv python list
```

> **Automatic Python installation**: UV installs missing Python versions during `uv sync`.

---

## Dependency groups / extras

UV uses modern dependency groups following PEP 735:

```toml
[project]
name = "my-app"
dependencies = [
    "fastapi>=0.100.0",
    "sqlalchemy>=2.0.0",
]

[dependency-groups]
dev = [
    "pytest>=7.4.0",
    "ruff>=0.4.0",
]
docs = [
    "mkdocs>=1.5.0",
    "mkdocs-material>=9.0.0",
]
lint = [
    "mypy>=1.5.0",
    "ruff>=0.4.0",
]
```

Managing dependency groups:

```bash
uv add --dev pytest ruff             # Add to dev group
uv add --group docs mkdocs           # Add to a named group
uv sync                              # Install all groups
uv sync --no-dev                     # Production only
uv sync --group lint                 # Install specific group
uv sync --only-group dev             # Install ONLY dev group
```

### Optional extras (PEP 508)

```toml
[project.optional-dependencies]
postgres = ["psycopg2>=2.9"]
redis = ["redis>=5.0"]
all = ["psycopg2>=2.9", "redis>=5.0"]
```

```bash
uv add "mypackage[postgres]"         # Install with extras
uv add "mypackage[postgres,redis]"   # Multiple extras
```

---

## The `--refresh` flag

The `--refresh` flag forces UV to re-resolve and re-download packages, bypassing the cache. This is useful when:

- A package was published with the same version but different content (e.g., a bad release was overwritten)
- You suspect your local cache is stale or corrupted
- You want to ensure you're getting the absolute latest compatible version

```bash
# Refresh all packages
uv add python-base-toolkit --refresh

# Refresh a specific package only
uv sync --refresh-package python-base-toolkit

# Refresh all packages during sync
uv sync --refresh

# Refresh when installing tools
uv tool install ruff --refresh
```

> **Tip**: `--refresh` re-resolves dependencies from the registry but still respects version constraints in `pyproject.toml`. It does **not** upgrade to newer versions beyond what your constraints allow — use `uv add package@latest` or update `pyproject.toml` for that.

---

## `uv lock` & lockfile management

The `uv.lock` file captures the exact resolved versions of every dependency (including transitive ones), ensuring reproducible installs across machines and CI.

```bash
# Generate or update the lockfile without installing
uv lock

# Update a specific package in the lockfile
uv lock --upgrade-package requests

# Upgrade all packages to latest allowed versions
uv lock --upgrade

# Check if the lockfile is up to date (useful in CI)
uv lock --check

# Export lockfile to requirements.txt format (for compatibility)
uv export --format requirements-txt -o requirements.txt
uv export --format requirements-txt --no-dev -o requirements.txt
```

> **Best practice**: Always commit `uv.lock` to version control. This guarantees every developer and CI run gets identical dependency trees.

### Lockfile in `pyproject.toml`

```toml
[tool.uv]
# Lock to a specific index
index-url = "https://pypi.org/simple"

# Allow pre-releases for specific packages
[tool.uv.sources]
my-package = { git = "https://github.com/org/my-package", branch = "main" }
```

---

## Workspace / monorepo support

UV natively supports workspaces for monorepos — multiple packages in a single repo sharing a lockfile.

```
my-monorepo/
├── pyproject.toml         # Root workspace config
├── uv.lock                # Shared lockfile
├── packages/
│   ├── core/
│   │   └── pyproject.toml
│   ├── api/
│   │   └── pyproject.toml
│   └── worker/
│       └── pyproject.toml
```

Root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = ["packages/*"]
```

Each member has its own `pyproject.toml` and can depend on sibling packages:

```toml
# packages/api/pyproject.toml
[project]
name = "api"
dependencies = [
    "core",          # Sibling workspace package
    "fastapi>=0.100",
]
```

```bash
# Sync the entire workspace
uv sync

# Sync a specific workspace member
uv sync --package api

# Run a command in a specific package context
uv run --package api uvicorn api.main:app

# Add a dep to a specific member
uv add httpx --package worker
```

> **Key benefit**: All workspace members share a single `uv.lock`, preventing version conflicts across packages in the same repo.

---

## Migrating from pip / poetry / pipenv

### From pip + requirements.txt

```bash
# One-time migration: import existing requirements
uv init
uv add $(cat requirements.txt)   # Or manually copy to pyproject.toml

# Or use pip compatibility mode directly
uv pip install -r requirements.txt
uv pip freeze > requirements.txt  # Still works if needed
```

### From Poetry

```bash
# UV reads pyproject.toml natively — just swap the commands:
# poetry install  →  uv sync
# poetry add X    →  uv add X
# poetry run X    →  uv run X
# poetry shell    →  (not needed, uv run handles activation)

# Export for interop
uv export --format requirements-txt -o requirements.txt
```

UV supports the `[tool.poetry]` format during migration. After migrating, clean up to use `[project]` (PEP 621) instead.

### From pipenv

```bash
# pipenv install   →  uv sync
# pipenv install X →  uv add X
# pipenv run X     →  uv run X

# Import from Pipfile
uv init
# Manually copy [packages] and [dev-packages] into pyproject.toml
```

### Migration cheat sheet

| Old command | UV equivalent |
|---|---|
| `pip install X` | `uv add X` |
| `pip install -r requirements.txt` | `uv sync` |
| `pip freeze` | `uv export --format requirements-txt` |
| `poetry install` | `uv sync` |
| `poetry add X` | `uv add X` |
| `poetry run X` | `uv run X` |
| `pipenv install X` | `uv add X` |
| `pyenv install 3.12` | `uv python install 3.12` |
| `python -m venv .venv` | `uv venv` (or automatic via `uv run`) |

---

## CI/CD integration

### GitHub Actions

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install UV
        uses: astral-sh/setup-uv@v4
        with:
          version: "latest"
          enable-cache: true           # Cache the UV package cache

      - name: Set up Python
        run: uv python install

      - name: Install dependencies
        run: uv sync --frozen          # --frozen fails if lockfile is out of date

      - name: Run tests
        run: uv run pytest

      - name: Run linter
        run: uv run ruff check .
```

> **`--frozen` vs `--locked`**: Use `--frozen` in CI — it installs from the lockfile and fails if `uv.lock` doesn't match `pyproject.toml`, catching lockfile drift early.

### Docker

```dockerfile
FROM python:3.12-slim

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first (layer caching)
COPY pyproject.toml uv.lock ./

# Install production dependencies only
RUN uv sync --frozen --no-dev --no-install-project

# Copy source
COPY . .

# Install the project itself
RUN uv sync --frozen --no-dev

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

### GitLab CI

```yaml
test:
  image: python:3.12-slim
  before_script:
    - pip install uv
    - uv sync --frozen
  script:
    - uv run pytest
    - uv run ruff check .
  cache:
    paths:
      - .venv/
      - ~/.cache/uv/
```

### Cache keys for CI

```yaml
# GitHub Actions — cache UV's package cache
- uses: actions/cache@v4
  with:
    path: ~/.cache/uv
    key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
    restore-keys: uv-${{ runner.os }}-
```

---

## Essential commands reference

```bash
# Project setup
uv init myproject                    # Create new project
uv add requests                      # Add dependency
uv add requests==2.31.0              # Add pinned version
uv add "requests>=2.28,<3"           # Add with constraints
uv add --dev pytest                  # Add dev dependency
uv add --group lint ruff             # Add to named group
uv remove requests                   # Remove dependency
uv sync                              # Install from lockfile
uv sync --frozen                     # Install, fail if lockfile changed (CI)
uv sync --no-dev                     # Production install

# Refresh / cache control
uv add package --refresh             # Re-resolve & re-download package
uv sync --refresh                    # Refresh all packages
uv sync --refresh-package X          # Refresh specific package

# Lockfile
uv lock                              # Update lockfile only
uv lock --upgrade                    # Upgrade all to latest allowed
uv lock --upgrade-package X          # Upgrade specific package
uv lock --check                      # Verify lockfile is current
uv export --format requirements-txt  # Export to requirements.txt

# Running code
uv run script.py                     # Run in project environment
uv run pytest                        # Run tests
uv run --package api uvicorn ...     # Run in workspace member context

# Python management
uv python install 3.12               # Install Python version
uv python pin 3.12                   # Set project Python
uv python list                       # List available versions

# Tools
uvx black .                          # Run tool temporarily (no install)
uv tool install ruff                 # Install tool globally
uv tool upgrade ruff                 # Upgrade global tool

# Package management (pip-compatible)
uv pip install requests              # Direct pip replacement
uv pip install -r requirements.txt   # From requirements file
uv pip freeze                        # List installed packages
```

---

## New project flow (full example)

```bash
uv init my-project
cd my-project
cursor .

uv add openai python-dotenv fastapi python-base-toolkit
uv add --dev pytest ruff ipykernel
echo "API_KEY=your-key" > .env

git init
git add .
git commit -m "Initial commit"

# Create new repo with GitHub CLI
gh repo create my-project --private --source=. --remote=origin --push
```

---

## Resources

- [UV Documentation](https://docs.astral.sh/uv/)
- [UV GitHub](https://github.com/astral-sh/uv)
- [Ruff (linter/formatter)](https://docs.astral.sh/ruff/)
- [PEP 735 – Dependency Groups](https://peps.python.org/pep-0735/)
- [PEP 621 – pyproject.toml metadata](https://peps.python.org/pep-0621/)
