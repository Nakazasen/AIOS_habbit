# -*- coding: utf-8 -*-
"""Verification script for Scenes 6, 7, and 8 of ticket DESKTOP-HOME-FUZZY-MEMORY-SEARCH-VERIFY-FIX.
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

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR / "src"))

from playwright.sync_api import sync_playwright

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


def ensure_test_conversation(conv_id: str, title: str, notebook_id: str = "NB-LAZY-DTL") -> None:
    conv_file = APP_DIR / "local_cases" / "workspace_chat" / "conversations.jsonl"
    conv_file.parent.mkdir(parents=True, exist_ok=True)
    lines = conv_file.read_text(encoding="utf-8").splitlines() if conv_file.exists() else []
    kept_convs = []
    for ln in lines:
        if not ln.strip():
            continue
        try:
            if json.loads(ln).get("id") != conv_id:
                kept_convs.append(ln)
        except Exception:
            kept_convs.append(ln)
    record = {
        "id": conv_id,
        "notebook_id": notebook_id,
        "title": title,
        "created_at": datetime.datetime.now().isoformat(),
        "updated_at": datetime.datetime.now().isoformat(),
        "selected_source_ids": [],
        "temporary_source_ids": [],
        "saved_case_id": None,
        "compressed_memory": "",
        "search_preference": "auto",
        "ui_locale": "vi",
        "answer_language": "vi",
        "ai_mode": "grounded",
    }
    kept_convs.append(json.dumps(record, ensure_ascii=False))
    conv_file.write_text("\n".join(kept_convs) + "\n", encoding="utf-8")

    # Clean messages in messages.jsonl
    msg_file = APP_DIR / "local_cases" / "workspace_chat" / "messages.jsonl"
    if msg_file.exists():
        kept = []
        for ln in msg_file.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            try:
                if json.loads(ln).get("conversation_id") != conv_id:
                    kept.append(ln)
            except Exception:
                kept.append(ln)
        msg_file.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")


def scroll_chat_messages_into_view(page) -> None:
    try:
        page.evaluate(
            """() => {
                const msgs = document.querySelectorAll('[data-testid="stChatMessage"]');
                if (msgs.length > 0) {
                    msgs[0].scrollIntoView({behavior: 'instant', block: 'start'});
                    window.scrollBy(0, -40);
                }
            }"""
        )
        page.wait_for_timeout(800)
    except Exception as e:
        print(f"[!] Scroll warning: {e}", flush=True)


def ask_question_on_ui(page, question_text: str, expected_text: str) -> None:
    print(f"[*] Waiting for composer textarea for question: '{question_text}'...", flush=True)
    textarea = page.locator('[class*="st-key-wsc_question_input_"] textarea').first
    textarea.wait_for(state="visible", timeout=45000)
    textarea.scroll_into_view_if_needed()
    textarea.fill(question_text)
    page.wait_for_timeout(800)

    print("[*] Waiting for enabled Send button...", flush=True)
    send_btn = page.locator(
        '[class*="st-key-wsc_ask_"] button:not([disabled]), [class*="st-key-wsc-action-"] button:not([disabled])'
    ).first
    send_btn.wait_for(state="visible", timeout=120000)
    send_btn.click(no_wait_after=True)
    print(f"[+] Send clicked for '{question_text}'!", flush=True)

    print(f"[*] Waiting for streaming completion and '{expected_text}'...", flush=True)
    for _ in range(300):
        writing_pill = page.locator('.wsc-streaming-writing-pill')
        cursor_el = page.locator('div[data-testid="stChatMessage"]:has-text("▌")')
        assist_msg = page.locator(f'div[data-testid="stChatMessage"]:has-text("{expected_text}")')
        if writing_pill.count() == 0 and cursor_el.count() == 0 and assist_msg.count() > 0:
            break
        page.wait_for_timeout(200)

    page.wait_for_selector(f'div[data-testid="stChatMessage"]:has-text("{expected_text}")', timeout=30000)
    page.wait_for_timeout(1500)
    scroll_chat_messages_into_view(page)
    print(f"[+] Completed response verified containing '{expected_text}'!", flush=True)


def save_dual_screenshot(page, filename: str) -> dict:
    p_local = OUT_DIR_LOCAL / filename
    p_desktop = OUT_DIR_DESKTOP / filename
    page.screenshot(path=str(p_local), full_page=False)
    p_desktop.write_bytes(p_local.read_bytes())
    size = p_local.stat().st_size
    sha = get_file_sha256(p_local)
    print(f"[+] Raw binary screenshot saved: {filename} ({size} bytes, SHA256={sha})", flush=True)
    return {
        "file": filename,
        "size_bytes": size,
        "sha256": sha,
    }


def main() -> int:
    ensure_test_conversation("CONV-FUZZY-MOM-DOMAIN-CHECK", "Kiểm chứng phạm vi miền: Sổ MOM hỏi JAM4212", "mom_opcenter")
    ensure_test_conversation("CONV-FUZZY-DTL-JAM4212-CONTROL", "Đối chứng: Sổ Điều tra lỗi hỏi JAM4212", "NB-LAZY-DTL")
    ensure_test_conversation("CONV-FUZZY-COLD-SWITCH-REGRESSION", "Hồi quy: Chuyển sổ lạnh rồi chờ tay không", "NB-LAZY-LSU")

    port = find_free_port()
    url = f"http://127.0.0.1:{port}"
    print(f"[*] Starting Streamlit on port {port}...", flush=True)

    server_env = os.environ.copy()
    server_env["PYTHONPATH"] = "src"
    server_env["OMP_NUM_THREADS"] = "1"
    server_env["MKL_NUM_THREADS"] = "1"
    server_env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    server_env["AIOS_RETRIEVAL_DEVICE"] = "cpu"
    server_env["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
    server_env["AIOS_RAG_V2_NUMPY_SCORING"] = "1"
    server_env["AIOS_AI_BACKEND"] = "nakazasen_router"
    server_env["AIOS_FEATURE_CHAT_ACTION"] = "1"
    server_env["AIOS_DOMAIN_ROUTING_ENABLED"] = "1"
    server_env["PYTHONIOENCODING"] = "utf-8"
    server_env["PYTHONUNBUFFERED"] = "1"
    server_env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    server_env["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
    server_env["STREAMLIT_SERVER_RUN_ON_SAVE"] = "false"
    server_env["STREAMLIT_SERVER_PORT"] = str(port)
    server_env["STREAMLIT_SERVER_HEADLESS"] = "true"
    server_env.pop("AIOS_RAGV2_WORKER_PERSIST", None)

    py_exe = APP_DIR / ".venv" / "Scripts" / "python.exe"

    log_file_path = APP_DIR / "scripts" / "streamlit_e2e_scenes_6_7_8.log"
    log_f = open(log_file_path, "w", encoding="utf-8")

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
        stdout=log_f,
        stderr=subprocess.STDOUT,
    )

    try:
        print("[*] Waiting for Streamlit server to respond...", flush=True)
        up = False
        for _ in range(45):
            try:
                with urllib.request.urlopen(f"{url}/_stcore/health", timeout=2) as resp:
                    if resp.status == 200:
                        up = True
                        break
            except Exception:
                time.sleep(1)

        if not up:
            print("[-] Streamlit server failed to start in 45s", flush=True)
            return 1
        print("[+] Streamlit server is UP and healthy!", flush=True)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1550})

            # SCENE 6: Domain Scope check in Sổ MOM (mom_opcenter) -> JAM4212
            conv6_url = f"{url}/?nb=mom_opcenter&conv=CONV-FUZZY-MOM-DOMAIN-CHECK"
            print(f"[*] Navigating to {conv6_url}...", flush=True)
            page.goto(conv6_url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)
            ask_question_on_ui(
                page,
                "JAM4212",
                "Kho tài liệu MOM",
            )
            s6 = save_dual_screenshot(page, "anh-fuzzy-06-mom-jam4212-scope-isolation.png")

            # SCENE 7: Control check in Sổ Điều tra lỗi (NB-LAZY-DTL) -> JAM4212 (30.075 ca, cards)
            conv7_url = f"{url}/?nb=NB-LAZY-DTL&conv=CONV-FUZZY-DTL-JAM4212-CONTROL"
            print(f"[*] Navigating to {conv7_url}...", flush=True)
            page.goto(conv7_url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(2000)
            ask_question_on_ui(
                page,
                "JAM4212",
                "30.075",
            )
            s7 = save_dual_screenshot(page, "anh-fuzzy-07-dieu-tra-loi-jam4212-control.png")

            # SCENE 8: Cold-switch regression: "Chuyển sổ lạnh rồi chờ tay không"
            conv8_url = f"{url}/?nb=NB-LAZY-LSU&conv=CONV-FUZZY-COLD-SWITCH-REGRESSION"
            print(f"[*] Navigating to {conv8_url}...", flush=True)
            page.goto(conv8_url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(2000)
            ask_question_on_ui(
                page,
                "C0030",
                "C0030",
            )
            s8 = save_dual_screenshot(page, "anh-fuzzy-08-cold-switch-cho-tay-khong.png")

            browser.close()

        print("[+] Scenes 6, 7, 8 captured successfully!", flush=True)
        return 0

    except Exception as e:
        print(f"[-] Execution error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        print("[*] Terminating Streamlit server process...", flush=True)
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        try:
            log_f.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
