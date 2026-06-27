from pathlib import Path


def test_case_cockpit_ui_copy_does_not_name_heavy_graph_libraries():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert "Cytoscape" not in cockpit_source
    assert "React Flow" not in cockpit_source
    assert "renderer HTML nhẹ" in cockpit_source
    assert "không dùng thư viện ngoài" in cockpit_source


def test_case_cockpit_map_selector_keeps_verified_map_first():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert 'business_map_label = "Bản đồ nghiệp vụ"' in cockpit_source
    assert 'import_map_label = "Đồ thị nhập từ NotebookLM"' in cockpit_source
    assert 'structural_map_label = "Sơ đồ cấu trúc ứng dụng"' in cockpit_source
    assert "map_source_opts = [business_map_label, import_map_label, structural_map_label]" in cockpit_source
    assert "Dữ liệu mẫu — chưa phải hồ sơ thật" in cockpit_source


def test_case_cockpit_unifies_mom_into_knowledge_notebook():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert 'MOM_NOTEBOOK_ID = "mom"' in cockpit_source
    assert 'MOM_NOTEBOOK_NAME = "Hệ thống MOM"' in cockpit_source
    assert '"🏭 MOM Pilot / Tài liệu MOM thật": "mom_pilot"' not in cockpit_source
    assert 'elif selected_category == "🏭 MOM Pilot / Tài liệu MOM thật"' not in cockpit_source
    assert '"📚 Sổ tri thức": "notebook"' in cockpit_source
    assert '"🏠 Tổng quan": "home"' in cockpit_source


def test_case_cockpit_local_qa_does_not_require_provider_for_mom():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert "generate_mom_grounded_answer" in cockpit_source
    assert "search_mom_index" in cockpit_source
    assert "Chưa cấu hình AI provider. Hãy cấu hình biến môi trường" not in cockpit_source
    assert "AIOS tự bảo vệ tài liệu công ty/mật" in cockpit_source
    assert "không gửi ra ngoài" in cockpit_source
    assert "Tạo prompt đối chiếu" in cockpit_source


def test_case_cockpit_mom_adapter_label_is_not_duplicated_by_persisted_notebooks():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert "user_notebooks = [n for n in notebooks if n.name.strip() != MOM_NOTEBOOK_NAME]" in cockpit_source
    assert "nb_opts.update({n.notebook_id: n.name for n in user_notebooks})" in cockpit_source
    assert 'st.session_state["unified_nb_select"] = MOM_NOTEBOOK_ID' not in cockpit_source


def test_case_cockpit_no_raw_local_only_in_main_ui_labels():
    """Main UI labels must not show raw 'local_only' as a visible label.
    It may appear as a Python value or in Chi tiết kỹ thuật expanders only."""
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    # These exact patterns indicate raw technical jargon was shown to the user.
    # format_func display strings must NOT contain (local_only) suffix.
    assert '"Chỉ lưu cục bộ (local_only)"' not in cockpit_source
    assert '"Cục bộ (local_only)"' not in cockpit_source
    # Visible metric label must not say "Local-only"
    assert 'metric("Local-only"' not in cockpit_source


def test_case_cockpit_no_deterministic_in_user_visible_text():
    """The word 'deterministic' should not appear in user-facing st.info/st.warning."""
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    # Allow 'deterministically' in code comments but not in st.info/st.warning strings.
    import re
    user_facing = re.findall(r'st\.(info|warning|error|success)\(.*?deterministic.*?\)', cockpit_source)
    assert len(user_facing) == 0, f"Found 'deterministic' in user-facing messages: {user_facing}"


def test_case_cockpit_no_raw_provider_in_main_labels():
    """Main UI must say 'bộ AI' not 'AI Provider'."""
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert '"Đã cấu hình AI Provider"' not in cockpit_source
    assert 'AIOS provider' not in cockpit_source


def test_case_cockpit_mom_pilot_top_level_absent():
    """MOM Pilot must not be a top-level sidebar category."""
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert '"🏭 MOM Pilot' not in cockpit_source


def test_case_cockpit_no_post_widget_session_mutation():
    """Must not set session_state for a widget key after widget is created."""
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert 'st.session_state["unified_nb_select"]' not in cockpit_source
    assert 'st.session_state["qa_nb_select"]' not in cockpit_source


def test_case_cockpit_notebook_upload_success_survives_rerun():
    """Multi-file upload success must remain visible after Streamlit reruns."""
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert 'st.session_state["notebook_upload_success"]' in cockpit_source
    assert 'st.success(f"Đã nạp thành công {upload_success[\'count\']} tài liệu.")' in cockpit_source
    assert 'for filename in upload_success.get("filenames", []):' in cockpit_source
    assert 'st.write(f"- {filename}")' in cockpit_source
    assert 'st.caption("Bấm Cập nhật mục lục tài liệu hoặc hỏi ngay trong tab Hỏi đáp.")' in cockpit_source


def test_case_cockpit_upload_is_visible_in_document_sources_section():
    """Section B owns the uploader; the source-view tab is not the upload entry point."""
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")
    section_b = cockpit_source.index('st.markdown("#### B. Kéo thả / chọn nhiều file")')
    section_c = cockpit_source.index('st.markdown("#### C. Tạo Sổ tri thức mới")')
    view_tab = cockpit_source.index("with tab3:", section_c)
    qa_tab = cockpit_source.index("with tab2:", view_tab)

    assert 'st.file_uploader(' in cockpit_source[section_b:section_c]
    assert 'key="notebook_source_files"' in cockpit_source[section_b:section_c]
    assert 'st.file_uploader(' not in cockpit_source[view_tab:qa_tab]


def test_case_cockpit_section_b_is_honest_for_mom():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert "mom_file_upload_disabled = selected_nb_id == MOM_NOTEBOOK_ID" in cockpit_source
    assert "disabled=mom_file_upload_disabled" in cockpit_source
    assert "Sổ Hệ thống MOM hiện nạp bằng cả thư mục" in cockpit_source


def test_case_cockpit_upload_refreshes_index_and_view_lists_original_filenames():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert "build_notebook_index(selected_nb_id)" in cockpit_source
    assert '"Chọn sổ tri thức để xem"' in cockpit_source
    assert 'st.write(f"- {source.original_filename}")' in cockpit_source


def test_case_cockpit_exposes_working_mom_answer_to_case_action():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert '"Tạo hồ sơ từ câu trả lời này"' in cockpit_source
    assert 'key="mom_answer_to_case_btn"' in cockpit_source
    assert "create_case_draft_from_qa_answer" in cockpit_source
    assert 'st.session_state["last_mom_qa_result"]' in cockpit_source
    assert 'st.success(f"Đã tạo hồ sơ: {created[\'case_id\']}")' in cockpit_source
    assert '"Mở hồ sơ sự việc"' in cockpit_source


def test_case_cockpit_mom_sources_use_readable_primary_labels():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert "Tin cậy {confidence_vn} · Không gửi ra ngoài" in cockpit_source
    assert 'with st.expander(f"Chi tiết nguồn {i}"' in cockpit_source
    assert "`{ref['chunk_id']}`" not in cockpit_source


def test_case_cockpit_uses_stable_case_selector_for_switching():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert 'key="case_selector"' in cockpit_source
    assert 'st.session_state["case_selector"] = result["case_id"]' in cockpit_source
    assert "index=selected_idx" not in cockpit_source


def test_case_cockpit_exposes_real_local_ai_bridge_copy():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert '"Tự động chọn AI tốt nhất"' in cockpit_source
    assert '"Chỉ dùng trong máy"' in cockpit_source
    assert '"Endpoint cục bộ"' in cockpit_source
    assert '"Tên mô hình"' in cockpit_source
    assert '"Kiểm tra kết nối AI cục bộ"' in cockpit_source
    assert "Antigravity direct bridge: chưa phát hiện API runtime" in cockpit_source
    assert "Antigravity IDE chỉ gọi trực tiếp được" in cockpit_source
    assert "route_answer" in cockpit_source
    assert "providers_from_env_or_session" in cockpit_source
    assert "local_ai_endpoint_stub" not in cockpit_source
    assert "local_ai_test_stub" not in cockpit_source



def test_case_cockpit_vietnamese_safety_modes_visible():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert '"Mức an toàn"' in cockpit_source
    assert "SAFETY_MODE_COMPANY" in cockpit_source
    assert "SAFETY_MODE_NORMAL" in cockpit_source
    assert "get_safety_mode_options()" in cockpit_source
    assert "AIOS sẽ tự chọn cách xử lý an toàn nhất" in cockpit_source


def test_case_cockpit_route_log_copy_visible():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert "Nhật ký AI đã dùng" in cockpit_source or "format_route_log_for_ui" in cockpit_source
    assert "Cách xử lý" in cockpit_source
    assert "Có gửi ra ngoài không" in cockpit_source
    assert "Nguồn AI" in cockpit_source
    assert "Có tự đổi nguồn không" in cockpit_source or "Tự đổi nguồn" in cockpit_source


def test_case_cockpit_no_raw_router_terms_in_main_source():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert "redacted_export" not in cockpit_source
    assert "cloud_allowed" not in cockpit_source
    assert "provider policy" not in cockpit_source.lower()
    assert "route policy" not in cockpit_source.lower()


def test_case_cockpit_qna_modes_are_router_1_copy():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert "Tự động chọn AI tốt nhất" in cockpit_source
    assert "Chỉ dùng trong máy" in cockpit_source
    assert "Tạo prompt đối chiếu" in cockpit_source
    assert "AIOS tự chọn nguồn phù hợp" in cockpit_source



def test_case_cockpit_provider_catalog_copy_visible():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert "Nguồn AI" in cockpit_source
    provider_catalog_source = Path("src/aios_habit/provider_catalog.py").read_text(encoding="utf-8")
    assert "Nguồn dùng trong máy / nội bộ" in provider_catalog_source
    assert "Nguồn AI cho tài liệu thường" in provider_catalog_source
    assert "Nguồn tự cấu hình" in provider_catalog_source
    assert "Tài liệu công ty/mật không gửi ra ngoài" in cockpit_source
    assert "Tài liệu thường có thể dùng toàn bộ nguồn AI đã cấu hình" in cockpit_source
    assert "Ollama" in cockpit_source or "get_provider_catalog" in cockpit_source
    assert "Gemini" in provider_catalog_source


def test_provider_catalog_raw_router_terms_not_visible_in_main_ui():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert "provider policy" not in cockpit_source.lower()
    assert "route policy" not in cockpit_source.lower()
    assert "cloud_allowed" not in cockpit_source
    assert "redacted_export" not in cockpit_source


def test_case_cockpit_provider_health_copy_visible_and_secret_safe():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")
    provider_health_source = Path("src/aios_habit/provider_health.py").read_text(encoding="utf-8")
    joined = cockpit_source + provider_health_source

    assert "Tình trạng nguồn AI" in cockpit_source
    assert "provider_health_table_for_ui" in cockpit_source
    assert "Sẵn sàng" in provider_health_source
    assert "Chưa cấu hình" in provider_health_source
    assert "Đang tạm nghỉ" in provider_health_source
    assert "Bị tắt do lỗi xác thực" in provider_health_source
    assert "Tài liệu công ty/mật vẫn không gửi ra ngoài" in cockpit_source
    assert ("sk" + "-") not in joined
    assert ("AI" + "za") not in joined
    assert ("nvapi" + "-") not in joined
    assert ("Authorization" + ": Bearer") not in joined



def test_case_cockpit_router3_route_log_wiring():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")
    assert "RouterRequest" in cockpit_source
    assert "route_answer" in cockpit_source
    assert "route_summary_vi" in cockpit_source
    assert "Nhật ký AI đã dùng" in cockpit_source or "format_route_log_for_ui" in cockpit_source
    assert "Có gửi ra ngoài không" in cockpit_source
    assert "Có tự đổi nguồn không" in cockpit_source or "Tự đổi nguồn" in cockpit_source or "Tự đổi nguồn" in cockpit_source
    assert "provider policy" not in cockpit_source.lower()
    assert "route policy" not in cockpit_source.lower()



def test_case_cockpit_router4_route_log_polish_copy():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")
    assert "Chi tiết các lần thử" in cockpit_source
    assert "Có gửi ra ngoài không" in cockpit_source
    assert "Tự đổi nguồn" in cockpit_source
    assert "Tài liệu này được xử lý theo chế độ công ty/mật nên không gửi ra ngoài" in cockpit_source
    assert "Tài liệu thường: AIOS được phép dùng nguồn AI đã cấu hình" in cockpit_source
    assert "Chưa có nguồn AI phù hợp hoặc nguồn AI lỗi" in cockpit_source
    assert "format_route_log_for_ui" in cockpit_source
    assert "provider policy" not in cockpit_source.lower()
    assert "route policy" not in cockpit_source.lower()



def test_case_cockpit_prompt_comparison_uses_safe_redacted_prompt():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")
    assert 'build_notebook_question_prompt(selected_nb_id, question, "external_review", "cloud_safe")' in cockpit_source
    assert 'build_notebook_question_prompt(selected_nb_id, question, "local_ai", "local")' not in cockpit_source


def test_case_cockpit_daily_flow_hardening_copy_visible_and_safe():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert "Luồng hôm nay" in cockpit_source
    assert "Việc tiếp theo" in cockpit_source
    assert "Đã tạo hồ sơ:" in cockpit_source
    assert "Tóm tắt tuyến AI đã lưu vào hồ sơ" in cockpit_source
    assert "Có gửi ra ngoài không" in cockpit_source
    assert "Nguồn AI đã dùng" in cockpit_source
    assert "Có dùng dự phòng cục bộ không" in cockpit_source
    assert "Tài liệu công ty/mật sẽ không gửi ra ngoài" in cockpit_source
    assert "API key" not in "\n".join(
        line for line in cockpit_source.splitlines() if "Luồng hôm nay" in line or "Tóm tắt tuyến AI" in line
    )
