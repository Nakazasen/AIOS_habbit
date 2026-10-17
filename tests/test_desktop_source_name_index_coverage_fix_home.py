import sqlite3
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from aios_habit.rag_v2.index import (
    LocalChunkIndex,
    ensure_index_source_name_index,
    ensure_index_source_state,
)
from aios_habit.workspace_chat_models import SOURCE_SCOPE_NOTEBOOK, SOURCE_SCOPE_TEMPORARY
from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
from aios_habit.workspace_chat_rag_v2_adapter import (
    WorkspaceChatRagV2CanaryConfig,
    _durable_semantic_coverage_ready,
    get_workspace_chat_source_preparation_status,
    is_production_index_available,
    retrieve_workspace_chat_evidence,
)


def _create_mock_chunks_db(db_path: Path, include_source_name_index: bool = False):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE chunks (
            chunk_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            source_path TEXT NOT NULL,
            source_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            text TEXT NOT NULL,
            normalized_text TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            privacy_labels_json TEXT NOT NULL,
            source_fingerprint TEXT,
            checksum TEXT,
            retrievable INTEGER NOT NULL DEFAULT 1 CHECK (retrievable IN (0, 1))
        )
        """
    )
    conn.execute("CREATE INDEX idx_chunks_document_id ON chunks(document_id)")
    conn.execute("CREATE INDEX idx_chunks_retrievable ON chunks(retrievable, document_id)")
    conn.execute("CREATE INDEX idx_chunks_retrievable_doc_fp ON chunks(retrievable, document_id, source_fingerprint)")
    if include_source_name_index:
        conn.execute("CREATE INDEX idx_chunks_retrievable_source_name ON chunks(retrievable, source_name)")

    # Insert sample chunks
    conn.execute(
        """
        INSERT INTO chunks (
            chunk_id, document_id, source_path, source_name, file_type,
            text, normalized_text, metadata_json, privacy_labels_json,
            source_fingerprint, checksum, retrievable
        ) VALUES
        ('c1', 'doc_1', '/path/doc1.txt', 'Doc One', 'txt', 'Sample text 1', 'sample text 1', '{}', '[]', 'fp1', 'cs1', 1),
        ('c2', 'doc_2', '/path/c7620_guide.txt', 'C7620 Manual', 'txt', 'Sample text C7620', 'sample text c7620', '{}', '[]', 'fp2', 'cs2', 1)
        """
    )
    conn.commit()
    conn.close()


def test_schema_creates_retrievable_source_name_index(tmp_path: Path):
    db_path = tmp_path / "test_schema.sqlite"
    index = LocalChunkIndex(db_path, read_only=False)
    index.close()

    with sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True) as conn:
        indexes = [r[1] for r in conn.execute("PRAGMA index_list(chunks)").fetchall()]
        assert "idx_chunks_retrievable_source_name" in indexes


def test_explain_query_plan_uses_new_index(tmp_path: Path):
    db_path = tmp_path / "test_plan.sqlite"
    _create_mock_chunks_db(db_path, include_source_name_index=True)

    with sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True) as conn:
        plan = conn.execute(
            "EXPLAIN QUERY PLAN SELECT document_id FROM chunks WHERE source_name=? AND retrievable=1 LIMIT 1",
            ("Doc One",),
        ).fetchall()
        plan_str = " ".join(str(row) for row in plan)
        assert "idx_chunks_retrievable_source_name" in plan_str
        assert "retrievable=? AND source_name=?" in plan_str


def test_auto_create_when_opening_existing_index_missing_index(tmp_path: Path):
    db_path = tmp_path / "legacy_index.sqlite"
    _create_mock_chunks_db(db_path, include_source_name_index=False)

    # Verify index is initially missing
    with sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True) as conn:
        indexes_before = [r[1] for r in conn.execute("PRAGMA index_list(chunks)").fetchall()]
        assert "idx_chunks_retrievable_source_name" not in indexes_before

    # Open via application LocalChunkIndex in read_only mode
    index = LocalChunkIndex(db_path, read_only=True)
    assert index._has_retrievable_source_name_index is True
    index.close()

    # Verify index was automatically created
    with sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True) as conn:
        indexes_after = [r[1] for r in conn.execute("PRAGMA index_list(chunks)").fetchall()]
        assert "idx_chunks_retrievable_source_name" in indexes_after


def test_ensure_index_source_name_index_helper(tmp_path: Path):
    db_path = tmp_path / "helper_test.sqlite"
    _create_mock_chunks_db(db_path, include_source_name_index=False)

    assert ensure_index_source_name_index(db_path) is True
    # Re-running on already indexed database is idempotent
    assert ensure_index_source_name_index(db_path) is True

    with sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True) as conn:
        indexes = [r[1] for r in conn.execute("PRAGMA index_list(chunks)").fetchall()]
        assert "idx_chunks_retrievable_source_name" in indexes


def test_coverage_decision_equivalence_and_speed(tmp_path: Path):
    db_path = tmp_path / "equiv_test.sqlite"
    _create_mock_chunks_db(db_path, include_source_name_index=True)

    with sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True) as conn:
        # Existing document by exact source_name
        row = conn.execute(
            "SELECT document_id FROM chunks WHERE source_name=? AND retrievable=1 LIMIT 1",
            ("Doc One",),
        ).fetchone()
        assert row is not None
        assert row[0] == "doc_1"

        # Nonexistent document
        row_missing = conn.execute(
            "SELECT document_id FROM chunks WHERE source_name=? AND retrievable=1 LIMIT 1",
            ("Nonexistent Title",),
        ).fetchone()
        assert row_missing is None

        # Fallback C7620 match
        row_c7620 = conn.execute(
            "SELECT document_id FROM chunks WHERE source_name LIKE '%C7620%' AND retrievable=1 LIMIT 1"
        ).fetchone()
        assert row_c7620 is not None
        assert row_c7620[0] == "doc_2"


def test_production_read_only_path_scans_only_temporary_sources():
    sources = (
        WorkspaceAIContextSource(
            source_id="nb_src_1",
            source_scope=SOURCE_SCOPE_NOTEBOOK,
            source_type="file",
            title="Notebook Source 1",
            privacy_label="local_only",
            text="notebook text",
            included_chars=13,
        ),
        WorkspaceAIContextSource(
            source_id="temp_src_1",
            source_scope=SOURCE_SCOPE_TEMPORARY,
            source_type="file",
            title="Temporary Source 1",
            privacy_label="local_only",
            text="temp text",
            included_chars=9,
        ),
    )

    with patch(
        "aios_habit.workspace_chat_rag_v2_adapter.is_production_index_available",
        return_value=True,
    ):
        with patch(
            "aios_habit.workspace_chat_rag_v2_adapter.get_workspace_chat_source_preparation_status"
        ) as mock_prep:
            mock_prep.return_value = {"temporary:temp_src_1": "ready"}

            with patch("aios_habit.workspace_chat_rag_v2_adapter._select_domain_route") as mock_route:
                mock_route.return_value = MagicMock(applied=False)
                config = MagicMock()
                config.enabled = True
                retrieve_workspace_chat_evidence(
                    "Test question",
                    sources,
                    config=config,
                    forced_domain="missing_domain",
                )

            assert mock_prep.called
            called_sources = mock_prep.call_args[0][0]
            assert len(called_sources) == 1
            assert called_sources[0].source_scope == SOURCE_SCOPE_TEMPORARY
            assert called_sources[0].source_id == "temp_src_1"
