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
    assert "Tóm tắt nguồn đang dùng" in ui_source
    assert "Nguồn đang bật cho câu hỏi" in ui_source
    assert "Cần kiểm tra lại" in ui_source
    assert "Việc nên làm tiếp" in ui_source
    assert "Lưu vào hồ sơ" in ui_source
    assert "Xem đoạn xem trước sẽ dùng ở bước sau" in ui_source
    assert "Bật nguồn này cho cuộc trò chuyện" in ui_source


def test_phase2e_required_copy_in_app():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    # Phase 2H: Radio removed, check AI-first flow labels instead
    assert "Đây là câu trả lời do AI tạo" in app_source
    assert "Hỏi AI với nguồn đang bật" in app_source
    assert "Kiểm tra nguồn trước" in app_source


def test_phase2g_required_copy():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    # Phase 2H: 'Không gửi dữ liệu ra ngoài' caption was removed with the radio
    assert "dán văn bản dài" in app_source
    assert "Excel .xlsx" in app_source
    assert "dữ liệu test không mật" in app_source
    assert "ô hỏi chỉ hỗ trợ nhập chữ" in app_source.lower()
    assert "chưa hỗ trợ dán ảnh hoặc thêm PDF/Word trực tiếp" in app_source


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


def test_phase2g_save_feedback_placeholder_truthful_copy():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    assert "Chưa lưu dữ liệu. Tính năng ‘Lưu vào hồ sơ’ hiện đang ở chế độ mô phỏng." in app_source
    assert "st.info(f\"ℹ️ {SAVE_CASE_PLACEHOLDER_MESSAGE}\")" in app_source
    forbidden_success_claims = [
        "Đã kích hoạt lưu",
        "hồ sơ sự việc mới thành công",
        "hồ sơ đã được tạo",
    ]
    for phrase in forbidden_success_claims:
        assert phrase not in app_source


def test_phase2h_no_mode_radio_in_app():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    ui_source = Path("src/aios_habit/workspace_chat_ui.py").read_text(encoding="utf-8")
    # The owner-facing radio must be absent
    assert "Chế độ trả lời" not in app_source
    assert "Chỉ xem trước trên máy" not in app_source
    assert "Cho phép gửi nội dung nguồn đang bật tới AI" not in app_source
    assert "st.radio" not in app_source


def test_phase2h_required_copy():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    ui_source = Path("src/aios_habit/workspace_chat_ui.py").read_text(encoding="utf-8")
    # Phase 2H required labels
    assert "Hỏi AI với nguồn đang bật" in ui_source
    assert "AI chưa trả lời" in ui_source
    assert "AI đã trả lời" in ui_source
    assert "Thiếu ngữ cảnh" in ui_source
    assert "Nguồn gửi cùng câu hỏi" in ui_source
    assert "Dán nhanh nhiều nguồn" in ui_source
    assert "Kiểm tra nguồn trước" in ui_source
    # App uses labels from ui
    assert "render_ai_answer_header" in app_source
    assert "render_insufficient_context" in app_source
    assert "render_source_check_panel" in app_source
    assert "render_privacy_block_message" in app_source
