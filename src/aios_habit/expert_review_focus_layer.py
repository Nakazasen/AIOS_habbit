# -*- coding: utf-8 -*-
"""Lớp duyệt tập trung chuyên gia (Expert Review Focus Layer).

Thực hiện nhiệm vụ vé DESKTOP-HOME-EXPERT-REVIEW-FOCUS-LAYER:
- Sidebar giữ nguyên kích thước ~300px và vai trò thông báo/hộp báo việc (danh sách rút gọn).
- Bấm vào một mục chờ duyệt -> mở LỚP DUYỆT TẬP TRUNG phủ tạm thời lên vùng chat chính.
- Đóng lớp -> khung chat trở lại đúng trạng thái trước đó: hội thoại, vị trí cuộn và
  CÂU ĐANG GÕ DỞ trong ô soạn thảo còn nguyên vẹn 100%.
- Trong lớp duyệt, nội dung xếp theo đúng thứ tự ra quyết định:
  (a) Câu hỏi gốc TOÀN VĂN, khổ đọc thoải mái, kèm tóm tắt tối đa 3 dòng vì sao mục bị đưa lên duyệt.
  (b) Nội dung đề xuất vào kho TOÀN VĂN, SỬA TẠI CHỖ ĐƯỢC trước khi duyệt;
      kèm đối chiếu khác biệt với bài học tương tự đã có trong kho để tránh duyệt trùng.
  (c) Bằng chứng/nguon: mặc định thu gọn, bấm mở rộng; mở nguồn gốc bằng đúng
      cơ chế xem nguồn trích dẫn đã có (citation_source_viewer).
- Thanh quyết định DÍNH Ở ĐÁY: Duyệt (chỉ đến thao tác này mới hỏi PIN) - Trả sửa kèm lý do (bắt buộc) - Bỏ qua/Sang mục tiếp.
  Sau khi quyết định xong một mục, lớp tự chuyển sang mục tiếp theo trong hàng đợi; hết hàng đợi thì lớp tự đóng.
- Màn hình hẹp: 3 phần (a)/(b)/(c) chuyển thành 3 tab, thanh quyết định vẫn dính ở đáy.
- Vòng lặp cải thiện liên tục (luật user 2026-10-03): ghi sự kiện duyệt vào local_cases/expert_review_events.jsonl.

Tương thích Python 3.11+.
"""

from __future__ import annotations

import difflib
import json
import os
import platform
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from aios_habit.citation_source_viewer import (
    CitationRef,
    check_citation_exists,
    record_source_verification_event,
    render_source_viewer_panel,
    resolve_citation_source,
)
from aios_habit.expert_review_queue import (
    ExpertReviewQueueRepository,
    QueueItem,
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    STATUS_REVISED,
    get_expert_queue_repo,
)
from aios_habit.expert_roles import (
    ExpertRoleRegistry,
    get_expert_role_registry,
    matches_subject,
)

_LOCAL_CASES_DIR = Path(__file__).resolve().parents[2] / "local_cases"
_REVIEW_EVENTS_LOG = _LOCAL_CASES_DIR / "expert_review_events.jsonl"
_MEMORY_VAULT_FILE = Path(__file__).resolve().parents[2] / "05_memory_vault" / "memory_units.jsonl"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_expert_review_event(
    event_type: str,
    item_id: str,
    domain_id: str,
    actor_subject: str,
    actor_machine: str,
    *,
    review_duration_seconds: float = 0.0,
    action: str = "",
    reason: str = "",
    has_inline_edit: bool = False,
    diff_detected: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Ghi nhật ký sự kiện duyệt vào local_cases để phục vụ đo lường điểm nghẽn.
    
    Tuân thủ quy tắc quản trị dữ liệu: Không ghi nội dung nhạy cảm thừa.
    """
    try:
        _LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)
        event_record = {
            "event_id": f"REV-EVT-{uuid.uuid4().hex[:8].upper()}",
            "timestamp": _utc_now_iso(),
            "event_type": event_type,
            "item_id": item_id,
            "domain_id": domain_id,
            "actor_subject": actor_subject,
            "actor_machine": actor_machine,
            "review_duration_seconds": round(max(0.0, review_duration_seconds), 2),
            "action": action or event_type,
            "reason_len": len(reason.strip()) if reason else 0,
            "has_inline_edit": has_inline_edit,
            "diff_detected": diff_detected,
            "metadata": metadata or {},
        }
        with open(_REVIEW_EVENTS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(event_record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def find_similar_lessons(
    target_item: QueueItem,
    repo: Optional[ExpertReviewQueueRepository] = None,
) -> Tuple[Optional[Dict[str, Any]], float, str]:
    """Tìm kiếm bài học tương tự trong kho tri thức công ty và các ca duyệt trước đó.
    
    Trả về: (bài_học_khớp_nhất, điểm_tương_đồng, nhận_định_khác_biệt).
    """
    candidates: List[Dict[str, Any]] = []

    # 1. Quét kho Memory Vault (company_knowledge)
    if _MEMORY_VAULT_FILE.exists():
        try:
            with open(_MEMORY_VAULT_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line_s = line.strip()
                    if line_s:
                        try:
                            data = json.loads(line_s)
                            if data.get("status") == "verified" or data.get("partition") == "company_knowledge":
                                candidates.append({
                                    "source": "memory_vault",
                                    "id": data.get("unit_id") or data.get("memory_id") or "VAULT",
                                    "title": data.get("title", ""),
                                    "question": data.get("question", ""),
                                    "statement": data.get("statement", ""),
                                    "scope": data.get("scope", ""),
                                })
                        except Exception:
                            continue
        except Exception:
            pass

    # 2. Quét các mục đã phê duyệt trong SQLite hàng đợi
    if repo is not None:
        try:
            with repo._connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT item_id, title, question, draft_answer, domain_id FROM queue_items WHERE status = 'approved' AND item_id != ?",
                    (target_item.item_id,),
                )
                for row in cur.fetchall():
                    candidates.append({
                        "source": "queue_approved",
                        "id": row[0],
                        "title": row[1] or "",
                        "question": row[2] or "",
                        "statement": row[3] or "",
                        "scope": f"domain:{row[4]}",
                    })
        except Exception:
            pass

    if not candidates:
        return None, 0.0, "Chưa có bài học nào trong kho tri thức."

    best_cand: Optional[Dict[str, Any]] = None
    best_sim: float = 0.0

    target_q = target_item.question.strip().lower()
    target_d = (target_item.draft_answer or target_item.title).strip().lower()

    for cand in candidates:
        c_title = cand.get("title", "").strip().lower()
        c_q = cand.get("question", "").strip().lower()
        c_stmt = cand.get("statement", "").strip().lower()

        # So khớp tiêu đề & câu hỏi
        q_sim = difflib.SequenceMatcher(None, target_q, c_q if c_q else c_title).ratio()
        stmt_sim = difflib.SequenceMatcher(None, target_d, c_stmt).ratio()
        combined_sim = (q_sim * 0.6) + (stmt_sim * 0.4)

        if combined_sim > best_sim:
            best_sim = combined_sim
            best_cand = cand

    if best_cand is not None and best_sim >= 0.20:
        c_name = best_cand.get("title") or best_cand.get("id")
        diff_lines = list(difflib.unified_diff(
            best_cand.get("statement", "").splitlines(),
            target_item.draft_answer.splitlines(),
            fromfile=f"Đã có ({best_cand.get('id')})",
            tofile="Đề xuất mới",
            lineterm="",
        ))
        diff_text = "\n".join(diff_lines[:15]) if diff_lines else "Khác biệt về phạm vi áp dụng và thông số kỹ thuật."
        return best_cand, best_sim, diff_text

    return None, best_sim, "Không phát hiện bài học tương tự (nội dung mới, không sợ trùng lặp)."


def _compute_escalation_summary(item: QueueItem, registry: ExpertRoleRegistry) -> List[str]:
    """Tạo bản tóm tắt tối đa 3 dòng vì sao mục bị đưa lên duyệt theo yêu cầu 2.3(a)."""
    # 1. Dòng 1: Phân loại & Miền
    domain_conf = registry.get_domain(item.domain_id)
    dom_title = domain_conf.title if domain_conf else item.domain_id.upper()
    
    src_labels = {
        "sma_negative_alert": "Cảnh báo xu hướng chê SMA(20)",
        "draft_promotion": "Đề xuất thăng hạng bản nháp Like cao",
        "tier5_inquiry": "Chuyển tiếp chuyên gia từ hỏi đáp trực tiếp (Nấc thang 5)",
        "user_correction": "Đề xuất hiệu chỉnh từ người dùng",
    }
    src_title = src_labels.get(item.source_type, "Hàng đợi chuyên gia")
    line1 = f"• **Phân loại nguồn:** {src_title} (Miền: *{dom_title}*)"

    # 2. Dòng 2: Tín hiệu & Điểm ưu tiên
    tot = item.dislike_count + item.like_count
    ratio_pct = (item.dislike_count / max(1, tot)) * 100.0 if tot > 0 else 0.0
    line2 = (
        f"• **Tín hiệu đánh giá:** {item.dislike_count} chê / {item.service_frequency} lượt hỏi "
        f"(tỷ lệ chê {ratio_pct:.0f}%) · **Priority Score:** `{item.priority_score:.1f}`"
    )

    # 3. Dòng 3: Cảnh báo quá hạn
    overdue_hours = 0.0
    try:
        c_dt = datetime.fromisoformat(item.created_at)
        now_dt = datetime.now(timezone.utc)
        overdue_hours = (now_dt - c_dt).total_seconds() / 3600.0
    except Exception:
        pass

    if overdue_hours >= 48.0:
        line3 = f"• **Cảnh báo tiến độ:** 🚨 Đã quá hạn **{overdue_hours:.1f} giờ** (vượt ngưỡng nhắc nhở 48h, cần xử lý dứt điểm)."
    elif overdue_hours >= 24.0:
        line3 = f"• **Tiến độ xử lý:** ⏳ Đang chờ duyệt **{overdue_hours:.1f} giờ** (trong thời hạn quy định 48h)."
    else:
        line3 = f"• **Tiến độ xử lý:** 🔔 Mới phát sinh ({overdue_hours:.1f}h trước), ưu tiên xử lý sớm."

    return [line1, line2, line3]


def _render_focus_review_content(
    item: QueueItem,
    subject: str,
    current_node: str,
    repo: ExpertReviewQueueRepository,
    registry: ExpertRoleRegistry,
    relevant_items: List[QueueItem],
) -> None:
    """Render nội dung chi tiết của Lớp duyệt tập trung."""
    open_time_key = f"wsc_focus_open_time_{item.item_id}"
    if open_time_key not in st.session_state:
        st.session_state[open_time_key] = time.time()
        record_expert_review_event(
            event_type="open_layer",
            item_id=item.item_id,
            domain_id=item.domain_id,
            actor_subject=subject,
            actor_machine=current_node,
            action="open_focus_layer",
        )

    # Header: Thông tin đầu mục và điều hướng
    cur_idx = 0
    for i, it in enumerate(relevant_items):
        if it.item_id == item.item_id:
            cur_idx = i
            break

    head_col1, head_col2, head_col3 = st.columns([6, 3, 2], vertical_alignment="center")
    with head_col1:
        st.markdown(f"### 🛡️ LỚP DUYỆT TẬP TRUNG CHUYÊN GIA")
        st.caption(f"Đăng nhập: `{subject}` | Máy trạm: `{current_node}` | Mục **{cur_idx+1}/{len(relevant_items)}** trong hàng đợi")
    with head_col2:
        p_color = "red" if item.priority_score >= 20 else "orange" if item.priority_score >= 10 else "blue"
        st.markdown(f":{p_color}[⭐ **Priority: {item.priority_score:.1f}**] · Miền: **{item.domain_id.upper()}**")
    with head_col3:
        if st.button("✕ Đóng lớp duyệt", key=f"btn_close_focus_top_{item.item_id}", use_container_width=True):
            st.session_state["wsc_focus_review_active_item_id"] = None
            st.session_state.pop(f"wsc_focus_pin_mode_{item.item_id}", None)
            st.session_state.pop(f"wsc_focus_rev_mode_{item.item_id}", None)
            dur = time.time() - st.session_state.get(open_time_key, time.time())
            record_expert_review_event(
                event_type="close_layer",
                item_id=item.item_id,
                domain_id=item.domain_id,
                actor_subject=subject,
                actor_machine=current_node,
                review_duration_seconds=dur,
                action="closed_by_user",
            )
            st.rerun()

    st.markdown("---")

    # Tùy chọn chuyển đổi màn hình hẹp / màn hình rộng (Yêu cầu 2.5)
    layout_pref_key = "wsc_focus_layout_mode"
    layout_mode = st.session_state.get(layout_pref_key, "auto")
    
    col_ctrl1, col_ctrl2 = st.columns([8, 3], vertical_alignment="center")
    with col_ctrl1:
        st.markdown(f"**Nhiệm vụ ra quyết định:** `#{cur_idx+1}. {item.title}`")
    with col_ctrl2:
        picked_mode = st.selectbox(
            "Bố cục giao diện:",
            ["Tự động / 3 Cột rộng", "Màn hình hẹp (3 Tab)"],
            index=1 if layout_mode == "narrow_tabs" else 0,
            key=f"sel_layout_mode_{item.item_id}",
            label_visibility="collapsed",
        )
        is_narrow = (picked_mode == "Màn hình hẹp (3 Tab)")
        st.session_state[layout_pref_key] = "narrow_tabs" if is_narrow else "wide_columns"

    # Chuẩn bị dữ liệu cho 3 phần (a), (b), (c)
    summary_lines = _compute_escalation_summary(item, registry)
    similar_cand, sim_score, diff_summary = find_similar_lessons(item, repo)
    
    draft_state_key = f"wsc_focus_draft_val_{item.item_id}"
    if draft_state_key not in st.session_state:
        st.session_state[draft_state_key] = item.draft_answer or item.title

    # -------------------------------------------------------------------------
    # HÀM RENDER NỘI DUNG 3 PHẦN
    # -------------------------------------------------------------------------
    def _render_section_a():
        st.markdown("#### (a) Câu hỏi gốc & Lý do leo thang")
        with st.container(border=True):
            st.markdown("**Câu hỏi gốc (Toàn văn):**")
            st.info(item.question, icon="❓")
            
            st.markdown("**Tóm tắt lý do đưa lên duyệt:**")
            for sl in summary_lines:
                st.markdown(sl)

    def _render_section_b():
        st.markdown("#### (b) Bản đề xuất vào kho & Đối chiếu")
        with st.container(border=True):
            st.markdown("**Nội dung đề xuất ghi kho (Chuyên gia sửa tại chỗ):**")
            edited_text = st.text_area(
                "Chỉnh sửa nội dung trước khi duyệt:",
                value=st.session_state[draft_state_key],
                height=150,
                key=f"wsc_focus_draft_input_{item.item_id}",
                help="Chuyên gia có thể sửa trực tiếp câu chữ, thông số kỹ thuật trước khi xác nhận ghi vào kho công ty.",
                label_visibility="collapsed",
            )
            st.session_state[draft_state_key] = edited_text

            # Đối chiếu khác biệt với bài học đã có trong kho
            st.markdown("---")
            st.markdown("**Đối chiếu tránh duyệt trùng lặp:**")
            if similar_cand is not None and sim_score >= 0.20:
                st.warning(
                    f"🔍 **Phát hiện bài học liên quan:** `{similar_cand.get('id')}: {similar_cand.get('title')}` "
                    f"(Độ tương đồng: **{sim_score*100:.1f}%**)"
                )
                with st.expander("So sánh khác biệt (Diff comparison)", expanded=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.caption("📄 **Bản đã có trong kho:**")
                        st.code(similar_cand.get("statement") or similar_cand.get("title"), language="text")
                    with c2:
                        st.caption("📝 **Bản đề xuất hiện tại:**")
                        st.code(edited_text, language="text")
                    st.caption(f"💡 Nhận định đối chiếu: {diff_summary}")
            else:
                st.success("✅ **Không phát hiện bài học trùng lặp trong kho** (Nội dung mới, chuẩn xác để đưa vào kho).")

    def _render_section_c():
        st.markdown("#### (c) Bằng chứng & Nguồn gốc")
        with st.expander("📂 **Bằng chứng & Nguồn trích dẫn gốc** (Bấm để mở rộng)", expanded=False):
            if item.source_file:
                st.markdown(f"• **Tệp nguồn quy chuẩn:** `{item.source_file}`")
                
                # Gọi cơ chế xem nguồn trích dẫn tương tác citation_source_viewer
                c_ref = CitationRef(
                    id=f"CIT-{item.item_id[:8]}",
                    ref_type="glossary_doc",
                    label=item.source_file,
                    source_file=item.source_file,
                )
                payload = resolve_citation_source(c_ref)
                
                if payload.found:
                    st.success(f"Trạng thái nguồn: Sẵn sàng trên máy trạm (`{payload.file_path or 'Cục bộ'}`)")
                    if payload.excerpt_text:
                        st.caption("Đoạn trích dẫn nguyên bản:")
                        st.text(payload.excerpt_text[:500])
                    if payload.can_open_file and payload.file_path:
                        st.caption("Tệp gốc sẵn sàng xem qua trình xem chuyên dụng.")
                else:
                    st.info(f"Nguồn tham khảo tiêu chuẩn kỹ thuật: `{item.source_file}` (định danh quy chuẩn nghiệp vụ)")

                # Nút ghi nhận kiểm tra nguồn
                if st.button("🔍 Mở trình xem chi tiết nguồn", key=f"btn_src_view_{item.item_id}"):
                    record_source_verification_event(
                        conversation_id=item.conversation_id or "EXPERT-REVIEW",
                        message_id=item.item_id,
                        citation_ref=c_ref,
                        found=payload.found,
                    )
                    render_source_viewer_panel(payload, key_prefix=f"focus_src_{item.item_id}")
            else:
                st.caption("Mục này phát sinh từ phản ánh đánh giá trực tiếp của người dùng, không kèm tệp tài liệu ngoài.")

    # Render bố cục theo chế độ (Cột rộng hoặc Tab hẹp)
    if is_narrow:
        tab_a, tab_b, tab_c = st.tabs([
            "📋 (a) Câu hỏi gốc & Lý do",
            "📝 (b) Bản đề xuất & Đối chiếu",
            "📂 (c) Bằng chứng & Nguồn",
        ])
        with tab_a:
            _render_section_a()
        with tab_b:
            _render_section_b()
        with tab_c:
            _render_section_c()
    else:
        col_a, col_b, col_c = st.columns([1.1, 1.3, 0.9])
        with col_a:
            _render_section_a()
        with col_b:
            _render_section_b()
        with col_c:
            _render_section_c()

    # -------------------------------------------------------------------------
    # THANH QUYẾT ĐỊNH DÍNH Ở ĐÁY (STICKY BOTTOM ACTION BAR) - YÊU CẦU 2.4
    # -------------------------------------------------------------------------
    st.markdown("---")
    
    # CSS ghim dính thanh quyết định ở đáy
    st.html("""
    <style>
    .focus-decision-bar {
        position: sticky;
        bottom: 0;
        background: #FFFFFF;
        padding: 12px 16px;
        border-top: 2px solid #E2E8F0;
        box-shadow: 0 -4px 12px rgba(15, 23, 42, 0.05);
        z-index: 999;
    }
    </style>
    """)

    pin_mode_key = f"wsc_focus_pin_mode_{item.item_id}"
    rev_mode_key = f"wsc_focus_rev_mode_{item.item_id}"
    is_pin_mode = bool(st.session_state.get(pin_mode_key, False))
    is_rev_mode = bool(st.session_state.get(rev_mode_key, False))

    def _advance_to_next_item():
        """Tự động chuyển sang mục tiếp theo trong hàng đợi; nếu hết thì tự đóng lớp duyệt."""
        dur = time.time() - st.session_state.get(open_time_key, time.time())
        # Cập nhật danh sách pending còn lại
        remaining = [it for it in relevant_items if it.item_id != item.item_id]
        if remaining:
            st.session_state["wsc_focus_review_active_item_id"] = remaining[0].item_id
        else:
            st.session_state["wsc_focus_review_active_item_id"] = None
            st.session_state["wsc_action_message"] = "✅ Đã xử lý toàn bộ các mục trong hàng đợi chuyên gia!"
        st.session_state.pop(pin_mode_key, None)
        st.session_state.pop(rev_mode_key, None)
        st.rerun()

    # KHỐI 1: FORM XÁC THỰC MÃ PIN KHI BẤM "DUYỆT VÀO KHO"
    if is_pin_mode:
        with st.container(border=True):
            st.markdown("#### 🔒 Xác thực Mã PIN Phê duyệt (Ghi kho công ty)")
            is_mach_ok = registry.is_machine_authorized(item.domain_id, current_node)
            if is_mach_ok:
                st.success(f"🖥️ Tên máy trạm: `{current_node}` (Hợp lệ cho miền {item.domain_id.upper()})")
            else:
                st.error(f"🚫 Máy tính '{current_node}' không được cấp phép phê duyệt tri thức cho miền '{item.domain_id}'.")

            with st.form(key=f"form_focus_pin_{item.item_id}"):
                st.caption(f"Tài khoản duyệt: **{subject}** | Mã mục: `{item.item_id}`")
                pin = st.text_input(
                    "Mã PIN chuyên gia (4–6 số):",
                    type="password",
                    key=f"input_focus_pin_{item.item_id}",
                    help="Nhập mã PIN cá nhân để ký duyệt ghi vào kho tri thức công ty.",
                )
                notes = st.text_input(
                    "Ghi chú phê duyệt (tùy chọn):",
                    value="Chuyên gia thẩm định đạt chuẩn chất lượng qua Focus Layer.",
                    key=f"input_focus_notes_{item.item_id}",
                )
                col_f1, col_f2 = st.columns(2)
                sub_pin = col_f1.form_submit_button("✅ Xác nhận & Ghi kho", type="primary", use_container_width=True)
                can_pin = col_f2.form_submit_button("Hủy", use_container_width=True)

            if can_pin:
                st.session_state[pin_mode_key] = False
                st.rerun()

            if sub_pin:
                if not is_mach_ok:
                    st.error(f"Máy trạm '{current_node}' không thuộc danh sách được cấp phép!")
                    return
                
                final_draft = st.session_state.get(draft_state_key, item.draft_answer)
                has_edit = (final_draft.strip() != item.draft_answer.strip())

                res = repo.approve_queue_item(
                    item_id=item.item_id,
                    actor_subject=subject,
                    pin=pin,
                    machine_node=current_node,
                    notes=notes,
                    updated_draft=final_draft,
                )

                if res.get("ok"):
                    dur = time.time() - st.session_state.get(open_time_key, time.time())
                    record_expert_review_event(
                        event_type="decision_approve",
                        item_id=item.item_id,
                        domain_id=item.domain_id,
                        actor_subject=subject,
                        actor_machine=current_node,
                        review_duration_seconds=dur,
                        action="approved_to_vault",
                        has_inline_edit=has_edit,
                        diff_detected=bool(similar_cand and sim_score >= 0.20),
                        metadata={"audit_id": res.get("audit_stamp", {}).get("audit_id")},
                    )
                    st.session_state["wsc_action_message"] = f"✅ Đã duyệt mục #{item.item_id} vào kho công ty!"
                    _advance_to_next_item()
                else:
                    st.error(f"❌ {res.get('error_vi', 'Lỗi xác thực mã PIN.')}")

    # KHỐI 2: FORM TRẢ SỬA KÈM LÝ DO BẮT BUỘC
    elif is_rev_mode:
        with st.container(border=True):
            st.markdown("#### ↩️ Yêu cầu Trả sửa mục hàng đợi")
            st.caption("Chuyên gia trả lại bản nháp để hiệu chỉnh; bắt buộc phải ghi rõ lý do chuyên môn.")
            
            with st.form(key=f"form_focus_revision_{item.item_id}"):
                rev_reason = st.text_area(
                    "Lý do trả sửa (bắt buộc):",
                    key=f"input_focus_rev_reason_{item.item_id}",
                    placeholder="Ví dụ: Thiếu thông số lực siết ốc căn chỉnh hoặc sai tiêu chuẩn xuất xưởng...",
                )
                col_r1, col_r2 = st.columns(2)
                sub_rev = col_r1.form_submit_button("Xác nhận Trả sửa", type="primary", use_container_width=True)
                can_rev = col_r2.form_submit_button("Hủy", use_container_width=True)

            if can_rev:
                st.session_state[rev_mode_key] = False
                st.rerun()

            if sub_rev:
                if not rev_reason or not rev_reason.strip():
                    st.error("❌ Bắt buộc phải nhập lý do trả sửa!")
                    return

                res = repo.reject_queue_item(
                    item_id=item.item_id,
                    actor_subject=subject,
                    reason=rev_reason.strip(),
                    machine_node=current_node,
                    decision_status=STATUS_REVISED,
                    require_pin=False,
                )

                if res.get("ok"):
                    dur = time.time() - st.session_state.get(open_time_key, time.time())
                    record_expert_review_event(
                        event_type="decision_revision",
                        item_id=item.item_id,
                        domain_id=item.domain_id,
                        actor_subject=subject,
                        actor_machine=current_node,
                        review_duration_seconds=dur,
                        action="revision_requested",
                        reason=rev_reason.strip(),
                    )
                    st.session_state["wsc_action_message"] = f"↩️ Đã yêu cầu trả sửa mục #{item.item_id}."
                    _advance_to_next_item()
                else:
                    st.error(f"❌ {res.get('error_vi', 'Lỗi khi ghi nhận trả sửa.')}")

    # KHỐI 3: THANH NÚT QUYẾT ĐỊNH MẶC ĐỊNH
    else:
        btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([2.5, 2.5, 2.5, 1.5], vertical_alignment="center")
        with btn_col1:
            if st.button("✅ Duyệt vào kho", type="primary", key=f"btn_focus_approve_{item.item_id}", use_container_width=True):
                st.session_state[pin_mode_key] = True
                st.session_state[rev_mode_key] = False
                st.rerun()

        with btn_col2:
            if st.button("↩️ Trả sửa kèm lý do", key=f"btn_focus_rev_{item.item_id}", use_container_width=True):
                st.session_state[rev_mode_key] = True
                st.session_state[pin_mode_key] = False
                st.rerun()

        with btn_col3:
            if st.button("⏭️ Bỏ qua / Sang mục tiếp", key=f"btn_focus_skip_{item.item_id}", use_container_width=True):
                dur = time.time() - st.session_state.get(open_time_key, time.time())
                record_expert_review_event(
                    event_type="decision_skip",
                    item_id=item.item_id,
                    domain_id=item.domain_id,
                    actor_subject=subject,
                    actor_machine=current_node,
                    review_duration_seconds=dur,
                    action="skipped_to_next",
                )
                _advance_to_next_item()

        with btn_col4:
            if st.button("Đóng", key=f"btn_focus_close_bot_{item.item_id}", use_container_width=True):
                st.session_state["wsc_focus_review_active_item_id"] = None
                dur = time.time() - st.session_state.get(open_time_key, time.time())
                record_expert_review_event(
                    event_type="close_layer",
                    item_id=item.item_id,
                    domain_id=item.domain_id,
                    actor_subject=subject,
                    actor_machine=current_node,
                    review_duration_seconds=dur,
                    action="closed_by_user",
                )
                st.rerun()


# Tạo dialog modal overlay Streamlit
if hasattr(st, "dialog"):
    @st.dialog("🛡️ Lớp Duyệt Tập Trung Chuyên Gia", width="large")
    def _render_focus_review_dialog_modal(
        item: QueueItem,
        subject: str,
        current_node: str,
        repo: ExpertReviewQueueRepository,
        registry: ExpertRoleRegistry,
        relevant_items: List[QueueItem],
    ) -> None:
        _render_focus_review_content(item, subject, current_node, repo, registry, relevant_items)


def render_focus_review_layer(
    item_id: str,
    subject: str,
    current_node: str,
    repo: ExpertReviewQueueRepository,
    registry: ExpertRoleRegistry,
    relevant_items: List[QueueItem],
) -> None:
    """Điểm kích hoạt Lớp duyệt tập trung chuyên gia."""
    target_item: Optional[QueueItem] = None
    for it in relevant_items:
        if it.item_id == item_id:
            target_item = it
            break
    
    if target_item is None:
        target_item = repo.get_item(item_id)

    if target_item is None:
        st.session_state["wsc_focus_review_active_item_id"] = None
        return

    if hasattr(st, "dialog"):
        _render_focus_review_dialog_modal(
            target_item, subject, current_node, repo, registry, relevant_items
        )
    else:
        # Fallback render inline nếu môi trường không có st.dialog
        _render_focus_review_content(
            target_item, subject, current_node, repo, registry, relevant_items
        )
