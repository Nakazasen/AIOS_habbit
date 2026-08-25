#!/usr/bin/env python3
"""Download and verify the pinned local reranker used by Workspace Chat."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from huggingface_hub import snapshot_download

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aios_habit.rag_v2.retrieval_backends import sha256_model_tree


TARGET_DIR = PROJECT_ROOT / "local_runs" / "retrieval_models" / "bge-reranker-v2-m3"
MODEL_ID = "BAAI/bge-reranker-v2-m3"
REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
EXPECTED_CHECKSUM = "sha256:8ac5c7407fac5d58a0e000c7dc821af8f1872ef66c1b659ac404b13e28a3a5a4"


def main() -> int:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY")
    print(f"Downloading {MODEL_ID} revision {REVISION} to {TARGET_DIR}...")
    TARGET_DIR.parent.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=MODEL_ID,
        revision=REVISION,
        local_dir=str(TARGET_DIR),
        token=token,
    )
    actual_checksum = sha256_model_tree(TARGET_DIR)
    print(f"Calculated checksum: {actual_checksum}")
    if actual_checksum.casefold() != EXPECTED_CHECKSUM.casefold():
        raise RuntimeError(
            f"Checksum mismatch: {actual_checksum} != {EXPECTED_CHECKSUM}"
        )
    print("Checksum verified successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
