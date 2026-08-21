import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aios_habit.rag_v2.retrieval_backends import verify_model_tree, sha256_model_tree
from aios_habit.workspace_chat_rag_v2_deployment import APPROVED_MODEL_CHECKSUMS

TARGET_DIR = PROJECT_ROOT / "local_runs" / "retrieval_models" / "bge-m3-5617a9f"
EXPECTED_CHECKSUMS = APPROVED_MODEL_CHECKSUMS

cache_dir = TARGET_DIR / ".cache"
if cache_dir.exists():
    print(f"Removing {cache_dir}...")
    shutil.rmtree(cache_dir, ignore_errors=True)

files = sorted(path for path in TARGET_DIR.rglob("*") if path.is_file())
print(f"Total files in model tree: {len(files)}")
for f in files:
    print(f"  {f.relative_to(TARGET_DIR).as_posix()} ({f.stat().st_size} bytes)")

actual_checksum = sha256_model_tree(TARGET_DIR)
print(f"Calculated checksum: {actual_checksum}")
print(f"Approved checksums:  {sorted(EXPECTED_CHECKSUMS)}")
if actual_checksum.casefold() not in {c.casefold() for c in EXPECTED_CHECKSUMS}:
    raise RuntimeError(f"Checksum mismatch: {actual_checksum} not in approved set")
print("Checksum matched perfectly!")
