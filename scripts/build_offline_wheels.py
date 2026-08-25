# -*- coding: utf-8 -*-
"""Build internal offline wheels for ExcaliFlow Studio and nakazasen-ai-router.

Produces:
  - vendor/wheels/excaliflow-0.1.3-py3-none-any.whl
  - vendor/wheels/nakazasen_ai_router-0.8.0-py3-none-any.whl
  - vendor/wheels/checksums.json
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import zipfile

REPO_ROOT = Path(__file__).resolve().parent.parent
VENDOR_WHEELS_DIR = REPO_ROOT / "vendor" / "wheels"
VENDOR_WHEELS_LINUX_DIR = REPO_ROOT / "vendor" / "wheels_linux"
EXCALIFLOW_SRC_DIR = REPO_ROOT / ".agents" / "skills" / "excaliflow" / "src" / "excaliflow"
SITE_PACKAGES_DIR = REPO_ROOT / ".venv" / "Lib" / "site-packages"


def make_wheel(
    wheel_path: Path,
    dist_name: str,
    version: str,
    package_dirs: dict[str, Path],
    summary: str,
) -> None:
    """Create a standard pure Python wheel archive."""
    dist_info_name = f"{dist_name}-{version}.dist-info"
    record_entries: list[str] = []

    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Write package files
        for pkg_name, src_dir in package_dirs.items():
            for root, _, files in os.walk(src_dir):
                for f in files:
                    if f.endswith(".pyc") or "__pycache__" in root:
                        continue
                    src_file = Path(root) / f
                    rel_to_src = src_file.relative_to(src_dir)
                    arcname = f"{pkg_name}/{rel_to_src.as_posix()}"
                    data = src_file.read_bytes()
                    zf.writestr(arcname, data)
                    sha = hashlib.sha256(data).hexdigest()
                    record_entries.append(f"{arcname},sha256={sha},{len(data)}")

        # Write METADATA
        metadata_content = (
            f"Metadata-Version: 2.1\n"
            f"Name: {dist_name.replace('_', '-')}\n"
            f"Version: {version}\n"
            f"Summary: {summary}\n"
            f"Author: Nakazasen\n"
            f"License: Proprietary / Internal\n"
            f"Requires-Python: >=3.11\n"
        ).encode("utf-8")
        zf.writestr(f"{dist_info_name}/METADATA", metadata_content)
        sha_meta = hashlib.sha256(metadata_content).hexdigest()
        record_entries.append(f"{dist_info_name}/METADATA,sha256={sha_meta},{len(metadata_content)}")

        # Write WHEEL
        wheel_content = (
            f"Wheel-Version: 1.0\n"
            f"Generator: aios_habit.offline_packager\n"
            f"Root-Is-Purelib: true\n"
            f"Tag: py3-none-any\n"
        ).encode("utf-8")
        zf.writestr(f"{dist_info_name}/WHEEL", wheel_content)
        sha_wheel = hashlib.sha256(wheel_content).hexdigest()
        record_entries.append(f"{dist_info_name}/WHEEL,sha256={sha_wheel},{len(wheel_content)}")

        # Write top_level.txt
        top_level_content = "\n".join(package_dirs.keys()).encode("utf-8") + b"\n"
        zf.writestr(f"{dist_info_name}/top_level.txt", top_level_content)
        sha_top = hashlib.sha256(top_level_content).hexdigest()
        record_entries.append(f"{dist_info_name}/top_level.txt,sha256={sha_top},{len(top_level_content)}")

        # Write RECORD
        record_entries.append(f"{dist_info_name}/RECORD,,")
        zf.writestr(f"{dist_info_name}/RECORD", "\n".join(record_entries) + "\n")


def build_all() -> None:
    VENDOR_WHEELS_DIR.mkdir(parents=True, exist_ok=True)

    # Clean old excaliflow 0.1.1 wheels
    for old_whl in [
        VENDOR_WHEELS_DIR / "excaliflow-0.1.1-py3-none-any.whl",
        VENDOR_WHEELS_LINUX_DIR / "excaliflow-0.1.1-py3-none-any.whl",
    ]:
        if old_whl.exists():
            old_whl.unlink()

    # 1. Build excaliflow wheel v0.1.3
    excaliflow_whl = VENDOR_WHEELS_DIR / "excaliflow-0.1.3-py3-none-any.whl"
    print(f"Building {excaliflow_whl.name}...")
    make_wheel(
        wheel_path=excaliflow_whl,
        dist_name="excaliflow",
        version="0.1.3",
        package_dirs={"excaliflow": EXCALIFLOW_SRC_DIR},
        summary="ExcaliFlow Studio in-process diagram and knowledge atlas package",
    )

    # Sync to vendor/wheels_linux
    if VENDOR_WHEELS_LINUX_DIR.exists():
        shutil.copy2(excaliflow_whl, VENDOR_WHEELS_LINUX_DIR / excaliflow_whl.name)

    # 2. Build nakazasen-ai-router wheel
    router_src = SITE_PACKAGES_DIR / "nakazasen_ai_router"
    router_whl = VENDOR_WHEELS_DIR / "nakazasen_ai_router-0.8.0-py3-none-any.whl"
    print(f"Building {router_whl.name}...")
    make_wheel(
        wheel_path=router_whl,
        dist_name="nakazasen_ai_router",
        version="0.8.0",
        package_dirs={"nakazasen_ai_router": router_src},
        summary="AI Model routing and provider arbitration engine",
    )

    # 3. Generate checksums.json for vendor/wheels
    for target_dir in [VENDOR_WHEELS_DIR, VENDOR_WHEELS_LINUX_DIR]:
        if not target_dir.exists():
            continue
        checksums: dict[str, dict] = {}
        for whl in sorted(target_dir.glob("*.whl")):
            data = whl.read_bytes()
            sha256 = hashlib.sha256(data).hexdigest()
            sha512 = hashlib.sha512(data).hexdigest()
            checksums[whl.name] = {
                "filename": whl.name,
                "size_bytes": len(data),
                "sha256": sha256,
                "sha512": sha512,
                "built_for": "AIOS_habbit Commit D Offline Packaging",
            }

        manifest_file = target_dir / "checksums.json"
        manifest_file.write_text(json.dumps(checksums, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Generated {manifest_file} with {len(checksums)} entries.")


if __name__ == "__main__":
    build_all()
