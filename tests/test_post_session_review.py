"""Unit and integration tests for Post-Session Reviewer & Adaptive Self-Learning.

Covers:
1. Signal detection (user correction, dislike with reason, repeated investigation)
2. Hermes rubric (distinguishing Lesson vs Skill)
3. Second Brain Habit Journal Standard (YAML frontmatter, wikilinks, domain MOC)
4. Read-before-write guard on skills
5. Staging auto-drafts into 'Sửa để AIOS học' UI
6. Background daemon thread execution & preemption/cancellation
7. Master switch & habit profiles wipe
8. Expanded 'Vì sao AIOS nhớ điều này?' panel with applied skills
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from aios_habit.post_session_review import (
    DRAFT_KIND_LESSON,
    DRAFT_KIND_SKILL,
    REASON_CAT_SAI,
    REASON_CAT_KHO_HIEU,
    SIGNAL_DISLIKE_WITH_REASON,
    SIGNAL_REPEATED_INVESTIGATION,
    SIGNAL_USER_CORRECTION,
    BackgroundReviewRun,
    LearningSignal,
    SecondBrainNote,
    cancel_active_review,
    classify_draft_kind,
    detect_learning_signals,
    get_master_self_learn_preference,
    list_local_skills,
    read_skill_before_write,
    save_note_to_vault,
    set_master_self_learn_preference,
    spawn_post_session_review,
    stage_draft_into_pending_form,
    synthesize_draft,
    update_domain_moc,
    wipe_all_habit_profiles,
)
from aios_habit.workspace_memory_models import (
    SOURCE_KIND_SKILL,
    WorkspaceMemoryRecallItem,
)
from aios_habit.workspace_memory_service import (
    load_pending_drafts,
    recall_workspace_memory,
)
from aios_habit.workspace_memory_ui import (
    format_why_memory_lines,
    master_self_learn_toggle_help,
    master_self_learn_toggle_label,
    restore_pending_drafts_to_session_state,
    why_memory_panel_title,
    wipe_habit_profiles_button_label,
)


class DummyMessage:
    def __init__(self, role: str, content: str, msg_id: str = "msg_1", trace_id: str | None = None) -> None:
        self.role = role
        self.content = content
        self.id = msg_id
        self.trace_id = trace_id


# ==============================================================================
# 1. SIGNAL DETECTION TESTS
# ==============================================================================

def test_detect_user_correction_signals() -> None:
    """Detect when user corrects assistant's answer or style in follow-up."""
    # Test case A: User complains about tables and wants bullets
    messages = [
        DummyMessage("user", "Hãy tóm tắt sự cố hôm qua", "u1"),
        DummyMessage("assistant", "| Bảng mã lỗi | Hiện tượng |\n|---|---|\n| E-01 | Kẹt giấy |", "a1"),
        DummyMessage("user", "Không phải thế, đừng kẻ bảng, hãy tóm tắt 3 gạch đầu dòng ngắn gọn", "u2"),
    ]
    signals = detect_learning_signals(messages, domain="dieutraloi")
    assert len(signals) >= 1
    sig = signals[0]
    assert sig.signal_type == SIGNAL_USER_CORRECTION
    assert sig.message_id == "a1"
    assert "đừng kẻ bảng" in sig.raw_text.lower()


def test_detect_dislike_with_reason_signals() -> None:
    """Detect when user gave negative rating with specific reason category."""
    feedback = [
        {
            "rating": "chua_huu_ich",
            "reason_category": REASON_CAT_SAI,
            "reason": "Dung sai cho phép là ±0.02 mm chứ không phải ±0.05 mm như đã trả lời.",
            "message_id": "msg_asst_10",
            "domain": "lsu",
        }
    ]
    messages = [
        DummyMessage("user", "Dung sai Jig 1002 là bao nhiêu?", "u1"),
        DummyMessage("assistant", "Dung sai là ±0.05 mm.", "msg_asst_10"),
    ]
    signals = detect_learning_signals(messages, feedback_records=feedback, domain="lsu")
    dislike_sigs = [s for s in signals if s.signal_type == SIGNAL_DISLIKE_WITH_REASON]
    assert len(dislike_sigs) == 1
    ds = dislike_sigs[0]
    assert ds.reason_category == REASON_CAT_SAI
    assert "±0.02" in ds.raw_text
    assert ds.domain == "lsu"


def test_detect_repeated_investigation_signals() -> None:
    """Detect recurring investigation patterns (4M, error codes, sensor check)."""
    messages = [
        DummyMessage("user", "Kiểm tra mã lỗi E-041 theo 4M", "u1"),
        DummyMessage("assistant", "Đang tra cứu...", "a1"),
        DummyMessage("user", "Kiểm tra yếu tố Machine và sensor log", "u2"),
        DummyMessage("assistant", "Đang đọc sensor log...", "a2"),
        DummyMessage("user", "Đối sách nguyên nhân gốc và lập biên bản sự cố", "u3"),
        DummyMessage("assistant", "Đã lập xong biên bản.", "a3"),
    ]
    signals = detect_learning_signals(messages, domain="dieutraloi")
    inv_sigs = [s for s in signals if s.signal_type == SIGNAL_REPEATED_INVESTIGATION]
    assert len(inv_sigs) >= 1
    assert inv_sigs[0].domain == "dieutraloi"


# ==============================================================================
# 2. HERMES RUBRIC TESTS (LESSON VS SKILL)
# ==============================================================================

def test_rubric_classification_lesson_for_style_and_formatting() -> None:
    """Formatting, verbosity, and style corrections classify as LESSON."""
    sig = LearningSignal(
        signal_type=SIGNAL_USER_CORRECTION,
        raw_text="Đừng vẽ bảng, hãy tóm tắt 3 gạch đầu dòng ngắn gọn",
        domain="dieutraloi",
        message_id="a1",
    )
    kind = classify_draft_kind(sig)
    assert kind == DRAFT_KIND_LESSON

    draft = synthesize_draft(sig, [])
    assert draft.kind == DRAFT_KIND_LESSON
    assert "thói quen" in draft.title.lower() or "định dạng" in draft.title.lower()
    assert draft.trang_thai == "draft"
    assert draft.partition == "local_habit"
    assert "[[dieutraloi_MOC]]" in draft.links


def test_rubric_classification_skill_for_multistep_procedure() -> None:
    """Multi-step workflows classify as SKILL with procedure and supporting files."""
    sig = LearningSignal(
        signal_type=SIGNAL_USER_CORRECTION,
        raw_text="Quy trình phải là: Bước 1 kiểm tra áp suất, Bước 2 xả bình tích, Bước 3 mới mở van.",
        domain="mom_opcenter",
        message_id="a2",
    )
    kind = classify_draft_kind(sig)
    assert kind == DRAFT_KIND_SKILL

    draft = synthesize_draft(sig, [])
    assert draft.kind == DRAFT_KIND_SKILL
    assert "quy trình" in draft.title.lower()
    assert draft.trang_thai == "draft"
    assert "Procedure First" in draft.content_body
    assert "Pitfalls" in draft.content_body
    assert len(draft.supporting_files) >= 1


# ==============================================================================
# 3. SECOND BRAIN HABIT JOURNAL STANDARD
# ==============================================================================

def test_second_brain_note_markdown_roundtrip() -> None:
    """Atomic note correctly formats YAML frontmatter and parses back without loss."""
    note = SecondBrainNote(
        id="LESSON-20261020-001",
        title="Không vẽ bảng khi tóm tắt báo cáo",
        kind=DRAFT_KIND_LESSON,
        created="2026-10-20T15:00:00+07:00",
        updated="2026-10-20T15:00:00+07:00",
        mien="dieutraloi",
        applies_when="Khi tóm tắt sự cố",
        does_not_apply_when="Khi xuất báo cáo Excel",
        trang_thai="draft",
        evidence_refs=["conv:C1", "msg:M1"],
        partition="local_habit",
        links=["[[dieutraloi_MOC]]", "[[SKILL-4M]]"],
        content_body="# Không vẽ bảng\n\n## Quy tắc\nDùng gạch đầu dòng.\n",
    )
    md_text = note.to_markdown()
    assert md_text.startswith("---\n")
    assert "partition: local_habit" in md_text
    assert "trang_thai: draft" in md_text
    assert "[[dieutraloi_MOC]]" in md_text

    # Parse back
    restored = SecondBrainNote.from_markdown(md_text)
    assert restored.id == note.id
    assert restored.title == note.title
    assert restored.kind == DRAFT_KIND_LESSON
    assert restored.mien == "dieutraloi"
    assert restored.partition == "local_habit"
    assert "[[SKILL-4M]]" in restored.links


def test_update_domain_moc_creates_and_updates(tmp_path: Path) -> None:
    """Domain Map of Content page is created and keeps wikilinks up to date."""
    moc_file = update_domain_moc(
        domain="lsu",
        note_id="SKILL-LSU-BEAM-01",
        title="Căn chỉnh Beam LSU",
        kind=DRAFT_KIND_SKILL,
        status="draft",
        vault_dir=tmp_path,
    )
    assert moc_file.exists()
    content = moc_file.read_text(encoding="utf-8")
    assert "Mục lục Miền lsu" in content
    assert "[[SKILL-LSU-BEAM-01]]: Căn chỉnh Beam LSU (draft)" in content

    # Update status to confirmed
    update_domain_moc(
        domain="lsu",
        note_id="SKILL-LSU-BEAM-01",
        title="Căn chỉnh Beam LSU",
        kind=DRAFT_KIND_SKILL,
        status="confirmed",
        vault_dir=tmp_path,
    )
    content_updated = moc_file.read_text(encoding="utf-8")
    assert "[[SKILL-LSU-BEAM-01]]: Căn chỉnh Beam LSU (confirmed)" in content_updated


def test_save_note_to_vault_lesson_and_skill(tmp_path: Path) -> None:
    """Saving note places files in designated Second Brain vault directories."""
    lesson_note = SecondBrainNote(
        id="LESSON-T01",
        title="Quy tắc định dạng ngắn",
        kind=DRAFT_KIND_LESSON,
        created="2026-10-20T15:00:00+07:00",
        updated="2026-10-20T15:00:00+07:00",
        mien="lsu",
        applies_when="Khi trả lời LSU",
        content_body="# Quy tắc\nNội dung bài học.\n",
    )
    saved_lesson = save_note_to_vault(lesson_note, root=tmp_path)
    assert saved_lesson.exists()
    assert (tmp_path / "second_brain" / "lessons" / "LESSON-T01.md").exists()
    assert (tmp_path / "second_brain" / "lsu_MOC.md").exists()

    skill_note = SecondBrainNote(
        id="SKILL-LSU-01",
        title="Quy trình đo Beam",
        kind=DRAFT_KIND_SKILL,
        created="2026-10-20T15:00:00+07:00",
        updated="2026-10-20T15:00:00+07:00",
        mien="lsu",
        applies_when="Khi đo Beam",
        content_body="# Quy trình đo\n1. Bước 1\n",
        supporting_files={"references/guide.md": "# Guide"},
    )
    saved_skill = save_note_to_vault(skill_note, root=tmp_path)
    assert saved_skill.exists()
    assert (tmp_path / "skills" / "SKILL-LSU-01" / "SKILL.md").exists()
    assert (tmp_path / "skills" / "SKILL-LSU-01" / "references" / "guide.md").exists()


# ==============================================================================
# 4. READ-BEFORE-WRITE GUARD
# ==============================================================================

def test_read_skill_before_write_guard(tmp_path: Path) -> None:
    """Enforces reading existing skill before write to prevent duplicate hoarding."""
    # Initially skill does not exist
    assert read_skill_before_write("skill_beam_calib", skills_dir=tmp_path) is None

    # Create a skill
    s_dir = tmp_path / "skill_beam_calib"
    s_dir.mkdir(parents=True)
    note = SecondBrainNote(
        id="skill_beam_calib",
        title="Căn chỉnh Beam",
        kind=DRAFT_KIND_SKILL,
        created="2026-10-20T15:00:00+07:00",
        updated="2026-10-20T15:00:00+07:00",
        mien="lsu",
        applies_when="LSU Beam",
        content_body="# Beam Calibration",
    )
    (s_dir / "SKILL.md").write_text(note.to_markdown(), encoding="utf-8")

    # Now read-before-write returns the existing note
    existing = read_skill_before_write("skill_beam_calib", skills_dir=tmp_path)
    assert existing is not None
    assert existing.title == "Căn chỉnh Beam"


# ==============================================================================
# 5. STAGING DRAFTS INTO "SỬA ĐỂ AIOS HỌC" UI
# ==============================================================================

def test_stage_draft_into_pending_form(tmp_path: Path) -> None:
    """Pushed drafts appear in pending_drafts.json for immediate UI consumption."""
    draft_path = tmp_path / "pending_drafts.json"
    note = SecondBrainNote(
        id="LESSON-AUTO-01",
        title="Tóm tắt không dùng bảng",
        kind=DRAFT_KIND_LESSON,
        created="2026-10-20T15:00:00+07:00",
        updated="2026-10-20T15:00:00+07:00",
        mien="dieutraloi",
        applies_when="Khi báo cáo lỗi",
        does_not_apply_when="Khi xuất Excel",
        content_body="# Quy tắc thói quen\nKhông dùng bảng Markdown.",
    )
    stage_draft_into_pending_form(note, message_id="msg_asst_99", workspace_id="ws_test", path=draft_path)

    loaded = load_pending_drafts(path=draft_path)
    forms = loaded.get("correction_forms", {})
    assert "msg_asst_99" in forms
    assert "Không dùng bảng Markdown" in forms["msg_asst_99"]["statement"]
    assert forms["msg_asst_99"]["applies_when"] == "Khi báo cáo lỗi"

    auto_drafts = loaded.get("auto_drafts", {})
    assert "msg_asst_99" in auto_drafts
    assert auto_drafts["msg_asst_99"]["is_auto_draft"] is True
    assert auto_drafts["msg_asst_99"]["note_id"] == "LESSON-AUTO-01"


# ==============================================================================
# 6. DAEMON THREAD EXECUTION & PREEMPTION / CANCELLATION
# ==============================================================================

def test_spawn_post_session_review_background_and_cancellation(tmp_path: Path) -> None:
    """Post-session review spawns in background and respects preemption."""
    draft_path = tmp_path / "pending_drafts.json"
    messages = [
        DummyMessage("user", "Hãy tóm tắt sự cố", "u1"),
        DummyMessage("assistant", "Bảng dữ liệu...", "a1"),
        DummyMessage("user", "Không phải thế, đừng vẽ bảng, hãy tóm tắt ngắn gọn", "u2"),
    ]

    # Run synchronous test mode
    run = spawn_post_session_review(
        conversation_id="conv_test_1",
        messages_snapshot=messages,
        domain="dieutraloi",
        last_assistant_id="a1",
        async_mode=False,
        drafts_path=draft_path,
    )
    assert run is not None
    assert run.done.is_set()

    # Verify draft was generated and staged
    loaded = load_pending_drafts(path=draft_path)
    assert "a1" in loaded.get("correction_forms", {})

    # Test preemption
    cancel_active_review()
    # verify cancel function executes safely without error


# ==============================================================================
# 7. MASTER SWITCH & WIPE HABIT PROFILES
# ==============================================================================

def test_master_switch_controls(tmp_path: Path) -> None:
    """Master switch enables/disables entire self-learning system."""
    settings_path = tmp_path / "settings.json"
    set_master_self_learn_preference(True, path=settings_path)
    assert get_master_self_learn_preference(path=settings_path) is True

    set_master_self_learn_preference(False, path=settings_path)
    assert get_master_self_learn_preference(path=settings_path) is False

    # When Master switch is off, spawn_post_session_review returns None
    from aios_habit.workspace_memory_service import override_memory_settings_path
    with override_memory_settings_path(settings_path):
        res = spawn_post_session_review("conv_1", [], async_mode=False)
        assert res is None


def test_wipe_all_habit_profiles(tmp_path: Path) -> None:
    """Wipe removes habit data cleanly without touching company knowledge or configs."""
    wm_dir = tmp_path / "workspace_memory"
    wm_dir.mkdir(parents=True)
    dec_file = wm_dir / "memory_decisions.jsonl"
    dec_file.write_text('{"statement": "abc"}\n', encoding="utf-8")
    draft_file = wm_dir / "pending_drafts.json"
    draft_file.write_text('{"correction_forms": {}}\n', encoding="utf-8")
    settings_file = wm_dir / "settings.json"
    settings_file.write_text('{"master_self_learn_enabled": true}\n', encoding="utf-8")

    skills_dir = tmp_path / "skills" / "skill_test"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")

    stats = wipe_all_habit_profiles(root=tmp_path)
    assert stats["decisions_removed"] == 1
    assert stats["drafts_removed"] == 1
    assert stats["skills_removed"] == 1
    assert not dec_file.exists()
    assert not draft_file.exists()
    # settings.json must remain
    assert settings_file.exists()


# ==============================================================================
# 8. EXPANDED 'VÌ SAO AIOS NHỚ ĐIỀU NÀY?' PANEL WITH APPLIED SKILLS
# ==============================================================================

def test_why_panel_formats_applied_skill() -> None:
    """Panel clearly displays applied skill information with clean local path."""
    skill_item = WorkspaceMemoryRecallItem(
        memory_key="skill:SKILL-LSU-01:v1",
        source_kind=SOURCE_KIND_SKILL,
        source_id="SKILL-LSU-01",
        title="Quy trình căn chỉnh Beam LSU",
        statement="Bước 1 kiểm tra jig 1002, Bước 2 đo độ lệch, Bước 3 siết ốc.",
        applies_when="Khi căn chỉnh cụm quang học LSU",
        does_not_apply_when="",
        scope="workspace:lsu",
        status="confirmed",
        evidence_refs=("conv:C1", "jig_log_1002"),
        privacy_classification="local_only",
        export_allowed=False,
        updated_at="2026-10-20T10:00:00+00:00",
    )
    lines = format_why_memory_lines((skill_item,))
    blob = " ".join(lines)
    assert "Áp dụng kỹ năng: Quy trình căn chỉnh Beam LSU" in blob
    assert "local_cases/skills/SKILL-LSU-01/SKILL.md" in blob
    assert "D:\\" not in blob  # Invariant: Clean friendly paths, no raw windows drives
    assert "2 mục bằng chứng" in blob


def test_ui_copy_labels() -> None:
    """UI labels and buttons are professional Vietnamese."""
    assert "Master Switch" in master_self_learn_toggle_label()
    assert "tự soạn bản nháp" in master_self_learn_toggle_help()
    assert "Xóa sạch hồ sơ thói quen" in wipe_habit_profiles_button_label()
    assert "Vì sao AIOS nhớ" in why_memory_panel_title()
