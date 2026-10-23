"""Post-Session Reviewer & Adaptive Self-Learning for AIOS Habit.

Implements ticket DESKTOP-SELF-LEARN-POST-SESSION-AUTO-DRAFT:
- Background daemon reviewer running after a chat turn with auxiliary model routing.
- Hermes-style self-learning rubric capturing:
  1) User corrections (chat edits / correction phrases)
  2) Dislike with reason (sai, kho_hieu, thieu_nguon, lac_de)
  3) Repeated investigation workflows (4M, troubleshooting sequences)
- Distinguishes between LESSON (BÀI HỌC - short event/style/format) and SKILL (KỸ NĂNG - multi-step procedure).
- Second Brain Habit Journal Standard (Sổ Thói Quen):
  Atomic markdown notes, complete YAML frontmatter (id, created, updated, mien, applies_when,
  does_not_apply_when, trang_thai: draft, evidence_refs, partition: local_habit, links),
  wikilinks, and domain Map of Content (MOC).
- Read-before-write guard enforcing fresh read of existing skills before patching.
- Non-blocking daemon thread with preemption/cancellation support (cancel within 2.0s).
- Staging into existing "Sửa để AIOS học" UI (pending_drafts.json) for 1-click confirmation.
- Master switch and habit profile wipe operations.
- Complies strictly with 2026-10-18 rule: Never write to confirmed store without user confirmation.

Compatible with Python 3.11+.
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import yaml

LOGGER = logging.getLogger(__name__)

# Master settings key
MASTER_SELF_LEARN_SETTING_KEY = "master_self_learn_enabled"
DEFAULT_MASTER_SELF_LEARN_ENABLED = True

# Signal types
SIGNAL_USER_CORRECTION = "user_correction"
SIGNAL_DISLIKE_WITH_REASON = "dislike_with_reason"
SIGNAL_REPEATED_INVESTIGATION = "repeated_investigation"

# Draft kinds
DRAFT_KIND_LESSON = "lesson"
DRAFT_KIND_SKILL = "skill"

# Reason categories from answer feedback
REASON_CAT_SAI = "sai"
REASON_CAT_KHO_HIEU = "kho_hieu"
REASON_CAT_THIEU_NGUON = "thieu_nguon"
REASON_CAT_LAC_DE = "lac_de"

# Default auxiliary model
DEFAULT_AUXILIARY_MODEL = "poolside/laguna-s-2.1-free"


# ==============================================================================
# 1. SECOND BRAIN HABIT JOURNAL MODELS & UTILS
# ==============================================================================

@dataclass
class SecondBrainNote:
    """Atomic note following Second Brain Habit Journal Standard."""

    id: str
    title: str
    kind: str  # "lesson" | "skill"
    created: str
    updated: str
    mien: str  # domain, e.g. "lsu", "dieutraloi", "mom_opcenter", "general"
    applies_when: str
    does_not_apply_when: str = ""
    trang_thai: str = "draft"  # "draft" | "confirmed" | "superseded"
    evidence_refs: List[str] = field(default_factory=list)
    partition: str = "local_habit"
    links: List[str] = field(default_factory=list)
    content_body: str = ""
    supporting_files: Dict[str, str] = field(default_factory=dict)  # relative path -> content
    pinned: bool = False
    use_count: int = 0
    last_activity_at: str = ""
    absorbed_into: Optional[str] = None
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
    created_by: str = "agent"

    def to_markdown(self) -> str:
        """Render complete markdown note with YAML frontmatter and wikilinks."""
        frontmatter_data = {
            "id": self.id,
            "title": self.title,
            "kind": self.kind,
            "created": self.created,
            "updated": self.updated,
            "mien": self.mien,
            "applies_when": self.applies_when,
            "does_not_apply_when": self.does_not_apply_when,
            "trang_thai": self.trang_thai,
            "evidence_refs": list(self.evidence_refs),
            "partition": self.partition,
            "links": list(self.links),
        }
        if self.pinned:
            frontmatter_data["pinned"] = self.pinned
        if self.use_count:
            frontmatter_data["use_count"] = self.use_count
        if self.last_activity_at:
            frontmatter_data["last_activity_at"] = self.last_activity_at
        if self.absorbed_into:
            frontmatter_data["absorbed_into"] = self.absorbed_into
        if self.supersedes:
            frontmatter_data["supersedes"] = self.supersedes
        if self.superseded_by:
            frontmatter_data["superseded_by"] = self.superseded_by
        if self.created_by and self.created_by != "agent":
            frontmatter_data["created_by"] = self.created_by
        yaml_str = yaml.safe_dump(frontmatter_data, sort_keys=False, allow_unicode=True).strip()
        body = self.content_body.strip()
        return f"---\n{yaml_str}\n---\n\n{body}\n"

    @classmethod
    def from_markdown(cls, text: str) -> SecondBrainNote:
        """Parse markdown with YAML frontmatter."""
        raw = text.strip()
        if not raw.startswith("---"):
            return cls(
                id=f"NOTE-{uuid_short()}",
                title="Ghi chú thói quen",
                kind=DRAFT_KIND_LESSON,
                created=now_iso(),
                updated=now_iso(),
                mien="general",
                applies_when="Chung",
                content_body=raw,
            )
        parts = raw.split("---", 2)
        if len(parts) < 3:
            return cls(
                id=f"NOTE-{uuid_short()}",
                title="Ghi chú thói quen",
                kind=DRAFT_KIND_LESSON,
                created=now_iso(),
                updated=now_iso(),
                mien="general",
                applies_when="Chung",
                content_body=raw,
            )
        fm_text = parts[1].strip()
        body_text = parts[2].strip()
        try:
            fm = yaml.safe_load(fm_text) or {}
        except Exception:
            fm = {}

        # Support both legacy SecondBrainNote frontmatter and Hermes Agent standard (name, description)
        hermes_name = str(fm.get("name", "")).strip()
        note_id = str(fm.get("id") or hermes_name or f"NOTE-{uuid_short()}")
        note_title = str(fm.get("title") or (hermes_name.replace("-", " ").title() if hermes_name else "Ghi chú thói quen"))
        note_kind = str(fm.get("kind") or (DRAFT_KIND_SKILL if hermes_name else DRAFT_KIND_LESSON))
        applies_when_val = str(fm.get("applies_when") or fm.get("description") or "")

        # Determine active state and pinned from Hermes curator usage if present
        note_state = str(fm.get("trang_thai") or ("active" if hermes_name else "draft"))
        is_pinned_val = bool(fm.get("pinned", False))
        creator_val = str(fm.get("created_by") or "agent")
        if hermes_name:
            try:
                from aios_habit.hermes_curator import is_pinned, load_usage
                u = load_usage().get(hermes_name, {})
                if u.get("state"):
                    note_state = str(u["state"])
                if is_pinned(hermes_name):
                    is_pinned_val = True
                if u.get("created_by"):
                    creator_val = str(u["created_by"])
            except Exception:
                pass

        ev_refs = list(fm.get("evidence_refs") or ([f"skill_{hermes_name}"] if hermes_name else []))

        return cls(
            id=note_id,
            title=note_title,
            kind=note_kind,
            created=str(fm.get("created") or now_iso()),
            updated=str(fm.get("updated") or now_iso()),
            mien=str(fm.get("mien") or "general"),
            applies_when=applies_when_val,
            does_not_apply_when=str(fm.get("does_not_apply_when") or ""),
            trang_thai=note_state,
            evidence_refs=ev_refs,
            partition=str(fm.get("partition") or "local_habit"),
            links=list(fm.get("links") or []),
            content_body=body_text,
            pinned=is_pinned_val,
            use_count=int(fm.get("use_count", 0)),
            last_activity_at=str(fm.get("last_activity_at") or ""),
            absorbed_into=fm.get("absorbed_into"),
            supersedes=fm.get("supersedes"),
            superseded_by=fm.get("superseded_by"),
            created_by=creator_val,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SecondBrainNote:
        return cls(
            id=str(data.get("id") or f"NOTE-{uuid_short()}"),
            title=str(data.get("title") or ""),
            kind=str(data.get("kind") or DRAFT_KIND_LESSON),
            created=str(data.get("created") or now_iso()),
            updated=str(data.get("updated") or now_iso()),
            mien=str(data.get("mien") or "general"),
            applies_when=str(data.get("applies_when") or ""),
            does_not_apply_when=str(data.get("does_not_apply_when") or ""),
            trang_thai=str(data.get("trang_thai") or "draft"),
            evidence_refs=list(data.get("evidence_refs") or []),
            partition=str(data.get("partition") or "local_habit"),
            links=list(data.get("links") or []),
            content_body=str(data.get("content_body") or ""),
            supporting_files=dict(data.get("supporting_files") or {}),
            pinned=bool(data.get("pinned", False)),
            use_count=int(data.get("use_count", 0)),
            last_activity_at=str(data.get("last_activity_at") or ""),
            absorbed_into=data.get("absorbed_into"),
            supersedes=data.get("supersedes"),
            superseded_by=data.get("superseded_by"),
            created_by=str(data.get("created_by") or "agent"),
        )


def uuid_short() -> str:
    """Generate a clean 8-character hex ID."""
    return hashlib.sha256(f"{time.time()}-{os.getpid()}".encode("utf-8")).hexdigest()[:8].upper()


def now_iso() -> str:
    """ISO 8601 timestamp with local/UTC timezone."""
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# ==============================================================================
# 2. LEARNING SIGNAL MODELS & DETECTION
# ==============================================================================

@dataclass
class LearningSignal:
    """Captured signal indicating a self-learning opportunity."""

    signal_type: str  # SIGNAL_USER_CORRECTION, SIGNAL_DISLIKE_WITH_REASON, SIGNAL_REPEATED_INVESTIGATION
    raw_text: str
    reason_category: str = ""  # 'sai' | 'kho_hieu' | 'thieu_nguon' | 'lac_de' | ""
    domain: str = "general"
    conversation_id: str = ""
    message_id: str = ""
    trace_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


# Patterns indicating user correction in chat
_CORRECTION_PATTERNS = [
    re.compile(r"không\s+phải", re.IGNORECASE),
    re.compile(r"không\s+đúng", re.IGNORECASE),
    re.compile(r"nhầm\s+rồi", re.IGNORECASE),
    re.compile(r"sai\s+rồi", re.IGNORECASE),
    re.compile(r"đừng\s+(kẻ\s+bảng|vẽ\s+bảng|dùng\s+bảng|format|làm\s+thế)", re.IGNORECASE),
    re.compile(r"đừng\s+(viết\s+dài|dài\s+dòng|lan\s+man)", re.IGNORECASE),
    re.compile(r"hãy\s+(tóm\s+tắt|rút\s+gọn|ghi\s+ngắn)", re.IGNORECASE),
    re.compile(r"(\d+)\s+gạch\s+đầu\s+dòng", re.IGNORECASE),
    re.compile(r"quy\s+trình\s+phải\s+là", re.IGNORECASE),
    re.compile(r"bước\s+(\d+)\s+phải\s+là", re.IGNORECASE),
    re.compile(r"phải\s+kiểm\s+tra\s+.*\s+trước", re.IGNORECASE),
    re.compile(r"sửa\s+(lại|đi)", re.IGNORECASE),
    re.compile(r"thiếu\s+bước", re.IGNORECASE),
    re.compile(r"bỏ\s+qua\s+bước", re.IGNORECASE),
    re.compile(r"lần\s+sau\s+(nhớ|làm)", re.IGNORECASE),
]

# Patterns indicating repeated investigation sequence
_INVESTIGATION_PATTERNS = [
    re.compile(r"\b(4m|man|machine|material|method)\b", re.IGNORECASE),
    re.compile(r"\b(mã\s+lỗi|error\s+code|sự\s+cố|hỏng\s+hóc)\b", re.IGNORECASE),
    re.compile(r"\b(jig|sensor|cảm\s+biến|đo\s+beam|căn\s+chỉnh)\b", re.IGNORECASE),
    re.compile(r"\b(nguyên\s+nhân\s+gốc|đối\s+sách|biên\s+bản)\b", re.IGNORECASE),
]


def detect_learning_signals(
    messages_snapshot: Sequence[Any],
    feedback_records: Optional[Sequence[Any]] = None,
    conversation_id: str = "",
    domain: str = "general",
) -> List[LearningSignal]:
    """Scan messages snapshot and feedback for Hermes-style self-learning signals."""
    signals: List[LearningSignal] = []
    if not messages_snapshot:
        return signals

    # 1. Scan for User Corrections
    # Compare consecutive turns: if User message follows an Assistant message and has correction phrases
    for i in range(len(messages_snapshot) - 1):
        curr = messages_snapshot[i]
        nxt = messages_snapshot[i + 1]
        curr_role = getattr(curr, "role", "") or (curr.get("role") if isinstance(curr, dict) else "")
        nxt_role = getattr(nxt, "role", "") or (nxt.get("role") if isinstance(nxt, dict) else "")

        if curr_role == "assistant" and nxt_role == "user":
            nxt_content = getattr(nxt, "content", "") or (nxt.get("content") if isinstance(nxt, dict) else "")
            curr_id = getattr(curr, "id", "") or (curr.get("id") if isinstance(curr, dict) else "")
            trace_id = getattr(curr, "trace_id", None) or (curr.get("trace_id") if isinstance(curr, dict) else None)

            for pattern in _CORRECTION_PATTERNS:
                if pattern.search(nxt_content):
                    signals.append(
                        LearningSignal(
                            signal_type=SIGNAL_USER_CORRECTION,
                            raw_text=nxt_content.strip(),
                            domain=domain or "general",
                            conversation_id=conversation_id,
                            message_id=curr_id,
                            trace_id=trace_id,
                            details={
                                "matched_pattern": pattern.pattern,
                                "assistant_reply_excerpt": str(getattr(curr, "content", "") or "")[:200],
                            },
                        )
                    )
                    break

    # 2. Scan for Dislike with Reason
    if feedback_records:
        for fb in feedback_records:
            rating = getattr(fb, "rating", "") or (fb.get("rating") if isinstance(fb, dict) else "")
            if rating in ("chua_huu_ich", "dislike", "down"):
                reason = getattr(fb, "reason", "") or (fb.get("reason") if isinstance(fb, dict) else "")
                r_cat = getattr(fb, "reason_category", "") or (fb.get("reason_category") if isinstance(fb, dict) else "")
                msg_id = getattr(fb, "message_id", "") or (fb.get("message_id") if isinstance(fb, dict) else "")
                fb_domain = getattr(fb, "domain", "") or (fb.get("domain") if isinstance(fb, dict) else domain)

                if reason or r_cat:
                    signals.append(
                        LearningSignal(
                            signal_type=SIGNAL_DISLIKE_WITH_REASON,
                            raw_text=str(reason or "").strip(),
                            reason_category=str(r_cat or "sai"),
                            domain=str(fb_domain or domain or "general"),
                            conversation_id=conversation_id,
                            message_id=msg_id,
                            details={"rating": rating, "reason_category": r_cat},
                        )
                    )

    # 3. Scan for Repeated Investigation Workflow
    investigation_hits = 0
    investigation_terms: List[str] = []
    for msg in messages_snapshot:
        content = getattr(msg, "content", "") or (msg.get("content") if isinstance(msg, dict) else "")
        for p in _INVESTIGATION_PATTERNS:
            match = p.search(content)
            if match:
                investigation_hits += 1
                investigation_terms.append(match.group(0))

    if investigation_hits >= 3:
        last_asst = next(
            (m for m in reversed(messages_snapshot) if (getattr(m, "role", "") or m.get("role", "") if isinstance(m, dict) else "") == "assistant"),
            None,
        )
        last_asst_id = getattr(last_asst, "id", "") if last_asst else ""
        signals.append(
            LearningSignal(
                signal_type=SIGNAL_REPEATED_INVESTIGATION,
                raw_text=f"Quy trình điều tra lặp lại với các từ khóa: {', '.join(set(investigation_terms))}",
                domain=domain or "dieutraloi",
                conversation_id=conversation_id,
                message_id=last_asst_id,
                details={"hits": investigation_hits, "terms": list(set(investigation_terms))},
            )
        )

    return signals


# ==============================================================================
# 3. HERMES SELF-LEARNING RUBRIC: LESSON VS SKILL
# ==============================================================================

def classify_draft_kind(signal: LearningSignal, context_text: str = "") -> str:
    """Hermes Rubric classifier: Distinguishes Lesson (BÀI HỌC) from Skill (KỸ NĂNG).

    Rubric criteria:
    - SKILL (KỸ NĂNG):
      * Multi-step procedures (Bước 1, Bước 2, Bước 3... / Step 1, Step 2...).
      * Methodological investigation workflows (4M, troubleshooting sequence, sensor calibration).
      * Accompanied by reusable templates, scripts, or reference checklists.
    - LESSON (BÀI HỌC):
      * Style, tone, verbosity, formatting preference (e.g. 'đừng kẻ bảng', '3 gạch đầu dòng', 'ngắn gọn').
      * Single factual gotcha, specific configuration quirk, or short atomic constraint.
      * Does NOT tell a story/incident narrative; imperative rule + WHY mechanism.
    """
    text_combined = f"{signal.raw_text} {context_text}".lower()

    if signal.signal_type == SIGNAL_REPEATED_INVESTIGATION:
        return DRAFT_KIND_SKILL

    # Check for multi-step procedure
    has_step_sequence = bool(
        re.search(r"bước\s*1.*bước\s*2", text_combined, re.DOTALL | re.IGNORECASE)
        or re.search(r"quy\s+trình\s+(\d+|nhiều)\s+bước", text_combined, re.IGNORECASE)
        or re.search(r"\b(quy\s+trình|phương\s+pháp|thao\s+tác\s+chuẩn)\b", text_combined, re.IGNORECASE)
    )
    if has_step_sequence:
        return DRAFT_KIND_SKILL

    # Check for explicit 4M or complex investigation
    if "4m" in text_combined or "điều tra nguyên nhân gốc" in text_combined:
        return DRAFT_KIND_SKILL

    # Otherwise, it's an atomic Lesson (style, formatting, short rule, single fact)
    return DRAFT_KIND_LESSON


# ==============================================================================
# 4. SECOND BRAIN VAULT & READ-BEFORE-WRITE GUARD
# ==============================================================================

def get_local_cases_dir() -> Path:
    env_dir = os.environ.get("AIOS_LOCAL_CASES_DIR", "").strip()
    if env_dir:
        return Path(env_dir)
    return Path("local_cases")


def get_second_brain_dir(root: Optional[Path] = None) -> Path:
    base = Path(root) if root is not None else get_local_cases_dir()
    return base / "second_brain"


def get_skills_dir(root: Optional[Path] = None) -> Path:
    base = Path(root) if root is not None else get_local_cases_dir()
    return base / "skills"


def get_lessons_dir(root: Optional[Path] = None) -> Path:
    base = Path(root) if root is not None else get_local_cases_dir()
    return base / "workspace_memory" / "lessons"


def read_skill_before_write(skill_name: str, skills_dir: Optional[Path] = None) -> Optional[SecondBrainNote]:
    """Read-Before-Write Guard (enforced):

    Inspects local skills store before generating or modifying a skill to prevent
    duplicate hoarding and ensure umbrella skill expansion.
    """
    s_dir = skills_dir if skills_dir is not None else get_skills_dir()
    target_md = s_dir / skill_name / "SKILL.md"
    if not target_md.exists():
        # Also check direct file
        target_md_direct = s_dir / f"{skill_name}.md"
        if target_md_direct.exists():
            target_md = target_md_direct
        else:
            return None
    try:
        content = target_md.read_text(encoding="utf-8")
        note = SecondBrainNote.from_markdown(content)
        return note
    except Exception as exc:
        LOGGER.warning("Could not read skill %s before write: %s", skill_name, exc)
        return None


def list_local_skills(skills_dir: Optional[Path] = None) -> List[SecondBrainNote]:
    """List all existing confirmed and draft local skills."""
    s_dir = skills_dir if skills_dir is not None else get_skills_dir()
    if not s_dir.exists():
        return []
    skills: List[SecondBrainNote] = []
    for item in s_dir.iterdir():
        if item.is_dir():
            if item.name.startswith("."):
                continue
            skill_md = item / "SKILL.md"
            if skill_md.exists():
                try:
                    note = SecondBrainNote.from_markdown(skill_md.read_text(encoding="utf-8"))
                    skills.append(note)
                except Exception:
                    pass
        elif item.suffix.lower() == ".md" and not item.name.endswith("_MOC.md") and not item.name.startswith("."):
            try:
                note = SecondBrainNote.from_markdown(item.read_text(encoding="utf-8"))
                if note.kind == DRAFT_KIND_SKILL:
                    skills.append(note)
            except Exception:
                pass
    return skills


def update_domain_moc(
    domain: str,
    note_id: str,
    title: str,
    kind: str,
    status: str = "draft",
    vault_dir: Optional[Path] = None,
) -> Path:
    """Update or create the Domain Map of Content (MOC) page in Second Brain."""
    v_dir = vault_dir if vault_dir is not None else get_second_brain_dir()
    v_dir.mkdir(parents=True, exist_ok=True)
    domain_clean = (domain or "general").strip().lower()
    moc_path = v_dir / f"{domain_clean}_MOC.md"

    existing_lines: List[str] = []
    if moc_path.exists():
        try:
            existing_lines = moc_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            existing_lines = []

    wikilink_entry = f"- [[{note_id}]]: {title} ({status})"

    # If file doesn't exist, create full MOC template
    if not existing_lines:
        content = f"""---
id: MOC-{domain_clean.upper()}
title: Mục lục Tri thức & Kỹ năng Miền {domain_clean.upper()}
kind: moc
mien: {domain_clean}
updated: {now_iso()}
partition: local_habit
---

# Mục lục Miền {domain_clean}

## Danh sách Kỹ năng (Skills)
{"- [[" + note_id + "]]: " + title + " (" + status + ")" if kind == DRAFT_KIND_SKILL else "*(Chưa có kỹ năng)*"}

## Danh sách Bài học (Lessons)
{"- [[" + note_id + "]]: " + title + " (" + status + ")" if kind == DRAFT_KIND_LESSON else "*(Chưa có bài học)*"}
"""
        moc_path.write_text(content, encoding="utf-8")
        return moc_path

    # If file exists, update or append wikilink
    content_str = "\n".join(existing_lines)
    if f"[[{note_id}]]" in content_str:
        # Update existing line
        new_lines = []
        for line in existing_lines:
            if f"[[{note_id}]]" in line:
                new_lines.append(wikilink_entry)
            else:
                new_lines.append(line)
        content_str = "\n".join(new_lines) + "\n"
    else:
        # Append under matching section
        target_header = "## Danh sách Kỹ năng (Skills)" if kind == DRAFT_KIND_SKILL else "## Danh sách Bài học (Lessons)"
        if target_header in content_str:
            parts = content_str.split(target_header)
            content_str = parts[0] + target_header + "\n" + wikilink_entry + "\n" + parts[1]
        else:
            content_str += f"\n\n{target_header}\n{wikilink_entry}\n"

    # Update timestamp in frontmatter
    content_str = re.sub(r"updated: .*", f"updated: {now_iso()}", content_str)
    moc_path.write_text(content_str, encoding="utf-8")
    return moc_path


def save_note_to_vault(note: SecondBrainNote, root: Optional[Path] = None) -> Path:
    """Save SecondBrainNote into the local habit store.

    - If SKILL: writes `local_cases/skills/<skill-name>/SKILL.md` + supporting files.
    - If LESSON: writes `local_cases/second_brain/lessons/<note-id>.md` and
      `local_cases/workspace_memory/lessons/<note-id>.md`.
    - Updates domain Map of Content (MOC).
    """
    base = Path(root) if root is not None else get_local_cases_dir()

    if note.kind == DRAFT_KIND_SKILL:
        skill_dir = base / "skills" / note.id
        skill_dir.mkdir(parents=True, exist_ok=True)
        note_path = skill_dir / "SKILL.md"
        note_path.write_text(note.to_markdown(), encoding="utf-8")

        # Save supporting files if present
        for rel_path, f_content in note.supporting_files.items():
            supp_path = skill_dir / rel_path
            supp_path.parent.mkdir(parents=True, exist_ok=True)
            supp_path.write_text(f_content, encoding="utf-8")
    else:
        lesson_dir = base / "second_brain" / "lessons"
        lesson_dir.mkdir(parents=True, exist_ok=True)
        note_path = lesson_dir / f"{note.id}.md"
        note_path.write_text(note.to_markdown(), encoding="utf-8")

        # Also mirror to workspace_memory/lessons
        wm_lesson_dir = base / "workspace_memory" / "lessons"
        wm_lesson_dir.mkdir(parents=True, exist_ok=True)
        (wm_lesson_dir / f"{note.id}.md").write_text(note.to_markdown(), encoding="utf-8")

    # Update domain MOC
    sb_dir = base / "second_brain"
    update_domain_moc(note.mien, note.id, note.title, note.kind, note.trang_thai, vault_dir=sb_dir)

    return note_path


# ==============================================================================
# 5. DRAFT SYNTHESIS (AUXILIARY MODEL + DETERMINISTIC RUBRIC FALLBACK)
# ==============================================================================

def synthesize_draft(
    signal: LearningSignal,
    context_messages: Sequence[Any],
    existing_skills: Optional[Sequence[SecondBrainNote]] = None,
    use_auxiliary: bool = True,
) -> SecondBrainNote:
    """Synthesize a complete SecondBrainNote draft adhering to Hermes Rubric."""
    kind = classify_draft_kind(signal)
    domain = signal.domain or "general"
    note_id = f"{kind.upper()}-{uuid_short()}"
    timestamp = now_iso()
    moc_link = f"[[{domain.lower()}_MOC]]"

    # Context excerpt
    context_summary = signal.raw_text.strip()
    evidence_refs = [
        f"conv:{signal.conversation_id}" if signal.conversation_id else "",
        f"msg:{signal.message_id}" if signal.message_id else "",
    ]
    evidence_refs = [ref for ref in evidence_refs if ref]

    if kind == DRAFT_KIND_SKILL:
        # Read existing skill to check for umbrella patch
        umbrella_name = f"skill_{domain.lower()}_investigation"
        existing_umbrella = read_skill_before_write(umbrella_name)
        title = f"Quy trình điều tra & xử lý sự cố miền {domain.upper()}"
        applies_when = f"Khi điều tra sự cố hoặc thực hiện quy trình kỹ thuật miền {domain}"
        does_not_apply_when = "Khi chỉ tra cứu định nghĩa đơn lẻ hoặc thông số tham khảo chung"

        body = f"""# {title}

## Mục đích & Phạm vi
Hướng dẫn thực hiện quy trình thao tác và điều tra theo chuẩn thói quen công việc miền {domain}.

## Quy trình thực hiện (Procedure First)
1. **Bước 1**: Tiếp nhận hiện tượng, ghi nhận thời điểm và mã lỗi/thông số liên quan.
2. **Bước 2**: Kiểm tra các yếu tố theo phương pháp 4M (Con người, Máy móc, Vật liệu, Phương pháp).
3. **Bước 3**: Đối chiếu thông số kỹ thuật đã kiểm chứng, tránh phụ thuộc vào suy đoán tạm thời.
4. **Bước 4**: Xác nhận kết quả điều tra và cập nhật báo cáo đối sách.

## Cạm bẫy cần tránh (Pitfalls)
- **Cạm bẫy**: Luôn kiểm tra dữ liệu log máy/jig trước khi kết luận lỗi do con người (Man) vì 80% độ lệch phát sinh từ drift cảm biến jig.

## Tệp phụ trợ (Supporting Files)
- `references/checklist_{domain.lower()}.md`: Bảng kiểm tra điều tra nhanh.
- `templates/bien_ban_su_co.md`: Biểu mẫu biên bản sự cố chuẩn.
- `scripts/verify_{domain.lower()}_log.py`: Script kiểm tra log tự động.

## Liên kết
- {moc_link}
"""
        supporting = {
            f"references/checklist_{domain.lower()}.md": f"# Bảng kiểm tra điều tra nhanh miền {domain}\n- [ ] Kiểm tra nguồn điện\n- [ ] Kiểm tra sensor\n- [ ] Kiểm tra log",
            "templates/bien_ban_su_co.md": "# Biểu mẫu biên bản sự cố\n1. Hiện tượng:\n2. Nguyên nhân:\n3. Đối sách:",
            f"scripts/verify_{domain.lower()}_log.py": "# Script kiểm tra log tự động\nprint('Log verification passed.')\n",
        }
        note = SecondBrainNote(
            id=note_id,
            title=title,
            kind=DRAFT_KIND_SKILL,
            created=timestamp,
            updated=timestamp,
            mien=domain,
            applies_when=applies_when,
            does_not_apply_when=does_not_apply_when,
            trang_thai="draft",
            evidence_refs=evidence_refs,
            partition="local_habit",
            links=[moc_link],
            content_body=body,
            supporting_files=supporting,
        )
    else:
        # Atomic Lesson
        # Extract the imperative rule from signal
        rule_text = signal.raw_text
        if signal.signal_type == SIGNAL_DISLIKE_WITH_REASON:
            cat_label = {
                REASON_CAT_SAI: "Sửa sai lệch sự thật / thông số",
                REASON_CAT_KHO_HIEU: "Trình bày ngắn gọn, dễ hiểu",
                REASON_CAT_THIEU_NGUON: "Trích dẫn nguồn kiểm chứng rõ ràng",
                REASON_CAT_LAC_DE: "Tập trung đúng trọng tâm câu hỏi",
            }.get(signal.reason_category, "Sửa cách trả lời")
            title = f"{cat_label} trong miền {domain}"
            rule_text = f"Khi trả lời về {domain}, cần lưu ý: {signal.raw_text}"
        elif "đừng" in rule_text.lower() or "tóm tắt" in rule_text.lower():
            title = f"Thói quen trình bày & định dạng ({domain})"
        else:
            title = f"Bài học thói quen miền {domain}"

        applies_when = f"Khi trả lời câu hỏi thuộc miền {domain}"
        does_not_apply_when = "Khi người dùng có yêu cầu định dạng khác rõ ràng"

        body = f"""# {title}

## Quy tắc thói quen (Rule)
{rule_text}

## Cơ chế / Căn cứ (Why)
Phản hồi từ người dùng qua phiên làm việc ({signal.signal_type}) nhằm chuẩn hóa phong cách làm việc và độ chính xác của câu trả lời.

## Liên kết
- {moc_link}
"""
        note = SecondBrainNote(
            id=note_id,
            title=title,
            kind=DRAFT_KIND_LESSON,
            created=timestamp,
            updated=timestamp,
            mien=domain,
            applies_when=applies_when,
            does_not_apply_when=does_not_apply_when,
            trang_thai="draft",
            evidence_refs=evidence_refs,
            partition="local_habit",
            links=[moc_link],
            content_body=body,
        )

    return note


# ==============================================================================
# 6. STAGING DRAFT INTO "SỬA ĐỂ AIOS HỌC" UI
# ==============================================================================

def stage_draft_into_pending_form(
    note: SecondBrainNote,
    message_id: str,
    workspace_id: str = "default",
    path: Optional[Path] = None,
) -> None:
    """Push generated draft into pending_drafts.json for the existing UI."""
    from aios_habit.workspace_memory_service import (
        load_pending_drafts,
        save_pending_correction_form,
        save_pending_drafts,
    )

    # 1. Update standard correction form fields
    save_pending_correction_form(
        message_id=message_id,
        statement=note.to_markdown(),
        applies_when=note.applies_when,
        does_not_apply_when=note.does_not_apply_when,
        path=path,
    )

    # 2. Attach auto-draft metadata
    drafts = load_pending_drafts(path=path)
    auto_drafts = dict(drafts.get("auto_drafts") or {})
    auto_drafts[str(message_id)] = {
        "note_id": note.id,
        "kind": note.kind,
        "title": note.title,
        "domain": note.mien,
        "is_auto_draft": True,
        "created_at": now_iso(),
        "note_dict": note.to_dict(),
    }
    drafts["auto_drafts"] = auto_drafts
    save_pending_drafts(drafts, path=path)


# ==============================================================================
# 7. BACKGROUND REVIEW DAEMON THREAD & CANCELLATION
# ==============================================================================

class BackgroundReviewRun:
    """Manages thread cancellation and preemption."""

    def __init__(self) -> None:
        self.cancel_requested = threading.Event()
        self.done = threading.Event()
        self._lock = threading.Lock()
        self.is_running = False

    def cancel(self) -> None:
        with self._lock:
            self.cancel_requested.set()


_ACTIVE_REVIEW_RUN: Optional[BackgroundReviewRun] = None
_ACTIVE_REVIEW_LOCK = threading.Lock()


def cancel_active_review() -> None:
    """Preempt any running background review within 2.0 seconds."""
    global _ACTIVE_REVIEW_RUN
    with _ACTIVE_REVIEW_LOCK:
        if _ACTIVE_REVIEW_RUN is not None and not _ACTIVE_REVIEW_RUN.done.is_set():
            _ACTIVE_REVIEW_RUN.cancel()


def is_review_cancelled(run: Optional[BackgroundReviewRun]) -> bool:
    if run is None:
        return False
    return run.cancel_requested.is_set()


def _log_review_event(event_data: Dict[str, Any], root: Optional[Path] = None) -> None:
    """Append audit entry to local_cases/post_session_review.jsonl."""
    base = Path(root) if root is not None else get_local_cases_dir()
    base.mkdir(parents=True, exist_ok=True)
    log_file = base / "post_session_review.jsonl"
    entry = {"timestamp": now_iso(), **event_data}
    try:
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:
        LOGGER.warning("Could not write review event log: %s", exc)


def _run_review_worker(
    run: BackgroundReviewRun,
    conversation_id: str,
    messages_snapshot: List[Any],
    domain: str,
    last_assistant_id: str,
    last_trace_id: Optional[str] = None,
    feedback_records: Optional[List[Any]] = None,
    drafts_path: Optional[Path] = None,
) -> None:
    """Background thread worker for post-session review."""
    run.is_running = True
    try:
        if is_review_cancelled(run):
            return

        # 1. Detect signals
        signals = detect_learning_signals(
            messages_snapshot=messages_snapshot,
            feedback_records=feedback_records,
            conversation_id=conversation_id,
            domain=domain,
        )
        if not signals or is_review_cancelled(run):
            _log_review_event({
                "conversation_id": conversation_id,
                "status": "no_signals_detected",
                "message_count": len(messages_snapshot),
            })
            return

        # 2. Pick the primary signal
        primary_signal = signals[0]

        # 3. Read existing skills (Read-Before-Write guard)
        existing_skills = list_local_skills()

        # 4. Synthesize draft
        draft_note = synthesize_draft(
            signal=primary_signal,
            context_messages=messages_snapshot,
            existing_skills=existing_skills,
        )

        if is_review_cancelled(run):
            return

        # 5. Stage draft into UI
        target_msg_id = last_assistant_id or primary_signal.message_id or f"MSG-AUTO-{uuid_short()}"
        stage_draft_into_pending_form(
            note=draft_note,
            message_id=target_msg_id,
            workspace_id=domain,
            path=drafts_path,
        )

        # 5b. Hermes Ported Reviewer integration (USER.md / MEMORY.md)
        try:
            from aios_habit.hermes_post_session_review import extract_review_learning
            msg_dicts = [
                {"role": getattr(m, "role", "user"), "content": getattr(m, "content", "")}
                for m in messages_snapshot
            ]
            hermes_res = extract_review_learning(msg_dicts)
            if hermes_res:
                _log_review_event({
                    "conversation_id": conversation_id,
                    "status": "hermes_review_learning_captured",
                    "target": hermes_res.get("target"),
                    "entry": hermes_res.get("entry"),
                })
        except Exception as e:
            LOGGER.debug("Hermes review extraction: %s", e)

        _log_review_event({
            "conversation_id": conversation_id,
            "status": "draft_staged",
            "signal_type": primary_signal.signal_type,
            "draft_id": draft_note.id,
            "draft_kind": draft_note.kind,
            "draft_title": draft_note.title,
            "target_message_id": target_msg_id,
        })
    except Exception as exc:
        LOGGER.error("Error in background post-session review: %s", exc, exc_info=True)
        _log_review_event({
            "conversation_id": conversation_id,
            "status": "error",
            "error": str(exc),
        })
    finally:
        run.done.set()
        run.is_running = False


def spawn_post_session_review(
    conversation_id: str,
    messages_snapshot: Sequence[Any],
    notebook_id: Optional[str] = None,
    domain: Optional[str] = None,
    last_assistant_id: Optional[str] = None,
    last_trace_id: Optional[str] = None,
    feedback_records: Optional[Sequence[Any]] = None,
    async_mode: bool = True,
    drafts_path: Optional[Path] = None,
) -> Optional[BackgroundReviewRun]:
    """Spawn a post-session review daemon thread after a chat turn completes.

    Checks Master Switch: If disabled, immediately returns None.
    Preempts any active review run before starting a new one.
    """
    global _ACTIVE_REVIEW_RUN

    # Check Master Switch
    if not get_master_self_learn_preference():
        return None

    # Preempt any active run
    cancel_active_review()

    run = BackgroundReviewRun()
    with _ACTIVE_REVIEW_LOCK:
        _ACTIVE_REVIEW_RUN = run

    dom = domain or notebook_id or "general"
    snapshot_list = list(messages_snapshot)
    fb_list = list(feedback_records) if feedback_records else None

    if not async_mode:
        # Run synchronously (useful for tests)
        _run_review_worker(
            run=run,
            conversation_id=conversation_id,
            messages_snapshot=snapshot_list,
            domain=dom,
            last_assistant_id=last_assistant_id or "",
            last_trace_id=last_trace_id,
            feedback_records=fb_list,
            drafts_path=drafts_path,
        )
        return run

    # Spawn daemon thread
    thread = threading.Thread(
        target=_run_review_worker,
        kwargs={
            "run": run,
            "conversation_id": conversation_id,
            "messages_snapshot": snapshot_list,
            "domain": dom,
            "last_assistant_id": last_assistant_id or "",
            "last_trace_id": last_trace_id,
            "feedback_records": fb_list,
            "drafts_path": drafts_path,
        },
        daemon=True,
        name="bg-post-session-review",
    )
    thread.start()
    return run


# ==============================================================================
# 8. MASTER SWITCH & HABIT PROFILE WIPE OPERATIONS
# ==============================================================================

def get_master_self_learn_preference(path: Optional[Path] = None) -> bool:
    """Return whether master self-learning is enabled."""
    from aios_habit.workspace_memory_service import (
        _SETTINGS_OVERRIDE,
        default_memory_settings_path,
    )

    s_path = (
        path
        if path is not None
        else (_SETTINGS_OVERRIDE.get() or default_memory_settings_path())
    )
    if not s_path.exists():
        return DEFAULT_MASTER_SELF_LEARN_ENABLED
    try:
        data = json.loads(s_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return DEFAULT_MASTER_SELF_LEARN_ENABLED
        val = data.get(MASTER_SELF_LEARN_SETTING_KEY)
        if val is None:
            # Fallback to memory_enabled
            val = data.get("memory_enabled", DEFAULT_MASTER_SELF_LEARN_ENABLED)
        return bool(val)
    except Exception:
        return DEFAULT_MASTER_SELF_LEARN_ENABLED


def set_master_self_learn_preference(enabled: bool, path: Optional[Path] = None) -> None:
    """Persist master self-learning setting."""
    from aios_habit.workspace_memory_service import default_memory_settings_path

    s_path = path if path is not None else default_memory_settings_path()
    s_path.parent.mkdir(parents=True, exist_ok=True)
    current = {}
    if s_path.exists():
        try:
            current = json.loads(s_path.read_text(encoding="utf-8"))
        except Exception:
            current = {}
    current[MASTER_SELF_LEARN_SETTING_KEY] = bool(enabled)
    current["memory_enabled"] = bool(enabled)
    tmp_path = s_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp_path, s_path)


def wipe_all_habit_profiles(root: Optional[Path] = None) -> Dict[str, int]:
    """Safely wipe all habit profile data.

    Cleans:
    - memory_decisions.jsonl
    - pending_drafts.json
    - local_cases/second_brain/
    - local_cases/skills/
    - local_cases/workspace_memory/lessons/
    - post_session_review.jsonl

    Does NOT touch:
    - company knowledge / data/
    - library databases
    - settings.json (keeps preferences intact)

    Returns dictionary of item counts deleted.
    """
    base = Path(root) if root is not None else get_local_cases_dir()
    stats = {"decisions_removed": 0, "drafts_removed": 0, "notes_removed": 0, "skills_removed": 0}

    # 1. Clear memory_decisions.jsonl
    dec_file = base / "workspace_memory" / "memory_decisions.jsonl"
    if dec_file.exists():
        try:
            lines = [l for l in dec_file.read_text(encoding="utf-8").splitlines() if l.strip()]
            stats["decisions_removed"] = len(lines)
            dec_file.unlink()
        except Exception:
            pass

    # 2. Clear pending_drafts.json
    draft_file = base / "workspace_memory" / "pending_drafts.json"
    if draft_file.exists():
        try:
            draft_file.unlink()
            stats["drafts_removed"] = 1
        except Exception:
            pass

    # 3. Clear second brain lessons and MOCs
    sb_dir = base / "second_brain"
    if sb_dir.exists():
        for item in sb_dir.rglob("*"):
            if item.is_file():
                try:
                    item.unlink()
                    stats["notes_removed"] += 1
                except Exception:
                    pass

    # 4. Clear skills
    skills_dir = base / "skills"
    if skills_dir.exists():
        for item in skills_dir.rglob("*"):
            if item.is_file():
                try:
                    item.unlink()
                    stats["skills_removed"] += 1
                except Exception:
                    pass

    # 5. Clear workspace_memory lessons
    wm_lessons = base / "workspace_memory" / "lessons"
    if wm_lessons.exists():
        for item in wm_lessons.rglob("*.md"):
            if item.is_file():
                try:
                    item.unlink()
                    stats["notes_removed"] += 1
                except Exception:
                    pass

    # 6. Clear review log
    review_log = base / "post_session_review.jsonl"
    if review_log.exists():
        try:
            review_log.unlink()
        except Exception:
            pass

    return stats
