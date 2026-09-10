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
import streamlit as st
from streamlit.testing.v1 import AppTest

import aios_habit.workspace_chat_store as store_mod
from aios_habit.feature_flags import override_feature_flags
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
            "COLLECTIONS_FILE": store_mod.COLLECTIONS_FILE,
            "CONVERSATIONS_FILE": store_mod.CONVERSATIONS_FILE,
            "MESSAGES_FILE": store_mod.MESSAGES_FILE,
            "TEMPORARY_SOURCES_FILE": store_mod.TEMPORARY_SOURCES_FILE,
            "NOTEBOOK_SOURCES_FILE": store_mod.NOTEBOOK_SOURCES_FILE,
            "SOURCE_SELECTIONS_FILE": store_mod.SOURCE_SELECTIONS_FILE,
            "TRACES_FILE": store_mod.TRACES_FILE,
        }
        try:
            store_mod.LOCAL_CHAT_DIR = tmp_path
            store_mod.NOTEBOOKS_FILE = tmp_path / "notebooks.jsonl"
            store_mod.COLLECTIONS_FILE = tmp_path / "collections.jsonl"
            store_mod.CONVERSATIONS_FILE = tmp_path / "conversations.jsonl"
            store_mod.MESSAGES_FILE = tmp_path / "messages.jsonl"
            store_mod.TEMPORARY_SOURCES_FILE = tmp_path / "temporary_sources.jsonl"
            store_mod.NOTEBOOK_SOURCES_FILE = tmp_path / "notebook_sources.jsonl"
            store_mod.SOURCE_SELECTIONS_FILE = tmp_path / "conversation_source_selections.jsonl"
            store_mod.TRACES_FILE = tmp_path / "traces.jsonl"
            store_mod.init_chat_store()
            st.session_state.clear()
            if hasattr(st, "_main") and hasattr(st._main, "_form_data"):
                st._main._form_data = None
            if hasattr(st, "sidebar") and hasattr(st.sidebar, "_form_data"):
                st.sidebar._form_data = None
            yield tmp_path
            st.session_state.clear()
            if hasattr(st, "_main") and hasattr(st._main, "_form_data"):
                st._main._form_data = None
            if hasattr(st, "sidebar") and hasattr(st.sidebar, "_form_data"):
                st.sidebar._form_data = None
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

    def test_smoke_source_preparation_drawer_navigation(self) -> None:
        """Verify navigation into source preparation drawer runs cleanly without errors."""
        with sandboxed_chat_store():
            at = AppTest.from_file(APP_SCRIPT_PATH, default_timeout=30)
            at.session_state["wsc_show_source_prep_drawer"] = True
            at.session_state["wsc_global_ui_locale"] = "vi"
            at.run()
            assert not at.exception, f"AppTest raised unexpected exception in source prep view: {at.exception}"

    @pytest.mark.parametrize("state_scenario", [
        "normal",
        "empty",
        "pending",
        "success",
        "warning",
        "error",
    ])
    def test_smoke_six_ui_states_source_preparation_and_cases(self, state_scenario: str) -> None:
        """Verify the app renders all 6 UI lifecycle states with genuine interactive buttons and content."""
        with sandboxed_chat_store():
            at = AppTest.from_file(APP_SCRIPT_PATH, default_timeout=30)
            at.session_state["wsc_global_ui_locale"] = "vi"

            if state_scenario == "normal":
                nb = DocumentNotebook(id="sb_normal", title="Sổ ghi chép bình thường")
                store_mod.save_notebook(nb)
                at.session_state["wsc_active_notebook_id"] = nb.id
            elif state_scenario == "empty":
                pass
            elif state_scenario == "pending":
                nb = DocumentNotebook(id="sb_pending", title="Sổ đang xử lý")
                store_mod.save_notebook(nb)
                at.session_state["wsc_active_notebook_id"] = nb.id
                at.session_state["wsc_sources_pending"] = True
            elif state_scenario == "success":
                at.session_state["wsc_action_message"] = "Thao tác thành công hoàn tất!"
            elif state_scenario == "warning":
                at.session_state["wsc_action_warning"] = "Cảnh báo: Dữ liệu cần kiểm tra lại."
            elif state_scenario == "error":
                at.session_state["wsc_action_error"] = "Lỗi: Không thể kết nối dịch vụ lúc này."

            at.run()
            assert not at.exception, f"AppTest raised unexpected exception in state scenario '{state_scenario}': {at.exception}"

            # Xác thực sự hiện diện của các nút bấm tương tác thực tế trên giao diện
            assert len(at.button) > 0, f"Giao diện ở kịch bản '{state_scenario}' phải có ít nhất một nút bấm tương tác."
            button_labels = [b.label for b in at.button if b.label]
            assert len(button_labels) > 0, f"Các nút bấm ở kịch bản '{state_scenario}' phải có nhãn hiển thị."

            # Kiểm tra chống rò rỉ từ vựng tiếng Anh trên nhãn nút
            for lbl in button_labels:
                lbl_lower = lbl.lower()
                for leak in ("failed", "completed", "error", "select language", "unit serial"):
                    assert leak not in lbl_lower, f"Nút bấm chứa từ rò rỉ tiếng Anh '{leak}': {lbl}"

            # Kiểm tra nội dung đặc thù cho từng trạng thái
            if state_scenario == "normal":
                assert any("Sổ" in lbl or "cuộc trò chuyện" in lbl.lower() or "Mở" in lbl for lbl in button_labels)
            elif state_scenario == "empty":
                has_active = "wsc_active_notebook_id" in at.session_state and at.session_state["wsc_active_notebook_id"] is not None
                assert not has_active
            elif state_scenario == "pending":
                assert at.session_state["wsc_sources_pending"] is True
            elif state_scenario == "success":
                assert len(at.success) > 0, "Giao diện phải hiển thị widget thông báo thành công."
                assert "thành công" in at.success[0].value.lower()
            elif state_scenario == "warning":
                assert len(at.warning) > 0, "Giao diện phải hiển thị widget thông báo cảnh báo."
                assert "cảnh báo" in at.warning[0].value.lower()
            elif state_scenario == "error":
                assert len(at.error) > 0, "Giao diện phải hiển thị widget thông báo lỗi."
                assert "lỗi" in at.error[0].value.lower()

    def test_smoke_six_shadow_ui_states_content_and_actions(self) -> None:
        """Verify all 6 shadow UI states render genuine Vietnamese content and action buttons."""
        from aios_habit.prediction_shadow_ui import shadow_state_summary, data_gate_state_summary

        shadow_states = ["learning_shadow", "auto_shadow", "no_risk", "has_risk", "stopped", "error"]
        for st_name in shadow_states:
            summary = shadow_state_summary(st_name, detail="Chi tiết thử nghiệm trạng thái")
            assert summary["status"], f"Trạng thái '{st_name}' phải có tiêu đề trạng thái."
            assert summary["message"], f"Trạng thái '{st_name}' phải có nội dung giải thích."
            assert summary["next_step"], f"Trạng thái '{st_name}' phải có bước tiếp theo."
            assert "Bước tiếp theo:" in summary["next_step"]
            for val in summary.values():
                assert not any(leak in val.lower() for leak in ("failed", "completed", "error:", "exception", "traceback"))

        # Xác thực các nhãn nút bấm cốt lõi trong giao diện kiểm tra LSU và chạy bóng
        from aios_habit.prediction_shadow_ui import render_lsu_data_gate
        import inspect
        src = inspect.getsource(render_lsu_data_gate)
        assert 'st.button("⬅️ Quay lại Sổ tài liệu"' in src
        assert 'st.button("🚀 Bắt đầu kiểm tra cổng dữ liệu"' in src
        assert 'st.button("💾 Đăng ký gói dữ liệu vào kho dự đoán"' in src
        assert 'st.button("🚀 Bắt đầu chạy bóng thủ công"' in src
        assert 'st.button("💾 Lưu kết quả thực tế vào kho dự đoán"' in src

    def test_smoke_case_lifecycle_create_open_modify_restart_readback(self, tmp_path: Path) -> None:
        """Verify full case lifecycle: creation with citation, opening, modifying, and disk readback after restart."""
        from aios_habit.workspace_case_repository import WorkspaceCaseRepository
        from aios_habit.workspace_case_models import CaseRecord, CaseEvidenceReference

        db_path = tmp_path / "workspace_cases_smoke.sqlite"
        store1 = WorkspaceCaseRepository(db_path)

        case = CaseRecord.new(
            conversation_id="CONV_SMOKE_01",
            assistant_message_id="MSG_SMOKE_01",
            trace_id="TRC_SMOKE_01",
            evidence_digest="DIGEST_SMOKE_01",
        )
        ref = CaseEvidenceReference(
            reference_id="REF_SMOKE_01",
            case_id=case.case_id,
            trace_id="TRC_SMOKE_01",
            evidence_node_id="NODE_SMOKE_01",
            citation_id="[T1]",
            source_locator="tailieu/quy_trinh_lsu.pdf",
            source_title="Quy trình đo kiểm LSU",
            reference_digest="REF_DIGEST_SMOKE_01",
        )
        created = store1.create_case_with_evidence(case, [ref])
        assert created.case_id == case.case_id

        # Render case workspace view in AppTest
        with sandboxed_chat_store():
            at = AppTest.from_file(APP_SCRIPT_PATH, default_timeout=30)
            at.session_state["wsc_show_case_workspace"] = True
            at.session_state["wsc_active_case_id"] = created.case_id
            at.session_state["wsc_global_ui_locale"] = "vi"
            at.run()
            assert not at.exception, f"AppTest raised exception while viewing case: {at.exception}"

        # Update case status via service
        from aios_habit.workspace_case_service import WorkspaceCaseService
        from aios_habit.workspace_case_models import CASE_STATUS_IN_PROGRESS
        service1 = WorkspaceCaseService(store1)
        service1.transition_case(
            case.case_id,
            expected_version=case.version,
            new_status=CASE_STATUS_IN_PROGRESS,
            rationale="Bắt đầu phân tích điều tra.",
        )

        # Simulate full application restart: recreate repository instance from disk
        store2 = WorkspaceCaseRepository(db_path)
        reloaded = store2.load_case(case.case_id)
        assert reloaded is not None
        assert reloaded.case_id == case.case_id
        assert reloaded.status == CASE_STATUS_IN_PROGRESS
        assert reloaded.evidence_digest == "DIGEST_SMOKE_01"
        assert store2.verify_activity_chain(case.case_id) is True

        refs = store2.list_evidence_references(case.case_id)
        assert len(refs) == 1
        assert refs[0].reference_id == "REF_SMOKE_01"
        assert refs[0].source_title == "Quy trình đo kiểm LSU"

    def test_smoke_four_stages_goal_010_accessible_from_workspace_chat(self) -> None:
        """T098: Verify all 4 Goal 010 stages are accessible from Workspace Chat without unhandled exceptions."""
        with sandboxed_chat_store(), override_feature_flags(expert_knowledge_acquisition=True):
            for stage_mode in ("library_select", "interview", "review_approve", "library_publish"):
                at = AppTest.from_file(APP_SCRIPT_PATH, default_timeout=30)
                at.session_state["wsc_show_case_workspace"] = True
                at.session_state["wsc_workspace_view_mode"] = stage_mode
                at.session_state["wsc_global_ui_locale"] = "vi"
                at.run()
                assert not at.exception, f"AppTest raised exception on stage '{stage_mode}': {at.exception}"
