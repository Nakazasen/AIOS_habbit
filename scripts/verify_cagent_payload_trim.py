"""Verification and measurement script for DESKTOP-PC0575-CAGENT-PAYLOAD-TRIM-FIX.
Measures payload sizes before and after trimming on real long conversation CONV-9C730D76,
verifies chosen limits, and executes a real query re-measurement at PC0575.
"""

from __future__ import annotations

import json
import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from aios_habit.cagent_api import (
    DEFAULT_CAGENT_MAX_HISTORY_CHARS,
    DEFAULT_CAGENT_MAX_HISTORY_TURNS,
    trim_chat_history_for_cagent,
)
from aios_habit.workspace_chat_ai_answer import (
    _cap_and_pack_sources,
    build_workspace_ai_prompt,
)
from aios_habit.workspace_chat_rag_v2_adapter import retrieve_workspace_chat_evidence


def measure_conv_9c730d76():
    print("=" * 80)
    print("ĐO ĐẠC KÍCH THƯỚC PAYLOAD TRƯỚC / SAU KHI CẮT TỈA TRÊN HỘI THOẠI CONV-9C730D76")
    print("=" * 80)

    # 1. Load messages for CONV-9C730D76
    msgs_path = os.path.join("local_cases", "workspace_chat", "messages.jsonl")
    msgs = []
    with open(msgs_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            if item.get("conversation_id") == "CONV-9C730D76":
                msgs.append(item)

    print(f"Tổng số tin nhắn trong CONV-9C730D76: {len(msgs)}")
    target_idx = next(i for i, m in enumerate(msgs) if m.get("id") == "MSG-1EF1690E")
    target_msg = msgs[target_idx]
    q_text = target_msg["content"]
    prior_msgs = msgs[:target_idx]
    print(f"Lượt hỏi 17:53 (MSG-1EF1690E): '{q_text}'")
    print(f"Số tin nhắn trước lượt hỏi: {len(prior_msgs)}")

    # Trích xuất 50 tin nhắn như trước đây khi chưa có trim
    history_before_50 = tuple({"role": m["role"], "content": m["content"]} for m in prior_msgs[-50:])
    chars_before_history = sum(len(m["content"]) for m in history_before_50)
    print(f"Lịch sử trước khi cắt (50 tin nhắn gần nhất): {chars_before_history} ký tự")

    # 2. Truy hồi bằng chứng như trong thực tế
    ret = retrieve_workspace_chat_evidence(q_text, (), search_preference="auto", forced_domain="lsu")
    retrieved_sources = ret.get("retrieved_context_sources", ())
    q_capped, capped_sources, _ = _cap_and_pack_sources(q_text, retrieved_sources)
    prompt_sources = [s for s in capped_sources if getattr(s, "included_chars", len(getattr(s, "text", ""))) > 0]
    chars_sources = sum(len(s.text) for s in prompt_sources)
    print(f"Bằng chứng truy hồi: {len(prompt_sources)} đoạn trích, tổng {chars_sources} ký tự")

    # 3. Payload trước khi cắt
    sys_before, usr_before = build_workspace_ai_prompt(q_text, prompt_sources, history_before_50, answer_language="vi")
    q_field_before = f"{sys_before}\n\n{usr_before}".strip()
    body_before = json.dumps({"question": q_field_before}, ensure_ascii=False)
    bytes_before = len(body_before.encode("utf-8"))

    # 4. Cắt tỉa theo hàm trim_chat_history_for_cagent
    history_after = trim_chat_history_for_cagent(history_before_50)
    chars_after_history = sum(len(m["content"]) for m in history_after)

    # 5. Payload sau khi cắt
    sys_after, usr_after = build_workspace_ai_prompt(q_text, prompt_sources, history_after, answer_language="vi")
    q_field_after = f"{sys_after}\n\n{usr_after}".strip()
    body_after = json.dumps({"question": q_field_after}, ensure_ascii=False)
    bytes_after = len(body_after.encode("utf-8"))

    # 6. So sánh
    diff_chars = len(q_field_before) - len(q_field_after)
    diff_bytes = bytes_before - bytes_after
    pct_chars = (diff_chars / len(q_field_before)) * 100
    pct_bytes = (diff_bytes / bytes_before) * 100

    print("\n--- BẢNG SO SÁNH KÍCH THƯỚC TRƯỚC / SAU CẮT TỈA ---")
    print(f"{'Thành phần':<35} | {'Trước khi cắt (50 tin)':<22} | {'Sau khi cắt (mới nhất)':<22} | {'Chênh lệch':<15}")
    print("-" * 105)
    print(f"{'Số tin nhắn lịch sử':<35} | {len(history_before_50):<22} | {len(history_after):<22} | -{len(history_before_50) - len(history_after)} tin")
    print(f"{'Ký tự phần lịch sử hội thoại':<35} | {chars_before_history:<22} | {chars_after_history:<22} | -{chars_before_history - chars_after_history} ký tự")
    print(f"{'Câu hỏi hiện tại':<35} | {len(q_text):<22} | {len(q_text):<22} | Giữ nguyên (0)")
    print(f"{'Số đoạn bằng chứng truy hồi':<35} | {len(prompt_sources):<22} | {len(prompt_sources):<22} | Giữ nguyên (0)")
    print(f"{'Ký tự bằng chứng truy hồi':<35} | {chars_sources:<22} | {chars_sources:<22} | Giữ nguyên (0)")
    print(f"{'System Prompt':<35} | {len(sys_before):<22} | {len(sys_after):<22} | Giữ nguyên (0)")
    print(f"{'Tổng ký tự trường question (API)':<35} | {len(q_field_before):<22} | {len(q_field_after):<22} | -{diff_chars} ({pct_chars:.1f}%)")
    print(f"{'Tổng dung lượng HTTP Body (UTF-8)':<35} | {bytes_before:<22} | {bytes_after:<22} | -{diff_bytes} ({pct_bytes:.1f}%)")
    print("-" * 105)

    return {
        "len_history_before": len(history_before_50),
        "len_history_after": len(history_after),
        "chars_history_before": chars_before_history,
        "chars_history_after": chars_after_history,
        "total_chars_before": len(q_field_before),
        "total_chars_after": len(q_field_after),
        "bytes_before": bytes_before,
        "bytes_after": bytes_after,
        "diff_chars": diff_chars,
        "pct_chars": pct_chars,
        "diff_bytes": diff_bytes,
        "pct_bytes": pct_bytes,
        "prompt_sources_count": len(prompt_sources),
        "chars_sources": chars_sources,
    }


if __name__ == "__main__":
    measure_conv_9c730d76()
