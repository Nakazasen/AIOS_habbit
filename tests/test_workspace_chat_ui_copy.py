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
    SEMANTIC_FORBIDDEN = [
        "phân tích đối chiếu",
        "khớp hoàn toàn",
        "khớp với nguồn",
        "nguồn chứng minh",
        "AIOS đã phân tích",
        "AIOS đã đối chiếu",
        "AIOS đã trích dẫn",
        "Kết luận từ tài liệu",
        "Dựa trên tài liệu"
    ]

    for word in FORBIDDEN_WORDS:
        assert word.lower() not in app_source.lower(), f"Forbidden word '{word}' found in workspace_chat_app.py"
        assert word.lower() not in ui_source.lower(), f"Forbidden word '{word}' found in workspace_chat_ui.py"

    for word in SEMANTIC_FORBIDDEN:
        assert word.lower() not in app_source.lower(), f"Semantic forbidden word/phrase '{word}' found in workspace_chat_app.py"
        assert word.lower() not in ui_source.lower(), f"Semantic forbidden word/phrase '{word}' found in workspace_chat_ui.py"

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
    assert "Bản xem trước câu trả lời" in ui_source
    assert "Nguồn đang bật cho cuộc trò chuyện" in ui_source
    assert "Điều owner cần kiểm tra" in ui_source
    assert "Việc nên làm tiếp" in ui_source
    assert "Lưu vào hồ sơ" in ui_source
    assert "Xem đoạn xem trước sẽ dùng ở bước sau" in ui_source


def test_phase2e_required_copy_in_app():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    assert "Chế độ trả lời" in app_source
    assert "Chỉ xem trước trên máy" in app_source
    assert "Cho phép gửi nội dung nguồn đang bật tới AI" in app_source
    assert "Câu trả lời AI" in app_source
    assert "Nguồn đang bật được đưa vào câu hỏi" in app_source
    assert "Nội dung có thể bị rút gọn để tránh quá dài" in app_source
    assert "Đây là câu trả lời do AI tạo, cần kiểm tra lại trước khi dùng." in app_source


def test_phase2e_forbidden_copy_absent():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    ui_source = Path("src/aios_habit/workspace_chat_ui.py").read_text(encoding="utf-8")

    forbidden = [
        "RAG", "vector", "embedding", "chunk", "retrieval", "citation",
        "claim", "provider router", "Mermaid", "Nguồn chứng minh",
        "AIOS đã chứng minh", "AIOS đã xác minh", "Kết luận chắc chắn từ tài liệu"
    ]
    for word in forbidden:
        assert word.lower() not in app_source.lower(), f"Forbidden word '{word}' found in app"
        assert word.lower() not in ui_source.lower(), f"Forbidden word '{word}' found in UI"
