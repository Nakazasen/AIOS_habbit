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


def test_phase2i_exact_owner_privacy_copy_and_no_owner_enum_leak():
    ui_source = Path("src/aios_habit/workspace_chat_ui.py").read_text(encoding="utf-8")
    required = [
        "Nguồn này được dùng thế nào?",
        "Có thể gửi AI",
        "Chỉ dùng trên máy / không gửi AI",
        "Bạn vẫn cần bấm Hỏi AI để gửi. Nguồn chỉ dùng trên máy sẽ không được gửi AI.",
        "Quyền riêng tư nguồn",
        "Có thể gửi AI khi bạn bấm Hỏi AI",
        "Nguồn này sẽ không được gửi AI",
        "Lưu lựa chọn",
        "Đã cập nhật quyền riêng tư nguồn.",
        "Có nguồn không được gửi AI. Hãy tắt nguồn đó hoặc đổi lựa chọn quyền riêng tư.",
    ]
    for copy in required:
        assert copy in ui_source

    rendered_copy = "\n".join(line for line in ui_source.splitlines() if "PRIVACY_" in line and "=" in line)
    for forbidden in ["privacy_label", "provider", "cloud consent"]:
        assert forbidden not in rendered_copy.lower()


def test_phase2i_exact_owner_privacy_copy_and_no_owner_enum_leak():
    ui_source = Path("src/aios_habit/workspace_chat_ui.py").read_text(encoding="utf-8")
    required = [
        "Nguồn này được dùng thế nào?",
        "Có thể gửi AI",
        "Chỉ dùng trên máy / không gửi AI",
        "Bạn vẫn cần bấm Hỏi AI để gửi. Nguồn chỉ dùng trên máy sẽ không được gửi AI.",
        "Quyền riêng tư nguồn",
        "Có thể gửi AI khi bạn bấm Hỏi AI",
        "Nguồn này sẽ không được gửi AI",
        "Lưu lựa chọn",
        "Đã cập nhật quyền riêng tư nguồn.",
        "Có nguồn không được gửi AI. Hãy tắt nguồn đó hoặc đổi lựa chọn quyền riêng tư.",
    ]
    for copy in required:
        assert copy in ui_source
    rendered_copy = "\n".join(line for line in ui_source.splitlines() if "PRIVACY_" in line and "=" in line)
    for forbidden in ["privacy_label", "provider", "cloud consent"]:
        assert forbidden not in rendered_copy.lower()


def test_hard_delete_required_copy():
    ui_source = Path("src/aios_habit/workspace_chat_ui.py").read_text(encoding="utf-8")
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")

    required_ui = [
        "Xóa vĩnh viễn sổ",
        "Hành động này sẽ xóa vĩnh viễn sổ và toàn bộ dữ liệu bên trong. Không thể khôi phục.",
        "Nhập chính xác tên sổ để xác nhận xóa",
        "Tôi hiểu dữ liệu sẽ bị xóa vĩnh viễn",
        "Xác nhận xóa vĩnh viễn",
        "Đã xóa vĩnh viễn sổ.",
        "Không thể xóa sổ vì tên xác nhận chưa đúng.",
        "Không thể xóa sổ. Vui lòng thử lại."
    ]
    for copy in required_ui:
        assert (copy in ui_source) or (copy in app_source), f"Required copy '{copy}' not found in ui or app"

    # Check that archive copy still exists and remains distinct
    assert "Lưu trữ sổ" in ui_source
    assert "Khôi phục sổ" in ui_source

    # Check that no trash/soft-delete copy is introduced
    for word in ["thùng rác", "soft delete", "soft-delete", "trash"]:
        assert word not in ui_source.lower()
        assert word not in app_source.lower()

    # Check no internal owner-facing terms in Vietnamese UI labels
    forbidden_terms = [
        "jsonl", "cascade", "schema", "source scopes", "machine_only",
        "local_only", "privacy_label", "provider_success", "mock",
        "test harness", "backend"
    ]

    import re
    # Extract string literals passed to streamlit text display functions or assigned to uppercase copy constants
    user_facing_strings = []
    streamlit_display_pattern = re.compile(
        r'(?:st\.(?:write|error|warning|info|success|markdown|text_input|checkbox|button|caption|title|header|subheader))\((.*?)\)'
    )
    constant_assign_pattern = re.compile(r'^([A-Z_0-9]+)\s*=\s*["\']([^"\']*)["\']\s*$')

    for source_text in [ui_source, app_source]:
        for line in source_text.splitlines():
            line_str = line.strip()
            if line_str.startswith("#"):
                continue
            # Check Streamlit calls
            for match in streamlit_display_pattern.finditer(line_str):
                args_str = match.group(1)
                for q_match in re.findall(r'"([^"]*)"|\'([^\']*)\'', args_str):
                    val = q_match[0] or q_match[1]
                    if val:
                        user_facing_strings.append(val.lower())
            # Check Constant assignments
            m = constant_assign_pattern.match(line_str)
            if m:
                val = m.group(2)
                if val:
                    user_facing_strings.append(val.lower())

    for term in forbidden_terms:
        for val in user_facing_strings:
            assert term not in val, f"Forbidden term '{term}' leaked in user-facing UI text: '{val}'"
