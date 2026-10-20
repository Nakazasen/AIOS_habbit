# -*- coding: utf-8 -*-
"""Test suite verifying cross-notebook draft scope locking (ticket DESKTOP-HOME-DRAFT-STORE-SCOPE-FIX).

Test bẫy xuyên sổ (Bắt buộc theo mục 2C):
1. Câu hỏi chỉ có bản thảo khớp nằm ở SỔ KHÁC -> kết quả phải là đường trung thực / không có bản thảo,
   KHÔNG được phục vụ bản thảo sổ khác (cả 2 chiều: MOM <-> LSU và các sổ còn lại).
2. Đối chứng dương: câu hỏi có bản thảo khớp trong CHÍNH sổ đang mở vẫn được phục vụ kèm nhãn như cũ.
3. Test cho CẢ tầng mới (draft_source_layer, workspace_chat_ai_answer, rag_answer_composer,
   final_answer_composer) và đường dự bị cũ (answer_draft_fallback).
"""

from __future__ import annotations

import sqlite3
import uuid
from typing import List

import pytest

from aios_habit.draft_source_layer import (
    MANDATORY_DRAFT_LABEL,
    get_draft_search_index,
    reset_draft_search_index,
    resolve_notebook_draft_domain,
)
from aios_habit.workspace_chat_models import (
    DocumentNotebook,
    WorkspaceConversation,
)
from aios_habit.workspace_chat_store import (
    load_messages,
    save_conversation,
    save_notebook,
)

# Câu hỏi đặc thù chỉ có trong bản thảo MOM (mom/batch-01.md)
MOM_QUESTION = "Trong file cấu hình Matecon, ctrlMode = 0 và ctrlMode = 1 khác nhau thế nào?"

# Câu hỏi đặc thù chỉ có trong bản thảo LSU (lsu/batch-16.md)
LSU_QUESTION = "File chỉ ra thiếu chức năng gì để phát hiện sớm tình trạng jig suy giảm?"


# ==============================================================================
# 1. KIỂM THỬ ÁNH XẠ SỔ ĐANG MỞ -> MIỀN/KHO ĐÍCH (MỤC 2A)
# ==============================================================================

def test_resolve_notebook_draft_domain_known_notebooks():
    """Kiểm tra ánh xạ các sổ chuẩn của app sang miền bản thảo chính xác."""
    # Sổ MOM
    assert resolve_notebook_draft_domain("mom_opcenter") == "mom"
    assert resolve_notebook_draft_domain("mom") == "mom"

    # Sổ LSU
    assert resolve_notebook_draft_domain("NB-LAZY-LSU") == "lsu"
    assert resolve_notebook_draft_domain("lsu") == "lsu"

    # Sổ Điều tra lỗi / Điều chỉnh
    assert resolve_notebook_draft_domain("NB-LAZY-DTL") == "dieuchinh"
    assert resolve_notebook_draft_domain("dieu_tra_loi") == "dieuchinh"
    assert resolve_notebook_draft_domain("dieuchinh") == "dieuchinh"

    # Các sổ không có kho bản thảo riêng -> Phải trả về None (rơi đường trung thực)
    assert resolve_notebook_draft_domain("interstock_wms") is None
    assert resolve_notebook_draft_domain("email_jp_vn") is None
    assert resolve_notebook_draft_domain("aios_project") is None
    assert resolve_notebook_draft_domain("NB-67DB7EFE") is None

    # Mặc định an toàn: None hoặc rỗng -> None
    assert resolve_notebook_draft_domain("") is None
    assert resolve_notebook_draft_domain(None) is None
    assert resolve_notebook_draft_domain("random_unknown_notebook_xyz") is None


def test_resolve_notebook_draft_domain_custom_document_notebooks():
    """Kiểm tra ánh xạ đối tượng DocumentNotebook tự định nghĩa từ metadata."""
    # Sổ tự tạo có collection_id là lsu
    nb_lsu = DocumentNotebook(id="my_custom_lsu", title="Sổ đo quang học", collection_id="lsu")
    assert resolve_notebook_draft_domain(nb_lsu) == "lsu"

    # Sổ tự tạo có tiêu đề chứa từ khóa MOM
    nb_mom = DocumentNotebook(id="my_custom_mom", title="Sổ họp MOM Opcenter", collection_id="tri_thuc")
    assert resolve_notebook_draft_domain(nb_mom) == "mom"

    # Sổ tự tạo chung chung không liên quan kho bản thảo
    nb_generic = DocumentNotebook(id="my_custom_gen", title="Kế hoạch tuần", collection_id="tri_thuc")
    assert resolve_notebook_draft_domain(nb_generic) is None


# ==============================================================================
# 2. KIỂM THỬ BẪY XUYÊN SỔ TRÊN TẦNG NGUỒN BẢN THẢO (DRAFT SEARCH INDEX)
# ==============================================================================

def test_draft_search_index_cross_notebook_trap():
    """Kiểm tra tầng DraftSearchIndex: Khóa nguồn theo domain_filter, chống rò rỉ xuyên sổ."""
    reset_draft_search_index()
    index = get_draft_search_index()

    # --- Câu hỏi MOM ---
    # Dương tính: Tìm trong miền "mom" -> Khớp bản thảo MOM
    mom_hits, _ = index.search(MOM_QUESTION, top_k=2, domain_filter="mom")
    assert len(mom_hits) > 0
    assert mom_hits[0].item.domain == "mom"
    assert "mom" in mom_hits[0].item.source_file.replace("\\", "/").lower()

    # Bẫy xuyên sổ: Tìm câu hỏi MOM khi mở sổ "lsu" -> Phải trả về rỗng!
    lsu_trap_hits, _ = index.search(MOM_QUESTION, top_k=2, domain_filter="lsu")
    assert len(lsu_trap_hits) == 0, "BẪY XUYÊN SỔ THẤT BẠI: Câu hỏi MOM bị lọt vào sổ LSU!"

    # Bẫy xuyên sổ: Tìm câu hỏi MOM trong miền "dieuchinh" -> Rỗng
    dtl_trap_hits, _ = index.search(MOM_QUESTION, top_k=2, domain_filter="dieuchinh")
    assert len(dtl_trap_hits) == 0

    # Mặc định an toàn: Không truyền domain_filter và allow_unscoped=False -> Phải trả về rỗng
    unscoped_hits, _ = index.search(MOM_QUESTION, top_k=2)
    assert len(unscoped_hits) == 0, "Mặc định an toàn không được phục vụ bản thảo khi chưa rõ sổ!"

    # --- Câu hỏi LSU ---
    # Dương tính: Tìm trong miền "lsu" -> Khớp bản thảo LSU
    lsu_hits, _ = index.search(LSU_QUESTION, top_k=2, domain_filter="lsu")
    assert len(lsu_hits) > 0
    assert lsu_hits[0].item.domain == "lsu"
    assert "lsu" in lsu_hits[0].item.source_file.replace("\\", "/").lower()

    # Bẫy xuyên sổ: Tìm câu hỏi LSU khi mở sổ "mom" -> Phải trả về rỗng!
    mom_trap_hits, _ = index.search(LSU_QUESTION, top_k=2, domain_filter="mom")
    assert len(mom_trap_hits) == 0, "BẪY XUYÊN SỔ THẤT BẠI: Câu hỏi LSU bị lọt vào sổ MOM!"


# ==============================================================================
# 3. KIỂM THỬ TRÊN WORKSPACE CHAT AI ANSWER (RECALL DRAFT LAYER)
# ==============================================================================

def test_recall_draft_layer_cross_notebook_trap():
    """Kiểm tra recall_draft_layer_for_answer khóa theo sổ đang mở trong WorkspaceAIAnswerRequest."""
    from aios_habit.workspace_chat_ai_answer import (
        PRIVACY_MODE_CLOUD_ALLOWED,
        WorkspaceAIAnswerRequest,
        recall_draft_layer_for_answer,
    )

    # 1. Đối chứng dương: Hỏi câu MOM trong sổ MOM
    req_mom_positive = WorkspaceAIAnswerRequest(
        conversation_id="conv-mom-pos",
        question=MOM_QUESTION,
        context_sources=(),
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        notebook_id="mom_opcenter",
    )
    drafts_mom = recall_draft_layer_for_answer(req_mom_positive)
    assert len(drafts_mom) > 0
    assert drafts_mom[0].item.domain == "mom"

    # 2. Bẫy xuyên sổ: Hỏi câu MOM trong sổ LSU
    req_mom_in_lsu = WorkspaceAIAnswerRequest(
        conversation_id="conv-mom-in-lsu",
        question=MOM_QUESTION,
        context_sources=(),
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        notebook_id="NB-LAZY-LSU",
    )
    drafts_trap1 = recall_draft_layer_for_answer(req_mom_in_lsu)
    assert len(drafts_trap1) == 0, "LỖI: Sổ LSU đã lấy bản thảo của sổ MOM!"

    # 3. Đối chứng dương: Hỏi câu LSU trong sổ LSU
    req_lsu_positive = WorkspaceAIAnswerRequest(
        conversation_id="conv-lsu-pos",
        question=LSU_QUESTION,
        context_sources=(),
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        notebook_id="NB-LAZY-LSU",
    )
    drafts_lsu = recall_draft_layer_for_answer(req_lsu_positive)
    assert len(drafts_lsu) > 0
    assert drafts_lsu[0].item.domain == "lsu"

    # 4. Bẫy xuyên sổ: Hỏi câu LSU trong sổ MOM
    req_lsu_in_mom = WorkspaceAIAnswerRequest(
        conversation_id="conv-lsu-in-mom",
        question=LSU_QUESTION,
        context_sources=(),
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        notebook_id="mom_opcenter",
    )
    drafts_trap2 = recall_draft_layer_for_answer(req_lsu_in_mom)
    assert len(drafts_trap2) == 0, "LỖI: Sổ MOM đã lấy bản thảo của sổ LSU!"

    # 5. Các sổ không có bản thảo (InterStock, Email, AIOS)
    for nb in ["interstock_wms", "email_jp_vn", "aios_project", "NB-67DB7EFE", ""]:
        req_unrelated = WorkspaceAIAnswerRequest(
            conversation_id="conv-unrelated",
            question=MOM_QUESTION,
            context_sources=(),
            privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
            notebook_id=nb,
        )
        assert len(recall_draft_layer_for_answer(req_unrelated)) == 0


# ==============================================================================
# 4. KIỂM THỬ TRÊN RAG ANSWER COMPOSER (COMPOSE LOCAL ANSWER)
# ==============================================================================

def test_rag_answer_composer_cross_notebook_trap():
    """Kiểm tra compose_local_answer chỉ hòa trộn bản thảo đúng sổ đang mở."""
    from aios_habit.rag_evidence import RAGEvidencePack
    from aios_habit.rag_answer_composer import compose_local_answer

    # Pack rỗng đại diện cho trường hợp RAG không có dữ liệu chuẩn
    pack_mom = RAGEvidencePack(
        pack_id="PACK-MOM-TEST",
        query=MOM_QUESTION,
        items=[],
        metadata={"notebook_id": "mom_opcenter"},
    )

    pack_lsu = RAGEvidencePack(
        pack_id="PACK-LSU-TEST",
        query=MOM_QUESTION,  # Câu hỏi MOM nhưng pack gắn sổ LSU
        items=[],
        metadata={"notebook_id": "NB-LAZY-LSU"},
    )

    # Khi mở sổ MOM: Nhận được bản thảo MOM kèm nhãn
    ans_mom = compose_local_answer(pack_mom)
    assert MANDATORY_DRAFT_LABEL in ans_mom.answer_text
    assert "mom" in ans_mom.metadata.get("draft_source", "").replace("\\", "/").lower()

    # Khi mở sổ LSU: Không được lấy bản thảo MOM
    ans_lsu = compose_local_answer(pack_lsu)
    assert MANDATORY_DRAFT_LABEL not in ans_lsu.answer_text
    assert ans_lsu.metadata.get("has_draft_label") != "True"


# ==============================================================================
# 5. KIỂM THỬ TRÊN FINAL ANSWER COMPOSER (DELIVER 5-TIER LADDER ANSWER)
# ==============================================================================

def test_deliver_5tier_ladder_answer_cross_notebook_trap():
    """Kiểm tra deliver_5tier_ladder_answer: Không mượn bản thảo sổ khác khi RAG thiếu bằng chứng."""
    from aios_habit.final_answer_composer import deliver_5tier_ladder_answer

    conv_mom_pos = f"CONV-LADDER-MOM-POS-{uuid.uuid4().hex[:6]}"
    conv_lsu_trap = f"CONV-LADDER-LSU-TRAP-{uuid.uuid4().hex[:6]}"
    conv_lsu_pos = f"CONV-LADDER-LSU-POS-{uuid.uuid4().hex[:6]}"
    conv_mom_trap = f"CONV-LADDER-MOM-TRAP-{uuid.uuid4().hex[:6]}"

    # 1. Đối chứng dương: Hỏi câu MOM trong sổ MOM
    ok, msg, badge, err = deliver_5tier_ladder_answer(
        question=MOM_QUESTION,
        conversation_id=conv_mom_pos,
        notebook_id="mom_opcenter",
        user_raw_input=MOM_QUESTION,
    )
    assert ok is True
    assert badge is not None
    assert badge.get("has_draft_label") is True
    assert "mom" in badge.get("draft_source", "").replace("\\", "/").lower()

    msgs_mom = load_messages(conv_mom_pos)
    asst_mom = next(m for m in msgs_mom if m.role == "assistant")
    assert MANDATORY_DRAFT_LABEL in asst_mom.content

    # 2. BẪY XUYÊN SỔ: Hỏi câu MOM trong sổ LSU
    ok_trap, msg_trap, badge_trap, err_trap = deliver_5tier_ladder_answer(
        question=MOM_QUESTION,
        conversation_id=conv_lsu_trap,
        notebook_id="NB-LAZY-LSU",
        user_raw_input=MOM_QUESTION,
    )
    assert ok_trap is True
    assert badge_trap is not None
    # Không được có nhãn bản thảo và không được có draft_source từ MOM
    assert badge_trap.get("has_draft_label") is not True
    assert badge_trap.get("draft_source") == ""

    msgs_lsu = load_messages(conv_lsu_trap)
    asst_lsu = next(m for m in msgs_lsu if m.role == "assistant")
    assert MANDATORY_DRAFT_LABEL not in asst_lsu.content
    assert "mom/batch-01.md" not in asst_lsu.content
    assert "mom\\batch-01.md" not in asst_lsu.content
    # Phải rơi vào đường suy luận trung thực nguyên tắc chung
    assert "hệ thống chưa tìm thấy dữ liệu đối chiếu trực tiếp" in asst_lsu.content

    # 3. Đối chứng dương: Hỏi câu LSU trong sổ LSU
    ok_lsu, _, badge_lsu, _ = deliver_5tier_ladder_answer(
        question=LSU_QUESTION,
        conversation_id=conv_lsu_pos,
        notebook_id="NB-LAZY-LSU",
        user_raw_input=LSU_QUESTION,
    )
    assert ok_lsu is True
    assert badge_lsu.get("has_draft_label") is True
    assert "lsu" in badge_lsu.get("draft_source", "").replace("\\", "/").lower()

    # 4. BẪY XUYÊN SỔ: Hỏi câu LSU trong sổ MOM
    ok_mom_trap, _, badge_mom_trap, _ = deliver_5tier_ladder_answer(
        question=LSU_QUESTION,
        conversation_id=conv_mom_trap,
        notebook_id="mom_opcenter",
        user_raw_input=LSU_QUESTION,
    )
    assert ok_mom_trap is True
    assert badge_mom_trap.get("has_draft_label") is not True
    assert badge_mom_trap.get("draft_source") == ""


# ==============================================================================
# 6. KIỂM THỬ TRÊN ĐƯỜNG DỰ BỊ CŨ (ANSWER DRAFT FALLBACK)
# ==============================================================================

def test_answer_draft_fallback_cross_notebook_trap():
    """Kiểm tra đường dự bị cũ (answer_draft_fallback): search_drafts, resolve_answer, deliver_draft_answer."""
    from aios_habit.answer_draft_fallback import (
        DRAFT_LABEL,
        deliver_draft_answer,
        get_default_draft_entries,
        resolve_answer,
        search_drafts,
    )

    all_entries = get_default_draft_entries()
    assert len(all_entries) > 0

    # 1. Kiểm tra search_drafts với domain_filter
    mom_draft_hits = search_drafts(MOM_QUESTION, all_entries, domain_filter="mom")
    assert len(mom_draft_hits) > 0
    assert mom_draft_hits[0].domain == "mom"

    # Bẫy: Hỏi câu MOM với domain_filter="lsu"
    mom_in_lsu_hits = search_drafts(MOM_QUESTION, all_entries, domain_filter="lsu")
    assert len(mom_in_lsu_hits) == 0

    # LSU hits
    lsu_draft_hits = search_drafts(LSU_QUESTION, all_entries, domain_filter="lsu")
    assert len(lsu_draft_hits) > 0
    assert lsu_draft_hits[0].domain == "lsu"

    # Bẫy: Hỏi câu LSU với domain_filter="mom"
    lsu_in_mom_hits = search_drafts(LSU_QUESTION, all_entries, domain_filter="mom")
    assert len(lsu_in_mom_hits) == 0

    # 2. Kiểm tra resolve_answer với notebook_id
    dec_mom_pos = resolve_answer(
        MOM_QUESTION,
        rag_ok=False,
        draft_entries=all_entries,
        notebook_id="mom_opcenter",
        require_scope=True,
    )
    assert dec_mom_pos.lane == "draft_fallback"
    assert "mom" in dec_mom_pos.draft_source.replace("\\", "/").lower()

    # BẪY: Câu hỏi MOM trong sổ LSU
    dec_mom_in_lsu = resolve_answer(
        MOM_QUESTION,
        rag_ok=False,
        draft_entries=all_entries,
        notebook_id="NB-LAZY-LSU",
        require_scope=True,
    )
    assert dec_mom_in_lsu.lane == "not_found"
    assert "không tìm thấy" in dec_mom_in_lsu.answer_text.lower()
    assert dec_mom_in_lsu.has_draft_label is False

    # 3. Kiểm tra deliver_draft_answer
    conv_del_mom = f"CONV-DEL-MOM-{uuid.uuid4().hex[:6]}"
    conv_del_lsu_trap = f"CONV-DEL-LSU-TRAP-{uuid.uuid4().hex[:6]}"

    # Dương tính: Hỏi câu MOM trong sổ MOM -> Được giao bản thảo
    res_mom = deliver_draft_answer(
        MOM_QUESTION,
        conversation_id=conv_del_mom,
        notebook_id="mom_opcenter",
        user_raw_input=MOM_QUESTION,
    )
    assert res_mom is not None
    assert res_mom[0] is True
    assert res_mom[2] is not None
    assert res_mom[2]["is_draft_fallback"] is True
    assert "mom" in res_mom[2]["draft_source"].replace("\\", "/").lower()

    # BẪY XUYÊN SỔ: Hỏi câu MOM trong sổ LSU -> Phải trả về None (từ chối giao bản thảo)
    res_lsu_trap = deliver_draft_answer(
        MOM_QUESTION,
        conversation_id=conv_del_lsu_trap,
        notebook_id="NB-LAZY-LSU",
        user_raw_input=MOM_QUESTION,
    )
    assert res_lsu_trap is None, "BẪY XUYÊN SỔ THẤT BẠI: deliver_draft_answer không được trả lời bản thảo MOM trong sổ LSU!"

    # Hỏi câu MOM trong sổ không liên quan (interstock_wms) -> Phải trả về None
    res_unrelated = deliver_draft_answer(
        MOM_QUESTION,
        conversation_id=f"CONV-DEL-OTHER-{uuid.uuid4().hex[:6]}",
        notebook_id="interstock_wms",
        user_raw_input=MOM_QUESTION,
    )
    assert res_unrelated is None
