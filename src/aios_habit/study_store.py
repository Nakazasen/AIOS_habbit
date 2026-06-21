import json
import inspect
import os
import uuid
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional

LOCAL_CASES_DIR = Path.cwd() / "local_cases"
STUDY_CARDS_FILE = LOCAL_CASES_DIR / "study_cards.jsonl"

@dataclass
class StudyCard:
    card_id: str
    notebook_id: str
    workspace_id: str
    front: str
    back: str
    source_ref: str
    tags: List[str]
    privacy_level: str = "local_only"
    status: str = "draft"  # draft, reviewed, confirmed
    created_at: str = ""
    updated_at: str = ""

def load_study_cards(notebook_id: Optional[str] = None) -> List[StudyCard]:
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)
    if not STUDY_CARDS_FILE.exists():
        return []
    
    card_fields = {p.name for p in inspect.signature(StudyCard).parameters.values()}
    cards = []
    
    with open(STUDY_CARDS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    filtered_data = {k: v for k, v in data.items() if k in card_fields}
                    if "privacy_level" not in filtered_data:
                        filtered_data["privacy_level"] = "local_only"
                    if "status" not in filtered_data:
                        filtered_data["status"] = "draft"
                    card = StudyCard(**filtered_data)
                    if notebook_id is None or card.notebook_id == notebook_id:
                        cards.append(card)
                except Exception:
                    pass
    return cards

def save_study_card(card: StudyCard) -> StudyCard:
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)
    cards = load_study_cards()
    
    now_str = datetime.now().isoformat()
    if not card.created_at:
        card.created_at = now_str
    card.updated_at = now_str
    
    found = False
    for i, c in enumerate(cards):
        if c.card_id == card.card_id:
            cards[i] = card
            found = True
            break
    if not found:
        cards.append(card)
        
    with open(STUDY_CARDS_FILE, 'w', encoding='utf-8') as f:
        for c in cards:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + '\n')
    return card

def save_study_cards(new_cards: List[StudyCard]) -> List[StudyCard]:
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)
    cards = load_study_cards()
    
    now_str = datetime.now().isoformat()
    for card in new_cards:
        if not card.created_at:
            card.created_at = now_str
        card.updated_at = now_str
        
        found = False
        for i, c in enumerate(cards):
            if c.card_id == card.card_id:
                cards[i] = card
                found = True
                break
        if not found:
            cards.append(card)
            
    with open(STUDY_CARDS_FILE, 'w', encoding='utf-8') as f:
        for c in cards:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + '\n')
    return new_cards

def delete_study_card(card_id: str) -> bool:
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)
    cards = load_study_cards()
    orig_len = len(cards)
    cards = [c for c in cards if c.card_id != card_id]
    if len(cards) == orig_len:
        return False
    with open(STUDY_CARDS_FILE, 'w', encoding='utf-8') as f:
        for c in cards:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + '\n')
    return True

def create_cards_from_chunks(notebook_id: str, workspace_id: str, limit: int = 10) -> List[StudyCard]:
    from aios_habit.notebook_index import load_chunks
    chunks = load_chunks(notebook_id)[:limit]
    cards = []
    existing_cards = load_study_cards(notebook_id)
    existing_fronts = {c.front for c in existing_cards}
    
    for chunk in chunks:
        top_k = ", ".join(chunk.keywords[:5])
        front = f"Nguồn này nói gì về: {top_k or chunk.source_title}?"
        if front in existing_fronts:
            continue
        back = chunk.text
        if len(back) > 500:
            back = back[:497] + "..."
        card = StudyCard(
            card_id=f"CARD-{str(uuid.uuid4())[:8].upper()}",
            notebook_id=notebook_id,
            workspace_id=workspace_id,
            front=front,
            back=back,
            source_ref=f"{chunk.source_title} / {chunk.source_id}",
            tags=chunk.keywords[:5],
            privacy_level="local_only",
            status="draft"
        )
        cards.append(card)
        
    if cards:
        save_study_cards(cards)
    return cards

def create_cards_from_study_pack_import(import_record, workspace_id: str) -> List[StudyCard]:
    if not import_record or import_record.import_type != "study_pack_json":
        return []
    
    parsed_json = import_record.parsed_json or {}
    flashcards = parsed_json.get("flashcards", [])
    cards = []
    existing_cards = load_study_cards(import_record.notebook_id)
    existing_fronts = {c.front for c in existing_cards}
    
    for f in flashcards:
        front = f.get("front", "").strip()
        back = f.get("back", "").strip()
        if not front or not back:
            continue
        if front in existing_fronts:
            continue
        source_ref = f.get("source_ref", "").strip() or import_record.title
        tags = ["notebooklm_import"]
        card = StudyCard(
            card_id=f"CARD-{str(uuid.uuid4())[:8].upper()}",
            notebook_id=import_record.notebook_id,
            workspace_id=workspace_id,
            front=front,
            back=back,
            source_ref=source_ref,
            tags=tags,
            privacy_level="local_only",
            status="draft"
        )
        cards.append(card)
        
    if cards:
        save_study_cards(cards)
    return cards
