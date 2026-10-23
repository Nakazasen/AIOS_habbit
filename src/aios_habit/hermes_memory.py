"""Hermes MemoryStore & Memory Tool - Ported directly from Hermes Agent.

Original Hermes files:
- tools/memory_tool_store.py (v0.21.6+724)
- tools/memory_tool.py (v0.21.6+724)

Port Classification: PORT CÓ SỬA MỐI NỐI (SEAMS)
Seam modifications:
1. get_memory_dir() resolves to local_cases/memories (honors AIOS_LOCAL_CASES_DIR).
2. Standalone atomic_write_text and file locking via msvcrt (Windows) / fcntl (Unix).
3. Self-contained threat pattern scan without hermes_cli or gateway runtime dependency.
4. Preserves 100% of Hermes data structures, ENTRY_DELIMITER ("\\n§\\n"), character budget checks,
   atomic batch operations, typography-folded matching, and external drift protection.
"""

from __future__ import annotations

import copy
from contextlib import contextmanager, suppress
from contextvars import ContextVar
import json
import logging
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("aios_habit.hermes_memory")

# Platform file locking: msvcrt on Windows, fcntl on Unix
msvcrt = None
fcntl = None
try:
    import msvcrt
except ImportError:
    try:
        import fcntl
    except ImportError:
        pass

# ==============================================================================
# HERMES DELIMITER & HEADERS (VERBATIM FROM HERMES AGENT)
# ==============================================================================

ENTRY_DELIMITER = "\n§\n"

MEMORY_BLOCK_HEADERS = {
    "memory": "MEMORY (your personal notes)",
    "user": "USER PROFILE (who the user is)",
}

DEFAULT_MEMORY_CHAR_LIMIT = 2200
DEFAULT_USER_CHAR_LIMIT = 1375

FAILURE_CLASS: ContextVar[str] = ContextVar("memory_failure_class", default="other")


def get_default_local_cases_dir() -> Path:
    """Resolve AIOS local_cases directory respecting environment overrides."""
    override = os.environ.get("AIOS_LOCAL_CASES_DIR")
    if override:
        return Path(override)
    return Path.cwd() / "local_cases"


def get_memory_dir() -> Path:
    """Profile-scoped memories directory inside local_cases/memories."""
    return get_default_local_cases_dir() / "memories"


# ==============================================================================
# ATOMIC WRITE & FILE LOCK (STANDALONE SEAM)
# ==============================================================================

def atomic_write_text(path: Path, text: str, encoding: str = "utf-8", tmp_prefix: str = ".mem_") -> None:
    """Atomic write via temporary file in same folder and replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.parent / f"{tmp_prefix}{path.name}.{os.getpid()}.{int(time.time() * 1000)}.tmp"
    try:
        temp_path.write_text(text, encoding=encoding)
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            with suppress(OSError):
                temp_path.unlink()


@contextmanager
def file_lock(path: Path):
    """Cross-process exclusive file lock for Windows (msvcrt) & Unix (fcntl)."""
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if fcntl is None and msvcrt is None:
        yield
        return

    flags = os.O_RDWR | os.O_CREAT
    raw_fd = os.open(lock_path, flags, 0o600)
    try:
        fd = os.fdopen(raw_fd, "r+", encoding="utf-8")
    except Exception:
        os.close(raw_fd)
        raise

    with fd:
        def _flock(unlock: bool):
            if fcntl:
                fcntl.flock(fd, fcntl.LOCK_UN if unlock else fcntl.LOCK_EX)
            elif msvcrt:
                fd.seek(0)
                msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK if unlock else msvcrt.LK_LOCK, 1)

        _flock(False)
        try:
            yield
        finally:
            with suppress(OSError):
                _flock(True)


# ==============================================================================
# CONTENT SAFETY & ERROR HELPERS (VERBATIM HERMES SEMANTICS)
# ==============================================================================

# Simple threat scan for prompt injection / exfiltration patterns
_SUSPICIOUS_PATTERNS = [
    re.compile(r"ignore\s+all\s+(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a\s+different\s+ai", re.IGNORECASE),
    re.compile(r"<script[\s>]", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
]


def _scan_memory_content(content: str) -> Optional[str]:
    """Scan memory entry for dangerous injection patterns before writing."""
    for pattern in _SUSPICIOUS_PATTERNS:
        if pattern.search(content):
            return "Content blocked: contains disallowed pattern."
    return None


def _error(message: str, failure_class: str, **extra) -> dict[str, Any]:
    FAILURE_CLASS.set(failure_class)
    return {"success": False, "error": message, **extra}


def _drift_error(path: Path, bak_path: str) -> dict[str, Any]:
    """External drift: the file wouldn't round-trip, so flushing would discard content."""
    return _error(
        (
            f"Refusing to write {path.name}: it holds an entry larger than the whole store's char limit, "
            f"i.e. free-form text written without § delimiters (the patch tool, a shell append, a manual "
            f"edit). Rewriting it would lose that text. A snapshot was saved to {bak_path}. Resolve the drift first — "
            f"either rewrite the file as a clean §-delimited list of entries, or move the extra "
            f"content out — then retry. This guard exists to prevent silent data loss (issue #26045)."
        ),
        "drift",
        drift_backup=bak_path,
        remediation=(
            "Open the .bak file, integrate the missing entries into the memory tool one at a time via "
            "memory(action=add, content=...), then remove or rewrite the original file to a clean state."
        ),
    )


def _read_failed_error(path: Path) -> dict[str, Any]:
    """Existing-but-unreadable file: saving from an assumed-empty view would wipe it."""
    return _error(
        f"Refusing to write {path.name}: the file exists on disk but could not be read right now "
        f"(temporarily locked by another program, a permission change, invalid/corrupt text encoding, "
        f"or a filesystem error). Treating an unreadable file as empty and saving would wipe existing "
        f"memory, so the write is refused. Nothing was changed — retry in a moment.",
        "read_failed",
    )


# Typography folding for match tolerance (Heremes verbatim)
_MATCH_FOLD = str.maketrans(
    {
        **dict.fromkeys("\"`\u2018\u2019\u201a\u201b\u201c\u201d\u201e\u201f", "'"),
        **dict.fromkeys("\u2010\u2011\u2012\u2013\u2014\u2015\u2212", "-"),
    }
)


def _normalize_for_match(text: str) -> str:
    """Quote/dash/whitespace-folded form for tolerant old_text matching."""
    return " ".join(str(text).replace("\\n", " ").translate(_MATCH_FOLD).split())


def _substring_matches(entries: list[str], old_text: str) -> list[int]:
    """Indices of entries containing old_text: byte-exact first, else typography-folded."""
    if exact := [i for i, e in enumerate(entries) if old_text in e]:
        return exact
    needle = _normalize_for_match(old_text)
    if not any(c.isalnum() for c in needle):
        return []
    return [i for i, e in enumerate(entries) if needle in _normalize_for_match(e)]


def _find_unique_match(entries: list[str], old_text: str) -> tuple[Optional[int], bool]:
    """(index, ambiguous) for entries matching old_text."""
    exact = [i for i, e in enumerate(entries) if e == old_text]
    matches = exact or _substring_matches(entries, old_text)
    if len({entries[i] for i in matches}) > 1:
        return None, True
    return (matches[0] if matches else None), False


def _no_match_error(entries: list[str], old_text: str, verb: str, **extra) -> dict[str, Any]:
    """Zero-match error naming the closest entries."""
    def _words(text: str) -> set[str]:
        return set(re.findall(r"\w+", text.lower()))

    words = _words(old_text)
    scored = sorted(
        ((len(words & _words(e)) / len(words), i) for i, e in enumerate(entries)) if words else [],
        key=lambda p: (-p[0], p[1]),
    )
    closest = [entries[i] for score, i in scored[:3] if score >= 0.3]
    hint = (
        " old_text must come from ONE entry ('§' separates entries); use one op per entry."
        if "§" in old_text
        else ""
    )
    return _error(
        f"No entry matched '{old_text}'.{hint} Retry the {verb} with old_text copied verbatim "
        f"from the intended entry" + (" (closest_entries below)." if closest else "."),
        "no_match",
        **({"closest_entries": closest} if closest else {}),
        **extra,
    )


def _over_limit(new_total: int, limit: int) -> str:
    return f"would put memory at {new_total:,}/{limit:,} chars: free at least {new_total - limit:,} chars"


def _pinned_index(entries: list[str], matched_entry: str) -> Optional[int]:
    """Index of the exact entry a staged write was reviewed against."""
    return entries.index(matched_entry) if matched_entry in entries else None


def _stale_entry_message(entry: str) -> str:
    return (
        f"Entry changed since it was staged, so this write was not applied: '{entry}' is no longer "
        f"in memory as reviewed. Recreate the change against the current entry or reject it; the "
        f"pending record has been preserved."
    )


# ==============================================================================
# MEMORY STORE (PORT NGUYÊN BẢN CƠ CHẾ HERMES)
# ==============================================================================

class MemoryStore:
    """Bounded, file-backed curated memory (MEMORY.md / USER.md).
    Ported directly from Hermes agent/tools/memory_tool_store.py.
    """

    _MAX_CONSOLIDATION_FAILURES_PER_TURN = 3

    def __init__(
        self,
        memory_char_limit: int = DEFAULT_MEMORY_CHAR_LIMIT,
        user_char_limit: int = DEFAULT_USER_CHAR_LIMIT,
        *,
        memory_enabled: bool = True,
        user_profile_enabled: bool = True,
        base_dir: Optional[Path] = None,
    ):
        self.memory_entries: list[str] = []
        self.user_entries: list[str] = []
        self.memory_char_limit = memory_char_limit
        self.user_char_limit = user_char_limit
        self.memory_enabled = memory_enabled
        self.user_profile_enabled = user_profile_enabled
        self.base_dir = base_dir
        self._system_prompt_snapshot: dict[str, str] = {"memory": "", "user": ""}
        self._consolidation_failures = 0

    def target_enabled(self, target: str) -> bool:
        return self.user_profile_enabled if target == "user" else self.memory_enabled

    def reset_consolidation_failures(self) -> None:
        self._consolidation_failures = 0

    def _consolidation_failure(self, response: dict[str, Any]) -> dict[str, Any]:
        self._consolidation_failures += 1
        if self._consolidation_failures <= self._MAX_CONSOLIDATION_FAILURES_PER_TURN:
            return response
        FAILURE_CLASS.set("retry_cap")
        return {
            "success": False,
            "done": True,
            "error": (
                f"Memory consolidation failed {self._consolidation_failures} times this turn. Stop retrying "
                "memory calls — leave memory unchanged for now and continue with your reply to the user. "
                "The fact can be saved in a later turn."
            ),
        }

    def _get_base_dir(self) -> Path:
        return self.base_dir if self.base_dir is not None else get_memory_dir()

    def _path_for(self, target: str) -> Path:
        filename = "USER.md" if target == "user" else "MEMORY.md"
        return self._get_base_dir() / filename

    def _entries_for(self, target: str) -> list[str]:
        return self.user_entries if target == "user" else self.memory_entries

    def _set_entries(self, target: str, entries: list[str]) -> None:
        setattr(self, "user_entries" if target == "user" else "memory_entries", entries)

    def _char_count(self, target: str) -> int:
        return len(ENTRY_DELIMITER.join(self._entries_for(target)))

    def _char_limit(self, target: str) -> int:
        return self.user_char_limit if target == "user" else self.memory_char_limit

    def _usage(self, target: str) -> str:
        return f"{self._char_count(target):,}/{self._char_limit(target):,}"

    def _usage_pct(self, target: str, current: int) -> str:
        limit = self._char_limit(target)
        pct = min(100, int((current / limit) * 100)) if limit > 0 else 0
        return f"{pct}% — {current:,}/{limit:,} chars"

    def _failure_with_entries(self, target: str, message: str) -> dict[str, Any]:
        return self._consolidation_failure(
            _error(message, "over_budget", current_entries=self._entries_for(target), usage=self._usage(target))
        )

    def _batch_failure(
        self, target: str, message: str, failure_class: str, closest_entries: Optional[list[str]] = None
    ) -> dict[str, Any]:
        return self._consolidation_failure(
            _error(
                message + " No operations were applied (batch is all-or-nothing).",
                failure_class,
                usage=self._usage(target),
                **({"closest_entries": closest_entries} if closest_entries else {}),
            )
        )

    def load_from_disk(self) -> None:
        """Load MEMORY.md and USER.md from disk and capture frozen system-prompt snapshot."""
        base = self._get_base_dir()
        base.mkdir(parents=True, exist_ok=True)
        for target in ("memory", "user"):
            path = self._path_for(target)
            entries = list(dict.fromkeys(self._read_file(path)))
            self._set_entries(target, entries)
            count = self._char_count(target)
            limit = self._char_limit(target)
            if count > limit:
                logger.warning(
                    "%s exceeds its char limit on load: %d/%d chars. Entries stay loaded; "
                    "further additions are blocked until it is back under the limit.",
                    path.name,
                    count,
                    limit,
                )
            self._system_prompt_snapshot[target] = self._render_block(target, entries)

    def _mutate(self, target: str, mutate_fn: Callable[[list[str], int], Any], *, skip_drift: bool = False) -> dict[str, Any]:
        path = self._path_for(target)
        with file_lock(path):
            raw, read_ok = self._read_raw_checked(path)
            if not read_ok:
                return _read_failed_error(path)
            bak = None if skip_drift else self._detect_external_drift(target, raw)
            self._set_entries(target, list(dict.fromkeys(self._parse_entries(raw))))
            if bak:
                return _drift_error(path, bak)
            result = mutate_fn(self._entries_for(target), self._char_limit(target))
            if isinstance(result, dict):
                return result
            self._set_entries(target, result[0])
            path.parent.mkdir(parents=True, exist_ok=True)
            self._write_file(path, result[0])
            extra_fields = result[2] if len(result) > 2 else {}
            return self._success_response(target, result[1], **extra_fields)

    def add(self, target: str, content: str) -> dict[str, Any]:
        """Append a new entry. Returns error if it would exceed character budget."""
        content = content.strip()
        if not content:
            return _error("Content cannot be empty.", "missing_content")
        if scan_error := _scan_memory_content(content):
            return _error(scan_error, "scan_blocked")

        def _add(entries: list[str], limit: int):
            if content in entries:
                return self._success_response(target, "Entry already exists (no duplicate added).")
            new_total = len(ENTRY_DELIMITER.join(entries + [content]))
            if new_total > limit:
                return self._failure_with_entries(
                    target,
                    (
                        f"Memory at {self._char_count(target):,}/{limit:,} chars; adding this entry ({len(content)} chars) "
                        f"would exceed the limit by {new_total - limit:,} chars. Retry as ONE 'operations' batch that "
                        f"removes or shortens (replace) stale entries from current_entries below to free at least "
                        f"{new_total - limit:,} chars AND adds this entry — the limit is checked only on the batch result."
                    ),
                )
            return entries + [content], "Entry added."

        return self._mutate(target, _add, skip_drift=True)

    def replace(
        self, target: str, old_text: str, new_content: str, matched_entry: Optional[str] = None
    ) -> dict[str, Any]:
        """Find the entry containing old_text and replace the WHOLE entry with new_content."""
        new_content = new_content.strip()
        if not old_text.strip():
            return _error("old_text cannot be empty.", "missing_old_text")
        if not new_content:
            return _error("new_content cannot be empty. Use 'remove' to delete entries.", "missing_content")
        if scan_error := _scan_memory_content(new_content):
            return _error(scan_error, "scan_blocked")
        return self._edit(target, old_text.strip(), new_content, matched_entry)

    def remove(self, target: str, old_text: str, matched_entry: Optional[str] = None) -> dict[str, Any]:
        """Remove the entry containing old_text substring."""
        if not old_text.strip():
            return _error("old_text cannot be empty.", "missing_old_text")
        return self._edit(target, old_text.strip(), None, matched_entry)

    def _locate(self, entries: list[str], old_text: str, verb: str, matched_entry: Optional[str] = None):
        if matched_entry is not None:
            idx = _pinned_index(entries, matched_entry)
            return idx if idx is not None else _error(_stale_entry_message(matched_entry), "stale_entry")
        idx, ambiguous = _find_unique_match(entries, old_text)
        if ambiguous:
            return _error(
                f"Multiple entries matched '{old_text}'. Be more specific.",
                "ambiguous",
                matches=[
                    entries[i][:80] + ("..." if len(entries[i]) > 80 else "")
                    for i in _substring_matches(entries, old_text)
                ],
            )
        if idx is None:
            return self._consolidation_failure(_no_match_error(entries, old_text, verb, current_entries=entries))
        return idx

    def resolve_entry(self, target: str, old_text: str, verb: str) -> dict[str, Any]:
        def _resolve(entries: list[str], limit: int):
            idx = self._locate(entries, old_text.strip(), verb)
            return idx if isinstance(idx, dict) else {"success": True, "matched_entry": entries[idx]}
        return self._mutate(target, _resolve, skip_drift=True)

    def _edit(
        self, target: str, old_text: str, new_content: Optional[str], matched_entry: Optional[str] = None
    ) -> dict[str, Any]:
        def _apply(entries: list[str], limit: int):
            idx = self._locate(entries, old_text, "replace" if new_content else "remove", matched_entry)
            if isinstance(idx, dict):
                return idx
            replaced = entries[:idx] + ([] if new_content is None else [new_content]) + entries[idx + 1:]
            if new_content is None:
                return replaced, "Entry removed.", {"removed_entry": entries[idx]}
            new_total = len(ENTRY_DELIMITER.join(replaced))
            if new_total > limit:
                return self._failure_with_entries(
                    target,
                    (
                        f"Replacement {_over_limit(new_total, limit)}. Shorten the new content, or retry as ONE "
                        f"'operations' batch with this replace plus removes/shortenings of other stale entries "
                        f"(see current_entries below) — the limit is checked only on the batch result."
                    ),
                )
            return replaced, "Entry replaced.", {"replaced_entry": entries[idx]}
        return self._mutate(target, _apply)

    @staticmethod
    def _apply_batch_op(
        working: list[str], act: str, content: str, old_text: str, pos: str, matched_entry: Optional[str] = None
    ) -> tuple[Optional[str], Any, str]:
        if act == "add":
            if not content:
                return f"{pos}: content is required.", None, "missing_content"
            if content not in working:
                working.append(content)
            return None, None, "none"
        if act not in ("replace", "remove"):
            return f"{pos}: unknown action. Use add, replace, or remove.", None, "invalid_args"
        if not old_text:
            return f"{pos}: old_text is required.", None, "missing_old_text"
        if act == "replace" and not content:
            return (
                f"{pos}: content is required — set this operation object's own 'content' to the COMPLETE "
                f"new entry (or use action='remove' to delete)."
            ), None, "missing_content"
        if matched_entry is not None:
            idx = _pinned_index(working, matched_entry)
            if idx is None:
                return f"{pos}: {_stale_entry_message(matched_entry)}", None, "stale_entry"
        else:
            idx, ambiguous = _find_unique_match(working, old_text)
            if ambiguous:
                return f"{pos}: '{old_text}' matched multiple distinct entries -- be more specific.", None, "ambiguous"
            if idx is None:
                miss = _no_match_error(working, old_text, act)
                return f"{pos}: {miss['error']}", miss.get("closest_entries"), "no_match"
        previous_content = working[idx]
        working[idx:idx + 1] = [content] if act == "replace" else []
        return None, previous_content, "none"

    def apply_batch(self, target: str, operations: list[dict[str, Any]]) -> dict[str, Any]:
        """Apply batch add/replace/remove ops atomically against final budget."""
        return self._batch(target, operations, commit=True)

    def resolve_batch_entries(self, target: str, operations: list[dict[str, Any]]) -> dict[str, Any]:
        return self._batch(target, operations, commit=False)

    def _batch(self, target: str, operations: list[dict[str, Any]], *, commit: bool) -> dict[str, Any]:
        if not operations:
            return _error("operations list is empty.", "invalid_args")
        ops = [op or {} for op in operations]
        for i, op in enumerate(ops):
            scan_error = (
                op.get("action") in {"add", "replace"}
                and op.get("content")
                and _scan_memory_content(op["content"])
            )
            if scan_error:
                return _error(f"Operation {i + 1}: {scan_error}", "scan_blocked")

        def _apply(entries: list[str], limit: int):
            working = list(entries)
            matched = []
            for i, op in enumerate(ops):
                act = op.get("action")
                msg, previous_content, failure_class = self._apply_batch_op(
                    working,
                    act,
                    (op.get("content") or op.get("new_text") or "").strip(),
                    (op.get("old_text") or "").strip(),
                    f"Operation {i + 1} ({act or 'unknown'})",
                    op.get("matched_entry"),
                )
                if msg:
                    return self._batch_failure(target, msg, failure_class, closest_entries=previous_content)
                matched.append(previous_content)

            if entries and not working:
                label = self._path_for(target).name
                return self._batch_failure(
                    target,
                    (
                        f"Refusing to empty {label}: this batch would remove every entry from a "
                        f"previously non-empty store. Keep at least one entry — merge overlapping "
                        f"entries into a shorter one instead of removing the last one. To delete the "
                        f"final entry deliberately, use single remove() calls."
                    ),
                    "would_empty",
                )

            new_total = len(ENTRY_DELIMITER.join(working))
            if new_total > limit:
                return self._batch_failure(
                    target,
                    (
                        f"Applying all {len(operations)} operations {_over_limit(new_total, limit)} more. Add "
                        f"removes or shorter replacements of other stale entries to the same batch, then retry."
                    ),
                    "over_budget",
                )
            if not commit:
                return {"success": True, "matched_entries": matched}

            replaced, removed = {}, {}
            for i, (op, previous_content) in enumerate(zip(ops, matched), 1):
                if previous_content is not None:
                    (replaced if op.get("action") == "replace" else removed)[i] = previous_content
            replaced_fields = {"replaced_entries": replaced} if replaced else {}
            if removed:
                replaced_fields["removed_entries"] = removed
            return working, f"Applied {len(operations)} operation(s).", replaced_fields

        return self._mutate(target, _apply, skip_drift=not commit)

    def format_for_system_prompt(self, target: str) -> Optional[str]:
        return self._system_prompt_snapshot.get(target, "") or None

    def _success_response(self, target: str, message: str | None = None, **extra) -> dict[str, Any]:
        self._consolidation_failures = 0
        return {
            "success": True,
            "done": True,
            "target": target,
            "usage": self._usage_pct(target, self._char_count(target)),
            "entry_count": len(self._entries_for(target)),
            **({"message": message} if message else {}),
            **extra,
            "note": "Write saved. This update is complete — do not repeat it.",
        }

    def _render_block(self, target: str, entries: list[str]) -> str:
        if not entries:
            return ""
        content, sep = ENTRY_DELIMITER.join(entries), "═" * 46
        title = MEMORY_BLOCK_HEADERS["user" if target == "user" else "memory"]
        return f"{sep}\n{title} [{self._usage_pct(target, len(content))}]\n{sep}\n{content}"

    @staticmethod
    def _read_raw_checked(path: Path) -> tuple[str, bool]:
        if not path.exists():
            return "", True
        try:
            return path.read_text(encoding="utf-8-sig"), True
        except (OSError, UnicodeDecodeError):
            return "", False

    @staticmethod
    def _parse_entries(raw: str) -> list[str]:
        return [e for e in (x.strip() for x in raw.split(ENTRY_DELIMITER)) if e]

    @staticmethod
    def _read_file(path: Path) -> list[str]:
        return MemoryStore._parse_entries(MemoryStore._read_raw_checked(path)[0])

    @staticmethod
    def _write_file(path: Path, entries: list[str]) -> None:
        try:
            atomic_write_text(path, ENTRY_DELIMITER.join(entries), tmp_prefix=".mem_")
        except OSError as e:
            raise RuntimeError(f"Failed to write memory file {path}: {e}")

    def _detect_external_drift(self, target: str, raw: str) -> Optional[str]:
        if max(map(len, self._parse_entries(raw)), default=0) <= self._char_limit(target):
            return None
        path = self._path_for(target)
        bak_path = path.with_suffix(path.suffix + f".bak.{int(time.time())}")
        try:
            bak_path.write_text(raw, encoding="utf-8")
        except OSError:
            return str(bak_path) + " (BACKUP FAILED — file unchanged on disk)"
        return str(bak_path)


# ==============================================================================
# MEMORY TOOL CALL WRAPPER (HERMES AGENT CONTRACT)
# ==============================================================================

_STORE_ACTIONS = {
    "add": lambda store, target, content, old_text: store.add(target, content),
    "replace": lambda store, target, content, old_text: store.replace(target, old_text, content),
    "remove": lambda store, target, content, old_text: store.remove(target, old_text),
}


def load_on_disk_store(base_dir: Optional[Path] = None) -> MemoryStore:
    """Fresh on-disk MemoryStore."""
    store = MemoryStore(base_dir=base_dir)
    store.load_from_disk()
    return store


def memory_tool(
    action: str | None = None,
    target: str = "memory",
    content: str | None = None,
    old_text: str | None = None,
    new_text: str | None = None,
    operations: Optional[list[dict[str, Any]]] = None,
    store: Optional[MemoryStore] = None,
) -> str:
    """Execute memory tool following Hermes API semantics."""
    if store is None:
        store = load_on_disk_store()

    if not content and new_text:
        content = new_text
    target = "memory" if target is None else target
    if target not in {"memory", "user"}:
        return json.dumps({"success": False, "error": f"Invalid memory target '{target}'. Use 'memory' or 'user'."}, ensure_ascii=False)

    if operations:
        if not isinstance(operations, list):
            return json.dumps({"success": False, "error": "operations must be a list of {action, content?, old_text?} objects."}, ensure_ascii=False)
        result = store.apply_batch(target, operations)
        return json.dumps(result, ensure_ascii=False)

    if not action:
        return json.dumps(
            {"success": False, "error": "Missing required parameter: provide 'action' (add/replace/remove) or 'operations' (batch list)."},
            ensure_ascii=False,
        )

    if action not in _STORE_ACTIONS:
        return json.dumps({"success": False, "error": f"Unknown action '{action}'. Use: add, replace, remove"}, ensure_ascii=False)

    if action == "add" and not content:
        return json.dumps({"success": False, "error": "Content is required for 'add' action."}, ensure_ascii=False)

    if action in ("replace", "remove") and not old_text:
        return json.dumps(
            {
                "success": False,
                "error": f"'{action}' needs old_text. Reissue the {action} with old_text set to part of one of current_entries.",
                "current_entries": store._entries_for(target),
                "usage": store._usage(target),
            },
            ensure_ascii=False,
        )

    if action == "replace" and not content:
        return json.dumps({"success": False, "error": "content is required for 'replace' action."}, ensure_ascii=False)

    result = _STORE_ACTIONS[action](store, target, content, old_text)
    return json.dumps(result, ensure_ascii=False)
