import streamlit as st
import json
import os
import sys
from pathlib import Path
from datetime import datetime

from aios_habit.case_models import Case, EvidenceItem
from aios_habit.case_store import load_cases, load_evidence, save_case, save_evidence, init_store, load_cases_for_workspace
from aios_habit.case_ingest import ingest_excel, ingest_csv, save_uploaded_file
from aios_habit.case_graph import generate_case_mermaid
from aios_habit.case_actions import generate_next_actions
from aios_habit.case_prompt import build_prompt_pack
from aios_habit.case_audit import audit_case_cockpit_state
from aios_habit.workspace_models import init_workspace_store, load_workspaces, load_notebooks, save_workspace, save_notebook, Workspace, KnowledgeNotebook
from aios_habit.source_ingest import init_source_store, load_sources, ingest_source_document

st.set_page_config(page_title="AIOS Case Cockpit v0.1", layout="wide")

def nav_to_page(page_name):
    mapping = {
        "Nhập nhanh sự việc": "🏠 Tổng quan & Bắt đầu",
        "Tóm tắt hôm nay": "🏠 Tổng quan & Bắt đầu",
        "Hồ sơ sự việc": "📁 Hồ sơ sự việc (Case)",
        "Thêm bằng chứng": "📁 Hồ sơ sự việc (Case)",
        "Bản đồ sự việc": "📁 Hồ sơ sự việc (Case)",
        "Việc cần làm tiếp": "📁 Hồ sơ sự việc (Case)",
        "Gói câu lệnh cho AI": "📤 Xuất kết quả",
        "Bàn giao": "📤 Xuất kết quả",
        "Rút bài học": "🎓 Học nghề & An toàn",
        "Kiểm tra an toàn": "🎓 Học nghề & An toàn",
    }
    category = mapping.get(page_name, "🏠 Tổng quan & Bắt đầu")
    st.session_state.active_main_category = category
    st.session_state.page = page_name

def page_quick_intake():
    st.title("⚡ Nhập nhanh sự việc")
    st.write("Tạo nhanh một hồ sơ sự việc mới đi kèm đầy đủ các bằng chứng ban đầu trong một màn hình duy nhất.")
    
    with st.form("quick_intake_form"):
        title = st.text_input("Tên sự việc / Tiêu đề", placeholder="Ví dụ: PolarisNext - Lỗi cấu hình xuất hàng U002")
        sit = st.text_area("Mô tả ngắn tình huống hiện tại (Current Situation)", placeholder="Mô tả bối cảnh hiện tại của sự việc...", height=120)
        
        col1, col2 = st.columns(2)
        priority = col1.selectbox("Mức độ ưu tiên", ["low", "normal", "high", "critical"], index=1, format_func=lambda x: {"low": "Thấp", "normal": "Bình thường", "high": "Cao", "critical": "Khẩn cấp"}[x])
        privacy = col2.selectbox("Mức riêng tư", ["local_only", "redacted_export", "cloud_allowed"], index=0, format_func=lambda x: {
            "local_only": "Chỉ lưu cục bộ (local_only)",
            "redacted_export": "Xuất ẩn danh (redacted_export)",
            "cloud_allowed": "Cho phép đưa lên đám mây (cloud_allowed)"
        }[x])
        
        chat_log = st.text_area("Dán tin nhắn Chat/Log/Email nếu có", placeholder="Dán nội dung log lỗi hoặc đoạn hội thoại chat hỗ trợ vào đây...", height=150)
        notes = st.text_area("Ghi chú bổ sung nếu có", placeholder="Nhập thêm ghi chú cá nhân, các hành động đã làm...", height=100)
        
        excel_csv_file = st.file_uploader("Tải lên Excel/CSV nếu có", type=["xlsx", "xls", "csv"])
        img_file = st.file_uploader("Tải lên ảnh/screenshot nếu có", type=["png", "jpg", "jpeg"])
        
        submitted = st.form_submit_button("Tạo hồ sơ và thêm bằng chứng")
        
        if submitted:
            if not title.strip():
                st.error("Tiêu đề sự việc không được để trống.")
            elif not sit.strip():
                st.error("Tình huống hiện tại không được để trống.")
            else:
                excel_csv_name = excel_csv_file.name if excel_csv_file else ""
                excel_csv_bytes = excel_csv_file.read() if excel_csv_file else b""
                
                img_name = img_file.name if img_file else ""
                img_bytes = img_file.read() if img_file else b""
                
                from aios_habit.case_store import create_quick_case_with_evidence
                
                res = create_quick_case_with_evidence(
                    title=title,
                    situation=sit,
                    priority=priority,
                    privacy=privacy,
                    chat_log=chat_log,
                    notes=notes,
                    excel_csv_file_name=excel_csv_name,
                    excel_csv_content_bytes=excel_csv_bytes,
                    img_file_name=img_name,
                    img_content_bytes=img_bytes
                )
                
                st.session_state.active_case_id = res["case_id"]
                st.session_state.quick_success = {
                    "case_id": res["case_id"],
                    "title": title,
                    "evidences_count": res["evidences_count"]
                }
                st.rerun()

    if "quick_success" in st.session_state:
        qs = st.session_state.quick_success
        st.success(f"🎉 Hồ sơ sự việc **{qs['title']}** (Mã: {qs['case_id']}) đã được tạo thành công cùng với {qs['evidences_count']} bằng chứng ban đầu!")
        
        st.info("💡 Bạn có thể tiếp tục xử lý sự việc bằng cách bấm các liên kết điều hướng nhanh dưới đây:")
        col_nav1, col_nav2, col_nav3, col_nav4, col_nav5 = st.columns(5)
        col_nav1.button("🗺️ Xem bản đồ sự việc", on_click=nav_to_page, args=("Bản đồ sự việc",))
        col_nav2.button("🚀 Việc cần làm tiếp", on_click=nav_to_page, args=("Việc cần làm tiếp",))
        col_nav3.button("🤖 Gói câu lệnh cho AI", on_click=nav_to_page, args=("Gói câu lệnh cho AI",))
        col_nav4.button("🤝 Tạo bàn giao", on_click=nav_to_page, args=("Bàn giao",))
        col_nav5.button("🧠 Rút bài học", on_click=nav_to_page, args=("Rút bài học",))
        st.info("Sau khi xử lý xong, hãy vào **Rút bài học** để lưu kinh nghiệm cho lần sau.")
        
        if st.button("Đóng thông báo"):
            del st.session_state.quick_success
            st.rerun()

def page_today_brief():
    st.title("☀️ Tóm tắt hôm nay")
    active_ws_id = st.session_state.get("active_workspace_id", "default")
    cases = load_cases_for_workspace(active_ws_id)
    open_cases = [c for c in cases if c.status == "open"]
    high_priority = [c for c in cases if c.priority == "high" and c.status != "resolved" and c.status != "archived"]
    recently_updated = sorted(cases, key=lambda c: c.updated_at, reverse=True)[:5]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Tổng số hồ sơ", len(cases))
    col2.metric("Hồ sơ đang mở", len(open_cases))
    col3.metric("Ưu tiên cao đang xử lý", len(high_priority))
    
    st.subheader("Hồ sơ cần tập trung")
    for c in high_priority[:3] if high_priority else open_cases[:3]:
        status_vn = {"open": "Mở", "investigating": "Đang điều tra", "waiting": "Đang chờ", "resolved": "Đã giải quyết", "archived": "Đã lưu trữ"}.get(c.status, c.status)
        st.write(f"- **{c.title}** ({status_vn}) - Cập nhật lần cuối: {c.updated_at[:10]}")
        
    if st.button("Làm mới tóm tắt"):
        st.rerun()
    st.button("Chạy kiểm tra", on_click=nav_to_page, args=("Kiểm tra an toàn",))

    st.divider()
    st.subheader("Chạy thử & Quản trị")
    st.markdown("- [Mở Checklist chạy thử thứ Hai (Monday Pilot Checklist)](MONDAY_PILOT_CHECKLIST.md)")
    st.markdown("- [Mở Định hướng sản phẩm (Product North Star)](PRODUCT_NORTH_STAR.md)")

def page_cases():
    st.title("🗂️ Hồ sơ sự việc")
    active_ws_id = st.session_state.get("active_workspace_id", "default")
    cases = load_cases_for_workspace(active_ws_id)
    
    with st.expander("➕ Tạo hồ sơ mới"):
        with st.form("new_case"):
            title = st.text_input("Tiêu đề")
            priority = st.selectbox("Độ ưu tiên", ["low", "normal", "high", "critical"], index=1, format_func=lambda x: {"low": "Thấp (low)", "normal": "Bình thường (normal)", "high": "Cao (high)", "critical": "Khẩn cấp (critical)"}[x])
            privacy = st.selectbox("Mức độ riêng tư", ["local_only", "redacted_export", "cloud_allowed"], format_func=lambda x: {"local_only": "Chỉ lưu cục bộ (local_only)", "redacted_export": "Xuất ẩn danh (redacted_export)", "cloud_allowed": "Cho phép đưa lên đám mây (cloud_allowed)"}[x])
            if st.form_submit_button("Tạo hồ sơ"):
                if not title.strip():
                    st.error("Tiêu đề hồ sơ không được để trống.")
                else:
                    import uuid
                    c = Case(
                        case_id=f"CASE-{str(uuid.uuid4())[:8].upper()}",
                        title=title.strip(),
                        priority=priority,
                        privacy_level=privacy,
                        workspace_id=active_ws_id
                    )
                    save_case(c)
                    st.success("Đã tạo hồ sơ sự việc!")
                    st.rerun()
                 
    st.subheader("Chọn hồ sơ sự việc")
    status_map = {"open": "Mở", "investigating": "Đang điều tra", "waiting": "Đang chờ", "resolved": "Đã giải quyết", "archived": "Đã lưu trữ"}
    case_opts = {c.case_id: f"{c.case_id} - {c.title} (Trạng thái: {status_map.get(c.status, c.status)})" for c in cases}
    
    # Check if active_case_id belongs to the current workspace
    selected_idx = 0
    active_id = st.session_state.get("active_case_id")
    if active_id and active_id in case_opts:
        selected_idx = list(case_opts.keys()).index(active_id)
    else:
        # Reset if not in options
        if "active_case_id" in st.session_state:
            del st.session_state.active_case_id
            
    selected_id = st.selectbox(
        "Hồ sơ đang hoạt động",
        options=list(case_opts.keys()),
        index=selected_idx,
        format_func=lambda x: case_opts[x]
    )
    
    if selected_id:
        st.session_state.active_case_id = selected_id
        active_case = next(c for c in cases if c.case_id == selected_id)
        st.write("---")
        st.subheader("Chi tiết hồ sơ")
        
        # Load notebooks for linking
        notebooks = [n for n in load_notebooks() if n.workspace_id == active_ws_id]
        nb_opts = {n.notebook_id: n.name for n in notebooks}
        
        # Backward compatibility for linked_notebook_ids
        if not hasattr(active_case, "linked_notebook_ids") or active_case.linked_notebook_ids is None:
            active_case.linked_notebook_ids = []
            
        workspaces = load_workspaces()
        ws_options = {w.workspace_id: w.name for w in workspaces}
        ws_idx = list(ws_options.keys()).index(active_case.workspace_id) if active_case.workspace_id in ws_options else 0
        
        with st.form("edit_case"):
            sit = st.text_area("Tình huống hiện tại (Current Situation)", value=active_case.current_situation, height=150)
            stat = st.selectbox("Trạng thái (Status)", ["open", "investigating", "waiting", "resolved", "archived"], index=["open", "investigating", "waiting", "resolved", "archived"].index(active_case.status), format_func=lambda x: {"open": "Mở (open)", "investigating": "Đang điều tra (investigating)", "waiting": "Đang chờ (waiting)", "resolved": "Đã giải quyết (resolved)", "archived": "Đã lưu trữ (archived)"}[x])
            pri = st.selectbox("Độ ưu tiên (Priority)", ["low", "normal", "high", "critical"], index=["low", "normal", "high", "critical"].index(active_case.priority), format_func=lambda x: {"low": "Thấp (low)", "normal": "Bình thường (normal)", "high": "Cao (high)", "critical": "Khẩn cấp (critical)"}[x])
            
            # Select workspace
            target_ws = st.selectbox("Workspace thuộc về (Di chuyển hồ sơ nếu cần)", options=list(ws_options.keys()), index=ws_idx, format_func=lambda x: ws_options[x])
            
            # Select linked notebooks
            linked_nbs = st.multiselect(
                "Liên kết Sổ tri thức (Workspace: " + active_case.workspace_id + ")",
                options=list(nb_opts.keys()),
                default=[nid for nid in active_case.linked_notebook_ids if nid in nb_opts],
                format_func=lambda x: nb_opts[x]
            )
            
            if st.form_submit_button("Lưu thay đổi hồ sơ"):
                active_case.current_situation = sit
                active_case.status = stat
                active_case.priority = pri
                active_case.workspace_id = target_ws
                active_case.linked_notebook_ids = linked_nbs
                active_case.updated_at = datetime.now().isoformat()
                save_case(active_case)
                st.success("Đã cập nhật hồ sơ!")
                st.rerun()

def get_active_case():
    if "active_case_id" not in st.session_state:
        return None
    cases = load_cases()
    for c in cases:
        if c.case_id == st.session_state.active_case_id:
            return c
    return None

def page_add_evidence():
    st.title("📎 Thêm bằng chứng")
    active_case = get_active_case()
    if not active_case:
        st.warning("Vui lòng chọn một hồ sơ sự việc trong tab 'Hồ sơ sự việc' trước.")
        return
        
    st.write(f"**Hồ sơ đang hoạt động:** {active_case.title}")
    st.warning("Bằng chứng được đánh dấu local_only (chỉ lưu cục bộ) sẽ chỉ ở trên máy tính này và tuyệt đối không được sao chép vào prompt đám mây hoặc kho lưu trữ Git công khai.")
    
    import uuid
    new_ev_id = f"EVD-{str(uuid.uuid4())[:8].upper()}"
    
    tab1, tab2, tab3, tab4 = st.tabs(["Tải lên Excel/CSV", "Tải lên Hình ảnh", "Dán đoạn Chat/Log", "Ghi chú thủ công"])
    
    with tab1:
        uploaded_file = st.file_uploader("Chọn tệp Excel hoặc CSV", type=["xlsx", "xls", "csv"])
        if uploaded_file and st.button("Xử lý bảng dữ liệu"):
            path = save_uploaded_file(uploaded_file, active_case.case_id)
            if uploaded_file.name.endswith(".csv"):
                ev = ingest_csv(path, active_case.case_id, new_ev_id, uploaded_file.name)
            else:
                ev = ingest_excel(path, active_case.case_id, new_ev_id, uploaded_file.name)
            save_evidence(ev)
            st.success("Đã nạp bảng dữ liệu.")
            st.text(ev.structured_summary)
            
    with tab2:
        uploaded_img = st.file_uploader("Chọn tệp hình ảnh", type=["png", "jpg", "jpeg"])
        desc = st.text_input("Hình ảnh này mô tả nội dung gì?")
        if uploaded_img and st.button("Lưu bằng chứng hình ảnh"):
            path = save_uploaded_file(uploaded_img, active_case.case_id)
            ev = EvidenceItem(evidence_id=new_ev_id, case_id=active_case.case_id, source_type="screenshot", source_path=path, title=f"Ảnh chụp: {uploaded_img.name}", extracted_text=desc)
            save_evidence(ev)
            st.success("Đã lưu hình ảnh bằng chứng.")
            
    with tab3:
        paste_text = st.text_area("Dán nội dung tin nhắn Chat hoặc nhật ký Log vào đây", height=200)
        title = st.text_input("Tiêu đề nhật ký (Log)")
        if st.button("Lưu bằng chứng nhật ký (Log)"):
            if not title.strip() and not paste_text.strip():
                st.error("Không thể lưu bằng chứng nhật ký: cả tiêu đề và nội dung đều trống.")
            else:
                ev = EvidenceItem(
                    evidence_id=new_ev_id,
                    case_id=active_case.case_id,
                    source_type="chat_paste",
                    source_path="clipboard",
                    title=title.strip() or "Đoạn Chat/Log dán tay",
                    extracted_text=paste_text.strip()
                )
                save_evidence(ev)
                active_case.timeline_events.append({"date": datetime.now().isoformat(), "event": f"Đã thêm nhật ký: {title.strip() or 'Đoạn Chat/Log dán tay'}"})
                save_case(active_case)
                st.success("Đã lưu bằng chứng nhật ký và cập nhật dòng thời gian (timeline).")
            
    with tab4:
        note_text = st.text_area("Ghi chú thủ công", height=150)
        if st.button("Lưu ghi chú"):
            if not note_text.strip():
                st.error("Không thể lưu ghi chú: nội dung đang trống.")
            else:
                ev = EvidenceItem(
                    evidence_id=new_ev_id,
                    case_id=active_case.case_id,
                    source_type="note",
                    source_path="manual",
                    title="Ghi chú thủ công",
                    extracted_text=note_text.strip()
                )
                save_evidence(ev)
                st.success("Đã lưu ghi chú thành công.")

def page_case_map():
    st.title("🗺️ Bản đồ sự việc")
    active_case = get_active_case()
    if not active_case:
        st.warning("Vui lòng chọn một hồ sơ sự việc trong tab 'Hồ sơ sự việc' trước.")
        return
        
    st.write(f"**Hồ sơ đang hoạt động:** {active_case.title}")
    evs = [e for e in load_evidence() if e.case_id == active_case.case_id]
    
    mermaid_str = generate_case_mermaid(active_case, evs)
    st.markdown("### Sơ đồ trực quan (Mermaid)")
    st.code(mermaid_str, language="mermaid")
    
    st.markdown("### Bảng tổng hợp dữ liệu")
    st.write("**Các nút của hồ sơ:**")
    st.write(f"- {active_case.title}")
    st.write("**Bằng chứng:**")
    type_icons = {"excel": "📊", "csv": "📊", "screenshot": "🖼️", "image": "🖼️", "chat_paste": "💬", "log_paste": "📜", "note": "📝"}
    for e in evs:
        privacy_vn = {"local_only": "Chỉ lưu cục bộ (local_only)", "redacted_export": "Xuất ẩn danh (redacted_export)", "cloud_allowed": "Cho phép đưa lên đám mây (cloud_allowed)"}.get(e.privacy_level, e.privacy_level)
        st.write(f"- {type_icons.get(e.source_type, '📌')} {e.source_type}: {e.title} — Quyền riêng tư: `{privacy_vn}`")
    st.write("**Giả thuyết:**")
    for h in active_case.hypotheses:
        st.write(f"- {h}")

def page_next_actions():
    st.title("🚀 Việc cần làm tiếp")
    active_case = get_active_case()
    if not active_case:
        st.warning("Vui lòng chọn một hồ sơ sự việc trong tab 'Hồ sơ sự việc' trước.")
        return
        
    st.write(f"**Hồ sơ đang hoạt động:** {active_case.title}")
    evs = [e for e in load_evidence() if e.case_id == active_case.case_id]
    
    if st.button("Tự động sinh các việc cần làm tiếp theo luật"):
        actions = generate_next_actions(active_case, evs)
        active_case.next_actions.extend([a for a in actions if a not in active_case.next_actions])
        save_case(active_case)
        st.success("Đã sinh các việc cần làm tiếp theo.")
        
    st.write("---")
    new_action = st.text_input("Thêm việc cần làm thủ công:")
    if st.button("Thêm việc cần làm"):
        if new_action.strip():
            active_case.next_actions.append(new_action.strip())
            save_case(active_case)
            st.rerun()
        else:
            st.error("Nội dung việc cần làm không được để trống.")
        
    for i, a in enumerate(active_case.next_actions):
        st.write(f"{i+1}. {a}")

def page_prompt_pack():
    st.title("🤖 Gói câu lệnh cho AI (Prompt)")
    active_case = get_active_case()
    if not active_case:
        st.warning("Vui lòng chọn một hồ sơ sự việc trong tab 'Hồ sơ sự việc' trước.")
        return
        
    evs = [e for e in load_evidence() if e.case_id == active_case.case_id]
    
    target = st.selectbox("AI đích nhận lệnh (Target)", ["Gemini", "GPT", "Copilot", "NotebookLM-safe summary", "Local AI (with local_only)"], format_func=lambda x: {
        "Gemini": "Gemini (Đám mây, tự động loại bỏ local_only)",
        "GPT": "GPT (ChatGPT/Đám mây, tự động loại bỏ local_only)",
        "Copilot": "Copilot (Đám mây, tự động loại bỏ local_only)",
        "NotebookLM-safe summary": "Tóm tắt an toàn cho NotebookLM (NotebookLM-safe, loại bỏ local_only)",
        "Local AI (with local_only)": "AI cục bộ có kèm dữ liệu local_only"
    }[x])
    
    target_mapping = {
        "Gemini": ("gemini", False),
        "GPT": ("gpt", False),
        "Copilot": ("copilot", False),
        "NotebookLM-safe summary": ("notebooklm_safe", False),
        "Local AI (with local_only)": ("local_ai", True)
    }
    
    mapped_target, include_local_only = target_mapping[target]
    
    # Lấy thông tin thẻ học nghề và gọi helper để hiển thị trạng thái
    try:
        from aios_habit.learning_models import load_learning_cards_for_case
        cards = load_learning_cards_for_case(active_case.case_id)
        learning_card = cards[0] if cards else None
    except Exception:
        learning_card = None
        
    from aios_habit.case_prompt import get_learning_prompt_policy
    policy = get_learning_prompt_policy(active_case, learning_card, mapped_target, include_local_only)
    
    if policy["include_raw"]:
        st.info(f"💡 {policy['status_label_vi']}")
    else:
        st.warning(f"⚠️ {policy['status_label_vi']}")
        
    prompt = build_prompt_pack(active_case, evs, mapped_target, include_local_only, learning_card=learning_card)
    st.text_area("Nội dung gói câu lệnh đã sinh (Copy-paste)", value=prompt, height=300)

def page_handover():
    st.title("🤝 Bàn giao công việc")
    active_case = get_active_case()
    if not active_case:
        st.warning("Vui lòng chọn một hồ sơ sự việc trong tab 'Hồ sơ sự việc' trước.")
        return
        
    evs = [e for e in load_evidence() if e.case_id == active_case.case_id]
    
    st.write("---")
    st.subheader("Cài đặt bàn giao")
    export_mode_vn = st.selectbox(
        "Chế độ xuất bàn giao",
        ["Bản nội bộ", "Bản ẩn dữ liệu", "Bản an toàn cho AI/cloud"],
        help="Lựa chọn mức độ bảo mật thông tin trước khi sao chép hoặc tải xuống."
    )
    mode_mapping = {
        "Bản nội bộ": "local",
        "Bản ẩn dữ liệu": "redacted",
        "Bản an toàn cho AI/cloud": "cloud_safe"
    }
    export_mode = mode_mapping[export_mode_vn]
    
    try:
        from aios_habit.learning_models import load_learning_cards_for_case
        cards = load_learning_cards_for_case(active_case.case_id)
        learning_card = cards[0] if cards else None
    except Exception:
        learning_card = None

    from aios_habit.case_handover import build_handover_markdown
    md = build_handover_markdown(active_case, evs, learning_card, export_mode)
    
    st.markdown("### Xem trước (Preview)")
    st.markdown(md)
    st.info("Sao chép nội dung Markdown bên dưới để bàn giao sự việc. Tuyệt đối giữ nội dung này cục bộ trừ khi toàn bộ bằng chứng đã được xác nhận an toàn để chia sẻ.")
    st.download_button("Tải xuống tệp Markdown bàn giao", md, file_name=f"{active_case.case_id}_handover.md", mime="text/markdown")
    st.text_area("Mã nguồn Markdown thô", value=md, height=200)

def page_audit():
    st.title("🛡️ Kiểm tra an toàn (Audit)")
    
    if st.button("Chạy kiểm tra an toàn cục bộ"):
        active = get_active_case()
        evs = load_evidence()
        
        # Build prompt outputs for all default external targets to check for leakage
        prompt_targets = ["gemini", "gpt", "copilot", "notebooklm_safe"]
        prompt_outputs = {}
        if active:
            active_evs = [e for e in evs if e.case_id == active.case_id]
            for t in prompt_targets:
                prompt_outputs[t] = build_prompt_pack(active, active_evs, t, include_local_only=False)
                
        result = audit_case_cockpit_state(active, evs, prompt_outputs)
        
        st.subheader("Kết quả kiểm tra")
        if result["status"] == "PASS":
            st.success("✅ Kiểm tra an toàn Case Cockpit đã Vượt qua (PASS)!")
        else:
            st.error("❌ Kiểm tra an toàn Case Cockpit Thất bại (FAIL)!")
            
        if result["errors"]:
            st.subheader("Danh sách Lỗi (Errors)")
            for err in result["errors"]:
                st.write(f"- 🔴 {err}")
                
        if result["warnings"]:
            st.subheader("Danh sách Cảnh báo (Warnings)")
            for warn in result["warnings"]:
                st.write(f"- 🟡 {warn}")


def page_learning_memory():
    st.title("🧠 Rút bài học (Trí nhớ học nghề)")
    
    st.info("💡 Senior Learning Memory MVP hiện là local-first. Chưa phải cloud/export-ready nếu chưa dùng redacted/cloud_safe mode và kiểm tra an toàn.")
    
    active_case = get_active_case()
    if not active_case:
        st.warning("Vui lòng chọn một hồ sơ sự việc trong tab 'Hồ sơ sự việc' trước.")
        return
        
    st.write(f"**Hồ sơ đang hoạt động:** {active_case.title} (Trạng thái: {active_case.status})")
    
    from aios_habit.learning_models import load_learning_cards_for_case, init_learning_card_for_case, save_learning_card
    
    cards = load_learning_cards_for_case(active_case.case_id)
    if not cards:
        st.info("Hồ sơ này chưa có thẻ học nghề. Hãy bấm nút dưới đây để tạo.")
        if st.button("Tạo thẻ học nghề cho hồ sơ này"):
            init_learning_card_for_case(active_case.case_id)
            st.success("Đã tạo thẻ học nghề mới.")
            st.rerun()
        return
        
    card = cards[0]
    
    st.warning("⚠️ Không ghi nguyên nhân thật nếu chưa có bằng chứng xác nhận. Nếu case chưa kết thúc, hãy để trạng thái bản nháp hoặc ghi 'chưa xác nhận'.")
    
    # Xác định giá trị ban đầu cho trường Nguyên nhân / Giả thuyết hiện tại
    if card.confidence == "confirmed":
        init_cause_hypo = card.true_cause
    else:
        init_cause_hypo = card.initial_hypotheses
        
    with st.form("learning_card_form"):
        # Status & Confidence
        conf_options = ["draft", "reviewed", "confirmed"]
        conf_labels = {"draft": "Bản nháp (draft)", "reviewed": "Đã xem lại (reviewed)", "confirmed": "Đã xác nhận (confirmed)"}
        confidence = st.selectbox(
            "Trạng thái xác nhận của bài học",
            options=conf_options,
            index=conf_options.index(card.confidence),
            format_func=lambda x: conf_labels[x]
        )
        
        # PHẦN 1: TỐI THIỂU ĐỂ LƯU BÀI HỌC (COMPACT MODE)
        st.markdown("### 📝 Tối thiểu để lưu bài học")
        c_symptoms = st.text_area("Triệu chứng (Symptoms) [Bản rút gọn]", value=card.symptoms, height=70, key="c_symptoms")
        c_cause_hypo = st.text_area("Nguyên nhân / giả thuyết hiện tại (nếu chưa xác nhận, hãy ghi ở dạng giả thuyết)", value=init_cause_hypo, height=70, key="c_cause_hypo")
        c_verification_evidence = st.text_area("Bằng chứng kiểm chứng [Bản rút gọn]", value=card.verification_evidence, height=70, key="c_verification_evidence")
        c_check_first_next_time = st.text_input("Lần sau nên kiểm gì trước [Bản rút gọn]", value=card.check_first_next_time, key="c_check_first_next_time")
        c_reusable_lesson = st.text_area("Bài học tái sử dụng [Bản rút gọn]", value=card.reusable_lesson, height=70, key="c_reusable_lesson")
        
        st.markdown("---")
        st.markdown("### 🔍 Các trường chi tiết nâng cao")
        
        # 1. Sự việc và triệu chứng
        with st.expander("🔍 1. Sự việc và triệu chứng", expanded=False):
            a_symptoms = st.text_area("Triệu chứng thấy được (Symptoms)", value=card.symptoms, height=80, key="a_symptoms")
            a_related_systems = st.text_input("Hệ thống/bộ phận liên quan (Related Systems)", value=card.related_systems, key="a_related_systems")
            a_related_artifacts = st.text_input("Log/bảng/file/màn hình liên quan (Related Artifacts)", value=card.related_artifacts, key="a_related_artifacts")
            
        # 2. Suy luận và kiểm chứng
        with st.expander("🧩 2. Suy luận và kiểm chứng", expanded=False):
            a_initial_hypotheses = st.text_area("Giả thuyết ban đầu (Initial Hypotheses)", value=card.initial_hypotheses, height=80, key="a_initial_hypotheses")
            a_rejected_hypotheses = st.text_area("Giả thuyết bị loại bỏ (Rejected Hypotheses)", value=card.rejected_hypotheses, height=80, key="a_rejected_hypotheses")
            a_true_cause = st.text_input("Nguyên nhân thật (True Cause)", value=card.true_cause, placeholder="Có thể để trống hoặc ghi 'chưa xác nhận'", key="a_true_cause")
            a_causal_chain = st.text_area("Chuỗi nhân quả (Causal Chain)", value=card.causal_chain, height=80, key="a_causal_chain")
            a_verification_evidence = st.text_area("Bằng chứng xác nhận (Verification Evidence)", value=card.verification_evidence, height=80, key="a_verification_evidence")
            a_counter_evidence = st.text_area("Bằng chứng phản bác (Counter Evidence)", value=card.counter_evidence, height=80, key="a_counter_evidence")
            
        # 3. Đối ứng
        with st.expander("🛠️ 3. Đối ứng", expanded=False):
            a_actions_taken = st.text_area("Đối sách đã làm (Actions Taken)", value=card.actions_taken, height=80, key="a_actions_taken")
            a_result_outcome = st.text_area("Kết quả sau đối ứng (Result Outcome)", value=card.result_outcome, height=80, key="a_result_outcome")
            
        # 4. Bài học cho lần sau
        with st.expander("💡 4. Bài học cho lần sau", expanded=False):
            a_reusable_lesson = st.text_area("Bài học tái sử dụng (Reusable Lesson)", value=card.reusable_lesson, height=80, key="a_reusable_lesson")
            a_pattern_to_recognize = st.text_area("Dấu hiệu nhận diện pattern này (Pattern to Recognize)", value=card.pattern_to_recognize, height=80, key="a_pattern_to_recognize")
            a_applies_when = st.text_input("Điều kiện áp dụng (Applies When)", value=card.applies_when, key="a_applies_when")
            a_does_not_apply_when = st.text_input("Điều kiện không áp dụng (Does Not Apply When)", value=card.does_not_apply_when, key="a_does_not_apply_when")
            a_check_first_next_time = st.text_input("Lần sau nên kiểm gì trước (Check First Next Time)", value=card.check_first_next_time, key="a_check_first_next_time")
            a_retrieval_keywords = st.text_input("Từ khóa để tìm lại (Retrieval Keywords)", value=card.retrieval_keywords, key="a_retrieval_keywords")
            
        # 5. Giao tiếp hữu ích
        with st.expander("💬 5. Giao tiếp hữu ích & Cập nhật tri thức", expanded=False):
            a_useful_reply_vi = st.text_area("Câu trả lời tiếng Việt hữu ích (Useful Reply VI)", value=card.useful_reply_vi, height=80, key="a_useful_reply_vi")
            a_useful_reply_ja = st.text_area("Câu trả lời tiếng Nhật hữu ích (Useful Reply JA)", value=card.useful_reply_ja, height=80, key="a_useful_reply_ja")
            a_knowledge_update_note = st.text_area("Ghi chú cập nhật tri thức (Knowledge Update Note)", value=card.knowledge_update_note, height=80, key="a_knowledge_update_note")
            
        if st.form_submit_button("Lưu thẻ học nghề"):
            def resolve_field(orig, comp, adv):
                orig_s = (orig or "").strip()
                comp_s = (comp or "").strip()
                adv_s = (adv or "").strip()
                if not comp_s:
                    return adv_s if adv_s else orig_s
                if comp_s != orig_s and adv_s == orig_s:
                    return comp_s
                if adv_s != orig_s and comp_s == orig_s:
                    return adv_s
                if adv_s != orig_s:
                    return adv_s
                return comp_s

            # Resolve 4 simple shared fields
            card.symptoms = resolve_field(card.symptoms, c_symptoms, a_symptoms)
            card.verification_evidence = resolve_field(card.verification_evidence, c_verification_evidence, a_verification_evidence)
            card.check_first_next_time = resolve_field(card.check_first_next_time, c_check_first_next_time, a_check_first_next_time)
            card.reusable_lesson = resolve_field(card.reusable_lesson, c_reusable_lesson, a_reusable_lesson)

            # Resolve Cause / Hypothesis field deterministically
            orig_cause_hypo = card.true_cause if card.confidence == "confirmed" else card.initial_hypotheses
            if (c_cause_hypo or "").strip() != (orig_cause_hypo or "").strip():
                if confidence == "confirmed":
                    card.true_cause = c_cause_hypo
                else:
                    card.initial_hypotheses = c_cause_hypo
            else:
                card.initial_hypotheses = a_initial_hypotheses
                card.true_cause = a_true_cause

            # Other fields from advanced expanders
            card.confidence = confidence
            card.related_systems = a_related_systems
            card.related_artifacts = a_related_artifacts
            card.rejected_hypotheses = a_rejected_hypotheses
            card.causal_chain = a_causal_chain
            card.counter_evidence = a_counter_evidence
            card.actions_taken = a_actions_taken
            card.result_outcome = a_result_outcome
            card.pattern_to_recognize = a_pattern_to_recognize
            card.applies_when = a_applies_when
            card.does_not_apply_when = a_does_not_apply_when
            card.retrieval_keywords = a_retrieval_keywords
            card.useful_reply_vi = a_useful_reply_vi
            card.useful_reply_ja = a_useful_reply_ja
            card.knowledge_update_note = a_knowledge_update_note
            card.updated_at = datetime.now().isoformat()
            
            save_learning_card(card)
            st.success("Đã cập nhật thẻ học nghề thành công!")
            st.rerun()

def page_notebooks():
    st.title("📚 Sổ tri thức (Knowledge Notebook)")
    st.write("Quản lý tài liệu nguồn cục bộ, cấu hình bảo mật và liên kết tri thức nền.")
    
    def render_sufficiency_panel(nb_id, q, t_mode, exp_mode):
        if not q.strip():
            return
        from aios_habit.notebook_qa import evaluate_context_sufficiency
        suff = evaluate_context_sufficiency(nb_id, q, t_mode, exp_mode)
        
        st.markdown("##### 📊 Mức độ đủ nguồn")
        col1, col2, col3 = st.columns(3)
        col1.metric("Tổng phân đoạn", suff["total_chunks_found"])
        col2.metric("Gửi được", suff["sendable_chunks_count"])
        col3.metric("Bị ẩn", suff["redacted_chunks_count"])
        
        if suff["top_source_titles"]:
            st.markdown(f"**Nguồn liên quan:** " + ", ".join(f"`{t}`" for t in suff["top_source_titles"]))
        st.markdown(f"*local_only:* `{suff['local_only_chunks_count']}` | *cloud_allowed:* `{suff['cloud_allowed_chunks_count']}`")
        
        recommendation = suff["recommendation"]
        if "Chưa đủ nguồn" in recommendation:
            st.error(recommendation)
        elif "không đủ dữ liệu" in recommendation or "bị chặn" in recommendation:
            st.warning(recommendation)
        elif "Có thể hỏi" in recommendation or "sẵn sàng" in recommendation:
            st.success(recommendation)
        else:
            st.info(recommendation)
    
    active_ws_id = st.session_state.get("active_workspace_id", "default")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Sổ tri thức", 
        "Tài liệu nguồn", 
        "Tìm & hỏi", 
        "Ôn bài", 
        "Bản đồ"
    ])
    
    # Load notebooks for active workspace
    notebooks = [n for n in load_notebooks() if n.workspace_id == active_ws_id]
    nb_opts = {n.notebook_id: n.name for n in notebooks}
    
    with tab1:
        st.subheader("Tạo Sổ tri thức mới")
        with st.form("new_notebook_form"):
            nb_name = st.text_input("Tên Sổ tri thức (Notebook Name)")
            nb_desc = st.text_area("Mô tả Sổ tri thức")
            nb_privacy = st.selectbox("Mức độ riêng tư Sổ tri thức", ["local_only", "redacted_export", "cloud_allowed"], format_func=lambda x: {
                "local_only": "Chỉ lưu cục bộ (local_only)",
                "redacted_export": "Xuất ẩn danh (redacted_export)",
                "cloud_allowed": "Cho phép đưa lên đám mây (cloud_allowed)"
            }[x])
            nb_tags_str = st.text_input("Thẻ phân loại (ngăn cách bằng dấu phẩy)")
            
            if st.form_submit_button("Tạo Sổ tri thức"):
                if not nb_name.strip():
                    st.error("Tên Sổ tri thức không được để trống.")
                else:
                    import uuid
                    nb_id = f"NB-{str(uuid.uuid4())[:8].upper()}"
                    tags = [t.strip() for t in nb_tags_str.split(",") if t.strip()]
                    new_nb = KnowledgeNotebook(
                        notebook_id=nb_id,
                        workspace_id=active_ws_id,
                        name=nb_name.strip(),
                        description=nb_desc.strip(),
                        domain_tags=tags,
                        privacy_level=nb_privacy
                    )
                    save_notebook(new_nb)
                    st.success(f"Đã tạo Sổ tri thức: {nb_name}")
                    st.rerun()
                    
        st.subheader("Các Sổ tri thức hiện có")
        if not notebooks:
            st.info("Chưa có Sổ tri thức nào trong Workspace này. Hãy tạo một sổ ở trên.")
        else:
            for n in notebooks:
                privacy_vn = {"local_only": "Cục bộ (local_only)", "redacted_export": "Ẩn danh (redacted_export)", "cloud_allowed": "Cho phép cloud (cloud_allowed)"}.get(n.privacy_level, n.privacy_level)
                st.write(f"📖 **{n.name}** (Quyền: {privacy_vn}) - *{n.description}*")
                
    with tab2:
        col_left, col_right = st.columns([1, 1])
        
        with col_left:
            st.subheader("Nạp tài liệu nguồn")
            if not notebooks:
                st.warning("Vui lòng tạo ít nhất một Sổ tri thức trước khi tải lên tài liệu.")
            else:
                selected_nb_id = st.selectbox("Chọn Sổ tri thức đích", options=list(nb_opts.keys()), format_func=lambda x: nb_opts[x], key="ingest_nb_select")
                uploaded_file = st.file_uploader("Chọn tài liệu nguồn (TXT, MD, CSV, Excel, PDF)", type=["txt", "md", "csv", "xlsx", "xls", "pdf"])
                doc_title = st.text_input("Tiêu đề tài liệu (để trống sẽ dùng tên tệp)")
                doc_desc = st.text_area("Mô tả tài liệu")
                
                selected_nb = next(n for n in notebooks if n.notebook_id == selected_nb_id)
                doc_privacy = st.selectbox("Mức độ riêng tư tài liệu", ["local_only", "redacted_export", "cloud_allowed"], index=["local_only", "redacted_export", "cloud_allowed"].index(selected_nb.privacy_level), key="ingest_doc_privacy")
                
                if uploaded_file and st.button("Nạp vào Sổ tri thức", key="ingest_btn"):
                    file_bytes = uploaded_file.read()
                    try:
                        ingest_source_document(
                            notebook_id=selected_nb_id,
                            original_filename=uploaded_file.name,
                            file_bytes=file_bytes,
                            title=doc_title,
                            description=doc_desc,
                            privacy_level=doc_privacy
                        )
                        st.success(f"Đã nạp thành công tài liệu: {uploaded_file.name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi nạp tài liệu: {e}")
                        
        with col_right:
            st.subheader("Danh sách Tài liệu nguồn đã nạp")
            sources = load_sources()
            ws_nb_ids = {n.notebook_id for n in notebooks}
            ws_sources = [s for s in sources if s.notebook_id in ws_nb_ids]
            
            if not ws_sources:
                st.info("Chưa có tài liệu nguồn nào được nạp trong Workspace này.")
            else:
                source_opts = {s.source_id: f"{s.title} (Sổ: {nb_opts.get(s.notebook_id, s.notebook_id)})" for s in ws_sources}
                selected_src_id = st.selectbox("Chọn tài liệu để xem", options=list(source_opts.keys()), format_func=lambda x: source_opts[x], key="preview_src_select")
                
                if selected_src_id:
                    src = next(s for s in ws_sources if s.source_id == selected_src_id)
                    st.write("---")
                    st.write(f"### Chi tiết tài liệu: {src.title}")
                    st.write(f"- **Tên tệp gốc:** {src.original_filename}")
                    st.write(f"- **Định dạng:** {src.source_type.upper()}")
                    st.write(f"- **Mức riêng tư:** {src.privacy_level}")
                    st.write(f"- **Mô tả:** {src.description}")
                    st.write(f"- **Đường dẫn cục bộ:** `{src.asset_path}`")
                    
                    st.write("#### Xem trước nội dung (Preview - Tối đa 1000 ký tự):")
                    if src.preview_text:
                        st.text_area("Nội dung trích xuất", value=src.preview_text, height=200, disabled=True, key="preview_text_area")
                    else:
                        st.info("Chưa có xem trước nội dung cho định dạng này ở M1.7.")
                        
    with tab3:
        st.subheader("Tìm kiếm và hỏi theo nguồn tri thức")
        st.markdown(
            "AI đích không tự có dữ liệu nội bộ. "
            "AIOS phải gửi kèm đoạn nguồn liên quan, hoặc bạn phải dùng NotebookLM đã được upload tài liệu."
        )
        
        from aios_habit.llm_client import is_llm_configured, load_llm_config
        config = load_llm_config()
        if config:
            st.success(
                f"✅ **Đã cấu hình AI Provider:** `{config.provider}` | "
                f"**Model:** `{config.model}` | "
                f"**Locality:** `{config.locality.upper()}`"
            )
        else:
            st.warning(
                "⚠️ **Chưa cấu hình AI provider.** Bạn vẫn có thể tạo prompt hoặc dùng NotebookLM Bridge để copy sang AI ngoài."
            )
            
        if not notebooks:
            st.warning("Vui lòng tạo ít nhất một Sổ tri thức trước khi tìm kiếm.")
        else:
            from aios_habit.notebook_index import build_notebook_index, search_notebook_chunks
            from aios_habit.notebook_qa import build_notebook_question_prompt, answer_notebook_question
            
            selected_nb_id = st.selectbox("Chọn Sổ tri thức để truy vấn", options=list(nb_opts.keys()), format_func=lambda x: nb_opts[x], key="qa_nb_select")
            
            from aios_habit.notebook_import_store import load_bridge_imports, delete_bridge_import
            saved_imports = load_bridge_imports(selected_nb_id)
            
            # Assistant Panel "Bước tiếp theo nên làm gì?"
            from aios_habit.daily_next_actions import suggest_next_actions
            next_actions = suggest_next_actions(active_ws_id, selected_nb_id)
            with st.expander("💡 Bước tiếp theo nên làm gì?", expanded=True):
                for act in next_actions:
                    st.write(f"- {act}")
            
            if st.button("Cập nhật chỉ mục (Re-index)", key="reindex_btn"):
                with st.spinner("Đang trích xuất và chỉ mục hóa tài liệu..."):
                    build_notebook_index(selected_nb_id)
                st.success("Đã cập nhật chỉ mục thành công!")
                
            search_query = st.text_input("Tìm kiếm từ khóa nhanh trong sổ", key="qa_search_query")
            if search_query.strip():
                hits = search_notebook_chunks(selected_nb_id, search_query, limit=5)
                if not hits:
                    st.info("Không tìm thấy đoạn tài liệu phù hợp.")
                else:
                    st.write(f"Tìm thấy {len(hits)} đoạn tài liệu phù hợp nhất:")
                    for i, hit in enumerate(hits):
                        with st.expander(f"📌 {i+1}. {hit.chunk.source_title} (Độ khớp: {hit.score:.1f})"):
                            st.write(f"- **File gốc:** `{hit.chunk.original_filename}` | **ID:** `{hit.chunk.source_id}` | **Privacy:** `{hit.chunk.privacy_level}`")
                            st.text_area(f"Đoạn {hit.chunk.chunk_index}", value=hit.chunk.text, height=120, disabled=True, key=f"hit_text_{hit.chunk.chunk_id}")
                            
            st.write("---")
            
            truth_mode = st.selectbox(
                "Chế độ hỏi (Truth Mode)",
                [
                    "Hỏi bằng AIOS local context",
                    "Hỏi cloud bằng context được phép",
                    "NotebookLM Bridge",
                    "Chỉ tạo prompt để copy"
                ],
                key="qa_truth_mode"
            )
            
            if truth_mode == "Hỏi bằng AIOS local context":
                st.info("💡 Chế độ này sẽ gửi dữ liệu local_only cục bộ. Đảm bảo provider AI của bạn chạy nội bộ (local).")
                question = st.text_area("Nhập câu hỏi", placeholder="Ví dụ: Cấu hình DHCP và thiết lập FRPO U002 là gì?", key="local_qa_question")
                
                # Context Sufficiency Panel
                render_sufficiency_panel(selected_nb_id, question, truth_mode, "local")
                
                col_btn1, col_btn2 = st.columns(2)
                ask_btn = col_btn1.button("Hỏi ngay trong AIOS", key="local_ask_btn")
                copy_btn = col_btn2.button("Tạo prompt để copy", key="local_copy_btn")
                
                if ask_btn:
                    if not question.strip():
                        st.error("Vui lòng nhập câu hỏi.")
                    elif not config:
                        st.error("Chưa cấu hình AI provider. Hãy cấu hình biến môi trường AIOS_LLM_PROVIDER.")
                    elif config.locality == "cloud":
                        st.error("❌ Không thể gửi dữ liệu local_only tới Gemini/GPT/Copilot. Hãy chọn Cloud-safe context hoặc dùng Local AI / NotebookLM Bridge.")
                    else:
                        with st.spinner("AIOS đang suy nghĩ cục bộ..."):
                            res = answer_notebook_question(selected_nb_id, question, "local_ai", "local")
                        if res.blocked:
                            st.error(f"⚠️ Yêu cầu bị chặn: {res.block_reason}")
                        else:
                            st.markdown("### 🤖 Câu trả lời từ AIOS:")
                            st.write(res.answer_text)
                            with st.expander("📝 Prompt đã gửi tới AIOS provider", expanded=False):
                                st.code(res.prompt_text, language="markdown")
                            with st.expander("📚 Các phân đoạn tài liệu được sử dụng"):
                                for i, chunk in enumerate(res.used_chunks):
                                    st.markdown(f"**{i+1}. {chunk.source_title}** ({chunk.original_filename})")
                                    st.text_area(f"Đoạn {chunk.chunk_index}", value=chunk.text, height=100, disabled=True, key=f"local_ans_{chunk.chunk_id}")
                
                if copy_btn:
                    if not question.strip():
                        st.error("Vui lòng nhập câu hỏi.")
                    else:
                        prompt = build_notebook_question_prompt(selected_nb_id, question, "local_ai", "local")
                        st.text_area("Prompt để copy (Gói prompt Q&A đã sinh)", value=prompt, height=200, key="local_prompt_out")
                        st.markdown("**Xem trước Prompt (để đọc dễ dàng):**")
                        st.code(prompt, language="markdown")
                        st.success("Đã sinh prompt thành công!")
                        
            elif truth_mode == "Hỏi cloud bằng context được phép":
                st.warning("⚠️ Dữ liệu local_only sẽ bị ẩn (redacted). Câu trả lời có thể yếu nếu phần lớn nguồn bị ẩn.")
                question = st.text_area("Nhập câu hỏi", placeholder="Ví dụ: Quy trình DHCP xuất hàng là gì?", key="cloud_qa_question")
                
                # Context Sufficiency Panel
                render_sufficiency_panel(selected_nb_id, question, truth_mode, "cloud_safe")
                
                col_btn1, col_btn2 = st.columns(2)
                ask_btn = col_btn1.button("Hỏi ngay trong AIOS", key="cloud_ask_btn")
                copy_btn = col_btn2.button("Tạo prompt để copy", key="cloud_copy_btn")
                
                if ask_btn:
                    if not question.strip():
                        st.error("Vui lòng nhập câu hỏi.")
                    elif not config:
                        st.error("Chưa cấu hình AI provider. Hãy cấu hình biến môi trường AIOS_LLM_PROVIDER.")
                    else:
                        with st.spinner("AIOS đang gọi AI Cloud..."):
                            res = answer_notebook_question(selected_nb_id, question, "gemini", "cloud_safe")
                        if res.blocked:
                            st.error(f"⚠️ Yêu cầu bị chặn: {res.block_reason}")
                        else:
                            st.markdown("### 🤖 Câu trả lời từ AIOS:")
                            st.write(res.answer_text)
                            with st.expander("📝 Prompt đã gửi tới AIOS provider", expanded=False):
                                st.code(res.prompt_text, language="markdown")
                            with st.expander("📚 Các phân đoạn tài liệu được sử dụng (Đã mã hóa/ẩn local_only)"):
                                for i, chunk in enumerate(res.used_chunks):
                                    st.markdown(f"**{i+1}. {chunk.source_title}** ({chunk.original_filename}, Privacy: {chunk.privacy_level})")
                                    txt = "[ĐÃ LOẠI BỎ VÌ RIÊNG TƯ - local_only]" if chunk.privacy_level == "local_only" else chunk.text
                                    st.text_area(f"Đoạn {chunk.chunk_index}", value=txt, height=100, disabled=True, key=f"cloud_ans_{chunk.chunk_id}")
                
                if copy_btn:
                    if not question.strip():
                        st.error("Vui lòng nhập câu hỏi.")
                    else:
                        prompt = build_notebook_question_prompt(selected_nb_id, question, "gemini", "cloud_safe")
                        st.text_area("Prompt để copy (Gói prompt Q&A đã sinh)", value=prompt, height=200, key="cloud_prompt_out")
                        st.markdown("**Xem trước Prompt (để đọc dễ dàng):**")
                        st.code(prompt, language="markdown")
                        st.success("Đã sinh prompt thành công!")
                        
            elif truth_mode == "NotebookLM Bridge":
                st.markdown(
                    "**Chỉ dùng chế độ này với NotebookLM đã được phép chứa tài liệu của bạn.**  \n"
                    "AIOS không tự gửi tài liệu sang NotebookLM trong bước này. "
                    "Bạn tự copy prompt và paste kết quả về."
                )
                
                task_type_vn = st.selectbox(
                    "Loại nhiệm vụ (Task Type)",
                    [
                        "Trích xuất đồ thị (knowledge_graph_json)",
                        "Bộ học tập ôn bài (study_pack_json)",
                        "Phân tích điều tra hồ sơ (case_investigation_json)",
                        "Vẽ sơ đồ Mermaid (mermaid_graph)"
                    ],
                    key="bridge_task_type"
                )
                
                task_type_map = {
                    "Trích xuất đồ thị (knowledge_graph_json)": "knowledge_graph_json",
                    "Bộ học tập ôn bài (study_pack_json)": "study_pack_json",
                    "Phân tích điều tra hồ sơ (case_investigation_json)": "case_investigation_json",
                    "Vẽ sơ đồ Mermaid (mermaid_graph)": "mermaid_graph"
                }
                task_type = task_type_map[task_type_vn]
                
                user_question = ""
                if task_type == "case_investigation_json":
                    user_question = st.text_area("Nhập tình huống hoặc câu hỏi cụ thể", key="bridge_question")
                    render_sufficiency_panel(selected_nb_id, user_question, truth_mode, "cloud_safe")
                    
                if st.button("Tạo prompt NotebookLM", key="bridge_prompt_btn"):
                    from aios_habit.notebook_bridge import build_notebooklm_bridge_prompt
                    prompt = build_notebooklm_bridge_prompt(selected_nb_id, task_type, user_question)
                    st.text_area("Prompt để copy (Prompt cho NotebookLM - Hãy copy toàn bộ)", value=prompt, height=200, key="bridge_prompt_out")
                    st.markdown("**Xem trước Prompt (để đọc dễ dàng):**")
                    st.code(prompt, language="markdown")
                    st.success("Đã sinh prompt! Hãy dán prompt này vào giao diện NotebookLM của bạn.")
                    
                st.write("---")
                st.markdown("### Dán kết quả từ NotebookLM")
                import_text = st.text_area("Kết quả dán từ NotebookLM", height=150, placeholder="Dán nội dung JSON hoặc mã Mermaid nhận được từ NotebookLM vào đây...", key="bridge_import_text")
                
                if st.button("Kiểm tra và nhập kết quả", key="bridge_import_btn"):
                    if not import_text.strip():
                        st.error("Vui lòng dán kết quả cần kiểm tra.")
                    else:
                        from aios_habit.notebook_bridge import detect_bridge_import_type, parse_bridge_import, graph_json_to_mermaid
                        imp_type = detect_bridge_import_type(import_text)
                        
                        if imp_type == "unknown":
                            st.error("❌ Định dạng không được nhận diện hoặc JSON không hợp lệ.")
                            if "parsed_import_data" in st.session_state:
                                del st.session_state.parsed_import_data
                        else:
                            parsed_json = parse_bridge_import(import_text)
                            mermaid = ""
                            if imp_type == "mermaid_graph":
                                from aios_habit.notebook_bridge import clean_code_fences
                                mermaid = clean_code_fences(import_text)
                            elif imp_type == "knowledge_graph_json":
                                mermaid = graph_json_to_mermaid(parsed_json)
                                
                            st.session_state.parsed_import_data = {
                                "type": imp_type,
                                "raw_text": import_text,
                                "parsed_json": parsed_json,
                                "mermaid_text": mermaid
                            }
                            st.success(f"✅ Đọc thành công dữ liệu dạng {imp_type}!")
                            st.rerun()
                            
                # Render preview and Save Form if parsed_import_data is loaded in session state
                if "parsed_import_data" in st.session_state:
                    pdata = st.session_state.parsed_import_data
                    imp_type = pdata["type"]
                    parsed_json = pdata["parsed_json"]
                    mermaid = pdata["mermaid_text"]
                    
                    st.write("---")
                    st.markdown("### Preview Dữ liệu vừa nhập")
                    
                    if imp_type == "mermaid_graph":
                        st.code(mermaid, language="mermaid")
                    elif imp_type == "knowledge_graph_json":
                        st.code(mermaid, language="mermaid")
                        st.markdown("#### Danh sách các nút:")
                        for node in parsed_json.get("nodes", []):
                            st.write(f"- **{node.get('label')}** ({node.get('type')}) — {node.get('description')} [Nguồn: {node.get('source_ref')}]")
                    elif imp_type == "study_pack_json":
                        st.write(f"**Tóm tắt:** {parsed_json.get('summary')}")
                        st.markdown("#### Thuật ngữ:")
                        for g in parsed_json.get("glossary", []):
                            st.write(f"- **{g.get('term')}:** {g.get('meaning')} (Nguồn: {g.get('source_ref')})")
                        st.markdown("#### Thẻ nhớ (Flashcards):")
                        for f in parsed_json.get("flashcards", []):
                            st.write(f"- **Hỏi:** {f.get('front')}  \n  **Đáp:** {f.get('back')} (Nguồn: {f.get('source_ref')})")
                    elif imp_type == "case_investigation_json":
                        st.write("**Triệu chứng:**", parsed_json.get("symptoms", []))
                        st.write("**Giả thuyết:**", parsed_json.get("hypotheses", []))
                        st.write("**Bằng chứng cần check:**", parsed_json.get("evidence_to_check", []))
                        st.write("**Chưa kết luận vội:**", parsed_json.get("do_not_conclude_yet", []))
                        st.write("**Phản hồi tiếng Việt:**", parsed_json.get("draft_reply_vi", ""))
                        
                    # Save Form
                    st.write("---")
                    st.subheader("Lưu kết quả vào AIOS")
                    st.warning("Kết quả NotebookLM import là dữ liệu do AI đề xuất. Mặc định trạng thái draft. Chỉ dùng làm tri thức xác nhận sau khi người dùng review.")
                    
                    col_save1, col_save2 = st.columns(2)
                    save_title = col_save1.text_input("Tiêu đề lưu trữ", value=f"NotebookLM import - {datetime.now().strftime('%Y-%m-%d %H:%M')}", key="bridge_save_title")
                    save_status = col_save2.selectbox("Trạng thái lưu", ["draft", "reviewed", "confirmed"], key="bridge_save_status")
                    
                    if st.button("Lưu kết quả", key="save_bridge_import_btn"):
                        import uuid
                        from aios_habit.notebook_import_store import NotebookBridgeImport, save_bridge_import
                        
                        import_id = f"IMP-{str(uuid.uuid4())[:8].upper()}"
                        new_record = NotebookBridgeImport(
                            import_id=import_id,
                            notebook_id=selected_nb_id,
                            workspace_id=active_ws_id,
                            import_type=imp_type,
                            title=save_title.strip() if save_title.strip() else "NotebookLM import",
                            raw_text=pdata["raw_text"],
                            parsed_json=parsed_json,
                            mermaid_text=mermaid,
                            privacy_level="local_only",
                            status=save_status
                        )
                        save_bridge_import(new_record)
                        
                        from aios_habit.notebook_bridge import summarize_bridge_import
                        summary = summarize_bridge_import(parsed_json, imp_type)
                        st.success(f"✅ Đã lưu kết quả thành công với ID: `{import_id}`")
                        st.write("Thông số lưu trữ:", summary)
                        
                        del st.session_state.parsed_import_data
                        st.rerun()
                        
            elif truth_mode == "Chỉ tạo prompt để copy":
                question = st.text_area("Nhập câu hỏi để soạn prompt", placeholder="Ví dụ: Cấu hình DHCP và thiết lập FRPO U002 là gì?", key="fallback_qa_question")
                
                col1, col2 = st.columns(2)
                target = col1.selectbox("AI đích nhận lệnh (Target)", ["Gemini", "GPT", "Copilot", "NotebookLM-safe summary", "Local AI (with local_only)"], key="fallback_target_select")
                export_mode = col2.selectbox("Chế độ xuất (Export Mode)", ["Bản nội bộ (local)", "Bản an toàn cho cloud (cloud_safe)"], key="fallback_export_mode_select")
                
                target_map = {
                    "Gemini": "gemini",
                    "GPT": "gpt",
                    "Copilot": "copilot",
                    "NotebookLM-safe summary": "notebooklm_safe",
                    "Local AI (with local_only)": "local_ai"
                }
                export_map = {
                    "Bản nội bộ (local)": "local",
                    "Bản an toàn cho cloud (cloud_safe)": "cloud_safe"
                }
                
                # Context Sufficiency Panel
                render_sufficiency_panel(selected_nb_id, question, truth_mode, export_map[export_mode])
                
                if target_map[target] != "local_ai" and export_map[export_mode] == "local":
                    st.warning("⚠️ Cảnh báo: Bạn đang chọn mục tiêu Cloud nhưng Chế độ xuất là Local. Prompt có thể chứa dữ liệu riêng tư local_only.")
                    
                if st.button("Tạo prompt trả lời", key="fallback_prompt_btn"):
                    if not question.strip():
                        st.error("Vui lòng nhập câu hỏi.")
                    else:
                        prompt = build_notebook_question_prompt(selected_nb_id, question, target_map[target], export_map[export_mode])
                        st.text_area("Prompt để copy (Gói prompt Q&A đã sinh)", value=prompt, height=200, key="fallback_prompt_output")
                        st.markdown("**Xem trước Prompt (để đọc dễ dàng):**")
                        st.code(prompt, language="markdown")
                        st.success("Đã tạo prompt thành công! Bạn có thể copy để gửi cho AI của mình.")
            
            # Saved imports list (independent of truth_mode)
            st.write("---")
            st.subheader("Kết quả NotebookLM đã lưu")
            
            from aios_habit.notebook_import_store import load_bridge_imports, delete_bridge_import
            saved_imports = load_bridge_imports(selected_nb_id)
            
            if not saved_imports:
                st.info("Chưa có kết quả NotebookLM nào được lưu cho sổ tri thức này.")
            else:
                for imp in saved_imports:
                    type_vn = {
                        "knowledge_graph_json": "Đồ thị tri thức (JSON)",
                        "study_pack_json": "Bộ học tập ôn bài (JSON)",
                        "case_investigation_json": "Phân tích điều tra hồ sơ (JSON)",
                        "mermaid_graph": "Sơ đồ Mermaid (Mã thô)"
                    }.get(imp.import_type, imp.import_type)
                    
                    with st.expander(f"📖 {imp.title} ({type_vn}) - Trạng thái: {imp.status.upper()} ({imp.created_at[:16]})"):
                        st.write(f"- **Mã nhập:** `{imp.import_id}`")
                        st.write(f"- **Mức riêng tư:** `{imp.privacy_level}`")
                        
                        if imp.import_type == "mermaid_graph" or imp.import_type == "knowledge_graph_json":
                            st.markdown("##### Sơ đồ quan hệ (Mermaid):")
                            st.code(imp.mermaid_text, language="mermaid")
                            if imp.import_type == "knowledge_graph_json" and imp.parsed_json:
                                st.markdown("##### Danh sách các nút:")
                                for node in imp.parsed_json.get("nodes", []):
                                    st.write(f"  * **{node.get('label')}** ({node.get('type')}) — {node.get('description')} [Nguồn: {node.get('source_ref')}]")
                        elif imp.import_type == "study_pack_json":
                            st.markdown("##### Tóm tắt:")
                            st.write(imp.parsed_json.get("summary", ""))
                            
                            st.markdown("##### Thuật ngữ:")
                            for g in imp.parsed_json.get("glossary", []):
                                st.write(f"  * **{g.get('term')}:** {g.get('meaning')} (Nguồn: {g.get('source_ref')})")
                                
                            st.markdown("##### Thẻ học (Flashcards):")
                            for f in imp.parsed_json.get("flashcards", []):
                                st.write(f"  * **Hỏi:** {f.get('front')}  \n    **Đáp:** {f.get('back')} (Nguồn: {f.get('source_ref')})")
                                
                            st.markdown("##### Câu hỏi ôn tập:")
                            for q in imp.parsed_json.get("review_questions", []):
                                st.write(f"  * **Q:** {q.get('question')}  \n    **A:** {q.get('expected_answer')} (Nguồn: {q.get('source_ref')})")
                        elif imp.import_type == "case_investigation_json":
                            st.write("**Triệu chứng:**", imp.parsed_json.get("symptoms", []))
                            st.write("**Giả thuyết:**", imp.parsed_json.get("hypotheses", []))
                            st.write("**Bằng chứng cần check:**", imp.parsed_json.get("evidence_to_check", []))
                            st.write("**Chưa kết luận vội:**", imp.parsed_json.get("do_not_conclude_yet", []))
                            st.write("**Phản hồi tiếng Việt:**", imp.parsed_json.get("draft_reply_vi", ""))
                            st.write("**Phản hồi tiếng Nhật:**", imp.parsed_json.get("draft_reply_ja", ""))
                            
                            st.write("---")
                            col_c1, col_c2 = st.columns(2)
                            if col_c1.button("Tạo Case nháp từ kết quả này", key=f"create_case_btn_{imp.import_id}"):
                                from aios_habit.notebook_case_actions import create_case_from_investigation_import
                                res = create_case_from_investigation_import(imp, active_ws_id)
                                st.success(f"✅ Đã tạo thành công Case nháp `{res['case_id']}` với {res['evidence_count']} checklist bằng chứng!")
                            
                        # Delete safety confirmation
                        st.write("---")
                        col_del1, col_del2 = st.columns([3, 1])
                        confirm_del = col_del1.checkbox("Tôi xác nhận muốn xóa kết quả đã lưu", key=f"confirm_del_imp_{imp.import_id}")
                        if col_del2.button("Xóa kết quả đã lưu", key=f"del_imp_{imp.import_id}"):
                            if not confirm_del:
                                st.error("Vui lòng tích chọn xác nhận trước khi xóa.")
                            else:
                                delete_bridge_import(imp.import_id)
                                st.success("Đã xóa thành công!")
                                st.rerun()
            
            # Recent Activity Panel
            st.write("---")
            st.subheader("⏱️ Hoạt động gần đây")
            col_act1, col_act2 = st.columns(2)
            
            with col_act1:
                st.markdown("##### Import NotebookLM gần đây")
                if not saved_imports:
                    st.info("Chưa có import nào.")
                else:
                    for imp in saved_imports[:5]:
                        type_vn = {
                            "knowledge_graph_json": "Đồ thị",
                            "study_pack_json": "Bộ học tập",
                            "case_investigation_json": "Điều tra",
                            "mermaid_graph": "Sơ đồ Mermaid"
                        }.get(imp.import_type, imp.import_type)
                        st.write(f"- **{imp.title}** ({type_vn}) — `{imp.status}` — *{imp.created_at[:16]}*")
                        
            with col_act2:
                st.markdown("##### Câu hỏi & Câu trả lời gần đây")
                from aios_habit.notebook_qa import load_answer_history
                history = load_answer_history(selected_nb_id, limit=5)
                if not history:
                    st.info("Chưa có câu hỏi nào được trả lời trong AIOS.")
                else:
                    for item in history:
                        st.write(f"- **Hỏi:** {item.get('question')}  \n  **AI:** {item.get('provider')}/{item.get('model')} — *{item.get('created_at', '')[:16]}*")
                    
    with tab4:
        st.subheader("Ôn bài trong AIOS")
        if not notebooks:
            st.warning("Vui lòng tạo ít nhất một Sổ tri thức trước khi ôn bài.")
        else:
            from aios_habit.study_store import (
                load_study_cards,
                delete_study_card,
                create_cards_from_chunks,
                create_cards_from_study_pack_import
            )
            from aios_habit.notebook_import_store import load_bridge_imports
            
            selected_nb_id = st.selectbox("Chọn Sổ tri thức để ôn bài", options=list(nb_opts.keys()), format_func=lambda x: nb_opts[x], key="study_nb_select")
            
            # Section 1 — Tạo thẻ học từ chỉ mục AIOS
            st.markdown("### 1. Tạo thẻ học từ chỉ mục AIOS")
            if st.button("Tạo thẻ học từ nguồn đã index", key="create_cards_chunks_btn"):
                from aios_habit.notebook_index import load_chunks
                chunks = load_chunks(selected_nb_id)
                if not chunks:
                    st.warning("Chưa có chỉ mục. Hãy sang tab Tìm & hỏi và bấm Cập nhật chỉ mục.")
                else:
                    new_cards = create_cards_from_chunks(selected_nb_id, active_ws_id)
                    st.success(f"Đã tạo thành công {len(new_cards)} thẻ học từ nguồn đã index!")
                    st.rerun()
                    
            # Section 2 — Nhập thẻ học từ NotebookLM
            st.markdown("### 2. Nhập thẻ học từ NotebookLM")
            saved_sp_imports = [imp for imp in load_bridge_imports(selected_nb_id) if imp.import_type == "study_pack_json"]
            if not saved_sp_imports:
                st.info("Chưa có Study Pack từ NotebookLM. Hãy dùng NotebookLM Bridge để tạo study_pack_json rồi lưu vào AIOS.")
            else:
                sp_opts = {imp.import_id: imp.title for imp in saved_sp_imports}
                selected_sp_id = st.selectbox("Chọn Study Pack đã lưu", options=list(sp_opts.keys()), format_func=lambda x: sp_opts[x], key="study_pack_import_select")
                if st.button("Tạo thẻ học từ Study Pack đã lưu", key="create_cards_sp_btn"):
                    selected_imp = next(imp for imp in saved_sp_imports if imp.import_id == selected_sp_id)
                    new_cards = create_cards_from_study_pack_import(selected_imp, active_ws_id)
                    st.success(f"Đã tạo thành công {len(new_cards)} thẻ học từ Study Pack `{selected_imp.title}`!")
                    st.rerun()
                    
            # Section 3 — Thẻ học đã lưu
            st.markdown("### 3. Thẻ học đã lưu")
            saved_cards = load_study_cards(selected_nb_id)
            if not saved_cards:
                st.info("Chưa có thẻ học nào được lưu cho sổ tri thức này.")
            else:
                for card in saved_cards:
                    with st.expander(f"🎴 {card.front} (Trạng thái: {card.status.upper()})"):
                        st.write(f"- **Nguồn tham chiếu:** {card.source_ref}")
                        st.write(f"- **Tags:** {', '.join(card.tags)}")
                        
                        show_back = st.checkbox("Hiển thị mặt sau (Đáp án)", key=f"show_back_{card.card_id}")
                        if show_back:
                            st.info(card.back)
                            
                        # Delete safety confirmation
                        st.write("---")
                        col_del1, col_del2 = st.columns([3, 1])
                        confirm_del = col_del1.checkbox("Tôi xác nhận muốn xóa thẻ này", key=f"confirm_del_{card.card_id}")
                        if col_del2.button("Xóa thẻ học", key=f"del_card_btn_{card.card_id}"):
                            if not confirm_del:
                                st.error("Vui lòng tích chọn xác nhận trước khi xóa.")
                            else:
                                delete_study_card(card.card_id)
                                st.success("Đã xóa thẻ học thành công!")
                                st.rerun()
                                
            # Section 4 — Prompt ôn bài nâng cao
            st.markdown("---")
            with st.expander("Tạo prompt nâng cao nếu muốn dùng NotebookLM/Gemini"):
                st.markdown(
                    "Gemini/GPT/Copilot chỉ tạo được nội dung tốt nếu AIOS gửi kèm context.\n\n"
                    "NotebookLM phù hợp hơn cho Study Pack vì đã có toàn bộ source bạn upload.\n\n"
                    "AIOS sẽ lưu thẻ học lại để dùng hằng ngày."
                )
                from aios_habit.notebook_qa import build_study_pack_prompt
                
                col1, col2 = st.columns(2)
                target = col1.selectbox("AI đích nhận lệnh (Target)", ["Gemini", "GPT", "Copilot", "NotebookLM-safe summary", "Local AI (with local_only)"], key="study_target_select")
                export_mode = col2.selectbox("Chế độ xuất (Export Mode)", ["Bản nội bộ (local)", "Bản an toàn cho cloud (cloud_safe)"], key="study_export_mode_select")
                
                target_map = {
                    "Gemini": "gemini",
                    "GPT": "gpt",
                    "Copilot": "copilot",
                    "NotebookLM-safe summary": "notebooklm_safe",
                    "Local AI (with local_only)": "local_ai"
                }
                export_map = {
                    "Bản nội bộ (local)": "local",
                    "Bản an toàn cho cloud (cloud_safe)": "cloud_safe"
                }
                
                if st.button("Tạo prompt ôn bài", key="study_prompt_btn"):
                    prompt = build_study_pack_prompt(selected_nb_id, target_map[target], export_map[export_mode], limit=8)
                    st.text_area("Prompt để copy (Gói prompt ôn bài đã sinh)", value=prompt, height=200, key="study_prompt_output")
                    st.markdown("**Xem trước Prompt (để đọc dễ dàng):**")
                    st.code(prompt, language="markdown")
                    st.success("Đã tạo prompt ôn bài thành công! Hãy copy đoạn prompt trên đưa vào AI của bạn để tạo bài ôn tập.")
                
    with tab5:
        st.subheader("Bản đồ quan hệ Sổ tri thức")
        if not notebooks:
            st.info("Chưa có Sổ tri thức để vẽ bản đồ.")
        else:
            from aios_habit.notebook_graph import build_notebook_mermaid_graph
            from aios_habit.notebook_import_store import load_bridge_imports
            from aios_habit.study_store import load_study_cards
            from aios_habit.knowledge_map_view import (
                build_saved_graph_view,
                graph_to_node_table,
                graph_to_edge_table,
                graph_to_pretty_mermaid
            )
            
            selected_nb_id = st.selectbox("Chọn phạm vi hiển thị bản đồ", ["Tất cả sổ tri thức"] + list(nb_opts.keys()), format_func=lambda x: "Tất cả sổ tri thức" if x == "Tất cả sổ tri thức" else nb_opts[x], key="graph_nb_select")
            
            graph_nb = None if selected_nb_id == "Tất cả sổ tri thức" else selected_nb_id
            
            # Load graph imports
            raw_saved = load_bridge_imports(graph_nb)
            if graph_nb is None:
                ws_nb_ids = {n.notebook_id for n in notebooks}
                saved_graphs = [
                    imp for imp in raw_saved
                    if imp.import_type in ("knowledge_graph_json", "mermaid_graph") and imp.notebook_id in ws_nb_ids
                ]
            else:
                saved_graphs = [
                    imp for imp in raw_saved
                    if imp.import_type in ("knowledge_graph_json", "mermaid_graph")
                ]
                
            # Stats calculation
            sources_list = load_sources()
            ws_nbs = notebooks
            if graph_nb:
                ws_nbs = [n for n in ws_nbs if n.notebook_id == graph_nb]
            ws_nb_ids = {n.notebook_id for n in ws_nbs}
            
            rel_sources = [s for s in sources_list if s.notebook_id in ws_nb_ids]
            
            cases_list = load_cases()
            if graph_nb:
                rel_cases = [c for c in cases_list if graph_nb in getattr(c, "linked_notebook_ids", [])]
            else:
                rel_cases = [c for c in cases_list if any(nb_id in ws_nb_ids for nb_id in getattr(c, "linked_notebook_ids", []))]
                
            rel_case_ids = {c.case_id for c in rel_cases}
            evidence_list = load_evidence()
            rel_evidence = [e for e in evidence_list if e.case_id in rel_case_ids]
            
            study_cards_count = len(load_study_cards(graph_nb))
            
            # Render Section 1: Tổng quan
            st.markdown("### 1. Thống kê tổng quan")
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            col_stat1.metric("Sổ tri thức", len(ws_nbs))
            col_stat2.metric("Tài liệu nguồn", len(rel_sources))
            col_stat3.metric("Thẻ học ôn bài", study_cards_count)
            
            col_stat4, col_stat5, col_stat6 = st.columns(3)
            col_stat4.metric("Hồ sơ liên kết", len(rel_cases))
            col_stat5.metric("Bằng chứng", len(rel_evidence))
            col_stat6.metric("Đồ thị imported", len(saved_graphs))
            
            # Render Section 2: Bản đồ tri thức nghiệp vụ (Semantic & Structural)
            st.write("---")
            st.markdown("### 2. Bản đồ tri thức nghiệp vụ")
            
            from aios_habit.worklens_semantic_map import build_worklens_semantic_graph
            from aios_habit.learning_models import load_learning_cards
            from aios_habit.notebook_graph import build_notebook_structural_dict_graph
            
            # Load learning cards and filter
            learning_cards = load_learning_cards()
            rel_learning = [lc for lc in learning_cards if lc.case_id in rel_case_ids]
            
            # Build semantic graph
            semantic_graph = build_worklens_semantic_graph(
                workspace=active_ws_id,
                notebooks=ws_nbs,
                sources=rel_sources,
                cases=rel_cases,
                evidence=rel_evidence,
                learning_cards=rel_learning,
                bridge_imports=raw_saved
            )
            
            has_real_cases_or_evidence = len(rel_cases) > 0 or len(rel_evidence) > 0 or len(rel_learning) > 0
            
            # Build map options
            map_source_opts = []
            
            # Add semantic map if real data exists
            if has_real_cases_or_evidence:
                map_source_opts.append("Bản đồ nghiệp vụ từ hồ sơ/sổ tri thức hiện có")
            else:
                map_source_opts.append("Chưa đủ dữ liệu nghiệp vụ để dựng bản đồ tri thức. Đang hiển thị sơ đồ cấu trúc.")
                
            # Add NotebookLM imports options
            for g in saved_graphs:
                map_source_opts.append(f"Đồ thị nhập từ NotebookLM: {g.title} ({g.import_id})")
                
            # Add structural graph option
            map_source_opts.append("Sơ đồ cấu trúc ứng dụng: Workspace → Notebook → Case")
            
            selected_map_source = st.selectbox(
                "Chọn bản đồ hiển thị",
                options=map_source_opts,
                key="selected_map_source"
            )
            
            graph_data = None
            label_kind = ""
            
            if selected_map_source == "Bản đồ nghiệp vụ từ hồ sơ/sổ tri thức hiện có":
                graph_data = semantic_graph
                label_kind = "semantic"
            elif selected_map_source == "Chưa đủ dữ liệu nghiệp vụ để dựng bản đồ tri thức. Đang hiển thị sơ đồ cấu trúc.":
                graph_data = build_notebook_structural_dict_graph(workspace_id=active_ws_id, notebook_id=graph_nb)
                label_kind = "insufficient"
            elif selected_map_source == "Sơ đồ cấu trúc ứng dụng: Workspace → Notebook → Case":
                graph_data = build_notebook_structural_dict_graph(workspace_id=active_ws_id, notebook_id=graph_nb)
                label_kind = "structural"
            else:
                # Find matching import
                import_id = None
                for g in saved_graphs:
                    if f"({g.import_id})" in selected_map_source:
                        import_id = g.import_id
                        break
                if import_id:
                    selected_graph = next(g for g in saved_graphs if g.import_id == import_id)
                    graph_data = build_saved_graph_view(selected_graph)
                    if selected_graph.import_id == "IMP-C707A8DF":
                        label_kind = "sample"
                    else:
                        label_kind = "imported"
                else:
                    graph_data = {"nodes": [], "edges": []}
                    label_kind = "empty"
                    
            # Render labels
            if label_kind == "semantic":
                st.success("🗺️ Bản đồ nghiệp vụ từ hồ sơ/sổ tri thức hiện có")
            elif label_kind == "insufficient":
                st.warning("⚠️ Chưa đủ dữ liệu nghiệp vụ để dựng bản đồ tri thức. Đang hiển thị sơ đồ cấu trúc.")
            elif label_kind == "sample":
                st.info("💡 Dữ liệu mẫu — chưa phải hồ sơ thật")
            elif label_kind == "imported":
                st.info("📥 Đồ thị nhập từ NotebookLM — kiểm tra lại trước khi kết luận")
            elif label_kind == "structural":
                st.info("⚙️ Đang hiển thị sơ đồ cấu trúc hệ thống")
                
            # Display mode selector
            display_mode = st.selectbox(
                "Kiểu hiển thị",
                ["Bản đồ thẻ HTML", "Bảng + Mermaid", "Cả hai"],
                index=0,
                key="map_display_mode"
            )
            
            nodes_list = graph_data.get("nodes", []) if graph_data else []
            
            # 1. Render HTML card map
            if display_mode in ("Bản đồ thẻ HTML", "Cả hai") and graph_data:
                from aios_habit.knowledge_map_html import graph_to_html_map
                import streamlit.components.v1 as components
                
                html_str = graph_to_html_map(graph_data, max_nodes=80, max_edges=160)
                components.html(html_str, height=700, scrolling=True)
                
            # 2. Render Bảng + Mermaid
            if display_mode in ("Bảng + Mermaid", "Cả hai") and graph_data:
                if len(nodes_list) > 50:
                    st.warning(f"⚠️ Đồ thị chứa {len(nodes_list)} nút. Bản xem thử Mermaid được giới hạn tối đa 50 nút đầu tiên để tránh lag.")
                
                pretty_mermaid = graph_to_pretty_mermaid(graph_data, max_nodes=50)
                st.markdown("#### Bản xem thử trực quan (Mermaid)")
                st.code(pretty_mermaid, language="mermaid")
                
                # Show full tables
                st.markdown("#### Bảng danh sách các nút (Nodes)")
                nodes_table = graph_to_node_table(graph_data)
                if nodes_table:
                    st.dataframe(nodes_table)
                else:
                    st.info("Không có dữ liệu nút.")
                    
                st.markdown("#### Bảng danh sách các quan hệ (Edges)")
                edges_table = graph_to_edge_table(graph_data)
                if edges_table:
                    st.dataframe(edges_table)
                else:
                    st.info("Không có dữ liệu quan hệ.")
                    
            st.info(
                "Bản đồ hiện dùng renderer HTML nhẹ, không dùng thư viện ngoài. "
                "Nếu sau này cần nâng cấp renderer, sẽ mở spike riêng sau khi daily flow ổn."
            )


def main():
    init_store()
    init_workspace_store()
    init_source_store()
    
    st.sidebar.title("AIOS Case Cockpit")
    
    # 1. Workspace Selection
    workspaces = load_workspaces()
    ws_options = {w.workspace_id: f"{w.name} ({w.workspace_id})" for w in workspaces}
    
    if "active_workspace_id" not in st.session_state:
        st.session_state.active_workspace_id = "default"
        
    if st.session_state.active_workspace_id not in ws_options:
        st.session_state.active_workspace_id = "default"
        
    active_ws_id = st.sidebar.selectbox(
        "Không gian làm việc (Workspace - Không gian làm việc)",
        options=list(ws_options.keys()),
        index=list(ws_options.keys()).index(st.session_state.active_workspace_id),
        key="active_workspace_id",
        format_func=lambda x: ws_options[x]
    )
    
    # Workspace management expander
    with st.sidebar.expander("🛠️ Quản lý Workspace"):
        ws_name = st.text_input("Tên Workspace mới", key="new_ws_name")
        ws_desc = st.text_area("Mô tả Workspace", key="new_ws_desc")
        if st.button("Tạo Workspace"):
            if ws_name.strip():
                import uuid
                new_ws_id = f"WS-{str(uuid.uuid4())[:8].upper()}"
                new_ws = Workspace(
                    workspace_id=new_ws_id,
                    name=ws_name.strip(),
                    description=ws_desc.strip()
                )
                save_workspace(new_ws)
                st.success(f"Đã tạo Workspace: {ws_name}")
                st.rerun()
            else:
                st.error("Tên Workspace không được để trống.")
                
    st.sidebar.markdown("---")
    
    # 2. Category selection (5 main navigation groups)
    main_categories = {
        "🏠 Tổng quan & Bắt đầu": "home",
        "📚 Sổ tri thức (Notebook - Sổ tri thức)": "notebook",
        "📁 Hồ sơ sự việc (Case - Hồ sơ sự việc)": "case",
        "📤 Xuất kết quả": "export",
        "🎓 Học nghề & An toàn": "learning"
    }
    
    if "active_main_category" not in st.session_state:
        st.session_state.active_main_category = "🏠 Tổng quan & Bắt đầu"
        
    if st.session_state.active_main_category not in main_categories:
        st.session_state.active_main_category = "🏠 Tổng quan & Bắt đầu"
        
    selected_category = st.sidebar.radio(
        "Phân vùng chức năng",
        options=list(main_categories.keys()),
        index=list(main_categories.keys()).index(st.session_state.active_main_category),
        key="active_main_category"
    )
    
    # Reset case choice if switching workspaces
    active_case = get_active_case()
    if active_case and active_case.workspace_id != st.session_state.active_workspace_id:
        if "active_case_id" in st.session_state:
            del st.session_state.active_case_id
            active_case = None
            
    # Show active case in sidebar
    if active_case:
        st.sidebar.markdown("---")
        st.sidebar.info(f"📁 **Hồ sơ đang xử lý:**\n**{active_case.title}**\n({active_case.case_id})")
        
    # 3. Main Area - Render based on category and sub-tabs
    if selected_category == "🏠 Tổng quan & Bắt đầu":
        tab1, tab2 = st.tabs(["☀️ Tóm tắt hôm nay", "⚡ Nhập nhanh sự việc"])
        with tab1:
            page_today_brief()
        with tab2:
            page_quick_intake()
            
    elif selected_category == "📚 Sổ tri thức (Notebook - Sổ tri thức)":
        page_notebooks()
        
    elif selected_category == "📁 Hồ sơ sự việc (Case - Hồ sơ sự việc)":
        tab1, tab2, tab3, tab4 = st.tabs(["🗂️ Hồ sơ sự việc", "📎 Thêm bằng chứng", "🗺️ Bản đồ sự việc", "🚀 Việc cần làm tiếp"])
        with tab1:
            page_cases()
        with tab2:
            page_add_evidence()
        with tab3:
            page_case_map()
        with tab4:
            page_next_actions()
            
    elif selected_category == "📤 Xuất kết quả":
        tab1, tab2 = st.tabs(["🤖 Gói câu lệnh cho AI", "🤝 Bàn giao"])
        with tab1:
            page_prompt_pack()
        with tab2:
            page_handover()
            
    elif selected_category == "🎓 Học nghề & An toàn":
        tab1, tab2 = st.tabs(["🧠 Rút bài học", "🛡️ Kiểm tra an toàn"])
        with tab1:
            page_learning_memory()
        with tab2:
            page_audit()

def launch():
    import subprocess
    subprocess.run([sys.executable, "-m", "streamlit", "run", __file__])

if __name__ == "__main__":
    if "streamlit" not in sys.modules:
        launch()
    else:
        main()
