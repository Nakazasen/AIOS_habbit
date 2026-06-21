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
