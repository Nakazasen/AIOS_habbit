# -*- coding: utf-8 -*-
"""Desktop packaging runner for AIOS WorkLens.

Validates the desktop build prerequisites, ensures vendored wheels and checksums
are up to date, and orchestrates offline bundle assembly.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
import sys

LOGGER = logging.getLogger("aios_habit.desktop_build")
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VENDOR_WHEELS_DIR = REPO_ROOT / "vendor" / "wheels"
SPEC_FILE = REPO_ROOT / "packaging" / "desktop" / "AIOS_WorkLens.spec"


def verify_build_prerequisites(require_model: bool = True) -> dict[str, Any]:
    """Check that all required files and vendored wheels exist and match checksums."""
    manifest_path = VENDOR_WHEELS_DIR / "checksums.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing checksum manifest: {manifest_path}")

    manifest: dict = json.loads(manifest_path.read_text(encoding="utf-8"))
    verified_wheels = []

    for filename, info in manifest.items():
        whl_path = VENDOR_WHEELS_DIR / filename
        if not whl_path.exists():
            raise FileNotFoundError(f"Missing vendored wheel: {whl_path}")

        data = whl_path.read_bytes()
        actual_sha256 = hashlib.sha256(data).hexdigest()
        expected_sha256 = info.get("sha256")
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"Checksum mismatch for {filename}: expected {expected_sha256}, got {actual_sha256}"
            )
        verified_wheels.append({
            "filename": filename,
            "size_bytes": len(data),
            "sha256": actual_sha256,
        })

    if not SPEC_FILE.exists():
        raise FileNotFoundError(f"Missing PyInstaller spec file: {SPEC_FILE}")

    # Check BGE-M3 model manifest
    from aios_habit.model_pack import DEFAULT_MANIFEST_PATH, resolve_bge_m3_model_path
    if not DEFAULT_MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Missing BGE-M3 model manifest: {DEFAULT_MANIFEST_PATH}")

    model_dir, model_status = resolve_bge_m3_model_path(auto_configure_env=False)

    if require_model and (model_dir is None or model_status.get("status") != "ready"):
        reason = model_status.get("reason", "model_pack_unavailable")
        raise RuntimeError(
            f"Cannot build BGE-enabled Desktop bundle: BGE-M3 model pack is {model_status.get('status', 'unavailable')} ({reason}). "
            f"For a lightweight build without offline BGE, specify require_model=False."
        )

    return {
        "status": "ready" if (model_status.get("status") == "ready" or not require_model) else "failed",
        "verified_wheels": verified_wheels,
        "spec_file": str(SPEC_FILE),
        "model_pack_status": model_status,
        "model_dir": str(model_dir) if model_dir else None,
        "bge_enabled": model_dir is not None and model_status.get("status") == "ready",
    }


def copy_model_pack_to_bundle(dist_dir: Path, model_source_dir: Path) -> Path:
    """Copy verified BGE-M3 model pack to desktop distribution folder."""
    import shutil
    target_dir = dist_dir / "models" / "bge-m3-5617a9f"
    target_dir.mkdir(parents=True, exist_ok=True)
    for item in model_source_dir.iterdir():
        if item.is_file():
            shutil.copy2(item, target_dir / item.name)
        elif item.is_dir():
            shutil.copytree(item, target_dir / item.name, dirs_exist_ok=True)
    return target_dir


def build_desktop_bundle(clean: bool = False, require_model: bool = True) -> Path:
    """Execute PyInstaller to build the standalone desktop application."""
    import subprocess

    prereqs = verify_build_prerequisites(require_model=require_model)

    dist_dir = REPO_ROOT / "dist"
    build_dir = REPO_ROOT / "build"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(SPEC_FILE),
        "--noconfirm",
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(build_dir),
    ]
    if clean:
        cmd.append("--clean")

    result = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"PyInstaller build failed:\n{result.stderr or result.stdout}")

    bundle_dir = dist_dir / "AIOS_WorkLens"
    exe_path = bundle_dir / ("AIOS_WorkLens.exe" if sys.platform == "win32" else "AIOS_WorkLens")
    if not exe_path.exists():
        raise FileNotFoundError(f"Built executable not found at: {exe_path}")

    # Copy verified BGE-M3 model pack to bundle companion directory
    if prereqs.get("bge_enabled") and prereqs.get("model_dir"):
        copy_model_pack_to_bundle(bundle_dir, Path(prereqs["model_dir"]))

    return exe_path


def main() -> int:
    """Run desktop build and verification."""
    import argparse
    parser = argparse.ArgumentParser(description="AIOS WorkLens Desktop Build Runner")
    parser.add_argument("--build", action="store_true", help="Build the standalone executable with PyInstaller")
    parser.add_argument("--clean", action="store_true", help="Clean cache before building")
    args = parser.parse_args()

    print("Verifying AIOS WorkLens Desktop Build prerequisites...")
    try:
        result = verify_build_prerequisites()
        print(f"Status: {result['status']}")
        print(f"Verified {len(result['verified_wheels'])} vendored wheels matching checksums.")
        print(f"Spec file: {result['spec_file']}")

        if args.build:
            print("Building standalone executable...")
            exe_path = build_desktop_bundle(clean=args.clean)
            print(f"Build completed successfully: {exe_path}")

        print("Desktop build configuration is 100% verified and offline-ready.")
        return 0
    except Exception as exc:
        print(f"Build verification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
