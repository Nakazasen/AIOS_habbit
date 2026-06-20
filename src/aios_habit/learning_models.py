from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import json
from typing import List, Optional
from aios_habit.case_store import LOCAL_CASES_DIR, init_store

LEARNING_CARDS_FILE = LOCAL_CASES_DIR / "learning_cards.jsonl"

@dataclass
class SeniorLearningCard:
    learning_id: str
    case_id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence: str = "draft"  # draft, reviewed, confirmed
    symptoms: str = ""
    related_systems: str = ""
    related_artifacts: str = ""
    initial_hypotheses: str = ""
    rejected_hypotheses: str = ""
    true_cause: str = ""
    causal_chain: str = ""
    verification_evidence: str = ""
    counter_evidence: str = ""
    actions_taken: str = ""
    result_outcome: str = ""
    reusable_lesson: str = ""
    pattern_to_recognize: str = ""
    applies_when: str = ""
    does_not_apply_when: str = ""
    check_first_next_time: str = ""
    retrieval_keywords: str = ""
    useful_reply_vi: str = ""
    useful_reply_ja: str = ""
    knowledge_update_note: str = ""

def load_learning_cards() -> List[SeniorLearningCard]:
    init_store()
    if not LEARNING_CARDS_FILE.exists():
        LEARNING_CARDS_FILE.touch()
    
    cards = []
    with open(LEARNING_CARDS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    cards.append(SeniorLearningCard(**data))
                except Exception:
                    pass
    return cards

def load_learning_cards_for_case(case_id: str) -> List[SeniorLearningCard]:
    cards = load_learning_cards()
    return [c for c in cards if c.case_id == case_id]

def save_learning_card(card: SeniorLearningCard):
    init_store()
    if not LEARNING_CARDS_FILE.exists():
        LEARNING_CARDS_FILE.touch()
        
    cards = load_learning_cards()
    found = False
    for i, c in enumerate(cards):
        if c.learning_id == card.learning_id:
            cards[i] = card
            found = True
            break
    if not found:
        # Also prevent multiple active cards for the same case just in case
        for i, c in enumerate(cards):
            if c.case_id == card.case_id:
                cards[i] = card
                found = True
                break
    if not found:
        cards.append(card)
        
    with open(LEARNING_CARDS_FILE, "w", encoding="utf-8") as f:
        for c in cards:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")

def init_learning_card_for_case(case_id: str) -> SeniorLearningCard:
    import uuid
    cards = load_learning_cards_for_case(case_id)
    if cards:
        return cards[0]
        
    card = SeniorLearningCard(
        learning_id=f"LRN-{str(uuid.uuid4())[:8].upper()}",
        case_id=case_id,
        confidence="draft"
    )
    save_learning_card(card)
    return card
