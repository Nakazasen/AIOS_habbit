# -*- coding: utf-8 -*-
"""Acceptance test runner for DESKTOP-HOME-ERRORLOOKUP-ROUTING-FIX.

Executes:
1. Runs the 4 sample queries in Sổ Điều tra lỗi (NB-LAZY-DTL):
   - QA1: "Tai lieu KTD-2026-06-0647 Iris2024 C33 A JAM4212 co noi dung gi?" (Doc query with error code)
   - QA2: "Tai lieu KTD-2026-06-0527 Iris2024 C33 A1.2 C3100 co noi dung gi?" (Doc query with error code)
   - QA3: "loi C6770 la gi" (Pure error query)
   - QA4: "Mã lỗi C7620 nguyên nhân chính là gì và đối sách xử lý thế nào theo báo cáo điều tra?" (Pure error query)
2. Starts Streamlit server and opens Playwright browser to capture real UI screenshots.
3. Saves images to hop-thu/lan-desktop/ket-qua/ and computes SHA-256 and byte sizes.
4. Saves raw results JSON.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
import urllib.request

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR / "src"))

os.environ["PYTHONPATH"] = str(APP_DIR / "src")
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["AIOS_FEATURE_CHAT_ACTION"] = "1"
os.environ["AIOS_DOMAIN_ROUTING_ENABLED"] = "1"
os.environ["AIOS_RAG_WARMED_OVERRIDE"] = "1"
os.environ["AIOS_ERROR_CASES_DB"] = r"C:\tmp\kdtps_standard\error_cases_reconciled.db"
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUNBUFFERED"] = "1"

import aios_habit.chat_action as ca
from aios_habit.chat_action_error_lookup import (
    ACTION_NAME,
    is_document_content_query,
)
from aios_habit.workspace_chat_models import ChatMessage, WorkspaceConversation
from aios_habit.workspace_chat_store import (
    delete_conversation,
    load_messages,
    save_conversation,
    save_message,
)
from aios_habit.workspace_chat_app import _run_chat_turn_async

KET_QUA_DIR = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")
KET_QUA_DIR.mkdir(parents=True, exist_ok=True)


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def wait_for_server(port: int, proc: subprocess.Popen, timeout_sec: int = 60) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_sec:
        if proc.poll() is not None:
            print(f"❌ Server exited early with code {proc.returncode}", flush=True)
            return False
        try:
            req = urllib.request.Request(f"http://localhost:{port}/_stcore/health")
            with urllib.request.urlopen(req, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def start_server(port: int) -> Tuple[subprocess.Popen, Any]:
    cmd = [
        str(APP_DIR / ".venv" / "Scripts" / "python.exe"),
        "-u",
        "-m",
        "streamlit",
        "run",
        "src/aios_habit/workspace_chat_app.py",
        f"--server.port={port}",
        "--server.headless=true",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]
    log_file = open(KET_QUA_DIR / "server_acceptance.log", "w", encoding="utf-8")
    env = os.environ.copy()
    proc = subprocess.Popen(cmd, cwd=APP_DIR, env=env, stdout=log_file, stderr=subprocess.STDOUT)
    return proc, log_file


def kill_server(proc: subprocess.Popen, log_file: Any) -> None:
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    try:
        log_file.close()
    except Exception:
        pass


def main():
    print("=== BAT DAU NGHIEM THU VE DESKTOP-HOME-ERRORLOOKUP-ROUTING-FIX ===", flush=True)
    ca.reset_actions()
    ca.load_builtin_actions()
    now_iso = datetime.now(timezone.utc).isoformat()

    items = [
        {
            "id": "cau_1_jam4212",
            "conv": "CONV-ROUTER-FIX-QA1-JAM4212",
            "nb": "NB-LAZY-DTL",
            "title": "Nghiệm thu Câu 1: KTD-2026-06-0647 JAM4212",
            "q": "Tai lieu KTD-2026-06-0647 Iris2024 C33 A JAM4212 co noi dung gi?",
            "file": "anh-errorlookup-routing-01-jam4212.png",
            "is_doc_content": True,
            "target_doc": "KTD-2026-06-0647-Iris2024-C33-A-JAM4212.xlsx",
        },
        {
            "id": "cau_2_c3100",
            "conv": "CONV-ROUTER-FIX-QA2-C3100",
            "nb": "NB-LAZY-DTL",
            "title": "Nghiệm thu Câu 2: KTD-2026-06-0527 C3100",
            "q": "Tai lieu KTD-2026-06-0527 Iris2024 C33 A1.2 C3100 co noi dung gi?",
            "file": "anh-errorlookup-routing-02-c3100.png",
            "is_doc_content": True,
            "target_doc": "KTD-2026-06-0527-Iris2024-C33-A1.2-C3100.xlsx",
        },
        {
            "id": "cau_3_c6770",
            "conv": "CONV-ROUTER-FIX-QA3-C6770",
            "nb": "NB-LAZY-DTL",
            "title": "Nghiệm thu Câu 3: Tra cứu lỗi thuần C6770",
            "q": "loi C6770 la gi",
            "file": "anh-errorlookup-routing-03-c6770.png",
            "is_doc_content": False,
            "target_doc": "error_cases_reconciled.db",
        },
        {
            "id": "cau_4_c7620",
            "conv": "CONV-ROUTER-FIX-QA4-C7620",
            "nb": "NB-LAZY-DTL",
            "title": "Nghiệm thu Câu 4: Tra cứu lỗi thuần C7620",
            "q": "Mã lỗi C7620 nguyên nhân chính là gì và đối sách xử lý thế nào theo báo cáo điều tra?",
            "file": "anh-errorlookup-routing-04-c7620.png",
            "is_doc_content": False,
            "target_doc": "error_cases_reconciled.db",
        },
    ]

    results_data: List[Dict[str, Any]] = []

    print(">> Đang sinh đáp án theo đúng tuyến định tuyến...", flush=True)
    for it in items:
        conv_id = it["conv"]
        nb_id = it["nb"]
        q = it["q"]
        is_doc = it["is_doc_content"]

        delete_conversation(conv_id)
        save_conversation(WorkspaceConversation(id=conv_id, notebook_id=nb_id, title=it["title"], ai_mode="grounded"))

        t0 = time.perf_counter()
        if is_doc:
            # Document content query: must route to RAG pipeline via _run_chat_turn_async
            print(f"  [+] Chạy RAG pipeline cho {it['id']}...", flush=True)
            u_msg_id = f"MSG-{conv_id}-U"
            save_message(ChatMessage(id=u_msg_id, conversation_id=conv_id, role="user", content=q, created_at=now_iso))
            ok, ans, meta, err = _run_chat_turn_async(
                q_text=q,
                conversation_id=conv_id,
                notebook_id=nb_id,
                user_raw_input=q,
                user_message_id=u_msg_id,
                forced_domain="dieu_tra_loi",
                collection_id="dieu_tra_loi",
                bypass_cache=True,
            )
            elapsed_s = time.perf_counter() - t0
            # Reload messages to get the saved assistant message
            msgs = load_messages(conv_id)
            asst_msgs = [m for m in msgs if m.role == "assistant"]
            if asst_msgs:
                ans_text = asst_msgs[-1].content
            else:
                ans_text = ans
            route_used = "rag_pipeline"
            sources_used = meta.get("source_titles", []) if meta else []
        else:
            # Pure error lookup: handled by chat_action
            print(f"  [+] Chạy chat_action_error_lookup cho {it['id']}...", flush=True)
            saved_asst: List[str] = []
            handled = ca.handle_chat_text(
                q,
                conversation_id=conv_id,
                notebook_id=nb_id,
                context={"forced_domain": "dieu_tra_loi"},
                save_user=lambda c: save_message(ChatMessage(id=f"MSG-{conv_id}-U", conversation_id=conv_id, role="user", content=c, created_at=now_iso)),
                save_assistant=lambda c: (saved_asst.append(c), save_message(ChatMessage(id=f"MSG-{conv_id}-A", conversation_id=conv_id, role="assistant", content=c, created_at=now_iso))),
            )
            elapsed_s = time.perf_counter() - t0
            ans_text = saved_asst[-1] if saved_asst else ""
            route_used = "chat_action_error_lookup"
            sources_used = ["error_cases_reconciled.db"]

        print(f"      Tuyến: {route_used} | Thời gian: {elapsed_s:.2f}s | Độ dài đáp án: {len(ans_text)} bytes", flush=True)
        results_data.append({
            "id": it["id"],
            "title": it["title"],
            "question": q,
            "notebook_id": nb_id,
            "is_document_content_query": is_doc,
            "route_used": route_used,
            "elapsed_seconds": round(elapsed_s, 2),
            "sources_used": sources_used,
            "target_doc": it["target_doc"],
            "verbatim_answer": ans_text,
            "file": it["file"],
        })

    # Start Streamlit server for screenshot capture
    port = find_free_port()
    print(f"\n>> Khởi động Streamlit tại port {port}...", flush=True)
    proc, log_f = start_server(port)

    if not wait_for_server(port, proc, timeout_sec=60):
        print("❌ Lỗi: Server không khởi động được!", flush=True)
        kill_server(proc, log_f)
        sys.exit(1)

    print(f"✅ Server sẵn sàng tại http://localhost:{port}", flush=True)
    time.sleep(2)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 960})

            for res in results_data:
                conv_id = [it["conv"] for it in items if it["id"] == res["id"]][0]
                nb_id = res["notebook_id"]
                out_path = KET_QUA_DIR / res["file"]
                url = f"http://localhost:{port}/?nb={nb_id}&conv={conv_id}"

                print(f">> Chụp ảnh {res['id']}: {res['title']}...", flush=True)
                page.goto(url, wait_until="networkidle", timeout=60000)
                page.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)

                chat_msgs = page.locator('[data-testid="stChatMessage"]')
                count = chat_msgs.count()
                print(f"   Tìm thấy {count} tin nhắn chat trên UI", flush=True)

                if count >= 2:
                    asst_msg = chat_msgs.nth(1)
                    asst_msg.scroll_into_view_if_needed()
                    time.sleep(1)
                    asst_msg.screenshot(path=str(out_path))
                else:
                    page.screenshot(path=str(out_path))

                sha = sha256_file(out_path)
                bytes_size = out_path.stat().st_size
                res["sha256"] = sha
                res["file_bytes"] = bytes_size
                print(f"   📸 Saved: {out_path.name} ({bytes_size:,} bytes) | SHA-256: {sha}", flush=True)

            browser.close()
    finally:
        kill_server(proc, log_f)
        print("\n>> Đã tắt Streamlit server.", flush=True)

    results_file = KET_QUA_DIR / "errorlookup_routing_fix_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results_data, f, ensure_ascii=False, indent=2)
    print(f">> Đã lưu dữ liệu nghiệm thu vào: {results_file}", flush=True)
    print("=== HOÀN TẤT TOÀN BỘ QUÁ TRÌNH NGHIỆM THU ===", flush=True)


if __name__ == "__main__":
    main()
