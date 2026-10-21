# -*- coding: utf-8 -*-
"""Reproduction and baseline measurement script for ticket DESKTOP-HOME-SEND-ACK-UX.

Measures baseline latency from clicking "Gửi" to the first visual feedback on UI.
Tests on real UI in Sổ Điều tra lỗi (NB-LAZY-DTL) with real question.
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
from aios_habit.workspace_chat_app import trigger_collection_warming_on_demand

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

        # Trigger warming in advance for clean measurement of send latency
        trigger_collection_warming_on_demand("dieu_tra_loi", notebook_id="NB-LAZY-DTL")

        target_conv = f"CONV-REPRO-SEND-{int(time.time())}"
        target_url = f"{url}/?nb=NB-LAZY-DTL&conv={target_conv}"
        print(f"[*] Navigating to {target_url}...", flush=True)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(target_url, wait_until="networkidle", timeout=45000)

            # Wait for composer textarea
            textarea = page.wait_for_selector('[class*="st-key-wsc_question_input_"] textarea', timeout=30000)
            print("[+] Composer textarea found.", flush=True)

            # Wait for send button to be enabled (warm worker)
            print("[*] Waiting for Send button to be enabled...", flush=True)
            send_btn = page.wait_for_selector(
                '[class*="st-key-wsc-action-"] button:not([disabled])',
                timeout=120000,
            )
            print("[+] Send button is ready and enabled.", flush=True)

            # Type real question
            real_question = "C6770 nguyen nhan thuong gap la gi?"
            textarea.fill(real_question)
            print(f"[+] Filled real test question: '{real_question}'", flush=True)

            page.wait_for_timeout(500)

            initial_user_bubbles_count = len(page.query_selector_all('[data-testid="stChatMessageAvatarUser"]'))
            initial_assistant_bubbles_count = len(page.query_selector_all('[data-testid="stChatMessageAvatarAssistant"]'))
            initial_btn_disabled = send_btn.is_disabled()
            initial_btn_text = send_btn.inner_text().strip()
            print(f"[*] Pre-click state: user_bubbles={initial_user_bubbles_count}, assistant_bubbles={initial_assistant_bubbles_count}, btn_text='{initial_btn_text}', btn_disabled={initial_btn_disabled}", flush=True)

            # Screenshot before click
            pre_click_png = OUT_DIR_LOCAL / "anh-repro-01-pre-click.png"
            page.screenshot(path=str(pre_click_png), full_page=True)

            # Now prepare measurement:
            # We want to measure the exact millisecond when the first visual feedback appears.
            print("[*] Clicking Send button and recording timestamps...", flush=True)
            t_click_perf = time.perf_counter()
            t_click_iso = datetime.datetime.now().isoformat()

            # Click send button
            send_btn.click()

            # Poll DOM with very high frequency (every 20ms) to detect first visual change
            first_visual_change = None
            t_first_visual_perf = None
            first_visual_type = None

            timeout_s = 20.0
            start_poll = time.perf_counter()

            while (time.perf_counter() - start_poll) < timeout_s:
                now_perf = time.perf_counter()

                # Check if a NEW user message bubble has appeared
                curr_user_bubbles = page.query_selector_all('[data-testid="stChatMessageAvatarUser"]')
                if len(curr_user_bubbles) > initial_user_bubbles_count:
                    first_visual_change = now_perf
                    first_visual_type = f"new_user_bubble_rendered (count: {len(curr_user_bubbles)})"
                    break

                # Check if assistant wait indicator has appeared
                curr_assistant_bubbles = page.query_selector_all('[data-testid="stChatMessageAvatarAssistant"]')
                if len(curr_assistant_bubbles) > initial_assistant_bubbles_count:
                    first_visual_change = now_perf
                    first_visual_type = f"assistant_wait_indicator (count: {len(curr_assistant_bubbles)})"
                    break

                # Check if send button changed to stop or disabled
                curr_btn = page.query_selector('[class*="st-key-wsc-action-"] button')
                if curr_btn:
                    is_dis = curr_btn.is_disabled()
                    btn_text = curr_btn.inner_text().strip()
                    if is_dis != initial_btn_disabled or btn_text != initial_btn_text:
                        first_visual_change = now_perf
                        first_visual_type = f"button_state_changed (disabled={is_dis}, text='{btn_text}')"
                        break

                time.sleep(0.02)

            t_first_visual_iso = datetime.datetime.now().isoformat() if first_visual_change else None
            latency_s = round(first_visual_change - t_click_perf, 3) if first_visual_change else -1

            print(f"[REPRO RESULT] Click timestamp: {t_click_iso}", flush=True)
            print(f"[REPRO RESULT] First visual feedback timestamp: {t_first_visual_iso}", flush=True)
            print(f"[REPRO RESULT] First visual feedback type: {first_visual_type}", flush=True)
            print(f"[REPRO RESULT] Measured latency to first visual feedback: {latency_s:.3f}s", flush=True)

            # Capture screenshot at first visual feedback
            ack_png = OUT_DIR_LOCAL / "anh-repro-02-first-visual-ack.png"
            page.screenshot(path=str(ack_png), full_page=True)

            # Wait for assistant response to complete
            print("[*] Waiting for query turn to complete...", flush=True)
            try:
                page.wait_for_selector(
                    '[data-testid="stChatMessageAvatarAssistant"]',
                    timeout=60000,
                )
                # wait until answer text stabilizes (no longer has streaming cursor or wait step)
                page.wait_for_timeout(3000)
            except Exception as e:
                print(f"[-] Wait assistant error: {e}", flush=True)

            repro_data = {
                "ticket": "DESKTOP-HOME-SEND-ACK-UX",
                "phase": "reproduction_baseline",
                "notebook_id": "NB-LAZY-DTL",
                "collection_id": "dieu_tra_loi",
                "question": real_question,
                "t_click_iso": t_click_iso,
                "t_first_visual_iso": t_first_visual_iso,
                "first_visual_type": first_visual_type,
                "latency_seconds": latency_s,
                "target_met": latency_s < 0.5 if latency_s > 0 else False,
            }

            repro_json_path = OUT_DIR_LOCAL / "reproduction_send_ack_evidence.json"
            repro_json_path.write_text(json.dumps(repro_data, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"[+] Saved reproduction evidence to {repro_json_path}", flush=True)

            browser.close()

    finally:
        print("[*] Terminating Streamlit server process...", flush=True)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    return 0


if __name__ == "__main__":
    sys.exit(main())
