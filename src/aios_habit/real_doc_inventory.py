from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, List

LOCAL_CASES_DIR = Path.cwd() / "local_cases"
MOM_RUNTIME_DIR = LOCAL_CASES_DIR / "mom_pilot"
INVENTORY_FILE = MOM_RUNTIME_DIR / "inventory.json"

SUPPORTED_TEXT_EXTS = {".txt", ".md", ".markdown", ".csv", ".json"}
SUPPORTED_TABLE_EXTS = {".xlsx", ".xls"}
SUPPORTED_DOC_EXTS = set()  # no extra dependency currently declared
SUPPORTED_PDF_EXTS = set()  # no PDF extraction dependency currently declared
SUPPORTED_EXTS = SUPPORTED_TEXT_EXTS | SUPPORTED_TABLE_EXTS | SUPPORTED_DOC_EXTS | SUPPORTED_PDF_EXTS


@dataclass
class MomFileInventoryItem:
    relative_path: str
    file_type: str
    size_bytes: int
    modified_time: str
    sha256_short: str
    privacy_level: str = "local_only"
    supported: bool = False
    unsupported_reason: str = ""


@dataclass
class MomInventory:
    root_path: str
    root_exists: bool
    scanned_at: str
    total_files: int
    file_types: dict[str, int]
    total_bytes: int
    folder_summary: dict[str, int]
    duplicate_hashes: dict[str, list[str]]
    unsupported_files: list[dict[str, Any]]
    privacy_level: str = "local_only"
    files: list[MomFileInventoryItem] = field(default_factory=list)


def ensure_mom_runtime_dir() -> Path:
    MOM_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    return MOM_RUNTIME_DIR


def _sha256_short(path: Path, max_bytes: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        remaining = max_bytes
        while remaining > 0:
            chunk = f.read(min(65536, remaining))
            if not chunk:
                break
            h.update(chunk)
            remaining -= len(chunk)
    return h.hexdigest()[:16]


def _iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_file():
            yield path


def _support_reason(ext: str) -> tuple[bool, str]:
    if ext in SUPPORTED_EXTS:
        return True, ""
    if ext in {".pdf"}:
        return False, "pdf extraction dependency not available"
    if ext in {".docx", ".doc"}:
        return False, "docx/doc extraction dependency not available"
    return False, "unsupported file type"


def scan_mom_inventory(root_path: str | Path, write_runtime: bool = True) -> MomInventory:
    root = Path(root_path)
    root_exists = root.exists() and root.is_dir()
    scanned_at = datetime.now().isoformat()
    if not root_exists:
        inv = MomInventory(
            root_path=str(root),
            root_exists=False,
            scanned_at=scanned_at,
            total_files=0,
            file_types={},
            total_bytes=0,
            folder_summary={},
            duplicate_hashes={},
            unsupported_files=[],
            files=[],
        )
        if write_runtime:
            save_inventory(inv)
        return inv

    root_resolved = root.resolve()
    items: list[MomFileInventoryItem] = []
    file_types: Counter[str] = Counter()
    folder_summary: Counter[str] = Counter()
    hash_to_paths: defaultdict[str, list[str]] = defaultdict(list)
    total_bytes = 0
    unsupported: list[dict[str, Any]] = []

    for file_path in sorted(_iter_files(root_resolved), key=lambda p: str(p).lower()):
        try:
            rel = file_path.relative_to(root_resolved).as_posix()
            ext = file_path.suffix.lower() or "[no_ext]"
            stat = file_path.stat()
            sha = _sha256_short(file_path)
            supported, reason = _support_reason(ext)
            folder = Path(rel).parent.as_posix()
            if folder == ".":
                folder = "[root]"
            item = MomFileInventoryItem(
                relative_path=rel,
                file_type=ext,
                size_bytes=stat.st_size,
                modified_time=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                sha256_short=sha,
                supported=supported,
                unsupported_reason=reason,
            )
            items.append(item)
            file_types[ext] += 1
            folder_summary[folder] += 1
            total_bytes += stat.st_size
            hash_to_paths[sha].append(rel)
            if not supported:
                unsupported.append({
                    "relative_path": rel,
                    "file_type": ext,
                    "reason": reason,
                    "privacy_level": "local_only",
                })
        except OSError:
            continue

    duplicates = {h: paths for h, paths in hash_to_paths.items() if len(paths) > 1}
    inv = MomInventory(
        root_path=str(root),
        root_exists=True,
        scanned_at=scanned_at,
        total_files=len(items),
        file_types=dict(sorted(file_types.items())),
        total_bytes=total_bytes,
        folder_summary=dict(sorted(folder_summary.items())),
        duplicate_hashes=duplicates,
        unsupported_files=unsupported,
        files=items,
    )
    if write_runtime:
        save_inventory(inv)
    return inv


def inventory_to_dict(inv: MomInventory) -> dict[str, Any]:
    data = asdict(inv)
    data["files"] = [asdict(item) if hasattr(item, "relative_path") else item for item in inv.files]
    return data


def save_inventory(inv: MomInventory) -> Path:
    ensure_mom_runtime_dir()
    INVENTORY_FILE.write_text(json.dumps(inventory_to_dict(inv), ensure_ascii=False, indent=2), encoding="utf-8")
    return INVENTORY_FILE
