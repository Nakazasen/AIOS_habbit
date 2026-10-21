"""Unit tests for ticket DESKTOP-SELF-LEARN-CURATOR-SKILLS-LOCAL-STORE.

Covers:
1. File locking (claim, collision, stale recovery, release).
2. Inactivity and interval gating (idle > 2h, interval >= 7d, deferred first run, force flag).
3. Deterministic pruning (stale after 14d, archive after 30d, reactivation).
4. Pinned skills bypass all pruning cycles.
5. User-created skills protected from auto-archiving.
6. Fail-closed safety guard on company knowledge partition.
7. Consolidation guard requiring absorbed_into pointer.
8. Skill tooling (list, restore from archive, pin/unpin).
9. Read-Before-Write guard preventing overwrite of manual human edits in Obsidian.
10. Second Brain Habit Journal vault setup (.obsidian/ config) and domain MOC sync.
11. Legacy data migration (verifying count before == count after).
12. Dual-read recall and supersede chain traversal.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

import pytest

from aios_habit.post_session_review import DRAFT_KIND_LESSON, DRAFT_KIND_SKILL, SecondBrainNote, now_iso
from aios_habit.skills_curator import (
    CLAIM_STALE_SECONDS,
    DEFAULT_ARCHIVE_AFTER_DAYS,
    DEFAULT_INTERVAL_HOURS,
    DEFAULT_MIN_IDLE_HOURS,
    DEFAULT_STALE_AFTER_DAYS,
    PARTITION_COMPANY_KNOWLEDGE,
    PARTITION_LOCAL_HABIT,
    STATE_ACTIVE,
    STATE_ARCHIVED,
    STATE_CONFIRMED,
    STATE_STALE,
    STATE_SUPERSEDED,
    CuratorRunReport,
    CuratorSafetyError,
    ManualEditConflictError,
    SecondBrainRecallEngine,
    SkillNotFoundError,
    SkillRecord,
    apply_automatic_transitions,
    assert_curator_safety,
    claim_run_lock,
    consolidate_skills,
    get_idle_seconds,
    get_skill,
    is_curator_paused,
    list_skills,
    load_curator_state,
    migrate_legacy_data,
    parse_skill_file,
    pin_skill,
    record_skill_usage,
    release_run_lock,
    restore_skill_from_archive,
    run_curator,
    save_curator_state,
    save_skill_to_store,
    set_curator_paused,
    setup_obsidian_vault,
    should_run_now,
    sync_all_domain_mocs,
)
from aios_habit.workspace_memory_models import (
    WorkspaceMemoryRecallItem,
    WorkspaceMemoryRecallRequest,
)
from aios_habit.workspace_memory_service import (
    load_live_catalog,
    recall_workspace_memory,
    set_workspace_memory_enabled_preference,
)


@pytest.fixture
def temp_curator_env(tmp_path: Path) -> Dict[str, Path]:
    """Create isolated test environment simulating local_cases."""
    local_cases = tmp_path / "local_cases"
    skills_dir = local_cases / "skills"
    second_brain = local_cases / "second_brain"
    workspace_mem = local_cases / "workspace_memory"

    skills_dir.mkdir(parents=True, exist_ok=True)
    second_brain.mkdir(parents=True, exist_ok=True)
    workspace_mem.mkdir(parents=True, exist_ok=True)

    # Set environment variable for psr
    os.environ["AIOS_LOCAL_CASES_DIR"] = str(local_cases)
    yield {
        "local_cases": local_cases,
        "skills_dir": skills_dir,
        "second_brain": second_brain,
        "workspace_memory": workspace_mem,
    }
    os.environ.pop("AIOS_LOCAL_CASES_DIR", None)


# ==============================================================================
# 1. FILE LOCKING & COLLISION TESTS
# ==============================================================================

def test_file_lock_lifecycle(temp_curator_env: Dict[str, Path]) -> None:
    skills_dir = temp_curator_env["skills_dir"]

    # First claim succeeds
    assert claim_run_lock(skills_dir) is True

    # Second claim from another runner fails (collision)
    assert claim_run_lock(skills_dir) is False

    # Release lock
    release_run_lock(skills_dir)

    # Claim succeeds again
    assert claim_run_lock(skills_dir) is True
    release_run_lock(skills_dir)


def test_stale_file_lock_recovery(temp_curator_env: Dict[str, Path]) -> None:
    skills_dir = temp_curator_env["skills_dir"]
    lock_file = skills_dir / ".locks" / "curator-run.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)

    # Create fake abandoned lock with mtime 2 hours ago
    lock_file.write_text("pid=99999\ntimestamp=old\n", encoding="utf-8")
    past_time = time.time() - (CLAIM_STALE_SECONDS + 500)
    os.utime(lock_file, (past_time, past_time))

    # claim_run_lock should detect stale lock, break it, and acquire
    assert claim_run_lock(skills_dir) is True
    release_run_lock(skills_dir)


# ==============================================================================
# 2. INACTIVITY & INTERVAL GATING TESTS
# ==============================================================================

def test_gating_deferred_on_first_run(temp_curator_env: Dict[str, Path]) -> None:
    skills_dir = temp_curator_env["skills_dir"]
    local_cases = temp_curator_env["local_cases"]
    now = datetime(2026, 10, 21, 10, 0, 0, tzinfo=timezone.utc)

    # First time run: last_run_at is None
    # Should seed last_run_at to now and defer execution (returns False)
    assert should_run_now(skills_dir, local_cases_dir=local_cases, now=now, idle_for_seconds=3.0 * 3600) is False

    state = load_curator_state(skills_dir)
    assert state["last_run_at"] is not None
    assert "deferred first run" in state["last_run_summary"]


def test_gating_inactivity_and_interval_checks(temp_curator_env: Dict[str, Path]) -> None:
    skills_dir = temp_curator_env["skills_dir"]
    local_cases = temp_curator_env["local_cases"]

    start = datetime(2026, 10, 1, 10, 0, 0, tzinfo=timezone.utc)
    save_curator_state(skills_dir, {"last_run_at": start.isoformat()})

    # Case A: Machine NOT idle enough (only 1 hour < 2 hours) -> reject
    check_date = start + timedelta(days=8)
    assert should_run_now(skills_dir, local_cases_dir=local_cases, now=check_date, idle_for_seconds=1.0 * 3600) is False

    # Case B: Interval NOT elapsed enough (only 3 days < 7 days), even if idle 5h -> reject
    check_date = start + timedelta(days=3)
    assert should_run_now(skills_dir, local_cases_dir=local_cases, now=check_date, idle_for_seconds=5.0 * 3600) is False

    # Case C: Both idle >= 2h AND interval >= 7d -> ACCEPT
    check_date = start + timedelta(days=7, hours=1)
    assert should_run_now(skills_dir, local_cases_dir=local_cases, now=check_date, idle_for_seconds=2.5 * 3600) is True

    # Case D: Force flag bypasses all gates
    assert should_run_now(skills_dir, local_cases_dir=local_cases, force=True) is True

    # Case E: Paused curator never runs automatically
    set_curator_paused(skills_dir, True)
    assert should_run_now(skills_dir, local_cases_dir=local_cases, now=check_date, idle_for_seconds=5.0 * 3600) is False


# ==============================================================================
# 3. DETERMINISTIC PRUNING & ARCHIVING TESTS
# ==============================================================================

def test_deterministic_pruning_stale_and_archive(temp_curator_env: Dict[str, Path]) -> None:
    skills_dir = temp_curator_env["skills_dir"]
    base_time = datetime(2026, 10, 21, 12, 0, 0, tzinfo=timezone.utc)

    # Create 3 skills with different ages:
    # 1. Fresh skill (used 3 days ago) -> should remain ACTIVE
    skill_fresh = SkillRecord(
        name="skill_lsu_fresh",
        title="Căn chỉnh LSU tươi",
        mien="lsu",
        created_at=(base_time - timedelta(days=5)).isoformat(),
        updated_at=(base_time - timedelta(days=3)).isoformat(),
        last_activity_at=(base_time - timedelta(days=3)).isoformat(),
        state=STATE_ACTIVE,
    )
    save_skill_to_store(skill_fresh, skills_dir=skills_dir)

    # 2. Stale skill (used 18 days ago > 14 days) -> should become STALE
    skill_stale = SkillRecord(
        name="skill_optical_stale",
        title="Quang học cũ",
        mien="lsu",
        created_at=(base_time - timedelta(days=20)).isoformat(),
        updated_at=(base_time - timedelta(days=18)).isoformat(),
        last_activity_at=(base_time - timedelta(days=18)).isoformat(),
        state=STATE_ACTIVE,
    )
    save_skill_to_store(skill_stale, skills_dir=skills_dir)

    # 3. Ancient skill (used 35 days ago > 30 days) -> should be ARCHIVED into .archive/
    skill_ancient = SkillRecord(
        name="skill_ancient_sensor",
        title="Sensor thời tiền sử",
        mien="dieutraloi",
        created_at=(base_time - timedelta(days=40)).isoformat(),
        updated_at=(base_time - timedelta(days=35)).isoformat(),
        last_activity_at=(base_time - timedelta(days=35)).isoformat(),
        state=STATE_ACTIVE,
    )
    save_skill_to_store(skill_ancient, skills_dir=skills_dir)

    # Run transitions
    report = apply_automatic_transitions(skills_dir, now=base_time)
    counts = report["counts"]

    assert counts["checked"] == 3
    assert counts["marked_stale"] == 1
    assert counts["archived"] == 1

    # Verify states on disk
    rec_fresh = get_skill("skill_lsu_fresh", skills_dir=skills_dir)
    assert rec_fresh is not None
    assert rec_fresh.state == STATE_ACTIVE
    assert (skills_dir / "skill_lsu_fresh").exists()

    rec_stale = get_skill("skill_optical_stale", skills_dir=skills_dir)
    assert rec_stale is not None
    assert rec_stale.state == STATE_STALE
    assert (skills_dir / "skill_optical_stale").exists()

    # Ancient skill must be in .archive/ and NOT in main skills dir
    assert not (skills_dir / "skill_ancient_sensor").exists()
    archived_path = skills_dir / ".archive" / "skill_ancient_sensor"
    assert archived_path.exists()
    rec_archived = get_skill("skill_ancient_sensor", skills_dir=skills_dir)
    assert rec_archived is not None
    assert rec_archived.state == STATE_ARCHIVED


def test_reactivation_of_stale_skill(temp_curator_env: Dict[str, Path]) -> None:
    skills_dir = temp_curator_env["skills_dir"]
    base_time = datetime(2026, 10, 21, 12, 0, 0, tzinfo=timezone.utc)

    # Create stale skill
    skill = SkillRecord(
        name="skill_stale_then_used",
        title="Kỹ năng dùng lại",
        mien="general",
        state=STATE_STALE,
        created_at=(base_time - timedelta(days=20)).isoformat(),
        last_activity_at=(base_time - timedelta(days=18)).isoformat(),
    )
    save_skill_to_store(skill, skills_dir=skills_dir)

    # Record usage today
    record_skill_usage("skill_stale_then_used", skills_dir=skills_dir)

    rec = get_skill("skill_stale_then_used", skills_dir=skills_dir)
    assert rec is not None
    assert rec.state == STATE_ACTIVE
    assert rec.use_count == 1


# ==============================================================================
# 4. PINNED & USER-CREATED SKILLS PROTECTION TESTS
# ==============================================================================

def test_pinned_skills_bypass_pruning(temp_curator_env: Dict[str, Path]) -> None:
    skills_dir = temp_curator_env["skills_dir"]
    base_time = datetime(2026, 10, 21, 12, 0, 0, tzinfo=timezone.utc)

    # Create a PINNED skill that has been unused for 60 days
    pinned_skill = SkillRecord(
        name="skill_safety_emergency_stop",
        title="Dừng khẩn cấp an toàn",
        mien="general",
        pinned=True,
        state=STATE_ACTIVE,
        created_at=(base_time - timedelta(days=70)).isoformat(),
        last_activity_at=(base_time - timedelta(days=60)).isoformat(),
    )
    save_skill_to_store(pinned_skill, skills_dir=skills_dir)

    report = apply_automatic_transitions(skills_dir, now=base_time)
    assert report["counts"]["pinned_bypassed"] == 1
    assert report["counts"]["archived"] == 0
    assert report["counts"]["marked_stale"] == 0

    # Pinned skill remains active in root skills_dir
    rec = get_skill("skill_safety_emergency_stop", skills_dir=skills_dir)
    assert rec is not None
    assert rec.state == STATE_ACTIVE
    assert rec.pinned is True
    assert (skills_dir / "skill_safety_emergency_stop").exists()


def test_user_created_skill_protection(temp_curator_env: Dict[str, Path]) -> None:
    skills_dir = temp_curator_env["skills_dir"]
    base_time = datetime(2026, 10, 21, 12, 0, 0, tzinfo=timezone.utc)

    # Skill written directly by human user
    human_skill = SkillRecord(
        name="skill_human_master_rule",
        title="Quy tắc do kỹ sư viết tay",
        mien="mom_opcenter",
        created_by="user",
        state=STATE_ACTIVE,
        created_at=(base_time - timedelta(days=50)).isoformat(),
        last_activity_at=(base_time - timedelta(days=45)).isoformat(),
    )
    save_skill_to_store(human_skill, skills_dir=skills_dir)

    report = apply_automatic_transitions(skills_dir, now=base_time)
    assert report["counts"]["archived"] == 0

    rec = get_skill("skill_human_master_rule", skills_dir=skills_dir)
    assert rec is not None
    assert (skills_dir / "skill_human_master_rule").exists()


# ==============================================================================
# 5. FAIL-CLOSED SAFETY GUARD TESTS
# ==============================================================================

def test_fail_closed_guard_blocks_company_knowledge(temp_curator_env: Dict[str, Path]) -> None:
    # Attempting to declare company_knowledge partition in curator operations must raise
    with pytest.raises(CuratorSafetyError, match="Refusing to modify company knowledge"):
        assert_curator_safety(
            target_path="local_cases/skills/test",
            partition=PARTITION_COMPANY_KNOWLEDGE,
        )

    # Attempting to target 05_memory_vault must raise
    with pytest.raises(CuratorSafetyError, match="Direct write to 05_memory_vault blocked"):
        assert_curator_safety(
            target_path="D:/Sandbox/AIOS_habbit/05_memory_vault/sop_01.md",
            partition=PARTITION_LOCAL_HABIT,
        )


# ==============================================================================
# 6. CONSOLIDATION GUARD TESTS
# ==============================================================================

def test_consolidation_requires_absorbed_into_and_preserves_data(temp_curator_env: Dict[str, Path]) -> None:
    skills_dir = temp_curator_env["skills_dir"]

    # Create umbrella skill
    umbrella = SkillRecord(
        name="skill_lsu_tuning_umbrella",
        title="Quy trình tổng thể căn chỉnh LSU",
        mien="lsu",
        content_body="# Quy trình tổng thể căn chỉnh LSU\n\nNội dung ô dù chính.",
    )
    save_skill_to_store(umbrella, skills_dir=skills_dir)

    # Create narrow redundant skill
    narrow = SkillRecord(
        name="skill_lsu_micro_screw",
        title="Chỉnh ốc vi sai LSU",
        mien="lsu",
        content_body="# Chỉnh ốc vi sai\nVặn 1/4 vòng.",
    )
    save_skill_to_store(narrow, skills_dir=skills_dir)

    # Consolidate narrow -> umbrella
    consolidate_skills(
        absorbed_name="skill_lsu_micro_screw",
        target_umbrella_name="skill_lsu_tuning_umbrella",
        reason="Kỹ năng quá hẹp, gom vào quy trình căn chỉnh tổng thể",
        skills_dir=skills_dir,
    )

    # Verify narrow skill is moved to .archive/ with absorbed_into recorded
    archived_md = skills_dir / ".archive" / "skill_lsu_micro_screw" / "SKILL.md"
    assert archived_md.exists()
    absorbed_rec = parse_skill_file(archived_md)
    assert absorbed_rec.absorbed_into == "skill_lsu_tuning_umbrella"
    assert absorbed_rec.state == STATE_SUPERSEDED

    # Verify umbrella skill has reference and link to absorbed skill
    updated_umbrella = get_skill("skill_lsu_tuning_umbrella", skills_dir=skills_dir)
    assert updated_umbrella is not None
    assert "[[skill_lsu_micro_screw]]" in updated_umbrella.links
    assert "Đã tiếp thu kỹ năng con: [[skill_lsu_micro_screw]]" in updated_umbrella.content_body


def test_consolidation_into_nonexistent_umbrella_fails_closed(temp_curator_env: Dict[str, Path]) -> None:
    skills_dir = temp_curator_env["skills_dir"]
    skill = SkillRecord(name="skill_orphan", title="Orphan", mien="general")
    save_skill_to_store(skill, skills_dir=skills_dir)

    with pytest.raises(SkillNotFoundError):
        consolidate_skills("skill_orphan", "non_existent_umbrella", skills_dir=skills_dir)


# ==============================================================================
# 7. TOOLING (LIST, RESTORE, PIN) TESTS
# ==============================================================================

def test_restore_from_archive(temp_curator_env: Dict[str, Path]) -> None:
    skills_dir = temp_curator_env["skills_dir"]

    # Create archived skill directly
    archive_dir = skills_dir / ".archive" / "skill_archived_to_restore"
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "SKILL.md").write_text(
        "---\nid: skill_archived_to_restore\ntitle: Phục hồi tôi đi\nkind: skill\nmien: lsu\ntrang_thai: archived\n---\n\nNội dung cần phục hồi.",
        encoding="utf-8",
    )

    # Verify listed in archive
    archived_skills = list_skills(skills_dir=skills_dir, state=STATE_ARCHIVED)
    assert any(s.name == "skill_archived_to_restore" for s in archived_skills)

    # Restore
    restored = restore_skill_from_archive("skill_archived_to_restore", skills_dir=skills_dir)
    assert restored.state == STATE_ACTIVE
    assert not archive_dir.exists()
    assert (skills_dir / "skill_archived_to_restore").exists()


def test_pin_and_unpin_tool(temp_curator_env: Dict[str, Path]) -> None:
    skills_dir = temp_curator_env["skills_dir"]
    skill = SkillRecord(name="skill_toggle_pin", title="Toggle pin", mien="general", pinned=False)
    save_skill_to_store(skill, skills_dir=skills_dir)

    # Pin
    pinned = pin_skill("skill_toggle_pin", pinned=True, skills_dir=skills_dir)
    assert pinned.pinned is True

    rec = get_skill("skill_toggle_pin", skills_dir=skills_dir)
    assert rec is not None and rec.pinned is True

    # Unpin
    unpinned = pin_skill("skill_toggle_pin", pinned=False, skills_dir=skills_dir)
    assert unpinned.pinned is False


# ==============================================================================
# 8. READ-BEFORE-WRITE MANUAL EDIT PROTECTION TESTS
# ==============================================================================

def test_read_before_write_conflict_guard(temp_curator_env: Dict[str, Path]) -> None:
    skills_dir = temp_curator_env["skills_dir"]
    skill = SkillRecord(name="skill_human_edited", title="Gốc", mien="general", content_body="Gốc")
    target_md = save_skill_to_store(skill, skills_dir=skills_dir)

    # Compute original hash
    orig_hash = "fake_wrong_hash"

    # Saving with mismatched expected_hash must raise ManualEditConflictError
    with pytest.raises(ManualEditConflictError, match="Manual edit conflict detected"):
        save_skill_to_store(skill, skills_dir=skills_dir, expected_hash=orig_hash)


# ==============================================================================
# 9. SECOND BRAIN OBSIDIAN VAULT & MOC SYNC TESTS
# ==============================================================================

def test_setup_obsidian_vault_and_moc_sync(temp_curator_env: Dict[str, Path]) -> None:
    second_brain = temp_curator_env["second_brain"]
    skills_dir = temp_curator_env["skills_dir"]

    # Run vault setup
    setup_obsidian_vault(second_brain, skills_dir=skills_dir)
    assert (second_brain / ".obsidian" / "app.json").exists()
    assert (second_brain / ".obsidian" / "graph.json").exists()

    # Create sample skills and lessons
    sk = SkillRecord(name="skill_beam_calib", title="Căn chỉnh chùm tia", mien="lsu", state=STATE_ACTIVE)
    save_skill_to_store(sk, skills_dir=skills_dir)

    lessons_dir = second_brain / "lessons"
    lessons_dir.mkdir(parents=True, exist_ok=True)
    lesson_note = SecondBrainNote(
        id="LESSON-001",
        title="Kiểm tra cảm biến trước",
        kind=DRAFT_KIND_LESSON,
        created=now_iso(),
        updated=now_iso(),
        mien="lsu",
        applies_when="Khi chùm tia lệch",
        trang_thai=STATE_CONFIRMED,
        links=["[[lsu_MOC]]", "[[skill_beam_calib]]"],
        content_body="# Bài học 001\nCần đối chiếu cảm biến.",
    )
    (lessons_dir / "LESSON-001.md").write_text(lesson_note.to_markdown(), encoding="utf-8")

    # Sync MOCs
    mocs = sync_all_domain_mocs(second_brain, skills_dir=skills_dir)
    assert len(mocs) >= 4  # lsu, dieutraloi, mom_opcenter, general

    lsu_moc = second_brain / "lsu_MOC.md"
    assert lsu_moc.exists()
    content = lsu_moc.read_text(encoding="utf-8")
    assert "[[skill_beam_calib]]: Căn chỉnh chùm tia (active)" in content
    assert "[[LESSON-001]]: Kiểm tra cảm biến trước (confirmed)" in content


# ==============================================================================
# 10. LEGACY DATA MIGRATION TESTS
# ==============================================================================

def test_legacy_data_migration(temp_curator_env: Dict[str, Path]) -> None:
    local_cases = temp_curator_env["local_cases"]
    wm_dir = temp_curator_env["workspace_memory"]

    # Seed 1 memory decision
    dec_file = wm_dir / "memory_decisions.jsonl"
    dec_data = {
        "decision_id": "dec_test1",
        "memory_id": "mem_01",
        "action": "confirm",
        "statement": "Luôn ngắt điện trước khi mở nắp LSU",
        "scope": "workspace:lsu",
        "created_at": "2026-10-20T08:00:00+00:00",
        "title": "Ngắt điện LSU",
    }
    dec_file.write_text(json.dumps(dec_data) + "\n", encoding="utf-8")

    # Seed 2 learning cards
    cards_file = local_cases / "learning_cards.jsonl"
    c1 = {
        "learning_id": "LRN-C1",
        "case_id": "CASE-101",
        "symptoms": "LSU beam tilt 0.5 deg",
        "true_cause": "Lỏng ốc M3",
        "reusable_lesson": "Xiết ốc M3 lực 0.4Nm",
        "confidence": "high",
        "created_at": "2026-06-20T10:00:00",
    }
    c2 = {
        "learning_id": "LRN-C2",
        "case_id": "CASE-102",
        "symptoms": "Kẹt job MES_SYNC",
        "true_cause": "Deadlock bảng",
        "reusable_lesson": "Xóa job treo trong MES_SYNC_LOG",
        "confidence": "confirmed",
        "created_at": "2026-06-21T10:00:00",
    }
    cards_file.write_text(json.dumps(c1) + "\n" + json.dumps(c2) + "\n", encoding="utf-8")

    # Run migration
    summary = migrate_legacy_data(local_cases_dir=local_cases)

    assert summary["input_decisions_count"] == 1
    assert summary["input_cards_count"] == 2
    assert summary["total_inputs"] == 3
    assert summary["migrated_lessons_saved"] == 3

    # Check migrated files exist
    sb_lessons = local_cases / "second_brain" / "lessons"
    assert (sb_lessons / "LESSON-DEC_TEST1.md").exists()
    assert (sb_lessons / "LESSON-LRN-C1.md").exists()
    assert (sb_lessons / "LESSON-LRN-C2.md").exists()

    # Verify content of migrated decision
    dec_note = SecondBrainNote.from_markdown((sb_lessons / "LESSON-DEC_TEST1.md").read_text(encoding="utf-8"))
    assert dec_note.title == "Ngắt điện LSU"
    assert dec_note.mien == "lsu"
    assert dec_note.trang_thai == STATE_CONFIRMED


# ==============================================================================
# 11. DUAL-READ RECALL & SUPERSEDE CHAIN TRAVERSAL TESTS
# ==============================================================================

def test_dual_read_and_supersede_chain(temp_curator_env: Dict[str, Path]) -> None:
    second_brain = temp_curator_env["second_brain"]
    lessons_dir = second_brain / "lessons"
    lessons_dir.mkdir(parents=True, exist_ok=True)

    # Note A: Old superseded note
    note_a = SecondBrainNote(
        id="LESSON-OLD-01",
        title="Quy tắc cũ về van khí",
        kind=DRAFT_KIND_LESSON,
        created=now_iso(),
        updated=now_iso(),
        mien="mom_opcenter",
        applies_when="van khí nén",
        trang_thai=STATE_SUPERSEDED,
        superseded_by="LESSON-NEW-02",
        content_body="Quy tắc cũ không còn áp dụng.",
    )
    (lessons_dir / "LESSON-OLD-01.md").write_text(note_a.to_markdown(), encoding="utf-8")

    # Note B: New active note superseding A
    note_b = SecondBrainNote(
        id="LESSON-NEW-02",
        title="Quy tắc mới về van khí xả áp",
        kind=DRAFT_KIND_LESSON,
        created=now_iso(),
        updated=now_iso(),
        mien="mom_opcenter",
        applies_when="van khí nén",
        trang_thai=STATE_CONFIRMED,
        supersedes="LESSON-OLD-01",
        content_body="Phải xả áp bình tích trước khi vặn van.",
    )
    (lessons_dir / "LESSON-NEW-02.md").write_text(note_b.to_markdown(), encoding="utf-8")

    engine = SecondBrainRecallEngine(vault_dir=second_brain)

    # Supersede traversal: resolving LESSON-OLD-01 returns LESSON-NEW-02
    resolved = engine.resolve_active_note("LESSON-OLD-01")
    assert resolved is not None
    assert resolved.id == "LESSON-NEW-02"

    # Recall returns only active/confirmed notes matching query
    results = engine.recall_notes(domain="mom_opcenter", query="van khí nén xả áp")
    assert len(results) == 1
    assert results[0].id == "LESSON-NEW-02"
    assert results[0].trang_thai == STATE_CONFIRMED


# ==============================================================================
# 12. FULL CURATOR RUN ORCHESTRATION & STATE TRACKING
# ==============================================================================

def test_full_curator_run_orchestration(temp_curator_env: Dict[str, Path]) -> None:
    skills_dir = temp_curator_env["skills_dir"]
    local_cases = temp_curator_env["local_cases"]

    # Create a stale skill
    base_time = datetime(2026, 10, 21, 12, 0, 0, tzinfo=timezone.utc)
    old_skill = SkillRecord(
        name="skill_old_jig",
        title="Jig cũ",
        mien="general",
        state=STATE_ACTIVE,
        created_at=(base_time - timedelta(days=25)).isoformat(),
        last_activity_at=(base_time - timedelta(days=20)).isoformat(),
    )
    save_skill_to_store(old_skill, skills_dir=skills_dir)

    # Trigger curator with force=True
    report = run_curator(skills_dir=skills_dir, local_cases_dir=local_cases, force=True, now=base_time)
    assert report is not None
    assert report.checked_count == 1
    assert report.marked_stale_count == 1
    assert "Curator run completed" in report.summary

    # Check state file .curator_state
    state = load_curator_state(skills_dir)
    assert state["run_count"] >= 1
    assert state["stale_count"] == 1
    assert state["last_run_at"] is not None

    # Check ledger .curator_ledger.jsonl
    ledger = skills_dir / ".curator_ledger.jsonl"
    assert ledger.exists()
    lines = ledger.read_text(encoding="utf-8").splitlines()
    assert any("auto_stale" in line for line in lines)
