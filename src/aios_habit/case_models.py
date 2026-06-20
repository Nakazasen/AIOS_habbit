from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

@dataclass
class EvidenceItem:
    evidence_id: str
    case_id: str
    source_type: str  # excel, csv, screenshot, image, chat_paste, log_paste, text_file, document, note
    source_path: str
    title: str
    extracted_text: str = ""
    structured_summary: str = ""
    confidence: str = "low"
    privacy_level: str = "local_only"  # local_only, redacted_export, cloud_allowed
    review_status: str = "raw"  # raw, parsed, reviewed, verified
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class Case:
    case_id: str
    title: str
    status: str = "open"  # open, investigating, waiting, resolved, archived
    priority: str = "normal"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    current_situation: str = ""
    sources: List[str] = field(default_factory=list)
    evidence_items: List[str] = field(default_factory=list) # List of evidence_ids
    timeline_events: List[Dict[str, str]] = field(default_factory=list)
    hypotheses: List[str] = field(default_factory=list)
    next_actions: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    outcome: str = ""
    lessons_learned: str = ""
    privacy_level: str = "local_only"
    workspace_id: str = "default"
    linked_notebook_ids: List[str] = field(default_factory=list)
