from pathlib import Path

from aios_habit.knowledge_map_html import graph_to_case_board_html, graph_to_html_map


case_graph = {
    "nodes": [
        {
            "id": "case-1",
            "label": "Lỗi xuất hàng U002",
            "type": "case",
            "description": "Đang điều tra lệch cấu hình khi xuất hàng",
            "confidence": "high",
        },
        {
            "id": "ev-1",
            "label": "Log xuất hàng",
            "type": "evidence",
            "description": "Có mã lỗi U002 trong ca sáng",
            "source_ref": "manual",
            "confidence": "medium",
        },
        {
            "id": "cause-1",
            "label": "Cấu hình thiếu kho đích",
            "type": "cause",
            "description": "Chỉ là giả thuyết, chưa kết luận",
        },
        {
            "id": "learning-1",
            "label": "Bài học: kiểm tra mapping trước",
            "type": "learning",
            "description": "Bài học kinh nghiệm: kiểm tra mapping trước khi chạy batch",
        },
    ],
    "edges": [
        {"from": "case-1", "to": "ev-1", "relation": "HAS_EVIDENCE"},
        {"from": "cause-1", "to": "case-1", "relation": "dẫn_đến"},
        {"from": "learning-1", "to": "case-1", "relation": "LEARNED_FROM"},
    ],
    "meta": {
        "graph_kind": "semantic",
        "uses_sample_data": False,
        "warnings": [],
    },
}


def test_case_board_renders_central_case_and_evidence_relation():
    html_str = graph_to_case_board_html(case_graph)

    assert "Case trung tâm" in html_str
    assert "case-focus" in html_str
    assert "Lỗi xuất hàng U002" in html_str
    assert "Bằng chứng" in html_str
    assert "Log xuất hàng" in html_str
    assert "có bằng chứng" in html_str


def test_learning_card_renders_as_learning_not_generic_document():
    html_str = graph_to_html_map(case_graph)

    assert "learning" in html_str
    assert "Bài học kinh nghiệm" in html_str
    assert "Đối ứng / Bài học / Tài liệu" in html_str


def test_notebooklm_import_is_labeled_as_import_not_verified_semantic():
    graph = {
        "nodes": [{"id": "n1", "label": "Claim từ NotebookLM", "type": "cause"}],
        "edges": [],
        "meta": {
            "graph_kind": "imported",
            "uses_sample_data": False,
            "warnings": [],
        },
    }

    html_str = graph_to_html_map(graph)

    assert "Đồ thị nhập từ NotebookLM" in html_str
    assert "kiểm tra lại trước khi kết luận" in html_str
    assert "Bản đồ nghiệp vụ từ hồ sơ" not in html_str


def test_sample_import_is_marked_not_real_case_file():
    graph = {
        "nodes": [{"id": "n1", "label": "Dữ liệu nhập", "type": "system"}],
        "edges": [],
        "meta": {
            "graph_kind": "imported",
            "uses_sample_data": True,
            "warnings": [],
        },
    }

    html_str = graph_to_html_map(graph)

    assert "Dữ liệu mẫu/import - chưa phải hồ sơ thật" in html_str


def test_structural_graph_remains_separate():
    graph = {
        "nodes": [{"id": "ws-1", "label": "Workspace", "type": "workspace"}],
        "edges": [],
        "meta": {
            "graph_kind": "structural",
            "uses_sample_data": False,
            "warnings": [],
        },
    }

    html_str = graph_to_html_map(graph)

    assert "Sơ đồ cấu trúc ứng dụng" in html_str
    assert "không phải bản đồ nghiệp vụ đã xác minh" in html_str


def test_empty_state_is_honest_and_does_not_pretend_pass():
    html_str = graph_to_html_map({})

    assert "Chưa đủ dữ liệu nghiệp vụ để dựng bản đồ tri thức" in html_str
    assert "Hãy tạo Case/Evidence hoặc chọn đồ thị nhập để xem trước" in html_str
    assert "PASS" not in html_str


def test_html_map_escapes_html():
    evil_graph = {
        "nodes": [
            {
                "id": "node-1",
                "label": "Case <script>alert(1)</script>",
                "type": "case",
                "description": "<evil>",
                "source_ref": "<source>",
            }
        ],
        "edges": [
            {"from": "node-1", "to": "node-1", "relation": "<rel>", "description": "<desc>"}
        ],
        "meta": {"graph_kind": "semantic", "uses_sample_data": False, "warnings": []},
    }
    html_str = graph_to_html_map(evil_graph)

    assert "<script" not in html_str.lower()
    assert "Case &lt;script&gt;alert(1)&lt;/script&gt;" in html_str
    assert "&lt;evil&gt;" in html_str
    assert "&lt;source&gt;" in html_str
    assert "&lt;rel&gt;" in html_str
    assert "&lt;desc&gt;" in html_str


def test_html_map_no_external_scripts_or_urls():
    html_str = graph_to_html_map(case_graph)
    html_lower = html_str.lower()

    assert "<script" not in html_lower
    assert "http://" not in html_lower
    assert "https://" not in html_lower


def test_limits_nodes_and_edges_with_warnings():
    graph = {
        "nodes": [
            {"id": "case-1", "label": "Case 1", "type": "case"},
            {"id": "ev-1", "label": "Evidence 1", "type": "evidence"},
            {"id": "ev-2", "label": "Evidence 2", "type": "evidence"},
        ],
        "edges": [
            {"from": "case-1", "to": "ev-1", "relation": "HAS_EVIDENCE"},
            {"from": "case-1", "to": "ev-2", "relation": "HAS_EVIDENCE"},
        ],
        "meta": {"graph_kind": "semantic", "uses_sample_data": False, "warnings": []},
    }

    html_str = graph_to_html_map(graph, max_nodes=2, max_edges=1)

    assert "Case 1" in html_str
    assert "Evidence 1" in html_str
    assert "Evidence 2" not in html_str
    assert "Số nút vượt quá 2" in html_str
    assert "Số liên kết vượt quá 1" in html_str


def test_unknown_node_type_falls_back_to_other():
    graph = {
        "nodes": [{"id": "node-unknown", "label": "Unknown Item", "type": "super_weird_type"}],
        "edges": [],
        "meta": {"graph_kind": "structural", "uses_sample_data": False, "warnings": []},
    }
    html_str = graph_to_html_map(graph)

    assert "other" in html_str
    assert "super_weird_type" not in html_str
    assert "Unknown Item" in html_str


def test_renderer_source_has_no_lsu_or_drum_default_data():
    renderer_source = Path("src/aios_habit/knowledge_map_html.py").read_text(encoding="utf-8")

    assert "LSU" not in renderer_source
    assert "Drum" not in renderer_source
