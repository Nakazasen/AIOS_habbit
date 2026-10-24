from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from aios_habit.answer_cache import (
    apply_cached_answer_to_conversation,
    build_cache_key,
    cache_metrics_file,
    cache_store_file,
    capture_last_assistant_turn_to_cache,
    compute_cache_metrics_summary,
    compute_relevant_data_fingerprint,
    format_fast_answer_notice,
    invalidate_cached_answer,
    lookup_cached_answer,
    normalize_question_for_cache,
    normalize_scope_id,
    record_cache_turn_metric,
    store_cached_answer,
)
from aios_habit.answer_feedback import RATING_CHUA_HUU_ICH, RATING_HUU_ICH, record_feedback
from aios_habit.workspace_chat_models import ChatMessage
from aios_habit.workspace_chat_ui import (
    extract_evidence_items_for_message,
    render_cached_answer_notice_block,
)


def test_normalize_question_for_cache_exact_rules() -> None:
    """Kiểm tra chuẩn hóa câu hỏi: gộp khoảng trắng thừa, chữ thường, bỏ dấu câu 2 đầu, KHÔNG khớp mờ."""
    q1 = "   Mã lỗi   C7620   nguyên nhân và đối sách là gì?!...  "
    q2 = "mã lỗi c7620 nguyên nhân và đối sách là gì"
    assert normalize_question_for_cache(q1) == "mã lỗi c7620 nguyên nhân và đối sách là gì"
    assert normalize_question_for_cache(q1) == normalize_question_for_cache(q2)

    scope = normalize_scope_id(notebook_id="NB-LAZY-DTL", forced_domain="dieu_tra_loi")
    k1, h1 = build_cache_key(q1, scope_id=scope, data_fingerprint="fp_v1")
    k2, h2 = build_cache_key(q2, scope_id=scope, data_fingerprint="fp_v1")
    assert k1 == k2
    assert h1 == h2

    # Câu gần giống (khác 1 từ) TUYỆT ĐỐI không trùng khóa (không khớp mờ)
    q_near = "Mã lỗi C7620 nguyên nhân là gì?"
    k_near, h_near = build_cache_key(q_near, scope_id=scope, data_fingerprint="fp_v1")
    assert k_near != k1
    assert h_near != h1


def test_cache_hit_miss_and_evidence_preservation(tmp_path: Path) -> None:
    """Kiểm tra lưu và lấy từ bộ nhớ kèm trích dẫn gắn theo từng câu trả lời."""
    scope = normalize_scope_id(notebook_id="NB-LAZY-DTL", forced_domain="dieu_tra_loi")
    fp = "fp_20261024_a"
    question = "Mã lỗi C7620 nguyên nhân và đối sách là gì?"

    # Lượt 1: Chưa có trong bộ nhớ -> Miss
    assert lookup_cached_answer(
        question,
        scope_id=scope,
        data_fingerprint=fp,
        base_dir=tmp_path,
    ) is None

    evidence = [
        {
            "title": "01_25_KDTPS_2025.xlsx",
            "location_info": "sheet Chi tiết, dòng 45",
            "text": "C7620: Lỗi cảm biến nhiệt độ cụm sấy, kiểm tra cầu chì nhiệt và giắc cắm CN12.",
            "source_type": "db_error_case",
            "source_file": "01_25_KDTPS_2025.xlsx",
            "sheet_name": "Chi tiết",
            "source_row": 45,
        }
    ]
    stored = store_cached_answer(
        question,
        answer_text="### Kết quả tra cứu C7620\n- Nguyên nhân: Lỗi cảm biến nhiệt độ cụm sấy.\n- Nguồn: `01_25_KDTPS_2025.xlsx` (sheet Chi tiết, dòng 45).",
        scope_id=scope,
        data_fingerprint=fp,
        notebook_id="NB-LAZY-DTL",
        evidence_items=evidence,
        snapshot_time_display="09:30:00 24/10/2026",
        base_dir=tmp_path,
    )
    assert stored.key_hash
    assert cache_store_file(tmp_path).is_file()

    # Lượt 2: Hỏi lại câu đã chuẩn hóa tương đương -> Hit ngay lập tức kèm trích dẫn
    hit = lookup_cached_answer(
        "  mã lỗi   c7620 nguyên nhân và đối sách là gì??? ",
        scope_id=scope,
        data_fingerprint=fp,
        base_dir=tmp_path,
    )
    assert hit is not None
    assert hit.key_hash == stored.key_hash
    assert hit.hit_count == 1
    assert len(hit.evidence_items) == 1
    assert hit.evidence_items[0]["title"] == "01_25_KDTPS_2025.xlsx"
    assert hit.evidence_items[0]["source_row"] == 45
    assert "09:30:00 24/10/2026" in format_fast_answer_notice(hit.snapshot_time_display)

    # Khác kho/khối tri thức -> Miss
    other_scope = normalize_scope_id(notebook_id="NB-LAZY-MOM", forced_domain="mom")
    assert lookup_cached_answer(
        question,
        scope_id=other_scope,
        data_fingerprint=fp,
        base_dir=tmp_path,
    ) is None


def test_invalidation_when_data_fingerprint_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Khi vân tay dữ liệu của kho thay đổi, bản ghi cũ không còn khớp và lượt hỏi mới ghi đè bản ghi mới."""
    scope = normalize_scope_id(notebook_id="NB-LAZY-DTL", forced_domain="dieu_tra_loi")
    question = "Lỗi vạch ngang bước 94mm nguyên nhân là do gì?"

    monkeypatch.setenv("AIOS_ANSWER_CACHE_DATA_FINGERPRINT_OVERRIDE", "fp_before_ingest")
    fp_old = compute_relevant_data_fingerprint(notebook_id="NB-LAZY-DTL", forced_domain="dieu_tra_loi")

    store_cached_answer(
        question,
        answer_text="Câu trả lời cũ trước khi cập nhật chỉ mục.",
        scope_id=scope,
        data_fingerprint=fp_old,
        notebook_id="NB-LAZY-DTL",
        evidence_items=[{"title": "SOP_Drum.pdf", "location_info": "trang 12", "text": "Chu vi trống 94mm."}],
        base_dir=tmp_path,
    )

    assert lookup_cached_answer(question, scope_id=scope, data_fingerprint=fp_old, base_dir=tmp_path) is not None

    # Giả lập kho vừa nạp thêm tài liệu / chỉ mục cập nhật -> đổi vân tay dữ liệu
    monkeypatch.setenv("AIOS_ANSWER_CACHE_DATA_FINGERPRINT_OVERRIDE", "fp_after_new_doc_ingest")
    fp_new = compute_relevant_data_fingerprint(notebook_id="NB-LAZY-DTL", forced_domain="dieu_tra_loi")
    assert fp_new != fp_old

    # Tra cứu với vân tay mới phải trả về None (không dùng bản ghi cũ)
    assert lookup_cached_answer(question, scope_id=scope, data_fingerprint=fp_new, base_dir=tmp_path) is None

    # Sau khi chạy tươi và lưu bản ghi mới, tra cứu với vân tay mới sẽ trúng bản ghi mới
    store_cached_answer(
        question,
        answer_text="Câu trả lời mới sau khi cập nhật tài liệu.",
        scope_id=scope,
        data_fingerprint=fp_new,
        notebook_id="NB-LAZY-DTL",
        evidence_items=[{"title": "SOP_Drum_v2.pdf", "location_info": "trang 15", "text": "Bổ sung kiểm tra trục sạc."}],
        base_dir=tmp_path,
    )
    hit_new = lookup_cached_answer(question, scope_id=scope, data_fingerprint=fp_new, base_dir=tmp_path)
    assert hit_new is not None
    assert "Câu trả lời mới" in hit_new.answer_text
    assert hit_new.evidence_items[0]["title"] == "SOP_Drum_v2.pdf"


def test_dislike_feedback_invalidates_cached_answer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Bấm 'không thích' (chua_huu_ich) trên câu trả lời lấy từ bộ nhớ thì vô hiệu hóa bản ghi đó cho lần hỏi sau."""
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))
    scope = normalize_scope_id(notebook_id="NB-LAZY-DTL", forced_domain="dieu_tra_loi")
    fp = "fp_dislike_test"
    question = "Mã lỗi C7620 xử lý như thế nào?"

    store_cached_answer(
        question,
        answer_text="Đáp án lưu trong bộ nhớ.",
        scope_id=scope,
        data_fingerprint=fp,
        notebook_id="NB-LAZY-DTL",
        base_dir=tmp_path,
    )

    # Bấm "Hữu ích" (👍) -> giữ nguyên bản ghi trong bộ nhớ
    res_up = record_feedback(
        conversation_id="CONV-1",
        message_id="MSG-A-1",
        question=question,
        answer="Đáp án lưu trong bộ nhớ.",
        rating=RATING_HUU_ICH,
        domain=scope,
    )
    assert res_up["ok"] is True
    assert lookup_cached_answer(question, scope_id=scope, data_fingerprint=fp, base_dir=tmp_path) is not None

    # Bấm "Chưa hữu ích" (👎) -> ghi vào answer_feedback.jsonl VÀ vô hiệu hóa bản ghi cache
    fb_rec = record_feedback(
        conversation_id="CONV-1",
        message_id="MSG-A-2",
        question=question,
        answer="Đáp án lưu trong bộ nhớ.",
        rating=RATING_CHUA_HUU_ICH,
        reason_category="sai",
        reason="Thiếu bước kiểm tra cầu chì nhiệt",
        domain=scope,
    )
    assert fb_rec["ok"] is True
    assert (tmp_path / "answer_feedback.jsonl").is_file()

    # Lần hỏi tiếp theo cho khóa đó phải trả về None (buộc chạy tươi, không khóa lỗi vào bộ nhớ)
    assert lookup_cached_answer(question, scope_id=scope, data_fingerprint=fp, base_dir=tmp_path) is None


def test_bypass_cache_retry_button_and_metrics_privacy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra nút 'Hỏi lại' (bypass_cache=True) và ghi metric ẩn danh không lộ câu hỏi thô."""
    scope = normalize_scope_id(notebook_id="NB-LAZY-DTL", forced_domain="dieu_tra_loi")
    fp = "fp_retry_test"
    secret_question = "Câu hỏi nhạy cảm nội bộ C7620 số serial SN-998877?"

    entry = store_cached_answer(
        secret_question,
        answer_text="Bản trả lời lần 1.",
        scope_id=scope,
        data_fingerprint=fp,
        snapshot_time_display="10:00:00 24/10/2026",
        base_dir=tmp_path,
    )

    # Khi bấm "Hỏi lại" -> bypass_cache=True phải bỏ qua bộ nhớ
    assert lookup_cached_answer(
        secret_question,
        scope_id=scope,
        data_fingerprint=fp,
        bypass_cache=True,
        base_dir=tmp_path,
    ) is None

    # Ghi metric cho lượt miss (lượt 1: 4200 ms) và lượt hit (lượt 2: 12.5 ms)
    record_cache_turn_metric(
        cache_hit=False,
        response_time_ms=4200.0,
        key_hash=entry.key_hash,
        scope_id=scope,
        data_fingerprint=fp,
        bypass_requested=False,
        conversation_id="CONV-TEST-1",
        base_dir=tmp_path,
    )
    record_cache_turn_metric(
        cache_hit=True,
        response_time_ms=12.5,
        key_hash=entry.key_hash,
        scope_id=scope,
        data_fingerprint=fp,
        bypass_requested=False,
        conversation_id="CONV-TEST-1",
        base_dir=tmp_path,
    )

    m_file = cache_metrics_file(tmp_path)
    assert m_file.is_file()
    raw_metrics_text = m_file.read_text(encoding="utf-8")
    # TUYỆT ĐỐI không chứa câu hỏi thô trong tệp metric
    assert "SN-998877" not in raw_metrics_text
    assert "Câu hỏi nhạy cảm" not in raw_metrics_text

    summary = compute_cache_metrics_summary(tmp_path)
    assert summary["total_turns"] == 2
    assert summary["hit_count"] == 1
    assert summary["miss_count"] == 1
    assert summary["hit_rate_pct"] == 50.0
    assert summary["avg_hit_ms"] == 12.5
    assert summary["avg_miss_ms"] == 4200.0


def test_render_cached_answer_notice_block_and_retry_trigger(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra hiển thị dòng thông báo trả lời nhanh và nút '🔄 Hỏi lại' kích hoạt cờ bypass_cache."""
    import aios_habit.workspace_chat_ui as ui_mod

    captions: List[str] = []
    reruns: List[bool] = []

    class DummyCol:
        def __enter__(self) -> "DummyCol":
            return self

        def __exit__(self, *args: Any) -> None:
            pass

    class DummySt:
        def __init__(self, click_retry: bool = False) -> None:
            self.session_state: Dict[str, Any] = {}
            self.click_retry = click_retry

        def caption(self, text: str, **kwargs: Any) -> None:
            captions.append(text)

        def columns(self, spec: Any, **kwargs: Any) -> List[DummyCol]:
            return [DummyCol(), DummyCol()]

        def button(self, label: str, key: str = "", **kwargs: Any) -> bool:
            if "Hỏi lại" in label and self.click_retry:
                return True
            return False

        def rerun(self) -> None:
            reruns.append(True)

    dummy_st = DummySt(click_retry=True)
    monkeypatch.setattr(ui_mod, "st", dummy_st)

    cached_msg = ChatMessage(
        id="MSG-A-CACHE1",
        conversation_id="CONV-UI-1",
        role="assistant",
        content="Nội dung trả lời từ bộ nhớ.",
        metadata={
            "cache_hit": True,
            "cache_snapshot_time": "10:15:00 24/10/2026",
            "cached_question": "Mã lỗi C7620 nguyên nhân và đối sách là gì?",
            "evidence_items": [
                {
                    "title": "01_25_KDTPS_2025.xlsx",
                    "location_info": "sheet Chi tiết, dòng 45",
                    "text": "Chi tiết ca lỗi C7620.",
                }
            ],
        },
    )

    ev_items = extract_evidence_items_for_message(cached_msg, display_content=cached_msg.content)
    assert len(ev_items) == 1
    assert ev_items[0]["title"] == "01_25_KDTPS_2025.xlsx"

    rendered = render_cached_answer_notice_block(
        msg=cached_msg,
        conversation_id="CONV-UI-1",
        feedback_question="Mã lỗi C7620 nguyên nhân và đối sách là gì?",
        render_interactive=True,
    )
    assert rendered is True
    assert any("Trả lời nhanh từ câu hỏi đã hỏi trước" in c and "10:15:00 24/10/2026" in c for c in captions)
    assert dummy_st.session_state.get("wsc_bypass_answer_cache_CONV-UI-1") is True
    assert dummy_st.session_state.get("wsc_suggest_send_CONV-UI-1") == "Mã lỗi C7620 nguyên nhân và đối sách là gì?"
    assert len(reruns) == 1
