import streamlit as st
import json
import os
import sys
from pathlib import Path
from datetime import datetime

from aios_habit.case_models import Case, EvidenceItem
from aios_habit.case_store import load_cases, load_evidence, save_case, save_evidence, init_store
from aios_habit.case_ingest import ingest_excel, ingest_csv, save_uploaded_file
from aios_habit.case_graph import generate_case_mermaid
from aios_habit.case_actions import generate_next_actions
from aios_habit.case_prompt import build_prompt_pack
from aios_habit.case_audit import audit_case_cockpit_state

st.set_page_config(page_title="AIOS Case Cockpit v0.1", layout="wide")

def nav_to_page(page_name):
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
    cases = load_cases()
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
    cases = load_cases()
    
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
                    c = Case(case_id=f"CASE-{str(uuid.uuid4())[:8].upper()}", title=title.strip(), priority=priority, privacy_level=privacy)
                    save_case(c)
                    st.success("Đã tạo hồ sơ sự việc!")
                    st.rerun()
                 
    st.subheader("Chọn hồ sơ sự việc")
    status_map = {"open": "Mở", "investigating": "Đang điều tra", "waiting": "Đang chờ", "resolved": "Đã giải quyết", "archived": "Đã lưu trữ"}
    case_opts = {c.case_id: f"{c.case_id} - {c.title} (Trạng thái: {status_map.get(c.status, c.status)})" for c in cases}
    selected_id = st.selectbox("Hồ sơ đang hoạt động", options=list(case_opts.keys()), format_func=lambda x: case_opts[x])
    
    if selected_id:
        st.session_state.active_case_id = selected_id
        active_case = next(c for c in cases if c.case_id == selected_id)
        st.write("---")
        st.subheader("Chi tiết hồ sơ")
        
        with st.form("edit_case"):
            sit = st.text_area("Tình huống hiện tại (Current Situation)", value=active_case.current_situation, height=150)
            stat = st.selectbox("Trạng thái (Status)", ["open", "investigating", "waiting", "resolved", "archived"], index=["open", "investigating", "waiting", "resolved", "archived"].index(active_case.status), format_func=lambda x: {"open": "Mở (open)", "investigating": "Đang điều tra (investigating)", "waiting": "Đang chờ (waiting)", "resolved": "Đã giải quyết (resolved)", "archived": "Đã lưu trữ (archived)"}[x])
            pri = st.selectbox("Độ ưu tiên (Priority)", ["low", "normal", "high", "critical"], index=["low", "normal", "high", "critical"].index(active_case.priority), format_func=lambda x: {"low": "Thấp (low)", "normal": "Bình thường (normal)", "high": "Cao (high)", "critical": "Khẩn cấp (critical)"}[x])
            
            if st.form_submit_button("Lưu thay đổi hồ sơ"):
                active_case.current_situation = sit
                active_case.status = stat
                active_case.priority = pri
                active_case.updated_at = datetime.now().isoformat()
                save_case(active_case)
                st.success("Đã cập nhật hồ sơ!")

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

def main():
    init_store()
    if "page" not in st.session_state:
        st.session_state.page = "Nhập nhanh sự việc"

    st.sidebar.title("AIOS Case Cockpit")
    pages = {
        "Nhập nhanh sự việc": page_quick_intake,
        "Tóm tắt hôm nay": page_today_brief,
        "Hồ sơ sự việc": page_cases,
        "Thêm bằng chứng": page_add_evidence,
        "Bản đồ sự việc": page_case_map,
        "Việc cần làm tiếp": page_next_actions,
        "Gói câu lệnh cho AI": page_prompt_pack,
        "Bàn giao": page_handover,
        "Rút bài học": page_learning_memory,
        "Kiểm tra an toàn": page_audit,
    }
    
    # Sử dụng key="page" để liên kết trực tiếp với st.session_state.page và đảm bảo chuyển trang tức thì chỉ với 1 click
    selected = st.sidebar.radio("Điều hướng", list(pages.keys()), key="page")
    
    pages[selected]()

def launch():
    import subprocess
    subprocess.run([sys.executable, "-m", "streamlit", "run", __file__])

if __name__ == "__main__":
    if "streamlit" not in sys.modules:
        launch()
    else:
        main()
