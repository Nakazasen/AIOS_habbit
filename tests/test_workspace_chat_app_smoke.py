# -*- coding: utf-8 -*-
"""Streamlit AppTest Smoke Tests for AIOS Workspace Chat App (Sandboxed).

Verifies that workspace_chat_app.py executes cleanly without uncaught exceptions
under various runtime lifecycle states:
1. Default home screen (no notebook selected).
2. Active notebook and active conversation selected.
3. Multilingual UI switches across Vietnamese (vi), Japanese (ja), and Simplified Chinese (zh-CN).

Guarantees:
- Runs in an isolated tempfile.TemporaryDirectory sandbox via path redirection.
- Asserts that the production local_cases/workspace_chat directory is 100% byte-for-byte unmodified before/after tests.
"""
import contextlib
import tempfile
from pathlib import Path
from typing import Generator
import pytest
from streamlit.testing.v1 import AppTest

import aios_habit.workspace_chat_store as store_mod
from aios_habit.workspace_chat_models import (
    DocumentNotebook,
    WorkspaceConversation,
)

APP_SCRIPT_PATH = "src/aios_habit/workspace_chat_app.py"


@contextlib.contextmanager
def sandboxed_chat_store() -> Generator[Path, None, None]:
    """Redirect all workspace_chat_store global paths to a temporary directory sandbox."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / "workspace_chat"
        orig_paths = {
            "LOCAL_CHAT_DIR": store_mod.LOCAL_CHAT_DIR,
            "NOTEBOOKS_FILE": store_mod.NOTEBOOKS_FILE,
            "CONVERSATIONS_FILE": store_mod.CONVERSATIONS_FILE,
            "MESSAGES_FILE": store_mod.MESSAGES_FILE,
            "TEMPORARY_SOURCES_FILE": store_mod.TEMPORARY_SOURCES_FILE,
            "NOTEBOOK_SOURCES_FILE": store_mod.NOTEBOOK_SOURCES_FILE,
            "SOURCE_SELECTIONS_FILE": store_mod.SOURCE_SELECTIONS_FILE,
        }
        try:
            store_mod.LOCAL_CHAT_DIR = tmp_path
            store_mod.NOTEBOOKS_FILE = tmp_path / "notebooks.jsonl"
            store_mod.CONVERSATIONS_FILE = tmp_path / "conversations.jsonl"
            store_mod.MESSAGES_FILE = tmp_path / "messages.jsonl"
            store_mod.TEMPORARY_SOURCES_FILE = tmp_path / "temporary_sources.jsonl"
            store_mod.NOTEBOOK_SOURCES_FILE = tmp_path / "notebook_sources.jsonl"
            store_mod.SOURCE_SELECTIONS_FILE = tmp_path / "conversation_source_selections.jsonl"
            store_mod.init_chat_store()
            yield tmp_path
        finally:
            for k, v in orig_paths.items():
                setattr(store_mod, k, v)


def _snapshot_real_store() -> dict[str, bytes]:
    """Capture byte-for-byte snapshot of production local_cases/workspace_chat."""
    store_dir = Path("local_cases/workspace_chat")
    snapshot = {}
    if store_dir.exists():
        for p in sorted(store_dir.rglob("*")):
            if p.is_file():
                rel = str(p.relative_to(store_dir))
                snapshot[rel] = p.read_bytes()
    return snapshot


@pytest.fixture(autouse=True)
def guard_real_store_integrity():
    """Verify local_cases/workspace_chat is strictly identical before and after each test."""
    before = _snapshot_real_store()
    yield
    after = _snapshot_real_store()
    assert before == after, "Violation: Production local_cases/workspace_chat was modified during smoke test!"


class TestWorkspaceChatAppSmoke:
    """Streamlit AppTest smoke tests in isolated sandbox."""

    def test_smoke_home_screen_no_notebook_selected(self) -> None:
        """Verify the app boots and renders the home notebook management screen with zero exceptions."""
        with sandboxed_chat_store():
            at = AppTest.from_file(APP_SCRIPT_PATH, default_timeout=30)
            at.run()
            assert not at.exception, f"AppTest raised unexpected exception on home screen: {at.exception}"

    def test_smoke_active_notebook_and_conversation_selected(self) -> None:
        """Verify the app renders the chat interface when a notebook and conversation are active."""
        with sandboxed_chat_store():
            nb = DocumentNotebook(
                id="sandbox_nb_active",
                title="Sandbox Notebook Test",
                description="Automated sandboxed smoke testing notebook",
            )
            store_mod.save_notebook(nb)
            conv = WorkspaceConversation(
                id="sandbox_conv_active",
                notebook_id=nb.id,
                title="Sandbox Conversation Test",
            )
            store_mod.save_conversation(conv)

            at = AppTest.from_file(APP_SCRIPT_PATH, default_timeout=30)
            at.session_state["wsc_active_notebook_id"] = nb.id
            at.session_state["wsc_active_conversation_id"] = conv.id
            at.run()
            assert not at.exception, f"AppTest raised unexpected exception in active notebook view: {at.exception}"

    @pytest.mark.parametrize("locale", ["vi", "ja", "zh-CN"])
    def test_smoke_multilingual_locales(self, locale: str) -> None:
        """Verify the app renders cleanly in Vietnamese, Japanese, and Simplified Chinese."""
        with sandboxed_chat_store():
            nb = DocumentNotebook(
                id=f"sandbox_nb_{locale}",
                title=f"Sandbox Notebook {locale}",
                description=f"Notebook for {locale} sandboxed smoke test",
            )
            store_mod.save_notebook(nb)
            conv = WorkspaceConversation(
                id=f"sandbox_conv_{locale}",
                notebook_id=nb.id,
                title=f"Sandbox Conv {locale}",
                ui_locale=locale,
                answer_language=locale,
            )
            store_mod.save_conversation(conv)

            at = AppTest.from_file(APP_SCRIPT_PATH, default_timeout=30)
            at.session_state["wsc_active_notebook_id"] = nb.id
            at.session_state["wsc_active_conversation_id"] = conv.id
            at.session_state["wsc_global_ui_locale"] = locale
            at.session_state["wsc_global_answer_language"] = locale
            at.run()
            assert not at.exception, f"AppTest raised unexpected exception in locale '{locale}': {at.exception}"
