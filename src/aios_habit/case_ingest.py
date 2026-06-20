import os
import pandas as pd
from pathlib import Path
from .case_models import EvidenceItem
from .case_store import get_case_assets_dir

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
    assets_dir = get_case_assets_dir(case_id)
    dest_path = assets_dir / uploaded_file.name
    with open(dest_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return str(dest_path)
