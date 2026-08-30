from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

import aios_habit.workspace_chat_store as store
from aios_habit.workspace_chat_folder_import import (
    IGNORED_DIR_NAMES,
    MAX_BATCH_FILE_SIZE_BYTES,
    MAX_FOLDER_SCAN_FILES,
    SUPPORTED_DOCUMENT_EXTENSIONS,
    BatchIngestItemResult,
    BatchIngestSummary,
    DirectoryScanResult,
    ScannedFileInfo,
    clean_input_path,
    create_batch_temporary_source,
    format_size_bytes,
    ingest_local_folder,
    ingest_scanned_files_batch,
    scan_local_directory,
    validate_directory_path,
)
from aios_habit.workspace_chat_models import (
    SOURCE_SCOPE_NOTEBOOK,
    SOURCE_SCOPE_TEMPORARY,
)
from aios_habit.workspace_chat_store import (
    load_conversation_source_selections,
    load_enabled_sources_for_conversation,
    load_notebook_sources,
    load_temporary_sources,
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


class TestPathValidationAndCleaning:
    def test_clean_input_path_strips_quotes_and_whitespace(self):
        assert clean_input_path('  "D:\\Documents\\Work"  ') == "D:\\Documents\\Work"
        assert clean_input_path("  'C:/Users/test/docs'  ") == "C:/Users/test/docs"
        assert clean_input_path(' ""D:\\Nested\\Quotes"" ') == "D:\\Nested\\Quotes"
        assert clean_input_path(" ' \"C:/Mixed/Quotes\" ' ") == "C:/Mixed/Quotes"
        assert clean_input_path('"D:\\SingleLeadingQuote') == "D:\\SingleLeadingQuote"
        assert clean_input_path(Path("/tmp/test")) == str(Path("/tmp/test"))
        assert clean_input_path("") == ""
        assert clean_input_path("   ") == ""
        assert clean_input_path(None) == ""

    def test_validate_directory_path_empty_or_none(self):
        valid, path, msg = validate_directory_path("")
        assert not valid
        assert path is None
        assert "Vui lòng nhập đường dẫn" in msg

        valid, path, msg = validate_directory_path("   ")
        assert not valid
        assert path is None
        assert "Vui lòng nhập đường dẫn" in msg

        valid, path, msg = validate_directory_path(None)
        assert not valid

    def test_validate_directory_path_null_bytes(self):
        valid, path, msg = validate_directory_path("/tmp/test\0bad")
        assert not valid
        assert path is None
        assert "không hợp lệ" in msg

    def test_validate_directory_path_nonexistent(self, tmp_path):
        fake_path = tmp_path / "non_existent_dir_12345"
        valid, path, msg = validate_directory_path(fake_path)
        assert not valid
        assert path is None
        assert "không tồn tại" in msg

    def test_validate_directory_path_is_file_not_dir(self, tmp_path):
        file_path = tmp_path / "a_regular_file.txt"
        file_path.write_text("hello", encoding="utf-8")

        valid, path, msg = validate_directory_path(file_path)
        assert not valid
        assert path is None
        assert "không phải là thư mục" in msg

    def test_validate_directory_path_valid(self, tmp_path):
        valid_dir = tmp_path / "my_docs"
        valid_dir.mkdir()

        valid, path, msg = validate_directory_path(valid_dir)
        assert valid
        assert path == valid_dir.resolve()
        assert msg == ""

    def test_validate_directory_path_permission_denied(self, tmp_path, monkeypatch):
        test_dir = tmp_path / "locked_dir"
        test_dir.mkdir()

        def mock_scandir(path):
            raise PermissionError("Access is denied")

        monkeypatch.setattr(os, "scandir", mock_scandir)
        valid, path, msg = validate_directory_path(test_dir)
        assert not valid
        assert "Không có quyền truy cập" in msg

    def test_validate_directory_path_invalid_oserror_characters(self, monkeypatch):
        def mock_resolve(self, *args, **kwargs):
            raise OSError("The filename, directory name, or volume label syntax is incorrect")

        with patch.object(Path, "resolve", mock_resolve):
            valid, path, msg = validate_directory_path("D:\\Invalid*Chars<?>")
            assert not valid
            assert path is None
            assert "không hợp lệ" in msg


class TestFormatSizeBytes:
    def test_format_size_bytes(self):
        assert format_size_bytes(-10) == "0 B"
        assert format_size_bytes(0) == "0 B"
        assert format_size_bytes(512) == "512 B"
        assert format_size_bytes(1024) == "1.0 KB"
        assert format_size_bytes(1536) == "1.5 KB"
        assert format_size_bytes(1024 * 1024) == "1.0 MB"
        assert format_size_bytes(25 * 1024 * 1024) == "25.0 MB"
        assert format_size_bytes(1024 * 1024 * 1024) == "1.00 GB"
        assert format_size_bytes(int(2.5 * 1024 * 1024 * 1024)) == "2.50 GB"


class TestDirectoryScanner:
    def test_scan_invalid_path_returns_error_result(self, tmp_path):
        bad_path = tmp_path / "missing_folder"
        res = scan_local_directory(bad_path)
        assert not res.ok
        assert "không tồn tại" in res.error_message
        assert res.total_files == 0
        assert res.supported_count() == 0
        assert res.unsupported_count() == 0

    def test_scan_empty_directory(self, tmp_path):
        empty_dir = tmp_path / "empty_dir"
        empty_dir.mkdir()

        res = scan_local_directory(empty_dir)
        assert res.ok
        assert res.total_files == 0
        assert res.supported_count() == 0
        assert res.unsupported_count() == 0
        assert res.total_supported_size_bytes == 0
        assert res.formatted_supported_size() == "0 B"
        assert res.formatted_total_size() == "0 B"

    def test_scan_flat_directory_mixed_files(self, tmp_path):
        doc_dir = tmp_path / "docs"
        doc_dir.mkdir()

        (doc_dir / "note.txt").write_text("Simple text", encoding="utf-8")
        (doc_dir / "report.md").write_text("# Markdown Report", encoding="utf-8")
        (doc_dir / "data.csv").write_text("a,b\n1,2", encoding="utf-8")
        (doc_dir / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (doc_dir / "photo.jpg").write_bytes(b"\xff\xd8\xff")
        (doc_dir / "doc.pdf").write_bytes(b"%PDF-1.4")
        (doc_dir / "slides.pptx").write_bytes(b"PK\x03\x04")
        (doc_dir / "sheet.xlsx").write_bytes(b"PK\x03\x04")
        (doc_dir / "word.docx").write_bytes(b"PK\x03\x04")
        (doc_dir / "legacy.xls").write_bytes(b"\xd0\xcf\x11\xe0")
        (doc_dir / "macro.xlsm").write_bytes(b"PK\x03\x04")
        (doc_dir / "webpage.html").write_text("<html></html>", encoding="utf-8")

        # Unsupported files
        (doc_dir / "program.exe").write_bytes(b"MZ\x90\x00")
        (doc_dir / "archive.zip").write_bytes(b"PK\x03\x04")
        (doc_dir / "data.bin").write_bytes(b"\x00\x01\x02")
        (doc_dir / "no_ext_file").write_text("no ext", encoding="utf-8")

        res = scan_local_directory(doc_dir, recursive=False)
        assert res.ok
        assert res.total_files == 16
        assert res.supported_count() == 11
        assert res.unsupported_count() == 5
        assert res.total_supported_size_bytes > 0
        assert ".txt" in res.extension_counts
        assert ".exe" in res.extension_counts

        supported_names = {f.filename for f in res.supported_files}
        assert "note.txt" in supported_names
        assert "report.md" in supported_names
        assert "data.csv" not in supported_names
        csv_info = next(item for item in res.unsupported_files if item.filename == "data.csv")
        assert csv_info.unsupported_reason == "csv_line_log"
        assert "image.png" in supported_names
        assert "photo.jpg" in supported_names
        assert "doc.pdf" in supported_names
        assert "slides.pptx" in supported_names
        assert "sheet.xlsx" in supported_names
        assert "word.docx" in supported_names
        assert "legacy.xls" in supported_names
        assert "macro.xlsm" in supported_names
        assert "webpage.html" in supported_names

        unsupported_names = {f.filename for f in res.unsupported_files}
        assert "program.exe" in unsupported_names
        assert "archive.zip" in unsupported_names
        assert "data.bin" in unsupported_names
        assert "no_ext_file" in unsupported_names

    def test_scan_recursive_subfolders(self, tmp_path):
        root_dir = tmp_path / "project_root"
        sub_dir1 = root_dir / "finance"
        sub_dir2 = root_dir / "engineering" / "specs"
        sub_dir1.mkdir(parents=True)
        sub_dir2.mkdir(parents=True)

        (root_dir / "readme.txt").write_text("root readme", encoding="utf-8")
        (sub_dir1 / "q1_budget.xlsx").write_bytes(b"PK\x03\x04")
        (sub_dir2 / "architecture.md").write_text("# Architecture", encoding="utf-8")

        # Non-recursive scan
        res_non_rec = scan_local_directory(root_dir, recursive=False)
        assert res_non_rec.ok
        assert res_non_rec.total_files == 1
        assert res_non_rec.supported_count() == 1
        assert res_non_rec.supported_files[0].filename == "readme.txt"

        # Recursive scan
        res_rec = scan_local_directory(root_dir, recursive=True)
        assert res_rec.ok
        assert res_rec.total_files == 3
        assert res_rec.supported_count() == 3
        rel_paths = {f.relative_path for f in res_rec.supported_files}
        assert "readme.txt" in rel_paths
        assert "finance/q1_budget.xlsx" in rel_paths
        assert "engineering/specs/architecture.md" in rel_paths

    def test_scan_ignores_hidden_files_and_system_directories(self, tmp_path):
        root_dir = tmp_path / "codebase"
        git_dir = root_dir / ".git"
        pycache_dir = root_dir / "__pycache__"
        venv_dir = root_dir / ".venv"
        node_modules_dir = root_dir / "node_modules"
        git_dir.mkdir(parents=True)
        pycache_dir.mkdir(parents=True)
        venv_dir.mkdir(parents=True)
        node_modules_dir.mkdir(parents=True)

        (root_dir / "valid_doc.md").write_text("Valid", encoding="utf-8")
        (root_dir / ".hidden_doc.txt").write_text("Hidden", encoding="utf-8")
        (git_dir / "commit.txt").write_text("Git commit", encoding="utf-8")
        (pycache_dir / "compiled.pyc").write_bytes(b"pyc")
        (venv_dir / "lib_doc.txt").write_text("Venv doc", encoding="utf-8")
        (node_modules_dir / "pkg_readme.md").write_text("Pkg readme", encoding="utf-8")

        res = scan_local_directory(root_dir, recursive=True, ignore_hidden=True)
        assert res.ok
        assert res.total_files == 1
        assert res.supported_count() == 1
        assert res.supported_files[0].filename == "valid_doc.md"

    def test_scan_max_files_limit_truncation(self, tmp_path):
        root_dir = tmp_path / "many_files"
        root_dir.mkdir()
        for i in range(15):
            (root_dir / f"doc_{i}.txt").write_text(f"content {i}", encoding="utf-8")

        res = scan_local_directory(root_dir, max_files=5)
        assert res.ok
        assert res.truncated_by_limit is True
        assert res.total_files == 5
        assert len(res.supported_files) == 5
        assert res.total_files == len(res.supported_files) + len(res.unsupported_files)

    def test_scan_handles_unreadable_file_stat_gracefully(self, tmp_path, monkeypatch):
        doc_dir = tmp_path / "unreadable_stat_dir"
        doc_dir.mkdir()

        good_file = doc_dir / "good.txt"
        good_file.write_text("I am good", encoding="utf-8")

        bad_file = doc_dir / "bad.txt"
        bad_file.write_text("I will fail stat", encoding="utf-8")

        original_stat = Path.stat

        def mock_stat(self, *args, **kwargs):
            if "bad.txt" in str(self):
                raise PermissionError("Access denied on stat")
            return original_stat(self, *args, **kwargs)

        monkeypatch.setattr(Path, "stat", mock_stat)

        res = scan_local_directory(doc_dir, recursive=False)
        assert res.ok
        assert res.total_files == 2
        assert res.supported_count() == 1
        assert res.unsupported_count() == 1
        assert res.unsupported_files[0].filename == "bad.txt"
        assert "Không thể đọc thông tin tập tin" in res.unsupported_files[0].unsupported_reason


class TestBatchIngestion:
    def test_ingest_scanned_files_batch_empty_list(self):
        summary = ingest_scanned_files_batch(
            files=[],
            conversation_id="conv_empty",
            privacy_choice="machine_only",
        )
        assert summary.total_files == 0
        assert summary.success_count == 0
        assert summary.fail_count == 0
        assert summary.item_results == []

    def test_ingest_scanned_files_batch_success_and_failures(self, tmp_path, monkeypatch):
        doc_dir = tmp_path / "batch_docs"
        doc_dir.mkdir()

        file1 = doc_dir / "doc1.txt"
        file1.write_text("Hello World 1", encoding="utf-8")

        file2 = doc_dir / "doc2.md"
        file2.write_text("# Markdown Title 2", encoding="utf-8")

        file_empty = doc_dir / "empty.txt"
        file_empty.write_text("", encoding="utf-8")

        file_corrupt = doc_dir / "corrupt_fail.docx"
        file_corrupt.write_bytes(b"NOT_A_VALID_DOCX")

        def mock_ingest(file_bytes, filename, privacy_label):
            if "fail" in filename:
                return {
                    "ok": False,
                    "filename": filename,
                    "error_code": "malformed",
                    "owner_message": "Tập tin bị lỗi cấu trúc.",
                    "text": "",
                    "preview": "",
                    "metadata": {"file_size_bytes": len(file_bytes), "extension": Path(filename).suffix},
                }
            return {
                "ok": True,
                "filename": filename,
                "error_code": None,
                "owner_message": "Đã trích xuất thành công.",
                "text": f"Extracted text of {filename}",
                "preview": f"Preview of {filename}",
                "metadata": {"file_size_bytes": len(file_bytes), "extension": Path(filename).suffix},
            }

        monkeypatch.setattr("aios_habit.workspace_chat_folder_import.ingest_and_extract_bytes", mock_ingest)

        scan_res = scan_local_directory(doc_dir)
        assert scan_res.ok

        progress_events = []
        def on_progress(cur, total, name):
            progress_events.append((cur, total, name))

        conversation_id = "test_conv_batch"
        notebook_id = "test_nb_batch"

        summary = ingest_scanned_files_batch(
            files=scan_res.supported_files,
            conversation_id=conversation_id,
            privacy_choice="Chỉ dùng trên máy / không gửi AI",
            enable_now=True,
            save_to_notebook=True,
            notebook_id=notebook_id,
            progress_callback=on_progress,
        )

        assert summary.total_files == 4
        assert summary.success_count == 2
        assert summary.fail_count == 2
        assert "doc1.txt" in summary.success_files
        assert "doc2.md" in summary.success_files
        assert "empty.txt" in summary.failed_files
        assert "corrupt_fail.docx" in summary.failed_files

        # Verify progress callback was invoked for all items
        assert len(progress_events) == 4
        assert progress_events[-1][0] == 4
        assert progress_events[-1][1] == 4

        # Verify saved temporary sources
        temp_sources = load_temporary_sources(conversation_id)
        assert len(temp_sources) == 2
        temp_titles = {s.title for s in temp_sources}
        assert "doc1.txt" in temp_titles
        assert "doc2.md" in temp_titles

        # Verify saved notebook sources
        nb_sources = load_notebook_sources(notebook_id)
        assert len(nb_sources) == 2

        # Verify conversation source selections were enabled
        enabled_selections = load_enabled_sources_for_conversation(conversation_id)
        assert len(enabled_selections) == 2

    def test_ingest_scanned_files_batch_locked_file_resilience(self, tmp_path, monkeypatch):
        doc_dir = tmp_path / "locked_test"
        doc_dir.mkdir()

        file_ok = doc_dir / "ok.txt"
        file_ok.write_text("I am accessible", encoding="utf-8")

        file_locked = doc_dir / "locked.txt"
        file_locked.write_text("I will simulate lock", encoding="utf-8")

        original_read_bytes = Path.read_bytes

        def mock_read_bytes(self):
            if "locked" in self.name:
                raise PermissionError("The process cannot access the file because it is being used by another process.")
            return original_read_bytes(self)

        monkeypatch.setattr(Path, "read_bytes", mock_read_bytes)

        summary = ingest_scanned_files_batch(
            files=[file_ok, file_locked],
            conversation_id="conv_locked",
            privacy_choice="machine_only",
            enable_now=False,
            save_to_notebook=False,
        )

        assert summary.total_files == 2
        assert summary.success_count == 1
        assert summary.fail_count == 1
        assert "ok.txt" in summary.success_files
        assert "locked.txt" in summary.failed_files
        assert "bị khóa" in summary.errors_by_file["locked.txt"]

    def test_ingest_scanned_files_batch_nonexistent_file(self, tmp_path):
        fake_file = tmp_path / "ghost.txt"
        summary = ingest_scanned_files_batch(
            files=[fake_file],
            conversation_id="conv_ghost",
            privacy_choice="machine_only",
        )
        assert summary.total_files == 1
        assert summary.success_count == 0
        assert summary.fail_count == 1
        assert summary.item_results[0].error_code == "not_found"
        assert "ghost.txt" in summary.failed_files

    def test_ingest_scanned_files_batch_oversized_file(self, tmp_path):
        doc_dir = tmp_path / "oversize_test"
        doc_dir.mkdir()

        file_big = doc_dir / "big.txt"
        file_big.write_bytes(b"A" * 2000)

        summary = ingest_scanned_files_batch(
            files=[file_big],
            conversation_id="conv_big",
            privacy_choice="machine_only",
            max_file_size=1000,
        )

        assert summary.total_files == 1
        assert summary.success_count == 0
        assert summary.fail_count == 1
        assert "vượt quá giới hạn dung lượng" in summary.errors_by_file["big.txt"]
        assert summary.item_results[0].error_code == "oversized"

    def test_ingest_duplicate_filenames_in_different_subdirs(self, tmp_path):
        root_dir = tmp_path / "dup_test"
        sub1 = root_dir / "sub1"
        sub2 = root_dir / "sub2"
        sub1.mkdir(parents=True)
        sub2.mkdir(parents=True)

        (sub1 / "notes.txt").write_text("Notes from sub1", encoding="utf-8")
        (sub2 / "notes.txt").write_text("Notes from sub2", encoding="utf-8")

        scan_res = scan_local_directory(root_dir, recursive=True)
        assert scan_res.ok
        assert scan_res.total_files == 2

        summary = ingest_scanned_files_batch(
            files=scan_res.supported_files,
            conversation_id="conv_dup",
            privacy_choice="machine_only",
            enable_now=True,
            save_to_notebook=False,
        )

        assert summary.total_files == 2
        assert summary.success_count == 2
        assert summary.fail_count == 0

        temp_sources = load_temporary_sources("conv_dup")
        assert len(temp_sources) == 2

    def test_ingest_local_folder_end_to_end(self, tmp_path):
        doc_dir = tmp_path / "full_folder"
        doc_dir.mkdir()

        (doc_dir / "docA.txt").write_text("Document Alpha", encoding="utf-8")
        (doc_dir / "docB.md").write_text("# Document Beta", encoding="utf-8")

        scan_res, summary = ingest_local_folder(
            folder_path=doc_dir,
            conversation_id="conv_full",
            privacy_choice="Chỉ dùng trên máy / không gửi AI",
            recursive=True,
            enable_now=True,
            save_to_notebook=True,
            notebook_id="nb_full",
        )

        assert scan_res.ok
        assert scan_res.supported_count() == 2
        assert summary.success_count == 2
        assert summary.fail_count == 0

        temp_sources = load_temporary_sources("conv_full")
        assert len(temp_sources) == 2
        nb_sources = load_notebook_sources("nb_full")
        assert len(nb_sources) == 2

    def test_ingest_local_folder_only_unsupported_files(self, tmp_path):
        doc_dir = tmp_path / "only_unsupported"
        doc_dir.mkdir()
        (doc_dir / "binary.bin").write_bytes(b"\x00\x01\x02")
        (doc_dir / "app.exe").write_bytes(b"MZ")

        scan_res, summary = ingest_local_folder(
            folder_path=doc_dir,
            conversation_id="conv_unsupp",
        )
        assert scan_res.ok
        assert scan_res.total_files == 2
        assert scan_res.supported_count() == 0
        assert scan_res.unsupported_count() == 2
        assert summary.total_files == 0
        assert summary.success_count == 0

    def test_ingest_local_folder_nonexistent_returns_empty_summary(self, tmp_path):
        missing_dir = tmp_path / "non_existent_folder_xyz"
        scan_res, summary = ingest_local_folder(
            folder_path=missing_dir,
            conversation_id="conv_missing",
        )
        assert not scan_res.ok
        assert summary.total_files == 0
        assert summary.success_count == 0
        assert summary.fail_count == 0

    def test_ingest_vietnamese_unicode_filenames(self, tmp_path):
        doc_dir = tmp_path / "tieng_viet"
        doc_dir.mkdir()

        f1 = doc_dir / "Báo cáo tài chính quý 1.txt"
        f1.write_text("Nội dung báo cáo tiếng Việt", encoding="utf-8")

        f2 = doc_dir / "Kế hoạch phát triển.md"
        f2.write_text("# Kế hoạch", encoding="utf-8")

        scan_res, summary = ingest_local_folder(
            folder_path=doc_dir,
            conversation_id="conv_vn",
            privacy_choice="Chỉ dùng trên máy / không gửi AI",
        )
        assert scan_res.ok
        assert scan_res.supported_count() == 2
        assert summary.success_count == 2
        assert summary.fail_count == 0
        temp_sources = load_temporary_sources("conv_vn")
        assert len(temp_sources) == 2


class TestWorkspaceChatAppFolderUI:
    def test_workspace_chat_app_has_folder_import_components(self):
        from aios_habit.workspace_chat_app import (
            scan_local_directory,
            ingest_scanned_files_batch,
            format_size_bytes,
        )
        assert callable(scan_local_directory)
        assert callable(ingest_scanned_files_batch)
        assert callable(format_size_bytes)

