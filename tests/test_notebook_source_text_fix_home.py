"""Tests reproducing and verifying fix for DESKTOP-NOTEBOOK-SOURCE-TEXT-FIX-HOME.

Ticket: DESKTOP-NOTEBOOK-SOURCE-TEXT-FIX-HOME
Bug: get_workspace_chat_preparation_summary in workspace_chat_rag_v2_adapter.py
crashed with AttributeError when given a NotebookSource (which lacks .text attribute).
"""

from __future__ import annotations

import pytest

from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
from aios_habit.workspace_chat_models import NotebookSource, SOURCE_SCOPE_NOTEBOOK
from aios_habit.workspace_chat_rag_v2_adapter import (
    WorkspaceChatRagV2CanaryConfig,
    _document_id,
    _source_fingerprint,
    get_workspace_chat_preparation_summary,
    get_workspace_chat_source_preparation_status,
)


def test_reproduce_notebook_source_lacks_text_attribute():
    """Verify raw NotebookSource from store schema does not possess a .text attribute."""
    nb_src = NotebookSource(
        id="nb_raw_01",
        notebook_id="mom_opcenter",
        title="Opcenter SOP 2026",
        source_type="txt",
        content_text="Quy trình kiểm tra vận hành hệ thống Opcenter.",
    )
    # By design of the SQLite dataclass model, text attribute is not defined on NotebookSource
    assert not hasattr(nb_src, "text"), "NotebookSource should not have .text attribute initially"
    assert hasattr(nb_src, "content_text")
    assert hasattr(nb_src, "content_preview")


def test_reproduce_and_verify_preparation_summary_with_notebook_source():
    """Reproduce crash before fix and verify safe execution after fix.

    Before fix:
        AttributeError: 'NotebookSource' object has no attribute 'text'
    After fix:
        Summary dict is returned with total=1 and identity key mapped in statuses.
    """
    nb_src = NotebookSource(
        id="nb_src_sop",
        notebook_id="mom_opcenter",
        title="Huong dan van hanh C7620",
        source_type="txt",
        content_text="Chi tiet cac buoc xu ly ma loi C7620 va kẹt giay.",
    )

    summary = get_workspace_chat_preparation_summary([nb_src])
    assert isinstance(summary, dict)
    assert summary["total"] == 1
    assert f"notebook:{nb_src.id}" in summary["statuses"]
    assert "preparation_state" in summary
    assert "errors" in summary


def test_preparation_summary_with_empty_notebook_source():
    """A NotebookSource with empty content_text and preview is safely ignored (total=0)."""
    nb_empty = NotebookSource(
        id="nb_empty_01",
        notebook_id="mom_opcenter",
        title="Tai lieu trong",
        source_type="txt",
        content_text="",
        content_preview="",
    )

    summary = get_workspace_chat_preparation_summary([nb_empty])
    assert isinstance(summary, dict)
    assert summary["total"] == 0


def test_preparation_summary_with_content_preview_fallback():
    """When content_text is empty, content_preview is used as fallback text."""
    nb_preview_only = NotebookSource(
        id="nb_preview_01",
        notebook_id="mom_opcenter",
        title="Ban xem truoc",
        source_type="pdf",
        content_text="",
        content_preview="Noi dung tom tat xem truoc cua tai lieu SOP.",
    )

    summary = get_workspace_chat_preparation_summary([nb_preview_only])
    assert isinstance(summary, dict)
    assert summary["total"] == 1
    assert f"notebook:{nb_preview_only.id}" in summary["statuses"]


def test_preparation_summary_preserves_context_source_behavior():
    """Existing behavior with WorkspaceAIContextSource is 100% preserved."""
    ctx_src = WorkspaceAIContextSource(
        source_id="ctx_src_01",
        source_scope="temporary",
        source_type="plain_text",
        title="Ghi chu tam thoi",
        privacy_label="local_only",
        text="Noi dung ghi chu kiem tra he thong.",
        included_chars=37,
    )

    summary = get_workspace_chat_preparation_summary([ctx_src])
    assert isinstance(summary, dict)
    assert summary["total"] == 1
    assert "temporary:ctx_src_01" in summary["statuses"]


def test_preparation_summary_mixed_sources():
    """Both WorkspaceAIContextSource and NotebookSource can be processed together seamlessly."""
    ctx_src = WorkspaceAIContextSource(
        source_id="ctx_01",
        source_scope="temporary",
        source_type="plain_text",
        title="Ghi chu",
        privacy_label="local_only",
        text="Van ban tam",
        included_chars=11,
    )
    nb_src = NotebookSource(
        id="nb_01",
        notebook_id="mom_opcenter",
        title="Tai lieu so tay",
        source_type="txt",
        content_text="Van ban so tay",
    )

    summary = get_workspace_chat_preparation_summary([ctx_src, nb_src])
    assert isinstance(summary, dict)
    assert summary["total"] == 2
    assert "temporary:ctx_01" in summary["statuses"]
    assert "notebook:nb_01" in summary["statuses"]


def test_get_workspace_chat_source_preparation_status_with_notebook_source():
    """get_workspace_chat_source_preparation_status accepts NotebookSource safely."""
    nb_src = NotebookSource(
        id="nb_status_01",
        notebook_id="mom_opcenter",
        title="Quy trinh",
        source_type="txt",
        content_text="Thong tin huong dan",
    )
    statuses = get_workspace_chat_source_preparation_status([nb_src])
    assert isinstance(statuses, dict)
    assert f"notebook:{nb_src.id}" in statuses


def test_source_fingerprint_and_document_id_with_notebook_source():
    """_source_fingerprint and _document_id safely handle NotebookSource without .text attribute."""
    nb_src = NotebookSource(
        id="nb_fp_01",
        notebook_id="mom_opcenter",
        title="Huong dan",
        source_type="txt",
        content_text="Kiem tra ham ma bam van ban.",
    )
    doc_id = _document_id(nb_src)
    assert doc_id.startswith("wsc-")

    fp = _source_fingerprint(nb_src)
    assert doc_id in fp
    assert len(fp.split(":")) == 3


def test_duck_typed_source_without_text_attribute():
    """A custom duck-typed object lacking .text but having content_text is safely supported."""
    class CustomSource:
        def __init__(self):
            self.id = "custom_99"
            self.title = "Custom Duck Source"
            self.content_text = "Custom extracted content text"
            self.source_scope = "custom_scope"

    custom_src = CustomSource()
    assert not hasattr(custom_src, "text")

    summary = get_workspace_chat_preparation_summary([custom_src])
    assert isinstance(summary, dict)
    assert summary["total"] == 1
    assert "custom_scope:custom_99" in summary["statuses"]
