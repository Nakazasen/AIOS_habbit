import hashlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET_DIR = PROJECT_ROOT / "local_runs" / "retrieval_models" / "bge-m3-5617a9f"
EXPECTED_CHECKSUM = "sha256:f8faedab99c4c901e5c2f311ea3f32786b3395b5cbb0c10a60c2b83970d64405"

files = sorted(p for p in TARGET_DIR.rglob("*") if p.is_file() and not p.as_posix().startswith(str(TARGET_DIR / ".cache")))

print("Individual file details:")
for f in files:
    content = f.read_bytes()
    h = hashlib.sha256(content).hexdigest()
    has_crlf = b"\r\n" in content
    print(f"  {f.relative_to(TARGET_DIR).as_posix():35s} {len(content):10d} bytes | CRLF: {has_crlf} | sha256: {h[:16]}...")
