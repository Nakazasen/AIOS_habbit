from pathlib import Path

FORBIDDEN_WORDS = [
    "RAG",
    "node",
    "edge",
    "claim",
    "citation",
    "provider router",
    "vector",
    "Mermaid",
    "local_only",
    "embedding",
    "chunk",
    "retrieval",
    "prompt pack"
]

def test_workspace_chat_ui_copy_no_forbidden_words():
    # Read files
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    ui_source = Path("src/aios_habit/workspace_chat_ui.py").read_text(encoding="utf-8")
    
    # We check that these words do not appear in any user-facing display string
    # To be safe, we check that they do not appear at all in the workspace_chat_ui.py and workspace_chat_app.py files
    for word in FORBIDDEN_WORDS:
        # Case insensitive check
        assert word.lower() not in app_source.lower(), f"Forbidden word '{word}' found in workspace_chat_app.py"
        assert word.lower() not in ui_source.lower(), f"Forbidden word '{word}' found in workspace_chat_ui.py"

def test_workspace_chat_ui_vietnamese_labels():
    ui_source = Path("src/aios_habit/workspace_chat_ui.py").read_text(encoding="utf-8")
    
    # Verify presence of required Vietnamese UI copy
    assert "Sổ tài liệu của tôi" in ui_source
    assert "Mở sổ" in ui_source
    assert "Cuộc trò chuyện" in ui_source
    assert "Tạo cuộc trò chuyện mới" in ui_source
    assert "Nguồn tạm trong cuộc trò chuyện" in ui_source
    assert "Chưa lưu lâu dài" in ui_source
    assert "Chỉ dùng trong cuộc trò chuyện này" in ui_source
    assert "Trả lời chính" in ui_source
    assert "Nguồn chứng minh" in ui_source
    assert "Ý cần kiểm lại" in ui_source
    assert "Việc nên làm tiếp" in ui_source
    assert "Lưu vào hồ sơ" in ui_source
    assert "Xem vì sao AIOS kết luận như vậy" in ui_source
