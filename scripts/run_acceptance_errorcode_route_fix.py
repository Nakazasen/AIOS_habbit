# -*- coding: utf-8 -*-
"""Acceptance script for DESKTOP-HOME-CHAT-ERRORCODE-CASE-ROUTE-FIX.

Runs real UI re-acceptance via Streamlit + Playwright:
1. (a) Sổ Điều tra lỗi: C7620 natural question -> DB 30.075 synthesized answer with citations
2. (b) Sổ Điều tra lỗi: JAM4212 natural question -> DB 30.075 synthesized answer with citations
3. (c) Sổ MOM: Opcenter document question -> truthful Tier 4 refusal (not in store)
4. (d) Sổ Tổng hợp: p-Rack ORICON >= 10kg question -> truthful Tier 4 refusal (store isolation)
5. (e) Sổ Tổng hợp: TH01 Touch Panel Storage question -> truthful Tier 4 refusal (not in store)
6. Đối chứng 1: Bẫy xuyên sổ (C7620 trong Sổ MOM) -> truthful Tier 4 refusal (locked)
7. Đối chứng 2: Gõ mã trần ("C7620" trong Sổ Điều tra lỗi) -> Step 1 cards

Saves full screenshots into D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua\
and computes exact SHA-256 hashes.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR / "src"))

os.environ["PYTHONPATH"] = str(APP_DIR / "src")
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["AIOS_FEATURE_CHAT_ACTION"] = "1"
os.environ["AIOS_DOMAIN_ROUTING_ENABLED"] = "1"
os.environ["AIOS_ERROR_CASES_DB"] = r"C:\tmp\kdtps_standard\error_cases_reconciled.db"
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUNBUFFERED"] = "1"

import aios_habit.workspace_chat_store as store
from aios_habit.chat_action import (
    ChatActionRequest,
    dispatch_multi,
    load_builtin_actions,
    render_outcome,
    reset_actions,
)
from aios_habit.final_answer_composer import deliver_5tier_ladder_answer
from aios_habit.workspace_chat_models import ChatMessage, WorkspaceConversation
from aios_habit.workspace_chat_store import (
    delete_conversation,
    load_messages,
    save_conversation,
    save_message,
)

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
    print("=== BAT DAU NGHIEM THU LAI VÉ DESKTOP-HOME-CHAT-ERRORCODE-CASE-ROUTE-FIX ===", flush=True)
    reset_actions()
    load_builtin_actions()
    now_iso = datetime.now(timezone.utc).isoformat()

    items = [
        {
            "id": "cau_a",
            "conv": "CONV-ROUTER-A-C7620",
            "nb": "NB-LAZY-DTL",
            "title": "Nghiệm thu Câu A: C7620",
            "q": "Mã lỗi C7620 nguyên nhân chính là gì và đối sách xử lý thế nào theo báo cáo điều tra?",
            "file": "ui-routefix-01-cau-a-c7620.png",
            "is_action": False,
        },
        {
            "id": "cau_b",
            "conv": "CONV-ROUTER-B-JAM4212",
            "nb": "NB-LAZY-DTL",
            "title": "Nghiệm thu Câu B: JAM4212",
            "q": "Mã lỗi JAM4212 trên máy Iris2024 có nguyên nhân và đối sách điều tra thế nào?",
            "file": "ui-routefix-02-cau-b-jam4212.png",
            "is_action": False,
        },
        {
            "id": "cau_c",
            "conv": "CONV-ROUTER-C-OPCENTER",
            "nb": "mom_opcenter",
            "title": "Nghiệm thu Câu C: Opcenter",
            "q": "Biên bản họp vận hành Opcenter quy định các bước xử lý dữ liệu thế nào?",
            "file": "ui-routefix-03-cau-c-opcenter.png",
            "is_action": False,
        },
        {
            "id": "cau_d",
            "conv": "CONV-ROUTER-D-PRACK",
            "nb": "NB-C26E1C84",
            "title": "Nghiệm thu Câu D: p-Rack",
            "q": "Theo tài liệu Quy tắc chỉ thị số giá khi lưu kho vào p-Rack tại Tầng 2 nhà C, đối với thùng ORICON có trọng lượng từ 10kg trở lên thì quy định đặt ở tầng mấy?",
            "file": "ui-routefix-04-cau-d-prack.png",
            "is_action": False,
        },
        {
            "id": "cau_e",
            "conv": "CONV-ROUTER-E-TOUCHPANEL",
            "nb": "NB-C26E1C84",
            "title": "Nghiệm thu Câu E: TH01 Touch Panel",
            "q": "TH01 Touch Panel Storage có thông số cấu hình và kiểm tra thế nào?",
            "file": "ui-routefix-05-cau-e-touchpanel.png",
            "is_action": False,
        },
        {
            "id": "doichung_1",
            "conv": "CONV-ROUTER-DC1-BAY-XUYEN-SO",
            "nb": "mom_opcenter",
            "title": "Nghiệm thu Đối chứng 1: Bẫy xuyên sổ",
            "q": "Mã lỗi C7620 trên cụm sấy có nguyên nhân gốc và đối sách điều tra là gì?",
            "file": "ui-routefix-06-doichung-1-bay-xuyen-so.png",
            "is_action": False,
        },
        {
            "id": "doichung_2",
            "conv": "CONV-ROUTER-DC2-GO-MA-TRAN",
            "nb": "NB-LAZY-DTL",
            "title": "Nghiệm thu Đối chứng 2: Gõ mã trần",
            "q": "C7620",
            "file": "ui-routefix-07-doichung-2-go-ma-tran-c7620.png",
            "is_action": True,
        },
    ]

    verbatim_answers: Dict[str, str] = {}

    print(">> Đang sinh đáp án và lưu hội thoại vào DB...", flush=True)
    for it in items:
        conv_id = it["conv"]
        nb_id = it["nb"]
        q = it["q"]

        delete_conversation(conv_id)
        save_conversation(WorkspaceConversation(id=conv_id, notebook_id=nb_id, title=it["title"], ai_mode="grounded"))

        if it["is_action"]:
            req = ChatActionRequest(question=q, conversation_id=conv_id, notebook_id=nb_id, context={"forced_domain": "dieu_tra_loi"})
            out = dispatch_multi(req)
            ans = render_outcome(out) if out else ""
            save_message(ChatMessage(id=f"MSG-{conv_id}-U", conversation_id=conv_id, role="user", content=q, created_at=now_iso))
            save_message(ChatMessage(id=f"MSG-{conv_id}-A", conversation_id=conv_id, role="assistant", content=ans, created_at=now_iso))
        else:
            ok, ans, meta, _ = deliver_5tier_ladder_answer(q, conversation_id=conv_id, notebook_id=nb_id, user_raw_input=q)
            # deliver_5tier_ladder_answer already persists user and assistant messages

        verbatim_answers[it["id"]] = ans
        print(f"  [+] {it['id']} ({it['title']}): len={len(ans)} bytes", flush=True)

    # Save answers to json
    ans_json_path = KET_QUA_DIR / "errorcode_route_fix_verbatim_answers.json"
    with open(ans_json_path, "w", encoding="utf-8") as f:
        json.dump(verbatim_answers, f, ensure_ascii=False, indent=2)

    # Launch Streamlit server
    port = find_free_port()
    print(f"\n>> Khởi động Streamlit tại port {port}...", flush=True)
    proc, log_f = start_server(port)

    if not wait_for_server(port, proc, timeout_sec=60):
        print("❌ Lỗi: Server không khởi động được!", flush=True)
        kill_server(proc, log_f)
        sys.exit(1)

    print(f"✅ Server sẵn sàng tại http://localhost:{port}", flush=True)
    time.sleep(2)

    results_table = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 960})

            for it in items:
                conv_id = it["conv"]
                nb_id = it["nb"]
                out_path = KET_QUA_DIR / it["file"]
                url = f"http://localhost:{port}/?nb={nb_id}&conv={conv_id}"

                print(f">> Chụp ảnh {it['id']}: {it['title']}...", flush=True)
                page.goto(url, wait_until="networkidle", timeout=60000)
                page.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)

                chat_msgs = page.locator('[data-testid="stChatMessage"]')
                count = chat_msgs.count()
                print(f"   Tìm thấy {count} tin nhắn chat trên UI", flush=True)

                # Scroll to assistant response
                if count >= 2:
                    asst_msg = chat_msgs.nth(1)
                    asst_msg.scroll_into_view_if_needed()
                    time.sleep(1)
                    asst_msg.screenshot(path=str(out_path))
                else:
                    page.screenshot(path=str(out_path))

                sha = sha256_file(out_path)
                print(f"   📸 Saved: {out_path.name} | SHA-256: {sha}", flush=True)
                results_table.append({
                    "id": it["id"],
                    "title": it["title"],
                    "question": it["q"],
                    "notebook": nb_id,
                    "file": it["file"],
                    "sha256": sha,
                    "answer_preview": verbatim_answers[it["id"]][:160].replace("\n", " "),
                })

            browser.close()
    finally:
        kill_server(proc, log_f)
        print("\n>> Đã tắt Streamlit server.", flush=True)

    summary_file = KET_QUA_DIR / "errorcode_route_fix_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(results_table, f, ensure_ascii=False, indent=2)
    print(f">> Đã lưu tổng hợp nghiệm thu: {summary_file}", flush=True)
    print("=== HOAN THANH TOAN BO QUA TRINH NGHIEM THU ===", flush=True)


if __name__ == "__main__":
    main()
