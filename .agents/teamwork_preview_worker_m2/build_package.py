#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build package for excaliflow-skill-v2.zip
"""

import os
import zipfile
from pathlib import Path

def create_excaliflow_zip():
    skill_dir = Path(r"C:\Users\Admin\.gemini\config\skills\excaliflow")
    zip_dest = Path(r"C:\Users\Admin\Downloads\excaliflow-skill-v2.zip")
    
    zip_dest.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"[*] Packaging {skill_dir} into {zip_dest}...")
    with zipfile.ZipFile(zip_dest, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(skill_dir):
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(skill_dir).as_posix()
                print(f"    + Adding {rel_path} ({full_path.stat().st_size:,} bytes)")
                zf.write(full_path, arcname=rel_path)
                
    print(f"[✓] Successfully generated {zip_dest} ({zip_dest.stat().st_size:,} bytes)")

if __name__ == "__main__":
    create_excaliflow_zip()
