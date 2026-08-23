# -*- coding: utf-8 -*-
"""BGE-M3 Model Pack Verification and Discovery Module.

Provides versioned manifest checking, tree integrity verification,
and runtime discovery for both Desktop and VPS environments.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Optional, Tuple

LOGGER = logging.getLogger("aios_habit.model_pack")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MANIFEST_PATH = REPO_ROOT / "packaging" / "models" / "bge_m3_manifest.json"

BGE_M3_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
BGE_M3_CHECKSUM = "sha256:b1d887e03f13547609b4c6498ce8f357242edb5079a448c62d31d4caac320b61"


def verify_model_pack(
    model_dir: str | Path,
    manifest_path: Optional[str | Path] = None,
) -> dict[str, Any]:
    """Verify that a directory contains a valid, uncorrupted BGE-M3 model pack."""
    root = Path(model_dir).resolve()
    if not root.is_dir():
        return {
            "status": "unavailable",
            "reason": f"model_dir_not_found: {root}",
            "model_path": str(root),
        }

    manifest_file = Path(manifest_path) if manifest_path else DEFAULT_MANIFEST_PATH
    if not manifest_file.is_file():
        # Fallback to in-bundle manifest if packaged
        if hasattr(sys, "_MEIPASS"):
            bundled_manifest = Path(sys._MEIPASS) / "packaging" / "models" / "bge_m3_manifest.json"
            if bundled_manifest.is_file():
                manifest_file = bundled_manifest

    if not manifest_file.is_file():
        return {
            "status": "unavailable",
            "reason": "bge_m3_manifest_missing",
            "model_path": str(root),
        }

    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "status": "corrupted",
            "reason": f"bge_m3_manifest_unreadable: {exc}",
            "model_path": str(root),
        }

    expected_files: Mapping[str, Mapping[str, Any]] = manifest.get("files", {})
    if not expected_files:
        return {
            "status": "corrupted",
            "reason": "manifest_has_no_files",
            "model_path": str(root),
        }

    # Verify all expected files exist and match sizes
    for rel_path, file_meta in expected_files.items():
        target_file = root / rel_path
        if not target_file.is_file():
            return {
                "status": "unavailable",
                "reason": f"missing_model_file: {rel_path}",
                "model_path": str(root),
            }
        expected_size = file_meta.get("size")
        if expected_size is not None and target_file.stat().st_size != expected_size:
            return {
                "status": "corrupted",
                "reason": f"model_file_size_mismatch: {rel_path} (expected {expected_size}, got {target_file.stat().st_size})",
                "model_path": str(root),
            }

    # Verify model tree digest matches pinned checksum
    try:
        from aios_habit.rag_v2.retrieval_backends import sha256_model_tree
        actual_tree_checksum = sha256_model_tree(root)
    except Exception as exc:
        return {
            "status": "corrupted",
            "reason": f"model_tree_hash_failed: {exc}",
            "model_path": str(root),
        }

    approved = frozenset(manifest.get("approved_checksums", [BGE_M3_CHECKSUM]))
    if actual_tree_checksum not in approved:
        return {
            "status": "corrupted",
            "reason": f"model_checksum_unapproved: {actual_tree_checksum}",
            "actual_checksum": actual_tree_checksum,
            "approved_checksums": list(approved),
            "model_path": str(root),
        }

    return {
        "status": "ready",
        "model_id": manifest.get("model_id", "BAAI/bge-m3"),
        "revision": manifest.get("revision", BGE_M3_REVISION),
        "checksum": actual_tree_checksum,
        "model_path": str(root),
        "file_count": len(expected_files),
    }


def resolve_bge_m3_model_path(
    auto_configure_env: bool = True,
) -> Tuple[Optional[Path], dict[str, Any]]:
    """Discover, verify, and optionally export environment variables for BGE-M3."""
    candidates: list[Path] = []

    # 1. Explicit environment variable
    env_path = os.environ.get("AIOS_BGE_M3_MODEL_PATH", "").strip()
    if env_path:
        candidates.append(Path(env_path))

    # 2. PyInstaller bundle path
    if hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "models" / "bge-m3-5617a9f")

    # 3. Executable sibling path
    exe_dir = Path(sys.executable).resolve().parent
    candidates.append(exe_dir / "models" / "bge-m3-5617a9f")
    candidates.append(exe_dir / ".." / "models" / "bge-m3-5617a9f")

    # 4. Project local directories
    candidates.append(REPO_ROOT / "local_runs" / "retrieval_models" / "bge-m3-5617a9f")
    candidates.append(REPO_ROOT / "models" / "bge-m3-5617a9f")

    last_status: dict[str, Any] = {"status": "unavailable", "reason": "no_candidate_paths_found"}

    for candidate in candidates:
        if candidate.is_dir():
            result = verify_model_pack(candidate)
            if result.get("status") == "ready":
                if auto_configure_env:
                    os.environ["AIOS_BGE_M3_MODEL_PATH"] = str(candidate.resolve())
                    os.environ["AIOS_BGE_M3_MODEL_REVISION"] = str(result.get("revision", BGE_M3_REVISION))
                    os.environ["AIOS_BGE_M3_MODEL_CHECKSUM"] = str(result.get("checksum", BGE_M3_CHECKSUM))
                return candidate.resolve(), result
            else:
                last_status = result

    return None, last_status
