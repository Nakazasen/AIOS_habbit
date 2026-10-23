"""Hermes Learn Prompt & Learning Graph - Ported directly from Hermes Agent.

Original Hermes files:
- agent/learn_prompt.py (v0.21.6+724)
- agent/learning_graph.py (v0.21.6+724)

Port Classification: PORT CÓ SỬA MỐI NỐI (SEAMS)
Seam modifications:
1. Resolves skill roots to local_cases/skills/ (honors AIOS_LOCAL_CASES_DIR).
2. Reads memory cards from local_cases/memories/USER.md and MEMORY.md.
3. Preserves 100% of Hermes authoring standards and learning graph structures:
   - _AUTHORING_STANDARDS verbatim.
   - _KNOWLEDGE_SKILL_STANDARDS verbatim.
   - build_learn_prompt() function.
   - memory_fingerprint (SHA-256[:12]) and memory_node_id.
   - build_learning_graph() assembling skills + memory cards into nodes and edges.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from aios_habit.hermes_curator import load_usage
from aios_habit.hermes_memory import MemoryStore, get_memory_dir
from aios_habit.hermes_skill_manager import get_skills_dir, parse_frontmatter

logger = logging.getLogger("aios_habit.hermes_learning")

UTC = timezone.utc

# ==============================================================================
# AUTHORING STANDARDS & LEARN PROMPT (VERBATIM HERMES AGENT)
# ==============================================================================

_AUTHORING_STANDARDS = """\
Follow the Hermes skill-authoring standards exactly. These are the same
HARDLINE rules a maintainer enforces in review:

Frontmatter:
- name: lowercase-hyphenated, <=64 chars, no spaces.
- description: ONE sentence, **<=60 characters**, ends with a period. State the
  capability, not the implementation. No marketing words (powerful,
  comprehensive, seamless, advanced, robust). Do NOT repeat the skill name. If
  the description contains a colon, wrap the whole value in double quotes.
  This is the most-violated rule and it is NOT cosmetic: the system-prompt
  skill index truncates the description to 60 chars and loads it every
  session, so anything past char 60 is silently cut and never routes. After
  you write the description, COUNT the characters; if it is over 60, cut it
  down before saving — do not ship a sentence and hope.
    Good (<=60): `Search arXiv papers by keyword, author, or ID.`
    Bad (123):   `A comprehensive skill that lets the agent search arXiv for
                  academic papers using keywords, authors, and categories.`
- version: 0.1.0
- author: always the literal value `Hermes`. NEVER fill it from the host
  environment — the OS/login username (e.g. the `user=` line in your
  environment hints), git config, or any identity you can probe must not be
  written. Skills get shared and published, so an environment-derived name is
  a privacy leak the user never opted into; the skill names itself as Hermes.
- platforms: declare `[macos]`, `[linux]`, and/or `[windows]` IF the skill
  uses OS-bound primitives (osascript/apt/systemctl => the matching OS; /proc,
  os.setsid, signal.SIGKILL => linux; fcntl/termios => POSIX). Prefer fixing it
  cross-platform first (tempfile.gettempdir(), pathlib.Path, psutil); gate only
  when the dependency is genuinely platform-bound. Omit the field for portable
  skills.
- metadata.hermes.tags: a few Capitalized, Relevant, Tags.

Body section order (omit a section only if it genuinely has no content):
1. "# <Human Title>" then a 2-3 sentence intro: what it does, what it does NOT
   do, and the key dependency stance (e.g. "stdlib only").
2. "## When to Use" — bullet list of concrete trigger phrases.
3. "## Prerequisites" — exact env vars, install steps, credentials.
4. "## How to Run" — the canonical invocation, framed through Hermes tools.
5. "## Quick Reference" — a flat command/endpoint list, no narration.
6. "## Procedure" — numbered steps with copy-paste-exact commands.
7. "## Pitfalls" — known limits, rate limits, things that look broken but aren't.
8. "## Verification" — a single command/check that proves the skill worked.

Hermes-tool framing (this is what makes it a skill, not shell docs):
- Frame running scripts as "invoke through the `terminal` tool".
- Reference Hermes tools by name in backticks: `terminal`, `read_file`,
  `write_file`, `search_files`, `patch`, `web_extract`, `web_search`,
  `vision_analyze`, `browser_navigate`, `delegate_task`, `image_generate`,
  `text_to_speech`, `cronjob`, `memory`, `skill_view`, `execute_code`.
- Do NOT name shell utilities the agent already has wrapped: say `read_file`
  not cat/head/tail, `search_files` not grep/rg/find/ls, `patch` not sed/awk,
  `web_extract` not curl-to-scrape, `write_file` not echo>file or heredocs.
- Third-party CLIs (ffmpeg, gh, an SDK) are fine inside a script file, but the
  prose still frames them as "invoke through the `terminal` tool". If the
  skill needs an MCP server, name it and document its setup in Prerequisites.

Quality bar:
- Prefer exact commands, endpoint URLs, function signatures, and config keys
  that appear VERBATIM in the source. NEVER invent flags, paths, or APIs — if
  you didn't see it in the source, don't write it.
- Keep it tight and scannable: ~100 lines for a simple skill, ~200 for a
  complex one. Don't re-paste the source docs. (For a knowledge-base skill
  this cap applies to SKILL.md itself — the distilled content lives in
  `references/` files; see the knowledge-base rules.)
- Don't write a router/index/hub skill that only points at other skills.
  (A knowledge-base SKILL.md indexing its OWN `references/` files is not a
  hub — that layout is required for large sources.)
- Larger scripts/parsers belong in a `scripts/` file (add via
  `skill_manage` write_file), referenced from SKILL.md by relative path — not
  inlined for the agent to re-type every run. References go in `references/`,
  templates in `templates/`."""

_KNOWLEDGE_SKILL_STANDARDS = """\
Knowledge-base skills (books, paper stacks, large doc corpora, specs):

When the source is a large body of prose rather than a workflow, do NOT cram
it into one SKILL.md and do NOT reduce it to a lossy summary. Author an
expansive skill:

- SKILL.md is a lean core, always loaded in full: the source's central mental
  models and the decision rules worth having in every session, followed by an
  index of every reference file with a one-line "load this when ..."
  description. Keep SKILL.md itself within the normal size bar; the bulk
  lives in `references/`.
- One file per chapter or major topic under `references/` (e.g.
  `references/ch04-replication.md`), each added with `skill_manage`
  write_file. Distill STRUCTURE, not summary: frameworks, definitions,
  tables, equations, trade-offs, decision trees.
- Never write `references/<date>-<topic>.md` or incident journals — references
  are reference material, not history."""


def build_learn_prompt(target_topic: str, source_text: str = "") -> str:
    """Build the canonical Hermes learn prompt."""
    prompt = (
        f"You are creating a new skill for the topic: '{target_topic}'.\n\n"
        f"{_AUTHORING_STANDARDS}\n\n"
        f"When handling extensive documentation:\n{_KNOWLEDGE_SKILL_STANDARDS}\n\n"
    )
    if source_text:
        prompt += f"Source material provided below:\n```\n{source_text[:8000]}\n```\n\n"
    prompt += "Now construct the skill and use skill_manage(action='create', ...) to save it."
    return prompt


# ==============================================================================
# LEARNING GRAPH ASSEMBLY (VERBATIM HERMES AGENT)
# ==============================================================================

@dataclass
class SkillNode:
    name: str
    category: str
    source: str = "profile"
    timestamp: Optional[int] = None
    use_count: int = 0
    state: str = "active"
    created_by: Optional[str] = None
    pinned: bool = False
    related: list[str] = field(default_factory=list)


def memory_fingerprint(entry: str) -> str:
    """Short stable digest of a memory entry's text (SHA-256[:12])."""
    return hashlib.sha256(entry.strip().encode("utf-8")).hexdigest()[:12]


def memory_node_id(card: dict[str, Any], index: int) -> str:
    return f"memory:{card['source']}:{index}:{card['fingerprint']}"


def _memory_cards() -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    base = get_memory_dir()
    for fname, source in (("MEMORY.md", "memory"), ("USER.md", "profile")):
        path = base / fname
        if not path.exists():
            continue
        try:
            file_ts = int(path.stat().st_mtime)
        except OSError:
            file_ts = None
        entries = MemoryStore._read_file(path)
        for chunk_idx, chunk in enumerate(entries):
            first = chunk.splitlines()[0].strip().lstrip("# ").strip()
            cards.append({
                "source": source,
                "timestamp": file_ts + chunk_idx if file_ts is not None else None,
                "title": (first[:80] + "…") if len(first) > 80 else first,
                "body": chunk[:1200],
                "fingerprint": memory_fingerprint(chunk),
            })
    return cards


def _tokenize(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) >= 3}


def _memory_skill_edges(memory_cards: list[dict[str, Any]], skills: list[SkillNode]) -> list[tuple[str, str]]:
    edges: list[tuple[str, str]] = []
    skill_meta = [(s.name, _tokenize(s.name), s.name.lower()) for s in skills]
    for idx, card in enumerate(memory_cards):
        text = f"{card.get('title', '')}\n{card.get('body', '')}".lower()
        text_tokens = _tokenize(text)
        scored = sorted(
            (
                (score, name)
                for name, tokens, name_lower in skill_meta
                if (score := (6 if name_lower in text else 0) + len(tokens & text_tokens)) > 0
            ),
            key=lambda x: (-x[0], x[1]),
        )
        edges.extend((memory_node_id(card, idx), name) for _, name in scored[:4])
    return edges


def build_skill_nodes(root: Optional[Path] = None) -> dict[str, SkillNode]:
    root = root or get_skills_dir()
    usage = load_usage()
    nodes: dict[str, SkillNode] = {}

    if not root.exists():
        return nodes

    for skill_md in root.rglob("SKILL.md"):
        parts = skill_md.parts
        if any(p in {".git", ".archive", ".locks", "node_modules"} for p in parts):
            continue
        try:
            fm, _ = parse_frontmatter(skill_md.read_text(encoding="utf-8-sig")[:4000])
        except Exception:
            fm = {}
        name = str(fm.get("name") or skill_md.parent.name).strip()
        if not name or name in nodes:
            continue
        rec = usage.get(name, {})
        cat = fm.get("category") or "general"
        nodes[name] = SkillNode(
            name=name,
            category=str(cat),
            source="profile",
            timestamp=int(skill_md.stat().st_mtime),
            use_count=int(rec.get("use_count", 0)),
            state=str(rec.get("state", "active")),
            created_by=rec.get("created_by", "agent"),
            pinned=bool(rec.get("pinned", False)),
        )
    return nodes


def build_edges(nodes: dict[str, SkillNode]) -> list[tuple[str, str]]:
    return list(
        dict.fromkeys(
            (min(node.name, target), max(node.name, target))
            for node in nodes.values()
            for target in node.related
            if target in nodes and target != node.name
        )
    )


def density_stats(nodes: dict[str, SkillNode], edges: list[tuple[str, str]]) -> dict[str, Any]:
    linked = {x for edge in edges for x in edge}
    cats = Counter(x.category for x in nodes.values())
    n = len(nodes) or 1
    return {
        "nodes": len(nodes),
        "related_edges": len(edges),
        "edges_per_node": round(len(edges) / n, 3),
        "linked_nodes": len(linked),
        "isolated_pct": round(100 * (n - len(linked)) / n, 1),
        "categories": len(cats),
        "agent_created": sum(1 for x in nodes.values() if x.created_by == "agent"),
        "used": sum(1 for x in nodes.values() if x.use_count > 0),
        "top_categories": sorted(cats.items(), key=lambda kv: -kv[1])[:8],
    }


def build_learning_graph() -> dict[str, Any]:
    """Full payload for desktop learning panel matching Hermes schema."""
    skills = build_skill_nodes()
    skill_edges = build_edges(skills)
    memory_cards = _memory_cards()
    memory_edges = _memory_skill_edges(memory_cards, list(skills.values()))

    clusters = Counter(node.category for node in skills.values())
    if memory_cards:
        clusters["memory"] = len(memory_cards)

    graph_nodes = [
        {
            "id": n.name,
            "label": n.name,
            "kind": "skill",
            "timestamp": n.timestamp,
            "category": n.category,
            "useCount": n.use_count,
            "state": n.state,
            "createdBy": n.created_by,
            "pinned": n.pinned,
        }
        for n in skills.values()
    ] + [
        {
            "id": memory_node_id(card, i),
            "label": card["title"],
            "kind": "memory",
            "memorySource": card["source"],
            "timestamp": card.get("timestamp"),
            "category": "memory",
            "useCount": 0,
            "state": "active",
            "createdBy": "memory",
            "pinned": False,
        }
        for i, card in enumerate(memory_cards)
    ]

    return {
        "nodes": graph_nodes,
        "edges": [{"source": a, "target": b} for a, b in skill_edges + memory_edges],
        "clusters": [{"category": c, "count": n} for c, n in sorted(clusters.items(), key=lambda kv: -kv[1])],
        "memory": memory_cards,
        "stats": {
            **density_stats(skills, skill_edges),
            "memory_nodes": len(memory_cards),
            "memory_skill_edges": len(memory_edges),
            "learned_skills": len(skills),
        },
    }
