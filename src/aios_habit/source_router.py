from dataclasses import dataclass, field
from typing import List, Dict, Any, Union
from .rag_search import RAGSearchResult
from .rag_evidence import RAGEvidenceItem

@dataclass
class QueryProfile:
    profile_id: str
    expected_source_types: List[str]

@dataclass
class RoutedEvidence:
    primary_items: List[Union[RAGSearchResult, RAGEvidenceItem]]
    supporting_items: List[Union[RAGSearchResult, RAGEvidenceItem]]
    rejected_or_demoted_items: List[Union[RAGSearchResult, RAGEvidenceItem]]
    missing_required_source_types: List[str]
    route_warnings: List[str]
    source_type_pass: str  # "PASS", "PARTIAL", "FAIL"

def classify_query_profile(question: str, target_source_type: str = "") -> QueryProfile:
    q_lower = question.lower()
    
    # Priority classification
    if target_source_type in ["png", "jpg", "screenshot", "image"]:
        if "what does" in q_lower and "show" in q_lower or "visible" in q_lower or "thấy gì" in q_lower:
            return QueryProfile("screenshot_visible_facts", ["screenshot", "image", "png", "jpg"])
        return QueryProfile("screenshot_unsupported_inference", ["screenshot", "image", "png", "jpg"])

    if "screenshot" in q_lower or "ảnh" in q_lower or "nhìn thấy" in q_lower:
        if "what does" in q_lower and "show" in q_lower or "visible" in q_lower or "thấy gì" in q_lower:
            return QueryProfile("screenshot_visible_facts", ["screenshot", "image", "png", "jpg"])
        return QueryProfile("screenshot_unsupported_inference", ["screenshot", "image", "png", "jpg"])

    if "design change" in q_lower or "eco" in q_lower or "ecn" in q_lower or "revup" in q_lower:
        return QueryProfile("design_change", ["pdf", "pptx", "document", "excel", "xlsx"])

    if "handover" in q_lower or "bàn giao" in q_lower or "next action" in q_lower:
        return QueryProfile("owner_handover", ["log", "chat", "note", "mixed", "pdf", "xlsx", "screenshot"])

    if "troubleshooting" in q_lower or "step-by-step" in q_lower or "kiểm tra gì" in q_lower or "thiếu bằng chứng" in q_lower:
        return QueryProfile("mixed_troubleshooting", ["log", "chat", "note", "mixed", "pdf", "xlsx"])

    if "automatic/manual boundary" in q_lower or "process" in q_lower or "quy trình" in q_lower or "chủ sở hữu" in q_lower:
        return QueryProfile("process_boundary", ["pdf", "pptx", "word", "document"])

    if "map" in q_lower or "mapping" in q_lower or "export" in q_lower or "import" in q_lower:
        return QueryProfile("excel_mapping", ["xlsx", "xls", "csv", "excel", "spreadsheet"])

    if "schema" in q_lower or "table" in q_lower and "field" in q_lower and "database" in q_lower:
        if "behavior" in q_lower or "logic" in q_lower:
            return QueryProfile("schema_unsupported_conclusions", ["html", "sql", "csv", "xlsx"])
        return QueryProfile("schema_tables_fields", ["html", "sql", "csv", "xlsx"])

    if "missing" in q_lower and "evidence" in q_lower:
        return QueryProfile("missing_evidence", ["log", "chat", "note", "mixed"])

    return QueryProfile("general", ["pdf", "pptx", "xlsx", "csv", "screenshot", "image", "png", "jpg", "html", "document", "spreadsheet"])

def get_base_source_type(file_type: str) -> str:
    ft = file_type.lower()
    if ft in ["png", "jpg", "jpeg", "screenshot", "image"]:
        return "screenshot"
    if ft in ["xlsx", "xls", "csv", "excel", "spreadsheet"]:
        return "spreadsheet"
    if ft in ["pdf", "pptx", "doc", "docx", "word", "document"]:
        return "document"
    if ft in ["html", "sql"]:
        return "schema"
    return "mixed"

def route_evidence_by_profile(items: List[Union[RAGSearchResult, RAGEvidenceItem]], profile: QueryProfile, target_source_type: str) -> RoutedEvidence:
    primary = []
    supporting = []
    demoted = []
    missing_required = []
    warnings = []
    
    # Normalize expected source types based on the profile
    expected_bases = [get_base_source_type(st) for st in profile.expected_expected_source_types] if hasattr(profile, 'expected_expected_source_types') else [get_base_source_type(st) for st in profile.expected_source_types]
    
    # Let's map target_source_type
    if target_source_type:
        explicit_target_base = get_base_source_type(target_source_type)
        if explicit_target_base not in expected_bases:
            expected_bases.insert(0, explicit_target_base)
            
    # Also if the profile is screenshot related but target_source_type is empty, still prefer screenshot
    if profile.profile_id.startswith("screenshot"):
        if "screenshot" not in expected_bases:
            expected_bases.insert(0, "screenshot")
    
    found_bases = set()
    for item in items:
        # For RAGSearchResult or RAGEvidenceItem, we can check file_type
        base_type = get_base_source_type(item.file_type) if hasattr(item, 'file_type') else get_base_source_type(item.source_type if hasattr(item, 'source_type') else "")
        found_bases.add(base_type)
        
        if base_type in expected_bases:
            if expected_bases.index(base_type) == 0:
                primary.append(item)
            else:
                supporting.append(item)
        else:
            if base_type == "schema" and profile.profile_id.startswith("screenshot"):
                # Very specific demotion: html/erd for screenshot questions
                demoted.append(item)
            else:
                # Still use as supporting if not explicitly demoted
                supporting.append(item)
                
    source_type_pass = "PASS"
    if expected_bases:
        primary_expected = expected_bases[0]
        if primary_expected not in found_bases:
            source_type_pass = "FAIL"
            missing_required.append(primary_expected)
            warnings.append(f"Required primary source type '{primary_expected}' not found.")
        else:
            # Maybe partial if mixed profile
            if profile.profile_id.startswith("mixed") and len(found_bases) < 2:
                source_type_pass = "PARTIAL"
                warnings.append("Mixed profile requested but only one source type found.")
                
    if not primary and supporting:
        # Fallback
        primary = supporting
        supporting = []
        source_type_pass = "PARTIAL"
        warnings.append("No optimal primary evidence found, falling back to supporting evidence.")
        
    return RoutedEvidence(
        primary_items=primary,
        supporting_items=supporting,
        rejected_or_demoted_items=demoted,
        missing_required_source_types=missing_required,
        route_warnings=warnings,
        source_type_pass=source_type_pass
    )
