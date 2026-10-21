"""Skills Curator & Local Habit Store for AIOS Habit.

Implements ticket DESKTOP-SELF-LEARN-CURATOR-SKILLS-LOCAL-STORE:
1. Local skills store conforming to Hermes structure:
   local_cases/skills/<skill-name>/ containing:
   - SKILL.md (YAML frontmatter + Markdown body)
   - references/
   - templates/
   - scripts/
2. Curator maintenance orchestrator in src/aios_habit/skills_curator.py:
   - Inactivity-triggered: Runs only when system is idle > 2 hours and last run >= 7 days.
   - Deterministic pruning: Unused > 14 days -> stale; unused > 30 days -> .archive/
     (never permanently deleted). Pinned skills bypass all pruning cycles.
   - Fail-closed guard: Never modifies company knowledge (05_memory_vault/ or
     company_knowledge partition). Consolidation requires absorbed_into tag.
   - Skill tooling: list, restore from archive, pin/unpin, consolidate.
3. Second Brain Habit Journal (Sổ thói quen) Standard:
   - Atomic notes: one markdown file per lesson in second_brain/lessons/.
   - YAML frontmatter with standardized metadata.
   - Bi-directional wikilinks ([[note_id]] <-> [[skill_name]] <-> [[case_id]]).
   - Domain Map of Content (MOC) auto-maintained.
   - Obsidian vault compatibility (.obsidian/ config, human edit protection via Read-Before-Write).
   - Fast retrieval with supersede chain traversal and negative constraint filtering.
   - Legacy data migration from memory_decisions.jsonl and learning_cards.jsonl.

Compatible with Python 3.11+.
"""

from __future__ import annotations

import contextlib
import ctypes
import hashlib
import json
import logging
import os
import re
import shutil
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set, Tuple

import yaml

from aios_habit.post_session_review import (
    DRAFT_KIND_LESSON,
    DRAFT_KIND_SKILL,
    SecondBrainNote,
    get_lessons_dir as psr_get_lessons_dir,
    get_local_cases_dir as psr_get_local_cases_dir,
    get_second_brain_dir as psr_get_second_brain_dir,
    get_skills_dir as psr_get_skills_dir,
    now_iso,
    update_domain_moc,
    uuid_short,
)

LOGGER = logging.getLogger(__name__)

# --- Timing & Threshold Defaults ---
DEFAULT_INTERVAL_HOURS: float = 168.0  # 7 days
DEFAULT_MIN_IDLE_HOURS: float = 2.0     # 2 hours
DEFAULT_STALE_AFTER_DAYS: float = 14.0  # 14 days
DEFAULT_ARCHIVE_AFTER_DAYS: float = 30.0  # 30 days
CLAIM_STALE_SECONDS: float = 3600.0     # 1 hour file-lock timeout

# --- Lifecycle States ---
STATE_ACTIVE = "active"
STATE_STALE = "stale"
STATE_ARCHIVED = "archived"
STATE_SUPERSEDED = "superseded"
STATE_CONFIRMED = "confirmed"
STATE_DRAFT = "draft"

# --- Partitions ---
PARTITION_LOCAL_HABIT = "local_habit"
PARTITION_COMPANY_KNOWLEDGE = "company_knowledge"


# ==============================================================================
# 1. EXCEPTIONS & SAFETY GUARDRAILS
# ==============================================================================

class CuratorSafetyError(PermissionError):
    """Raised when curator operations violate boundary or fail-closed invariants."""


class ManualEditConflictError(RuntimeError):
    """Raised when a file was modified manually in Obsidian and cannot be safely overwritten."""


class SkillNotFoundError(FileNotFoundError):
    """Raised when an operation targets a skill that does not exist."""


def assert_curator_safety(target_path: Path | str, partition: str = PARTITION_LOCAL_HABIT) -> None:
    """Fail-closed guardrail:

    Curator is STRICTLY confined to local user skills and local second brain habit notes.
    Any attempt to modify company knowledge or write outside local_cases raises CuratorSafetyError.
    """
    if partition == PARTITION_COMPANY_KNOWLEDGE:
        raise CuratorSafetyError(
            "Curator Fail-Closed Violation: Refusing to modify company knowledge partition."
        )

    resolved = Path(target_path).resolve()
    resolved_str = str(resolved).replace("\\", "/").lower()

    # Block any access to corporate memory vault
    if "05_memory_vault" in resolved_str:
        raise CuratorSafetyError(
            f"Curator Fail-Closed Violation: Direct write to 05_memory_vault blocked ({resolved})."
        )


# ==============================================================================
# 2. DATA MODELS
# ==============================================================================

@dataclass
class SkillRecord:
    """Represents a local skill managed by the Curator."""

    name: str
    title: str
    kind: str = DRAFT_KIND_SKILL
    mien: str = "general"
    state: str = STATE_ACTIVE
    pinned: bool = False
    use_count: int = 0
    created_at: str = ""
    updated_at: str = ""
    last_activity_at: str = ""
    applies_when: str = ""
    does_not_apply_when: str = ""
    partition: str = PARTITION_LOCAL_HABIT
    evidence_refs: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    path: Optional[Path] = None
    absorbed_into: Optional[str] = None
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
    created_by: str = "agent"
    content_body: str = ""
    supporting_files: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.path is not None:
            d["path"] = str(self.path)
        return d


@dataclass
class CuratorRunReport:
    """Execution report returned after a Curator run."""

    started_at: str
    finished_at: str
    duration_seconds: float
    checked_count: int = 0
    marked_stale_count: int = 0
    archived_count: int = 0
    reactivated_count: int = 0
    pinned_bypassed_count: int = 0
    consolidated_count: int = 0
    summary: str = ""
    actions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ==============================================================================
# 3. DIRECTORY & PATH HELPERS
# ==============================================================================

def get_local_cases_dir() -> Path:
    return psr_get_local_cases_dir()


def get_skills_dir(root: Optional[Path] = None) -> Path:
    base = Path(root) if root is not None else get_local_cases_dir()
    return base / "skills"


def get_second_brain_dir(root: Optional[Path] = None) -> Path:
    base = Path(root) if root is not None else get_local_cases_dir()
    return base / "second_brain"


def _state_file_path(skills_dir: Path) -> Path:
    return skills_dir / ".curator_state"


def _ledger_file_path(skills_dir: Path) -> Path:
    return skills_dir / ".curator_ledger.jsonl"


def _run_claim_path(skills_dir: Path) -> Path:
    return skills_dir / ".locks" / "curator-run.lock"


# ==============================================================================
# 4. FILE LOCKING & MUTEX (PROCESS SYNCHRONIZATION)
# ==============================================================================

def claim_run_lock(skills_dir: Path) -> bool:
    """Acquire an atomic process lock using O_CREAT | O_EXCL.

    If an existing lock is older than CLAIM_STALE_SECONDS (1 hour),
    it is treated as a crashed holder and taken over safely.
    """
    lock_file = _run_claim_path(skills_dir)
    try:
        lock_file.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return True

    try:
        fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            mtime = lock_file.stat().st_mtime
            if (time.time() - mtime) > CLAIM_STALE_SECONDS:
                LOGGER.warning("Curator lock file is stale (>%ds), breaking lock.", CLAIM_STALE_SECONDS)
                with contextlib.suppress(OSError):
                    lock_file.unlink()
                return claim_run_lock(skills_dir)
        except OSError:
            pass
        return False

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(f"pid={os.getpid()}\ntimestamp={now_iso()}\n")
        return True
    except Exception:
        with contextlib.suppress(OSError):
            lock_file.unlink()
        return False


def release_run_lock(skills_dir: Path) -> None:
    """Release the atomic process lock file."""
    lock_file = _run_claim_path(skills_dir)
    with contextlib.suppress(OSError):
        if lock_file.exists():
            lock_file.unlink()


# ==============================================================================
# 5. STATE & AUDIT LEDGER PERSISTENCE
# ==============================================================================

def load_curator_state(skills_dir: Path) -> Dict[str, Any]:
    """Load persistent scheduler state from .curator_state."""
    base: Dict[str, Any] = {
        "last_run_at": None,
        "last_run_duration_seconds": None,
        "last_run_summary": None,
        "run_count": 0,
        "paused": False,
        "stale_count": 0,
        "archived_count": 0,
        "reactivated_count": 0,
        "last_report_path": None,
    }
    path = _state_file_path(skills_dir)
    if not path.exists():
        return base
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            base.update(data)
    except Exception as exc:
        LOGGER.warning("Could not load curator state from %s: %s", path, exc)
    return base


def save_curator_state(skills_dir: Path, data: Dict[str, Any]) -> None:
    """Atomic write of curator state via temp file."""
    skills_dir.mkdir(parents=True, exist_ok=True)
    target = _state_file_path(skills_dir)
    tmp_path = skills_dir / f".curator_state.tmp.{os.getpid()}"
    try:
        tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(target)
    except Exception as exc:
        LOGGER.error("Failed to save curator state: %s", exc)
        with contextlib.suppress(OSError):
            if tmp_path.exists():
                tmp_path.unlink()


def is_curator_paused(skills_dir: Path) -> bool:
    return bool(load_curator_state(skills_dir).get("paused", False))


def set_curator_paused(skills_dir: Path, paused: bool) -> None:
    st = load_curator_state(skills_dir)
    st["paused"] = bool(paused)
    save_curator_state(skills_dir, st)


def log_curator_ledger(
    skills_dir: Path,
    action: str,
    skill_name: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Append immutable audit log entry into .curator_ledger.jsonl."""
    skills_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = _ledger_file_path(skills_dir)
    entry = {
        "timestamp": now_iso(),
        "action": action,
        "skill_name": skill_name,
        "details": details or {},
    }
    try:
        with open(ledger_path, "a", encoding="utf-8") as fp:
            fp.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:
        LOGGER.warning("Failed to write to curator ledger: %s", exc)


# ==============================================================================
# 6. INACTIVITY & INTERVAL GATING (NON-BLOCKING)
# ==============================================================================

def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def get_os_idle_seconds() -> Optional[float]:
    """Measure OS-level input idle time on Windows using GetLastInputInfo."""
    if sys.platform != "win32":
        return None
    try:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            return max(0.0, float(millis) / 1000.0)
    except Exception:
        pass
    return None


def get_last_user_activity_timestamp(local_cases_dir: Optional[Path] = None) -> Optional[datetime]:
    """Find the latest user interaction timestamp from local cases files."""
    base = local_cases_dir if local_cases_dir is not None else get_local_cases_dir()
    if not base.exists():
        return None

    candidate_files = [
        base / "answer_feedback.jsonl",
        base / "workspace_memory" / "pending_drafts.json",
        base / "workspace_chat_app.log",
        base / "cases.jsonl",
    ]

    latest_mtime: float = 0.0
    for f in candidate_files:
        if f.exists():
            try:
                mt = f.stat().st_mtime
                if mt > latest_mtime:
                    latest_mtime = mt
            except OSError:
                pass

    # Check workspace_chat SQLite files
    chat_dir = base / "workspace_chat"
    if chat_dir.exists():
        for item in chat_dir.glob("*.sqlite*"):
            try:
                mt = item.stat().st_mtime
                if mt > latest_mtime:
                    latest_mtime = mt
            except OSError:
                pass

    if latest_mtime > 0.0:
        return datetime.fromtimestamp(latest_mtime, tz=timezone.utc)
    return None


def get_idle_seconds(
    local_cases_dir: Optional[Path] = None,
    now: Optional[datetime] = None,
) -> float:
    """Return total inactivity duration in seconds."""
    current = now or datetime.now(timezone.utc)
    last_act = get_last_user_activity_timestamp(local_cases_dir)
    file_idle: Optional[float] = None
    if last_act is not None:
        file_idle = max(0.0, (current - last_act).total_seconds())

    os_idle = get_os_idle_seconds()
    if os_idle is not None and file_idle is not None:
        # Use the more conservative (shorter) idle duration
        return min(os_idle, file_idle)
    if file_idle is not None:
        return file_idle
    if os_idle is not None:
        return os_idle
    # Default to 3 hours if no files exist yet
    return 3.0 * 3600.0


def should_run_now(
    skills_dir: Path,
    local_cases_dir: Optional[Path] = None,
    now: Optional[datetime] = None,
    force: bool = False,
    idle_for_seconds: Optional[float] = None,
    interval_hours: float = DEFAULT_INTERVAL_HOURS,
    min_idle_hours: float = DEFAULT_MIN_IDLE_HOURS,
) -> bool:
    """Gates for Curator automatic trigger:

    1. Must not be paused.
    2. Interval since last run must be >= interval_hours (default: 7 days).
       If first run (last_run_at is None), seeds last_run_at and defers.
    3. Machine must be idle >= min_idle_hours (default: 2 hours).
    4. Passing force=True bypasses all gates.
    """
    if force:
        return True

    if is_curator_paused(skills_dir):
        return False

    current = now or datetime.now(timezone.utc)
    state = load_curator_state(skills_dir)
    last_run = _parse_iso(state.get("last_run_at"))

    if last_run is None:
        # Defer first run on fresh setup to avoid mutating library immediately
        state["last_run_at"] = current.isoformat()
        state["last_run_summary"] = "deferred first run — curator seeded, will run after one interval"
        save_curator_state(skills_dir, state)
        return False

    # Check interval (>= 7 days)
    elapsed_hours = (current - last_run).total_seconds() / 3600.0
    if elapsed_hours < interval_hours:
        return False

    # Check inactivity (>= 2 hours)
    idle_s = idle_for_seconds if idle_for_seconds is not None else get_idle_seconds(local_cases_dir, now=current)
    if idle_s < (min_idle_hours * 3600.0):
        return False

    return True


# ==============================================================================
# 7. PARSING & READ-BEFORE-WRITE PROTECTION
# ==============================================================================

def parse_skill_file(skill_md_path: Path) -> SkillRecord:
    """Parse SKILL.md into SkillRecord with complete frontmatter metadata."""
    if not skill_md_path.exists():
        raise SkillNotFoundError(f"SKILL.md not found at {skill_md_path}")

    text = skill_md_path.read_text(encoding="utf-8")
    note = SecondBrainNote.from_markdown(text)
    name = skill_md_path.parent.name

    # Determine state: respect frontmatter 'trang_thai' or 'state'
    raw_frontmatter: Dict[str, Any] = {}
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            with contextlib.suppress(Exception):
                raw_frontmatter = yaml.safe_load(parts[1]) or {}

    state = str(raw_frontmatter.get("state") or raw_frontmatter.get("trang_thai") or STATE_ACTIVE)
    if state == "confirmed":
        state = STATE_ACTIVE

    # Load any supporting files
    skill_dir = skill_md_path.parent
    supporting: Dict[str, str] = {}
    for sub in ("references", "templates", "scripts"):
        sub_path = skill_dir / sub
        if sub_path.exists() and sub_path.is_dir():
            for f in sub_path.rglob("*"):
                if f.is_file():
                    rel = f.relative_to(skill_dir).as_posix()
                    try:
                        supporting[rel] = f.read_text(encoding="utf-8")
                    except Exception:
                        pass

    return SkillRecord(
        name=name,
        title=note.title or name,
        kind=DRAFT_KIND_SKILL,
        mien=note.mien or "general",
        state=state,
        pinned=bool(raw_frontmatter.get("pinned", False)),
        use_count=int(raw_frontmatter.get("use_count", 0)),
        created_at=note.created,
        updated_at=note.updated,
        last_activity_at=str(raw_frontmatter.get("last_activity_at") or note.updated or note.created),
        applies_when=note.applies_when,
        does_not_apply_when=note.does_not_apply_when,
        partition=note.partition or PARTITION_LOCAL_HABIT,
        evidence_refs=list(note.evidence_refs),
        links=list(note.links),
        path=skill_md_path,
        absorbed_into=raw_frontmatter.get("absorbed_into"),
        supersedes=raw_frontmatter.get("supersedes"),
        superseded_by=raw_frontmatter.get("superseded_by"),
        created_by=str(raw_frontmatter.get("created_by") or "agent"),
        content_body=note.content_body,
        supporting_files=supporting,
    )


def save_skill_to_store(
    skill: SkillRecord | SecondBrainNote,
    skills_dir: Optional[Path] = None,
    overwrite_conflict: bool = False,
    expected_hash: Optional[str] = None,
) -> Path:
    """Save a skill into local_cases/skills/<skill-name>/ adhering to Hermes standard.

    Creates:
    - SKILL.md
    - references/
    - templates/
    - scripts/
    Enforces Read-Before-Write guard: if the file on disk was modified by user
    since expected_hash, raises ManualEditConflictError.
    """
    s_dir = skills_dir if skills_dir is not None else get_skills_dir()
    name = skill.name if isinstance(skill, SkillRecord) else skill.id
    target_dir = s_dir / name
    assert_curator_safety(target_dir, partition=skill.partition)

    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "references").mkdir(parents=True, exist_ok=True)
    (target_dir / "templates").mkdir(parents=True, exist_ok=True)
    (target_dir / "scripts").mkdir(parents=True, exist_ok=True)

    target_md = target_dir / "SKILL.md"

    # Read-Before-Write Conflict Guard
    if target_md.exists() and not overwrite_conflict and expected_hash:
        current_content = target_md.read_text(encoding="utf-8")
        current_hash = hashlib.sha256(current_content.encode("utf-8")).hexdigest()
        if current_hash != expected_hash:
            raise ManualEditConflictError(
                f"Manual edit conflict detected for skill '{name}' in Obsidian. "
                "File was modified externally; refusing to overwrite silently."
            )

    # Convert to SecondBrainNote for consistent markdown rendering
    if isinstance(skill, SkillRecord):
        note = SecondBrainNote(
            id=skill.name,
            title=skill.title,
            kind=DRAFT_KIND_SKILL,
            created=skill.created_at or now_iso(),
            updated=skill.updated_at or now_iso(),
            mien=skill.mien,
            applies_when=skill.applies_when,
            does_not_apply_when=skill.does_not_apply_when,
            trang_thai=skill.state,
            evidence_refs=list(skill.evidence_refs),
            partition=skill.partition,
            links=list(skill.links),
            content_body=skill.content_body,
            supporting_files=dict(skill.supporting_files),
            pinned=skill.pinned,
            use_count=skill.use_count,
            last_activity_at=skill.last_activity_at,
            absorbed_into=skill.absorbed_into,
            supersedes=skill.supersedes,
            superseded_by=skill.superseded_by,
            created_by=skill.created_by,
        )
    else:
        note = skill

    target_md.write_text(note.to_markdown(), encoding="utf-8")

    # Write supporting files
    for rel_path, file_content in note.supporting_files.items():
        file_path = target_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(file_content, encoding="utf-8")

    # Update Domain MOC
    vault_dir = get_second_brain_dir()
    update_domain_moc(
        domain=note.mien,
        note_id=name,
        title=note.title,
        kind=DRAFT_KIND_SKILL,
        status=note.trang_thai,
        vault_dir=vault_dir,
    )

    return target_md


# ==============================================================================
# 8. SKILL MANAGEMENT TOOLING (LIST, RESTORE, PIN, CONSOLIDATE)
# ==============================================================================

def list_skills(
    skills_dir: Optional[Path] = None,
    include_archived: bool = True,
    state: Optional[str] = None,
    domain: Optional[str] = None,
) -> List[SkillRecord]:
    """List all local skills with metadata, state, and pinned flag."""
    s_dir = skills_dir if skills_dir is not None else get_skills_dir()
    if not s_dir.exists():
        return []

    records: List[SkillRecord] = []

    # Active & Stale skills in main skills directory
    for item in s_dir.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            skill_md = item / "SKILL.md"
            if skill_md.exists():
                try:
                    rec = parse_skill_file(skill_md)
                    records.append(rec)
                except Exception as exc:
                    LOGGER.debug("Could not parse skill %s: %s", item.name, exc)

    # Archived skills in .archive/
    if include_archived:
        archive_dir = s_dir / ".archive"
        if archive_dir.exists():
            for item in archive_dir.iterdir():
                if item.is_dir():
                    skill_md = item / "SKILL.md"
                    if skill_md.exists():
                        try:
                            rec = parse_skill_file(skill_md)
                            rec.state = STATE_ARCHIVED
                            records.append(rec)
                        except Exception as exc:
                            LOGGER.debug("Could not parse archived skill %s: %s", item.name, exc)

    # Apply filters
    filtered: List[SkillRecord] = []
    for r in records:
        if state is not None and r.state != state:
            continue
        if domain is not None and r.mien.lower() != domain.lower():
            continue
        filtered.append(r)

    # Sort by domain then name
    filtered.sort(key=lambda x: (x.mien, x.name))
    return filtered


def get_skill(skill_name: str, skills_dir: Optional[Path] = None) -> Optional[SkillRecord]:
    """Retrieve a single skill record by name (active, stale, or archived)."""
    s_dir = skills_dir if skills_dir is not None else get_skills_dir()
    direct_md = s_dir / skill_name / "SKILL.md"
    if direct_md.exists():
        return parse_skill_file(direct_md)

    archived_md = s_dir / ".archive" / skill_name / "SKILL.md"
    if archived_md.exists():
        rec = parse_skill_file(archived_md)
        rec.state = STATE_ARCHIVED
        return rec

    return None


def pin_skill(skill_name: str, pinned: bool = True, skills_dir: Optional[Path] = None) -> SkillRecord:
    """Set or remove the pinned flag on a skill. Pinned skills bypass all pruning."""
    s_dir = skills_dir if skills_dir is not None else get_skills_dir()
    skill = get_skill(skill_name, skills_dir=s_dir)
    if not skill or not skill.path or not skill.path.exists():
        raise SkillNotFoundError(f"Skill '{skill_name}' not found.")

    skill.pinned = pinned
    skill.updated_at = now_iso()
    save_skill_to_store(skill, skills_dir=s_dir, overwrite_conflict=True)

    log_curator_ledger(
        s_dir,
        action="pin" if pinned else "unpin",
        skill_name=skill_name,
        details={"pinned": pinned},
    )
    return skill


def restore_skill_from_archive(skill_name: str, skills_dir: Optional[Path] = None) -> SkillRecord:
    """Restore a skill from .archive/ back into active circulation."""
    s_dir = skills_dir if skills_dir is not None else get_skills_dir()
    archived_dir = s_dir / ".archive" / skill_name
    if not archived_dir.exists():
        raise SkillNotFoundError(f"Archived skill '{skill_name}' not found at {archived_dir}.")

    target_dir = s_dir / skill_name
    if target_dir.exists():
        raise FileExistsError(
            f"Cannot restore '{skill_name}': destination {target_dir} already exists."
        )

    # Move directory out of .archive/
    shutil.move(str(archived_dir), str(target_dir))

    target_md = target_dir / "SKILL.md"
    rec = parse_skill_file(target_md)
    rec.state = STATE_ACTIVE
    rec.updated_at = now_iso()
    rec.last_activity_at = now_iso()
    save_skill_to_store(rec, skills_dir=s_dir, overwrite_conflict=True)

    # Update MOC
    vault_dir = get_second_brain_dir()
    update_domain_moc(
        domain=rec.mien,
        note_id=skill_name,
        title=rec.title,
        kind=DRAFT_KIND_SKILL,
        status=STATE_ACTIVE,
        vault_dir=vault_dir,
    )

    log_curator_ledger(
        s_dir,
        action="restore",
        skill_name=skill_name,
        details={"restored_to": str(target_dir)},
    )
    return rec


def record_skill_usage(skill_name: str, skills_dir: Optional[Path] = None) -> None:
    """Touch a skill's activity timestamp and increment use_count.

    Reactivates the skill if it was previously marked stale.
    """
    s_dir = skills_dir if skills_dir is not None else get_skills_dir()
    skill = get_skill(skill_name, skills_dir=s_dir)
    if not skill or not skill.path or not skill.path.exists():
        return

    skill.use_count += 1
    skill.last_activity_at = now_iso()
    skill.updated_at = now_iso()
    if skill.state == STATE_STALE:
        skill.state = STATE_ACTIVE

    save_skill_to_store(skill, skills_dir=s_dir, overwrite_conflict=True)
    log_curator_ledger(
        s_dir,
        action="use",
        skill_name=skill_name,
        details={"use_count": skill.use_count},
    )


def consolidate_skills(
    absorbed_name: str,
    target_umbrella_name: str,
    reason: str = "",
    skills_dir: Optional[Path] = None,
) -> None:
    """Merge an overly specific skill into an umbrella skill.

    Enforces Fail-Closed Guard:
    1. The target umbrella skill must exist in the active collection.
    2. The absorbed skill MUST record absorbed_into = target_umbrella_name in frontmatter.
    3. The absorbed skill is moved to .archive/ with absorbed_into pointer (never deleted).
    """
    s_dir = skills_dir if skills_dir is not None else get_skills_dir()
    target_umbrella = get_skill(target_umbrella_name, skills_dir=s_dir)
    if not target_umbrella or target_umbrella.state == STATE_ARCHIVED:
        raise SkillNotFoundError(
            f"Consolidation target umbrella skill '{target_umbrella_name}' must exist and be active."
        )

    absorbed = get_skill(absorbed_name, skills_dir=s_dir)
    if not absorbed:
        raise SkillNotFoundError(f"Absorbed skill '{absorbed_name}' not found.")

    # Update absorbed skill metadata with absorbed_into pointer
    absorbed.absorbed_into = target_umbrella_name
    absorbed.state = STATE_SUPERSEDED
    absorbed.updated_at = now_iso()
    save_skill_to_store(absorbed, skills_dir=s_dir, overwrite_conflict=True)

    # Move absorbed skill to archive
    archive_dir = s_dir / ".archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    src_dir = s_dir / absorbed_name
    dest_dir = archive_dir / absorbed_name
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    shutil.move(str(src_dir), str(dest_dir))

    # Append wikilink reference into target umbrella
    target_umbrella.links.append(f"[[{absorbed_name}]]")
    target_umbrella.updated_at = now_iso()
    ref_note = (
        f"\n\n### Đã tiếp thu kỹ năng con: [[{absorbed_name}]]\n"
        f"- **Lý do gộp**: {reason or 'Gộp kỹ năng trùng lặp / cụ thể hóa vào ô dù chung'}\n"
        f"- **Thời điểm gộp**: {now_iso()}\n"
    )
    target_umbrella.content_body += ref_note
    save_skill_to_store(target_umbrella, skills_dir=s_dir, overwrite_conflict=True)

    log_curator_ledger(
        s_dir,
        action="consolidate",
        skill_name=absorbed_name,
        details={"absorbed_into": target_umbrella_name, "reason": reason},
    )


# ==============================================================================
# 9. DETERMINISTIC PRUNING & AUTOMATIC TRANSITIONS
# ==============================================================================

def apply_automatic_transitions(
    skills_dir: Path,
    now: Optional[datetime] = None,
    stale_after_days: float = DEFAULT_STALE_AFTER_DAYS,
    archive_after_days: float = DEFAULT_ARCHIVE_AFTER_DAYS,
) -> Dict[str, Any]:
    """Execute deterministic lifecycle transitions on all local skills:

    - Pinned skills bypass all pruning.
    - Skills with created_by="user" bypass auto-archive.
    - Inactivity > stale_after_days (14d) -> state=stale.
    - Inactivity > archive_after_days (30d) -> move to .archive/ (never deleted).
    - If recent activity on a stale skill -> reactivated.
    """
    current = now or datetime.now(timezone.utc)
    stale_cutoff = current - timedelta(days=stale_after_days)
    archive_cutoff = current - timedelta(days=archive_after_days)

    counts = {
        "checked": 0,
        "marked_stale": 0,
        "archived": 0,
        "reactivated": 0,
        "pinned_bypassed": 0,
    }
    actions: List[Dict[str, Any]] = []

    if not skills_dir.exists():
        return {"counts": counts, "actions": actions}

    for item in list(skills_dir.iterdir()):
        if not item.is_dir() or item.name.startswith("."):
            continue

        skill_md = item / "SKILL.md"
        if not skill_md.exists():
            continue

        counts["checked"] += 1
        try:
            skill = parse_skill_file(skill_md)
        except Exception as exc:
            LOGGER.warning("Could not parse skill %s during pruning: %s", item.name, exc)
            continue

        # Rule 1: Pinned skills bypass all pruning
        if skill.pinned:
            counts["pinned_bypassed"] += 1
            continue

        # Rule 2: User-created skills are never auto-archived
        if skill.created_by == "user":
            continue

        # Determine anchor timestamp (latest activity or updated or created)
        anchor = _parse_iso(skill.last_activity_at) or _parse_iso(skill.updated_at) or _parse_iso(skill.created_at) or current

        # Transition logic
        if anchor <= archive_cutoff and skill.state != STATE_ARCHIVED:
            # Move to .archive/
            archive_dir = skills_dir / ".archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            dest = archive_dir / item.name
            if dest.exists():
                shutil.rmtree(dest)

            # Update state in frontmatter before moving
            skill.state = STATE_ARCHIVED
            skill.updated_at = current.isoformat()
            save_skill_to_store(skill, skills_dir=skills_dir, overwrite_conflict=True)

            shutil.move(str(item), str(dest))
            counts["archived"] += 1
            action_desc = {"skill": item.name, "action": "archived", "anchor": anchor.isoformat()}
            actions.append(action_desc)
            log_curator_ledger(skills_dir, action="auto_archive", skill_name=item.name, details=action_desc)

        elif anchor <= stale_cutoff and skill.state == STATE_ACTIVE:
            skill.state = STATE_STALE
            skill.updated_at = current.isoformat()
            save_skill_to_store(skill, skills_dir=skills_dir, overwrite_conflict=True)
            counts["marked_stale"] += 1
            action_desc = {"skill": item.name, "action": "marked_stale", "anchor": anchor.isoformat()}
            actions.append(action_desc)
            log_curator_ledger(skills_dir, action="auto_stale", skill_name=item.name, details=action_desc)

        elif anchor > stale_cutoff and skill.state == STATE_STALE:
            skill.state = STATE_ACTIVE
            skill.updated_at = current.isoformat()
            save_skill_to_store(skill, skills_dir=skills_dir, overwrite_conflict=True)
            counts["reactivated"] += 1
            action_desc = {"skill": item.name, "action": "reactivated", "anchor": anchor.isoformat()}
            actions.append(action_desc)
            log_curator_ledger(skills_dir, action="auto_reactivate", skill_name=item.name, details=action_desc)

    return {"counts": counts, "actions": actions}


# ==============================================================================
# 10. CURATOR RUN ORCHESTRATOR
# ==============================================================================

def run_curator(
    skills_dir: Optional[Path] = None,
    local_cases_dir: Optional[Path] = None,
    force: bool = False,
    dry_run: bool = False,
    now: Optional[datetime] = None,
) -> Optional[CuratorRunReport]:
    """Execute a complete Curator maintenance cycle.

    Synchronizes file-locks, validates gates, applies automatic transitions,
    updates state, and persists audit ledger.
    """
    s_dir = skills_dir if skills_dir is not None else get_skills_dir()
    l_dir = local_cases_dir if local_cases_dir is not None else get_local_cases_dir()
    current = now or datetime.now(timezone.utc)

    if not should_run_now(s_dir, local_cases_dir=l_dir, now=current, force=force):
        LOGGER.info("Curator run deferred: Gating conditions not satisfied.")
        return None

    if not claim_run_lock(s_dir):
        LOGGER.info("Curator run skipped: Another process holds the lock.")
        return None

    t_start = time.perf_counter()
    report_started = current.isoformat()
    try:
        if dry_run:
            LOGGER.info("Running curator in DRY-RUN mode.")
            report = CuratorRunReport(
                started_at=report_started,
                finished_at=now_iso(),
                duration_seconds=0.01,
                summary="Dry-run preview completed. No files modified.",
            )
            return report

        # Execute automatic transitions
        result = apply_automatic_transitions(s_dir, now=current)
        counts = result["counts"]
        actions = result["actions"]

        duration = time.perf_counter() - t_start
        summary = (
            f"Curator run completed in {duration:.2f}s: checked {counts['checked']} skills, "
            f"stale {counts['marked_stale']}, archived {counts['archived']}, "
            f"reactivated {counts['reactivated']}, pinned bypassed {counts['pinned_bypassed']}."
        )

        report = CuratorRunReport(
            started_at=report_started,
            finished_at=now_iso(),
            duration_seconds=round(duration, 3),
            checked_count=counts["checked"],
            marked_stale_count=counts["marked_stale"],
            archived_count=counts["archived"],
            reactivated_count=counts["reactivated"],
            pinned_bypassed_count=counts["pinned_bypassed"],
            summary=summary,
            actions=actions,
        )

        # Update scheduler state
        st = load_curator_state(s_dir)
        st["last_run_at"] = report_started
        st["last_run_duration_seconds"] = round(duration, 3)
        st["last_run_summary"] = summary
        st["run_count"] = int(st.get("run_count", 0)) + 1
        st["stale_count"] = counts["marked_stale"]
        st["archived_count"] = counts["archived"]
        st["reactivated_count"] = counts["reactivated"]
        save_curator_state(s_dir, st)

        return report
    finally:
        release_run_lock(s_dir)


def maybe_run_curator(
    skills_dir: Optional[Path] = None,
    local_cases_dir: Optional[Path] = None,
    idle_for_seconds: Optional[float] = None,
) -> Optional[CuratorRunReport]:
    """Safe, non-blocking entry point called from background loops or turn hooks."""
    try:
        s_dir = skills_dir if skills_dir is not None else get_skills_dir()
        l_dir = local_cases_dir if local_cases_dir is not None else get_local_cases_dir()
        if not should_run_now(s_dir, local_cases_dir=l_dir, idle_for_seconds=idle_for_seconds):
            return None
        return run_curator(skills_dir=s_dir, local_cases_dir=l_dir, force=False)
    except Exception as exc:
        LOGGER.debug("maybe_run_curator failed safely: %s", exc)
        return None


# ==============================================================================
# 11. SECOND BRAIN HABIT JOURNAL & OBSIDIAN VAULT INTEGRATION
# ==============================================================================

def setup_obsidian_vault(
    vault_dir: Path,
    skills_dir: Optional[Path] = None,
) -> None:
    """Prepare an Obsidian-compatible vault structure with .obsidian configuration."""
    vault_dir.mkdir(parents=True, exist_ok=True)
    obsidian_conf = vault_dir / ".obsidian"
    obsidian_conf.mkdir(parents=True, exist_ok=True)

    # Core Obsidian configuration
    app_json = obsidian_conf / "app.json"
    if not app_json.exists():
        app_json.write_text(
            json.dumps(
                {
                    "useMarkdownLinks": False,
                    "newFileLocation": "current",
                    "showLineNumber": True,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    graph_json = obsidian_conf / "graph.json"
    if not graph_json.exists():
        graph_json.write_text(
            json.dumps(
                {
                    "collapse-filter": False,
                    "search": "",
                    "showTags": True,
                    "showAttachments": False,
                    "hideUnresolved": False,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    # Link skills directory into vault if external
    s_dir = skills_dir if skills_dir is not None else get_skills_dir()
    vault_skills = vault_dir / "skills"
    if not vault_skills.exists() and s_dir.exists():
        # Attempt directory junction or directory symlink on Windows
        try:
            if sys.platform == "win32":
                import subprocess
                subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(vault_skills), str(s_dir.resolve())],
                    capture_output=True,
                    check=False,
                )
        except Exception:
            pass


def sync_all_domain_mocs(
    vault_dir: Path,
    skills_dir: Path,
) -> List[Path]:
    """Scan all atomic lessons and skills and regenerate domain MOC index pages."""
    vault_dir.mkdir(parents=True, exist_ok=True)
    lessons_dir = vault_dir / "lessons"

    # Group notes and skills by domain
    domain_skills: Dict[str, List[SkillRecord]] = {}
    domain_lessons: Dict[str, List[SecondBrainNote]] = {}

    all_domains = {"lsu", "dieutraloi", "mom_opcenter", "general"}

    # Gather skills
    for sk in list_skills(skills_dir=skills_dir, include_archived=True):
        m = (sk.mien or "general").strip().lower()
        all_domains.add(m)
        domain_skills.setdefault(m, []).append(sk)

    # Gather lessons
    if lessons_dir.exists():
        for f in lessons_dir.glob("*.md"):
            try:
                note = SecondBrainNote.from_markdown(f.read_text(encoding="utf-8"))
                m = (note.mien or "general").strip().lower()
                all_domains.add(m)
                domain_lessons.setdefault(m, []).append(note)
            except Exception:
                pass

    updated_mocs: List[Path] = []
    for d in sorted(all_domains):
        moc_path = vault_dir / f"{d}_MOC.md"
        skills_in_d = domain_skills.get(d, [])
        lessons_in_d = domain_lessons.get(d, [])

        skill_lines = [
            f"- [[{s.name}]]: {s.title} ({s.state})" for s in skills_in_d
        ] or ["*(Chưa có kỹ năng)*"]

        lesson_lines = [
            f"- [[{l.id}]]: {l.title} ({l.trang_thai})" for l in lessons_in_d
        ] or ["*(Chưa có bài học)*"]

        content = f"""---
id: MOC-{d.upper()}
title: Mục lục Tri thức & Kỹ năng Miền {d.upper()}
kind: moc
mien: {d}
updated: {now_iso()}
partition: local_habit
---

# Mục lục Miền {d.upper()}

## Danh sách Kỹ năng (Skills)
{chr(10).join(skill_lines)}

## Danh sách Bài học (Lessons)
{chr(10).join(lesson_lines)}
"""
        moc_path.write_text(content, encoding="utf-8")
        updated_mocs.append(moc_path)

    return updated_mocs


# ==============================================================================
# 12. LEGACY DATA MIGRATION ENGINE
# ==============================================================================

def migrate_legacy_data(local_cases_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Map and migrate legacy memory_decisions.jsonl and learning_cards.jsonl

    into Second Brain atomic notes in local_cases/second_brain/lessons/.
    Maintains count verification before and after migration.
    """
    base = local_cases_dir if local_cases_dir is not None else get_local_cases_dir()
    vault_dir = get_second_brain_dir(root=base)
    lessons_dir = vault_dir / "lessons"
    wm_lessons_dir = base / "workspace_memory" / "lessons"

    lessons_dir.mkdir(parents=True, exist_ok=True)
    wm_lessons_dir.mkdir(parents=True, exist_ok=True)
    setup_obsidian_vault(vault_dir, skills_dir=base / "skills")

    input_decisions_count = 0
    input_cards_count = 0
    migrated_notes: List[SecondBrainNote] = []

    # 1. Migrate memory_decisions.jsonl
    decisions_file = base / "workspace_memory" / "memory_decisions.jsonl"
    if decisions_file.exists():
        for line in decisions_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            input_decisions_count += 1
            try:
                row = json.loads(line)
                dec_id = str(row.get("decision_id") or f"dec_{uuid_short()}")
                mem_id = str(row.get("memory_id") or "")
                statement = str(row.get("statement") or row.get("title") or "")
                scope = str(row.get("scope") or "general")
                domain = "general"
                if "workspace:" in scope:
                    domain = scope.split("workspace:", 1)[1].strip()

                note_id = f"LESSON-{dec_id.upper()}"
                title = str(row.get("title") or statement)
                created = str(row.get("created_at") or now_iso())
                links = [f"[[{domain.lower()}_MOC]]"]
                if mem_id:
                    links.append(f"[[{mem_id}]]")

                body = f"""# {title}

## Quy tắc áp dụng
{statement}

## Bối cảnh & Phạm vi
- **Phạm vi**: {scope}
- **Quyết định gốc**: `{dec_id}`
- **Hành động**: `{row.get('action') or 'confirm'}`

## Liên kết
- [[{domain.lower()}_MOC]]
"""
                note = SecondBrainNote(
                    id=note_id,
                    title=title,
                    kind=DRAFT_KIND_LESSON,
                    created=created,
                    updated=created,
                    mien=domain,
                    applies_when=str(row.get("applies_when") or f"Khi làm việc trong phạm vi {scope}"),
                    does_not_apply_when=str(row.get("does_not_apply_when") or ""),
                    trang_thai=STATE_CONFIRMED if row.get("action") == "confirm" else STATE_DRAFT,
                    evidence_refs=list(row.get("evidence_refs") or ["user_confirm"]),
                    partition=PARTITION_LOCAL_HABIT,
                    links=links,
                    content_body=body,
                    supersedes=row.get("supersedes_decision_id"),
                )
                migrated_notes.append(note)
            except Exception as exc:
                LOGGER.warning("Error parsing legacy memory decision: %s", exc)

    # 2. Migrate learning_cards.jsonl
    cards_file = base / "learning_cards.jsonl"
    if cards_file.exists():
        for line in cards_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            input_cards_count += 1
            try:
                row = json.loads(line)
                learning_id = str(row.get("learning_id") or f"LRN-{uuid_short()}")
                case_id = str(row.get("case_id") or "")
                symptoms = str(row.get("symptoms") or "")
                reusable_lesson = str(row.get("reusable_lesson") or row.get("true_cause") or "")
                title = reusable_lesson[:80] if reusable_lesson else f"Bài học ca {case_id or learning_id}"

                # Infer domain from case or symptoms
                domain = "general"
                text_combined = f"{symptoms} {case_id} {row.get('related_systems', '')}".lower()
                if "lsu" in text_combined:
                    domain = "lsu"
                elif "mom" in text_combined or "opcenter" in text_combined or "mes" in text_combined:
                    domain = "mom_opcenter"
                elif "loi" in text_combined or "dieutra" in text_combined or "4m" in text_combined:
                    domain = "dieutraloi"

                note_id = f"LESSON-{learning_id.replace(':', '_').upper()}"
                links = [f"[[{domain.lower()}_MOC]]"]
                if case_id:
                    links.append(f"[[{case_id}]]")

                body = f"""# {title}

## Hiện tượng & Triệu chứng
{symptoms or 'Không ghi nhận triệu chứng chi tiết.'}

## Nguyên nhân gốc & Bài học
- **Nguyên nhân**: {row.get('true_cause') or 'Chưa xác định'}
- **Bài học rút ra**: {reusable_lesson}
- **Kiểm tra trước tiên lần sau**: {row.get('check_first_next_time') or 'Kiểm tra quy trình chuẩn'}

## Bằng chứng & Ca gốc
- **Ca gốc**: [[{case_id}]]
- **Bằng chứng xác thực**: {row.get('verification_evidence') or 'Kiểm chứng thực tế'}

## Liên kết
- [[{domain.lower()}_MOC]]
"""
                note = SecondBrainNote(
                    id=note_id,
                    title=title,
                    kind=DRAFT_KIND_LESSON,
                    created=str(row.get("created_at") or now_iso()),
                    updated=str(row.get("updated_at") or now_iso()),
                    mien=domain,
                    applies_when=str(row.get("applies_when") or f"Khi gặp triệu chứng tương tự ca {case_id}"),
                    does_not_apply_when=str(row.get("does_not_apply_when") or ""),
                    trang_thai=STATE_CONFIRMED if row.get("confidence") in ("high", "confirmed") else STATE_DRAFT,
                    evidence_refs=[case_id] if case_id else [],
                    partition=PARTITION_LOCAL_HABIT,
                    links=links,
                    content_body=body,
                )
                migrated_notes.append(note)
            except Exception as exc:
                LOGGER.warning("Error parsing legacy learning card: %s", exc)

    # Save all migrated notes
    saved_count = 0
    for n in migrated_notes:
        target_path = lessons_dir / f"{n.id}.md"
        target_path.write_text(n.to_markdown(), encoding="utf-8")
        # Mirror to workspace_memory/lessons
        wm_target = wm_lessons_dir / f"{n.id}.md"
        wm_target.write_text(n.to_markdown(), encoding="utf-8")
        saved_count += 1

    # Regenerate MOCs
    sync_all_domain_mocs(vault_dir, skills_dir=base / "skills")

    return {
        "input_decisions_count": input_decisions_count,
        "input_cards_count": input_cards_count,
        "total_inputs": input_decisions_count + input_cards_count,
        "migrated_lessons_saved": saved_count,
        "vault_path": str(vault_dir),
    }


# ==============================================================================
# 13. FAST SECOND BRAIN RECALL ENGINE
# ==============================================================================

class SecondBrainRecallEngine:
    """Indexed recall engine traversing supersede chains and domain metadata."""

    def __init__(self, vault_dir: Optional[Path] = None):
        self.vault_dir = vault_dir if vault_dir is not None else get_second_brain_dir()
        self._cache: Dict[str, SecondBrainNote] = {}
        self._mtime_map: Dict[str, float] = {}

    def refresh(self) -> None:
        """Scan lessons and refresh cache based on file mtimes."""
        lessons_dir = self.vault_dir / "lessons"
        if not lessons_dir.exists():
            return

        current_files = set()
        for f in lessons_dir.glob("*.md"):
            current_files.add(f.name)
            try:
                mt = f.stat().st_mtime
                if f.name not in self._mtime_map or self._mtime_map[f.name] < mt:
                    note = SecondBrainNote.from_markdown(f.read_text(encoding="utf-8"))
                    self._cache[note.id] = note
                    self._mtime_map[f.name] = mt
            except Exception:
                pass

        # Remove deleted
        to_del = [k for k in self._mtime_map if k not in current_files]
        for k in to_del:
            self._mtime_map.pop(k, None)

    def resolve_active_note(self, note_id: str) -> Optional[SecondBrainNote]:
        """Traverse supersede chain to return the newest active note."""
        self.refresh()
        visited: Set[str] = set()
        curr_id = note_id

        while curr_id and curr_id not in visited:
            visited.add(curr_id)
            note = self._cache.get(curr_id)
            if not note:
                break
            if note.superseded_by and note.superseded_by in self._cache:
                curr_id = note.superseded_by
            else:
                return note
        return self._cache.get(note_id)

    def recall_notes(
        self,
        domain: str = "",
        query: str = "",
        limit: int = 5,
    ) -> List[SecondBrainNote]:
        """Query active confirmed lessons matching domain and search terms."""
        self.refresh()
        matches: List[Tuple[float, SecondBrainNote]] = []
        q_tokens = set(re.findall(r"\w+", query.lower()))

        for note_id, note in self.cache_items():
            if note.trang_thai == STATE_SUPERSEDED:
                continue

            # Negative filter: does_not_apply_when
            if note.does_not_apply_when:
                neg_tokens = set(re.findall(r"\w+", note.does_not_apply_when.lower()))
                if neg_tokens and neg_tokens.issubset(q_tokens):
                    continue

            score = 0.0
            # Domain match
            if domain and note.mien.lower() == domain.lower():
                score += 5.0

            # Title & applies_when match
            note_tokens = set(re.findall(r"\w+", f"{note.title} {note.applies_when} {note.content_body}".lower()))
            overlap = len(q_tokens & note_tokens)
            score += float(overlap)

            if score > 0.0 or not query:
                matches.append((score, note))

        matches.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in matches[:limit]]

    def cache_items(self) -> List[Tuple[str, SecondBrainNote]]:
        return list(self._cache.items())


# ==============================================================================
# 14. CLI ENTRY POINT
# ==============================================================================

def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line interface for the Curator."""
    import argparse

    parser = argparse.ArgumentParser(description="AIOS Habit Skills Curator & Second Brain Store")
    subparsers = parser.add_subparsers(dest="subcommand", help="Curator actions")

    # list
    p_list = subparsers.add_parser("list", help="List local skills")
    p_list.add_argument("--domain", type=str, default=None, help="Filter by domain")
    p_list.add_argument("--state", type=str, default=None, help="Filter by state (active/stale/archived)")
    p_list.add_argument("--no-archived", action="store_true", help="Exclude archived skills")

    # status
    subparsers.add_parser("status", help="Show curator scheduler state")

    # run
    p_run = subparsers.add_parser("run", help="Trigger a curator maintenance run")
    p_run.add_argument("--force", action="store_true", help="Bypass inactivity and interval gates")
    p_run.add_argument("--dry-run", action="store_true", help="Report actions without modifying files")

    # restore
    p_restore = subparsers.add_parser("restore", help="Restore a skill from .archive/")
    p_restore.add_argument("skill_name", type=str, help="Name of the skill to restore")

    # pin
    p_pin = subparsers.add_parser("pin", help="Pin or unpin a skill")
    p_pin.add_argument("skill_name", type=str, help="Name of the skill")
    p_pin.add_argument("--unpin", action="store_true", help="Unpin the skill")

    # consolidate
    p_cons = subparsers.add_parser("consolidate", help="Consolidate an absorbed skill into an umbrella")
    p_cons.add_argument("absorbed_name", type=str, help="Skill to absorb")
    p_cons.add_argument("umbrella_name", type=str, help="Target umbrella skill")
    p_cons.add_argument("--reason", type=str, default="", help="Reason for consolidation")

    # migrate
    subparsers.add_parser("migrate", help="Migrate legacy data to Second Brain vault")

    args = parser.parse_args(argv)

    skills_dir = get_skills_dir()
    if args.subcommand == "list":
        skills = list_skills(
            skills_dir=skills_dir,
            include_archived=not args.no_archived,
            state=args.state,
            domain=args.domain,
        )
        print(f"Total skills found: {len(skills)}")
        for s in skills:
            pin_mark = "[PINNED]" if s.pinned else "        "
            print(f"- {s.name:<32} | {s.mien:<12} | {s.state:<8} | {pin_mark} | uses: {s.use_count}")
        return 0

    elif args.subcommand == "status":
        state = load_curator_state(skills_dir)
        print(json.dumps(state, indent=2, ensure_ascii=False))
        return 0

    elif args.subcommand == "run":
        report = run_curator(skills_dir=skills_dir, force=args.force, dry_run=args.dry_run)
        if report:
            print(report.summary)
        else:
            print("Curator run skipped (conditions not met; use --force to override).")
        return 0

    elif args.subcommand == "restore":
        try:
            rec = restore_skill_from_archive(args.skill_name, skills_dir=skills_dir)
            print(f"Successfully restored skill '{rec.name}' ({rec.title}) to active library.")
            return 0
        except Exception as exc:
            print(f"Error restoring skill: {exc}")
            return 1

    elif args.subcommand == "pin":
        try:
            rec = pin_skill(args.skill_name, pinned=not args.unpin, skills_dir=skills_dir)
            status = "pinned" if rec.pinned else "unpinned"
            print(f"Skill '{rec.name}' is now {status}.")
            return 0
        except Exception as exc:
            print(f"Error pinning skill: {exc}")
            return 1

    elif args.subcommand == "consolidate":
        try:
            consolidate_skills(
                absorbed_name=args.absorbed_name,
                target_umbrella_name=args.umbrella_name,
                reason=args.reason,
                skills_dir=skills_dir,
            )
            print(f"Successfully consolidated '{args.absorbed_name}' into umbrella '{args.umbrella_name}'.")
            return 0
        except Exception as exc:
            print(f"Error consolidating skills: {exc}")
            return 1

    elif args.subcommand == "migrate":
        summary = migrate_legacy_data()
        print("Migration completed:")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
