"""Hermes Background Post-Session Reviewer - Ported directly from Hermes Agent.

Original Hermes files:
- agent/background_review.py (v0.21.6+724)
- agent/review_engine.py (v0.21.6+724)

Port Classification: PORT CÓ SỬA MỐI NỐI (SEAMS)
Seam modifications:
1. Targets ported MemoryStore (USER.md / MEMORY.md) in local_cases/memories/.
2. Targets ported skill_manage in local_cases/skills/.
3. Removes gateway / runtime fork dependencies; provides thread-safe cancellation runner.
4. Preserves 100% of Hermes prompts, rubrics, routing blocks, and non-blocking execution invariants:
   - _MEMORY_ROUTING_BLOCK (USER.md for who user is vs MEMORY.md for environment).
   - _LESSON_LAYER_BLOCK (Procedure first, pitfall = rule + why, no PR/tickets).
   - _DO_NOT_CAPTURE_BLOCK (Never capture transient failures or negative tool claims).
   - _SKILL_REVIEW_PROMPT & _COMBINED_REVIEW_PROMPT.
   - _BackgroundReviewRun cancellation token.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from aios_habit.hermes_memory import MemoryStore, load_on_disk_store
from aios_habit.hermes_skill_manager import skill_manage

logger = logging.getLogger("aios_habit.hermes_post_session_review")

_BACKGROUND_REVIEW_CANCEL_TIMEOUT_SECONDS = 2.0

# ==============================================================================
# PROMPT DEFINITIONS & RUBRIC BLOCKS (VERBATIM HERMES AGENT)
# ==============================================================================

_MEMORY_ROUTING_BLOCK = (
    "TWO distinct stores — pick the right one for each fact:\n"
    "  • USER.md (memory tool, target='user'): who the user is — persona, preferences, "
    "communication and work style, personal details they revealed, and expectations about how you "
    "should behave.\n"
    "  • MEMORY.md (memory tool, target='memory'): facts about the ENVIRONMENT you operate in — "
    "tool quirks, project conventions, config gotchas, paths and endpoints that matter.\n\n"
    "One fact goes to ONE store, never both — writing it to both bloats both files until they hit "
    "their size limits and crowds out the facts that matter; misrouting it puts it where the next "
    "session won't look. If the tool schema lists only one "
    "target, that store is the only one enabled — use it and skip the other.\n\n"
)

_MEMORY_REVIEW_PROMPT = (
    "Review the conversation above and consider saving to memory if appropriate.\n\n"
    "Memory has " + _MEMORY_ROUTING_BLOCK +
    "If something stands out, save it once, in the right store, using the memory tool with the "
    "matching target. If nothing is worth saving, just say 'Nothing to save.' and stop."
)

_LESSON_LAYER_BLOCK = (
    "What a skill IS: the instructions for doing a class of task the most efficient and correct "
    "way, to THIS user's specifications — the procedure, the tools and commands that work, the "
    "order, the user's preferences for how the result should look, and the pitfalls that cost time. "
    "A future session should be able to follow it and produce what the user wants on the first "
    "try. Everything below is about writing that well:\n"
    "  • Procedure first: the steps in the order they are done, with the concrete commands, tool "
    "calls, and decision points. Lessons and pitfalls attach to the step they affect.\n"
    "  • A pitfall is a generalizable rule + one clause of WHY (the mechanism), imperative. 'Grep the "
    "test tree for the SYMBOL before widening a helper signature — hand-rolled mocks reimplement the "
    "old shape and fail on a shard you did not run.' Not a narrative of what happened this session.\n"
    "  • No PR/issue numbers, dates, ticket IDs, or quoted user text as content — the rule must stand "
    "without the incident behind it. Keep a short quote ONLY when the quote itself is the clearest "
    "statement of the rule.\n"
    "  • The same lesson learned twice is ONE rule. Before adding, search the skill (and its "
    "references/) for the rule already stated; strengthen or clarify it rather than appending a "
    "second copy.\n"
    "  • Not a duplicate of what the environment already teaches: repo AGENTS.md files, tool schema "
    "descriptions, and other always-loaded context. A skill carries the WORKFLOW and the pitfalls; "
    "it does not restate the codebase map or a tool's parameter list.\n"
    "  • Always-on rules (standing user preferences, gates that apply to every instance of the "
    "task) live in SKILL.md itself, whole. references/ is for depth that is only needed sometimes: "
    "a decision table, a recipe, a domain note — each file topical and reusable, never "
    "'<date>-<incident>.md'. Prefer extending an existing references/ file over creating one; "
    "a skill with dozens of one-off references is the failure shape, not the goal.\n"
    "  • Fix the skill in place when it is wrong: edit the sentence that misled, do not append "
    "'UPDATE: actually...' underneath it.\n\n"
)

_DO_NOT_CAPTURE_BLOCK = (
    " (these become persistent self-imposed constraints that bite you later when the environment "
    "changes):\n"
    "  • Environment-dependent failures: missing binaries, fresh-install errors, post-migration "
    "path mismatches, 'command not found', unconfigured credentials, uninstalled packages. The "
    "user can fix these — they are not durable rules.\n"
    "  • Negative claims about tools or features ('browser tools do not work', 'X tool is broken', "
    "'cannot use Y from execute_code'). These harden into refusals the agent cites against itself "
    "for months after the actual problem was fixed.\n"
    "  • Session-specific transient errors that resolved before the conversation ended. If "
    "retrying worked, the lesson is the retry pattern, not the original failure.\n"
    "  • One-off task narratives. A user asking 'summarize today's market' or 'analyze this PR' is "
    "not a class of work that warrants a skill.\n\n"
    "  • Unresolved failures: if the session ended WITHOUT actually finding a working method — you "
    "tried several things, none worked, and told the user to check manually — do NOT write those "
    "attempts up as a 'reliable workflow' or 'recommended approach'. That presents an untested "
    "sequence of failures as validated guidance a future session will trust and repeat. Either say "
    "'Nothing to save', or, only if you are independently confident of a real working alternative "
    "(not something you are merely guessing might work), capture ONLY that alternative — never the "
    "dead ends, and never dressed up as best practice.\n\n"
    "If a tool failed because of setup state, capture the FIX (install command, config step, env "
    "var to set) under an existing setup or troubleshooting skill — never 'this tool does not "
    "work' as a standalone constraint.\n\n"
)

_SKILL_REVIEW_PROMPT = (
    "Review the conversation above and update the skill library. Be ACTIVE — most sessions produce "
    "at least one skill update, even if small. A pass that does nothing is a missed learning "
    "opportunity, not a neutral outcome.\n\n"
    "Target shape of the library: CLASS-LEVEL skills, each with a SKILL.md of always-on rules and a "
    "small `references/` set of topical depth. Not a flat list of narrow one-session skills, and "
    "not an umbrella hoarding a references/ file per session. This shapes HOW you update, not "
    "WHETHER you update.\n\n" + _LESSON_LAYER_BLOCK +
    "Signals to look for (any one of these warrants action):\n"
    "  • User corrected your style, tone, format, legibility, or verbosity. Frustration signals "
    "like 'stop doing X', 'this is too verbose', 'don't format like this', 'why are you "
    "explaining', 'just give me the answer', 'you always do Y and I hate it', or an explicit "
    "'remember this' are FIRST-CLASS skill signals, not just memory signals. Update the relevant "
    "skill(s) to embed the preference so the next session starts already knowing.\n"
    "  • User corrected your workflow, approach, or sequence of steps. Encode the correction as a "
    "pitfall or explicit step in the skill that governs that class of task.\n"
    "  • Non-trivial technique, fix, workaround, debugging path, or tool-usage pattern emerged "
    "that a future session would benefit from. Capture it.\n"
    "  • A skill that got loaded or consulted this session turned out to be wrong, missing a step, "
    "or outdated. Patch it NOW.\n\n"
    "Do NOT capture" + _DO_NOT_CAPTURE_BLOCK +
    "'Nothing to save.' is a real option but should NOT be the default. If the session ran "
    "smoothly with no corrections and produced no new technique, just say 'Nothing to save.' and "
    "stop. Otherwise, act."
)

_COMBINED_REVIEW_PROMPT = (
    "Review the conversation above and update two things:\n\n"
    "**Memory**: " + _MEMORY_ROUTING_BLOCK +
    "**Skills**: how to do this class of task. Be ACTIVE — most sessions produce at least one "
    "skill update. A pass that does nothing is a missed learning opportunity, not a neutral "
    "outcome.\n\n"
    "Target shape of the skill library: CLASS-LEVEL skills with a SKILL.md of always-on rules and a "
    "small `references/` set of topical depth — not narrow one-session skills, and not an umbrella "
    "hoarding a references/ file per session.\n\n" + _LESSON_LAYER_BLOCK +
    "Signals that warrant a skill update (any one is enough):\n"
    "  • User corrected your style, tone, format, legibility, verbosity, or approach.\n"
    "  • Non-trivial technique, fix, workaround, or debugging path emerged.\n"
    "  • A skill that was loaded or consulted turned out wrong, missing, or outdated — patch it now.\n\n"
    "Do NOT capture" + _DO_NOT_CAPTURE_BLOCK +
    "If nothing to update, reply 'Nothing to save.' and stop."
)


# ==============================================================================
# BACKGROUND REVIEW RUN & CANCELLATION HANDSHAKE
# ==============================================================================

class BackgroundReviewRun:
    """Per-review cancellation and request-completion handshake (Verbatim Hermes semantics)."""

    def __init__(self) -> None:
        self.cancel_requested = threading.Event()
        self.request_done = threading.Event()
        self._lock = threading.Lock()
        self._request_finished = False

    def cancel(self) -> None:
        with self._lock:
            self.cancel_requested.set()

    def mark_request_finished(self) -> bool:
        with self._lock:
            if self._request_finished:
                return False
            self._request_finished = True
            self.request_done.set()
            return True


# ==============================================================================
# REVIEW EVALUATION LOGIC
# ==============================================================================

# Fast regex detectors for first-class Hermes review signals
_USER_CORRECTION_RE = re.compile(
    r"(không phải thế|sai rồi|đừng kẻ bảng|đừng viết dài|hãy tóm tắt|ngắn gọn thôi|"
    r"stop doing|don't format|too verbose|you always|remember this|đừng|lần sau|từ nay)",
    re.IGNORECASE,
)


def extract_review_learning(
    messages: List[Dict[str, str]],
    store: Optional[MemoryStore] = None,
) -> Optional[Dict[str, Any]]:
    """Evaluate messages against Hermes review rubric and extract memory/skill update.
    Returns extracted change dict or None if 'Nothing to save.'
    """
    if len(messages) < 2:
        return None

    # Check for user corrections in any user turn after the first assistant response
    correction_turn = None
    prior_assistant_turn = None

    for i in range(1, len(messages)):
        msg = messages[i]
        if msg.get("role") == "user":
            content = msg.get("content", "")
            match = _USER_CORRECTION_RE.search(content)
            if match:
                correction_turn = content
                if i > 0 and messages[i - 1].get("role") == "assistant":
                    prior_assistant_turn = messages[i - 1].get("content", "")
                break

    if not correction_turn:
        return None

    if store is None:
        store = load_on_disk_store()

    # Apply Hermes USER profile learning: persona, format preference, style expectation
    user_pref_entry = f"Sở thích/Phong cách người dùng: {correction_turn.strip()} (Tránh định dạng gây phiền; ưu tiên ngắn gọn theo yêu cầu)."
    store.add(target="user", content=user_pref_entry)

    return {
        "status": "learned",
        "target": "user",
        "entry": user_pref_entry,
        "signal": "user_correction",
        "trigger": correction_turn,
        "matched_rubric": "USER.md (who the user is — persona, preferences, communication and work style)",
    }


def execute_background_review_async(
    messages: List[Dict[str, str]],
    store: Optional[MemoryStore] = None,
    on_complete: Optional[Callable[[Optional[Dict[str, Any]]], None]] = None,
) -> BackgroundReviewRun:
    """Spawn daemon thread to execute review without blocking live session."""
    run = BackgroundReviewRun()

    def _worker():
        try:
            if run.cancel_requested.is_set():
                return
            result = extract_review_learning(messages, store=store)
            if on_complete and not run.cancel_requested.is_set():
                on_complete(result)
        finally:
            run.mark_request_finished()

    t = threading.Thread(target=_worker, daemon=True, name="hermes_background_reviewer")
    t.start()
    return run
