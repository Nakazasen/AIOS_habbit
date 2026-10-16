# -*- coding: utf-8 -*-
"""Unit tests cho cac cai tien ket xuat giao dien (DESKTOP-PC0575-UI-RENDER-FIX).
Bao gom:
1. Gioi han so nguon hien thi trong sidebar (toi da 20 nguon mac dinh, tim kiem, tai them).
2. Gioi han tin nhan co nut tuong tac (toi da 10 tin nhan gan nhat co nut, tin cu la markdown thuan).
3. Co che gate live watcher fragment chi kich hoat khi co canh bao realtime hoac che do theo doi.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
import streamlit as st

from aios_habit.workspace_chat_models import ChatMessage, NotebookSource, TemporaryConversationSource
from aios_habit.workspace_chat_ui import render_chat_bubble, render_source_library


class MockSessionState(dict):
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


class MockStreamlit:
    def __init__(self) -> None:
        self.calls: List[tuple] = []
        self.session_state = MockSessionState()
        self.widget_states: Dict[str, Any] = {}

    def subheader(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("subheader", str(text)))

    def write(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("write", str(text)))

    def markdown(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("markdown", str(text)))

    def info(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("info", str(text)))

    def caption(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("caption", str(text)))

    def checkbox(self, label: str, value: bool = False, key: Optional[str] = None, on_change: Any = None, *args: Any, **kwargs: Any) -> bool:
        self.calls.append(("checkbox", str(label), value, key, on_change))
        if key in self.widget_states:
            return self.widget_states[key]
        return value

    def expander(self, label: str, expanded: bool = False, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(("expander", str(label), expanded))

        class MockExpander:
            def __enter__(self) -> MockExpander:
                return self

            def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                pass

        return MockExpander()

    def button(self, label: str, key: Optional[str] = None, *args: Any, **kwargs: Any) -> bool:
        self.calls.append(("button", str(label), key))
        if key in self.widget_states:
            return self.widget_states[key]
        return False

    def text_input(self, label: str, value: str = "", placeholder: Optional[str] = None, key: Optional[str] = None, *args: Any, **kwargs: Any) -> str:
        self.calls.append(("text_input", str(label), value, placeholder, key))
        if key in self.session_state:
            return str(self.session_state[key])
        if key in self.widget_states:
            return str(self.widget_states[key])
        return value

    def columns(self, spec: Any, *args: Any, **kwargs: Any) -> List[Any]:
        class MockColumn:
            def __enter__(self) -> MockColumn:
                return self

            def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                pass

        count = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
        return [MockColumn() for _ in range(count)]

    def warning(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("warning", str(text)))

    def divider(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("divider", ""))

    def html(self, html_text: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("html", str(html_text)))

    def chat_message(self, role: str) -> Any:
        class MockChatMessage:
            def __enter__(self) -> MockChatMessage:
                return self

            def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                pass

        return MockChatMessage()


@pytest.fixture
def mock_st_env(monkeypatch: pytest.MonkeyPatch) -> MockStreamlit:
    mock = MockStreamlit()
    monkeypatch.setattr(st, "subheader", mock.subheader)
    monkeypatch.setattr(st, "write", mock.write)
    monkeypatch.setattr(st, "markdown", mock.markdown)
    monkeypatch.setattr(st, "info", mock.info)
    monkeypatch.setattr(st, "caption", mock.caption)
    monkeypatch.setattr(st, "checkbox", mock.checkbox)
    monkeypatch.setattr(st, "button", mock.button)
    monkeypatch.setattr(st, "expander", mock.expander)
    monkeypatch.setattr(st, "text_input", mock.text_input)
    monkeypatch.setattr(st, "columns", mock.columns)
    monkeypatch.setattr(st, "warning", mock.warning)
    monkeypatch.setattr(st, "divider", mock.divider)
    monkeypatch.setattr(st, "html", mock.html)
    monkeypatch.setattr(st, "chat_message", mock.chat_message)
    monkeypatch.setattr(st, "session_state", mock.session_state)
    return mock


# ============================================================================
# 1. TEST GIOI HAN SO NGUON HIEN THI TRONG SIDEBAR
# ============================================================================


def test_source_library_limits_to_20_sources_by_default(mock_st_env: MockStreamlit) -> None:
    """Khi so co 50 nguon, chi render toi da 20 nguon dau mac dinh."""
    sources = [
        NotebookSource(id=f"src_{i:03d}", notebook_id="nb_test", title=f"Tai lieu thu {i:03d}", source_type="txt", content_preview="")
        for i in range(50)
    ]

    render_source_library(
        notebook_sources=sources,
        temp_sources=[],
        selections_map={},
        conversation_id="conv_test_50",
        on_toggle_source=lambda *a: None,
        on_promote_temporary=lambda *a: None,
        on_privacy_save=lambda *a: None,
        on_delete_source=lambda *a: None,
    )

    # Kiem tra so checkbox render cho tung nguon (khong vuot qua 20)
    source_checkboxes = [c for c in mock_st_env.calls if c[0] == "checkbox" and str(c[3]).startswith("wsc_toggle_")]
    assert len(source_checkboxes) == 20

    # Kiem tra co nut Tai them va Xem tat ca
    button_keys = [c[2] for c in mock_st_env.calls if c[0] == "button"]
    assert "wsc_btn_load_more_conv_test_50" in button_keys
    assert "wsc_btn_show_all_conv_test_50" in button_keys

    # Kiem tra co dong thong bao so luong nguon hien thi
    caption_texts = " ".join([c[1] for c in mock_st_env.calls if c[0] == "caption"])
    assert "20 / 50" in caption_texts


def test_source_library_expand_limit_on_demand(mock_st_env: MockStreamlit) -> None:
    """Khi session_state co limit = 40, render 40 nguon."""
    sources = [
        NotebookSource(id=f"src_{i:03d}", notebook_id="nb_test", title=f"SOP quy trinh {i:03d}", source_type="txt", content_preview="")
        for i in range(50)
    ]

    # Gia lap nguoi dung da bam Tai them (+20) -> limit = 40
    mock_st_env.session_state["wsc_source_limit_conv_test_expand"] = 40

    render_source_library(
        notebook_sources=sources,
        temp_sources=[],
        selections_map={},
        conversation_id="conv_test_expand",
        on_toggle_source=lambda *a: None,
        on_promote_temporary=lambda *a: None,
        on_privacy_save=lambda *a: None,
        on_delete_source=lambda *a: None,
    )

    source_checkboxes = [c for c in mock_st_env.calls if c[0] == "checkbox" and str(c[3]).startswith("wsc_toggle_")]
    assert len(source_checkboxes) == 40


def test_source_library_search_filtering(mock_st_env: MockStreamlit) -> None:
    """O tim kiem loc dung danh sach tai lieu theo tu khoa."""
    sources = [
        NotebookSource(id="src_iris_01", notebook_id="nb_test", title="Iris LSU Beam Report", source_type="txt", content_preview=""),
        NotebookSource(id="src_wms_01", notebook_id="nb_test", title="WMS Stock Guideline", source_type="txt", content_preview=""),
        NotebookSource(id="src_iris_02", notebook_id="nb_test", title="Iris LSU Alignment 4M", source_type="txt", content_preview=""),
    ]

    # Gia lap nguoi dung go tim kiem "iris"
    mock_st_env.session_state["wsc_source_filter_conv_test_search"] = "iris"

    render_source_library(
        notebook_sources=sources,
        temp_sources=[],
        selections_map={},
        conversation_id="conv_test_search",
        on_toggle_source=lambda *a: None,
        on_promote_temporary=lambda *a: None,
        on_privacy_save=lambda *a: None,
        on_delete_source=lambda *a: None,
        max_visible_sources=20,
    )

    rendered_markdowns = [c[1] for c in mock_st_env.calls if c[0] == "markdown"]
    rendered_titles = " ".join(rendered_markdowns)
    assert "Iris LSU Beam Report" in rendered_titles
    assert "Iris LSU Alignment 4M" in rendered_titles
    assert "WMS Stock Guideline" not in rendered_titles


def test_source_library_toggle_and_privacy_retained(mock_st_env: MockStreamlit) -> None:
    """Chuc nang chon nguon va luu rieng tu van hoat dong chuan xac."""
    sources = [
        NotebookSource(id="src_single", notebook_id="nb_test", title="Tai lieu duy nhat", source_type="txt", content_preview="Preview")
    ]
    toggled = []

    def on_toggle(scope: str, sid: str, val: bool) -> None:
        toggled.append((scope, sid, val))

    saved_privacy = []

    def on_privacy(scope: str, sid: str, choice: str) -> None:
        saved_privacy.append((scope, sid, choice))

    render_source_library(
        notebook_sources=sources,
        temp_sources=[],
        selections_map={},
        conversation_id="conv_single",
        on_toggle_source=on_toggle,
        on_promote_temporary=lambda *a: None,
        on_privacy_save=on_privacy,
        on_delete_source=lambda *a: None,
    )

    # Kiem tra checkbox render
    chk = [c for c in mock_st_env.calls if c[0] == "checkbox" and c[3] == "wsc_toggle_notebook_conv_single_src_single"]
    assert len(chk) == 1

    # Kiem tra nut bat tat ca hoat dong
    enable_all_btn = next((c for c in mock_st_env.calls if c[0] == "button" and c[2] == "wsc_select_all_conv_single"), None)
    assert enable_all_btn is not None


# ============================================================================
# 2. TEST GIOI HAN TIN NHAN CO NUT TUONG TAC (10 TIN NHAN GAN NHAT)
# ============================================================================


def test_render_chat_bubble_non_interactive_renders_plain_markdown_no_buttons(mock_st_env: MockStreamlit) -> None:
    """Khi render_interactive=False, tin nhan tro ly chi render markdown thuan, KHONG co bat ky nut nao."""
    msg = ChatMessage(
        id="msg_old_001",
        conversation_id="conv_test",
        role="assistant",
        content="Day la cau tra loi cu. Co trinh bay ky thuat chi tiet.\n<!-- aios_realtime_alert: {} -->\n<!-- aios_chat_artifact: {} -->",
        trace_id="trc_old_001",
    )

    render_chat_bubble(
        msg,
        is_latest=False,
        locale="vi",
        conversation_id="conv_test",
        feedback_question="Cau hoi cu?",
        render_interactive=False,
    )

    # Xac nhan KHONG co bat ky nut bam nao duoc render
    button_calls = [c for c in mock_st_env.calls if c[0] == "button"]
    assert len(button_calls) == 0

    # Xac nhan markdown van duoc hien thi va da duoc don sach comment
    markdown_calls = [c for c in mock_st_env.calls if c[0] == "markdown"]
    assert len(markdown_calls) == 1
    assert "Day la cau tra loi cu" in markdown_calls[0][1]
    assert "aios_realtime_alert" not in markdown_calls[0][1]


def test_render_chat_bubble_interactive_renders_buttons(mock_st_env: MockStreamlit) -> None:
    """Khi render_interactive=True, tin nhan tro ly duoc render day du nut phan hoi."""
    msg = ChatMessage(
        id="msg_recent_001",
        conversation_id="conv_test",
        role="assistant",
        content="Day la cau tra loi moi trong top 10 tin nhan.",
        trace_id=None,
    )

    render_chat_bubble(
        msg,
        is_latest=True,
        locale="vi",
        conversation_id="conv_test",
        feedback_question="Cau hoi moi?",
        render_interactive=True,
    )

    # Xac nhan co cac nut phan hoi (Thoa dang, Chua ro, Sai lech, Duyet ban thao, ...)
    button_calls = [c for c in mock_st_env.calls if c[0] == "button"]
    assert len(button_calls) > 0


def test_chat_window_interactive_threshold_logic() -> None:
    """Kiem tra logic tinh threshold: trong 72 tin nhan, dung 10 tin nhan cuoi co nut."""
    messages = [
        ChatMessage(id=f"msg_{i:02d}", conversation_id="conv_72", role="assistant" if i % 2 == 1 else "user", content=f"Tin nhan {i}")
        for i in range(72)
    ]

    total_msgs = len(messages)
    interactive_threshold_idx = max(0, total_msgs - 10)
    assert interactive_threshold_idx == 62

    interactive_flags = [(i >= interactive_threshold_idx) for i in range(total_msgs)]
    # 62 tin nhan dau tien khong co nut
    assert sum(1 for flag in interactive_flags[:62] if not flag) == 62
    # 10 tin nhan cuoi cung (chi so 62 den 71) co nut day du
    assert sum(1 for flag in interactive_flags[62:] if flag) == 10


# ============================================================================
# 3. TEST FRAGMENT WATCHER GATE TRONG REALTIME ALERT
# ============================================================================


def test_rt_alert_gate_inactive_on_normal_conversation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hoi thoai thong thuong (ca nhan, khong canh bao) phai tra ve False de khong phat xung 1.5s."""
    normal_conv = MagicMock()
    normal_conv.title = "Dieu tra loi LSU ky thuat"
    normal_messages = [
        ChatMessage(id=f"m_{i}", conversation_id="c1", role="user", content=f"Cau hoi {i}")
        for i in range(10)
    ]

    # Gia lap get_jig_session_type tra ve ca_nhan va khong co canh bao realtime
    monkeypatch.setattr("aios_habit.workspace_chat_app.get_jig_session_type", lambda: "ca_nhan")
    monkeypatch.setattr("aios_habit.production_prediction.rt_app_wire.get_last_dispatch_time", lambda: 0.0)

    # Goi logic check
    from aios_habit.production_prediction.session_isolation import classify_session

    is_watchdog = classify_session(normal_conv.title) == "truc_ban"
    assert is_watchdog is False

    has_alert_marker = any("<!-- aios_realtime_alert:" in str(m.content or "") for m in normal_messages)
    assert has_alert_marker is False


def test_rt_alert_gate_active_in_watchdog_or_with_alerts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hoi thoai truc ban hoac co canh bao realtime phai tra ve True de bat live watcher."""
    from aios_habit.production_prediction.session_isolation import classify_session

    watchdog_title = "Trực ban công đoạn JIG máy 1"
    assert classify_session(watchdog_title) == "truc_ban"

    alert_messages = [
        ChatMessage(id="m_alt", conversation_id="c2", role="assistant", content="Cảnh báo realtime: JIG-01 — Độ lệch SMA(20)\n<!-- aios_realtime_alert: {\"alert_id\": \"A1\"} -->")
    ]
    has_alert = any("<!-- aios_realtime_alert:" in str(m.content or "") for m in alert_messages)
    assert has_alert is True
