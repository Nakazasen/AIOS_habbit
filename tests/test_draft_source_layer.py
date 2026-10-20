"""Kiểm thử tầng nguồn bản thảo (ticket DESKTOP-SELF-LEARN-DRAFT-SOURCE-LAYER)."""

import json
from pathlib import Path
import pytest
import sqlite3
import time

from aios_habit.draft_source_layer import (
    MANDATORY_DRAFT_LABEL,
    DraftSearchIndex,
    DraftSearchResult,
    DraftSourceItem,
    check_and_promote_draft_candidate,
    extract_key_metrics_and_specs,
    format_draft_answer_body,
    get_draft_search_index,
    has_mandatory_draft_label,
    load_chatgpt_draft_items,
    load_intake_staging_draft_items,
    load_unified_draft_catalog,
    reconcile_draft_with_standard,
    record_draft_feedback,
    record_draft_invocation,
    reset_draft_search_index,
)


def test_load_unified_draft_catalog():
    """Kiểm tra nạp đủ 54 tệp ChatGPT và các mục từ intake staging."""
    chatgpt_items = load_chatgpt_draft_items()
    assert len(chatgpt_items) >= 2000, f"Expected >= 2000 ChatGPT items, got {len(chatgpt_items)}"

    # Kiểm tra các tệp thuộc LSU và MOM
    lsu_files = {item.source_file for item in chatgpt_items if "lsu" in item.source_file.lower()}
    mom_files = {item.source_file for item in chatgpt_items if "mom" in item.source_file.lower()}
    assert len(lsu_files) >= 39, f"Expected >= 39 LSU files, got {len(lsu_files)}"
    assert len(mom_files) >= 15, f"Expected >= 15 MOM files, got {len(mom_files)}"
    assert len(lsu_files) + len(mom_files) >= 54, "Tổng số tệp LSU + MOM phải đạt tối thiểu 54 tệp"

    # Kiểm tra nạp intake staging
    intake_items = load_intake_staging_draft_items()
    assert len(intake_items) >= 10, f"Expected >= 10 intake items, got {len(intake_items)}"

    # Hợp nhất catalog
    catalog = load_unified_draft_catalog()
    assert len(catalog) == len(chatgpt_items) + len(intake_items)


def test_draft_search_index_latency_under_30ms():
    """Kiểm tra độ trễ tìm kiếm của tầng bản thảo bắt buộc phải dưới 30ms."""
    reset_draft_search_index()
    index = get_draft_search_index()

    test_queries = [
        "LSU Beam",
        "Jig 1002 NanoScan",
        "MOM Opcenter",
        "Lỗi lệch tâm quang học",
        "Laser Diode",
    ]

    for q in test_queries:
        results, elapsed_ms = index.search(q, top_k=3, allow_unscoped=True)
        assert elapsed_ms < 30.0, f"Query '{q}' took {elapsed_ms:.2f}ms, exceeding 30ms limit!"
        assert len(results) > 0, f"Query '{q}' should return at least 1 result"
        for r in results:
            assert r.item.item_id
            assert r.score > 0
            assert r.search_time_ms < 30.0


def test_mandatory_draft_label_enforcement():
    """Kiểm tra áp đặt nhãn bắt buộc '[Bản thảo - chưa kiểm chứng qua chuyên gia]'."""
    raw_answer = "Cần hiệu chỉnh lại SettingFile của Jig 1002 theo máy đo NanoScan."
    formatted = format_draft_answer_body(raw_answer, source_name="docs/phieu-viec/chatgpt-enrichment-fixed/lsu/test.md")

    assert MANDATORY_DRAFT_LABEL in formatted
    assert has_mandatory_draft_label(formatted) is True
    assert "lsu/test.md" in formatted
    assert raw_answer in formatted

    # Nếu chuỗi đã có nhãn thì không bị nhân đôi
    re_formatted = format_draft_answer_body(formatted)
    assert formatted == re_formatted


def test_reconcile_draft_with_standard_no_conflict():
    """Kiểm tra hòa trộn khi không có xung đột số liệu: chuẩn kết hợp bản thảo có nhãn."""
    std = "Quy trình kiểm tra LSU bao gồm 4 bước chính theo tài liệu SOP-LSU-01."
    draft = "Các bước thao tác chi tiết trên máy jig đo quang học."

    res = reconcile_draft_with_standard(
        standard_text=std,
        draft_text=draft,
        standard_source_title="SOP-LSU-01",
        draft_source_title="lsu/LSU_01.md",
    )

    assert res.has_conflict is False
    assert MANDATORY_DRAFT_LABEL in res.reconciled_text
    assert "SOP-LSU-01" in std
    assert draft in res.reconciled_text
    assert len(res.conflicting_specs) == 0


def test_reconcile_draft_with_standard_conflicting_numbers():
    """Kiểm tra chống phối số liệu mâu thuẫn: Chuẩn thắng, bản thảo ghi chú đối chiếu."""
    std = "Tiêu chuẩn dung sai đường kính Beam cho phép là ±0.02 mm theo quy chuẩn QC-IRIS."
    draft = "Theo kinh nghiệm vận hành, dung sai Beam thường áp dụng là ±0.05 mm."

    res = reconcile_draft_with_standard(
        standard_text=std,
        draft_text=draft,
        standard_source_title="QC-IRIS",
        draft_source_title="chatgpt-enrichment/lsu_beam.md",
    )

    assert res.has_conflict is True
    assert len(res.conflicting_specs) >= 1
    assert "±0.02 mm" in res.reconciled_text
    # Kiểm tra ghi chú đối chiếu rõ ràng
    assert "Đối chiếu bản thảo:" in res.reconciled_text
    assert "Hệ thống ưu tiên số liệu chuẩn" in res.reconciled_text
    assert MANDATORY_DRAFT_LABEL in res.reconciled_text


def test_automatic_promotion_candidate_generation(tmp_path: Path):
    """Kiểm tra tự động sinh ứng viên thăng hạng khi bản thảo được gọi > 3 lần và Like cao."""
    draft_id = "DFT-TEST-LSU-BEAM-01"
    question = "Cách xử lý chênh lệch đo Beam giữa Jig 1002 và NanoScan"
    source_file = "lsu/LSU_BEAM_FIX.md"

    # Gọi 4 lần (> 3 lần)
    for _ in range(4):
        record_draft_invocation(
            draft_id=draft_id,
            question=question,
            source_file=source_file,
            domain="lsu",
            base_cases_dir=tmp_path,
        )

    # Chưa có Like -> Chưa được sinh đề xuất thăng hạng
    stat_file = tmp_path / "draft_source_stats.jsonl"
    assert stat_file.exists()
    expert_file = tmp_path / "expert_inquiries" / "expert_queue.jsonl"
    assert not expert_file.exists()

    # Nhận đánh giá Like
    record_draft_feedback(
        draft_id=draft_id,
        is_like=True,
        base_cases_dir=tmp_path,
    )

    # Sau khi Like, kiểm tra đã tự động tạo mục đề xuất trong expert_queue.jsonl
    assert expert_file.exists()
    queue_content = expert_file.read_text(encoding="utf-8")
    assert "draft_promotion_candidate" in queue_content
    assert draft_id in queue_content
    assert question in queue_content

    # Kiểm tra parse JSON hợp lệ
    lines = [json.loads(l) for l in queue_content.strip().splitlines() if l.strip()]
    assert len(lines) == 1
    item = lines[0]
    assert item["draft_id"] == draft_id
    assert item["invocation_count"] == 4
    assert item["like_count"] == 1
    assert item["status"] == "pending_expert_review"

    # Gọi lại lần nữa -> Không bị tạo trùng lặp
    candidate_again = check_and_promote_draft_candidate(draft_id, base_cases_dir=tmp_path)
    assert candidate_again is None
    lines_after = [json.loads(l) for l in expert_file.read_text(encoding="utf-8").strip().splitlines() if l.strip()]
    assert len(lines_after) == 1


def test_workspace_chat_ai_answer_parallel_draft_retrieval():
    """Kiểm tra tích hợp truy hồi song song vào workspace_chat_ai_answer."""
    from aios_habit.workspace_chat_ai_answer import (
        PRIVACY_MODE_CLOUD_ALLOWED,
        WorkspaceAIAnswerRequest,
        WorkspaceAIContextSource,
        generate_workspace_ai_answer,
        recall_draft_layer_for_answer,
    )

    req = WorkspaceAIAnswerRequest(
        conversation_id="conv-draft-test-01",
        question="LSU Beam và SettingFile",
        context_sources=(
            WorkspaceAIContextSource(
                source_id="src-1",
                source_scope="workspace",
                source_type="text",
                title="SOP-LSU.txt",
                privacy_label="cloud_allowed",
                text="Tài liệu kiểm tra LSU tiêu chuẩn quy định trình tự kiểm tra quang học.",
                included_chars=75,
            ),
        ),
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        cloud_consent_confirmed=True,
        consent_source_keys=(("workspace", "src-1"),),
        notebook_id="NB-LAZY-LSU",
    )

    # 1. Gọi trực tiếp recall_draft_layer_for_answer
    t0 = time.perf_counter()
    drafts = recall_draft_layer_for_answer(req, top_k=2)
    elapsed = (time.perf_counter() - t0) * 1000.0
    assert elapsed < 30.0, f"Draft recall took {elapsed:.2f}ms (> 30ms)"
    assert len(drafts) > 0

    # 2. Gọi generate_workspace_ai_answer với fake provider
    class FakeProvider:
        def generate(self, *, system_prompt: str, user_prompt: str) -> str:
            # Kiểm tra hệ thống prompt đã chèn quy tắc bản thảo và khối dữ liệu bản thảo
            assert "TẦNG NGUỒN BẢN THẢO" in system_prompt
            assert MANDATORY_DRAFT_LABEL in system_prompt
            assert "TẦNG NGUỒN BẢN THẢO" in user_prompt
            return f"Thông tin hiệu chỉnh theo {MANDATORY_DRAFT_LABEL}."

    res = generate_workspace_ai_answer(req, FakeProvider())
    assert res.ok is True
    assert len(res.draft_source_titles) > 0
    assert res.has_draft_label is True
    assert MANDATORY_DRAFT_LABEL in res.answer_text


def test_rag_answer_composer_anti_conflict_and_label_integration():
    """Kiểm tra ghép tầng bản thảo vào rag_answer_composer và chống phối số liệu mâu thuẫn."""
    from aios_habit.rag_ingest import RAGChunk
    from aios_habit.rag_evidence import build_evidence_pack, EvidencePackConfig
    from aios_habit.rag_search import create_rag_search_schema, index_rag_chunks, search_rag_chunks
    from aios_habit.rag_answer_composer import compose_local_answer

    # 1. Trường hợp có bằng chứng chuẩn và bản thảo có số liệu mâu thuẫn
    chunks = [
        RAGChunk("C1", "D1", ["e1"], "Dung sai đường kính cho phép là ±0.02 mm theo quy chuẩn QC-IRIS.", "QC-IRIS", "qc.pdf", "qc.pdf", "QC p1", "pdf", ["text"], [1], [], [], [], [], [], "cloud_safe"),
    ]
    conn = sqlite3.connect(":memory:")
    try:
        create_rag_search_schema(conn)
        index_rag_chunks(conn, chunks)
        res_items = search_rag_chunks(conn, "Dung sai đường kính Beam", limit=5)
        pack = build_evidence_pack("Dung sai đường kính Beam", res_items)
    finally:
        conn.close()

    # Giả lập draft result có số liệu mâu thuẫn (±0.05 mm)
    draft_item = DraftSourceItem(
        item_id="dft-lsu-99",
        source_type="chatgpt_enrichment",
        source_file="lsu/LSU_BEAM_TOLERANCE.md",
        domain="lsu",
        question="Dung sai đường kính Beam",
        answer="Kinh nghiệm đo thực tế dung sai thường là ±0.05 mm.",
    )
    mock_draft_result = DraftSearchResult(
        item=draft_item,
        score=1.5,
        search_time_ms=1.2,
    )

    answer = compose_local_answer(pack, draft_results=[mock_draft_result])
    assert answer.final_answer is False
    assert MANDATORY_DRAFT_LABEL in answer.answer_text
    assert "±0.02 mm" in answer.answer_text
    # Kiểm tra số liệu chuẩn thắng, bản thảo ghi chú đối chiếu
    assert "Đối chiếu bản thảo:" in answer.answer_text
    assert "Hệ thống ưu tiên số liệu chuẩn" in answer.answer_text
    assert answer.metadata.get("has_conflict") == "True"
    assert answer.metadata.get("has_draft_label") == "True"

    # 2. Trường hợp kho chuẩn không có bằng chứng (empty evidence), bản thảo bổ trợ
    empty_pack = build_evidence_pack("Dung sai đường kính Beam", [], EvidencePackConfig())
    empty_answer = compose_local_answer(empty_pack, draft_results=[mock_draft_result])
    assert MANDATORY_DRAFT_LABEL in empty_answer.answer_text
    assert "Kinh nghiệm đo thực tế" in empty_answer.answer_text
    assert any("tầng nguồn bản thảo" in w for w in empty_answer.warnings)


def test_deliver_5tier_ladder_answer_with_parallel_draft():
    """Kiểm tra deliver_5tier_ladder_answer tích hợp tầng bản thảo song song."""
    from aios_habit.final_answer_composer import deliver_5tier_ladder_answer
    from aios_habit.workspace_chat_store import load_messages
    import uuid

    conv_id = f"CONV-DRAFT-LADDER-{uuid.uuid4().hex[:8]}"
    chunks = []

    # Câu hỏi khớp với bản thảo LSU SettingFile
    ok, msg, badge, err = deliver_5tier_ladder_answer(
        question="LSU Beam SettingFile Jig 1002",
        conversation_id=conv_id,
        notebook_id="NB-LSU",
        user_raw_input="LSU Beam SettingFile Jig 1002",
        on_chunk=lambda c: chunks.append(c),
    )

    assert ok is True
    assert err is None
    assert badge is not None
    # Kiểm tra badge có thông tin draft_source
    assert badge["has_draft_label"] is True
    assert badge["draft_source"] != ""

    # Kiểm tra tin nhắn lưu trong SQLite
    saved_msgs = load_messages(conv_id)
    asst_msg = next(m for m in saved_msgs if m.role == "assistant")
    assert MANDATORY_DRAFT_LABEL in asst_msg.content
    assert "Hành động tiếp nối" in asst_msg.content
