from pathlib import Path


def test_case_cockpit_ui_copy_does_not_name_heavy_graph_libraries():
    cockpit_source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")

    assert "Cytoscape" not in cockpit_source
    assert "React Flow" not in cockpit_source
    assert "renderer HTML nhẹ" in cockpit_source
    assert "không dùng thư viện ngoài" in cockpit_source
