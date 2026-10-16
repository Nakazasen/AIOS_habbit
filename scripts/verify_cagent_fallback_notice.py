"""Verification script for DESKTOP-PC0575-CAGENT-FALLBACK-NOTICE-FIX.
Simulates C-Agent timeout / error failover and verifies fallback notice display.
"""

from __future__ import annotations

import os
import sys

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from types import SimpleNamespace

# Ensure repo root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from aios_habit.cagent_api import CAgentResponse
from aios_habit import antigravity_bridge as bridge
from aios_habit.workspace_chat_ui import (
    format_fallback_notice,
    render_fallback_notice,
    should_show_fallback_notice,
)


class DummyStreamlit:
    def __init__(self):
        self.warnings = []
        self.successes = []

    def warning(self, text):
        self.warnings.append(text)
        print(f"[UI RENDER - ST.WARNING] ⚠️  {text}")

    def success(self, text):
        self.successes.append(text)
        print(f"[UI RENDER - ST.SUCCESS] 📄 {text}")


def run_verification():
    print("=" * 80)
    print("XÁC MINH HIỂN THỊ CẢNH BÁO RƠI LÀN TỪ C-AGENT XUỐNG TỔNG HỢP CỤC BỘ")
    print("Mã vé: DESKTOP-PC0575-CAGENT-FALLBACK-NOTICE-FIX")
    print("=" * 80)

    # 1. Simulate Fallback Scenario (C-Agent timeout)
    print("\n[KỊCH BẢN 1: TÍCH CỰC] Người dùng ghim C-Agent, C-Agent bị timeout 60s -> Rơi làn cục bộ")
    badge_cagent_timeout = {
        "conversation_id": "CONV-9C730D76",
        "type": "ai_answered",
        "source_count": 20,
        "source_titles": ["Tài liệu LSU 01", "Tài liệu LSU 02"],
        "ai_source": "Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình",
        "bridge": "Trích xuất cục bộ",
        "provider": "Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình",
        "operational_mode": "local_grounded_fallback",
        "retrieval_summary": "Tra cứu 20 đoạn liên quan từ khối LSU.",
        "fallback_used": True,
        "initial_backend": "cagent_api",
    }

    should_show = should_show_fallback_notice(badge_cagent_timeout)
    notice_text = format_fallback_notice(badge_cagent_timeout, locale="vi")
    print(f"-> should_show_fallback_notice: {should_show}")
    print(f"-> format_fallback_notice: \"{notice_text}\"")

    dummy_st = DummyStreamlit()
    import streamlit
    orig_warn = getattr(streamlit, "warning", None)
    streamlit.warning = dummy_st.warning
    try:
        render_fallback_notice(badge_cagent_timeout, locale="vi")
    finally:
        if orig_warn:
            streamlit.warning = orig_warn

    assert should_show is True
    assert notice_text == "Dịch vụ C-Agent không phản hồi trong thời gian chờ, đáp án hiện tại là bản tổng hợp cục bộ từ tài liệu."
    assert len(dummy_st.warnings) == 1
    print("=> KẾT QUẢ KỊCH BẢN 1: ĐẠT (Cảnh báo hiển thị chính xác tên C-Agent và thông điệp tiếng Việt).")

    # 2. Negative Scenario 1: User explicitly chose local backend
    print("\n[KỊCH BẢN 2: ÂM TÍNH 1] Người dùng tự chọn Chạy cục bộ ngay từ đầu")
    badge_user_chose_local = {
        "conversation_id": "CONV-LOCAL-TEST",
        "type": "ai_answered",
        "source_count": 5,
        "source_titles": ["Tài liệu nội bộ"],
        "ai_source": "Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình",
        "bridge": "Trích xuất cục bộ",
        "provider": "Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình",
        "operational_mode": "local_grounded_fallback",
        "fallback_used": True,
        "initial_backend": "local",
    }
    should_show_2 = should_show_fallback_notice(badge_user_chose_local)
    print(f"-> should_show_fallback_notice: {should_show_2}")
    assert should_show_2 is False
    print("=> KẾT QUẢ KỊCH BẢN 2: ĐẠT (Không hiển thị cảnh báo khi người dùng chủ động chọn cục bộ).")

    # 3. Negative Scenario 2: C-Agent succeeded normally
    print("\n[KỊCH BẢN 3: ÂM TÍNH 2] C-Agent phản hồi thành công (không có lỗi/timeout)")
    badge_cagent_ok = {
        "conversation_id": "CONV-CAGENT-OK",
        "type": "ai_answered",
        "source_count": 5,
        "source_titles": ["Tài liệu LSU"],
        "ai_source": "C-Agent",
        "provider": "cagent_api",
        "operational_mode": "grounded",
        "fallback_used": False,
        "initial_backend": None,
    }
    should_show_3 = should_show_fallback_notice(badge_cagent_ok)
    print(f"-> should_show_fallback_notice: {should_show_3}")
    assert should_show_3 is False
    print("=> KẾT QUẢ KỊCH BẢN 3: ĐẠT (Không hiển thị cảnh báo khi C-Agent chạy bình thường).")

    print("\n" + "=" * 80)
    print("TẤT CẢ CÁC BÀI KIỂM TRA ĐÃ HOÀN TẤT THÀNH CÔNG VỚI ĐỘ CHÍNH XÁC 100%.")
    print("=" * 80)


if __name__ == "__main__":
    run_verification()
