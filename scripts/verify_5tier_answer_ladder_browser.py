# -*- coding: utf-8 -*-
"""Browser verification for ticket DESKTOP-SELF-LEARN-5TIER-ANSWER-LADDER.

Automated verification with real Playwright Chromium:
1. Seeds two test conversations under an active notebook:
   - Tier 3 (Ambiguous): "LSU bị lỗi" -> Suggestions + provisional answer + Tier 5 actions.
   - Tier 4 (Missing evidence): "Mã lỗi E-999 trên máy hàn laser là gì?" -> Fixed warning banner + inferred technical reasoning + Tier 5 actions.
2. Starts Streamlit workspace chat server on a dynamic port.
3. Opens Chromium browser via Playwright.
4. Navigates to Tier 3 conversation (Page 1):
   - Verifies suggestion buttons and provisional answer rendered in UI.
   - Captures screenshot: ui-ladder-tier3-suggestions.png.
5. Navigates to Tier 4 conversation (Page 2):
   - Verifies mandatory fixed warning banner rendered prominently in UI.
   - Verifies Tier 5 action buttons ("🎓 Dạy AIOS điều này", "👨‍💼 Hỏi chuyên gia miền", "🌐 Hỏi AI ngoài").
   - Clicks "👨‍💼 Hỏi chuyên gia miền" to test live button interaction.
   - Captures screenshot: ui-ladder-tier4-inferred-warning.png.
6. Shuts down server and outputs verification results.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import uuid

# Ensure UTF-8 output on Windows console
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from playwright.sync_api import sync_playwright

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR / "src"))

from aios_habit.final_answer_composer import (
    TIER_3_AMBIGUOUS,
    TIER_4_INFERRED,
    TIER_4_WARNING_BANNER,
    deliver_5tier_ladder_answer,
)
from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import load_active_notebooks, save_conversation

def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

PORT = find_free_port()
URL = f"http://localhost:{PORT}"

OUT_DIR_DESKTOP = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")
OUT_DIR_DESKTOP.mkdir(parents=True, exist_ok=True)

LOCAL_DOC_DIR = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
LOCAL_DOC_DIR.mkdir(parents=True, exist_ok=True)

ARTIFACT_DIR = Path(r"C:\Users\Admin\.gemini\antigravity\brain\8dd7c067-d0c1-41de-b809-415e7790b2ed")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

SERVER_LOG = LOCAL_DOC_DIR / "server_5tier_ladder_verify.log"
if SERVER_LOG.exists():
    try:
        SERVER_LOG.unlink()
    except Exception:
        pass


def main() -> int:
    print("=" * 70)
    print("STARTING 5-TIER ANSWER LADDER BROWSER VERIFICATION")
    print("=" * 70)

    # 1. Resolve notebook and seed test conversations
    nbs = load_active_notebooks()
    nb_id = nbs[0].id if nbs else "NB-DEFAULT"

    conv_tier3_id = f"CONV-T3-{uuid.uuid4().hex[:6].upper()}"
    save_conversation(
        WorkspaceConversation(
            id=conv_tier3_id,
            notebook_id=nb_id,
            title="Kiểm thử Tier 3 - Gợi ý diễn đạt lại",
            ai_mode="grounded",
        )
    )

    t3_question = "LSU bị lỗi"
    print(f"[SEED] Delivering Tier 3 answer for '{t3_question}' in {conv_tier3_id}...")
    ok3, msg3, badge3, err3 = deliver_5tier_ladder_answer(
        question=t3_question,
        conversation_id=conv_tier3_id,
        notebook_id=nb_id,
        user_raw_input=t3_question,
    )
    assert ok3 is True, f"Failed to deliver Tier 3 answer: {err3}"
    assert badge3["tier"] == TIER_3_AMBIGUOUS

    conv_tier4_id = f"CONV-T4-{uuid.uuid4().hex[:6].upper()}"
    save_conversation(
        WorkspaceConversation(
            id=conv_tier4_id,
            notebook_id=nb_id,
            title="Kiểm thử Tier 4 - Cảnh báo suy luận AI",
            ai_mode="grounded",
        )
    )

    t4_question = "Mã lỗi E-999 trên máy hàn laser là gì?"
    print(f"[SEED] Delivering Tier 4 answer for '{t4_question}' in {conv_tier4_id}...")
    ok4, msg4, badge4, err4 = deliver_5tier_ladder_answer(
        question=t4_question,
        conversation_id=conv_tier4_id,
        notebook_id=nb_id,
        user_raw_input=t4_question,
    )
    assert ok4 is True, f"Failed to deliver Tier 4 answer: {err4}"
    assert badge4["tier"] == TIER_4_INFERRED
    assert badge4["has_warning_banner"] is True

    # 2. Start Streamlit server
    env = os.environ.copy()
    env["PYTHONPATH"] = str(APP_DIR / "src")
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    env["AIOS_RETRIEVAL_DEVICE"] = "cpu"
    env["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
    env["AIOS_RAG_V2_NUMPY_SCORING"] = "1"
    env["AIOS_AI_BACKEND"] = "local"
    env["AIOS_FEATURE_CHAT_ACTION"] = "1"
    env["AIOS_DOMAIN_ROUTING_ENABLED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"

    print(f"[SERVER] Starting Streamlit on port {PORT}...")
    log_h = open(SERVER_LOG, "a", encoding="utf-8")
    cmd = [
        str(APP_DIR / ".venv" / "Scripts" / "python.exe"),
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
    proc = subprocess.Popen(cmd, cwd=APP_DIR, env=env, stdout=log_h, stderr=subprocess.STDOUT)

    try:
        deadline = time.time() + 60
        server_ready = False
        while time.time() < deadline:
            try:
                req = urllib.request.Request(f"http://localhost:{PORT}/_stcore/health")
                with urllib.request.urlopen(req, timeout=2) as r:
                    if r.status == 200:
                        server_ready = True
                        break
            except Exception:
                pass
            time.sleep(1)

        if not server_ready:
            print("[ERROR] Streamlit server did not become healthy within 60s.")
            return 1

        print(f"[SERVER] Server is UP at {URL}")
        time.sleep(2)

        # 3. Launch Playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # --- VERIFY TIER 3 CONVERSATION (PAGE 1) ---
            page1 = browser.new_page(viewport={"width": 1440, "height": 960})
            tier3_url = f"{URL}/?nb={nb_id}&conv={conv_tier3_id}"
            print(f"[BROWSER] Navigating to Tier 3 conversation: {tier3_url}")
            page1.goto(tier3_url, wait_until="domcontentloaded", timeout=60000)
            page1.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)
            page1.wait_for_timeout(3000)

            print("[BROWSER] Checking Tier 3 elements...")
            clarify_header = page1.locator(':has-text("Làm rõ ý định câu hỏi")')
            assert clarify_header.count() >= 1, "Missing 'Làm rõ ý định câu hỏi' header"
            print("[BROWSER] Found 'Làm rõ ý định câu hỏi' section.")

            suggest_btns = page1.locator('button:has-text("👉")')
            btn_count = suggest_btns.count()
            print(f"[BROWSER] Found {btn_count} rephrasing suggestion buttons.")
            assert btn_count >= 2, f"Expected at least 2 suggestion buttons, found {btn_count}"

            teach_btn = page1.locator('button:has-text("🎓 Dạy AIOS điều này")').first
            expert_btn = page1.locator('button:has-text("👨‍💼 Hỏi chuyên gia miền")').first
            extai_btn = page1.locator('button:has-text("🌐 Hỏi AI ngoài")').first
            assert teach_btn.is_visible()
            assert expert_btn.is_visible()
            assert extai_btn.is_visible()
            print("[BROWSER] Found all 3 Tier 5 action buttons on Tier 3 message.")

            # Capture screenshot 1: Tier 3 suggestions
            shot_tier3_desktop = OUT_DIR_DESKTOP / "ui-ladder-tier3-suggestions.png"
            shot_tier3_local = LOCAL_DOC_DIR / "ui-ladder-tier3-suggestions.png"
            shot_tier3_artifact = ARTIFACT_DIR / "ui-ladder-tier3-suggestions.png"

            print(f"[SCREENSHOT 1] Capturing Tier 3 suggestions to {shot_tier3_desktop}...")
            page1.screenshot(path=str(shot_tier3_desktop), full_page=True)
            page1.screenshot(path=str(shot_tier3_local), full_page=True)
            page1.screenshot(path=str(shot_tier3_artifact), full_page=True)
            print(f"[SCREENSHOT 1] Saved (size: {shot_tier3_desktop.stat().st_size} bytes)")
            page1.close()

            # --- VERIFY TIER 4 CONVERSATION (PAGE 2) ---
            page2 = browser.new_page(viewport={"width": 1440, "height": 960})
            tier4_url = f"{URL}/?nb={nb_id}&conv={conv_tier4_id}"
            print(f"[BROWSER] Navigating to Tier 4 conversation: {tier4_url}")
            page2.goto(tier4_url, wait_until="domcontentloaded", timeout=60000)
            page2.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)
            page2.wait_for_timeout(3000)

            print("[BROWSER] Checking Tier 4 elements...")
            warning_banner = page2.locator(':has-text("CÂU TRẢ LỜI ĐƯỢC SUY LUẬN TỰ ĐỘNG BỞI AI")')
            assert warning_banner.count() >= 1, "Missing mandatory fixed warning banner"
            print("[BROWSER] Found mandatory fixed warning banner.")

            inferred_sec = page2.locator(':has-text("Nhận định & Suy luận")')
            actions_sec = page2.locator(':has-text("Hành động tiếp nối")')
            assert inferred_sec.count() >= 1, "Missing 'Nhận định & Suy luận' section"
            assert actions_sec.count() >= 1, "Missing 'Hành động tiếp nối' section"
            print("[BROWSER] Found inferred reasoning sections.")

            teach_btn_t4 = page2.locator('button:has-text("🎓 Dạy AIOS điều này")').first
            expert_btn_t4 = page2.locator('button:has-text("👨‍💼 Hỏi chuyên gia miền")').first
            extai_btn_t4 = page2.locator('button:has-text("🌐 Hỏi AI ngoài")').first
            assert teach_btn_t4.is_visible()
            assert expert_btn_t4.is_visible()
            assert extai_btn_t4.is_visible()
            print("[BROWSER] Verified all 3 Tier 5 action buttons on Tier 4 message.")

            # Capture screenshot 2: Tier 4 inferred warning
            shot_tier4_desktop = OUT_DIR_DESKTOP / "ui-ladder-tier4-inferred-warning.png"
            shot_tier4_local = LOCAL_DOC_DIR / "ui-ladder-tier4-inferred-warning.png"
            shot_tier4_artifact = ARTIFACT_DIR / "ui-ladder-tier4-inferred-warning.png"

            print(f"[SCREENSHOT 2] Capturing Tier 4 warning banner to {shot_tier4_desktop}...")
            page2.screenshot(path=str(shot_tier4_desktop), full_page=True)
            page2.screenshot(path=str(shot_tier4_local), full_page=True)
            page2.screenshot(path=str(shot_tier4_artifact), full_page=True)
            print(f"[SCREENSHOT 2] Saved (size: {shot_tier4_desktop.stat().st_size} bytes)")

            # Test live interaction: Click "👨‍💼 Hỏi chuyên gia miền"
            print("[BROWSER] Clicking '👨‍💼 Hỏi chuyên gia miền' button...")
            expert_btn_t4.click()
            page2.wait_for_timeout(2000)

            # Verify expert queue file was created/updated
            expert_file = APP_DIR / "local_cases" / "expert_inquiries" / "expert_queue.jsonl"
            assert expert_file.exists(), f"Expected expert queue file at {expert_file}"
            expert_lines = expert_file.read_text(encoding="utf-8").strip().splitlines()
            assert len(expert_lines) >= 1
            last_record = json.loads(expert_lines[-1])
            assert last_record["conversation_id"] == conv_tier4_id
            print(f"[VERIFIED] Expert queue record persisted: {last_record}")

            page2.close()
            browser.close()

    finally:
        print("[SHUTDOWN] Terminating Streamlit server process...")
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        try:
            log_h.close()
        except Exception:
            pass

    print("=" * 70)
    print("BROWSER VERIFICATION COMPLETED SUCCESSFULLY (100% PASS)")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
