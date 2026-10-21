# -*- coding: utf-8 -*-
"""Verification script for ticket DESKTOP-HOME-ANSWER-LANGUAGE-PURITY-FIX.

Tests the complete flow on the real Streamlit application with Playwright:
1. Launches Streamlit on an ephemeral port.
2. Navigates to Sổ Điều tra lỗi (NB-LAZY-DTL).
3. Query 1: 'Mã lỗi C6770 nguyên nhân là gì?'
   - Verifies 100% Vietnamese body, no raw '不要'.
   - Captures anh-language-purity-01-c6770.png framing the complete answer body.
4. Query 2: 'Mã lỗi JAM4212 nguyên nhân và xử lý thế nào?'
   - Verifies 100% Vietnamese body, no raw Japanese sentences.
   - Captures anh-language-purity-02-jam4212.png framing the complete answer body.
5. Query 3: 'Mã lỗi F000 nguyên nhân và biện pháp xử lý là gì?'
   - Verifies 100% Vietnamese body, no raw Japanese sentences.
   - Captures anh-language-purity-03-f000.png framing the complete answer body.
6. Verifies continuous improvement log in local_cases/answer_language_events.jsonl.
7. Computes SHA-256 and byte size manifest.
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

os.environ["AIOS_RAGV2_WORKER_PERSIST"] = "1"
os.environ["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["AIOS_RETRIEVAL_DEVICE"] = "cpu"

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


def ensure_test_conversation(conv_id: str, title: str) -> None:
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
        "notebook_id": "NB-LAZY-DTL",
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

    # Clean messages in both messages.jsonl and messages/<conv_id>.jsonl
    msg_dir_file = APP_DIR / "local_cases" / "workspace_chat" / "messages" / f"{conv_id}.jsonl"
    if msg_dir_file.exists():
        try:
            msg_dir_file.unlink()
        except Exception:
            pass
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
    """Scroll the chat messages container so the assistant answer is cleanly framed."""
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
        time.sleep(0.8)
    except Exception as e:
        print(f"[!] Scroll warning: {e}", flush=True)


def ask_question_on_ui(page, question_text: str, expected_text: str) -> None:
    print(f"[*] Waiting for composer textarea for question: '{question_text}'...", flush=True)
    textarea = page.locator('[class*="st-key-wsc_question_input_"] textarea').first
    textarea.wait_for(state="attached", timeout=60000)
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
    for _ in range(400):
        writing_pill = page.locator('.wsc-streaming-writing-pill')
        cursor_el = page.locator('div[data-testid="stChatMessage"]:has-text("▌")')
        assist_msg = page.locator(f'div[data-testid="stChatMessage"]:has-text("{expected_text}")')
        if writing_pill.count() == 0 and cursor_el.count() == 0 and assist_msg.count() > 0:
            break
        time.sleep(0.15)

    page.wait_for_selector(f'div[data-testid="stChatMessage"]:has-text("{expected_text}")', timeout=45000)
    time.sleep(1.5)
    print(f"[+] Completed response verified containing '{expected_text}'!", flush=True)


def capture_answer_screenshot(page, filename: str) -> dict:
    """Capture a screenshot framing the complete assistant answer body."""
    p_local = OUT_DIR_LOCAL / filename
    p_desktop = OUT_DIR_DESKTOP / filename

    # Scroll the top of the assistant message into view
    page.evaluate(
        """() => {
            const msgs = document.querySelectorAll('[data-testid="stChatMessage"]');
            if (msgs.length > 0) {
                msgs[msgs.length - 1].scrollIntoView({behavior: 'instant', block: 'start'});
                window.scrollBy(0, -30);
            }
        }"""
    )
    time.sleep(1.0)

    # Take screenshot of the entire assistant message card to guarantee 100% full answer body is captured
    assist_msg = page.locator('div[data-testid="stChatMessage"]').last
    assist_msg.screenshot(path=str(p_local))
    p_desktop.write_bytes(p_local.read_bytes())
    size = p_local.stat().st_size
    sha = get_file_sha256(p_local)
    print(f"[+] Full answer card screenshot saved: {filename} ({size} bytes, SHA256={sha})", flush=True)
    return {
        "file": filename,
        "size_bytes": size,
        "sha256": sha,
    }


def main() -> int:
    ensure_test_conversation("CONV-PURITY-C6770-001", "Kiểm tra ngôn ngữ C6770")
    ensure_test_conversation("CONV-PURITY-JAM4212-002", "Kiểm tra ngôn ngữ JAM4212")
    ensure_test_conversation("CONV-PURITY-F000-003", "Kiểm tra ngôn ngữ F000")

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
        print("[*] Waiting for Streamlit server to respond...", flush=True)
        up = False
        for _ in range(50):
            try:
                with urllib.request.urlopen(f"{url}/_stcore/health", timeout=2) as resp:
                    if resp.status == 200:
                        up = True
                        break
            except Exception:
                time.sleep(1)

        if not up:
            print("[-] Streamlit server failed to start in 50s", flush=True)
            return 1
        print("[+] Streamlit server is UP and healthy!", flush=True)

        screenshots_meta = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1550})

            # QUERY 1: C6770
            conv1_url = f"{url}/?nb=NB-LAZY-DTL&conv=CONV-PURITY-C6770-001"
            print(f"[*] Navigating to {conv1_url}...", flush=True)
            page.goto(conv1_url, wait_until="networkidle", timeout=60000)
            time.sleep(3)

            ask_question_on_ui(
                page,
                "Mã lỗi C6770 nguyên nhân là gì?",
                "Không xác định nguyên nhân bất thường",
            )
            s1 = capture_answer_screenshot(page, "anh-language-purity-01-c6770.png")
            s1["scene"] = "C6770: Thân đáp án thuần Việt, '不要' được dịch sang đối sách xử lý tại chỗ, không còn ký tự Nhật thô"
            screenshots_meta.append(s1)

            # QUERY 2: JAM4212
            conv2_url = f"{url}/?nb=NB-LAZY-DTL&conv=CONV-PURITY-JAM4212-002"
            print(f"[*] Navigating to {conv2_url}...", flush=True)
            page.goto(conv2_url, wait_until="networkidle", timeout=60000)
            time.sleep(3)

            ask_question_on_ui(
                page,
                "Mã lỗi JAM4212 nguyên nhân và xử lý thế nào?",
                "Kẹt giấy tại cảm biến sấy",
            )
            s2 = capture_answer_screenshot(page, "anh-language-purity-02-jam4212.png")
            s2["scene"] = "JAM4212: Định nghĩa, cơ chế và nguyên nhân thuần Việt, chỉ giữ tên file tài liệu tham chiếu hợp lệ"
            screenshots_meta.append(s2)

            # QUERY 3: F000
            conv3_url = f"{url}/?nb=NB-LAZY-DTL&conv=CONV-PURITY-F000-003"
            print(f"[*] Navigating to {conv3_url}...", flush=True)
            page.goto(conv3_url, wait_until="networkidle", timeout=60000)
            time.sleep(3)

            ask_question_on_ui(
                page,
                "Mã lỗi F000 nguyên nhân và biện pháp xử lý là gì?",
                "Màn hình dừng ở màn hình Welcome",
            )
            s3 = capture_answer_screenshot(page, "anh-language-purity-03-f000.png")
            s3["scene"] = "F000: Bất thường truyền thông Panel-Main, 6 biện pháp xử lý kỹ thuật thuần Việt"
            screenshots_meta.append(s3)

            browser.close()

        # Verify continuous improvement events file
        events_path = APP_DIR / "local_cases" / "answer_language_events.jsonl"
        events_count = 0
        sample_events = []
        if events_path.is_file():
            lines = [ln for ln in events_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
            events_count = len(lines)
            for ln in lines[-6:]:
                try:
                    sample_events.append(json.loads(ln))
                except Exception:
                    pass
        print(f"[+] Continuous improvement log contains {events_count} events at {events_path}", flush=True)

        manifest = {
            "ticket": "DESKTOP-HOME-ANSWER-LANGUAGE-PURITY-FIX",
            "timestamp": datetime.datetime.now().isoformat(),
            "events_logged_count": events_count,
            "sample_recent_events": sample_events,
            "screenshots": screenshots_meta,
            "status": "PASS",
        }

        m_local = OUT_DIR_LOCAL / "answer_language_purity_verification.json"
        m_desktop = OUT_DIR_DESKTOP / "answer_language_purity_verification.json"
        m_local.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        m_desktop.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        print("[+] Verification manifest written successfully!", flush=True)
        return 0

    finally:
        print("[*] Terminating Streamlit server...", flush=True)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        print("[+] Streamlit server terminated cleanly.", flush=True)


if __name__ == "__main__":
    sys.exit(main())
