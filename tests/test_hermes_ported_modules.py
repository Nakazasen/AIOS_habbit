"""Comprehensive behavioral verification suite for Hermes Ported Modules in AIOS.

Tests the 5 self-learning capabilities ported from Hermes Agent v0.21.6+724:
1. Memory store: ENTRY_DELIMITER ("\\n§\\n"), character budget overflow, atomic batch rollback, drift backup.
2. Skill manager: authoring standards, frontmatter validation (<=60 chars description), file hierarchy (references/, templates/, scripts/), patch/delete.
3. Skills curator: deterministic lifecycle (14d stale, 30d archive), pinned skill exemption, reactivation.
4. Post-session review: verbatim prompts (_MEMORY_ROUTING_BLOCK, _LESSON_LAYER_BLOCK, _DO_NOT_CAPTURE_BLOCK), signal extraction, cancellation handshake.
5. User profile / learning: build_learn_prompt, memory_fingerprint (SHA-256[:12]), build_learning_graph.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile
import pytest

from aios_habit.hermes_memory import (
    ENTRY_DELIMITER,
    MEMORY_BLOCK_HEADERS,
    MemoryStore,
    load_on_disk_store,
    memory_tool,
)
from aios_habit.hermes_skill_manager import (
    SKILL_PROMPT_DESC_LIMIT,
    create_skill,
    find_skill,
    get_skills_dir,
    parse_frontmatter,
    patch_skill,
    read_skill,
    skill_manage,
    write_supporting_file,
)
from aios_habit.hermes_curator import (
    DEFAULT_ARCHIVE_AFTER_DAYS,
    DEFAULT_STALE_AFTER_DAYS,
    STATE_ACTIVE,
    STATE_ARCHIVED,
    STATE_STALE,
    apply_automatic_transitions,
    archive_skill,
    curated_report,
    is_pinned,
    load_usage,
    record_skill_usage,
    restore_skill,
    set_pinned,
    set_state,
)
from aios_habit.hermes_post_session_review import (
    _COMBINED_REVIEW_PROMPT,
    _DO_NOT_CAPTURE_BLOCK,
    _LESSON_LAYER_BLOCK,
    _MEMORY_REVIEW_PROMPT,
    _MEMORY_ROUTING_BLOCK,
    _SKILL_REVIEW_PROMPT,
    BackgroundReviewRun,
    extract_review_learning,
)
from aios_habit.hermes_learning import (
    _AUTHORING_STANDARDS,
    _KNOWLEDGE_SKILL_STANDARDS,
    build_learn_prompt,
    build_learning_graph,
    memory_fingerprint,
    memory_node_id,
)

UTC = timezone.utc


@pytest.fixture
def temp_local_cases(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cases_dir = tmp_path / "local_cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(cases_dir))
    return cases_dir


# ==============================================================================
# 1. KHO NHỚ NGƯỜI DÙNG: ENTRY_DELIMITER ("\n§\n"), TRÀN KÝ TỰ & ATOMIC BATCH
# ==============================================================================

def test_hermes_memory_delimiter_and_overflow(temp_local_cases: Path):
    """Test Hermes memory delimiter, char limit overflow, replace and atomic batch."""
    assert ENTRY_DELIMITER == "\n§\n"
    assert "memory" in MEMORY_BLOCK_HEADERS
    assert "user" in MEMORY_BLOCK_HEADERS

    mem_dir = temp_local_cases / "memories"
    mem_dir.mkdir(parents=True, exist_ok=True)

    # 1. Add entry and verify delimiter on disk
    store = MemoryStore(memory_char_limit=100, user_char_limit=80, base_dir=mem_dir)
    res1 = store.add("memory", "First environmental fact: JIG_01 uses SMA20.")
    assert res1["success"] is True

    res2 = store.add("memory", "Second environmental fact: Camera is 12MP.")
    assert res2["success"] is True

    memory_file = mem_dir / "MEMORY.md"
    assert memory_file.exists()
    content = memory_file.read_text(encoding="utf-8")
    assert "\n§\n" in content
    assert "First environmental fact: JIG_01 uses SMA20." in content
    assert "Second environmental fact: Camera is 12MP." in content

    # Verify reload parses exactly 2 entries
    store.load_from_disk()
    assert len(store.memory_entries) == 2

    # 2. Test char limit overflow refusal
    huge_fact = "A" * 80
    overflow_res = store.add("memory", huge_fact)
    assert overflow_res["success"] is False
    assert "would exceed the limit" in overflow_res["error"]

    # 3. Test tolerant replace
    replace_res = store.replace("memory", "Camera is 12MP", "Camera is upgraded to 24MP.")
    assert replace_res["success"] is True
    updated_content = memory_file.read_text(encoding="utf-8")
    assert "Camera is upgraded to 24MP." in updated_content
    assert "Camera is 12MP." not in updated_content

    # 4. Test atomic batch: all-or-nothing
    batch_ops = [
        {"action": "add", "content": "Third entry."},
        {"action": "remove", "old_text": "Non-existent entry will cause failure."},
    ]
    batch_res = store.apply_batch("memory", batch_ops)
    assert batch_res["success"] is False
    assert "No operations were applied" in batch_res["error"]

    # Verify rollback: "Third entry." was NOT committed to disk
    store.load_from_disk()
    assert "Third entry." not in store.memory_entries

    # 5. Test system prompt snapshot rendering
    snapshot = store.format_for_system_prompt("memory")
    assert snapshot is not None
    assert "═" * 46 in snapshot
    assert "MEMORY (your personal notes)" in snapshot


def test_hermes_memory_tool_dispatch(temp_local_cases: Path):
    """Test tool wrapper memory_tool function."""
    mem_dir = temp_local_cases / "memories"
    store = MemoryStore(base_dir=mem_dir)
    store.load_from_disk()

    # Add to USER profile
    raw_res = memory_tool(action="add", target="user", content="User prefers concise answers.", store=store)
    res = json.loads(raw_res)
    assert res["success"] is True

    user_file = mem_dir / "USER.md"
    assert user_file.exists()
    assert "User prefers concise answers." in user_file.read_text(encoding="utf-8")


# ==============================================================================
# 2. KHO KỸ NĂNG: AUTHORING STANDARDS & SKILL MANAGE TOOL
# ==============================================================================

def test_hermes_skill_manager_authoring_standards(temp_local_cases: Path):
    """Test Hermes skill frontmatter validation and directory structure."""
    skills_dir = temp_local_cases / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    # 1. Reject skill description exceeding 60 characters
    long_desc_content = """---
name: test-overlength
description: This description is deliberately written way too long to exceed the sixty char budget.
---
# Procedure
1. Step one.
"""
    res_fail = create_skill("test-overlength", long_desc_content)
    assert res_fail["success"] is False
    assert f"{SKILL_PROMPT_DESC_LIMIT}-char system-prompt budget" in res_fail["error"]

    # 2. Accept valid skill with concise description
    valid_content = """---
name: troubleshooting-jig-sensor
description: Diagnose optical sensor errors on assembly JIG.
---
# JIG Sensor Troubleshooting
## When to Use
- Optical sensor yellow LED blinking.

## Procedure
1. Inspect 24V power rail.
2. Clean optical lens with isopropanol.
"""
    res_ok = create_skill("troubleshooting-jig-sensor", valid_content)
    assert res_ok["success"] is True
    skill_dir = skills_dir / "troubleshooting-jig-sensor"
    assert (skill_dir / "SKILL.md").exists()

    # 3. Add supporting reference file
    ref_res = write_supporting_file(
        "troubleshooting-jig-sensor",
        "references/error_codes.md",
        "# Error Code Table\n| Code | Cause |\n| E01 | Sensor disconnected |\n",
    )
    assert ref_res["success"] is True
    assert (skill_dir / "references" / "error_codes.md").exists()

    # 4. Patch skill procedure
    patch_res = patch_skill(
        "troubleshooting-jig-sensor",
        "Inspect 24V power rail.",
        "Inspect 24V power rail using multimeter pin 3.",
    )
    assert patch_res["success"] is True
    patched_body = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "multimeter pin 3" in patched_body

    # 5. Read skill
    read_res = read_skill("troubleshooting-jig-sensor")
    assert read_res["success"] is True
    assert "multimeter pin 3" in read_res["content"]


# ==============================================================================
# 3. CURATOR GOM/KHÓA LƯU TRỮ: VÒNG ĐỜI KỸ NĂNG & MIỄN TRỪ PINNED
# ==============================================================================

def test_hermes_curator_lifecycle_and_pinned_exemption(temp_local_cases: Path):
    """Test Hermes deterministic transitions: active -> stale -> archived, and pinned exemption."""
    skills_dir = temp_local_cases / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    # Create 3 skills
    create_skill("skill-normal", "---\nname: skill-normal\ndescription: Normal skill.\n---\nBody")
    create_skill("skill-stale-candidate", "---\nname: skill-stale-candidate\ndescription: Stale candidate.\n---\nBody")
    create_skill("skill-pinned-forever", "---\nname: skill-pinned-forever\ndescription: Pinned skill.\n---\nBody")

    # Record initial usage
    record_skill_usage("skill-normal")
    record_skill_usage("skill-stale-candidate")
    record_skill_usage("skill-pinned-forever")

    # Pin the third skill
    set_pinned("skill-pinned-forever", True)
    assert is_pinned("skill-pinned-forever") is True

    # Manipulate usage timestamps to simulate aging:
    # skill-normal: active 5 days ago
    # skill-stale-candidate: inactive 16 days ago (> 14d -> stale)
    # skill-pinned-forever: inactive 100 days ago (> 30d -> would be archived, BUT PINNED!)
    now = datetime.now(UTC)
    t_5d = (now - timedelta(days=5)).isoformat()
    t_16d = (now - timedelta(days=16)).isoformat()
    t_100d = (now - timedelta(days=100)).isoformat()

    usage = load_usage()
    usage["skill-normal"]["last_used_at"] = t_5d
    usage["skill-normal"]["last_activity_at"] = t_5d
    usage["skill-normal"]["created_at"] = t_5d
    usage["skill-normal"]["use_count"] = 1

    usage["skill-stale-candidate"]["last_used_at"] = t_16d
    usage["skill-stale-candidate"]["last_activity_at"] = t_16d
    usage["skill-stale-candidate"]["created_at"] = t_16d
    usage["skill-stale-candidate"]["use_count"] = 1

    usage["skill-pinned-forever"]["last_used_at"] = t_100d
    usage["skill-pinned-forever"]["last_activity_at"] = t_100d
    usage["skill-pinned-forever"]["created_at"] = t_100d
    usage["skill-pinned-forever"]["use_count"] = 1
    usage["skill-pinned-forever"]["pinned"] = True

    from aios_habit.hermes_curator import save_usage
    save_usage(usage)

    # 1. Run automatic transitions at now
    counts = apply_automatic_transitions(now=now)
    assert counts["marked_stale"] == 1
    assert counts["archived"] == 0

    reloaded_usage = load_usage()
    assert reloaded_usage["skill-normal"]["state"] == STATE_ACTIVE
    assert reloaded_usage["skill-stale-candidate"]["state"] == STATE_STALE
    # HERMES CRUCIAL INVARIANT: Pinned skill remains ACTIVE despite 100 days inactivity!
    assert reloaded_usage["skill-pinned-forever"]["state"] == STATE_ACTIVE
    assert (skills_dir / "skill-pinned-forever").exists()

    # 2. Advance time past 30 days for skill-stale-candidate (e.g. now + 20 days)
    future_now = now + timedelta(days=20)
    counts2 = apply_automatic_transitions(now=future_now)
    assert counts2["archived"] == 1

    reloaded_usage2 = load_usage()
    assert reloaded_usage2["skill-stale-candidate"]["state"] == STATE_ARCHIVED
    assert not (skills_dir / "skill-stale-candidate").exists()
    assert (skills_dir / ".archive" / "skill-stale-candidate").exists()

    # 3. Test restore from archive
    restore_ok, _ = restore_skill("skill-stale-candidate")
    assert restore_ok is True
    assert (skills_dir / "skill-stale-candidate").exists()
    assert load_usage()["skill-stale-candidate"]["state"] == STATE_ACTIVE


# ==============================================================================
# 4. RÀ SOÁT SAU PHIÊN: PROMPT VERBATIM & REVIEW EXTRACTION
# ==============================================================================

def test_hermes_post_session_review_prompts_and_execution(temp_local_cases: Path):
    """Test Hermes background review prompts and signal extraction into USER.md."""
    # Check verbatim prompt text presence
    assert "TWO distinct stores — pick the right one for each fact:" in _MEMORY_ROUTING_BLOCK
    assert "USER.md (memory tool, target='user'): who the user is" in _MEMORY_ROUTING_BLOCK
    assert "MEMORY.md (memory tool, target='memory'): facts about the ENVIRONMENT" in _MEMORY_ROUTING_BLOCK
    assert "What a skill IS: the instructions for doing a class of task" in _LESSON_LAYER_BLOCK
    assert "A pitfall is a generalizable rule + one clause of WHY" in _LESSON_LAYER_BLOCK
    assert "Environment-dependent failures" in _DO_NOT_CAPTURE_BLOCK
    assert "Review the conversation above and update the skill library." in _SKILL_REVIEW_PROMPT
    assert "Review the conversation above and update two things:" in _COMBINED_REVIEW_PROMPT

    mem_dir = temp_local_cases / "memories"
    store = MemoryStore(base_dir=mem_dir)
    store.load_from_disk()

    # Simulate conversation with user correction
    messages = [
        {"role": "user", "content": "Tóm tắt sự cố hôm qua của hệ thống máy dán nhãn"},
        {
            "role": "assistant",
            "content": "| STT | Thiết bị | Hiện tượng |\n|---|---|---|\n| 1 | Cụm cấp phôi | Kẹt nhãn |",
        },
        {
            "role": "user",
            "content": "Không phải thế, đừng kẻ bảng, hãy tóm tắt 3 gạch đầu dòng ngắn gọn thôi.",
        },
        {
            "role": "assistant",
            "content": "Tôi hiểu rồi. Tôi sẽ tóm tắt bằng 3 gạch đầu dòng.",
        },
    ]

    learning = extract_review_learning(messages, store=store)
    assert learning is not None
    assert learning["status"] == "learned"
    assert learning["target"] == "user"

    # Verify USER.md contains the extracted preference with \n§\n delimiter
    user_file = mem_dir / "USER.md"
    assert user_file.exists()
    content = user_file.read_text(encoding="utf-8")
    assert "Sở thích/Phong cách người dùng:" in content
    assert "đừng kẻ bảng" in content

    # Test BackgroundReviewRun cancellation
    run = BackgroundReviewRun()
    assert run.cancel_requested.is_set() is False
    run.cancel()
    assert run.cancel_requested.is_set() is True


# ==============================================================================
# 5. HỌC THÓI QUEN / HỒ SƠ & BẢNG ĐỒ TRI THỨC (LEARNING GRAPH)
# ==============================================================================

def test_hermes_learning_standards_and_graph(temp_local_cases: Path):
    """Test Hermes learn prompt authoring standards and learning graph assembly."""
    assert "Follow the Hermes skill-authoring standards exactly." in _AUTHORING_STANDARDS
    assert "description: ONE sentence, **<=60 characters**, ends with a period." in _AUTHORING_STANDARDS
    assert "Knowledge-base skills (books, paper stacks, large doc corpora, specs):" in _KNOWLEDGE_SKILL_STANDARDS

    # 1. Build learn prompt
    prompt = build_learn_prompt("plc-siemens-s7-1200", "PLC S7-1200 troubleshooting manual...")
    assert "You are creating a new skill for the topic: 'plc-siemens-s7-1200'." in prompt
    assert "Follow the Hermes skill-authoring standards exactly." in prompt

    # 2. Memory fingerprinting SHA-256[:12]
    text = "User prefers markdown lists over tables."
    fp = memory_fingerprint(text)
    assert len(fp) == 12
    card = {"source": "profile", "fingerprint": fp}
    node_id = memory_node_id(card, 0)
    assert node_id == f"memory:profile:0:{fp}"

    # 3. Create a skill and a memory entry, then build learning graph
    create_skill(
        "plc-inspection",
        "---\nname: plc-inspection\ndescription: Inspect Siemens S7 PLC diagnostic LEDs.\ncategory: automation\n---\n# Procedure\n1. Check SF LED.",
    )
    record_skill_usage("plc-inspection")

    mem_dir = temp_local_cases / "memories"
    store = MemoryStore(base_dir=mem_dir)
    store.add("user", "User prefers bullet points for PLC inspections.")

    graph = build_learning_graph()
    assert "nodes" in graph
    assert "edges" in graph
    assert "clusters" in graph
    assert "stats" in graph
    assert graph["stats"]["learned_skills"] >= 1
