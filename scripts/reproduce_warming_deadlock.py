# -*- coding: utf-8 -*-
"""Reproduction script for ticket DESKTOP-HOME-UI-WARMING-DEADLOCK-FIX.

Captures pre-fix evidence under BB-CONFIG-PARITY-01:
1. Opens Sổ Điều tra lỗi (cold collection dieu_tra_loi).
2. Verifies Send button is disabled and warming status line is shown.
3. Enters question into composer textarea.
4. Captures screenshot (i): cold collection warming state.
5. Polls backend until BGE worker for dieu_tra_loi reports ready=True.
6. Waits 10 seconds without any user interaction (no click, no F5).
7. Verifies that Streamlit UI did NOT auto-rerun and remains permanently deadlocked.
8. Captures screenshot (ii): UI deadlocked with Send button still locked.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Ensure standard production environment
os.environ["AIOS_RAGV2_WORKER_PERSIST"] = "1"
os.environ["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["AIOS_RETRIEVAL_DEVICE"] = "cpu"

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR / "src"))

from playwright.sync_api import sync_playwright

from aios_habit.workspace_chat_rag_v2_adapter import (
    get_workspace_chat_worker_progress,
    is_workspace_chat_worker_warmed,
)

OUT_DIR_LOCAL = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
OUT_DIR_LOCAL.mkdir(parents=True, exist_ok=True)

OUT_DIR_DESKTOP = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")
OUT_DIR_DESKTOP.mkdir(parents=True, exist_ok=True)


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def get_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def main() -> int:
    port = find_free_port()
    url = f"http://127.0.0.1:{port}"
    print(f"[*] Starting Streamlit on port {port}...", flush=True)

    server_env = os.environ.copy()
    server_env["PYTHONPATH"] = "src"
    server_env["AIOS_RAGV2_WORKER_PERSIST"] = "1"
    server_env["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
    server_env["OMP_NUM_THREADS"] = "1"
    server_env["MKL_NUM_THREADS"] = "1"
    server_env["AIOS_RETRIEVAL_DEVICE"] = "cpu"
    server_env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    server_env["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
    server_env["STREAMLIT_SERVER_RUN_ON_SAVE"] = "false"
    server_env["STREAMLIT_SERVER_PORT"] = str(port)
    server_env["STREAMLIT_SERVER_HEADLESS"] = "true"

    py_exe = APP_DIR / ".venv" / "Scripts" / "python.exe"

    proc = subprocess.Popen(
        [
            str(py_exe),
            "-m",
            "streamlit",
            "run",
            "src/aios_habit/workspace_chat_app.py",
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
            "--server.fileWatcherType",
            "none",
            "--server.runOnSave",
            "false",
        ],
        cwd=str(APP_DIR),
        env=server_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # Wait for Streamlit server to start
        print("[*] Waiting for Streamlit server to respond...", flush=True)
        up = False
        for _ in range(30):
            try:
                with urllib.request.urlopen(f"{url}/_stcore/health", timeout=2) as resp:
                    if resp.status == 200:
                        up = True
                        break
            except Exception:
                time.sleep(1)

        if not up:
            print("[-] Streamlit server failed to start in 30s", flush=True)
            return 1
        print("[+] Streamlit server is UP and healthy!", flush=True)

        target_url = f"{url}/?nb=NB-LAZY-DTL&conv=CONV-LAZY-P2-DTL-99E41D"
        print(f"[*] Navigating to {target_url}...", flush=True)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(target_url, wait_until="networkidle", timeout=45000)

            # Wait for composer textarea
            textarea = page.wait_for_selector('[class*="st-key-wsc_question_input_"] textarea', timeout=30000)
            print("[+] Composer textarea found.", flush=True)

            # Type question
            test_question = "Tìm nguyên nhân lỗi rò dầu xi lanh và cách xử lý"
            textarea.fill(test_question)
            print(f"[+] Filled test question: '{test_question}'", flush=True)

            # Check send button disabled status
            send_btn = page.query_selector('[class*="st-key-wsc-action-"] button')
            is_disabled = send_btn.is_disabled() if send_btn else None
            print(f"[*] Send button disabled: {is_disabled}", flush=True)

            # Check status text
            page.wait_for_timeout(2000)
            body_text = page.inner_text("body")

            has_warming = "đang nạp mô hình BGE-M3" in body_text or "Đang nạp bộ đọc cho kho" in body_text
            print(f"[*] Warming status visible on page: {has_warming}", flush=True)

            # Screenshot (i): Cold collection warming state
            shot1_path = OUT_DIR_LOCAL / "anh-01-repro-warming-cold-dieu-tra-loi.png"
            page.screenshot(path=str(shot1_path), full_page=True)
            print(f"[+] Saved screenshot 1: {shot1_path}", flush=True)

            # Also copy to desktop out dir
            shot1_desktop = OUT_DIR_DESKTOP / "anh-01-repro-warming-cold-dieu-tra-loi.png"
            shot1_desktop.write_bytes(shot1_path.read_bytes())

            # Now poll until worker is warmed in backend
            print("[*] Polling backend for BGE worker warming completion...", flush=True)
            warmed = False
            start_poll = time.time()
            worker_ready_timestamp = None

            for i in range(120):
                w = is_workspace_chat_worker_warmed(collection_id="dieu_tra_loi")
                prog = get_workspace_chat_worker_progress(collection_id="dieu_tra_loi")
                if w or prog.get("ready"):
                    warmed = True
                    worker_ready_timestamp = datetime.datetime.now().isoformat()
                    elapsed = time.time() - start_poll
                    print(f"[+] BGE worker ready! Elapsed: {elapsed:.1f}s, Ready timestamp: {worker_ready_timestamp}", flush=True)
                    print(f"    Progress info: {prog}", flush=True)
                    break
                if i % 5 == 0:
                    print(f"    Waiting for worker... ({i*2}s) status: {prog.get('reason')} alive: {prog.get('alive')} pid: {prog.get('pid')}", flush=True)
                time.sleep(2)

            if not warmed:
                print("[-] Worker did not become ready within 240s!", flush=True)
                return 1

            # Wait 10 seconds without any user interaction
            print("[*] Waiting 10s WITHOUT user interaction to verify deadlock...", flush=True)
            time.sleep(10)

            # Check UI state again
            send_btn_after = page.query_selector('[class*="st-key-wsc-action-"] button')
            is_still_disabled = send_btn_after.is_disabled() if send_btn_after else None
            ui_check_timestamp = datetime.datetime.now().isoformat()

            body_text_after = page.inner_text("body")
            warming_still_present = "đang nạp mô hình BGE-M3" in body_text_after or "Đang nạp bộ đọc cho kho" in body_text_after

            print(f"[!] UI check timestamp: {ui_check_timestamp}", flush=True)
            print(f"[!] Send button STILL disabled: {is_still_disabled}", flush=True)
            print(f"[!] Warming caption STILL present: {warming_still_present}", flush=True)

            # Screenshot (ii): Deadlocked UI after worker ready
            shot2_path = OUT_DIR_LOCAL / "anh-02-repro-deadlock-after-worker-ready.png"
            page.screenshot(path=str(shot2_path), full_page=True)
            print(f"[+] Saved screenshot 2: {shot2_path}", flush=True)

            shot2_desktop = OUT_DIR_DESKTOP / "anh-02-repro-deadlock-after-worker-ready.png"
            shot2_desktop.write_bytes(shot2_path.read_bytes())

            repro_result = {
                "ticket": "DESKTOP-HOME-UI-WARMING-DEADLOCK-FIX",
                "phase": "REPRODUCTION_BEFORE_FIX",
                "collection": "dieu_tra_loi",
                "notebook_id": "NB-LAZY-DTL",
                "worker_ready_timestamp": worker_ready_timestamp,
                "ui_check_timestamp": ui_check_timestamp,
                "send_button_disabled_initially": is_disabled,
                "send_button_still_disabled_after_worker_ready": is_still_disabled,
                "warming_caption_still_present": warming_still_present,
                "screenshot_1": {
                    "path": str(shot1_path),
                    "size_bytes": shot1_path.stat().st_size,
                    "sha256": get_file_sha256(shot1_path),
                },
                "screenshot_2": {
                    "path": str(shot2_path),
                    "size_bytes": shot2_path.stat().st_size,
                    "sha256": get_file_sha256(shot2_path),
                },
            }

            result_file = OUT_DIR_LOCAL / "reproduction_evidence.json"
            result_file.write_text(json.dumps(repro_result, indent=2, ensure_ascii=False), encoding="utf-8")
            (OUT_DIR_DESKTOP / "reproduction_evidence.json").write_text(
                json.dumps(repro_result, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print(f"[+] Reproduction evidence recorded: {json.dumps(repro_result, indent=2)}", flush=True)

            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        print("[*] Streamlit server terminated.", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
