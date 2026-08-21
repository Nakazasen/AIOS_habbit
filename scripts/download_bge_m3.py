#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from huggingface_hub import snapshot_download

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aios_habit.rag_v2.retrieval_backends import verify_model_tree, sha256_model_tree
from aios_habit.workspace_chat_rag_v2_deployment import APPROVED_MODEL_CHECKSUMS

TARGET_DIR = PROJECT_ROOT / "local_runs" / "retrieval_models" / "bge-m3-5617a9f"
EXPECTED_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
EXPECTED_CHECKSUMS = APPROVED_MODEL_CHECKSUMS

token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY")

print(f"Downloading BAAI/bge-m3 revision {EXPECTED_REVISION} to {TARGET_DIR}...")
TARGET_DIR.parent.mkdir(parents=True, exist_ok=True)
download_path = snapshot_download(
    repo_id="BAAI/bge-m3",
    revision=EXPECTED_REVISION,
    local_dir=str(TARGET_DIR),
    token=token,
)
print(f"Download completed at {download_path}")

print("Calculating checksum...")
actual_checksum = sha256_model_tree(TARGET_DIR)
print(f"Calculated checksum: {actual_checksum}")
print(f"Approved checksums:  {sorted(EXPECTED_CHECKSUMS)}")
if actual_checksum.casefold() not in {c.casefold() for c in EXPECTED_CHECKSUMS}:
    raise RuntimeError(f"Checksum mismatch: {actual_checksum} not in approved set")
print("Checksum verified successfully!")
