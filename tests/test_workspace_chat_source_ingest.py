import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

import aios_habit.workspace_chat_store as store
from aios_habit.workspace_chat_models import (
    TemporaryConversationSource,
    SOURCE_SCOPE_TEMPORARY,
)
from aios_habit.workspace_chat_source_ingest import (
    sanitize_filename,
    ingest_and_extract_bytes,
)

@pytest.fixture(autouse=True)
def setup_test_store(tmp_path, monkeypatch):
    test_dir = tmp_path / "workspace_chat"
    monkeypatch.setattr(store, "LOCAL_CHAT_DIR", test_dir)
    monkeypatch.setattr(store, "NOTEBOOKS_FILE", test_dir / "notebooks.jsonl")
    monkeypatch.setattr(store, "CONVERSATIONS_FILE", test_dir / "conversations.jsonl")
    monkeypatch.setattr(store, "MESSAGES_FILE", test_dir / "messages.jsonl")
    monkeypatch.setattr(store, "TEMPORARY_SOURCES_FILE", test_dir / "temporary_sources.jsonl")
    monkeypatch.setattr(store, "NOTEBOOK_SOURCES_FILE", test_dir / "notebook_sources.jsonl")
    monkeypatch.setattr(store, "SOURCE_SELECTIONS_FILE", test_dir / "conversation_source_selections.jsonl")
    store.init_chat_store()

def test_architecture_boundary():
    # Ensure neither studio.py nor case_cockpit.py is imported in the source ingest module
    source_path = Path("src/aios_habit/workspace_chat_source_ingest.py")
    content = source_path.read_text(encoding="utf-8")
    assert "import studio" not in content
    assert "import case_cockpit" not in content
    assert "aios_habit.studio" not in content
    assert "aios_habit.case_cockpit" not in content

def test_sanitize_filename():
    assert sanitize_filename("test.txt") == "test.txt"
    assert sanitize_filename("test/../../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\some_file.docx") == "some_file.docx"
    assert sanitize_filename("a b c.xlsx") == "a_b_c.xlsx"
    assert sanitize_filename("special!@#char.pdf") == "special___char.pdf"

def test_ingest_txt_md_csv_success():
    # TXT Success
    txt_bytes = b"Hello, this is a plain text file for testing."
    res = ingest_and_extract_bytes(txt_bytes, "test_file.txt")
    assert res["ok"] is True
    assert "tài liệu" in res["owner_message"]
    assert res["text"] == "Hello, this is a plain text file for testing."
    assert res["preview"] == "Hello, this is a plain text file for testing."

    # MD Success
    md_bytes = b"# Heading\nSome markdown *content* here."
    res_md = ingest_and_extract_bytes(md_bytes, "doc.md")
    assert res_md["ok"] is True
    assert res_md["text"] == "# Heading\nSome markdown *content* here."

    # CSV Success
    csv_bytes = b"Name,Age,Role\nAlice,30,Dev\nBob,25,Tester"
    res_csv = ingest_and_extract_bytes(csv_bytes, "employees.csv")
    assert res_csv["ok"] is True
    assert "tài liệu" in res_csv["owner_message"]
    assert "Alice,30,Dev" in res_csv["text"]
    assert res_csv["metadata"]["row_count"] == 3

def test_ingest_xlsx_preserved():
    # XLSX should delegate to workspace_chat_excel
    # We will use mock to verify it delegates correctly
    mock_res = MagicMock()
    mock_res.ok = True
    mock_res.filename = "mocked.xlsx"
    mock_res.text = "Mocked Excel Text"
    mock_res.preview = "Mocked Preview"
    mock_res.sheet_names = ("Sheet1",)
    mock_res.truncated = False
    mock_res.owner_message = "Mocked owner message"

    with patch("aios_habit.workspace_chat_source_ingest.extract_xlsx_text", return_value=mock_res) as mock_extract:
        res = ingest_and_extract_bytes(b"dummybytes", "mocked.xlsx")
        assert res["ok"] is True
        assert res["text"] == "Mocked Excel Text"
        mock_extract.assert_called_once_with(b"dummybytes", "mocked.xlsx")

def test_ingest_empty_oversized_unsupported():
    # Empty
    res_empty = ingest_and_extract_bytes(b"", "empty.txt")
    assert res_empty["ok"] is False
    assert res_empty["error_code"] == "empty"
    assert "rỗng" in res_empty["owner_message"]

    # Oversized (>10MB)
    huge_bytes = b"a" * (11 * 1024 * 1024)
    res_huge = ingest_and_extract_bytes(huge_bytes, "huge.txt")
    assert res_huge["ok"] is False
    assert res_huge["error_code"] == "oversized"
    assert "giới hạn" in res_huge["owner_message"]

    # Unsupported extension
    res_unsupported = ingest_and_extract_bytes(b"content", "file.exe")
    assert res_unsupported["ok"] is False
    assert res_unsupported["error_code"] == "unsupported"
    assert "chưa được hỗ trợ" in res_unsupported["owner_message"]

def test_pdf_graceful_degradation():
    # Simulate missing PDF optional dependencies (fitz / pymupdf4llm)
    # We trigger this by mocking extract_text_chunks_from_file to return dependency_missing status
    mock_chunks = [
        {
            "text": "",
            "extraction_status": "dependency_missing",
            "warning": "pymupdf4llm and fitz are not installed",
            "element_type": "pdf_page_text",
        }
    ]
    with patch("aios_habit.workspace_chat_source_ingest.extract_text_chunks_from_file", return_value=mock_chunks):
        res = ingest_and_extract_bytes(b"pdf_bytes", "doc.pdf")
        assert res["ok"] is False
        assert res["error_code"] == "dependency_missing"
        assert "chưa có bộ đọc PDF" in res["owner_message"]

def test_image_ocr_graceful_degradation():
    # Simulate missing OCR engines (pytesseract or tesseract.exe missing)
    mock_chunks = [
        {
            "text": "",
            "extraction_status": "unsupported_no_local_ocr",
            "warning": "local OCR unavailable",
        }
    ]
    with patch("aios_habit.workspace_chat_source_ingest.extract_text_chunks_from_file", return_value=mock_chunks):
        res = ingest_and_extract_bytes(b"img_bytes", "screenshot.png")
        assert res["ok"] is False
        assert res["error_code"] == "dependency_missing"
        assert "chưa có bộ đọc chữ trong ảnh" in res["owner_message"]

def test_temp_file_cleanup_on_success_and_failure(tmp_path):
    # Mock OS temp dir to use our tmp_path to easily inspect files
    tempdir_str = str(tmp_path)
    
    with patch("tempfile.gettempdir", return_value=tempdir_str):
        # 1. Success case
        mock_chunks = [{"text": "extracted content", "extraction_status": "extracted"}]
        with patch("aios_habit.workspace_chat_source_ingest.extract_text_chunks_from_file", return_value=mock_chunks):
            res = ingest_and_extract_bytes(b"pdf_data", "test.pdf")
            assert res["ok"] is True
            # Assert no temp files left in the directory
            leftovers = list(tmp_path.glob("wsc_extract_*"))
            assert len(leftovers) == 0

        # 2. Failure/Exception case
        with patch("aios_habit.workspace_chat_source_ingest.extract_text_chunks_from_file", side_effect=ValueError("Boom!")):
            res_fail = ingest_and_extract_bytes(b"pdf_data", "test.pdf")
            assert res_fail["ok"] is False
            assert res_fail["error_code"] == "malformed"
            # Assert temp file is cleaned up even after exception
            leftovers = list(tmp_path.glob("wsc_extract_*"))
            assert len(leftovers) == 0

def test_no_provider_or_ai_called():
    # We patch AI calls to verify they are never reached during ingest_and_extract_bytes
    with patch("aios_habit.workspace_chat_ai_answer.generate_workspace_ai_answer") as mock_ai:
        res = ingest_and_extract_bytes(b"hello", "test.txt")
        assert res["ok"] is True
        mock_ai.assert_not_called()

def test_app_integration_upload_flow_logic():
    # We simulate the UI integration logic in workspace_chat_app.py
    from aios_habit.workspace_chat_app import create_general_temporary_source
    
    conv_id = "test_conv"
    
    # Scenario 1: Upload TXT with enable_now = False
    result_txt = {
        "ok": True,
        "filename": "hello.txt",
        "preview": "hello world",
        "text": "hello world full",
        "metadata": {"extension": ".txt"}
    }
    
    # Store integration
    ts1 = create_general_temporary_source(
        conversation_id=conv_id,
        title=result_txt["filename"],
        source_type="txt",
        content_preview=result_txt["preview"],
        content_text=result_txt["text"],
        owner_choice="machine_only",
        enable_source=False,
    )
    
    assert ts1.id.startswith("SRC-")
    assert ts1.title == "hello.txt"
    assert ts1.privacy_label == "machine_only"
    
    # Check selection status (should not be enabled)
    selections = store.load_conversation_source_selections(conv_id)
    enabled_selections = [s for s in selections if s.source_id == ts1.id and s.enabled]
    assert len(enabled_selections) == 0

    # Scenario 2: Upload TXT with enable_now = True
    ts2 = create_general_temporary_source(
        conversation_id=conv_id,
        title=result_txt["filename"],
        source_type="txt",
        content_preview=result_txt["preview"],
        content_text=result_txt["text"],
        owner_choice="machine_only",
        enable_source=True,
    )
    
    # Check selection status (should be enabled)
    selections2 = store.load_conversation_source_selections(conv_id)
    enabled_selections2 = [s for s in selections2 if s.source_id == ts2.id and s.enabled]
    assert len(enabled_selections2) == 1
    assert enabled_selections2[0].source_scope == SOURCE_SCOPE_TEMPORARY


def test_excel_checkbox_on_off_behavior_real():
    from aios_habit.workspace_chat_app import create_general_temporary_source
    conv_id = "test_excel_conv"

    # Scenario A: Excel checkbox is OFF -> should_enable must be False
    ts_off = create_general_temporary_source(
        conversation_id=conv_id,
        title="test_off.xlsx",
        source_type="xlsx",
        content_preview="Preview",
        content_text="Full text",
        owner_choice="machine_only",
        enable_source=False,  # checkbox OFF
    )
    selections_off = store.load_conversation_source_selections(conv_id)
    enabled_off = [s for s in selections_off if s.source_id == ts_off.id and s.enabled]
    assert len(enabled_off) == 0, "Excel should NOT be auto-enabled when checkbox is OFF"

    # Scenario B: Excel checkbox is ON -> should_enable is True
    ts_on = create_general_temporary_source(
        conversation_id=conv_id,
        title="test_on.xlsx",
        source_type="xlsx",
        content_preview="Preview",
        content_text="Full text",
        owner_choice="machine_only",
        enable_source=True,  # checkbox ON
    )
    selections_on = store.load_conversation_source_selections(conv_id)
    enabled_on = [s for s in selections_on if s.source_id == ts_on.id and s.enabled]
    assert len(enabled_on) == 1, "Excel should be enabled when checkbox is ON"


def test_docx_pptx_synthetic_extraction_real():
    import zipfile
    from io import BytesIO

    # 1. Create a synthetic DOCX zip in memory
    docx_io = BytesIO()
    with zipfile.ZipFile(docx_io, "w") as docx_zip:
        # docx needs word/document.xml containing <w:t> tags
        document_xml = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">\n'
            '  <w:body>\n'
            '    <w:p>\n'
            '      <w:r>\n'
            '        <w:t>Hello DOCX synthetic content!</w:t>\n'
            '      </w:r>\n'
            '    </w:p>\n'
            '  </w:body>\n'
            '</w:document>'
        )
        docx_zip.writestr("word/document.xml", document_xml.encode("utf-8"))
    
    docx_bytes = docx_io.getvalue()
    res_docx = ingest_and_extract_bytes(docx_bytes, "doc.docx")
    assert res_docx["ok"] is True
    assert "Hello DOCX synthetic content!" in res_docx["text"]

    # 2. Create a synthetic PPTX zip in memory
    pptx_io = BytesIO()
    with zipfile.ZipFile(pptx_io, "w") as pptx_zip:
        # pptx needs ppt/slides/slide1.xml or slides/slideX.xml containing <a:t> or <p:sp>
        # document_extractors pptx parser reads ppt/slides/*.xml and extracts xml text
        slide_xml = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"\n'
            '       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">\n'
            '  <p:cSld>\n'
            '    <p:spTree>\n'
            '      <p:sp>\n'
            '        <p:txBody>\n'
            '          <a:p>\n'
            '            <a:r>\n'
            '              <a:t>Hello PPTX slide content!</a:t>\n'
            '            </a:r>\n'
            '          </a:p>\n'
            '        </a:p>\n'
            '      </p:txBody>\n'
            '    </p:sp>\n'
            '  </p:spTree>\n'
            '  </p:cSld>\n'
            '</p:sld>'
        )
        pptx_zip.writestr("ppt/slides/slide1.xml", slide_xml.encode("utf-8"))
    
    pptx_bytes = pptx_io.getvalue()
    res_pptx = ingest_and_extract_bytes(pptx_bytes, "presentation.pptx")
    assert res_pptx["ok"] is True
    assert "Hello PPTX slide content!" in res_pptx["text"]


def test_malformed_real_zip_files():
    bad_bytes = b"This is not a valid zip archive file data at all!"
    
    for filename in ["malformed.docx", "malformed.pptx", "malformed.xlsx"]:
        res = ingest_and_extract_bytes(bad_bytes, filename)
        assert res["ok"] is False
        assert res["error_code"] == "malformed"
        
        # Verify sanitization: NO raw exceptions or class names leaked
        msg = res["owner_message"]
        assert "Không thể đọc tập tin này" in msg
        assert "Vui lòng kiểm tra lại" in msg
        
        # Strict leak prevention checks
        for forbidden in ["traceback", "exception", "valueerror", "badzipfile", "zipfile", "invalid", "c:\\", "tmp"]:
            assert forbidden not in msg.lower()


def test_exception_sanitization_strict():
    # Monkeypatch extract_text_chunks_from_file to throw a ValueError containing sensitive info
    sensitive_msg = "boom error in C:\\Windows\\temp\\stack.log with raw StackTrace"
    
    with patch(
        "aios_habit.workspace_chat_source_ingest.extract_text_chunks_from_file",
        side_effect=ValueError(sensitive_msg)
    ):
        res = ingest_and_extract_bytes(b"dummy pdf content", "test.pdf")
        assert res["ok"] is False
        assert res["error_code"] == "malformed"
        
        msg = res["owner_message"]
        assert msg == "Không thể đọc tập tin này. Vui lòng kiểm tra lại tập tin hoặc thử định dạng khác."
        
        # Double check no raw exception/trace elements leaked
        for forbidden in ["traceback", "exception", "valueerror", "boom", "stack", "raw", "c:\\", "tmp"]:
            assert forbidden not in msg.lower()


def test_no_duplicate_uploader_and_copy_on_main_ui():
    app_path = Path("src/aios_habit/workspace_chat_app.py")
    content = app_path.read_text(encoding="utf-8")
    
    # 1. Parse content to isolate main rendering path from compatibility dead code helper
    # Compatibility helper is defined as `def _legacy_excel_uploader_compatibility_dont_call`
    main_content_end = content.find("def _legacy_excel_uploader_compatibility_dont_call")
    assert main_content_end != -1, "Compatibility helper not found"
    
    main_content = content[:main_content_end]
    
    # 2. Assert legacy Excel expander is NOT in the main UI rendering code
    assert "📊 Thêm file Excel .xlsx" not in main_content
    assert "excel_upload_form" not in main_content
    
    # 3. Assert old stale copy is NOT in the main UI info bar
    assert "chưa hỗ trợ dán ảnh hoặc thêm PDF/Word trực tiếp" not in main_content
    
    # 4. Assert compatibility helper is not called in main flow
    # Count occurrences of the helper name in the file. Should only be 1 (its definition).
    occurrences = content.count("_legacy_excel_uploader_compatibility_dont_call")
    assert occurrences == 1, "Compatibility helper is called somewhere in main flow!"

