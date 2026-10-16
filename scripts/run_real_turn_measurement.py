"""Real turn measurement script for DESKTOP-PC0575-CAGENT-PAYLOAD-TRIM-FIX.
Executes a real query on CONV-9C730D76 with the full conversation history
through route_workspace_chat_submission with cagent_api backend.
Records timing, answer generation lane, payload size, and trace ID.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from aios_habit import antigravity_bridge as bridge
from aios_habit.cagent_api import (
    DEFAULT_CAGENT_MAX_HISTORY_CHARS,
    DEFAULT_CAGENT_MAX_HISTORY_TURNS,
    trim_chat_history_for_cagent,
)
from aios_habit.workspace_chat_ai_answer import _cap_and_pack_sources, build_workspace_ai_prompt
from aios_habit.workspace_chat_rag_v2_adapter import retrieve_workspace_chat_evidence
from aios_habit.workspace_chat_store import load_messages, load_conversation_source_selections


def run_real_turn_measurement():
    print("=" * 80)
    print("CHẠY ĐO ĐẠC MỘT LƯỢT HỎI THẬT TRÊN HỘI THOẠI DÀI CONV-9C730D76 TẠI PC0575")
    print("=" * 80)

    conv_id = "CONV-9C730D76"
    nb_id = "NB-E35A7BEE"
    question = "LSU là gì và gồm những bộ phận quang học chính nào?"

    # 1. Load conversation history
    msgs_path = os.path.join("local_cases", "workspace_chat", "messages.jsonl")
    msgs = []
    with open(msgs_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            if item.get("conversation_id") == conv_id:
                msgs.append(item)

    # Lấy toàn bộ 50 tin nhắn gần nhất trước lượt mới
    chat_history = tuple({"role": m["role"], "content": m["content"]} for m in msgs[-50:])
    raw_history_chars = sum(len(m["content"]) for m in chat_history)
    print(f"Hội thoại: {conv_id} (tổng {len(msgs)} tin nhắn hiện có)")
    print(f"Lịch sử đưa vào (50 tin nhắn gần nhất): {len(chat_history)} tin, {raw_history_chars} ký tự")

    # 2. Kiểm tra trước bước cắt tỉa
    trimmed_history = trim_chat_history_for_cagent(chat_history)
    trimmed_chars = sum(len(m["content"]) for m in trimmed_history)
    print(f"Lịch sử sau cắt tỉa: {len(trimmed_history)} tin nhắn, {trimmed_chars} ký tự")
    print(f"Ngân sách áp dụng: max_turns={DEFAULT_CAGENT_MAX_HISTORY_TURNS}, max_chars={DEFAULT_CAGENT_MAX_HISTORY_CHARS}")

    # 3. Thực hiện truy hồi bằng chứng
    t_ret_start = time.time()
    ret = retrieve_workspace_chat_evidence(question, (), search_preference="auto", forced_domain="lsu")
    t_ret_end = time.time()
    ret_duration = t_ret_end - t_ret_start
    retrieved_sources = ret.get("retrieved_context_sources", ())
    evidence_items = ret.get("evidence_items", [])
    local_synthesis = ret.get("local_synthesis")
    print(f"Truy hồi bằng chứng: {len(retrieved_sources)} đoạn, thời gian: {ret_duration:.2f}s")

    # 4. Tính toán payload thực tế gửi sang C-Agent
    q_capped, capped_sources, _ = _cap_and_pack_sources(question, retrieved_sources)
    prompt_sources = [s for s in capped_sources if getattr(s, "included_chars", len(getattr(s, "text", ""))) > 0]
    sys_prompt, usr_prompt = build_workspace_ai_prompt(question, prompt_sources, trimmed_history, answer_language="vi")
    cagent_full_prompt = f"{sys_prompt}\n\n{usr_prompt}".strip()
    cagent_payload_json = json.dumps({"question": cagent_full_prompt}, ensure_ascii=False)
    print(f"Kích thước payload C-Agent gửi đi: {len(cagent_full_prompt)} ký tự ({len(cagent_payload_json.encode('utf-8'))} bytes UTF-8)")

    # 5. Thực hiện gửi qua route_workspace_chat_submission
    print("\nBắt đầu gọi route_workspace_chat_submission (backend='cagent_api')...")
    t_start = time.time()
    iso_start = datetime.now(timezone.utc).isoformat()

    ok, message, badge, error = bridge.route_workspace_chat_submission(
        question=question,
        evidence_items=evidence_items,
        packed_sources=prompt_sources,
        conversation_id=conv_id,
        notebook_id=nb_id,
        retrieval_applied=True,
        retrieved_sources=retrieved_sources,
        retrieval_summary="Tra cứu 20 đoạn liên quan từ khối LSU.",
        current_keys=(),
        chat_history=chat_history,
        user_raw_input=question,
        backend="cagent_api",
        local_synthesis=local_synthesis,
    )

    t_end = time.time()
    iso_end = datetime.now(timezone.utc).isoformat()
    total_duration = t_end - t_start

    print("\n--- KẾT QUẢ ĐO ĐẠC LƯỢT HỎI THẬT ---")
    print(f"Thời điểm bắt đầu: {iso_start}")
    print(f"Thời điểm kết thúc: {iso_end}")
    print(f"Tổng thời gian xử lý: {total_duration:.2f}s (trong đó truy hồi trước đó: {ret_duration:.2f}s)")
    print(f"Trạng thái (ok): {ok}")
    print(f"Thông điệp (message): {message}")
    print(f"Lỗi (error): {error}")

    operational_mode = badge.get("operational_mode") if badge else "unknown"
    provider_name = badge.get("provider") or badge.get("ai_source") if badge else "unknown"
    trace_id = badge.get("trace_id") if badge else "none"
    fallback_used = badge.get("fallback_used", False) if badge else False

    print(f"Làn sinh đáp án thực tế: {provider_name} (operational_mode: {operational_mode})")
    print(f"Chế độ dự phòng (fallback_used): {fallback_used}")
    print(f"Mã Trace ID: {trace_id}")

    result_data = {
        "conversation_id": conv_id,
        "question": question,
        "start_time": iso_start,
        "end_time": iso_end,
        "duration_seconds": round(total_duration, 2),
        "retrieval_duration_seconds": round(ret_duration, 2),
        "history_messages_raw": len(chat_history),
        "history_chars_raw": raw_history_chars,
        "history_messages_trimmed": len(trimmed_history),
        "history_chars_trimmed": trimmed_chars,
        "payload_chars": len(cagent_full_prompt),
        "payload_utf8_bytes": len(cagent_payload_json.encode("utf-8")),
        "ok": ok,
        "operational_mode": operational_mode,
        "provider_name": provider_name,
        "fallback_used": fallback_used,
        "trace_id": trace_id,
    }

    out_file = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua\ket-qua-do-desktop-pc0575-cagent-payload-trim.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    print(f"\nĐã lưu kết quả đo đạc vào: {out_file}")

    return result_data


if __name__ == "__main__":
    run_real_turn_measurement()
