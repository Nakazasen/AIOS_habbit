from dataclasses import dataclass, field
from typing import List, Dict, Any, Union
from .rag_core_profiles import classify_generic_query_profile, expected_source_types_for, normalize_profile_id
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
    profile_id = classify_generic_query_profile(question, target_source_type)
    return QueryProfile(profile_id, expected_source_types_for(profile_id))

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
    normalized_profile = normalize_profile_id(profile.profile_id)

    if normalized_profile.startswith("image_"):
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
            if base_type == "schema" and normalized_profile.startswith("image_"):
                # Very specific demotion: html/erd for image-visible questions.
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
            if normalized_profile in {"troubleshooting_general", "missing_evidence_general", "handover_general"} and len(found_bases) < 2:
                source_type_pass = "PARTIAL"
                warnings.append("Multi-evidence profile requested but only one source type found.")
                
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
