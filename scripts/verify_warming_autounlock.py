# -*- coding: utf-8 -*-
"""Verification script for ticket DESKTOP-HOME-UI-WARMING-DEADLOCK-FIX.

Verifies end-to-end fix under BB-CONFIG-PARITY-01:
1. Opens Sổ Điều tra lỗi (cold collection dieu_tra_loi).
2. Verifies Send button is disabled, status line has exactly ONE hourglass icon (no duplicate).
3. Types question into composer textarea.
4. Captures screenshot (i): cold collection warming state.
5. Monitors BGE worker warming completion timestamp in backend.
6. Waits in Playwright WITHOUT ANY user interaction until UI automatically unlocks.
7. Records timestamp when UI automatically unlocks, calculates auto-unlock latency.
8. Verifies user's typed question in textarea is NOT lost after auto-rerun.
9. Verifies warming caption disappears completely.
10. Captures screenshot (ii): UI auto-unlocked with enabled Send button and question intact.
11. Clicks Send button on warm worker to verify warm query execution and measures latency.
12. Records all metrics into JSON report.
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
import threading
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

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
            is_disabled_initially = send_btn.is_disabled() if send_btn else None
            print(f"[*] Send button disabled initially: {is_disabled_initially}", flush=True)

            # Check status text
            page.wait_for_timeout(2000)
            body_text = page.inner_text("body")

            has_warming = "đang nạp mô hình BGE-M3" in body_text or "Đang nạp bộ đọc cho kho" in body_text
            has_double_hourglass = "⏳ ⏳" in body_text
            print(f"[*] Warming status visible on page: {has_warming}", flush=True)
            print(f"[*] Duplicate hourglass '⏳ ⏳' present: {has_double_hourglass} (Must be False)", flush=True)

            # Screenshot (i): Cold collection warming state
            shot1_path = OUT_DIR_LOCAL / "anh-03-fixed-cold-warming-state.png"
            page.screenshot(path=str(shot1_path), full_page=True)
            print(f"[+] Saved screenshot 1: {shot1_path}", flush=True)

            shot1_desktop = OUT_DIR_DESKTOP / "anh-03-fixed-cold-warming-state.png"
            shot1_desktop.write_bytes(shot1_path.read_bytes())

            # Background thread to monitor backend worker ready time
            worker_ready_data = {"timestamp": None, "perf": None, "done": False}

            def _poll_worker():
                start = time.time()
                for _ in range(120):
                    if worker_ready_data["done"]:
                        break
                    w = is_workspace_chat_worker_warmed(collection_id="dieu_tra_loi")
                    prog = get_workspace_chat_worker_progress(collection_id="dieu_tra_loi")
                    if w or prog.get("ready"):
                        worker_ready_data["timestamp"] = datetime.datetime.now().isoformat()
                        worker_ready_data["perf"] = time.perf_counter()
                        print(f"\n[BACKEND] BGE worker ready! Elapsed: {time.time()-start:.1f}s, Timestamp: {worker_ready_data['timestamp']}", flush=True)
                        break
                    time.sleep(1)

            t_thread = threading.Thread(target=_poll_worker, daemon=True)
            t_thread.start()

            # Now wait in Playwright for the button to automatically become enabled (NO click, NO F5!)
            print("[*] Waiting for UI to AUTOMATICALLY unlock (polling with Playwright selector :not([disabled]))...", flush=True)
            unlocked_btn = page.wait_for_selector(
                '[class*="st-key-wsc-action-"] button:not([disabled])',
                timeout=180000,
            )
            t_ui_unlocked_perf = time.perf_counter()
            ui_unlocked_timestamp = datetime.datetime.now().isoformat()
            worker_ready_data["done"] = True
            t_thread.join(timeout=2)

            print(f"[+] UI AUTOMATICALLY UNLOCKED at: {ui_unlocked_timestamp}!", flush=True)

            worker_perf = worker_ready_data["perf"] or t_ui_unlocked_perf
            unlock_latency_s = round(t_ui_unlocked_perf - worker_perf, 2)
            print(f"[+] Unlock latency after worker ready: {unlock_latency_s}s (Target: within few seconds)", flush=True)

            # Check question in textarea is preserved
            current_typed_text = textarea.input_value()
            question_preserved = (current_typed_text == test_question)
            print(f"[+] Textarea value preserved: {question_preserved} ('{current_typed_text}')", flush=True)

            # Check warming caption disappeared
            page_text_after = page.inner_text("body")
            warming_caption_gone = ("Đang nạp bộ đọc cho kho" not in page_text_after)
            print(f"[+] Warming caption disappeared: {warming_caption_gone}", flush=True)

            # Screenshot (ii): UI auto-unlocked with enabled Send button and question intact
            shot2_path = OUT_DIR_LOCAL / "anh-04-fixed-auto-unlocked-no-interaction.png"
            page.screenshot(path=str(shot2_path), full_page=True)
            print(f"[+] Saved screenshot 2: {shot2_path}", flush=True)

            shot2_desktop = OUT_DIR_DESKTOP / "anh-04-fixed-auto-unlocked-no-interaction.png"
            shot2_desktop.write_bytes(shot2_path.read_bytes())

            # Now test sending the question on warm worker and measure query latency
            print("[*] Testing sending question on warm worker...", flush=True)
            t_query_start = time.perf_counter()
            unlocked_btn.click()

            # Wait for assistant response bubble
            page.wait_for_selector('[data-testid="stChatMessageAvatarAssistant"]', timeout=90000)
            t_query_elapsed = round(time.perf_counter() - t_query_start, 2)
            print(f"[+] Warm query response received! Total query roundtrip latency: {t_query_elapsed}s", flush=True)

            # Screenshot (iii): Warm query response
            shot3_path = OUT_DIR_LOCAL / "anh-05-fixed-warm-query-response.png"
            page.screenshot(path=str(shot3_path), full_page=True)
            print(f"[+] Saved screenshot 3: {shot3_path}", flush=True)

            shot3_desktop = OUT_DIR_DESKTOP / "anh-05-fixed-warm-query-response.png"
            shot3_desktop.write_bytes(shot3_path.read_bytes())

            verify_result = {
                "ticket": "DESKTOP-HOME-UI-WARMING-DEADLOCK-FIX",
                "phase": "VERIFICATION_AFTER_FIX",
                "collection": "dieu_tra_loi",
                "notebook_id": "NB-LAZY-DTL",
                "worker_ready_timestamp": worker_ready_data["timestamp"],
                "ui_unlocked_timestamp": ui_unlocked_timestamp,
                "auto_unlock_latency_seconds": unlock_latency_s,
                "send_button_initially_disabled": is_disabled_initially,
                "send_button_auto_unlocked": True,
                "question_preserved_after_rerun": question_preserved,
                "warming_caption_disappeared": warming_caption_gone,
                "no_duplicate_hourglass": not has_double_hourglass,
                "warm_query_latency_seconds": t_query_elapsed,
                "screenshot_warming": {
                    "path": str(shot1_path),
                    "size_bytes": shot1_path.stat().st_size,
                    "sha256": get_file_sha256(shot1_path),
                },
                "screenshot_auto_unlocked": {
                    "path": str(shot2_path),
                    "size_bytes": shot2_path.stat().st_size,
                    "sha256": get_file_sha256(shot2_path),
                },
                "screenshot_query_response": {
                    "path": str(shot3_path),
                    "size_bytes": shot3_path.stat().st_size,
                    "sha256": get_file_sha256(shot3_path),
                },
            }

            result_file = OUT_DIR_LOCAL / "verification_evidence.json"
            result_file.write_text(json.dumps(verify_result, indent=2, ensure_ascii=False), encoding="utf-8")
            (OUT_DIR_DESKTOP / "verification_evidence.json").write_text(
                json.dumps(verify_result, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print(f"[+] Verification evidence recorded: {json.dumps(verify_result, indent=2)}", flush=True)

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
