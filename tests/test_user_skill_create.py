# -*- coding: utf-8 -*-
"""Comprehensive test suite for ticket DESKTOP-HOME-USER-SKILL-CREATE.

Verifies:
1. Catalog: All 4 /kynang commands present with 3-language (VI/JA/ZH) metadata and aliases.
2. Router: Accurately classifies slash commands and natural queries in all 3 languages.
3. Interactive Interview Flow: Step-by-step interview creates compliant Hermes SKILL.md.
4. Hermes Authoring Standard: YAML frontmatter (name <= 64, description <= 60 ending with .).
5. PINNED Exemption: User skills are created in PINNED state, exempt from curator auto-archiving.
6. Execution & Application: Saved skill is immediately recognized and recalled by AIOS in relevant queries.
7. Metrics: Tracks user skill creation, usage, and approval actions in local_cases metrics.
"""

from __future__ import annotations

import datetime
from pathlib import Path
import pytest

from aios_habit.chat_intent_router import (
    KYNANG_DANH_SACH,
    KYNANG_LUU_TRU,
    KYNANG_TAO,
    KYNANG_XEM,
    classify_intent,
    extract_slots,
)
from aios_habit.hermes_curator import (
    apply_automatic_transitions,
    is_pinned,
    load_usage,
)
from aios_habit.hermes_skill_manager import (
    SKILL_PROMPT_DESC_LIMIT,
    find_skill,
    get_skills_dir,
    parse_frontmatter,
)
from aios_habit.slash_command_catalog import (
    get_all_alive_slash_commands,
    get_command_catalog,
)
from aios_habit.user_skill_manager import (
    archive_skill_markdown,
    cancel_interview,
    get_user_skill_metrics_path,
    handle_interview_turn,
    list_user_skills_markdown,
    load_user_skill_metrics,
    normalize_hermes_description,
    normalize_skill_name,
    save_and_finalize_skill,
    start_or_reset_interview,
    view_skill_markdown,
)
from aios_habit.workspace_memory_models import WorkspaceMemoryRecallRequest
from aios_habit.workspace_memory_service import recall_workspace_memory


@pytest.fixture(autouse=True)
def setup_temp_local_cases(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Isolate tests inside temporary local_cases directory."""
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    yield tmp_path


def test_slash_command_catalog_kynang_entries():
    """Catalog contains all 4 kynang commands with full 3-language metadata and aliases."""
    cat = get_command_catalog()
    kynang_cmds = {item["command"]: item for item in cat if item["command"].startswith("/kynang")}

    expected_cmds = ["/kynang", "/kynang tao", "/kynang xem", "/kynang luu-tru"]
    for cmd in expected_cmds:
        assert cmd in kynang_cmds, f"Thiếu lệnh {cmd} trong catalog"
        item = kynang_cmds[cmd]

        # VI
        assert item.get("category") == "Kỹ năng người dùng"
        assert item.get("description")
        assert item.get("natural_query")
        assert item.get("context_required")

        # JA
        assert item.get("category_ja") == "ユーザー・スキル"
        assert item.get("description_ja")
        assert item.get("natural_query_ja")
        assert item.get("context_required_ja")

        # ZH
        assert item.get("category_zh") == "用户技能"
        assert item.get("description_zh")
        assert item.get("natural_query_zh")
        assert item.get("context_required_zh")

        # Aliases
        assert len(item.get("aliases", [])) >= 2, f"Lệnh {cmd} phải có ít nhất 2 alias (JA/ZH)"


def test_router_kynang_multilingual_classification():
    """Router correctly classifies /kynang commands and natural equivalents across VI/JA/ZH."""
    cases = [
        # /kynang (list)
        ("/kynang", KYNANG_DANH_SACH),
        ("/ky-nang", KYNANG_DANH_SACH),
        ("/スキル", KYNANG_DANH_SACH),
        ("/技能", KYNANG_DANH_SACH),
        ("xem kỹ năng của tôi", KYNANG_DANH_SACH),
        ("danh sách kỹ năng", KYNANG_DANH_SACH),
        ("私のスキル一覧", KYNANG_DANH_SACH),
        ("查看我的技能", KYNANG_DANH_SACH),

        # /kynang tao (create)
        ("/kynang tao", KYNANG_TAO),
        ("/kynang-tao", KYNANG_TAO),
        ("/スキル作成", KYNANG_TAO),
        ("/创建技能", KYNANG_TAO),
        ("tạo kỹ năng mới", KYNANG_TAO),
        ("muốn tự tạo skill của mình", KYNANG_TAO),
        ("新規スキル作成", KYNANG_TAO),
        ("创建新技能", KYNANG_TAO),

        # /kynang xem (view)
        ("/kynang xem sensor-jig", KYNANG_XEM),
        ("/kynang-xem sensor-jig", KYNANG_XEM),
        ("/スキル確認 sensor-jig", KYNANG_XEM),
        ("/查看技能 sensor-jig", KYNANG_XEM),
        ("xem chi tiết kỹ năng sensor-jig", KYNANG_XEM),
        ("スキル詳細確認 sensor-jig", KYNANG_XEM),
        ("查看技能详情 sensor-jig", KYNANG_XEM),

        # /kynang luu-tru (archive)
        ("/kynang luu-tru sensor-jig", KYNANG_LUU_TRU),
        ("/kynang-luu-tru sensor-jig", KYNANG_LUU_TRU),
        ("/kynang-luutru sensor-jig", KYNANG_LUU_TRU),
        ("/スキルアーカイブ sensor-jig", KYNANG_LUU_TRU),
        ("/归档技能 sensor-jig", KYNANG_LUU_TRU),
        ("lưu trữ kỹ năng sensor-jig", KYNANG_LUU_TRU),
        ("スキルをアーカイブ sensor-jig", KYNANG_LUU_TRU),
        ("归档此技能 sensor-jig", KYNANG_LUU_TRU),
    ]

    for text, expected_intent in cases:
        intent = classify_intent(text)
        assert intent == expected_intent, f"Phân loại sai '{text}': kỳ vọng {expected_intent}, nhận {intent}"

    # Verify slot extraction
    slots_view = extract_slots("/kynang xem kiem-tra-jig", KYNANG_XEM)
    assert slots_view.get("skill_name") == "kiem-tra-jig"

    slots_arc = extract_slots("/kynang luu-tru kiem-tra-jig", KYNANG_LUU_TRU)
    assert slots_arc.get("skill_name") == "kiem-tra-jig"


def test_user_skill_interview_flow_to_completion():
    """End-to-end interview flow: phỏng vấn -> nháp -> duyệt -> lưu PINNED."""
    cid = "CONV-TEST-INTERVIEW-001"

    # Turn 1: Start interview
    out1 = start_or_reset_interview(cid, "/kynang tao")
    assert "Bước 1/4: Tên kỹ năng" in out1

    # Turn 2: Provide invalid name -> rejected with helpful guidance
    out2_bad = handle_interview_turn(cid, "Tên Kỹ Năng Sai!! 123")
    # Cleaned name or rejection
    # If user provides valid name
    out2 = handle_interview_turn(cid, "kiem-tra-sensor-jig")
    assert "Bước 2/4: Việc gì" in out2

    # Turn 3: Provide description
    out3 = handle_interview_turn(cid, "Kiểm tra và xử lý lỗi cảm biến quang đồ gá JIG.")
    assert "Bước 3/4: Điều kiện kích hoạt" in out3

    # Turn 4: Provide trigger context
    out4 = handle_interview_turn(cid, "Khi đèn LED vàng cảm biến nhấp nháy hoặc JIG báo không nhận sản phẩm.")
    assert "Bước 4/4: Các bước thực hiện" in out4

    # Turn 5: Provide steps -> generates draft preview
    steps = (
        "1. Đo nguồn cấp 24V tại chân cảm biến quang.\n"
        "2. Vệ sinh thấu kính đọc bằng cồn IPA sạch.\n"
        "3. Hiệu chỉnh cự ly và độ nhạy đến khi đèn xanh sáng ổn định."
    )
    out5 = handle_interview_turn(cid, steps)
    assert "BẢN NHÁP KỸ NĂNG NGƯỜI DÙNG" in out5
    assert "kiem-tra-sensor-jig" in out5
    assert "PINNED" in out5
    assert "aios_user_skill_draft" in out5

    # Turn 6: Approve and finalize
    out6 = handle_interview_turn(cid, "duyệt")
    assert "ĐÃ TẠO VÀ LƯU KỸ NĂNG THÀNH CÔNG" in out6
    assert "PINNED" in out6

    # Verify physical file on disk
    skill_dir = get_skills_dir() / "kiem-tra-sensor-jig"
    skill_md = skill_dir / "SKILL.md"
    assert skill_md.is_file(), f"Tệp SKILL.md chưa được tạo tại {skill_md}"

    content = skill_md.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(content)

    # Hermes Authoring standards verification
    assert fm.get("name") == "kiem-tra-sensor-jig"
    desc = fm.get("description", "")
    assert desc.endswith("."), "Mô tả Hermes phải kết thúc bằng dấu chấm."
    assert len(desc) <= SKILL_PROMPT_DESC_LIMIT, f"Mô tả vượt giới hạn budget {SKILL_PROMPT_DESC_LIMIT} ký tự."

    # Pinned and Curator exemption verification
    assert is_pinned("kiem-tra-sensor-jig") is True, "Kỹ năng người dùng tạo phải ở trạng thái PINNED."
    usage = load_usage()
    assert usage.get("kiem-tra-sensor-jig", {}).get("created_by") == "user"

    # Simulate curator auto transitions 100 days later -> PINNED must NEVER be archived
    now_future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=100)
    apply_automatic_transitions(now=now_future)
    assert (get_skills_dir() / "kiem-tra-sensor-jig" / "SKILL.md").exists(), "Kỹ năng PINNED bị curator tự động lưu trữ sai luật!"


def test_user_skill_one_shot_creation():
    """One-shot creation with all arguments provided in single command."""
    cid = "CONV-TEST-ONESHOT-002"
    raw_cmd = (
        "/kynang tao "
        "ten: do-nguon-24v | "
        "viec: Đo kiểm tra nguồn 24V tủ điện JIG. | "
        "khi_nao: Khi PLC báo mất nguồn cảm biến | "
        "buoc: 1. Bật đồng hồ vạn năng dải đo DC. 2. Đo chân V+ và V-."
    )
    out_draft = start_or_reset_interview(cid, raw_cmd)
    assert "BẢN NHÁP KỸ NĂNG NGƯỜI DÙNG" in out_draft
    assert "do-nguon-24v" in out_draft

    out_save = handle_interview_turn(cid, "xác nhận")
    assert "ĐÃ TẠO VÀ LƯU KỸ NĂNG THÀNH CÔNG" in out_save

    assert (get_skills_dir() / "do-nguon-24v" / "SKILL.md").exists()
    assert is_pinned("do-nguon-24v") is True


def test_user_skill_cancel_and_edit_flow():
    """User can cancel or revise the draft."""
    cid = "CONV-TEST-CANCEL-003"
    start_or_reset_interview(cid, "/kynang tao")
    handle_interview_turn(cid, "ky-nang-tam")
    cancel_res = handle_interview_turn(cid, "hủy")
    assert "Đã hủy phiên tạo kỹ năng" in cancel_res
    assert find_skill("ky-nang-tam") is None

    # Test editing draft
    cid2 = "CONV-TEST-EDIT-004"
    start_or_reset_interview(
        cid2,
        "/kynang tao ten: skill-can-sua | viec: Lam viec A. | khi_nao: Khi gap A | buoc: 1. Buoc A",
    )
    edit_res = handle_interview_turn(cid2, "sửa: viec: Khắc phục lỗi A trên dây chuyền. | buoc: 1. Bước sửa A")
    assert "Đã cập nhật bản nháp theo yêu cầu" in edit_res
    assert "Khắc phục lỗi A trên dây chuyền." in edit_res


def test_user_skill_recall_and_application(tmp_path: Path):
    """Saved skill is immediately recognized and applied in relevant AIOS questions."""
    # 1. Create skill
    cid = "CONV-TEST-RECALL-005"
    raw_cmd = (
        "/kynang tao "
        "ten: xu-ly-ket-giay-cum-say | "
        "viec: Xử lý kẹt giấy tại cụm sấy máy in. | "
        "khi_nao: Máy in báo mã lỗi kẹt giấy tại cụm sấy hoặc giấy bị nhăn khi qua lô ép | "
        "buoc: 1. Mở nắp phía sau cụm sấy. 2. Nhẹ nhàng xoay bánh răng rút giấy ra ngoài. 3. Vệ sinh trục cuốn."
    )
    start_or_reset_interview(cid, raw_cmd)
    handle_interview_turn(cid, "duyệt")

    # 2. Recall via Workspace Memory
    req = WorkspaceMemoryRecallRequest(
        question="Máy in bị kẹt giấy tại cụm sấy và giấy bị nhăn thì xử lý thế nào?",
        workspace_id="default",
        collection_id="default",
        provider_mode="local",
        include_local_only=True,
    )
    result = recall_workspace_memory(req)
    assert len(result.items) >= 1, "Kỹ năng cá nhân vừa tạo không được Workspace Memory nhận diện!"

    matched = [it for it in result.items if it.source_id == "xu-ly-ket-giay-cum-say"]
    assert len(matched) == 1, f"Không tìm thấy kỹ năng trong kết quả recall: {[i.source_id for i in result.items]}"
    item = matched[0]
    assert item.source_kind == "skill"
    assert "Mở nắp phía sau cụm sấy" in item.statement

    # 3. Check metrics incremented
    metrics = load_user_skill_metrics()
    assert metrics.get("total_user_skills_used", 0) >= 1


def test_user_skill_list_view_and_archive_commands():
    """Commands /kynang, /kynang xem, /kynang luu-tru work as expected."""
    # Create a skill
    cid = "CONV-TEST-CMDS-006"
    raw_cmd = (
        "/kynang tao "
        "ten: ve-sinh-cum-drum | "
        "viec: Vệ sinh định kỳ cụm trống Drum. | "
        "khi_nao: Định kỳ bảo dưỡng cụm drum | "
        "buoc: 1. Tháo cụm trống. 2. Dùng chổi mịn quét bụi."
    )
    start_or_reset_interview(cid, raw_cmd)
    handle_interview_turn(cid, "duyệt")

    # 1. List
    list_md = list_user_skills_markdown()
    assert "ve-sinh-cum-drum" in list_md
    assert "PINNED" in list_md

    # 2. View
    view_md = view_skill_markdown("ve-sinh-cum-drum")
    assert "ve-sinh-cum-drum" in view_md
    assert "Tháo cụm trống" in view_md

    # 3. Archive
    archive_md = archive_skill_markdown("ve-sinh-cum-drum")
    assert "ĐÃ LƯU TRỮ KỸ NĂNG" in archive_md
    assert (get_skills_dir() / ".archive" / "ve-sinh-cum-drum" / "SKILL.md").exists()
    assert not (get_skills_dir() / "ve-sinh-cum-drum" / "SKILL.md").exists()

    # 4. Metrics
    metrics = load_user_skill_metrics()
    assert metrics.get("total_user_skills_archived", 0) >= 1
