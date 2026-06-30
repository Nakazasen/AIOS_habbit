import pytest

def test_visual_map_case_cockpit_interaction_labels():
    with open("src/aios_habit/case_cockpit.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check if the necessary Vietnamese labels are present
    assert "Bản đồ tri thức công việc" in content
    assert "Tóm tắt bản đồ" in content
    assert "Số nút" in content
    assert "Số quan hệ" in content
    assert "Bằng chứng còn thiếu" in content
    assert "Rủi ro / claim cần kiểm" in content
    assert "Việc tiếp theo" in content
    assert "Chọn góc nhìn" in content
    assert "Bản đồ hồ sơ hiện tại" in content
    assert "Bản đồ bằng chứng" in content
    assert "Bản đồ hành động" in content
    assert "Bản đồ bài học" in content
    assert "Lọc theo loại nút" in content
    assert "Lọc theo loại quan hệ" in content
    assert "Lọc theo mức riêng tư" in content
    assert "Lọc theo độ tin cậy" in content
    assert "Tìm trong bản đồ" in content
    assert "Chọn nút để xem chi tiết" in content
    assert "Chọn quan hệ để xem lý do" in content
    assert "Bằng chứng liên quan" in content
    assert "Bài học tái sử dụng" in content
    assert "Xuất JSON local" in content
    assert "Xuất Mermaid an toàn" in content
    assert "Tóm tắt cho owner" in content
    assert "Dữ liệu local_only chỉ dùng trong máy này" in content

def test_no_forbidden_dependencies():
    with open("src/aios_habit/case_cockpit.py", "r", encoding="utf-8") as f:
        content = f.read()
        
    assert "react_flow" not in content.lower()
    assert "cytoscape" not in content.lower()
    assert "d3" not in content.lower()
    assert "NotebookLM replacement" not in content
    assert "P1.0 opened" not in content
    assert "manufacturing-only" not in content

def test_no_cli_required():
    with open("src/aios_habit/case_cockpit.py", "r", encoding="utf-8") as f:
        content = f.read()
    # Ensure there is no os.system("py -3 -m aios_habit.cli visual-map") call
    assert "py -3 -m aios_habit.cli visual-map" not in content
