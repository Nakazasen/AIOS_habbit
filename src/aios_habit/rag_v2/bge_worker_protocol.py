"""Shared protocol helpers for the persistent BGE worker pipe (SPEED-COLDSTART).

A persistent worker keeps the pinned BGE-M3 model, the numpy dense matrix
cache, and the sparse inverted index alive across Streamlit restarts. A
question asked right after an app restart then re-attaches to the warm worker
instead of paying the cold init again (KDTVN-PC0575: 180.9 s on an idle disk,
up to ~408 s under disk load).

Transport is a Windows named pipe (``multiprocessing.connection``, ``AF_PIPE``)
carrying the same newline-free JSON request/response objects as the legacy
stdio worker. The pipe name binds both the code fingerprint (so a daemon from
an older build is never reused) and the canonical config (so one pipe serves
exactly one query-mode pipeline). Enabled only when
``AIOS_RAGV2_WORKER_PERSIST`` is truthy; the legacy subprocess path remains the
default and is untouched.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Mapping

PERSIST_ENV_VAR = "AIOS_RAGV2_WORKER_PERSIST"
PROTOCOL_VERSION = "persist-1"
_PIPE_PREFIX = "aios_bge_worker"


def persistent_worker_enabled() -> bool:
    """Whether the persistent named-pipe worker path is enabled."""
    value = str(os.environ.get(PERSIST_ENV_VAR, "")).strip().casefold()
    return value in {"1", "true", "yes", "on"}


def worker_code_fingerprint() -> str:
    """Fingerprint of the worker source file, so stale daemons are never attached."""
    path = Path(__file__).with_name("bge_subprocess_worker.py")
    try:
        payload = path.read_bytes()
    except OSError:
        payload = b""
    return hashlib.sha256(payload).hexdigest()[:16]


def canonical_config_json(config: Any) -> str:
    """Stable JSON for a ``RagV2DevConfig`` used for pipe naming."""
    if is_dataclass(config):
        payload = dict(asdict(config))
    elif isinstance(config, Mapping):
        payload = dict(config)
    else:
        payload = {}
    normalized: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, Path):
            value = str(value)
        elif isinstance(value, tuple):
            value = list(value)
        normalized[str(key)] = value
    return json.dumps(normalized, sort_keys=True, ensure_ascii=False, default=str)


def pipe_name_for_config(config: Any) -> str:
    """Deterministic pipe address for one code build + one pipeline config."""
    digest = hashlib.sha256(
        "|".join(
            (
                PROTOCOL_VERSION,
                worker_code_fingerprint(),
                canonical_config_json(config),
            )
        ).encode("utf-8")
    ).hexdigest()[:24]
    return rf"\\.\pipe\{_PIPE_PREFIX}_{digest}"


def authkey_for_worker() -> bytes:
    """Shared pipe authkey; local-only transport with per-user pipe ACL."""
    return hashlib.sha256(
        f"{PROTOCOL_VERSION}|{worker_code_fingerprint()}|authkey".encode("utf-8")
    ).digest()
