"""Tests for ticket DESKTOP-ANSWER-DISPLAY-DEDUP-HOME:
Deduplicating secondary content blocks (disclaimer line and embedded JIG chart)
in workspace answer display layer with strict idempotency.
"""

from __future__ import annotations

import base64
import inspect
import re
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from aios_habit.i18n import t
from aios_habit.production_prediction.jig_chat_wire import JigChatOutcome
from aios_habit.workspace_chat_ui import render_ai_answer_header


class MockStreamlit:
    """Captures Streamlit calls to inspect rendered UI components."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.session_state: dict[str, Any] = {}

    def caption(self, text: str, **kwargs: Any) -> None:
        self.calls.append(("caption", str(text)))

    def write(self, text: str, **kwargs: Any) -> None:
        self.calls.append(("write", str(text)))

    def success(self, text: str, **kwargs: Any) -> None:
        self.calls.append(("success", str(text)))

    def info(self, text: str, **kwargs: Any) -> None:
        self.calls.append(("info", str(text)))

    def warning(self, text: str, **kwargs: Any) -> None:
        self.calls.append(("warning", str(text)))

    def error(self, text: str, **kwargs: Any) -> None:
        self.calls.append(("error", str(text)))

    def markdown(self, text: str, **kwargs: Any) -> None:
        self.calls.append(("markdown", str(text)))

    def expander(self, title: str, expanded: bool = False) -> _MockExpanderContext:
        self.calls.append(("expander", str(title)))
        return _MockExpanderContext(self)


class _MockExpanderContext:
    def __init__(self, parent: MockStreamlit) -> None:
        self.parent = parent

    def __enter__(self) -> _MockExpanderContext:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    def write(self, text: str, **kwargs: Any) -> None:
        self.parent.write(text, **kwargs)


@pytest.fixture
def mock_st():
    st_mock = MockStreamlit()
    with patch("aios_habit.workspace_chat_ui.st", st_mock):
        yield st_mock


# ---------------------------------------------------------------------------
# 1. AI DISCLAIMER DEDUPLICATION TESTS
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("locale", ["vi", "ja", "zh-CN"])
def test_render_ai_answer_header_emits_disclaimer_exactly_once(mock_st: MockStreamlit, locale: str):
    """Verify render_ai_answer_header emits exactly one disclaimer caption."""
    render_ai_answer_header(
        source_count=1,
        source_titles=["TaiLieu.pdf"],
        ai_source="Antigravity IDE",
        model_tool_name="deepseek/deepseek-v4.1-flash",
        operational_mode="direct",
        provider_name="Command Code",
        locale=locale,
    )

    expected_disclaimer = t("ai_disclaimer", locale=locale)
    disclaimer_captions = [c[1] for c in mock_st.calls if c[0] == "caption" and expected_disclaimer in c[1]]
    assert len(disclaimer_captions) == 1, (
        f"Expected exactly 1 disclaimer caption for locale {locale}, but got {len(disclaimer_captions)}: {disclaimer_captions}"
    )


@pytest.mark.parametrize("locale", ["vi", "ja", "zh-CN"])
def test_render_ai_answer_header_idempotent_re_render(mock_st: MockStreamlit, locale: str):
    """Idempotency check: rendering header sequentially in separate passes outputs 1 disclaimer per pass."""
    for pass_idx in range(3):
        mock_st.calls.clear()
        render_ai_answer_header(
            source_count=pass_idx,
            source_titles=[],
            ai_source="Command Code",
            model_tool_name="deepseek/deepseek-v4.1-flash",
            operational_mode="external_ai",
            provider_name="Command Code",
            locale=locale,
        )
        expected_disclaimer = t("ai_disclaimer", locale=locale)
        disclaimer_captions = [c[1] for c in mock_st.calls if c[0] == "caption" and expected_disclaimer in c[1]]
        assert len(disclaimer_captions) == 1, (
            f"Pass {pass_idx}: Expected exactly 1 disclaimer caption, got {len(disclaimer_captions)}"
        )


def test_app_source_locks_no_duplicate_disclaimer_after_header():
    """Verify workspace_chat_app.py does not make duplicate calls to st.caption(t('ai_disclaimer')) after render_ai_answer_header."""
    from pathlib import Path
    app_path = Path("src/aios_habit/workspace_chat_app.py")
    assert app_path.exists()
    content = app_path.read_text(encoding="utf-8")

    # Locate both AI Answer Badge render branches
    ext_branch_idx = content.find('badge_data.get("operational_mode") == "local_grounded_fallback"')
    assert ext_branch_idx != -1

    badge_slice = content[ext_branch_idx:ext_branch_idx + 3500]

    # Check external AI branch:
    # Must call render_ai_answer_header but must NOT have st.caption(t("ai_disclaimer")) immediately after
    ext_call = re.search(
        r'render_ai_answer_header\([^)]*operational_mode="external_ai"[^)]*\)\s*\n\s*(st\.caption\(t\("ai_disclaimer"[^)]*\)\))',
        badge_slice,
    )
    assert ext_call is None, "Found redundant st.caption(t('ai_disclaimer')) immediately following external AI render_ai_answer_header"

    # Check grounded AI branch:
    grounded_call = re.search(
        r'render_ai_answer_header\([^)]*badge_data\.get\("source_count"\)[^)]*\)\s*\n(?:[^\n]*\n){1,4}\s*(st\.caption\(t\("ai_disclaimer"[^)]*\)\))',
        badge_slice,
    )
    assert grounded_call is None, "Found redundant st.caption(t('ai_disclaimer')) immediately following grounded AI render_ai_answer_header"


def test_local_fallback_retains_strict_no_disclaimer_invariant():
    """FR-030 Invariant: Local grounded fallback must never render AI disclaimer or AI header."""
    from pathlib import Path
    app_path = Path("src/aios_habit/workspace_chat_app.py")
    content = app_path.read_text(encoding="utf-8")

    local_idx = content.find('badge_data.get("operational_mode") == "local_grounded_fallback"')
    assert local_idx != -1
    next_branch_idx = content.find('elif (', local_idx)
    assert next_branch_idx != -1

    local_block = content[local_idx:next_branch_idx]
    assert "ai_disclaimer" not in local_block
    assert "render_ai_answer_header" not in local_block


# ---------------------------------------------------------------------------
# 2. JIG CHART EMBEDDING DEDUPLICATION TESTS
# ---------------------------------------------------------------------------

def test_chart_embedding_dedup_when_assistant_text_already_has_chart():
    """Verify _xu_ly_mot_y_dinh does not duplicate chart markdown when assistant_text already has base64 chart."""
    from aios_habit.workspace_chat_app import _xu_ly_mot_y_dinh
    from aios_habit.chat_intent_router import VE_BIEU_DO

    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRtest_data_bytes"
    b64_data = base64.b64encode(fake_png).decode("ascii")
    pre_embedded_md = f"Đã vẽ biểu đồ phân bố BOW_B.\n\n![biểu đồ](data:image/png;base64,{b64_data})"

    mock_outcome = JigChatOutcome(
        handled=True,
        assistant_text=pre_embedded_md,
        chart_png=fake_png,
        chart_meta={"ma_jig": "2ND-1002", "ten_chi_so": "BOW_B"},
    )

    mock_conv = MagicMock(id="conv_test_dedup_01")
    with patch("aios_habit.production_prediction.jig_chat_wire._quyet_dinh_ve_bieu_do", return_value=mock_outcome):
        result = _xu_ly_mot_y_dinh(
            VE_BIEU_DO,
            slots={},
            q_text="vẽ biểu đồ BOW_B",
            active_conversation=mock_conv,
            active_nb_id="nb_test",
        )

    assert result is not None
    chart_marker = f"data:image/png;base64,{b64_data}"
    count = result.count(chart_marker)
    assert count == 1, f"Expected chart data URI to appear exactly once, but found {count} occurrences in:\n{result}"


def test_chart_embedding_idempotence_multiple_runs():
    """Idempotency test: repeated invocation of chart handling never accumulates multiple charts."""
    from aios_habit.workspace_chat_app import _xu_ly_mot_y_dinh
    from aios_habit.chat_intent_router import VE_BIEU_DO

    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRidempotent_test"
    b64_data = base64.b64encode(fake_png).decode("ascii")
    raw_text = "Đã vẽ biểu đồ phân bố 2ND-1002."

    # First run without pre-embedded chart: outcome has raw text + chart_png
    mock_outcome = JigChatOutcome(
        handled=True,
        assistant_text=raw_text,
        chart_png=fake_png,
        chart_meta={"ma_jig": "2ND-1002", "ten_chi_so": "BOW_B"},
    )

    mock_conv = MagicMock(id="conv_test_idempotent")
    with patch("aios_habit.production_prediction.jig_chat_wire._quyet_dinh_ve_bieu_do", return_value=mock_outcome):
        result_first = _xu_ly_mot_y_dinh(
            VE_BIEU_DO,
            slots={},
            q_text="vẽ biểu đồ BOW_B",
            active_conversation=mock_conv,
            active_nb_id="nb_test",
        )

    assert result_first is not None
    chart_marker = f"data:image/png;base64,{b64_data}"
    assert result_first.count(chart_marker) == 1

    # Second run with outcome assistant_text containing the result from first run (simulating re-render / pipeline rerun)
    mock_outcome_re = JigChatOutcome(
        handled=True,
        assistant_text=result_first,
        chart_png=fake_png,
        chart_meta={"ma_jig": "2ND-1002", "ten_chi_so": "BOW_B"},
    )
    with patch("aios_habit.production_prediction.jig_chat_wire._quyet_dinh_ve_bieu_do", return_value=mock_outcome_re):
        result_second = _xu_ly_mot_y_dinh(
            VE_BIEU_DO,
            slots={},
            q_text="vẽ biểu đồ BOW_B",
            active_conversation=mock_conv,
            active_nb_id="nb_test",
        )

    assert result_second is not None
    assert result_second.count(chart_marker) == 1, (
        f"Second pass duplicated the chart! Found {result_second.count(chart_marker)} occurrences."
    )


def test_chart_session_state_updated_properly():
    """Verify _xu_ly_mot_y_dinh saves chart_png and chart_meta to session_state."""
    import streamlit as st
    from aios_habit.workspace_chat_app import _xu_ly_mot_y_dinh
    from aios_habit.chat_intent_router import VE_BIEU_DO

    fake_png = b"dummy_png_bytes"
    mock_outcome = JigChatOutcome(
        handled=True,
        assistant_text="Biểu đồ phân bố",
        chart_png=fake_png,
        chart_meta={"ma_jig": "2ND-1002", "ten_chi_so": "BOW_B"},
    )

    mock_conv = MagicMock(id="conv_test_session_state")
    with patch("aios_habit.production_prediction.jig_chat_wire._quyet_dinh_ve_bieu_do", return_value=mock_outcome):
        _xu_ly_mot_y_dinh(
            VE_BIEU_DO,
            slots={},
            q_text="vẽ biểu đồ",
            active_conversation=mock_conv,
            active_nb_id="nb_test",
        )

    assert st.session_state.get("wsc_last_chart_png") == fake_png
    assert st.session_state.get("wsc_last_chart_meta") == {"ma_jig": "2ND-1002", "ten_chi_so": "BOW_B"}


# ---------------------------------------------------------------------------
# 3. OTHER ANSWER TYPES PRESERVATION TESTS
# ---------------------------------------------------------------------------

def test_other_intents_preserved_in_xu_ly_mot_y_dinh():
    """Verify CANH_BAO_NGUONG and XU_HUONG_LOG_TINH intents continue to operate without interference."""
    from aios_habit.workspace_chat_app import _xu_ly_mot_y_dinh
    from aios_habit.chat_intent_router import CANH_BAO_NGUONG, XU_HUONG_LOG_TINH

    mock_conv = MagicMock(id="conv_test_preserve")

    # 1. XU_HUONG_LOG_TINH
    mock_outcome = JigChatOutcome(
        handled=True,
        assistant_text="Xu hướng SMA(20) bình thường",
    )
    with patch("aios_habit.production_prediction.jig_chat_wire._quyet_dinh_xu_huong_log_tinh", return_value=mock_outcome):
        res_trend = _xu_ly_mot_y_dinh(
            XU_HUONG_LOG_TINH,
            slots={},
            q_text="xu hướng log tĩnh",
            active_conversation=mock_conv,
            active_nb_id="nb_test",
        )
    assert res_trend == "Xu hướng SMA(20) bình thường"

    # 2. CANH_BAO_NGUONG
    with patch("aios_habit.threshold_alert_chat.xu_ly_cau_lenh", return_value="Cảnh báo vượt ngưỡng: 52.0"):
        res_alert = _xu_ly_mot_y_dinh(
            CANH_BAO_NGUONG,
            slots={},
            q_text="cảnh báo ngưỡng",
            active_conversation=mock_conv,
            active_nb_id="nb_test",
        )
    assert res_alert == "Cảnh báo vượt ngưỡng: 52.0"
