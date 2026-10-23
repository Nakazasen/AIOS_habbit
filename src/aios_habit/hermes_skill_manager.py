"""Hermes Skill Manager & Authoring Standards - Ported directly from Hermes Agent.

Original Hermes files:
- tools/skill_manager_tool.py (v0.21.6+724)
- agent/skill_utils.py (v0.21.6+724)

Port Classification: PORT CÓ SỬA MỐI NỐI (SEAMS)
Seam modifications:
1. get_skills_dir() resolves to local_cases/skills (honors AIOS_LOCAL_CASES_DIR).
2. Standalone PyYAML parsing and safe frontmatter loading.
3. Standalone msvcrt (Windows) / fcntl (Unix) cross-process file locks under .locks/.
4. Preserves 100% of Hermes authoring standards:
   - Frontmatter YAML fence (---), name <= 64 chars, description <= 60 chars ending with a period.
   - Max body size 100,000 characters, supporting file limit 1 MiB.
   - Allowed subdirectories: references, templates, scripts, assets.
   - Actions: create, edit, patch, write_file, remove_file, delete, read.
"""

from __future__ import annotations

from contextlib import ExitStack, contextmanager, suppress
import hashlib
import json
import logging
import os
from pathlib import Path, PurePath
import re
import shutil
import time
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

import yaml

from aios_habit.hermes_memory import atomic_write_text, file_lock, get_default_local_cases_dir

logger = logging.getLogger("aios_habit.hermes_skill_manager")

# ==============================================================================
# HERMES CONSTRAINTS & CONSTANTS (VERBATIM)
# ==============================================================================

MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_SKILL_CONTENT_CHARS = 100_000   # ~36k tokens
MAX_SKILL_FILE_BYTES = 1_048_576    # 1 MiB
SKILL_PROMPT_DESC_LIMIT = 60        # One sentence, trigger first, ends with dot

VALID_NAME_RE = re.compile(r'^[a-z0-9][a-z0-9._-]*$')
ALLOWED_SUBDIRS = frozenset({"references", "templates", "scripts", "assets"})
EXCLUDED_SKILL_DIRS = frozenset((
    ".git", ".github", ".hub", ".archive", ".curator_backups", ".locks",
    ".venv", "venv", "node_modules", "site-packages", "__pycache__",
))

_FRONTMATTER_END_RE = re.compile(r'\n---\s*\n')
_NAME_RULE = "Use lowercase letters, numbers, hyphens, dots, and underscores."


def get_skills_dir() -> Path:
    """Resolve AIOS skills directory inside local_cases/skills."""
    return get_default_local_cases_dir() / "skills"


def _skill_lock_path(name: str) -> Path:
    digest = hashlib.sha256(Path(name).name.encode("utf-8", "surrogatepass")).hexdigest()
    return get_skills_dir() / ".locks" / f"{digest}.lock"


def _skill_mutation_lock(name: str):
    return file_lock(_skill_lock_path(name))


def is_excluded_skill_path(path: Path) -> bool:
    parts = PurePath(str(path)).parts
    return any(part in EXCLUDED_SKILL_DIRS for part in parts)


# ==============================================================================
# FRONTMATTER & VALIDATION HELPERS (VERBATIM HERMES)
# ==============================================================================

def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from markdown; returns (frontmatter_dict, body)."""
    content = content.removeprefix("\ufeff")
    if not content.startswith("---"):
        return {}, content
    end_match = _FRONTMATTER_END_RE.search(content[3:])
    if not end_match:
        return {}, content
    yaml_content = content[3 : end_match.start() + 3]
    body = content[end_match.end() + 3 :]
    try:
        parsed = yaml.safe_load(yaml_content)
        if isinstance(parsed, dict):
            return parsed, body
    except Exception as e:
        logger.debug("Frontmatter YAML parse failed: %s", e)
    return {}, body


def _validate_name(name: str) -> Optional[str]:
    if not name:
        return "Skill name is required."
    if len(name) > MAX_NAME_LENGTH:
        return f"Skill name exceeds {MAX_NAME_LENGTH} characters."
    if not VALID_NAME_RE.match(name):
        return f"Invalid skill name '{name}'. {_NAME_RULE} Must start with a letter or digit."
    return None


def _validate_category(category: Optional[str]) -> Optional[str]:
    if category is None or (isinstance(category, str) and not category.strip()):
        return None
    category = category.strip()
    if "/" in category or "\\" in category:
        return f"Invalid category '{category}'. {_NAME_RULE} Categories must be a single directory name."
    if len(category) > MAX_NAME_LENGTH or not VALID_NAME_RE.match(category):
        return f"Invalid category '{category}'. {_NAME_RULE}"
    return None


def _validate_frontmatter(content: str, *, new_skill: bool = False) -> Optional[str]:
    """Validate YAML frontmatter and character limits strictly according to Hermes rules."""
    if not content.strip():
        return "Content cannot be empty."
    content = content.lstrip("\ufeff")
    if not content.startswith("---"):
        return "SKILL.md must start with YAML frontmatter (---). See existing skills for format."
    end_match = _FRONTMATTER_END_RE.search(content[3:])
    if not end_match:
        return "SKILL.md frontmatter is not closed. Ensure you have a closing '---' line."
    try:
        parsed = yaml.safe_load(content[3 : end_match.start() + 3])
    except yaml.YAMLError as e:
        return f"YAML frontmatter parse error: {e}"
    if not isinstance(parsed, dict):
        return "Frontmatter must be a YAML mapping (key: value pairs)."
    for field in ("name", "description"):
        if field not in parsed:
            return f"Frontmatter must include '{field}' field."
    desc = str(parsed["description"])
    if len(desc) > MAX_DESCRIPTION_LENGTH:
        return f"Description exceeds {MAX_DESCRIPTION_LENGTH} characters."
    if new_skill and len(desc.strip().strip("'\"")) > SKILL_PROMPT_DESC_LIMIT:
        return (
            f"Description is {len(desc.strip())} chars — new skills must fit the "
            f"{SKILL_PROMPT_DESC_LIMIT}-char system-prompt budget (one sentence, trigger first, "
            f"ends with a period). The skill index truncates longer descriptions to "
            f"{SKILL_PROMPT_DESC_LIMIT - 3} chars + '...', destroying the routing signal. "
            f"Move detail into the skill body."
        )
    if not content[end_match.end() + 3 :].strip():
        return "SKILL.md must have content after the frontmatter (instructions, procedures, etc.)."
    return None


def _validate_content_size(content: str, label: str = "SKILL.md") -> Optional[str]:
    if len(content) > MAX_SKILL_CONTENT_CHARS:
        return (
            f"{label} content is {len(content):,} characters (limit: {MAX_SKILL_CONTENT_CHARS:,}). "
            f"Consider splitting into a smaller SKILL.md with supporting files in references/ "
            f"or templates/."
        )
    return None


def _validate_file_path(file_path: str) -> Optional[str]:
    if not file_path:
        return "file_path is required."
    parts = Path(file_path).parts
    if ".." in parts:
        return "Path traversal ('..') is not allowed."
    if parts and parts[-1] == "SKILL.md" and len(parts) in (1, 2):
        return None
    if not parts or parts[0] not in ALLOWED_SUBDIRS:
        allowed = ", ".join(sorted(ALLOWED_SUBDIRS))
        return f"File must be under one of: {allowed}. Got: '{file_path}'"
    if len(parts) < 2:
        return f"Provide a file path, not just a directory. Example: '{parts[0]}/myfile.md'"
    return None


def _description_preview(content: str) -> str:
    with suppress(Exception):
        fm, _ = parse_frontmatter(content)
        return str(fm.get("description", ""))[:120]
    return ""


# ==============================================================================
# RESOLUTION & SEARCH (PORTED FOR LOCAL_CASES)
# ==============================================================================

def _resolve_skill_dir(name: str, category: str | None = None) -> Path:
    base = get_skills_dir()
    if category:
        return base / category / name
    return base / name


def _iter_skill_dirs(root: Path) -> Iterator[Path]:
    if not root.exists():
        return
    for skill_md in root.rglob("SKILL.md"):
        if not is_excluded_skill_path(skill_md):
            yield skill_md.parent


def find_skill(name: str) -> Optional[dict[str, Any]]:
    """Find skill directory matching name by directory or frontmatter name."""
    root = get_skills_dir()
    if not root.exists():
        return None
    for skill_dir in _iter_skill_dirs(root):
        if skill_dir.name == name:
            return {"path": skill_dir}
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            try:
                fm, _ = parse_frontmatter(skill_md.read_text(encoding="utf-8-sig")[:4000])
                if fm.get("name") == name:
                    return {"path": skill_dir}
            except Exception:
                pass
    return None


# ==============================================================================
# SKILL MANAGE ACTIONS (HERMES VERBATIM)
# ==============================================================================

def _err(message: str) -> dict[str, Any]:
    return {"success": False, "error": message}


def create_skill(name: str, content: str, category: str | None = None) -> dict[str, Any]:
    """Create a new skill package conforming to Hermes standards."""
    if err := (
        _validate_name(name)
        or _validate_category(category)
        or _validate_frontmatter(content, new_skill=True)
        or _validate_content_size(content)
    ):
        return _err(err)

    if existing := find_skill(name):
        return _err(f"A skill named '{name}' already exists at {existing['path']}.")

    skill_dir = _resolve_skill_dir(name, category)
    with _skill_mutation_lock(name):
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_md = skill_dir / "SKILL.md"
        atomic_write_text(skill_md, content)

    return {
        "success": True,
        "message": f"Skill '{name}' created.",
        "path": str(skill_dir),
        "skill_md": str(skill_md),
        "hint": (
            f"To add reference files, templates, or scripts, use skill_manage(action='write_file', "
            f"name='{name}', file_path='references/example.md', file_content='...')"
        ),
    }


def edit_skill(name: str, content: str) -> dict[str, Any]:
    """Full rewrite of an existing skill's SKILL.md."""
    if err := _validate_frontmatter(content) or _validate_content_size(content):
        return _err(err)
    existing = find_skill(name)
    if not existing:
        return _err(f"Skill '{name}' not found.")
    skill_dir = existing["path"]
    skill_md = skill_dir / "SKILL.md"
    with _skill_mutation_lock(name):
        atomic_write_text(skill_md, content)
    return {"success": True, "message": f"Skill '{name}' updated (full rewrite).", "path": str(skill_dir)}


def patch_skill(
    name: str, old_string: str, new_string: str, file_path: str | None = None, replace_all: bool = False
) -> dict[str, Any]:
    """Find and replace old_string with new_string in SKILL.md or a supporting file."""
    if not old_string:
        return _err("old_string is required for patch.")
    if new_string is None:
        return _err("new_string is required for patch.")

    existing = find_skill(name)
    if not existing:
        return _err(f"Skill '{name}' not found.")
    skill_dir = existing["path"]
    target = (skill_dir / file_path) if file_path else (skill_dir / "SKILL.md")
    if not target.exists():
        return _err(f"File not found: {target}")

    with _skill_mutation_lock(name):
        content = target.read_text(encoding="utf-8-sig")
        if old_string not in content:
            return _err(f"old_string '{old_string[:80]}' not found in {target.name}.")
        if not replace_all and content.count(old_string) > 1:
            return _err(f"old_string appears {content.count(old_string)} times. Be more specific or use replace_all=True.")

        new_content = content.replace(old_string, new_string) if replace_all else content.replace(old_string, new_string, 1)
        if not file_path:
            if err := _validate_frontmatter(new_content):
                return _err(f"Patch would break SKILL.md structure: {err}")
        atomic_write_text(target, new_content)

    return {"success": True, "message": f"Patched {target.name} in skill '{name}'."}


def write_supporting_file(name: str, file_path: str, file_content: str) -> dict[str, Any]:
    """Write supporting file in references/, templates/, scripts/, assets/."""
    if err := _validate_file_path(file_path):
        return _err(err)
    if len(file_content.encode("utf-8")) > MAX_SKILL_FILE_BYTES:
        return _err(f"File size exceeds limit of {MAX_SKILL_FILE_BYTES} bytes.")

    existing = find_skill(name)
    if not existing:
        return _err(f"Skill '{name}' not found.")
    skill_dir = existing["path"]
    target = skill_dir / file_path
    with _skill_mutation_lock(name):
        target.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(target, file_content)

    return {"success": True, "message": f"Wrote {file_path} in skill '{name}'."}


def remove_supporting_file(name: str, file_path: str) -> dict[str, Any]:
    """Remove supporting file from references/, templates/, scripts/."""
    if err := _validate_file_path(file_path):
        return _err(err)
    existing = find_skill(name)
    if not existing:
        return _err(f"Skill '{name}' not found.")
    skill_dir = existing["path"]
    target = skill_dir / file_path
    if not target.exists():
        return _err(f"File '{file_path}' does not exist.")
    with _skill_mutation_lock(name):
        target.unlink()
    return {"success": True, "message": f"Removed {file_path} from skill '{name}'."}


def delete_skill(name: str, archive: bool = True) -> dict[str, Any]:
    """Delete or archive a skill."""
    existing = find_skill(name)
    if not existing:
        return _err(f"Skill '{name}' not found.")
    skill_dir = existing["path"]
    with _skill_mutation_lock(name):
        if archive:
            archive_dir = get_skills_dir() / ".archive" / name
            archive_dir.parent.mkdir(parents=True, exist_ok=True)
            if archive_dir.exists():
                archive_dir = archive_dir.with_name(f"{name}-{int(time.time())}")
            shutil.move(str(skill_dir), str(archive_dir))
            return {"success": True, "message": f"Skill '{name}' archived to {archive_dir.name}."}
        else:
            shutil.rmtree(skill_dir)
            return {"success": True, "message": f"Skill '{name}' permanently deleted."}


def read_skill(name: str, file_path: Optional[str] = None) -> dict[str, Any]:
    """Read SKILL.md or supporting file."""
    existing = find_skill(name)
    if not existing:
        return _err(f"Skill '{name}' not found.")
    skill_dir = existing["path"]
    target = (skill_dir / file_path) if file_path else (skill_dir / "SKILL.md")
    if not target.exists():
        return _err(f"File '{target.name}' not found.")
    try:
        content = target.read_text(encoding="utf-8-sig")
        return {"success": True, "name": name, "file_path": file_path or "SKILL.md", "content": content}
    except Exception as e:
        return _err(f"Failed to read file: {e}")


# ==============================================================================
# DISPATCHER TOOL
# ==============================================================================

def skill_manage(
    action: str,
    name: str,
    content: Optional[str] = None,
    file_path: Optional[str] = None,
    file_content: Optional[str] = None,
    old_string: Optional[str] = None,
    new_string: Optional[str] = None,
    category: Optional[str] = None,
    replace_all: bool = False,
    archive: bool = True,
) -> dict[str, Any]:
    """Main skill management entry point conforming to Hermes skill_manage tool."""
    action = (action or "").strip().lower()
    name = (name or "").strip()

    if action == "create":
        return create_skill(name, content or "", category=category)
    elif action == "edit":
        return edit_skill(name, content or "")
    elif action == "patch":
        return patch_skill(name, old_string or "", new_string or "", file_path=file_path, replace_all=replace_all)
    elif action == "write_file":
        return write_supporting_file(name, file_path or "", file_content or "")
    elif action == "remove_file":
        return remove_supporting_file(name, file_path or "")
    elif action == "delete":
        return delete_skill(name, archive=archive)
    elif action in ("read", "view"):
        return read_skill(name, file_path=file_path)
    else:
        return _err(f"Unknown action '{action}'. Use create, edit, patch, write_file, remove_file, delete, read.")
