"""Safe Runtime Smoke Test for Antigravity Direct Context Compression & Inheritance.

Safeguards:
1. STRICT ISOLATION & RESTORATION: Runs in a dedicated tempfile.TemporaryDirectory.
   Restores all global storage pointers to their original values in `finally` so the module remains 100% safe for programmatic invocation.
2. GUARANTEED CLEANUP: All temporary store files are purged in try...finally.
3. EXPLICIT LIVE FLAG: Requires '--live' argument to execute live Gemini Web inference; otherwise performs dry-run verification.
"""
import sys
import uuid
import tempfile
import argparse
from pathlib import Path
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import aios_habit.workspace_chat_store as store
from aios_habit.antigravity_bridge import (
    AntigravityHealthStatus,
    AntigravityBridgeResponse,
    FSM_DIRECT_READY,
    get_antigravity_bridge_health,
    compress_conversation_context_direct,
    route_workspace_chat_submission,
)
from aios_habit.workspace_chat_models import (
    DocumentNotebook,
    WorkspaceConversation,
    ChatMessage,
    NotebookSource,
    SOURCE_SCOPE_NOTEBOOK,
)
from aios_habit.workspace_chat_store import (
    init_chat_store,
    save_notebook,
    save_conversation,
    load_conversation,
    save_message,
    load_messages,
    save_notebook_source,
    set_source_enabled,
    load_conversation_source_selections,
)


def run_smoke_test(is_live: bool = False) -> int:
    print("=================================================================")
    mode_label = "LIVE (GEMINI WEB DIRECT)" if is_live else "DRY-RUN / VERIFICATION ONLY"
    print(f"🚀 BẮT ĐẦU SMOKE TEST ANTIGRAVITY DIRECT [{mode_label}]")
    print("=================================================================")

    # Backup original global store paths
    orig_local_chat_dir = store.LOCAL_CHAT_DIR
    orig_notebooks_file = store.NOTEBOOKS_FILE
    orig_conversations_file = store.CONVERSATIONS_FILE
    orig_messages_file = store.MESSAGES_FILE
    orig_temporary_sources_file = store.TEMPORARY_SOURCES_FILE
    orig_notebook_sources_file = store.NOTEBOOK_SOURCES_FILE
    orig_source_selections_file = store.SOURCE_SELECTIONS_FILE

    # 1. Health Check
    health = get_antigravity_bridge_health(timeout_seconds=3.0)
    print(f"[Step 1] Health Status: status='{health.status}', mode='{health.mode}', direct_ready={health.is_direct_ready}")
    if is_live and not health.is_direct_ready:
        print(f"❌ LỖI: Sidecar Bridge không ở trạng thái direct_ready. Reason: {health.reason}")
        return 1

    try:
        # 2. Setup Isolated Temporary Storage
        with tempfile.TemporaryDirectory(prefix="aios_wsc_smoke_") as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            print(f"[Step 2] Khởi tạo sandbox lưu trữ cách ly tại: {temp_dir}")

            # Redirect store pointers strictly to the sandbox directory
            store.LOCAL_CHAT_DIR = temp_dir
            store.NOTEBOOKS_FILE = temp_dir / "notebooks.jsonl"
            store.CONVERSATIONS_FILE = temp_dir / "conversations.jsonl"
            store.MESSAGES_FILE = temp_dir / "messages.jsonl"
            store.TEMPORARY_SOURCES_FILE = temp_dir / "temporary_sources.jsonl"
            store.NOTEBOOK_SOURCES_FILE = temp_dir / "notebook_sources.jsonl"
            store.SOURCE_SELECTIONS_FILE = temp_dir / "conversation_source_selections.jsonl"
            init_chat_store()

            try:
                nb_id = f"NB-SANDBOX-{uuid.uuid4().hex[:6].upper()}"
                conv_id = f"CONV-SANDBOX-{uuid.uuid4().hex[:6].upper()}"

                nb = DocumentNotebook(id=nb_id, title="Sổ Sandbox Thử Nghiệm")
                save_notebook(nb)

                conv = WorkspaceConversation(
                    id=conv_id,
                    notebook_id=nb_id,
                    title="Thảo luận kiến trúc BGE-M3 & RRF",
                    search_preference="deep",
                )
                save_conversation(conv)

                m1 = ChatMessage(
                    id=f"MSG-1-{uuid.uuid4().hex[:6]}",
                    conversation_id=conv_id,
                    role="user",
                    content="Hệ thống AIOS đang chuẩn hóa mô hình BGE-M3 revision 5617a9f cho RAG v2 hybrid retrieval.",
                )
                m2 = ChatMessage(
                    id=f"MSG-2-{uuid.uuid4().hex[:6]}",
                    conversation_id=conv_id,
                    role="assistant",
                    content="Mô hình BGE-M3 đã tải xong tại local_runs/retrieval_models/bge-m3-5617a9f và hỗ trợ multi-vector dense + sparse + lexical.",
                )
                m3 = ChatMessage(
                    id=f"MSG-3-{uuid.uuid4().hex[:6]}",
                    conversation_id=conv_id,
                    role="user",
                    content="Chúng ta đã thống nhất tắt reranker cục bộ trên CPU bằng biến AIOS_WORKSPACE_RAG_V2_ADAPTIVE_ENABLED=0 để tránh tràn bộ nhớ ảo Windows.",
                )
                save_message(m1)
                save_message(m2)
                save_message(m3)

                ns = NotebookSource(
                    id=f"NBS-{uuid.uuid4().hex[:6]}",
                    notebook_id=nb_id,
                    title="Tài liệu Kiến trúc AIOS",
                    source_type="plain_text",
                    content_preview="Tài liệu mô tả RAG v2 và BGE-M3",
                    content_text="Chi tiết kiến trúc RAG v2 với BGE-M3",
                )
                save_notebook_source(ns)
                set_source_enabled(conv_id, SOURCE_SCOPE_NOTEBOOK, ns.id, True)

                print(f"[Step 3] Đã tạo hội thoại ban đầu {conv_id} trong sandbox với 3 tin nhắn kỹ thuật.")

                history = (
                    {"role": m1.role, "content": m1.content},
                    {"role": m2.role, "content": m2.content},
                    {"role": m3.role, "content": m3.content},
                )

                if is_live:
                    print("[Step 4] Đang gửi yêu cầu nén ngữ cảnh sang Live Sidecar Daemon...")
                    ok, summary, err = compress_conversation_context_direct(
                        history,
                        health_status=health,
                        timeout_seconds=45,
                    )
                    if not ok or not summary.strip():
                        print(f"❌ LỖI NÉN NGỮ CẢNH: {err}")
                        return 1
                else:
                    print("[Step 4] [DRY-RUN] Bỏ qua gọi Live Gemini API. Sử dụng tóm tắt giả lập an toàn.")
                    summary = (
                        "**Thực thể & Tham số:** BGE-M3 revision 5617a9f, AIOS_WORKSPACE_RAG_V2_ADAPTIVE_ENABLED=0.\n"
                        "**Quyết định:** Tắt reranker cục bộ trên CPU để chống tràn bộ nhớ ảo Windows."
                    )
                    ok, err = True, None

                print("\n" + "-"*50)
                print("✅ TÓM TẮT NGỮ CẢNH ĐÃ TẠO:")
                print(summary)
                print("-"*50 + "\n")

                # 4. Create New Conversation with Compressed Memory
                new_conv_id = f"CONV-SANDBOX-NEW-{uuid.uuid4().hex[:6].upper()}"
                new_conv = WorkspaceConversation(
                    id=new_conv_id,
                    notebook_id=nb_id,
                    title=f"Tiếp tục: {conv.title}",
                    compressed_memory=summary.strip(),
                    search_preference=conv.search_preference,
                )
                save_conversation(new_conv)

                # Inherit notebook sources
                active_selections = load_conversation_source_selections(conv_id)
                for sel in active_selections:
                    if sel.source_scope == SOURCE_SCOPE_NOTEBOOK:
                        set_source_enabled(new_conv.id, SOURCE_SCOPE_NOTEBOOK, sel.source_id, sel.enabled)

                print(f"[Step 5] Đã tạo chat mới {new_conv.id} mang compressed_memory và kế thừa nguồn sổ trong sandbox.")

                # 5. Ask Follow-up Question in New Conversation
                evidence_items = [
                    {"title": "system_env.txt", "text": "Môi trường: CPU Intel i7, Windows 11, paging size: auto."}
                ]
                chat_history = (
                    {"role": "system", "content": new_conv.compressed_memory},
                )
                follow_up_q = "Nhắc lại quyết định cấu hình reranker và mô hình chúng ta đã chốt?"

                if is_live:
                    print(f"[Step 6] Đang gửi câu hỏi tiếp theo sang Live Direct Daemon...")
                    ok, success_msg, badge, err = route_workspace_chat_submission(
                        question=follow_up_q,
                        evidence_items=evidence_items,
                        packed_sources=(),
                        conversation_id=new_conv.id,
                        notebook_id=nb_id,
                        retrieval_applied=True,
                        retrieved_sources=(),
                        retrieval_summary="Đã đính kèm 1 bằng chứng môi trường",
                        current_keys=(),
                        chat_history=chat_history,
                        user_raw_input=follow_up_q,
                        health_status=health,
                    )
                    if not ok or err:
                        print(f"❌ LỖI ROUTE SUBMISSION: {err}")
                        return 1

                    saved_msgs = load_messages(new_conv.id)
                    print("\n" + "-"*50)
                    print("✅ CÂU TRẢ LỜI CỦA AI DIRECT (SỬ DỤNG NGỮ CẢNH KẾ THỪA):")
                    print(saved_msgs[-1].content)
                    print("-"*50)
                else:
                    print("[Step 6] [DRY-RUN] Bỏ qua gọi Live QA API. Kiểm tra định dạng ngữ cảnh kế thừa:")
                    print(f"  - Chat History system role: {chat_history[0]['content']}")
                    print(f"  - Question: {follow_up_q}")

                print("\n=================================================================")
                print("🎉 SMOKE TEST ĐÃ HOÀN TẤT THÀNH CÔNG VÀ AN TOÀN!")
                print("=================================================================")
                return 0

            finally:
                print(f"[Cleanup] Đang tự động dọn dẹp và hủy sandbox tại: {temp_dir}")
    finally:
        # Restore original global store paths
        store.LOCAL_CHAT_DIR = orig_local_chat_dir
        store.NOTEBOOKS_FILE = orig_notebooks_file
        store.CONVERSATIONS_FILE = orig_conversations_file
        store.MESSAGES_FILE = orig_messages_file
        store.TEMPORARY_SOURCES_FILE = orig_temporary_sources_file
        store.NOTEBOOK_SOURCES_FILE = orig_notebook_sources_file
        store.SOURCE_SELECTIONS_FILE = orig_source_selections_file
        print(f"[Cleanup] Đã khôi phục toàn bộ đường dẫn lưu trữ gốc: {store.LOCAL_CHAT_DIR}")


def main() -> int:
    parser = argparse.ArgumentParser(description="AIOS Antigravity Direct Smoke Test")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Gửi yêu cầu thực tế tới Antigravity Direct Daemon (Gemini Web)",
    )
    args = parser.parse_args()
    return run_smoke_test(is_live=args.live)


if __name__ == "__main__":
    sys.exit(main())
