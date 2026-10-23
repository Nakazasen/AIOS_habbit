"""Hermes Skills Curator & Lifecycle Manager - Ported directly from Hermes Agent.

Original Hermes files:
- agent/curator.py (v0.21.6+724)
- tools/skill_usage.py (v0.21.6+724)

Port Classification: PORT CÓ SỬA MỐI NỐI (SEAMS)
Seam modifications:
1. Skills directory resolves to local_cases/skills (honors AIOS_LOCAL_CASES_DIR).
2. Telemetry saved to local_cases/skills/.usage.json and scheduler state in .curator_state.
3. Archive directory is local_cases/skills/.archive/.
4. Standalone file locking with msvcrt (Windows) / fcntl (Unix).
5. Preserves 100% of Hermes lifecycle semantics:
   - 14 days inactivity -> stale.
   - 30 days inactivity -> archived (moved to .archive/).
   - Pinned skills (pinned=True) are strictly exempt from all automatic pruning and archiving.
   - Reactivation: stale skill used again transitions back to active.
"""

from __future__ import annotations

from contextlib import suppress
from datetime import datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
import shutil
import time
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple

from aios_habit.hermes_memory import atomic_write_text, file_lock, get_default_local_cases_dir
from aios_habit.hermes_skill_manager import get_skills_dir, parse_frontmatter

logger = logging.getLogger("aios_habit.hermes_curator")

UTC = timezone.utc

# ==============================================================================
# HERMES CURATOR DEFAULTS & CONSTANTS (VERBATIM)
# ==============================================================================

STATE_ACTIVE = "active"
STATE_STALE = "stale"
STATE_ARCHIVED = "archived"
VALID_STATES = {STATE_ACTIVE, STATE_STALE, STATE_ARCHIVED}

DEFAULT_INTERVAL_HOURS: int = 24 * 7  # 7 days
DEFAULT_MIN_IDLE_HOURS: float = 2.0    # 2 hours
DEFAULT_STALE_AFTER_DAYS: int = 14     # 14 days
DEFAULT_ARCHIVE_AFTER_DAYS: int = 30   # 30 days


def _usage_file() -> Path:
    return get_skills_dir() / ".usage.json"


def _state_file() -> Path:
    return get_skills_dir() / ".curator_state"


def _archive_dir() -> Path:
    return get_skills_dir() / ".archive"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except Exception:
        return None


# ==============================================================================
# USAGE TELEMETRY & PERSISTENCE (.usage.json)
# ==============================================================================

def _empty_record() -> dict[str, Any]:
    return {
        "created_by": "agent",
        "use_count": 0,
        "view_count": 0,
        "last_used_at": None,
        "last_viewed_at": None,
        "patch_count": 0,
        "last_patched_at": None,
        "created_at": _now_iso(),
        "state": STATE_ACTIVE,
        "pinned": False,
        "archived_at": None,
    }


def load_usage() -> dict[str, dict[str, Any]]:
    path = _usage_file()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as e:
        logger.debug("Failed to read usage file %s: %s", path, e)
        return {}


def save_usage(data: dict[str, dict[str, Any]]) -> None:
    path = _usage_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.parent / f".usage_{int(time.time() * 1000)}.tmp"
    try:
        temp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            with suppress(OSError):
                temp_path.unlink()


def _mutate_usage(skill_name: str, mutator_fn: Callable[[dict[str, Any]], Any]) -> Any:
    with file_lock(_usage_file()):
        data = load_usage()
        rec = data.setdefault(skill_name, _empty_record())
        result = mutator_fn(rec)
        save_usage(data)
        return result


def record_skill_usage(skill_name: str) -> None:
    """Increment use_count and bump last_used_at timestamp."""
    def _apply(rec: dict[str, Any]):
        rec["use_count"] = int(rec.get("use_count", 0)) + 1
        rec["last_used_at"] = _now_iso()
        if rec.get("state") == STATE_STALE:
            rec["state"] = STATE_ACTIVE
    _mutate_usage(skill_name, _apply)


def mark_agent_created(skill_name: str) -> None:
    def _apply(rec: dict[str, Any]):
        rec["created_by"] = "agent"
    _mutate_usage(skill_name, _apply)


def set_state(skill_name: str, state: str) -> None:
    if state not in VALID_STATES:
        return

    def _apply(rec: dict[str, Any]):
        rec["state"] = state
        if state == STATE_ARCHIVED:
            rec["archived_at"] = _now_iso()
        elif state == STATE_ACTIVE:
            rec["archived_at"] = None
    _mutate_usage(skill_name, _apply)


def set_pinned(skill_name: str, pinned: bool) -> bool:
    """Pin or unpin a skill. Pinned skills are never stale or archived."""
    def _apply(rec: dict[str, Any]):
        rec["pinned"] = bool(pinned)
    _mutate_usage(skill_name, _apply)
    return True


def is_pinned(skill_name: str) -> bool:
    usage = load_usage()
    return bool(usage.get(skill_name, {}).get("pinned", False))


# ==============================================================================
# ARCHIVE & RESTORE (VERBATIM HERMES)
# ==============================================================================

def archive_skill(skill_name: str) -> tuple[bool, str]:
    """Move a skill directory to .archive/."""
    from aios_habit.hermes_skill_manager import find_skill
    found = find_skill(skill_name)
    if not found:
        return False, f"skill '{skill_name}' not found"

    skill_dir = found["path"]
    archive_root = _archive_dir()
    archive_root.mkdir(parents=True, exist_ok=True)
    dest = archive_root / skill_name
    if dest.exists():
        dest = dest.with_name(f"{skill_name}-{int(time.time())}")

    try:
        shutil.move(str(skill_dir), str(dest))
    except Exception as e:
        return False, f"failed to archive: {e}"

    set_state(skill_name, STATE_ARCHIVED)
    return True, f"archived to {dest}"


def restore_skill(skill_name: str) -> tuple[bool, str]:
    """Restore an archived skill back to local_cases/skills/."""
    archive_root = _archive_dir()
    archived_dir = archive_root / skill_name
    if not archived_dir.exists():
        # Check timestamped variants
        candidates = list(archive_root.glob(f"{skill_name}-*"))
        if candidates:
            archived_dir = sorted(candidates)[-1]
        else:
            return False, f"archived skill '{skill_name}' not found in {archive_root}"

    dest = get_skills_dir() / skill_name
    try:
        shutil.move(str(archived_dir), str(dest))
    except Exception as e:
        return False, f"failed to restore: {e}"

    set_state(skill_name, STATE_ACTIVE)
    return True, f"restored to {dest}"


# ==============================================================================
# CURATOR REPORT & STATE (.curator_state)
# ==============================================================================

def curated_report() -> list[dict[str, Any]]:
    """Scan all skills and produce rows with telemetry for curation decisions."""
    root = get_skills_dir()
    usage = load_usage()
    report: list[dict[str, Any]] = []

    if not root.exists():
        return report

    for skill_md in root.rglob("SKILL.md"):
        parts = skill_md.parts
        if any(p in {".git", ".archive", ".locks", "node_modules"} for p in parts):
            continue
        try:
            fm, _ = parse_frontmatter(skill_md.read_text(encoding="utf-8-sig")[:4000])
        except Exception:
            fm = {}
        name = fm.get("name") or skill_md.parent.name
        rec = usage.get(name, {})
        report.append({
            "name": name,
            "path": skill_md.parent,
            "state": rec.get("state", STATE_ACTIVE),
            "pinned": bool(rec.get("pinned", False)),
            "use_count": int(rec.get("use_count", 0)),
            "created_at": rec.get("created_at"),
            "last_used_at": rec.get("last_used_at"),
            "last_patched_at": rec.get("last_patched_at"),
            "last_activity_at": rec.get("last_activity_at") or rec.get("last_used_at") or rec.get("last_patched_at") or rec.get("created_at"),
            "created_by": rec.get("created_by", "agent"),
            "_persisted": name in usage,
        })
    return report


def load_state() -> dict[str, Any]:
    base: dict[str, Any] = {
        "last_run_at": None,
        "last_run_duration_seconds": None,
        "last_run_summary": None,
        "paused": False,
        "run_count": 0,
    }
    path = _state_file()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                base.update(data)
        except Exception:
            pass
    return base


def save_state(data: dict[str, Any]) -> None:
    path = _state_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        atomic_write_text(path, json.dumps(data, indent=2, sort_keys=True))
    except Exception as e:
        logger.debug("Failed to save curator state: %s", e)


def set_paused(paused: bool) -> None:
    state = load_state()
    state["paused"] = bool(paused)
    save_state(state)


def is_paused() -> bool:
    return bool(load_state().get("paused", False))


def should_run_now(now: Optional[datetime] = None) -> bool:
    if is_paused():
        return False
    state = load_state()
    last = _parse_iso(state.get("last_run_at"))
    now = now or datetime.now(UTC)
    if last is None:
        state["last_run_at"] = now.isoformat()
        state["last_run_summary"] = "seeded curator first run"
        save_state(state)
        return False
    return (now - last) >= timedelta(hours=DEFAULT_INTERVAL_HOURS)


# ==============================================================================
# AUTOMATIC STATE TRANSITIONS (VERBATIM HERMES LOGIC)
# ==============================================================================

def apply_automatic_transitions(
    now: Optional[datetime] = None,
    stale_after_days: int = DEFAULT_STALE_AFTER_DAYS,
    archive_after_days: int = DEFAULT_ARCHIVE_AFTER_DAYS,
) -> dict[str, int]:
    """Execute deterministic lifecycle state transitions.
    1. Active -> Stale when inactive > stale_after_days (14d).
    2. Stale -> Archived when inactive > archive_after_days (30d).
    3. Stale -> Active (reactivated) if used again.
    4. Pinned skills (pinned=True) are strictly EXEMPT from all transitions.
    """
    now = now or datetime.now(UTC)
    stale_cutoff = now - timedelta(days=stale_after_days)
    archive_cutoff = now - timedelta(days=archive_after_days)

    counts = {"marked_stale": 0, "archived": 0, "reactivated": 0, "checked": 0, "seeded": 0}

    for row in curated_report():
        counts["checked"] += 1
        name = row["name"]

        # HERMES INVARIANT: Pinned skills bypass all pruning cycles!
        if row.get("pinned"):
            continue

        if not row.get("_persisted", True):
            _mutate_usage(name, lambda r: r)
            counts["seeded"] += 1
            continue

        anchor = _parse_iso(row.get("last_activity_at")) or _parse_iso(row.get("created_at")) or now
        current = row.get("state", STATE_ACTIVE)

        # Never-used skill younger than stale_cutoff is protected
        if int(row.get("use_count", 0)) == 0 and anchor > stale_cutoff:
            if current == STATE_STALE:
                set_state(name, STATE_ACTIVE)
                counts["reactivated"] += 1
            continue

        if anchor <= archive_cutoff and current != STATE_ARCHIVED:
            ok, _ = archive_skill(name)
            if ok:
                counts["archived"] += 1
        elif anchor <= stale_cutoff and current == STATE_ACTIVE:
            set_state(name, STATE_STALE)
            counts["marked_stale"] += 1
        elif anchor > stale_cutoff and current == STATE_STALE:
            set_state(name, STATE_ACTIVE)
            counts["reactivated"] += 1

    return counts
