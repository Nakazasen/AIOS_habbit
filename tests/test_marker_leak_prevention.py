"""Unit tests for DESKTOP-HOME-UX-MARKER-LEAK-FIX.

Verifies:
1. Universal marker stripper (strip_all_aios_markers):
   - Exact G7 fixture from screenshot (SMA JIG 1003_1 with escaped unicode \u00f3\u01b1).
   - Known markers: aios_realtime_alert, aios_log_chart_builder, aios_chat_artifact.
   - Unregistered / unknown future marker: aios_unregistered_custom_marker_2026.
   - Broken / corrupted JSON marker: <!-- aios_broken: {not json... -->.
   - Truncated / unclosed marker at EOF.
   - In all cases, stripped output MUST NOT contain "<!--", "aios_", or raw "\\u".
2. Realtime alert marker parser (parse_jig_realtime_alert_marker):
   - Correctly parses both aios_realtime_alert and aios_jig_alert_card.
   - Accurately maps Vietnamese keys: ma_jig, thong_so, chi_tiet, gia_tri, sma/sma20,
     muc_lech, so_diem_lien_tiep, thoi_diem.
   - Unescapes unicode strings into proper Vietnamese characters.
   - Returns None for broken JSON or unregistered markers (safe fallback).
3. Integration with render_chat_bubble and build_jig_realtime_card_data:
   - Full card builder with G7 fixture produces cleanly formatted card without marker leaks.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest

from aios_habit.workspace_chat_models import ChatMessage
from aios_habit.workspace_chat_ui import (
    build_jig_realtime_card_data,
    parse_jig_realtime_alert_marker,
    render_chat_bubble,
    strip_all_aios_markers,
)

# Exact message fixture from G7 screenshot (MSG-LOOP-A2 in local_cases/workspace_chat/messages.jsonl)
G7_FIXTURE_CONTENT = (
    "### 🚨 Kết luận kiểm tra cổng xu hướng SMA(20): Nguy cơ (Vi phạm)\n\n"
    "- **Thông số kiểm tra:** `takt:MeasureFieldCurvatureYellow[sec]` | JIG: `1003_1`\n"
    "- **Giá trị hiện tại:** `4.6 sec` | **SMA(20):** `4.6 sec` | **Độ lệch:** `-0.00 (-0.0%)`\n"
    "- **Căn cứ qua cổng:** `8` điểm bất thường liên tiếp lệch xa SMA(20) qua ngưỡng 2.5σ\n"
    "- **Xu hướng SMA(20):** Có xu hướng bất thường: 8 điểm liên tiếp lệch xa SMA(20). Điểm mới nhất 4.600 so với SMA 4.600.\n\n"
    "**Cảnh báo:** ⚠️ Đã kích hoạt cảnh báo xu hướng tự động theo đúng luật liên tiếp >= 3 điểm.\n"
    "*Theo tài liệu quy trình: Mở phiên trực ban công đoạn để xem biểu đồ và duyệt email cảnh báo (hoặc tương tác trực tiếp qua khung chat).*\n\n"
    '<!-- aios_jig_alert_card: {"type": "jig_realtime_alert", "card": {"loai_the": "canh_bao_realtime", '
    '"alert_id": "ALT-1003_1-takt:MeasureFieldCurvatureYellow[sec]", "jig_id": "1003_1", "ma_jig": "1003_1", '
    '"metric": "takt:MeasureFieldCurvatureYellow[sec]", "thong_so": "takt:MeasureFieldCurvatureYellow[sec]", '
    '"muc_do": "nguy_co", "chi_tiet": "C\\u00f3 xu h\\u01b0\\u1edbng b\\u1ea5t th\\u01b0\\u1eddng: 8 \\u0111i\\u1ec3m '
    'li\\u00ean ti\\u1ebfp l\\u1ec7ch xa SMA(20). \\u0110i\\u1ec3m m\\u1edbi nh\\u1ea5t 4.600 so v\\u1edbi SMA 4.600.", '
    '"gia_tri": 4.6, "don_vi": "sec", "sma": 4.6, "sma20": 4.6, "residual": -0.0, "sigma": 0.0, '
    '"muc_lech": "-0.00 (-0.0%)", "deviation_pct": null, "deviation_sigma": null, "so_diem_lien_tiep": 8, '
    '"thoi_diem": "", "timestamp": "", "nguon": "", "huong_dan": "Theo t\\u00e0i li\\u1ec7u quy tr\\u00ecnh: '
    'M\\u1edf phi\\u00ean tr\\u1ef1c ban c\\u00f4ng \\u0111o\\u1ea1n \\u0111\\u1ec3 xem bi\\u1ec3u \\u0111\\u1ed3 v\\u00e0 '
    'duy\\u1ec7t email c\\u1ea3nh b\\u00e1o (ho\\u1eb7c t\\u01b0\\u01a1ng t\\u00e1c tr\\u1ef1c ti\\u1ebfp qua khung chat)."}} -->'
)


def _assert_no_marker_leak(text: str) -> None:
    """Invariant: rendered/stripped text must never contain raw markers or raw unicode escapes."""
    assert "<!--" not in text, f"Found leaked '<!--' in: {text!r}"
    assert "-->" not in text, f"Found leaked '-->' in: {text!r}"
    assert "aios_" not in text, f"Found leaked 'aios_' in: {text!r}"
    assert "\\u" not in text, f"Found raw unicode escape '\\u' in: {text!r}"


def test_strip_all_aios_markers_g7_fixture():
    """G7 fixture text stripped must preserve clean markdown and eliminate machine marker."""
    cleaned = strip_all_aios_markers(G7_FIXTURE_CONTENT)
    _assert_no_marker_leak(cleaned)
    assert "### 🚨 Kết luận kiểm tra cổng xu hướng SMA(20): Nguy cơ (Vi phạm)" in cleaned
    assert "takt:MeasureFieldCurvatureYellow[sec]" in cleaned
    assert "JIG: `1003_1`" in cleaned
    assert "4.6 sec" in cleaned
    assert "Theo tài liệu quy trình:" in cleaned


def test_strip_all_aios_markers_known_and_unknown_markers():
    """Strip all known and unknown markers across various formats."""
    # 1. Known marker: aios_realtime_alert
    m1 = "Cảnh báo realtime\n<!-- aios_realtime_alert: {\"jig_id\": \"1003_1\", \"metric\": \"takt\"} -->\nHết cảnh báo"
    c1 = strip_all_aios_markers(m1)
    _assert_no_marker_leak(c1)
    assert "Cảnh báo realtime" in c1
    assert "Hết cảnh báo" in c1

    # 2. Known marker: aios_log_chart_builder
    m2 = "Biểu đồ sản xuất:\n<!-- aios_log_chart_builder: {\"spec_id\": \"SPEC-01\", \"chart_type\": \"line\"} -->\nNhận xét"
    c2 = strip_all_aios_markers(m2)
    _assert_no_marker_leak(c2)
    assert "Biểu đồ sản xuất:" in c2
    assert "Nhận xét" in c2

    # 3. Known marker: aios_chat_artifact
    m3 = "Báo cáo công đoạn:\n<!-- aios_chat_artifact: {\"work_id\": \"ARE-01\", \"result_path\": \"rep.md\"} -->\nXong"
    c3 = strip_all_aios_markers(m3)
    _assert_no_marker_leak(c3)
    assert "Báo cáo công đoạn:" in c3
    assert "Xong" in c3

    # 4. Unknown unregistered marker
    m4 = "Dữ liệu mới:\n<!-- aios_future_unregistered_tag: {\"any_key\": \"value\", \"raw\": \"\\u0111\\u1ec3\"} -->\nKết thúc"
    c4 = strip_all_aios_markers(m4)
    _assert_no_marker_leak(c4)
    assert "Dữ liệu mới:" in c4
    assert "Kết thúc" in c4

    # 5. Broken JSON marker
    m5 = "Phân tích:\n<!-- aios_broken_json: {this is broken json, not valid -->\nChi tiết sạch"
    c5 = strip_all_aios_markers(m5)
    _assert_no_marker_leak(c5)
    assert "Phân tích:" in c5
    assert "Chi tiết sạch" in c5

    # 6. Truncated marker cut off at EOF
    m6 = "Nội dung chuẩn <!-- aios_incomplete_cut_off: {\"type\": \"unfinished\""
    c6 = strip_all_aios_markers(m6)
    _assert_no_marker_leak(c6)
    assert c6 == "Nội dung chuẩn"


def test_parse_jig_realtime_alert_marker_g7_payload():
    """G7 fixture payload must be parsed and mapped to Vietnamese keys accurately."""
    parsed = parse_jig_realtime_alert_marker(G7_FIXTURE_CONTENT)
    assert parsed is not None
    assert parsed["jig_id"] == "1003_1"
    assert parsed["ma_jig"] == "1003_1"
    assert parsed["metric"] == "takt:MeasureFieldCurvatureYellow[sec]"
    assert parsed["thong_so"] == "takt:MeasureFieldCurvatureYellow[sec]"
    assert parsed["gia_tri"] == 4.6
    assert parsed["sma"] == 4.6
    assert parsed["so_diem_lien_tiep"] == 8
    assert parsed["muc_lech"] == "-0.00 (-0.0%)"
    assert parsed["don_vi"] == "sec"
    assert parsed["alert_id"] == "ALT-1003_1-takt:MeasureFieldCurvatureYellow[sec]"

    # Verify unicode decoding into real Vietnamese letters
    assert "Có xu hướng bất thường: 8 điểm liên tiếp" in parsed["chi_tiet"]
    assert "\\u" not in parsed["chi_tiet"]


def test_parse_jig_realtime_alert_marker_legacy_format():
    """Legacy aios_realtime_alert format must also parse accurately."""
    legacy = (
        '<!-- aios_realtime_alert: {"alert_id": "ALT-LEGACY-01", "jig_id": "JIG-202", '
        '"metric": "TotalTakt", "gia_tri": 12.4, "sma": 12.0, "muc_lech": "+3.3%", '
        '"so_diem_lien_tiep": 4, "don_vi": "sec", "chi_tiet": "Trôi dạt nền"} -->'
    )
    parsed = parse_jig_realtime_alert_marker(legacy)
    assert parsed is not None
    assert parsed["jig_id"] == "JIG-202"
    assert parsed["metric"] == "TotalTakt"
    assert parsed["gia_tri"] == 12.4
    assert parsed["sma"] == 12.0
    assert parsed["muc_lech"] == "+3.3%"
    assert parsed["so_diem_lien_tiep"] == 4


def test_parse_jig_realtime_alert_marker_broken_json_safe_fallback():
    """Corrupted JSON marker must safely return None (allowing clean text fallback)."""
    broken = '<!-- aios_jig_alert_card: {"type": "jig_realtime_alert", "card": {unclosed -->'
    parsed = parse_jig_realtime_alert_marker(broken)
    assert parsed is None


def test_build_card_from_g7_fixture_contract():
    """Full card builder with G7 values matches acceptance requirements."""
    parsed = parse_jig_realtime_alert_marker(G7_FIXTURE_CONTENT)
    assert parsed is not None

    card = build_jig_realtime_card_data(
        jig_id=parsed["jig_id"],
        metric=parsed["metric"],
        chi_tiet=parsed["chi_tiet"],
        gia_tri=parsed["gia_tri"],
        don_vi=parsed["don_vi"],
        sma=parsed["sma"],
        muc_lech=parsed["muc_lech"],
        so_diem_lien_tiep=parsed["so_diem_lien_tiep"],
        alert_id=parsed["alert_id"],
    )

    assert card["loai_the"] == "canh_bao_realtime"
    assert card["ma_jig"] == "1003_1"
    assert card["thong_so"] == "takt:MeasureFieldCurvatureYellow[sec]"
    assert card["gia_tri"] == 4.6
    assert card["sma"] == 4.6
    assert card["so_diem_lien_tiep"] == 8
    assert "Mở phiên trực ban" in card["huong_dan"]
    assert "Theo tài liệu quy trình:" in card["huong_dan"]

    # String representations must be pure UTF-8 without \u escapes
    card_str = json.dumps(card, ensure_ascii=False)
    _assert_no_marker_leak(card_str)


def test_render_chat_bubble_non_interactive_no_leak():
    """When render_interactive=False, raw marker must not leak into st.markdown."""
    msg = ChatMessage(
        id="MSG-TEST-G7",
        conversation_id="CONV-TEST",
        role="assistant",
        content=G7_FIXTURE_CONTENT,
    )

    rendered_texts: list[str] = []

    def mock_markdown(text: str, *args, **kwargs):
        rendered_texts.append(text)

    with patch("streamlit.markdown", side_effect=mock_markdown), \
         patch("streamlit.chat_message") as mock_cm, \
         patch("streamlit.html"):
        mock_cm.return_value.__enter__ = MagicMock()
        mock_cm.return_value.__exit__ = MagicMock()

        render_chat_bubble(msg, render_interactive=False)

    assert len(rendered_texts) >= 1
    for r_text in rendered_texts:
        _assert_no_marker_leak(r_text)
    assert "takt:MeasureFieldCurvatureYellow[sec]" in rendered_texts[0]


def test_render_chat_bubble_broken_marker_renders_clean_text():
    """A message with a corrupted marker must hide the marker and render clean text."""
    broken_content = "### Kết quả bình thường\nChi tiết phân tích.\n<!-- aios_jig_alert_card: {corrupted json -->"
    msg = ChatMessage(
        id="MSG-TEST-BROKEN",
        conversation_id="CONV-TEST",
        role="assistant",
        content=broken_content,
    )

    rendered_markdown: list[str] = []

    def mock_markdown(text: str, *args, **kwargs):
        rendered_markdown.append(text)

    with patch("streamlit.markdown", side_effect=mock_markdown), \
         patch("streamlit.chat_message") as mock_cm, \
         patch("streamlit.html"), \
         patch("aios_habit.citation_source_viewer.render_assistant_answer_with_citations", side_effect=lambda st_module, content, **kw: mock_markdown(content)):
        mock_cm.return_value.__enter__ = MagicMock()
        mock_cm.return_value.__exit__ = MagicMock()

        render_chat_bubble(msg, render_interactive=True)

    assert len(rendered_markdown) >= 1
    for r_text in rendered_markdown:
        _assert_no_marker_leak(r_text)
    assert "### Kết quả bình thường" in rendered_markdown[0]
