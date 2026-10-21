"""Giao diện Huy hiệu Hàng đợi Chuyên gia & Popup Xác thực PIN khi Phê duyệt.

Tuân thủ thiết kế Mục 5.6 - 5.8 Báo cáo Tự học (DESKTOP-AIOS-SELF-LEARN-HERMES-ANALYSIS-HOME)
và nhiệm vụ vé DESKTOP-SELF-LEARN-EXPERT-QUEUE-ROUTING-PIN:
- Tự động nhận diện tài khoản Windows (domain\\user) qua WindowsOSIdentityProvider.
- Tự động hiển thị huy hiệu [Duyệt miền X: N] trong sidebar nếu tài khoản là chuyên gia miền.
- Hiển thị cảnh báo quá hạn 48h và leo thang 7 ngày.
- Bật hộp thoại bảo mật yêu cầu nhập mã PIN 4-6 số và kiểm tra ràng buộc tên máy.
- Đóng dấu kiểm toán và ghi nhận vào kho công ty.
- Nguyên lý Non-blocking: Người dùng thường không bị ảnh hưởng giao diện hay cản trở hỏi đáp.

Tương thích Python 3.11+.
"""

from __future__ import annotations

import platform
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from aios_habit.expert_identity_windows import WindowsOSIdentityProvider
from aios_habit.expert_review_queue import (
    ExpertReviewQueueRepository,
    QueueItem,
    STATUS_PENDING,
    get_expert_queue_repo,
)
from aios_habit.expert_roles import (
    ExpertRoleRegistry,
    get_expert_role_registry,
    matches_subject,
)


def get_current_windows_principal() -> Tuple[str, str]:
    """Lấy định danh Windows OS hiện tại (subject, node).

    Hỗ trợ biến mô phỏng trong st.session_state phục vụ kiểm thử / demo.
    """
    simulated = st.session_state.get("wsc_simulated_expert")
    if simulated:
        sim_node = st.session_state.get("wsc_simulated_machine", platform.node())
        return str(simulated).strip(), str(sim_node).strip()

    try:
        provider = WindowsOSIdentityProvider()
        principal = provider.resolve_current_principal()
        if principal:
            node = principal.metadata.get("node") or platform.node()
            return principal.subject, node
    except Exception:
        pass

    return "local_user", platform.node()


def render_expert_queue_sidebar() -> None:
    """Render huy hiệu hàng đợi chuyên gia và ngăn kéo phê duyệt trong sidebar."""
    subject, current_node = get_current_windows_principal()
    registry = get_expert_role_registry()
    repo = get_expert_queue_repo()

    # Kiểm tra xem tài khoản này có phải chuyên gia của miền nào không
    expert_domains = registry.get_domains_for_expert(subject)
    if not expert_domains:
        # Người dùng thường: Không hiển thị hàng đợi, không làm gián đoạn trải nghiệm
        return

    # Quét cập nhật leo thang theo tuổi
    try:
        repo.check_and_apply_escalations()
    except Exception:
        pass

    # Lấy danh sách mục đang chờ của các miền chuyên gia phụ trách
    all_pending = repo.list_pending_items()
    relevant_items: List[QueueItem] = []
    domain_counts: Dict[str, int] = {}
    domain_overdue: Dict[str, int] = {}

    for item in all_pending:
        if item.domain_id in expert_domains:
            # Kiểm tra phân công hoặc leo thang
            target_expert = (
                item.escalated_to
                if (item.escalation_level >= 2 and item.escalated_to)
                else item.assigned_expert
            )
            # Nếu được phân công trực tiếp hoặc là chuyên gia dự phòng của miền
            if matches_subject(subject, target_expert) or registry.is_expert_for_domain(subject, item.domain_id):
                relevant_items.append(item)
                domain_counts[item.domain_id] = domain_counts.get(item.domain_id, 0) + 1
                if item.escalation_level >= 1:
                    domain_overdue[item.domain_id] = domain_overdue.get(item.domain_id, 0) + 1

    total_count = len(relevant_items)
    if total_count == 0:
        # Có vai trò chuyên gia nhưng hàng đợi trống
        st.sidebar.markdown("---")
        st.sidebar.caption(f"👤 Chuyên gia: `{subject}`")
        st.sidebar.success("✅ Hàng đợi duyệt chuyên gia: Trống (0)")
        return

    # Xây dựng nhãn huy hiệu (Badge)
    primary_domain = expert_domains[0]
    dconf = registry.get_domain(primary_domain)
    domain_title = dconf.title if dconf else primary_domain.upper()
    overdue_count = sum(domain_overdue.values())

    if overdue_count > 0:
        badge_label = f"🚨 Duyệt miền {primary_domain.upper()}: {total_count} ({overdue_count} quá hạn)"
    else:
        badge_label = f"🔔 Duyệt miền {primary_domain.upper()}: {total_count}"

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"### 🛡️ Khu vực Chuyên gia")
    st.sidebar.caption(f"Đăng nhập: `{subject}` | Máy: `{current_node}`")

    with st.sidebar.expander(f"**[{badge_label}]**", expanded=True):
        # 1. Chỉ số sức khỏe hàng đợi
        metrics = repo.get_queue_health_metrics()
        col1, col2 = st.columns(2)
        col1.metric("Chờ duyệt", f"{total_count} mục")
        col2.metric("Lâu nhất", f"{metrics.oldest_item_age_hours:.1f}h")
        if metrics.overdue_rate > 0:
            st.caption(f"⚠️ Tỷ lệ quá hạn: **{metrics.overdue_rate*100:.1f}%**")

        st.markdown("---")
        st.markdown("**Danh sách mục chờ duyệt:**")

        active_approve_id = st.session_state.get("wsc_expert_active_approve_item")

        for idx, item in enumerate(relevant_items):
            item_dconf = registry.get_domain(item.domain_id)
            m_title = item_dconf.title if item_dconf else item.domain_id

            # Badge trạng thái ưu tiên và quá hạn (Rút gọn)
            p_badge = f"⭐ Priority: {item.priority_score:.1f}"
            st.markdown(f"**#{idx+1}. {item.title}**")
            st.caption(f"Miền: *{m_title}* · {p_badge} · Chê: {item.dislike_count} · Lượt hỏi: {item.service_frequency}")

            if item.escalation_level == 1:
                st.warning("⚠️ **Mục này đã chờ quá 48h** (Đang nhắc nhở trong ứng dụng).")
            elif item.escalation_level >= 2:
                st.error(f"🔥 **Đã quá 7 ngày!** Đã leo thang sang chuyên gia dự phòng: `{item.escalated_to}`.")

            # Nút mở Lớp duyệt tập trung (Focus Layer) phủ lên vùng chat chính
            if st.button("🔍 Mở duyệt tập trung", key=f"btn_open_focus_{item.item_id}", use_container_width=True):
                st.session_state["wsc_focus_review_active_item_id"] = item.item_id
                st.rerun()

            st.write("---")

    # Mở Lớp duyệt tập trung khi người dùng chọn mục
    active_focus_id = st.session_state.get("wsc_focus_review_active_item_id")
    if active_focus_id:
        try:
            from aios_habit.expert_review_focus_layer import render_focus_review_layer
            render_focus_review_layer(
                item_id=active_focus_id,
                subject=subject,
                current_node=current_node,
                repo=repo,
                registry=registry,
                relevant_items=relevant_items,
            )
        except Exception as exc:
            st.error(f"Lỗi khi mở lớp duyệt tập trung: {exc}")


def _render_pin_approval_form(
    item: QueueItem,
    subject: str,
    current_node: str,
    repo: ExpertReviewQueueRepository,
    registry: ExpertRoleRegistry,
) -> None:
    """Render popup xác thực mã PIN chuyên gia bảo vệ thao tác duyệt ghi kho công ty."""
    st.markdown("#### 🔒 Xác thực Chuyên gia Phê duyệt")
    st.caption("Thao tác này sẽ ghi tri thức vào kho chung công ty (`company_knowledge`).")

    # Kiểm tra ràng buộc máy tính
    is_mach_ok = registry.is_machine_authorized(item.domain_id, current_node)
    if is_mach_ok:
        st.success(f"🖥️ Tên máy: `{current_node}` (Hợp lệ)")
    else:
        st.error(f"🚫 Tên máy: `{current_node}` (Không được cấp phép duyệt miền này!)")

    # Form nhập PIN
    with st.form(key=f"form_pin_approve_{item.item_id}"):
        st.write(f"Tài khoản: **{subject}** | Mã mục: `{item.item_id}`")
        pin = st.text_input(
            "Mã PIN chuyên gia (4–6 số):",
            type="password",
            key=f"input_pin_{item.item_id}",
            help="Mã PIN cá nhân do chuyên gia thiết lập, băm salt SHA-256 lưu cục bộ.",
        )
        notes = st.text_area(
            "Ghi chú phê duyệt / sửa đổi (tùy chọn):",
            key=f"input_notes_{item.item_id}",
            placeholder="Ví dụ: Đã kiểm tra đối chiếu tài liệu kỹ thuật, chuẩn xác 100%.",
        )
        col_sub1, col_sub2 = st.columns(2)
        submit_btn = col_sub1.form_submit_button("Xác nhận & Ghi kho", type="primary", use_container_width=True)
        cancel_btn = col_sub2.form_submit_button("Hủy bỏ", use_container_width=True)

    if cancel_btn:
        st.session_state["wsc_expert_active_approve_item"] = None
        st.rerun()

    if submit_btn:
        if not is_mach_ok:
            st.error(f"Máy tính '{current_node}' không thuộc danh sách được cấp phép!")
            return

        res = repo.approve_queue_item(
            item_id=item.item_id,
            actor_subject=subject,
            pin=pin,
            machine_node=current_node,
            notes=notes,
        )

        if res.get("ok"):
            st.session_state["wsc_expert_active_approve_item"] = None
            st.session_state["wsc_action_message"] = (
                f"✅ Đã phê duyệt thành công mục #{item.item_id} vào kho công ty! "
                f"Dấu kiểm toán: {res['audit_stamp']['audit_id']}"
            )
            st.success("✅ Phê duyệt thành công!")
            st.rerun()
        else:
            st.error(f"❌ {res.get('error_vi', 'Lỗi xác thực mã PIN.')}")


def _render_reject_form(
    item: QueueItem,
    subject: str,
    current_node: str,
    repo: ExpertReviewQueueRepository,
    registry: ExpertRoleRegistry,
) -> None:
    """Render form từ chối mục hàng đợi kèm lý do kiểm toán."""
    st.markdown("#### ❌ Từ chối mục hàng đợi")
    with st.form(key=f"form_reject_{item.item_id}"):
        reason = st.text_area(
            "Lý do từ chối (bắt buộc):",
            key=f"input_rej_reason_{item.item_id}",
            placeholder="Ví dụ: Sai tiêu chuẩn dung sai cho phép hoặc dữ liệu đã lỗi thời.",
        )
        pin = st.text_input("Mã PIN chuyên gia:", type="password", key=f"input_rej_pin_{item.item_id}")
        col_s1, col_s2 = st.columns(2)
        sub_rej = col_s1.form_submit_button("Xác nhận từ chối", type="primary", use_container_width=True)
        can_rej = col_s2.form_submit_button("Hủy", use_container_width=True)

    if can_rej:
        st.session_state["wsc_expert_active_reject_item"] = None
        st.rerun()

    if sub_rej:
        res = repo.reject_queue_item(
            item_id=item.item_id,
            actor_subject=subject,
            pin=pin,
            reason=reason,
            machine_node=current_node,
        )
        if res.get("ok"):
            st.session_state["wsc_expert_active_reject_item"] = None
            st.session_state["wsc_action_message"] = f"Đã từ chối mục #{item.item_id}."
            st.success("Đã ghi nhận từ chối.")
            st.rerun()
        else:
            st.error(f"❌ {res.get('error_vi')}")
