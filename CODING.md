# Coding Conventions

> Quick reference for contributors. All config lives in `pyproject.toml`.

## Python Version

- **Minimum:** Python 3.11+
- Set in `pyproject.toml` → `requires-python = ">=3.11"`

## Ruff (Linter & Formatter)

Ruff handles both linting and formatting. Config in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM"]
```

**Enabled rule sets:**
| Code | Category |
|------|----------|
| `E`  | pycodestyle errors |
| `F`  | pyflakes |
| `I`  | isort (import ordering) |
| `N`  | pep8-naming |
| `UP` | pyupgrade (modern Python syntax) |
| `B`  | flake8-bugbear |
| `SIM`| flake8-simplify |

**How to run:**
```bash
ruff check .              # lint
ruff check . --fix        # lint + auto-fix
ruff format .             # format
ruff format . --check     # check formatting without changes
```

### Import Order

The `I` rule enforces isort-compatible import ordering:
1. Standard library
2. Third-party packages
3. Local imports

Ruff auto-fixes import order with `--fix`.

## mypy (Type Checker)

Strict mode is enabled:

```toml
[tool.mypy]
python_version = "3.11"
strict = true
```

**How to run:**
```bash
mypy bot/ commands/
```

Strict mode requires type annotations on all function signatures and disallows `Any` without explicit opt-in.

## pytest (Testing)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.coverage.run]
source = ["bot", "commands"]
omit = ["bot/__main__.py"]

[tool.coverage.report]
fail_under = 50
show_missing = true
```

**How to run:**
```bash
pytest                        # run all tests
pytest tests/test_foo.py      # run specific file
pytest -x                     # stop on first failure
pytest --cov                  # with coverage report
pytest --cov --cov-report=html  # HTML coverage report
```

- **asyncio_mode = auto** — no need to mark async tests with `@pytest.mark.asyncio`
- **Coverage threshold:** 50% minimum (enforced by `fail_under = 50`)
- **Coverage sources:** `bot/` and `commands/` packages

## Pre-commit Hooks

Installed as a dev dependency. Config in `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

**Setup:**
```bash
pip install -e ".[dev]"
pre-commit install
```

Hooks run automatically on `git commit` — ruff lint (with auto-fix) and ruff format.

## Project Structure

The `bot/core/` package follows **hexagonal architecture** (ports & adapters):

```
bot/core/
├── models.py        # Domain entities (pure data, no I/O)
├── ports.py         # Abstract interfaces (ABCs for repositories, services)
├── use_cases.py     # Business logic (depends only on ports)
└── repositories.py  # Concrete implementations of ports
```

- **models** — Pydantic models or dataclasses representing domain objects
- **ports** — Abstract base classes defining what the core needs from the outside
- **use_cases** — Application logic; depends on ports, never on concrete implementations
- **repositories** — Adapter implementations (file I/O, APIs, databases)

## Code Style Notes

- Line length: **100 characters**
- Use `async`/`await` throughout — the bot is async (python-telegram-bot)
- Prefer `pathlib.Path` over `os.path`
- Use type annotations on all functions (enforced by mypy strict)
- Packages: `bot/` (core bot logic), `commands/` (Telegram command handlers)
