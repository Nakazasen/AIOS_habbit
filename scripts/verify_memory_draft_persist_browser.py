# -*- coding: utf-8 -*-
"""Verification script for ticket DESKTOP-MEMORY-DRAFT-PERSIST-HOME.

Browser acceptance test with real Chromium:
1. Opens Workspace Chat session 1 on target conversation.
2. Sends command: "Hãy nhớ: Khi bảo dưỡng máy nén khí phải xả áp bình tích trước khi mở van"
3. Verifies pending draft box appears in UI and pending_drafts.json exists on disk.
4. Captures screenshot 1.
5. Closes browser context (simulates closing/restarting browser session).
6. Opens brand-new browser context 2.
7. Verifies pending draft is intact in the awaiting review frame ("nhu chua tung dong phien").
8. Captures screenshot 2.
9. Clicks "Xác nhận".
10. Verifies pending draft disappears from UI, pending_drafts.json is cleared from disk,
    and decision is saved to local_cases/workspace_memory/memory_decisions.jsonl.
11. Captures screenshot 3.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import uuid
from typing import Any

from playwright.sync_api import sync_playwright

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
PYTHON_EXE = APP_DIR / ".venv" / "Scripts" / "python.exe"
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR / "src"))

from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import load_active_notebooks, save_conversation
from aios_habit.workspace_memory_service import (
    default_decisions_path,
    default_pending_drafts_path,
    load_pending_drafts,
    set_workspace_memory_enabled_preference,
)

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

PORT = 8574
URL = f"http://localhost:{PORT}"
OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SERVER_LOG_FILE = OUT_DIR / "server_memory_draft_persist_verify.log"


def log(msg: str) -> None:
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{now_str}] {msg}"
    try:
        print(formatted, flush=True)
    except Exception:
        try:
            print(formatted.encode("ascii", errors="replace").decode("ascii"), flush=True)
        except Exception:
            pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def get_git_head() -> str:
    try:
        res = subprocess.run(
            ["git", "-C", str(APP_DIR), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception as exc:
        return f"UNKNOWN ({exc})"


def wait_for_server(url: str, timeout_s: float = 60.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            req = urllib.request.Request(f"{url}/_stcore/health")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(1.0)
    return False


def start_server() -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(APP_DIR / "src")
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    env["AIOS_RETRIEVAL_DEVICE"] = "cpu"
    env["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
    env["AIOS_RAG_V2_NUMPY_SCORING"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    env["STREAMLIT_SERVER_PORT"] = str(PORT)
    env["AIOS_AI_BACKEND"] = "local"
    env["AIOS_MAX_PERSISTENT_WORKERS"] = "1"
    env["AIOS_RAG_WARMED_OVERRIDE"] = "1"

    if SERVER_LOG_FILE.exists():
        try:
            SERVER_LOG_FILE.unlink()
        except Exception:
            pass

    log_handle = open(SERVER_LOG_FILE, "a", encoding="utf-8")
    cmd = [
        str(PYTHON_EXE),
        "-u",
        "-m",
        "streamlit",
        "run",
        "src/aios_habit/workspace_chat_app.py",
        f"--server.port={PORT}",
        "--server.headless=true",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]
    log(f"Khoi dong Streamlit tai port {PORT}...")
    proc = subprocess.Popen(
        cmd,
        cwd=str(APP_DIR),
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
    )
    return proc


def kill_server(proc: subprocess.Popen) -> None:
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def run_browser_verification() -> dict[str, Any]:
    log("=== BAT DAU KIEM CHUNG TRINH DUYET THAT CHO DESKTOP-MEMORY-DRAFT-PERSIST-HOME ===")

    # 0. Ensure memory preference enabled
    set_workspace_memory_enabled_preference(True)

    # Clean up any leftover pending drafts file for clean benchmark
    pending_path = default_pending_drafts_path()
    if pending_path.exists():
        try:
            pending_path.unlink()
        except Exception:
            pass

    # Setup dedicated conversation
    nbs = load_active_notebooks()
    nb_id = nbs[0].id if nbs else "NB-DEFAULT"
    conv_id = f"CONV-MEM-{uuid.uuid4().hex[:6].upper()}"
    save_conversation(
        WorkspaceConversation(
            id=conv_id,
            notebook_id=nb_id,
            title="Kiem chung ban nhap ghi nho song sot dong phien",
            ai_mode="grounded",
        )
    )
    target_url = f"{URL}/?nb={nb_id}&conv={conv_id}"
    log(f"Cuoc hoi thoai kiem chung: {conv_id} tai notebook {nb_id}")

    proc = start_server()
    results: dict[str, Any] = {
        "server_started": False,
        "step1_draft_created": False,
        "step2_restored_after_restart": False,
        "step3_confirmed_and_persisted": False,
        "screenshots": {},
    }

    try:
        if not wait_for_server(URL, timeout_s=90.0):
            log("[FAIL] Khong the ket noi toi Streamlit server sau 90s")
            return results
        results["server_started"] = True
        log("[OK] Streamlit server da san sang.")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # --- PHIEN 1: Tao ban nhap cho ---
            log("--- [PHIEN 1] Tao ban nhap cho qua chat ---")
            context1 = browser.new_context(viewport={"width": 1400, "height": 900})
            page1 = context1.new_page()
            log(f"Dieu huong toi {target_url}...")
            page1.goto(target_url, wait_until="networkidle", timeout=60000)
            page1.wait_for_timeout(3000)

            composer_selector = f'[class*="st-key-wsc_question_input_{conv_id}"] textarea:visible'
            log(f"Cho khung soan thao cau hoi: {composer_selector}...")
            page1.wait_for_selector(composer_selector, timeout=30000)
            textarea = page1.locator(composer_selector).first
            textarea.click(force=True)

            cmd_text = "Hãy nhớ: Khi bảo dưỡng máy nén khí phải xả áp bình tích trước khi mở van"
            log(f"Nhap lenh: '{cmd_text}'...")
            textarea.type(cmd_text, delay=15)
            page1.wait_for_timeout(500)

            # Click send button
            log(f"Cho nut gui wsc_ask_{conv_id}...")
            send_btn = page1.locator(f'[class*="st-key-wsc_ask_{conv_id}"] button').first
            send_btn.wait_for(state="visible", timeout=15000)
            page1.wait_for_timeout(1000)
            log(f"Clicking send button: wsc_ask_{conv_id}...")
            send_btn.click(force=True)

            # Wait for confirm button to appear
            confirm_btn_selector = (
                '[class*="st-key-wsc_memory_confirm"] button, '
                'button:has-text("Xác nhận")'
            )
            log("Cho khung xac nhan ban nhap xuat hien tren giao dien...")
            page1.wait_for_selector(confirm_btn_selector, timeout=30000)
            page1.wait_for_timeout(1000)

            # Screenshot 1
            ss1_path = OUT_DIR / "anh-desktop-memory-draft-persist-01-draft-created.png"
            page1.screenshot(path=str(ss1_path), full_page=True)
            results["screenshots"]["ss1"] = {
                "path": str(ss1_path),
                "sha256": sha256_file(ss1_path),
            }
            log(f"[OK] Da chup anh 1: {ss1_path.name}")

            # Verify disk has pending draft
            assert pending_path.exists(), "pending_drafts.json khong ton tai sau khi gui lenh"
            drafts = load_pending_drafts(pending_path)
            assert drafts.get("command") is not None
            assert "máy nén khí" in drafts["command"]["statement"]
            results["step1_draft_created"] = True
            log("[OK] Buoc 1 DAT: Ban nhap da ton tai tren dia va hien tren khung cho.")

            # Close context 1 (Simulate closing browser tab/session)
            log("--- Dong phien trinh duyet 1 (simulating session close) ---")
            context1.close()
            time.sleep(2.0)

            # --- PHIEN 2: Mo phien moi, kiem tra ban nhap con nguyen ---
            log("--- [PHIEN 2] Mo phien trinh duyet moi (hoan toan doc lap, session moi) ---")
            context2 = browser.new_context(viewport={"width": 1400, "height": 900})
            page2 = context2.new_page()
            log(f"Dieu huong toi {target_url} trong phien moi...")
            page2.goto(target_url, wait_until="networkidle", timeout=60000)
            page2.wait_for_timeout(3000)

            # Verify confirm button and text are STILL PRESENT without user re-typing
            log("Kiem tra khung ban nhap cho co duoc khoi phuc nguyen ven...")
            page2.wait_for_selector(confirm_btn_selector, timeout=30000)
            page2.get_by_text("Khi bảo dưỡng máy nén khí").first.wait_for(
                state="visible", timeout=15000
            )
            page2.wait_for_timeout(1000)

            # Screenshot 2
            ss2_path = OUT_DIR / "anh-desktop-memory-draft-persist-02-restored-after-browser-restart.png"
            page2.screenshot(path=str(ss2_path), full_page=True)
            results["screenshots"]["ss2"] = {
                "path": str(ss2_path),
                "sha256": sha256_file(ss2_path),
            }
            log(f"[OK] Da chup anh 2: {ss2_path.name}")
            results["step2_restored_after_restart"] = True
            log("[OK] Buoc 2 DAT: Ban nhap con nguyen ven sau khi khoi dong lai phien trinh duyet!")

            # --- PHIEN 2: Bam "Xac nhan" ---
            log("--- Bam nut 'Xac nhan' trong phien 2 ---")
            confirm_btn = page2.locator(confirm_btn_selector).first
            confirm_btn.click(force=True)
            page2.wait_for_timeout(3000)

            # Verify confirm button is now gone
            page2.wait_for_selector(
                '[class*="st-key-wsc_memory_confirm"] button',
                state="detached",
                timeout=20000,
            )
            page2.wait_for_timeout(1000)

            # Screenshot 3
            ss3_path = OUT_DIR / "anh-desktop-memory-draft-persist-03-confirmed-and-disappeared.png"
            page2.screenshot(path=str(ss3_path), full_page=True)
            results["screenshots"]["ss3"] = {
                "path": str(ss3_path),
                "sha256": sha256_file(ss3_path),
            }
            log(f"[OK] Da chup anh 3: {ss3_path.name}")

            # Verify disk state
            # 1. pending_drafts.json is cleared/deleted
            post_drafts = load_pending_drafts(pending_path)
            assert post_drafts.get("command") is None, (
                "Ban nhap van con trong pending_drafts.json sau khi xac nhan"
            )

            # 2. decision is in memory_decisions.jsonl
            dec_path = default_decisions_path()
            assert dec_path.exists(), "memory_decisions.jsonl chua ton tai"
            dec_lines = [
                line for line in dec_path.read_text(encoding="utf-8").splitlines() if line.strip()
            ]
            dec_records = [json.loads(line) for line in dec_lines]
            matched_dec = next(
                (r for r in dec_records if "máy nén khí" in str(r.get("statement", ""))), None
            )
            assert matched_dec is not None, (
                "Khong tim thay quyet dinh da xac nhan trong memory_decisions.jsonl"
            )
            assert matched_dec["action"] == "confirm"
            log(
                f"[OK] Da tim thay quyet dinh trong memory_decisions.jsonl: "
                f"decision_id={matched_dec['decision_id']}"
            )

            results["step3_confirmed_and_persisted"] = True
            results["decision"] = matched_dec
            log(
                "[OK] Buoc 3 DAT: Ban nhap bien mat, tep pending duoc don sach, "
                "quyet dinh da vao memory_decisions.jsonl!"
            )

            context2.close()
            browser.close()

    finally:
        log("Dung Streamlit server...")
        kill_server(proc)

    log("=== HOAN TAT KIEM CHUNG TRINH DUYET THAT ===")
    return results


if __name__ == "__main__":
    res = run_browser_verification()
    log("\nKET QUA:")
    log(json.dumps(res, indent=2, ensure_ascii=False))
