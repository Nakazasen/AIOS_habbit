import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
import json

from aios_habit.rag_search import RAGSearchResult

@dataclass
class EvidencePackConfig:
    max_items: int = 15
    min_items_for_sufficient: int = 1
    min_top_score: float = 0.0
    min_coverage_score: float = 0.0
    max_snippet_chars: int = 1500
    allow_external_for_cloud_safe: bool = True

@dataclass
class RAGEvidenceItem:
    evidence_id: str
    chunk_id: str
    document_id: str
    citation_id: str
    citation_label: str
    source_title: str
    relative_path: str
    file_type: str
    privacy_mode: str
    text: str
    snippet: str
    score: float
    rank: int
    page_numbers: List[int] = field(default_factory=list)
    sheet_names: List[str] = field(default_factory=list)
    slide_numbers: List[int] = field(default_factory=list)
    element_types: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    score_details: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

@dataclass
class RAGEvidencePack:
    pack_id: str
    query: str
    items: List[RAGEvidenceItem] = field(default_factory=list)
    privacy_mode: str = "local_only"
    allowed_external: bool = False
    source_count: int = 0
    document_count: int = 0
    top_score: float = 0.0
    coverage_score: float = 0.0
    confidence_label: str = "insufficient"
    insufficient_evidence: bool = True
    missing_evidence_warnings: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    route_hint: str = "local_only"
    metadata: Dict[str, str] = field(default_factory=dict)

def stable_evidence_id(pack_id: str, chunk_id: str, rank: int) -> str:
    raw = f"{pack_id}:{chunk_id}:{rank}".encode("utf-8")
    return f"EVD-{hashlib.md5(raw).hexdigest()[:8].upper()}"

def stable_pack_id(query: str, search_results: List[RAGSearchResult]) -> str:
    # Ensure same query and ordered results give same pack_id
    res_str = "".join([f"{r.chunk_id}:{r.score:.4f}" for r in search_results])
    raw = f"{query}:{res_str}".encode("utf-8")
    return f"PACK-{hashlib.sha256(raw).hexdigest()[:12].upper()}"

def make_snippet(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."

def normalize_pack_privacy(items: List[RAGEvidenceItem]) -> str:
    if not items:
        return "local_only" # Safest default when empty
    for item in items:
        if item.privacy_mode == "local_only":
            return "local_only"
    return "cloud_safe"

def is_external_allowed(privacy_mode: str, config: EvidencePackConfig) -> bool:
    if privacy_mode == "local_only":
        return False
    if privacy_mode == "cloud_safe" and config.allow_external_for_cloud_safe:
        return True
    return False

def build_evidence_pack(query: str, search_results: List[RAGSearchResult], config: Optional[EvidencePackConfig] = None) -> RAGEvidencePack:
    if config is None:
        config = EvidencePackConfig()
        
    pack_id = stable_pack_id(query, search_results)
    
    items = []
    doc_ids = set()
    source_titles = set()
    
    for rank, result in enumerate(search_results[:config.max_items]):
        # Citation ID can just be E+rank to make it easy to cite in prompt
        citation_id = f"[{rank + 1}]"
        
        evidence_id = stable_evidence_id(pack_id, result.chunk_id, rank + 1)
        
        snippet = make_snippet(result.text, config.max_snippet_chars)
        
        item = RAGEvidenceItem(
            evidence_id=evidence_id,
            chunk_id=result.chunk_id,
            document_id=result.document_id,
            citation_id=citation_id,
            citation_label=result.citation_label,
            source_title=result.source_title,
            relative_path=result.relative_path,
            file_type=result.file_type,
            privacy_mode=result.privacy_mode,
            text=result.text,
            snippet=snippet,
            score=result.score,
            rank=rank + 1,
            page_numbers=result.page_numbers,
            sheet_names=result.sheet_names,
            slide_numbers=result.slide_numbers,
            element_types=result.element_types,
            metadata={k: str(v) for k, v in result.metadata.items() if isinstance(v, (str, int, float, bool))},
            score_details={"base_score": result.score},
            warnings=[]
        )
        items.append(item)
        doc_ids.add(result.document_id)
        if result.source_title:
            source_titles.add(result.source_title)
            
    privacy_mode = normalize_pack_privacy(items)
    allowed_external = is_external_allowed(privacy_mode, config)
    
    source_count = len(source_titles)
    document_count = len(doc_ids)
    
    top_score = items[0].score if items else 0.0
    
    # Coverage score heuristic: more unique docs/sources = better coverage
    # This is a simple placeholder for now.
    coverage_score = min(1.0, (document_count * 0.5) + (top_score * 0.1) if items else 0.0)
    
    insufficient_evidence = False
    missing_evidence_warnings = []
    
    if not items:
        insufficient_evidence = True
        missing_evidence_warnings.append("No results found.")
    elif len(items) < config.min_items_for_sufficient:
        insufficient_evidence = True
        missing_evidence_warnings.append(f"Found only {len(items)} items, need {config.min_items_for_sufficient}.")
    elif top_score < config.min_top_score:
        insufficient_evidence = True
        missing_evidence_warnings.append(f"Top score {top_score:.2f} is below minimum {config.min_top_score:.2f}.")
        
    confidence_label = "insufficient"
    if not insufficient_evidence:
        if top_score > 10.0 and document_count > 1:
            confidence_label = "high"
        elif top_score > 2.0:
            confidence_label = "medium"
        else:
            confidence_label = "low"
            
    if privacy_mode == "local_only":
        route_hint = "local_only"
    elif allowed_external:
        route_hint = "cloud_safe_allowed"
    else:
        route_hint = "redacted_export_required"
        
    return RAGEvidencePack(
        pack_id=pack_id,
        query=query,
        items=items,
        privacy_mode=privacy_mode,
        allowed_external=allowed_external,
        source_count=source_count,
        document_count=document_count,
        top_score=top_score,
        coverage_score=coverage_score,
        confidence_label=confidence_label,
        insufficient_evidence=insufficient_evidence,
        missing_evidence_warnings=missing_evidence_warnings,
        route_hint=route_hint
    )

def evidence_pack_to_dict(pack: RAGEvidencePack) -> Dict[str, Any]:
    return asdict(pack)

def format_evidence_pack_for_prompt(pack: RAGEvidencePack) -> str:
    lines = []
    lines.append(f"### Evidence Pack (Query: '{pack.query}')")
    
    if pack.insufficient_evidence:
        lines.append("WARNING: Insufficient evidence to fully answer.")
        for w in pack.missing_evidence_warnings:
            lines.append(f"- {w}")
            
    if pack.privacy_mode == "local_only":
        lines.append("PRIVACY NOTICE: Contains local_only company/mật data. External export NOT allowed.")
    else:
        lines.append("PRIVACY NOTICE: Content is cloud_safe.")
        
    lines.append(f"Confidence: {pack.confidence_label.upper()} | Sources: {pack.source_count} | Documents: {pack.document_count}")
    lines.append("---")
    
    for item in pack.items:
        meta_parts = []
        if item.page_numbers:
            meta_parts.append(f"Page: {','.join(map(str, item.page_numbers))}")
        if item.sheet_names:
            meta_parts.append(f"Sheet: {','.join(item.sheet_names)}")
        if item.slide_numbers:
            meta_parts.append(f"Slide: {','.join(map(str, item.slide_numbers))}")
            
        meta_str = f" ({'; '.join(meta_parts)})" if meta_parts else ""
        
        lines.append(f"Citation ID: {item.citation_id}")
        lines.append(f"Source: {item.citation_label}{meta_str}")
        lines.append(f"Snippet:\n{item.snippet}\n---")
        
    return "\n".join(lines)
