import os
import re
import time
import pandas as pd
from pathlib import Path
from .case_models import EvidenceItem
from .case_store import get_case_assets_dir

def safe_asset_filename(original_name: str) -> str:
    import uuid
    uniq = uuid.uuid4().hex[:6]
    timestamp = f"{int(time.time() * 1000)}"
    
    if not original_name:
        return f"asset_{timestamp}_{uniq}"
    
    # Replace path separators to block traversal at the string level
    name = original_name.replace("/", "_").replace("\\", "_")
    
    # Split stem and suffix
    p = Path(name)
    stem = p.stem
    ext = p.suffix
    
    # Clean stem: keep only a-zA-Z0-9_-
    stem_clean = re.sub(r'[^A-Za-z0-9_-]', '_', stem)
    if not stem_clean:
        stem_clean = "asset"
        
    # Clean extension: keep only a-zA-Z0-9
    ext_clean = re.sub(r'[^A-Za-z0-9]', '', ext)
    if ext_clean:
        ext_clean = "." + ext_clean
        
    return f"{timestamp}_{uniq}_{stem_clean}{ext_clean}"

def ingest_excel(file_path: str, case_id: str, evidence_id: str, original_name: str) -> EvidenceItem:
    try:
        xls = pd.ExcelFile(file_path)
        sheets = xls.sheet_names
        summary = f"Excel Workbook: {original_name}\nSheets: {', '.join(sheets)}\n"
        
        for sheet in sheets:
            df = pd.read_excel(xls, sheet_name=sheet, nrows=5)
            summary += f"\nSheet '{sheet}' Preview (cols={len(df.columns)}):\n"
            summary += df.to_string(index=False) + "\n"
            
        return EvidenceItem(
            evidence_id=evidence_id,
            case_id=case_id,
            source_type="excel",
            source_path=file_path,
            title=f"Excel Data: {original_name}",
            structured_summary=summary,
            extracted_text=summary
        )
    except Exception as e:
        return EvidenceItem(
            evidence_id=evidence_id,
            case_id=case_id,
            source_type="excel",
            source_path=file_path,
            title=f"Excel Data: {original_name}",
            extracted_text=f"Error reading Excel: {e}",
            structured_summary="Failed to parse."
        )

def ingest_csv(file_path: str, case_id: str, evidence_id: str, original_name: str) -> EvidenceItem:
    try:
        df = pd.read_csv(file_path, nrows=5)
        summary = f"CSV File: {original_name}\nCols: {len(df.columns)}\nPreview:\n" + df.to_string(index=False)
        return EvidenceItem(
            evidence_id=evidence_id,
            case_id=case_id,
            source_type="csv",
            source_path=file_path,
            title=f"CSV Data: {original_name}",
            structured_summary=summary,
            extracted_text=summary
        )
    except Exception as e:
        return EvidenceItem(
            evidence_id=evidence_id,
            case_id=case_id,
            source_type="csv",
            source_path=file_path,
            title=f"CSV Data: {original_name}",
            extracted_text=f"Error reading CSV: {e}",
            structured_summary="Failed to parse."
        )

def save_uploaded_file(uploaded_file, case_id: str) -> str:
    assets_dir_resolved = get_case_assets_dir(case_id).resolve()
    sanitized_name = safe_asset_filename(uploaded_file.name)
    dest_path_resolved = (assets_dir_resolved / sanitized_name).resolve()
    
    # Path containment assertion (directory traversal defense)
    if not dest_path_resolved.is_relative_to(assets_dir_resolved):
        raise ValueError("Invalid file upload path: directory traversal detected.")
        
    with open(dest_path_resolved, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return str(dest_path_resolved)
