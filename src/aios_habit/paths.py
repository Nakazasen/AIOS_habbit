"""Repository path constants for AIOS Habit."""

from pathlib import Path

REPO_ROOT = Path.cwd()

IGNORE_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "inbox_local_only",
    "raw",
    "cache",
    "private",
    "secrets",
}
