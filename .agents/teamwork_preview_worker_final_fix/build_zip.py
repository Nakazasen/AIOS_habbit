#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build script to package C:\\Users\\Admin\\.gemini\\config\\skills\\excaliflow
into C:\\Users\\Admin\\Downloads\\excaliflow-skill-v2.zip
"""

import os
import sys
import zipfile
from pathlib import Path

SKILL_DIR = Path(r"C:\Users\Admin\.gemini\config\skills\excaliflow").resolve()
ZIP_DEST = Path(r"C:\Users\Admin\Downloads\excaliflow-skill-v2.zip").resolve()

def build_zip():
    print(f"[*] Packaging {SKILL_DIR} -> {ZIP_DEST}...")
    ZIP_DEST.parent.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(ZIP_DEST, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(SKILL_DIR):
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(SKILL_DIR).as_posix()
                print(f"  + {rel_path} ({full_path.stat().st_size:,} bytes)")
                zf.write(full_path, arcname=rel_path)
                
    print(f"[✓] Created {ZIP_DEST} ({ZIP_DEST.stat().st_size:,} bytes)")
    
    # Verify
    with zipfile.ZipFile(ZIP_DEST, "r") as zf:
        assert zf.testzip() is None, "Corrupted archive!"
        names = zf.namelist()
        print(f"[*] Entries: {names}")
        assert "SKILL.md" in names
        assert "scripts/generate_diagram.py" in names
        
        script = zf.read("scripts/generate_diagram.py").decode("utf-8")
        assert "raw_edges = [e for e in raw_edges if isinstance(e, dict)]" in script
        assert "MERMAID_RESERVED_KEYWORDS" in script
        print("[✓] All verification checks passed!")

if __name__ == "__main__":
    build_zip()
