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
    assert "Đang dùng chế độ local" in cockpit_source
    assert "không gọi AI ngoài" in cockpit_source
    assert "Tạo prompt đối chiếu NotebookLM" in cockpit_source


def test_case_cockpit_mom_adapter_label_is_not_duplicated_by_persisted_notebooks():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert "user_notebooks = [n for n in notebooks if n.name.strip() != MOM_NOTEBOOK_NAME]" in cockpit_source
    assert "nb_opts.update({n.notebook_id: n.name for n in user_notebooks})" in cockpit_source
    assert 'st.session_state["unified_nb_select"] = MOM_NOTEBOOK_ID' not in cockpit_source
