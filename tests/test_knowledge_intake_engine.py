"""Bộ kiểm thử toàn diện cho Bộ máy thu tri thức chuyên gia (Ticket DESKTOP-KNOWLEDGE-INTAKE-ENGINE-HOME).

Kiểm chứng đầy đủ các yêu cầu cốt lõi:
1. Cơ chế Hồ sơ đích theo kho:
   - Hồ sơ mẫu Kho LSU: 5 trường bắt buộc Bước 0 (ma_loi, hien_tuong, nguyen_nhan, doi_sach, cong_doan) + 4 trường phụ (model, line, dau_hieu_som, ghi_chu).
   - Thêm kho mới chỉ cần khai báo một hồ sơ, không sửa lõi bộ máy.
   - Nhãn nguồn thống nhất: loai + ten nguoi + ngay + kho dich.
2. Hai chế độ vận hành:
   - Chế độ Phỏng vấn: AI dẫn hỏi 4M + Why-Why, tự động đào sâu khi câu trả lời chung chung.
   - Chế độ Dạy: chuyên gia giảng, AI đóng vai người học làm rõ phạm vi, ngoại lệ, ví dụ thật, chỗ hay hiểu sai.
3. Nguyên tắc đạo đức & chất lượng:
   - AI KHÔNG được bịa: trường không nói tới để trống hoặc ghi "chưa xác nhận".
   - Mỗi mục nháp truy vết được về đúng câu trả lời gốc (source_quote nguyên văn + source_turn_ids).
4. Vòng duyệt tại chỗ:
   - Chọn Đúng -> review_status="dung", ingest_status="cho_nap".
   - Chọn Sửa -> review_status="da_sua", ingest_status="cho_nap", cập nhật nội dung sửa.
   - Chọn Loại -> review_status="loai", ingest_status="khong_nap" (tuyệt đối không cho_nap).
5. Staging chung:
   - Store local riêng, phân theo kho đích, không trộn dữ liệu giữa các kho.
6. Vòng lặp cải thiện liên tục 3 điểm (Luật User 2026-10-03):
   (1) Điểm hứng feedback (duyệt tại chỗ trong chat).
   (2) Metric đo được (tỉ lệ duyệt, độ đủ khuôn, số phiên theo kho/chế độ).
   (3) Vòng xem lại để cải thiện (bề mặt xem lại danh sách CHO NAP + metric).
7. Chat action & UI widgets:
   - Nhận diện lệnh chat, nhúng marker tương tác và render widget với FakeSt.

Tương thích Python 3.11: không dùng PEP 701 multiline f-strings.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from aios_habit import chat_action
from aios_habit.chat_action import ChatActionRequest
from aios_habit.chat_action_knowledge_intake import (
    ACTION_NAME,
    _handler,
    _parse_expert_name,
    _parse_mode,
    _parse_store_id,
    _parse_topic,
)
from aios_habit.chat_intake_ui import (
    clear_live_sessions,
    extract_intake_review_marker,
    extract_intake_session_marker,
    intake_review_marker,
    intake_session_marker,
    render_intake_review_widget,
    render_intake_session_widget,
    strip_intake_markers,
)
from aios_habit.intake_metrics import (
    compute_intake_metrics,
    format_review_surface_markdown,
)
from aios_habit.intake_staging import (
    INGEST_CHO_NAP,
    INGEST_KHONG_NAP,
    STATUS_CHO_DUYET,
    STATUS_DA_SUA,
    STATUS_DUNG,
    STATUS_LOAI,
    IntakeDraftItemRecord,
    IntakeSessionRecord,
    IntakeStagingStore,
    IntakeTurnRecord,
)
from aios_habit.intake_target_profiles import (
    KHO_LSU_PROFILE,
    STORE_ID_LSU,
    TargetFieldSpec,
    TargetProfile,
    format_source_tag,
    get_target_profile,
    list_target_profiles,
    parse_source_tag,
    register_target_profile,
    reset_target_profiles,
)
from aios_habit.knowledge_intake_engine import (
    CLARIFY_HIEU_SAI,
    CLARIFY_NGOAI_LE,
    CLARIFY_PHAM_VI,
    CLARIFY_VI_DU_THAT,
    MODE_DAY,
    MODE_PHONG_VAN,
    PROBE_4M_WHY,
    PROBE_DAU_HIEU_SOM,
    PROBE_DIEU_KIEN_PHAT_SINH,
    PROBE_MODEL_LINE,
    PROBE_PHAN_BIET_LOI,
    PROBE_XU_LY_HIEU_QUA,
    PROBE_XU_LY_KHONG_HIEU_QUA,
    KnowledgeIntakeEngine,
    detect_missing_aspects_interview,
    synthesize_draft_items,
)


@pytest.fixture(autouse=True)
def _isolate_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Cách ly môi trường DB staging và registry cho từng test."""
    staging_file = tmp_path / "test_knowledge_intake_staging.sqlite"
    monkeypatch.setenv("AIOS_INTAKE_STAGING_DB", str(staging_file))
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))
    reset_target_profiles()
    clear_live_sessions()
    chat_action.reset_actions()
    yield
    reset_target_profiles()
    clear_live_sessions()
    chat_action.reset_actions()


# ---------------------------------------------------------------------------
# Fake Streamlit cho UI testing
# ---------------------------------------------------------------------------


class _FakeColumn:
    def __init__(self, fake: "FakeSt") -> None:
        self._fake = fake

    def __enter__(self) -> "FakeSt":
        return self._fake

    def __exit__(self, *args: Any) -> bool:
        return False


class FakeSt:
    """Giả lập streamlit để kiểm thử tương tác widget hoàn toàn tự động."""

    def __init__(self, session_state: Optional[Dict[str, Any]] = None) -> None:
        self.session_state = {} if session_state is None else session_state
        self.markdown_calls: List[str] = []
        self.info_calls: List[str] = []
        self.success_calls: List[str] = []
        self.warning_calls: List[str] = []
        self.button_clicks: Dict[str, bool] = {}
        self.text_area_inputs: Dict[str, str] = {}
        self.text_inputs: Dict[str, str] = {}
        self.rerun_called = False

    def markdown(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.markdown_calls.append(str(text))

    def caption(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.markdown_calls.append("CAPTION: " + str(text))

    def info(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.info_calls.append(str(text))

    def success(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.success_calls.append(str(text))

    def warning(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.warning_calls.append(str(text))

    def columns(self, n: int) -> List[_FakeColumn]:
        return [_FakeColumn(self) for _ in range(n)]

    def button(self, label: str, key: Optional[str] = None, *args: Any, **kwargs: Any) -> bool:
        if key and key in self.button_clicks:
            return self.button_clicks[key]
        return False

    def text_area(self, label: str, value: str = "", key: Optional[str] = None, *args: Any, **kwargs: Any) -> str:
        if key and key in self.text_area_inputs:
            return self.text_area_inputs[key]
        return value

    def text_input(self, label: str, value: str = "", key: Optional[str] = None, *args: Any, **kwargs: Any) -> str:
        if key and key in self.text_inputs:
            return self.text_inputs[key]
        return value

    def rerun(self) -> None:
        self.rerun_called = True


# ===========================================================================
# 1. Kiểm thử Cơ chế Hồ sơ đích theo kho (Target Profiles)
# ===========================================================================


def test_kho_lsu_profile_conforms_to_spec():
    """Hồ sơ mẫu Kho LSU phải có đủ 5 trường bắt buộc Bước 0 và các trường phụ."""
    profile = get_target_profile(STORE_ID_LSU)
    assert profile is not None
    assert profile.store_id == "kho_lsu"
    assert profile.display_name == "Kho LSU"
    assert profile.ingest_route == "DESKTOP-LSU-EXPERT-INTERVIEW-INGEST-HOME"
    assert profile.source_prefix == "kho_lsu"

    req_fields = profile.required_fields
    assert set(req_fields) == {"ma_loi", "hien_tuong", "nguyen_nhan", "doi_sach", "cong_doan"}
    assert len(req_fields) == 5

    opt_fields = profile.optional_fields
    assert "model" in opt_fields
    assert "line" in opt_fields
    assert "dau_hieu_som" in opt_fields
    assert "ghi_chu" in opt_fields


def test_add_new_target_profile_declaratively():
    """Thêm kho mới chỉ cần khai báo một hồ sơ mới mà không cần sửa bộ máy."""
    new_profile = TargetProfile(
        store_id="kho_mom",
        display_name="Kho MOM/Opcenter",
        description="Kho dữ liệu sản xuất MOM",
        ingest_route="DESKTOP-MOM-INGEST",
        source_prefix="kho_mom",
        fields=(
            TargetFieldSpec("work_order", "Mã lệnh sản xuất", is_mandatory=True),
            TargetFieldSpec("station_id", "Mã trạm", is_mandatory=True),
            TargetFieldSpec("operator_note", "Ghi chú vận hành", is_mandatory=False),
        ),
    )
    register_target_profile(new_profile)

    retrieved = get_target_profile("kho_mom")
    assert retrieved is not None
    assert retrieved.display_name == "Kho MOM/Opcenter"
    assert retrieved.required_fields == ("work_order", "station_id")
    assert retrieved.optional_fields == ("operator_note",)


def test_unified_source_tag_formatting_and_parsing():
    """Nhãn nguồn phải thống nhất: loai + ten nguoi + ngay + kho dich."""
    tag = format_source_tag(
        mode="phong_van",
        expert_name="Nguyễn Văn A",
        date_str="2026-10-18",
        store_id="kho_lsu",
    )
    assert tag == "phong-van | Nguyễn Văn A | 2026-10-18 | kho_lsu"

    parsed = parse_source_tag(tag)
    assert parsed["mode"] == "phong-van"
    assert parsed["expert_name"] == "Nguyễn Văn A"
    assert parsed["date"] == "2026-10-18"
    assert parsed["store_id"] == "kho_lsu"

    tag_day = format_source_tag(
        mode="day",
        expert_name="Trần Thị B",
        date_str="2026-10-19",
        store_id="kho_mom",
    )
    assert tag_day == "day | Trần Thị B | 2026-10-19 | kho_mom"


# ===========================================================================
# 2. Kiểm thử Staging chung & Phân vùng theo kho đích
# ===========================================================================


def test_staging_store_partitioning_by_store(tmp_path: Path):
    """Dữ liệu giữa các kho đích phải phân vùng cách ly 100%, không trộn lẫn."""
    staging = IntakeStagingStore(tmp_path / "staging_iso.sqlite")

    # Lưu 1 mục cho kho_lsu
    draft_lsu = IntakeDraftItemRecord(
        draft_id="draft-lsu-01",
        session_id="sess-01",
        store_id="kho_lsu",
        mode="phong_van",
        expert_name="Chuyên gia A",
        topic="Lỗi C7620",
        source_tag="phong-van | Chuyên gia A | 2026-10-18 | kho_lsu",
        fields={"ma_loi": "C7620", "hien_tuong": "Kẹt giấy cụm sấy"},
        source_quote="Kẹt giấy khi nhiệt độ sấy vọt quá cao",
    )
    staging.save_draft_item(draft_lsu)

    # Lưu 1 mục cho kho khác (kho_dieu_tra)
    draft_dt = IntakeDraftItemRecord(
        draft_id="draft-dt-01",
        session_id="sess-02",
        store_id="kho_dieu_tra",
        mode="day",
        expert_name="Chuyên gia B",
        topic="Điều tra rung động",
        source_tag="day | Chuyên gia B | 2026-10-18 | kho_dieu_tra",
        fields={"case_id": "DT-101", "root_cause": "Lỏng ốc bạc đạn"},
        source_quote="Rung động ở tần số 120Hz do ốc cố định bị lỏng",
    )
    staging.save_draft_item(draft_dt)

    # Truy vấn lọc theo kho_lsu
    lsu_items = staging.list_draft_items_by_store("kho_lsu")
    assert len(lsu_items) == 1
    assert lsu_items[0].draft_id == "draft-lsu-01"
    assert lsu_items[0].store_id == "kho_lsu"

    # Truy vấn lọc theo kho_dieu_tra
    dt_items = staging.list_draft_items_by_store("kho_dieu_tra")
    assert len(dt_items) == 1
    assert dt_items[0].draft_id == "draft-dt-01"
    assert dt_items[0].store_id == "kho_dieu_tra"


def test_in_chat_review_workflow_status_transitions(tmp_path: Path):
    """Kiểm tra vòng duyệt tại chỗ: Đúng -> cho_nap; Sửa -> cho_nap; Loại -> khong_nap."""
    staging = IntakeStagingStore(tmp_path / "staging_review.sqlite")

    draft1 = IntakeDraftItemRecord(
        draft_id="draft-001",
        session_id="sess-01",
        store_id="kho_lsu",
        mode="phong_van",
        expert_name="Nguyễn Văn A",
        topic="C7620",
        source_tag="phong-van | Nguyễn Văn A | 2026-10-18 | kho_lsu",
        fields={"ma_loi": "C7620", "hien_tuong": "Mực sấy không chín"},
    )
    draft2 = IntakeDraftItemRecord(
        draft_id="draft-002",
        session_id="sess-01",
        store_id="kho_lsu",
        mode="phong_van",
        expert_name="Nguyễn Văn A",
        topic="C3501",
        source_tag="phong-van | Nguyễn Văn A | 2026-10-18 | kho_lsu",
        fields={"ma_loi": "C3501", "hien_tuong": "Lệch màu bản in"},
    )
    draft3 = IntakeDraftItemRecord(
        draft_id="draft-003",
        session_id="sess-01",
        store_id="kho_lsu",
        mode="phong_van",
        expert_name="Nguyễn Văn A",
        topic="F000",
        source_tag="phong-van | Nguyễn Văn A | 2026-10-18 | kho_lsu",
        fields={"ma_loi": "F000", "hien_tuong": "Lỗi giao tiếp tạm thời"},
    )
    staging.save_draft_items([draft1, draft2, draft3])

    # 1. Duyệt Đúng mục 1
    updated1 = staging.update_review_status("draft-001", "dung", reviewer="Kỹ sư trưởng")
    assert updated1.review_status == STATUS_DUNG
    assert updated1.ingest_status == INGEST_CHO_NAP
    assert updated1.reviewed_by == "Kỹ sư trưởng"

    # 2. Duyệt Sửa mục 2 (chỉnh sửa nội dung)
    updated2 = staging.update_review_status(
        "draft-002",
        "sua",
        edited_fields={"hien_tuong": "Lệch màu bản in ở mép phải 2mm", "cong_doan": "Lắp ráp cụm quang"},
        reviewer="Kỹ sư trưởng",
    )
    assert updated2.review_status == STATUS_DA_SUA
    assert updated2.ingest_status == INGEST_CHO_NAP
    assert updated2.fields["hien_tuong"] == "Lệch màu bản in ở mép phải 2mm"
    assert updated2.fields["cong_doan"] == "Lắp ráp cụm quang"
    assert "hien_tuong" in updated2.edited_fields

    # 3. Duyệt Loại mục 3
    updated3 = staging.update_review_status("draft-003", "loai", reviewer="Kỹ sư trưởng")
    assert updated3.review_status == STATUS_LOAI
    assert updated3.ingest_status == INGEST_KHONG_NAP  # Tuyệt đối không nạp

    # Kiểm tra truy vấn các mục CHO_NAP
    cho_nap_items = staging.list_draft_items_by_store("kho_lsu", ingest_status=INGEST_CHO_NAP)
    assert len(cho_nap_items) == 2
    ids_cho_nap = {it.draft_id for it in cho_nap_items}
    assert ids_cho_nap == {"draft-001", "draft-002"}
    assert "draft-003" not in ids_cho_nap


# ===========================================================================
# 3. Kiểm thử Hai chế độ Phỏng vấn & Dạy + Đào sâu + Không bịa
# ===========================================================================


def test_interview_mode_flow_and_deep_probing(tmp_path: Path):
    """Chế độ phỏng vấn: dẫn hỏi 4M + Why-Why và kích hoạt câu hỏi đào sâu khi câu trả lời ngắn/chung chung."""
    staging = IntakeStagingStore(tmp_path / "staging_interview.sqlite")
    engine = KnowledgeIntakeEngine(staging_store=staging)

    session = engine.start_session(
        store_id=STORE_ID_LSU,
        mode=MODE_PHONG_VAN,
        topic="Lỗi nhiệt sấy C7620",
        expert_name="Kỹ sư Nguyễn",
    )

    assert session.mode == MODE_PHONG_VAN
    assert session.store_id == "kho_lsu"
    assert len(session.turns) == 1
    assert "hien_tuong_ma_loi" in session.turns[0].probe_type

    # Câu trả lời 1: ngắn, chưa có dấu hiệu sớm và chưa có phân biệt lỗi
    is_done, msg, next_turn = engine.submit_answer(
        session, "Mã lỗi C7620, hiện tượng máy báo quá nhiệt tại lô sấy số 2."
    )
    assert not is_done
    assert next_turn is not None
    # Hệ thống phải chèn câu hỏi đào sâu (ví dụ dấu hiệu nhận biết sớm hoặc phân biệt lỗi)
    assert any(
        probe[0] in (PROBE_DAU_HIEU_SOM, PROBE_PHAN_BIET_LOI, PROBE_XU_LY_KHONG_HIEU_QUA)
        for probe in session.pending_probes
    )

    # Trả lời câu đào sâu
    is_done2, msg2, next_turn2 = engine.submit_answer(
        session, "Dấu hiệu nhận biết sớm là bề mặt giấy có vết gợn sóng và tiếng rơ-le nhảy tanh tách."
    )
    assert not is_done2
    assert next_turn2 is not None

    # Trả lời các câu tiếp theo đến khi hoàn tất
    while session.pending_probes:
        engine.submit_answer(
            session,
            "Nguyên nhân 4M do cảm biến nhiệt bị bám bụi muội than dẫn đến đo sai. "
            "Đối sách hiệu quả là vệ sinh thermistor và thay tấm gạt định kỳ ở công đoạn Lắp ráp Line 1."
        )

    # Kết thúc và tổng hợp nháp
    drafts = engine.end_and_synthesize(session)
    assert len(drafts) >= 1
    draft = drafts[0]

    # Kiểm tra trích dẫn nguyên văn
    assert draft.source_quote != ""
    assert "C7620" in draft.source_quote
    assert len(draft.source_turn_ids) >= 2
    assert draft.source_tag.startswith("phong-van | Kỹ sư Nguyễn")

    # Kiểm tra điền đúng các trường đã nói
    assert draft.fields["ma_loi"] == "C7620"
    assert draft.fields["line"] == "Line 1"


def test_teaching_mode_flow_and_learner_role(tmp_path: Path):
    """Chế độ dạy: chuyên gia giảng bài, AI đóng vai người học và làm rõ phạm vi, ngoại lệ, ví dụ."""
    staging = IntakeStagingStore(tmp_path / "staging_teaching.sqlite")
    engine = KnowledgeIntakeEngine(staging_store=staging)

    session = engine.start_session(
        store_id=STORE_ID_LSU,
        mode=MODE_DAY,
        topic="Kỹ thuật cân chỉnh gương phản xạ LSU",
        expert_name="Thầy Bảy",
    )

    assert session.mode == MODE_DAY
    first_q = session.turns[0].question_text
    assert "học hỏi" in first_q or "giảng giải" in first_q

    # Chuyên gia giảng bài chi tiết (>100 ký tự)
    lecture_1 = (
        "Khi lắp đặt cụm laser LSU, gương đa giác quay với vận tốc 30.000 vòng/phút. "
        "Nếu góc lệch vượt quá 0.05 độ thì chùm tia quét sẽ bị méo hình thang trên trống drum. "
        "Cần dùng dưỡng đo chuyên dụng JIG-08 để siết ốc đối xứng theo 3 điểm cân bằng."
    )
    is_done, msg, next_turn = engine.submit_answer(session, lecture_1)
    assert not is_done
    assert next_turn is not None
    # Hệ thống chèn câu hỏi làm rõ trường hợp ngoại lệ hoặc phạm vi
    clarify_types = [p[0] for p in session.pending_probes]
    assert CLARIFY_NGOAI_LE in clarify_types or CLARIFY_PHAM_VI in clarify_types

    # Trả lời câu làm rõ
    engine.submit_answer(
        session,
        "Trường hợp ngoại lệ là vào mùa đông nhiệt độ phòng dưới 18 độ C thì phải ủ nhiệt mô tơ 10 phút trước khi đo."
    )

    # Kết thúc phiên
    drafts = engine.end_and_synthesize(session)
    assert len(drafts) >= 1
    draft = drafts[0]
    assert draft.mode == "day"
    assert "day | Thầy Bảy" in draft.source_tag
    assert "gương đa giác" in draft.source_quote


def test_anti_hallucination_leaves_missing_fields_unconfirmed():
    """AI KHÔNG được bịa: trường nào người nói không đề cập phải là 'chưa xác nhận'."""
    session = KnowledgeIntakeEngine().start_session(
        store_id=STORE_ID_LSU,
        mode=MODE_PHONG_VAN,
        topic="Cân chỉnh nhiệt",
        expert_name="Chuyên gia",
    )
    # Câu trả lời chỉ nói hiện tượng, không nói mã lỗi, không nói model, không nói line
    session.turns[0].answer_text = "Hiện tượng giấy bị cong vênh mép khi ra khỏi khay sấy."
    session.turns[0].speaker = "expert"

    drafts = synthesize_draft_items(session)
    assert len(drafts) == 1
    d = drafts[0]

    # Kiểm tra tuyệt đối không tự bịa mã lỗi hoặc model/line
    assert d.fields["ma_loi"] == "chưa xác nhận"
    assert d.fields["model"] == "chưa xác nhận"
    assert d.fields["line"] == "chưa xác nhận"
    assert d.fields["cong_doan"] == "chưa xác nhận"
    assert "cong vênh" in d.fields["hien_tuong"]


# ===========================================================================
# 4. Kiểm thử Vòng lặp cải thiện liên tục 3 điểm (Luật User 2026-10-03)
# ===========================================================================


def test_continuous_improvement_loop_3_points(tmp_path: Path):
    """Kiểm tra đầy đủ 3 điểm: (1) Hứng feedback -> (2) Metric đo được -> (3) Bề mặt xem lại."""
    staging = IntakeStagingStore(tmp_path / "staging_loop.sqlite")

    # Tạo phiên và các mục nháp
    session = IntakeSessionRecord(
        session_id="sess-loop-01",
        store_id=STORE_ID_LSU,
        mode=MODE_PHONG_VAN,
        expert_name="Nguyễn Văn A",
        topic="Lỗi C7620",
        status="ended",
    )
    staging.save_session(session)

    item1 = IntakeDraftItemRecord(
        draft_id="item-01",
        session_id="sess-loop-01",
        store_id=STORE_ID_LSU,
        mode=MODE_PHONG_VAN,
        expert_name="Nguyễn Văn A",
        topic="Lỗi C7620",
        source_tag="phong-van | Nguyễn Văn A | 2026-10-18 | kho_lsu",
        fields={
            "ma_loi": "C7620",
            "hien_tuong": "Quá nhiệt",
            "nguyen_nhan": "Hỏng cảm biến",
            "doi_sach": "Thay cảm biến",
            "cong_doan": "Lắp ráp cụm sấy",
        },
        source_quote="Quá nhiệt do hỏng cảm biến",
    )
    item2 = IntakeDraftItemRecord(
        draft_id="item-02",
        session_id="sess-loop-01",
        store_id=STORE_ID_LSU,
        mode=MODE_PHONG_VAN,
        expert_name="Nguyễn Văn A",
        topic="Lỗi C7620",
        source_tag="phong-van | Nguyễn Văn A | 2026-10-18 | kho_lsu",
        fields={
            "ma_loi": "C7620",
            "hien_tuong": "Lệch nhiệt",
            "nguyen_nhan": "chưa xác nhận",
            "doi_sach": "chưa xác nhận",
            "cong_doan": "chưa xác nhận",
        },
        source_quote="Lệch nhiệt",
    )
    staging.save_draft_items([item1, item2])

    # --- ĐIỂM (1): Hứng feedback duyệt tại chỗ ---
    # Duyệt Đúng mục 1 -> cho_nap
    staging.update_review_status("item-01", "dung")
    # Duyệt Loại mục 2 -> loai
    staging.update_review_status("item-02", "loai")

    # --- ĐIỂM (2): Metric đo được ---
    metrics = compute_intake_metrics(STORE_ID_LSU, staging_store=staging)
    assert metrics.total_draft_items == 2
    assert metrics.approved_items == 1
    assert metrics.approval_rate == 0.5  # 1/2 = 50%
    assert metrics.rejected_items == 1
    assert metrics.pending_ingest_count == 1

    # Độ đủ khuôn của mục được duyệt (item1 có đủ 5/5 trường bắt buộc -> 100%)
    assert STORE_ID_LSU in metrics.schema_completeness_by_store
    assert metrics.schema_completeness_by_store[STORE_ID_LSU] == 1.0

    # Số phiên phân theo chế độ
    assert STORE_ID_LSU in metrics.sessions_by_store_and_mode
    assert metrics.sessions_by_store_and_mode[STORE_ID_LSU].get(MODE_PHONG_VAN) == 1

    # --- ĐIỂM (3): Bề mặt xem lại để cải thiện ---
    surface_md = format_review_surface_markdown(STORE_ID_LSU, staging_store=staging)
    assert "Bề mặt xem lại & cải thiện thu tri thức" in surface_md
    assert "50.0%" in surface_md  # Tỉ lệ duyệt
    assert "item-01" in surface_md  # Mục chờ nạp hiển thị trong bảng
    assert "item-02" not in surface_md  # Mục bị loại KHÔNG nằm trong bảng chờ nạp
    assert "Quy tắc 3 điểm" in surface_md


# ===========================================================================
# 5. Kiểm thử Chat Action & Streamlit UI Widgets với FakeSt
# ===========================================================================


def test_chat_action_handler_open_session_and_review():
    """Chat action nhận diện lệnh mở phiên và lệnh xem bề mặt xem lại/metric."""
    # Lệnh mở phiên phỏng vấn
    req_open = ChatActionRequest(
        question="mở phiên thu tri thức kho lsu về lỗi C7620 chuyên gia Lê Văn C"
    )
    outcome_open = _handler(req_open)
    assert outcome_open is not None
    assert outcome_open.action == ACTION_NAME
    assert len(outcome_open.blocks) >= 1
    text_open = outcome_open.blocks[0].text
    assert "Kho LSU" in text_open
    assert "C7620" in text_open
    assert "Lê Văn C" in text_open
    assert "aios_intake_session" in text_open

    # Lệnh mở phiên dạy kiến thức
    req_day = ChatActionRequest(
        question="bắt đầu dạy kiến thức kho lsu về căn chỉnh laser chuyên gia Trần Kỹ Sư"
    )
    outcome_day = _handler(req_day)
    assert outcome_day is not None
    assert "CHẾ ĐỘ DẠY" in outcome_day.blocks[0].text

    # Lệnh xem danh sách chờ nạp và metric
    req_review = ChatActionRequest(question="xem các mục chờ nạp kho lsu")
    outcome_review = _handler(req_review)
    assert outcome_review is not None
    assert "Bề mặt xem lại & cải thiện" in outcome_review.blocks[0].text


def test_chat_intake_ui_session_widget_with_fakest(tmp_path: Path):
    """Widget hỏi-đáp tương tác mượt mà với FakeSt khi gửi câu trả lời và dừng phiên."""
    staging = IntakeStagingStore(tmp_path / "staging_ui.sqlite")
    engine = KnowledgeIntakeEngine(staging_store=staging)

    session = engine.start_session(
        store_id=STORE_ID_LSU,
        mode=MODE_PHONG_VAN,
        topic="C7620",
        expert_name="Anh Kỹ sư",
    )
    from aios_habit.chat_intake_ui import register_live_session
    register_live_session(session)

    fake = FakeSt()
    # Nhập câu trả lời vào text area
    key_ans = "intake_q_%s_0_ans" % session.session_id.replace("-", "_")
    key_submit = "intake_q_%s_0_submit" % session.session_id.replace("-", "_")
    fake.text_area_inputs[key_ans] = "Mã lỗi C7620, cụm sấy không nóng."
    fake.button_clicks[key_submit] = True

    render_intake_session_widget(fake, session.session_id, staging_store=staging)
    assert fake.rerun_called
    assert len(session.turns) >= 2  # Đã chuyển sang câu hỏi tiếp theo


def test_chat_intake_ui_review_widget_with_fakest(tmp_path: Path):
    """Widget duyệt nháp tại chỗ với 3 nút [Đúng], [Sửa], [Loại] phản hồi chính xác."""
    staging = IntakeStagingStore(tmp_path / "staging_ui_rev.sqlite")

    session_rec = IntakeSessionRecord(
        session_id="sess-test-ui-01",
        store_id=STORE_ID_LSU,
        mode=MODE_PHONG_VAN,
        expert_name="Anh Ba",
        topic="C7620",
        status="ended",
    )
    staging.save_session(session_rec)

    draft = IntakeDraftItemRecord(
        draft_id="draft-ui-01",
        session_id="sess-test-ui-01",
        store_id=STORE_ID_LSU,
        mode=MODE_PHONG_VAN,
        expert_name="Anh Ba",
        topic="C7620",
        source_tag="phong-van | Anh Ba | 2026-10-18 | kho_lsu",
        fields={"ma_loi": "C7620", "hien_tuong": "Kẹt giấy"},
        source_quote="Kẹt giấy ở cửa ra",
    )
    staging.save_draft_item(draft)

    # 1. Bấm nút [Đúng (Chờ nạp)]
    fake_ok = FakeSt()
    card_key = "wsc_draft_draft_ui_01"
    fake_ok.button_clicks[card_key + "_btn_ok"] = True

    render_intake_review_widget(fake_ok, "sess-test-ui-01", staging_store=staging)
    assert fake_ok.rerun_called
    assert any("CHỜ NẠP" in msg for msg in fake_ok.success_calls)

    updated = staging.get_draft_item("draft-ui-01")
    assert updated is not None
    assert updated.review_status == STATUS_DUNG
    assert updated.ingest_status == INGEST_CHO_NAP

    # 2. Bấm nút [Loại bỏ]
    fake_rej = FakeSt()
    fake_rej.button_clicks[card_key + "_btn_rej"] = True

    render_intake_review_widget(fake_rej, "sess-test-ui-01", staging_store=staging)
    assert fake_rej.rerun_called
    assert any("loại bỏ" in msg.lower() for msg in fake_rej.warning_calls)

    updated_rej = staging.get_draft_item("draft-ui-01")
    assert updated_rej is not None
    assert updated_rej.review_status == STATUS_LOAI
    assert updated_rej.ingest_status == INGEST_KHONG_NAP


def test_marker_helpers_extract_and_strip():
    """Kiểm tra các hàm marker nhúng và bóc tách HTML comment."""
    m_sess = intake_session_marker("sess-123", "kho_lsu")
    m_rev = intake_review_marker("sess-123", "kho_lsu")

    content = f"Văn bản mở đầu\n{m_sess}\n{m_rev}\nVăn bản kết thúc"

    extracted_sess = extract_intake_session_marker(content)
    assert extracted_sess == {"session_id": "sess-123", "store_id": "kho_lsu"}

    extracted_rev = extract_intake_review_marker(content)
    assert extracted_rev == {"session_id": "sess-123", "store_id": "kho_lsu"}

    clean = strip_intake_markers(content)
    assert "aios_intake_session" not in clean
    assert "aios_intake_review" not in clean
    assert "Văn bản mở đầu" in clean
    assert "Văn bản kết thúc" in clean


# ===========================================================================
# 6. Kiểm thử hồi quy độ chính xác phát hiện khía cạnh & nhãn ghi_chu
#    (Ticket DESKTOP-KNOWLEDGE-INTAKE-PROBE-LABEL-FIX-HOME)
# ===========================================================================


def test_regression_c7620_opening_with_qua_nhiet_triggers_early_signs_probe():
    """Hồi quy 1: Câu trả lời mở đầu chứa 'quá nhiệt' vẫn kích hoạt câu đào sâu dấu hiệu sớm.

    Từ 'nhiệt' trong 'quá nhiệt' hoặc 'lô sấy' không được coi là đã có dấu hiệu sớm.
    Cả 5 nhóm khía cạnh không được đánh dấu 'đã có' chỉ vì một từ ngẫu nhiên.
    """
    answer_c7620 = "Mã lỗi C7620, hiện tượng máy báo quá nhiệt lô sấy trên model Sirius."
    missing = detect_missing_aspects_interview(answer_c7620)
    assert PROBE_DAU_HIEU_SOM in missing
    assert PROBE_PHAN_BIET_LOI in missing

    # Khi nạp câu trả lời vào engine, câu đào sâu tiếp theo phải là dấu hiệu nhận biết sớm
    engine = KnowledgeIntakeEngine()
    session = engine.start_session(
        store_id=STORE_ID_LSU,
        mode=MODE_PHONG_VAN,
        topic="Lỗi C7620",
        expert_name="Kỹ sư Test",
    )
    is_done, msg, next_turn = engine.submit_answer(session, answer_c7620)
    assert not is_done
    assert next_turn is not None
    assert next_turn.probe_type == PROBE_DAU_HIEU_SOM
    assert "Dấu hiệu nhận biết sớm" in next_turn.question_text

    # Kiểm tra thêm 4 nhóm còn lại không bị đánh lừa bởi từ đơn ngẫu nhiên:
    # - "dòng điện 220V" không bị tính là model/line (chữ "dòng")
    # - "không được tắt máy" không bị tính là xử lý không hiệu quả (chữ "không được")
    # - "nhiệt độ sấy tăng" không bị tính là điều kiện phát sinh (chữ "nhiệt độ")
    # - "nhảm nhí" không bị tính là phân biệt lỗi gần giống (chữ "nham")
    tricky_text = "Hiện tượng dòng điện 220V sụt áp, nhiệt độ sấy tăng, công nhân không được thao tác nhảm nhí."
    tricky_missing = detect_missing_aspects_interview(tricky_text)
    assert PROBE_MODEL_LINE in tricky_missing
    assert PROBE_XU_LY_KHONG_HIEU_QUA in tricky_missing
    assert PROBE_DIEU_KIEN_PHAT_SINH in tricky_missing
    assert PROBE_PHAN_BIET_LOI in tricky_missing
    assert PROBE_DAU_HIEU_SOM in tricky_missing


def test_regression_interview_simulation_aligns_answers_to_actual_probes(tmp_path: Path):
    """Hồi quy 2: Chạy phiên phỏng vấn mô phỏng cấp câu trả lời theo ĐÚNG thứ tự câu hỏi

    bộ máy đặt ra, kiểm tra từng đoạn ghi_chu mang nhãn của đúng câu hỏi đã mời ra câu trả lời đó.
    """
    staging = IntakeStagingStore(tmp_path / "staging_regr_interview.sqlite")
    engine = KnowledgeIntakeEngine(staging_store=staging)

    session = engine.start_session(
        store_id=STORE_ID_LSU,
        mode=MODE_PHONG_VAN,
        topic="Lỗi C7620 quá nhiệt cụm sấy",
        expert_name="Kỹ sư Nguyễn Văn An",
    )

    # Từ điển câu trả lời chuẩn theo probe_type thật sự của câu hỏi được máy đặt ra
    responses_by_probe = {
        "hien_tuong_ma_loi": "Mã lỗi C7620, hiện tượng máy báo quá nhiệt lô sấy trên model Sirius.",
        PROBE_DAU_HIEU_SOM: "Dấu hiệu nhận biết sớm là rơ-le nhiệt nhảy lạch cạch và giấy ra hơi cong mép.",
        PROBE_PHAN_BIET_LOI: "Phân biệt với lỗi C7610 (đứt cầu chì nhiệt): C7620 nhiệt tăng vọt trên 215 độ C trước khi ngắt.",
        PROBE_4M_WHY: "Theo 4M + Why-Why: nguyên nhân do bụi mực đóng cặn trên bề mặt cảm biến thermistor làm đọc nhiệt độ thấp hơn thực tế nên mạch cấp nguồn đun liên tục.",
        PROBE_XU_LY_HIEU_QUA: "Đối sách hiệu quả là vệ sinh đầu dò thermistor bằng cồn IPA và thay miếng đệm cách nhiệt tại công đoạn Lắp ráp cụm sấy trên Line 2.",
        PROBE_XU_LY_KHONG_HIEU_QUA: "Đã thử chỉnh offset phần mềm nhưng không hiệu quả.",
        PROBE_DIEU_KIEN_PHAT_SINH: "Điều kiện phát sinh: nhiệt độ môi trường phòng máy trên 35 độ C hoặc chạy liên tục nhiều ca.",
        PROBE_MODEL_LINE: "Xảy ra trên model Sirius tại Line 2.",
        "cong_doan_line": "Thuộc công đoạn Lắp ráp cụm sấy trên Line 2.",
    }

    # Đọc câu hỏi THẬT bộ máy đặt ra rồi mới trả lời theo đúng câu hỏi đó (Luật Mục 5 của vé)
    max_turns = 10
    turn_count = 0
    while not session.is_completed and turn_count < max_turns:
        turn_count += 1
        current_turn = session.turns[-1]
        pt = current_turn.probe_type
        ans = responses_by_probe.get(
            pt,
            "Thông tin bổ sung cho khía cạnh %s." % pt,
        )
        is_done, msg, next_turn = engine.submit_answer(session, ans)
        if is_done:
            break

    drafts = engine.end_and_synthesize(session)
    assert len(drafts) == 1
    draft = drafts[0]
    fields = draft.fields

    # Kiểm tra 5 trường bắt buộc
    assert fields["ma_loi"] == "C7620"
    assert "quá nhiệt" in fields["hien_tuong"]
    assert "thermistor" in fields["nguyen_nhan"]
    assert "vệ sinh đầu dò thermistor" in fields["doi_sach"]
    assert fields["cong_doan"] == "Lắp Ráp Cụm Sấy"

    # Kiểm tra các trường phụ
    assert fields["model"] == "Sirius"
    assert fields["line"] == "Line 2"
    assert "rơ-le nhiệt nhảy lạch cạch" in fields["dau_hieu_som"]

    # KIỂM TRA ĐỘ CHÍNH XÁC NHÃN GHI CHÚ:
    # Tách các đoạn trong ghi_chu để kiểm chứng từng nhãn khớp chính xác với nội dung câu hỏi
    ghi_chu = fields["ghi_chu"]
    assert "[phan_biet_loi_gan_giong]:" in ghi_chu
    assert "[dieu_kien_phat_sinh]:" in ghi_chu
    assert "[xu_ly_khong_hieu_qua]:" in ghi_chu

    # 1. phan_biet_loi_gan_giong PHẢI mang nội dung so sánh với C7610, KHÔNG mang nội dung dấu hiệu sớm
    part_phan_biet = ghi_chu.split("[phan_biet_loi_gan_giong]:")[1].split("[")[0]
    assert "C7610" in part_phan_biet
    assert "rơ-le nhiệt nhảy lạch cạch" not in part_phan_biet

    # 2. dieu_kien_phat_sinh PHẢI mang nội dung điều kiện môi trường, TUYỆT ĐỐI KHÔNG mang nội dung C7610
    part_dieu_kien = ghi_chu.split("[dieu_kien_phat_sinh]:")[1].split("[")[0]
    assert "nhiệt độ môi trường" in part_dieu_kien
    assert "C7610" not in part_dieu_kien

    # 3. xu_ly_khong_hieu_qua PHẢI mang nội dung chỉnh offset phần mềm
    part_khong_hieu_qua = ghi_chu.split("[xu_ly_khong_hieu_qua]:")[1].split("[")[0]
    assert "chỉnh offset phần mềm" in part_khong_hieu_qua
    assert "C7610" not in part_khong_hieu_qua


def test_regression_teaching_simulation_preserves_pham_vi_and_ngoai_le_labels(tmp_path: Path):
    """Hồi quy 3: Chế độ dạy với cặp phạm vi áp dụng / trường hợp ngoại lệ.

    Đọc câu hỏi thật của bộ máy và trả lời đúng theo câu hỏi, đảm bảo nhãn
    [pham_vi_ap_dung] và [truong_hop_ngoai_le] không bị tráo đổi.
    """
    staging = IntakeStagingStore(tmp_path / "staging_regr_teaching.sqlite")
    engine = KnowledgeIntakeEngine(staging_store=staging)

    session = engine.start_session(
        store_id=STORE_ID_LSU,
        mode=MODE_DAY,
        topic="Cân chỉnh chùm tia cụm quang LSU C3501",
        expert_name="Chuyên gia Trần Minh Đức",
    )

    responses_by_probe = {
        "mo_dau_bai_giang": (
            "Khi lắp cụm LSU cho dòng máy Iris, nếu lệch trục gương đa giác sẽ gây mã lỗi C3501 "
            "lệch đồng bộ tia laser đầu dòng (BD sensor error) tại công đoạn Kiểm tra quang học trên Line 1."
        ),
        CLARIFY_PHAM_VI: (
            "Áp dụng cho toàn bộ dòng máy Iris và Sirius tại công đoạn Kiểm tra quang học."
        ),
        CLARIFY_NGOAI_LE: (
            "Trường hợp ngoại lệ: khi nhiệt độ phòng dưới 18 độ C cần chạy làm ấm motor 5 phút trước khi căn chỉnh bằng dưỡng JIG-LSU-04."
        ),
        CLARIFY_VI_DU_THAT: (
            "Ví dụ thật ở nhà máy: tháng trước Line 1 bị 12 máy báo C3501 liên tiếp do kỹ thuật viên mới siết ốc gương theo chiều kim đồng hồ làm trượt giá đỡ."
        ),
        CLARIFY_HIEU_SAI: (
            "Chỗ người mới hay hiểu sai: người mới hay hiểu sai là chỉnh chiết áp công suất laser sẽ hết nhưng thực ra phải chỉnh cơ khí gương phản xạ."
        ),
    }

    # Đọc câu hỏi THẬT bộ máy đặt ra rồi mới trả lời theo đúng câu hỏi đó (Mục 5 của vé)
    max_turns = 10
    turn_count = 0
    while not session.is_completed and turn_count < max_turns:
        turn_count += 1
        current_turn = session.turns[-1]
        pt = current_turn.probe_type
        ans = responses_by_probe.get(
            pt,
            "Giải thích bổ sung về bài giảng cho khía cạnh %s." % pt,
        )
        is_done, msg, next_turn = engine.submit_answer(session, ans)
        if is_done:
            break

    drafts = engine.end_and_synthesize(session)
    assert len(drafts) == 1
    draft = drafts[0]
    ghi_chu = draft.fields["ghi_chu"]

    # Kiểm tra nhãn [pham_vi_ap_dung] mang ĐÚNG nội dung phạm vi máy
    assert "[pham_vi_ap_dung]: Áp dụng cho toàn bộ dòng máy Iris và Sirius tại công đoạn Kiểm tra quang học." in ghi_chu
    # Kiểm tra nhãn [truong_hop_ngoai_le] mang ĐÚNG nội dung ngoại lệ nhiệt độ < 18 độ C
    assert "[truong_hop_ngoai_le]: Trường hợp ngoại lệ: khi nhiệt độ phòng dưới 18 độ C cần chạy làm ấm motor 5 phút" in ghi_chu

    # KHÔNG BỊ TRÁO ĐỔI:
    assert "[pham_vi_ap_dung]: Trường hợp ngoại lệ" not in ghi_chu
    assert "[truong_hop_ngoai_le]: Áp dụng cho toàn bộ dòng máy" not in ghi_chu

