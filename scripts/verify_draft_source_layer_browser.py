# -*- coding: utf-8 -*-
"""Browser verification for ticket DESKTOP-SELF-LEARN-DRAFT-SOURCE-LAYER.

Automated verification with real Playwright Chromium:
1. Seeds test conversation under an active notebook with a question matching draft sources:
   - "LSU Beam SettingFile Jig 1002" -> Retrieves from 54 ChatGPT draft files in parallel.
   - Embeds mandatory label "[Bản thảo - chưa kiểm chứng qua chuyên gia]".
2. Starts Streamlit workspace chat server on a dynamic port.
3. Opens Chromium browser via Playwright.
4. Verifies the mandatory label and draft content are rendered in UI.
5. Captures screenshot: ui-draft-source-parallel-answer.png.
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

from aios_habit.draft_source_layer import MANDATORY_DRAFT_LABEL
from aios_habit.final_answer_composer import deliver_5tier_ladder_answer
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

ARTIFACT_DIR = Path(r"C:\Users\Admin\.gemini\antigravity\brain\e75f307d-e11b-49c3-b44e-731efb35d8a1")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

SERVER_LOG = LOCAL_DOC_DIR / "server_draft_source_verify.log"
if SERVER_LOG.exists():
    try:
        SERVER_LOG.unlink()
    except Exception:
        pass


def main() -> int:
    print("=" * 70)
    print("STARTING DRAFT SOURCE LAYER BROWSER VERIFICATION")
    print("=" * 70)

    # 1. Resolve notebook and seed test conversation
    nbs = load_active_notebooks()
    nb_id = nbs[0].id if nbs else "NB-DEFAULT"

    conv_id = f"CONV-DRAFT-{uuid.uuid4().hex[:6].upper()}"
    save_conversation(
        WorkspaceConversation(
            id=conv_id,
            notebook_id=nb_id,
            title="Kiểm thử Tầng nguồn bản thảo song song",
            ai_mode="grounded",
        )
    )

    question = "LSU Beam SettingFile Jig 1002 và NanoScan"
    print(f"[SEED] Delivering parallel draft answer for '{question}' in {conv_id}...")
    ok, msg, badge, err = deliver_5tier_ladder_answer(
        question=question,
        conversation_id=conv_id,
        notebook_id=nb_id,
        user_raw_input=question,
    )
    assert ok is True, f"Failed to deliver draft answer: {err}"
    assert badge is not None
    assert badge["has_draft_label"] is True, "Badge missing has_draft_label=True"
    print(f"[SEED] Seeded successfully. Draft source: {badge.get('draft_source')}")

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

        # 3. Launch Playwright Chromium
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 960})
            conv_url = f"{URL}/?nb={nb_id}&conv={conv_id}"
            print(f"[BROWSER] Navigating to draft conversation: {conv_url}")
            page.goto(conv_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)
            page.wait_for_timeout(3000)

            print("[BROWSER] Checking draft answer elements in UI...")
            # Kiểm tra nhãn bản thảo bắt buộc hiển thị rõ trên màn hình
            label_locator = page.locator(f':has-text("{MANDATORY_DRAFT_LABEL}")')
            assert label_locator.count() >= 1, f"Missing mandatory label '{MANDATORY_DRAFT_LABEL}' in UI"
            print(f"[BROWSER] Confirmed mandatory draft label '{MANDATORY_DRAFT_LABEL}' is visible!")

            # Kiểm tra các nút hành động tiếp nối
            teach_btn = page.locator('button:has-text("🎓 Dạy AIOS điều này")').first
            expert_btn = page.locator('button:has-text("👨‍💼 Hỏi chuyên gia miền")').first
            assert teach_btn.is_visible()
            assert expert_btn.is_visible()
            print("[BROWSER] Confirmed actionable follow-up buttons are visible.")

            # Chụp ảnh bằng chứng
            shot_desktop = OUT_DIR_DESKTOP / "ui-draft-source-parallel-answer.png"
            shot_local = LOCAL_DOC_DIR / "ui-draft-source-parallel-answer.png"
            shot_artifact = ARTIFACT_DIR / "ui-draft-source-parallel-answer.png"

            print(f"[SCREENSHOT] Capturing draft answer screenshot to {shot_desktop}...")
            page.screenshot(path=str(shot_desktop), full_page=True)
            page.screenshot(path=str(shot_local), full_page=True)
            page.screenshot(path=str(shot_artifact), full_page=True)
            print(f"[SCREENSHOT] Saved (size: {shot_desktop.stat().st_size} bytes)")

            page.close()
            browser.close()

    finally:
        print("[CLEANUP] Stopping Streamlit server...")
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
        print("[CLEANUP] Streamlit server stopped.")

    print("=" * 70)
    print("BROWSER VERIFICATION COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
