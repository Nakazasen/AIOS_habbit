import json
import os
from pathlib import Path
from dataclasses import asdict
from typing import List

from .case_models import Case, EvidenceItem

LOCAL_CASES_DIR = Path.cwd() / "local_cases"
CASES_FILE = LOCAL_CASES_DIR / "cases.jsonl"
EVIDENCE_FILE = LOCAL_CASES_DIR / "evidence.jsonl"
ASSETS_DIR = LOCAL_CASES_DIR / "assets"

def init_store():
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    if not CASES_FILE.exists():
        CASES_FILE.touch()
    if not EVIDENCE_FILE.exists():
        EVIDENCE_FILE.touch()

def load_cases() -> List[Case]:
    init_store()
    cases = []
    with open(CASES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    cases.append(Case(**data))
                except Exception:
                    pass
    return cases

def load_evidence() -> List[EvidenceItem]:
    init_store()
    items = []
    with open(EVIDENCE_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    items.append(EvidenceItem(**data))
                except Exception:
                    pass
    return items

def save_case(case: Case):
    init_store()
    cases = load_cases()
    found = False
    for i, c in enumerate(cases):
        if c.case_id == case.case_id:
            cases[i] = case
            found = True
            break
    if not found:
        cases.append(case)
        
    with open(CASES_FILE, 'w', encoding='utf-8') as f:
        for c in cases:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + '\n')

def save_evidence(evidence: EvidenceItem):
    init_store()
    items = load_evidence()
    found = False
    for i, e in enumerate(items):
        if e.evidence_id == evidence.evidence_id:
            items[i] = evidence
            found = True
            break
    if not found:
        items.append(evidence)
        
    with open(EVIDENCE_FILE, 'w', encoding='utf-8') as f:
        for e in items:
            f.write(json.dumps(asdict(e), ensure_ascii=False) + '\n')

def get_case_assets_dir(case_id: str) -> Path:
    init_store()
    p = ASSETS_DIR / case_id
    p.mkdir(parents=True, exist_ok=True)
    return p
