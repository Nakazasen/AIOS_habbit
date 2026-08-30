from pathlib import Path
import ast
import re

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

STREAMLIT_DISPLAY_FUNCTIONS = {
    "write", "markdown", "caption", "button", "info", "warning", "error",
    "success", "title", "header", "subheader", "text_input", "text_area",
    "selectbox", "radio", "checkbox", "expander", "progress", "toast",
    "file_uploader", "metric", "spinner", "dataframe", "popover", "form",
    "tabs", "help",
}


def _literal_text(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
        return "".join(parts) if parts else None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _literal_text(node.left)
        right = _literal_text(node.right)
        if left is not None and right is not None:
            return left + right
    return None


def _is_streamlit_display_call(func: ast.AST) -> bool:
    if isinstance(func, ast.Attribute) and func.attr in STREAMLIT_DISPLAY_FUNCTIONS:
        root = func.value
        if isinstance(root, ast.Name) and root.id == "st":
            return True
        if isinstance(root, ast.Attribute) and root.attr == "sidebar":
            return True
    return False


class _DisplayCopyVisitor(ast.NodeVisitor):
    """Collect string literals passed to Streamlit display calls."""

    def __init__(self) -> None:
        self.strings: list[str] = []

    def visit_Call(self, node: ast.Call) -> None:
        if _is_streamlit_display_call(node.func):
            for arg in node.args:
                text = _literal_text(arg)
                if text:
                    self.strings.append(text)
            for keyword in node.keywords:
                text = _literal_text(keyword.value)
                if text:
                    self.strings.append(text)
        self.generic_visit(node)


def iter_display_ui_strings(code: str) -> list[str]:
    """Return UI copy at Streamlit call sites, including multiline captions."""
    tree = ast.parse(code)
    visitor = _DisplayCopyVisitor()
    visitor.visit(tree)
    return visitor.strings


def extract_strings_from_code(code: str) -> list[str]:
    return iter_display_ui_strings(code)


def is_technical_identifier(s: str) -> bool:
    # Widget/i18n keys, not captions. Display copy is scanned even when multiline.
    if not s.strip():
        return True
    if " " not in s and "\n" not in s and "_" in s:
        return True
    return False


def test_multiline_display_copy_with_forbidden_word_is_detected() -> None:
    sample = '''
import streamlit as st
st.markdown("""Dòng một
Dòng hai
RAG hiển thị cho người dùng
Dòng bốn""")
'''
    strings = iter_display_ui_strings(sample)
    assert any("RAG" in item for item in strings)
    scanned = [item for item in strings if not is_technical_identifier(item)]
    assert any("rag" in item.lower() for item in scanned)


def test_nondisplay_code_identifier_is_not_scanned_as_ui_copy() -> None:
    sample = '''
from aios_habit.workspace_chat_store import (
    relocate_collection_storage,
    set_collection_storage_root,
)
HELP = "internal relocate_collection_storage note"
'''
    strings = iter_display_ui_strings(sample)
    assert strings == []


def test_workspace_chat_ui_copy_no_forbidden_words():
    # Read files
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    ui_source = Path("src/aios_habit/workspace_chat_ui.py").read_text(encoding="utf-8")

    app_strings = [s for s in extract_strings_from_code(app_source) if not is_technical_identifier(s)]
    ui_strings = [s for s in extract_strings_from_code(ui_source) if not is_technical_identifier(s)]

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
        for val in app_strings:
            assert word.lower() not in val.lower(), f"Forbidden word '{word}' found in app string literal: '{val}'"
        for val in ui_strings:
            assert word.lower() not in val.lower(), f"Forbidden word '{word}' found in UI string literal: '{val}'"

    for word in SEMANTIC_FORBIDDEN:
        for val in app_strings:
            assert word.lower() not in val.lower(), f"Semantic forbidden word/phrase '{word}' found in app string literal: '{val}'"
        for val in ui_strings:
            assert word.lower() not in val.lower(), f"Semantic forbidden word/phrase '{word}' found in UI string literal: '{val}'"

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
    assert "Hỏi AI với nguồn đang bật" not in app_source
    assert "Kiểm tra nguồn trước" not in app_source


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

    app_strings = [s for s in extract_strings_from_code(app_source) if not is_technical_identifier(s)]
    ui_strings = [s for s in extract_strings_from_code(ui_source) if not is_technical_identifier(s)]

    forbidden = [
        "RAG", "vector", "embedding", "chunk", "retrieval", "citation",
        "claim", "provider router", "Mermaid", "Nguồn chứng minh",
        "AIOS đã chứng minh", "AIOS đã xác minh", "Kết luận chắc chắn từ tài liệu"
    ]
    for word in forbidden:
        for val in app_strings:
            assert word.lower() not in val.lower(), f"Forbidden word '{word}' found in app UI text: '{val}'"
        for val in ui_strings:
            assert word.lower() not in val.lower(), f"Forbidden word '{word}' found in UI UI text: '{val}'"


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
    assert "Hỏi" in ui_source
    assert "AI chưa trả lời" in ui_source
    assert "AI đã trả lời" in ui_source
    assert "Thiếu ngữ cảnh" in ui_source
    assert "Nguồn gửi cùng câu hỏi" in ui_source
    assert "Dán nhanh nhiều nguồn" in ui_source
    assert "Kiểm tra" in ui_source
    # App uses labels from ui
    assert "render_ai_answer_header" in app_source
    assert "render_insufficient_context" in app_source
    assert "render_privacy_block_message" in app_source

    # Advanced expanders must be removed from production UI
    assert "Quản lý nguồn nâng cao" not in app_source
    assert "Quản lý nguồn nâng cao" not in ui_source
    assert "Kiểm tra nguồn nâng cao" not in app_source
    assert "Kiểm tra nguồn nâng cao" not in ui_source


def test_phase2i_exact_owner_privacy_copy_and_no_owner_enum_leak():
    ui_source = Path("src/aios_habit/workspace_chat_ui.py").read_text(encoding="utf-8")
    required = [
        "Nguồn này được dùng thế nào?",
        "Có thể gửi nội dung tới AI bên ngoài",
        "Chỉ dùng trên máy / không gửi AI",
        "Chỉ chọn gửi AI ngoài khi nội dung được phép chia sẻ. Bạn vẫn cần bấm Hỏi để gửi.",
        "Quyền riêng tư nguồn",
        "Nội dung có thể gửi AI ngoài khi bạn bấm Hỏi",
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

def test_gate_1c_source_library_copy():
    ui_source = Path("src/aios_habit/workspace_chat_ui.py").read_text(encoding="utf-8")
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    required_ui = [
        "📚 Thư viện nguồn",
        "Xác nhận xóa nguồn này?",
        "Xác nhận xóa",
        "Đã bật",
        "Đã tắt",
        "Tùy chọn nguồn",
    ]
    for copy in required_ui:
        assert (copy in ui_source) or (copy in app_source), f"Required copy '{copy}' not found in ui or app"


def test_no_inspect_stack_in_production_ui():
    ui_source = Path("src/aios_habit/workspace_chat_ui.py").read_text(encoding="utf-8")
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    for source in [ui_source, app_source]:
        assert "inspect.stack" not in source
        assert "inspect.currentframe" not in source
        assert "sys._getframe" not in source
        assert "caller_mock_st" not in source
        assert "Các bước thử nghiệm" not in source
        assert "Pilot" not in source


def test_workspace_chat_ui_copy_notebooklm_governance_harden():
    ui_source = Path("src/aios_habit/workspace_chat_ui.py").read_text(encoding="utf-8")
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")

    # 1. Ensure the exact simple instruction is recorded
    assert "Thêm tài liệu rồi hỏi tự nhiên; AIOS sẽ tự kiểm tra nguồn và cảnh báo nếu thiếu." in app_source

    # 2. Ensure main button is "Hỏi"
    assert "Hỏi" in ui_source

    # 3. List of strictly forbidden UI strings
    forbidden_terms = [
        "giao ai xử lý",
        "nhập kết quả ai",
        "task pack",
        "report import",
        "hash",
        "gate",
        "commit",
        "branch",
        "push",
        "a17",
        "các bước thử nghiệm",
        "pilot",
        "hỏi ai với nguồn đang bật",
        "kiểm tra nguồn trước"
    ]

    # Extract user-facing string literals
    user_facing_strings = []
    streamlit_display_pattern = re.compile(
        r'(?:st\.(?:write|error|warning|info|success|markdown|text_input|checkbox|button|caption|title|header|subheader))\((.*?)\)'
    )
    constant_assign_pattern = re.compile(r'^([A-Z_0-9]+)\s*=\s*["\']([^"\']*)["\']\s*$')

    # Also parse get_vietnamese_labels dictionary values
    labels_pattern = re.compile(r'["\']([a-z0-9_]+)["\']\s*:\s*["\']([^"\']+)["\']')

    for source_text in [ui_source, app_source]:
        for line in source_text.splitlines():
            line_str = line.strip()
            if line_str.startswith("#"):
                continue
            # Streamlit calls
            for match in streamlit_display_pattern.finditer(line_str):
                args_str = match.group(1)
                for q_match in re.findall(r'"([^"]*)"|\'([^\']*)\'', args_str):
                    val = q_match[0] or q_match[1]
                    if val:
                        user_facing_strings.append(val.lower())
            # Constants
            m = constant_assign_pattern.match(line_str)
            if m:
                val = m.group(2)
                if val:
                    user_facing_strings.append(val.lower())
            # Dictionary labels
            for match in labels_pattern.finditer(line_str):
                val = match.group(2)
                if val:
                    user_facing_strings.append(val.lower())

    for term in forbidden_terms:
        for val in user_facing_strings:
            # We allow words like "gate" if they are in technical variables, but not in user-facing literals.
            assert term not in val, f"Forbidden term '{term}' leaked in user-facing UI text: '{val}'"


def test_adaptive_search_preference_copy_in_app():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    assert "Tự động" in app_source
    assert "Tìm kỹ hơn" in app_source
    assert "Mức độ tìm kiếm" in app_source

    forbidden_technical = ["bge_m3_hybrid_rerank", "cross_encoder", "bge_reranker_model_path"]
    for term in forbidden_technical:
        assert f'"{term}"' not in app_source
