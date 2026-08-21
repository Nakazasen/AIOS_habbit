"""Portable defaults for Workspace Chat's optional local integrations."""

from __future__ import annotations

import os
from pathlib import Path


def default_agent_workspace_root() -> Path:
    """Return the explicitly configured root, or the repository containing this module."""
    configured = os.environ.get("AIOS_AGENT_WORKSPACE_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def load_env_file(env_file: Path | str | None = None) -> None:
    """Load key-value pairs from .env file into os.environ if not already present."""
    if env_file is None:
        target = default_agent_workspace_root() / ".env"
    else:
        target = Path(env_file)
    if not target.is_file():
        return
    try:
        content = target.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass


load_env_file()
