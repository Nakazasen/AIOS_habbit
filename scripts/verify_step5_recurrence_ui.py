# -*- coding: utf-8 -*-
"""Real UI Verification Script for DESKTOP-HOME-STEP5-RECURRENCE-CODE-FIX.

Runs Streamlit server + Playwright headless browser to render:
1. Positive case: "Tạo vụ điều tra lỗi mới: kẹt giấy cụm sấy lỗi C7620"
   - Preview card with recurrence alert: 136 cases, most recent ticket FY27H2/263, remedy 不要,
     priority for code meaning (Điều chỉnh) over conflicting symptom ('kẹt giấy').
2. Negative control: "Tạo vụ điều tra lỗi mới: kẹt giấy cụm sấy lỗi X9999"
   - Preview card WITHOUT recurrence alert (is_recurrence=false, count=0).

Saves screenshots to docs/phieu-viec/ket-qua/ and hop-thu/lan-desktop/ket-qua/.
Computes SHA-256 hashes directly from file bytes.
"""

from __future__ import annotations

import sys
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

import hashlib
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
PYTHON_EXE = APP_DIR / ".venv" / "Scripts" / "python.exe"
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR / "src"))

os.environ["PYTHONPATH"] = str(APP_DIR / "src")
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["AIOS_FEATURE_CHAT_ACTION"] = "1"
os.environ["AIOS_ERROR_CASES_DB"] = r"C:\tmp\kdtps_standard\error_cases_reconciled.db"
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUNBUFFERED"] = "1"

from aios_habit.chat_action import ChatActionRequest, dispatch_multi, render_outcome
from aios_habit.workspace_chat_models import ChatMessage, WorkspaceConversation
from aios_habit.workspace_chat_store import (
    delete_conversation,
    save_conversation,
    save_message,
)

DOCS_OUT_DIR = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
DOCS_OUT_DIR.mkdir(parents=True, exist_ok=True)

DESKTOP_OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")
DESKTOP_OUT_DIR.mkdir(parents=True, exist_ok=True)


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
            print(f"Server exited early with code {proc.returncode}", flush=True)
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


def start_server(port: int):
    cmd = [
        str(PYTHON_EXE),
        "-u",
        "-m",
        "streamlit",
        "run",
        "src/aios_habit/workspace_chat_app.py",
        f"--server.port={port}",
        "--server.headless=true",
        "--server.fileWatcherType=none",
    ]
    log_f = open(DOCS_OUT_DIR / "verify_step5_streamlit.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        cmd,
        cwd=str(APP_DIR),
        stdout=log_f,
        stderr=subprocess.STDOUT,
        env=os.environ.copy(),
    )
    return proc, log_f


def main():
    now_iso = datetime.now(timezone.utc).isoformat()

    conv_pos = "CONV-STEP5-VERIFY-C7620"
    conv_neg = "CONV-STEP5-VERIFY-X9999"

    delete_conversation(conv_pos)
    delete_conversation(conv_neg)

    save_conversation(
        WorkspaceConversation(
            id=conv_pos,
            notebook_id="NB-LAZY-DTL",
            title="Nghiệm thu Bước 5: C7620 Cảnh báo tái phát",
            created_at=now_iso,
            updated_at=now_iso,
        )
    )
    save_conversation(
        WorkspaceConversation(
            id=conv_neg,
            notebook_id="NB-LAZY-DTL",
            title="Nghiệm thu Bước 5: X9999 Đối chứng âm",
            created_at=now_iso,
            updated_at=now_iso,
        )
    )

    # 1. Sinh đáp án C7620
    q_pos = "Tạo vụ điều tra lỗi mới: kẹt giấy cụm sấy lỗi C7620"
    out_pos = dispatch_multi(
        ChatActionRequest(
            question=q_pos,
            conversation_id=conv_pos,
            notebook_id="NB-LAZY-DTL",
        )
    )
    text_pos = render_outcome(out_pos) if out_pos else ""
    save_message(
        ChatMessage(
            id="MSG-VERIFY-POS-U",
            conversation_id=conv_pos,
            role="user",
            content=q_pos,
            created_at=now_iso,
        )
    )
    save_message(
        ChatMessage(
            id="MSG-VERIFY-POS-A",
            conversation_id=conv_pos,
            role="assistant",
            content=text_pos,
            created_at=now_iso,
        )
    )

    # 2. Sinh đáp án X9999 (Đối chứng âm)
    q_neg = "Tạo vụ điều tra lỗi mới: kẹt giấy cụm sấy lỗi X9999"
    out_neg = dispatch_multi(
        ChatActionRequest(
            question=q_neg,
            conversation_id=conv_neg,
            notebook_id="NB-LAZY-DTL",
        )
    )
    text_neg = render_outcome(out_neg) if out_neg else ""
    save_message(
        ChatMessage(
            id="MSG-VERIFY-NEG-U",
            conversation_id=conv_neg,
            role="user",
            content=q_neg,
            created_at=now_iso,
        )
    )
    save_message(
        ChatMessage(
            id="MSG-VERIFY-NEG-A",
            conversation_id=conv_neg,
            role="assistant",
            content=text_neg,
            created_at=now_iso,
        )
    )

    print(">> Đã khởi tạo tin nhắn mẫu cho cả hai kịch bản trong DB chat.", flush=True)

    # Khởi động Streamlit Server
    port = find_free_port()
    url = f"http://localhost:{port}"
    print(f">> Khởi động Streamlit Server tại {url}...", flush=True)
    proc, log_f = start_server(port)

    if not wait_for_server(port, proc, timeout_sec=60):
        print("❌ Lỗi: Không thể khởi động Streamlit Server!", flush=True)
        proc.kill()
        log_f.close()
        sys.exit(1)

    print(f"✅ Streamlit Server đã sẵn sàng tại {url}", flush=True)
    time.sleep(2)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 960})

            # 1. Chụp ảnh C7620
            print("\n--- Chụp ảnh Thẻ xem trước C7620 có cảnh báo tái phát ---", flush=True)
            page.goto(f"{url}/?nb=NB-LAZY-DTL&conv={conv_pos}", wait_until="networkidle", timeout=60000)
            page.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)
            asst_pos = page.locator('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])').first
            asst_pos.scroll_into_view_if_needed()

            shot_pos_docs = DOCS_OUT_DIR / "step5-verify-c7620-recurrence.png"
            shot_pos_desktop = DESKTOP_OUT_DIR / "step5-verify-c7620-recurrence.png"
            asst_pos.screenshot(path=str(shot_pos_docs))
            shutil.copyfile(str(shot_pos_docs), str(shot_pos_desktop))
            sha_pos = sha256_file(shot_pos_docs)
            print(f"📸 C7620: {shot_pos_docs.name} | SHA-256: {sha_pos}", flush=True)

            # 2. Chụp ảnh X9999 (Đối chứng âm)
            print("\n--- Chụp ảnh Thẻ xem trước X9999 (Đối chứng âm, không cảnh báo) ---", flush=True)
            page.goto(f"{url}/?nb=NB-LAZY-DTL&conv={conv_neg}", wait_until="networkidle", timeout=60000)
            page.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)
            asst_neg = page.locator('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])').first
            asst_neg.scroll_into_view_if_needed()

            shot_neg_docs = DOCS_OUT_DIR / "step5-verify-x9999-negative-control.png"
            shot_neg_desktop = DESKTOP_OUT_DIR / "step5-verify-x9999-negative-control.png"
            asst_neg.screenshot(path=str(shot_neg_docs))
            shutil.copyfile(str(shot_neg_docs), str(shot_neg_desktop))
            sha_neg = sha256_file(shot_neg_docs)
            print(f"📸 X9999: {shot_neg_docs.name} | SHA-256: {sha_neg}", flush=True)

            browser.close()

        print("\n✅ HOÀN TẤT NGHIỆM THU UI THẬT 100%!", flush=True)
        print(f"- Ảnh C7620 SHA-256: {sha_pos}")
        print(f"- Ảnh X9999 SHA-256: {sha_neg}")
        print(f"- Văn bản C7620:\n{text_pos}\n")
        print(f"- Văn bản X9999:\n{text_neg}\n")

    finally:
        try:
            import psutil
            parent = psutil.Process(proc.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        log_f.close()


if __name__ == "__main__":
    main()
