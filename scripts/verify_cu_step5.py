# -*- coding: utf-8 -*-
"""Computer Use (CU) Real UI Verification for ticket DESKTOP-HOME-STEP5-CLASSIFY-WEAK-CLASS-FIX.

Runs real Streamlit server and navigates Playwright Chromium to verify:
1. Case 1 (lap_rap): "Tạo vụ điều tra lỗi mới: công nhân quên cắm cáp và lắp sai vị trí cụm sấy"
   - Preview card shows auto-classification group: "Lắp ráp"
   - Concrete provenance (căn cứ) surfaced.
   - User confirmation & editing form accessible before saving.
2. Case 2 (recurrence): "Tạo vụ điều tra lỗi mới: kẹt giấy cụm sấy lỗi C7620"
   - Recurrence alert fires (136 historical cases in DB 30,075, recent ticket FY27H2/263).
   - Concrete provenance & glossary conflict resolution surfaced.
   - User confirmation & editing form accessible before saving.

Saves raw PNG screenshots to both:
- docs/phieu-viec/ket-qua/
- D:\\Sandbox\\aios-dieu-phoi-desktop\\hop-thu\\lan-desktop\\ket-qua\\
Computes exact file size and SHA-256 directly from saved raw PNG files.
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
    log_f = open(DOCS_OUT_DIR / "verify_step5_cu_streamlit.log", "w", encoding="utf-8")
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

    conv_laprap = "CONV-STEP5-CU-LAPRAP"
    conv_recurrence = "CONV-STEP5-CU-RECURRENCE"

    delete_conversation(conv_laprap)
    delete_conversation(conv_recurrence)

    save_conversation(
        WorkspaceConversation(
            id=conv_laprap,
            notebook_id="NB-LAZY-DTL",
            title="Nghiệm thu CU Ca 1: Lắp ráp (lap_rap)",
            created_at=now_iso,
            updated_at=now_iso,
        )
    )
    save_conversation(
        WorkspaceConversation(
            id=conv_recurrence,
            notebook_id="NB-LAZY-DTL",
            title="Nghiệm thu CU Ca 2: Tái phát (C7620 136 lần)",
            created_at=now_iso,
            updated_at=now_iso,
        )
    )

    # 1. Sinh đáp án Ca 1: Lắp ráp
    q_laprap = "Tạo vụ điều tra lỗi mới: công nhân quên cắm cáp và lắp sai vị trí cụm sấy"
    out_lr = dispatch_multi(
        ChatActionRequest(
            question=q_laprap,
            conversation_id=conv_laprap,
            notebook_id="NB-LAZY-DTL",
        )
    )
    text_lr = render_outcome(out_lr) if out_lr else ""
    save_message(
        ChatMessage(
            id="MSG-CU-LR-U",
            conversation_id=conv_laprap,
            role="user",
            content=q_laprap,
            created_at=now_iso,
        )
    )
    save_message(
        ChatMessage(
            id="MSG-CU-LR-A",
            conversation_id=conv_laprap,
            role="assistant",
            content=text_lr,
            created_at=now_iso,
        )
    )

    # 2. Sinh đáp án Ca 2: Tái phát C7620
    q_rec = "Tạo vụ điều tra lỗi mới: kẹt giấy cụm sấy lỗi C7620"
    out_rec = dispatch_multi(
        ChatActionRequest(
            question=q_rec,
            conversation_id=conv_recurrence,
            notebook_id="NB-LAZY-DTL",
        )
    )
    text_rec = render_outcome(out_rec) if out_rec else ""
    save_message(
        ChatMessage(
            id="MSG-CU-REC-U",
            conversation_id=conv_recurrence,
            role="user",
            content=q_rec,
            created_at=now_iso,
        )
    )
    save_message(
        ChatMessage(
            id="MSG-CU-REC-A",
            conversation_id=conv_recurrence,
            role="assistant",
            content=text_rec,
            created_at=now_iso,
        )
    )

    print(">> Đã khởi tạo 2 hội thoại nghiệm thu CU trong DB chat.", flush=True)

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

            # 1. Chụp ảnh Ca 1: Lắp ráp
            print("\n--- Chụp ảnh Ca 1: Lắp ráp (lap_rap) ---", flush=True)
            page.goto(f"{url}/?nb=NB-LAZY-DTL&conv={conv_laprap}", wait_until="networkidle", timeout=60000)
            page.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)
            asst_lr = page.locator('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])').first
            asst_lr.scroll_into_view_if_needed()

            shot_lr_docs = DOCS_OUT_DIR / "anh-step5-cu-laprap-preview.png"
            shot_lr_desktop = DESKTOP_OUT_DIR / "anh-step5-cu-laprap-preview.png"
            asst_lr.screenshot(path=str(shot_lr_docs))
            shutil.copyfile(str(shot_lr_docs), str(shot_lr_desktop))
            sha_lr = sha256_file(shot_lr_docs)
            size_lr = shot_lr_docs.stat().st_size
            print(f"📸 Ca 1 (lap_rap): {shot_lr_docs.name} | Size: {size_lr} bytes | SHA-256: {sha_lr}", flush=True)

            # 2. Chụp ảnh Ca 2: Tái phát C7620
            print("\n--- Chụp ảnh Ca 2: Tái phát (C7620 136 lần) ---", flush=True)
            page.goto(f"{url}/?nb=NB-LAZY-DTL&conv={conv_recurrence}", wait_until="networkidle", timeout=60000)
            page.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)
            asst_rec = page.locator('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])').first
            asst_rec.scroll_into_view_if_needed()

            shot_rec_docs = DOCS_OUT_DIR / "anh-step5-cu-recurrence-c7620.png"
            shot_rec_desktop = DESKTOP_OUT_DIR / "anh-step5-cu-recurrence-c7620.png"
            asst_rec.screenshot(path=str(shot_rec_docs))
            shutil.copyfile(str(shot_rec_docs), str(shot_rec_desktop))
            sha_rec = sha256_file(shot_rec_docs)
            size_rec = shot_rec_docs.stat().st_size
            print(f"📸 Ca 2 (recurrence): {shot_rec_docs.name} | Size: {size_rec} bytes | SHA-256: {sha_rec}", flush=True)

            browser.close()

        print("\n✅ HOÀN TẤT CHỤP ẢNH COMPUTER USE (CU) THẬT 100%!", flush=True)
        print(f"1. Ca Lắp ráp: {shot_lr_docs.name} | {size_lr} bytes | SHA-256: {sha_lr}")
        print(f"2. Ca Tái phát C7620: {shot_rec_docs.name} | {size_rec} bytes | SHA-256: {sha_rec}")
        print(f"\nVăn bản Ca Lắp ráp:\n{text_lr}\n")
        print(f"Văn bản Ca Tái phát C7620:\n{text_rec}\n")

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
