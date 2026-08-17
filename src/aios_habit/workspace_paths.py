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
