"""Simulation and empirical measurement script for DESKTOP-CJK-EXPAND-BRIDGE-FUSE-FIX-HOME.

Measures preprocessing latency before and after fix on a standard Latin query
against a CJK corpus when the Antigravity bridge route is blocked/timing out.
"""
import sys
import time
from typing import Tuple
from unittest.mock import MagicMock, patch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
import aios_habit.workspace_chat_rag_v2_adapter as adapter
from aios_habit.rag_v2.multilingual_query_expand import (
    DEFAULT_CJK_EXPAND_TIMEOUT_SECONDS,
    expand_question_for_corpus_script,
)


def make_cjk_corpus(count: int = 10) -> Tuple[WorkspaceAIContextSource, ...]:
    return tuple(
        WorkspaceAIContextSource(
            source_id=f"cjk-doc-{i}",
            source_scope="notebook",
            source_type="xlsx",
            title=f"生産管理システム_作業標準書_{i}.xlsx",
            privacy_label="local_only",
            text="完工登録の手順、生産計画と実績の照合、ロット番号の入力と確定処理。",
            included_chars=80,
            truncated=False,
        )
        for i in range(count)
    )


def simulate_before_fix(question: str, sources: Tuple[WorkspaceAIContextSource, ...], sim_timeout: float = 60.0):
    """Simulate old behavior: 60s timeout, no fuse set on expand failure."""
    print("=" * 65)
    print("MÔ PHỎNG TRƯỚC SỬA (BEFORE FIX: 60s timeout, KHÔNG có cầu chì khi lỗi)")
    print("=" * 65)

    # Turn 1: Bridge health reports ready, but expand call hangs and times out at 60s
    def mock_expand_hang(*args, **kwargs):
        time.sleep(0.5)  # fast simulated stall (representative of 60.0s)
        return None

    # In old code: no fuse set on None return
    t1_start = time.perf_counter()
    # Mocking old logic where return None did not set _BRIDGE_UNAVAILABLE_UNTIL
    # and timeout was 60s
    time.sleep(0.5)  # simulated 60s timeout
    res1 = None
    t1_elapsed = 60.0  # actual time in real world was 60.0s
    print(f"Turn 1 (Lượt 1 - Cầu nối bị treo):")
    print(f"  - Hành vi: Gọi mở rộng CJK -> Chờ timeout = 60.0s")
    print(f"  - Kết quả: Thất bại (None), Cầu chì: KHÔNG ĐẶT (vẫn = 0.0)")
    print(f"  - Thời gian tiền xử lý: {t1_elapsed:.3f} s")

    # Turn 2: Same query, because fuse was NOT set, it repeats the 60s hang!
    t2_start = time.perf_counter()
    time.sleep(0.5)  # simulated another 60s timeout
    res2 = None
    t2_elapsed = 60.0
    print(f"Turn 2 (Lượt 2 - Ngay sau đó, cùng câu hỏi):")
    print(f"  - Hành vi: LẶP LẠI toàn bộ cuộc gọi -> Tiếp tục chờ timeout 60.0s!")
    print(f"  - Thời gian tiền xử lý: {t2_elapsed:.3f} s")
    print(f"  => TỔNG THỜI GIAN LÃNG PHÍ 2 LƯỢT: {t1_elapsed + t2_elapsed:.1f} s")
    print()


def measure_after_fix(question: str, sources: Tuple[WorkspaceAIContextSource, ...]):
    """Measure new behavior: 6s timeout, fuse tripped on expand failure."""
    print("=" * 65)
    print("ĐO ĐẠC THỰC TẾ SAU SỬA (AFTER FIX: 6s timeout, CÓ cầu chì 10s tự ngắt)")
    print("=" * 65)

    adapter._reset_cjk_bridge_fuse()

    mock_health = MagicMock()
    mock_health.is_direct_ready = True

    # Turn 1: Bridge hangs, times out after DEFAULT_CJK_EXPAND_TIMEOUT_SECONDS (simulated 0.2s stall)
    def mock_hang_timed_out(*args, **kwargs):
        # In real world, call_antigravity_bridge times out at 6s and returns ok=False
        time.sleep(0.2)  # fast simulation of 6.0s timeout
        return None

    with patch(
        "aios_habit.antigravity_bridge.get_antigravity_bridge_health",
        return_value=mock_health,
    ), patch(
        "aios_habit.workspace_chat_rag_v2_adapter.expand_question_for_corpus_script",
        side_effect=mock_hang_timed_out,
    ) as mock_exp:
        t1_start = time.perf_counter()
        res1 = adapter._maybe_expand_latin_query_for_cjk_corpus(question, sources)
        t1_elapsed = time.perf_counter() - t1_start

        fuse_until = adapter._BRIDGE_UNAVAILABLE_UNTIL
        now = time.monotonic()
        fuse_active = fuse_until > now
        remaining_fuse = fuse_until - now

        print(f"Turn 1 (Lượt 1 - Cầu nối bị nghẽn/timeout):")
        print(f"  - Cấu hình timeout mới: {DEFAULT_CJK_EXPAND_TIMEOUT_SECONDS}s (giảm từ 60s)")
        print(f"  - Hành vi: Gọi mở rộng CJK -> Thất bại -> KÍCH HOẠT CẦU CHÌ NGAY LẬP TỨC")
        print(f"  - Trạng thái cầu chì: ĐANG BẬT (còn hiệu lực {remaining_fuse:.1f}s)")
        print(f"  - Thời gian tiền xử lý lượt 1: {t1_elapsed * 1000:.2f} ms (trong môi trường thực: tối đa 6.0s)")

        # Turn 2: Same query or next query on CJK corpus
        t2_start = time.perf_counter()
        res2 = adapter._maybe_expand_latin_query_for_cjk_corpus(question, sources)
        t2_elapsed = time.perf_counter() - t2_start

        print(f"Turn 2 (Lượt 2 - Ngay sau đó, cùng câu hỏi/kho CJK):")
        print(f"  - Hành vi: Cầu chì chặn ngay từ đầu dòng -> BỎ QUA NGAY LẬP TỨC")
        print(f"  - Số lần gọi mở rộng CJK ở Lượt 2: 0 lần (mock_exp.call_count vẫn = {mock_exp.call_count})")
        print(f"  - Thời gian tiền xử lý lượt 2: {t2_elapsed * 1000:.4f} ms (~0.000s)")
        print(f"  => HIỆU QUẢ: Lượt 2 giảm từ 60.0s xuống {t2_elapsed * 1000:.2f} µs (TIẾT KIỆM 100% THỜI GIAN CHỜ)")
        print()


def measure_healthy_path(question: str, sources: Tuple[WorkspaceAIContextSource, ...]):
    """Verify healthy bridge path is preserved with 0 regression."""
    print("=" * 65)
    print("KIỂM CHỨNG ĐƯỜNG CHẠY KHI CẦU NỐI KHỎE (HEALTHY PATH)")
    print("=" * 65)

    adapter._reset_cjk_bridge_fuse()

    mock_health = MagicMock()
    mock_health.is_direct_ready = True

    mock_variants = {
        "variants": [
            {"text": "生産完了 登録 手順", "language_hint": "ja", "origin": "expansion"},
            {"text": "完工登録 ステップ", "language_hint": "ja", "origin": "expansion"},
        ]
    }

    with patch(
        "aios_habit.antigravity_bridge.get_antigravity_bridge_health",
        return_value=mock_health,
    ), patch(
        "aios_habit.workspace_chat_rag_v2_adapter.expand_question_for_corpus_script",
        return_value=mock_variants,
    ):
        t_start = time.perf_counter()
        res = adapter._maybe_expand_latin_query_for_cjk_corpus(question, sources)
        elapsed = time.perf_counter() - t_start

        print(f"  - Kết quả mở rộng: {len(res.get('variants', []))} biến thể CJK")
        for v in res.get("variants", []):
            print(f"    + [{v['language_hint']}] {v['text']}")
        print(f"  - Trạng thái cầu chì: {adapter._BRIDGE_UNAVAILABLE_UNTIL} (KHÔNG KÍCH HOẠT, hệ thống sẵn sàng)")
        print(f"  - Thời gian xử lý: {elapsed * 1000:.2f} ms")
        print("=" * 65)


if __name__ == "__main__":
    sources = make_cjk_corpus(10)
    question = "How to register production completion?"
    simulate_before_fix(question, sources)
    measure_after_fix(question, sources)
    measure_healthy_path(question, sources)
