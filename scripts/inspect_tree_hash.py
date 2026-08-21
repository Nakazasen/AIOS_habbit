import hashlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET_DIR = PROJECT_ROOT / "local_runs" / "retrieval_models" / "bge-m3-5617a9f"
EXPECTED_CHECKSUM = "sha256:f8faedab99c4c901e5c2f311ea3f32786b3395b5cbb0c10a60c2b83970d64405"

def hash_files(file_paths):
    digest = hashlib.sha256()
    for path in sorted(file_paths):
        relative = path.relative_to(TARGET_DIR).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(path.stat().st_size.to_bytes(8, "big"))
        with path.open("rb") as handle:
            while block := handle.read(1024 * 1024):
                digest.update(block)
    return f"sha256:{digest.hexdigest()}"

all_files = [p for p in TARGET_DIR.rglob("*") if p.is_file() and not p.as_posix().startswith(str(TARGET_DIR / ".cache"))]

tests = {
    "all_30_files": all_files,
    "no_ds_store": [p for p in all_files if p.name != ".DS_Store"],
    "no_imgs": [p for p in all_files if "imgs" not in p.parts],
    "no_onnx": [p for p in all_files if "onnx" not in p.parts],
    "no_imgs_no_onnx": [p for p in all_files if "imgs" not in p.parts and "onnx" not in p.parts],
    "no_imgs_no_onnx_no_longjpg": [p for p in all_files if "imgs" not in p.parts and "onnx" not in p.parts and p.name != "long.jpg"],
    "no_ds_store_no_onnx": [p for p in all_files if p.name != ".DS_Store" and "onnx" not in p.parts],
}

for name, flist in tests.items():
    h = hash_files(flist)
    match = "MATCH!" if h == EXPECTED_CHECKSUM else "no"
    print(f"{name:30s} ({len(flist)} files): {h} -> {match}")
