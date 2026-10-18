"""Giao diện người dùng trong khung chat (UI glue) cho bộ máy thu tri thức.

Cung cấp:
- Quản lý phiên trong bộ nhớ chat (`LiveIntakeStore`).
- HTML comment markers để nhúng widget tương tác vào markdown của tin nhắn assistant:
  `aios_intake_session` và `aios_intake_review`.
- Render widget phiên hỏi-đáp từng câu ngay trong chat.
- Render widget duyệt tại chỗ 3 nút (Đúng / Sửa / Loại) chuyển trạng thái CHO NẠP.
- Render widget bề mặt xem lại và metric cải thiện 3 điểm.
- Hỗ trợ FakeSt cho 100% kiểm thử tự động không cần khởi động Streamlit server.

Tương thích Python 3.11: không dùng f-string nhiều dòng (PEP 701), không type statement.
"""

from __future__ import annotations

import json
import re
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

from aios_habit.intake_metrics import format_review_surface_markdown
from aios_habit.intake_staging import (
    INGEST_CHO_NAP,
    STATUS_CHO_DUYET,
    STATUS_DA_SUA,
    STATUS_DUNG,
    STATUS_LOAI,
    IntakeDraftItemRecord,
    IntakeStagingStore,
)
from aios_habit.knowledge_intake_engine import (
    KnowledgeIntakeEngine,
    KnowledgeIntakeSession,
)

# Marker tags nhúng trong markdown
_INTAKE_SESSION_TAG = "aios_intake_session"
_INTAKE_REVIEW_TAG = "aios_intake_review"

_INTAKE_SESSION_RE = re.compile(
    r"<!--\s*aios_intake_session\s*:\s*(\{.*?\})\s*-->", re.DOTALL
)
_INTAKE_REVIEW_RE = re.compile(
    r"<!--\s*aios_intake_review\s*:\s*(\{.*?\})\s*-->", re.DOTALL
)


def intake_session_marker(session_id: str, store_id: str) -> str:
    """Tạo marker HTML comment để mở widget hỏi-đáp của phiên thu tri thức."""
    payload = {"session_id": str(session_id), "store_id": str(store_id)}
    return "<!-- %s: %s -->" % (_INTAKE_SESSION_TAG, json.dumps(payload, ensure_ascii=False))


def intake_review_marker(session_id: str, store_id: str) -> str:
    """Tạo marker HTML comment để mở widget duyệt nháp tại chỗ."""
    payload = {"session_id": str(session_id), "store_id": str(store_id)}
    return "<!-- %s: %s -->" % (_INTAKE_REVIEW_TAG, json.dumps(payload, ensure_ascii=False))


def extract_intake_session_marker(content: str) -> Optional[Dict[str, str]]:
    """Trích xuất thông tin session_id và store_id từ marker session."""
    match = _INTAKE_SESSION_RE.search(str(content or ""))
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
        return {
            "session_id": str(data.get("session_id", "")).strip(),
            "store_id": str(data.get("store_id", "")).strip(),
        }
    except Exception:
        return None


def extract_intake_review_marker(content: str) -> Optional[Dict[str, str]]:
    """Trích xuất thông tin session_id và store_id từ marker review."""
    match = _INTAKE_REVIEW_RE.search(str(content or ""))
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
        return {
            "session_id": str(data.get("session_id", "")).strip(),
            "store_id": str(data.get("store_id", "")).strip(),
        }
    except Exception:
        return None


def strip_intake_markers(content: str) -> str:
    """Xóa các marker của intake trước khi hiển thị văn bản markdown."""
    text = _INTAKE_SESSION_RE.sub("", str(content or ""))
    text = _INTAKE_REVIEW_RE.sub("", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Quản lý phiên trực tiếp trong bộ nhớ ứng dụng Chat
# ---------------------------------------------------------------------------


class LiveIntakeStore:
    """Kho lưu trữ các phiên thu tri thức đang hoạt động trong bộ nhớ."""

    def __init__(self, capacity: int = 30) -> None:
        self._capacity = max(1, int(capacity))
        self._sessions: "OrderedDict[str, KnowledgeIntakeSession]" = OrderedDict()

    def put(self, session: KnowledgeIntakeSession) -> None:
        sid = str(session.session_id or "").strip()
        if not sid:
            raise ValueError("Phiên thu tri thức thiếu session_id.")
        self._sessions.pop(sid, None)
        self._sessions[sid] = session
        while len(self._sessions) > self._capacity:
            self._sessions.popitem(last=False)

    def get(self, session_id: str) -> Optional[KnowledgeIntakeSession]:
        return self._sessions.get(str(session_id or "").strip())

    def drop(self, session_id: str) -> None:
        self._sessions.pop(str(session_id or "").strip(), None)

    def clear(self) -> None:
        self._sessions.clear()


_LIVE_STORE = LiveIntakeStore()


def register_live_session(session: KnowledgeIntakeSession) -> None:
    _LIVE_STORE.put(session)


def get_live_session(session_id: str) -> Optional[KnowledgeIntakeSession]:
    return _LIVE_STORE.get(session_id)


def clear_live_sessions() -> None:
    _LIVE_STORE.clear()


# ---------------------------------------------------------------------------
# Streamlit Widget Renders
# ---------------------------------------------------------------------------


def render_intake_session_widget(
    st: Any, session_id: str, staging_store: Optional[IntakeStagingStore] = None
) -> None:
    """Vẽ widget hỏi-đáp từng câu ngay trong bubble chat của phiên thu tri thức."""
    session = get_live_session(session_id)
    store = staging_store or IntakeStagingStore()

    if session is None:
        st.info("Phiên thu tri thức %s không còn trong bộ nhớ tạm." % session_id)
        return

    if session.is_completed:
        st.success(
            "✅ Phiên thu tri thức **%s** đã hoàn thành. Vui lòng duyệt các mục nháp bên dưới."
            % session_id
        )
        render_intake_review_widget(st, session_id, staging_store=store)
        return

    # Lấy câu hỏi hiện tại
    current_turn = session.turns[-1] if session.turns else None
    if not current_turn:
        st.warning("Phiên chưa có câu hỏi nào.")
        return

    st.markdown("---")
    st.markdown("#### 🎙️ Đang trong phiên: %s (Kho đích: **%s**)" % (session.topic, session.store_id))
    st.markdown(
        "**Câu hỏi hiện tại (%s):** %s"
        % (current_turn.probe_type, current_turn.question_text)
    )

    key_base = "intake_q_%s_%d" % (
        re.sub(r"\W+", "_", session_id), current_turn.turn_index
    )
    answer_val = st.text_area(
        "Nội dung trả lời của bạn / chuyên gia:",
        key=key_base + "_ans",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📤 Gửi câu trả lời", key=key_base + "_submit"):
            if not str(answer_val or "").strip():
                st.warning("Vui lòng nhập nội dung câu trả lời trước khi gửi.")
            else:
                engine = KnowledgeIntakeEngine(staging_store=store)
                is_done, msg, next_turn = engine.submit_answer(session, answer_val)
                if is_done:
                    st.success(msg)
                else:
                    st.info(msg)
                if hasattr(st, "rerun"):
                    st.rerun()

    with col2:
        if st.button("⏹️ Dừng & Tổng hợp nháp ngay", key=key_base + "_stop"):
            engine = KnowledgeIntakeEngine(staging_store=store)
            drafts = engine.end_and_synthesize(session)
            st.success("Đã kết thúc phiên và tổng hợp %d mục nháp." % len(drafts))
            if hasattr(st, "rerun"):
                st.rerun()


def render_intake_review_widget(
    st: Any, session_id: str, staging_store: Optional[IntakeStagingStore] = None
) -> None:
    """Vẽ widget duyệt tại chỗ từng mục nháp: [Đúng] / [Sửa] / [Loại].

    Chỉ mục chọn 'Đúng' hoặc 'Sửa' mới chuyển sang trạng thái CHO NAP (`cho_nap`).
    """
    store = staging_store or IntakeStagingStore()
    session_rec = store.get_session(session_id)
    if not session_rec:
        st.info("Không tìm thấy thông tin phiên %s trong staging store." % session_id)
        return

    drafts = store.list_draft_items_by_store(session_rec.store_id)
    session_drafts = [d for d in drafts if d.session_id == session_id]

    if not session_drafts:
        st.info("Chưa có mục nháp nào được tổng hợp cho phiên này.")
        return

    st.markdown("---")
    st.markdown("### 📝 Duyệt mục tri thức nháp tại chỗ (Inline Review)")
    st.caption("Xem xét từng mục: chọn **Đúng**, **Sửa** hoặc **Loại**. Chỉ mục được duyệt mới chuyển sang trạng thái CHỜ NẠP.")

    for idx, draft in enumerate(session_drafts):
        card_key = "wsc_draft_%s" % re.sub(r"\W+", "_", draft.draft_id)
        status = draft.review_status
        ingest = draft.ingest_status

        # Tiêu đề card và huy hiệu trạng thái
        if status == STATUS_DUNG:
            badge = "✅ **ĐÃ DUYỆT (CHỜ NẠP)**"
        elif status == STATUS_DA_SUA:
            badge = "✏️ **ĐÃ SỬA & DUYỆT (CHỜ NẠP)**"
        elif status == STATUS_LOAI:
            badge = "❌ **ĐÃ LOẠI (KHÔNG NẠP)**"
        else:
            badge = "⏳ **CHỜ DUYỆT**"

        st.markdown("#### Mục %d: `%s` — %s" % (idx + 1, draft.draft_id, badge))
        st.markdown("- **Nhãn nguồn:** `%s`" % draft.source_tag)
        st.markdown("- **Căn cứ nguồn trích nguyên văn:** *“%s”*" % draft.source_quote)

        # Hiển thị các trường trong khuôn hồ sơ đích
        fields = draft.fields
        st.markdown("**Nội dung theo khuôn hồ sơ đích:**")
        lines = []
        for fname, fval in fields.items():
            lines.append("- **%s:** %s" % (fname, fval))
        st.markdown("\n".join(lines))

        # Khối thao tác duyệt nếu chưa duyệt hoặc người dùng muốn đổi ý
        col_ok, col_edit, col_rej = st.columns(3)

        with col_ok:
            if st.button("✅ Đúng (Chờ nạp)", key=card_key + "_btn_ok"):
                updated = store.update_review_status(draft.draft_id, "dung")
                st.success("Đã xác nhận Đúng -> Chuyển sang trạng thái CHỜ NẠP!")
                if hasattr(st, "rerun"):
                    st.rerun()

        with col_edit:
            edit_requested = st.button("✏️ Sửa nội dung", key=card_key + "_btn_edit")

        with col_rej:
            if st.button("❌ Loại bỏ", key=card_key + "_btn_rej"):
                updated = store.update_review_status(draft.draft_id, "loai")
                st.warning("Đã loại bỏ mục này -> Tuyệt đối không nạp!")
                if hasattr(st, "rerun"):
                    st.rerun()

        # Hiển thị form sửa nếu đang bật
        state_key = "editing_" + card_key
        if edit_requested:
            st.session_state[state_key] = True

        if getattr(st, "session_state", {}).get(state_key, False):
            st.markdown("##### ✏️ Biểu mẫu sửa mục `%s`" % draft.draft_id)
            edited_inputs: Dict[str, str] = {}
            for fname, fval in fields.items():
                input_key = "%s_field_%s" % (card_key, fname)
                edited_inputs[fname] = st.text_input(
                    "Sửa trường %s:" % fname, value=fval, key=input_key
                )
            if st.button("💾 Lưu sửa đổi & Duyệt chờ nạp", key=card_key + "_btn_save_edit"):
                updated = store.update_review_status(
                    draft.draft_id, "sua", edited_fields=edited_inputs
                )
                st.session_state[state_key] = False
                st.success("Đã lưu sửa đổi -> Chuyển sang trạng thái CHỜ NẠP!")
                if hasattr(st, "rerun"):
                    st.rerun()


def render_intake_review_surface(
    st: Any, store_id: Optional[str] = None, staging_store: Optional[IntakeStagingStore] = None
) -> None:
    """Render bề mặt xem lại và metric cho vòng lặp cải thiện 3 điểm."""
    md = format_review_surface_markdown(store_id=store_id, staging_store=staging_store)
    st.markdown(md)
