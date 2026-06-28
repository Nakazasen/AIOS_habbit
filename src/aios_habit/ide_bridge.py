import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from aios_habit.rag_evidence import RAGEvidencePack, format_evidence_pack_for_prompt

@dataclass
class IDEBridgeConfig:
    allow_cloud_safe_export: bool = True
    allow_redacted_export: bool = False
    max_prompt_chars: int = 15000
    require_model_tool_name: bool = True
    allowed_model_hints: Optional[List[str]] = None

@dataclass
class IDEPromptPack:
    prompt_pack_id: str
    source_evidence_pack_id: str
    query: str
    target_model_hint: str
    prompt_text: str
    privacy_mode: str
    allowed_external: bool
    export_policy: str
    evidence_refs: List[str] = field(default_factory=list)
    citation_ids: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, str] = field(default_factory=dict)

@dataclass
class IDEPasteBackAnswer:
    answer_id: str
    prompt_pack_id: str
    source_evidence_pack_id: str
    model_tool_name: str
    answer_text: str
    privacy_mode: str
    external_ai_used: bool
    route_summary: str
    confidence_label: str
    evidence_refs: List[str] = field(default_factory=list)
    citation_ids: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, str] = field(default_factory=dict)

def stable_prompt_pack_id(evidence_pack: RAGEvidencePack, target_model_hint: str) -> str:
    raw = f"{evidence_pack.pack_id}:{target_model_hint}".encode("utf-8")
    return f"PROMPT-{hashlib.md5(raw).hexdigest()[:12].upper()}"

def stable_answer_id(prompt_pack_id: str, model_tool_name: str, answer_text: str) -> str:
    raw = f"{prompt_pack_id}:{model_tool_name}:{hashlib.md5(answer_text.encode('utf-8')).hexdigest()}".encode("utf-8")
    return f"ANS-{hashlib.md5(raw).hexdigest()[:12].upper()}"

def format_ide_prompt_pack(prompt_pack: IDEPromptPack) -> str:
    return prompt_pack.prompt_text

def build_ide_prompt_pack(evidence_pack: RAGEvidencePack, target_model_hint: str, config: Optional[IDEBridgeConfig] = None) -> IDEPromptPack:
    if config is None:
        config = IDEBridgeConfig()
        
    prompt_pack_id = stable_prompt_pack_id(evidence_pack, target_model_hint)
    
    warnings = []
    
    # Export Policy
    export_policy = "blocked_local_only"
    allowed_external = False
    
    if evidence_pack.privacy_mode == "local_only":
        export_policy = "blocked_local_only"
        allowed_external = False
    elif evidence_pack.privacy_mode == "redacted":
        if config.allow_redacted_export:
            export_policy = "allowed_redacted"
            allowed_external = True
        else:
            export_policy = "blocked_by_config"
            allowed_external = False
    elif evidence_pack.privacy_mode == "cloud_safe":
        if config.allow_cloud_safe_export:
            export_policy = "allowed_cloud_safe"
            allowed_external = True
        else:
            export_policy = "blocked_by_config"
            allowed_external = False

    # Extract refs
    evidence_refs = [item.evidence_id for item in evidence_pack.items]
    citation_ids = [item.citation_id for item in evidence_pack.items]
    
    # Generate Prompt
    lines = []
    lines.append(f"Goal: {evidence_pack.query}")
    lines.append("")
    lines.append(format_evidence_pack_for_prompt(evidence_pack))
    lines.append("")
    if export_policy == "blocked_local_only":
        lines.append("DO NOT EXPORT EXTERNALLY. This prompt contains local_only data.")
    
    lines.append("Instructions:")
    lines.append("1. Answer the goal using ONLY the provided Evidence Pack.")
    lines.append("2. Cite your sources using the Citation IDs (e.g., [1]).")
    lines.append("3. If the evidence is insufficient to answer the goal fully, state clearly what is missing and abstain from guessing.")
    
    prompt_text = "\n".join(lines)
    
    if len(prompt_text) > config.max_prompt_chars:
        warnings.append(f"Prompt truncated from {len(prompt_text)} to {config.max_prompt_chars} chars; review privacy notice before any external use.")
        notice = "PRIVACY/TRUNCATION NOTICE: Prompt was truncated; do not export unless policy allows it.\n"
        if config.max_prompt_chars <= len(notice):
            prompt_text = notice[:config.max_prompt_chars]
        else:
            prompt_text = notice + prompt_text[:config.max_prompt_chars - len(notice)]
        
    return IDEPromptPack(
        prompt_pack_id=prompt_pack_id,
        source_evidence_pack_id=evidence_pack.pack_id,
        query=evidence_pack.query,
        target_model_hint=target_model_hint,
        prompt_text=prompt_text,
        privacy_mode=evidence_pack.privacy_mode,
        allowed_external=allowed_external,
        export_policy=export_policy,
        evidence_refs=evidence_refs,
        citation_ids=citation_ids,
        warnings=warnings
    )

def validate_prompt_export(prompt_pack: IDEPromptPack) -> bool:
    if prompt_pack.export_policy == "blocked_local_only" or not prompt_pack.allowed_external:
        return False
    return True

def record_paste_back_answer(prompt_pack: IDEPromptPack, model_tool_name: str, answer_text: str, route_summary: str = "", confidence_label: str = "", config: Optional[IDEBridgeConfig] = None) -> IDEPasteBackAnswer:
    if config is None:
        config = IDEBridgeConfig()
        
    model_tool_name = model_tool_name.strip()
    if not model_tool_name:
        if config.require_model_tool_name:
            raise ValueError("model_tool_name is required but was empty.")
        model_tool_name = "unknown"
        
    warnings = []
    
    answer_id = stable_answer_id(prompt_pack.prompt_pack_id, model_tool_name, answer_text)
    
    # Trust the prompt pack's privacy resolution for external usage
    external_ai_used = prompt_pack.allowed_external

    return IDEPasteBackAnswer(
        answer_id=answer_id,
        prompt_pack_id=prompt_pack.prompt_pack_id,
        source_evidence_pack_id=prompt_pack.source_evidence_pack_id,
        model_tool_name=model_tool_name,
        answer_text=answer_text,
        privacy_mode=prompt_pack.privacy_mode,
        external_ai_used=external_ai_used,
        route_summary=route_summary,
        confidence_label=confidence_label or "unknown",
        evidence_refs=prompt_pack.evidence_refs,
        citation_ids=prompt_pack.citation_ids,
        warnings=warnings
    )

def ide_prompt_pack_to_dict(prompt_pack: IDEPromptPack) -> Dict[str, Any]:
    return asdict(prompt_pack)

def ide_answer_to_dict(answer: IDEPasteBackAnswer) -> Dict[str, Any]:
    return asdict(answer)
