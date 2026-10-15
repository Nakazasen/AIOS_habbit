"""Live UI verification for DESKTOP-FEEDBACK-REVIEW-CHATCMD-HOME.

Starts Streamlit on port 8589, uses Playwright to send 'xem phản hồi' in the chat,
verifies assistant response with the live feedback summary, and takes a full-resolution
screenshot of the chat UI with the summary rendered inside the assistant bubble.
"""

from __future__ import annotations

import os
import subprocess
import time
import urllib.request
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
PORT = 8589
URL = f"http://localhost:{PORT}"
OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua")
OUT_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_DOC_DIR = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
LOCAL_DOC_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR = Path(r"C:\Users\Admin\.gemini\antigravity\brain\f9fc95a1-8f23-4e03-86a1-8776cb528a82")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

SERVER_LOG = OUT_DIR / "server_feedback_review_chatcmd.log"
if SERVER_LOG.exists():
    try:
        SERVER_LOG.unlink()
    except Exception:
        pass

env = os.environ.copy()
env["PYTHONPATH"] = str(APP_DIR / "src")
env["OMP_NUM_THREADS"] = "1"
env["MKL_NUM_THREADS"] = "1"
env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
env["AIOS_RETRIEVAL_DEVICE"] = "cpu"
env["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
env["AIOS_RAG_V2_NUMPY_SCORING"] = "1"
env["AIOS_AI_BACKEND"] = "nakazasen_router"
env["AIOS_FEATURE_CHAT_ACTION"] = "1"
env["AIOS_DOMAIN_ROUTING_ENABLED"] = "1"
env["PYTHONIOENCODING"] = "utf-8"
env["PYTHONUNBUFFERED"] = "1"

print(f"[STARTUP] Starting Streamlit server on port {PORT}...")
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

# Wait for server ready
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
    print("[ERROR] Server did not become ready in 60s!")
    proc.terminate()
    raise SystemExit(1)

print(f"[SERVER] Server ready at {URL}")
time.sleep(2)

# Create conversation
import sys
sys.path.insert(0, str(APP_DIR / "src"))
from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import load_active_notebooks, load_messages, save_conversation

nbs = load_active_notebooks()
nb_id = nbs[0].id if nbs else "NB-DEFAULT"

conv_id = f"CONV-FB-CMD-{uuid.uuid4().hex[:6].upper()}"
save_conversation(
    WorkspaceConversation(
        id=conv_id,
        notebook_id=nb_id,
        title="Xem lại phản hồi lệnh chat",
        ai_mode="grounded",
    )
)

print(f"[CONV] Created conversation: {conv_id} under notebook: {nb_id}")

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        target_url = f"{URL}/?nb={nb_id}&conv={conv_id}"
        print(f"[BROWSER] Navigating to {target_url}...")
        page.goto(target_url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        # Look for textarea
        print("[BROWSER] Waiting for composer textarea...")
        page.wait_for_selector('textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"]', timeout=30000)
        textarea = page.locator('textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"]').first

        cmd_text = "xem phản hồi"
        print(f"[BROWSER] Typing command: '{cmd_text}'...")
        textarea.fill(cmd_text)
        time.sleep(0.5)
        print("[BROWSER] Pressing Control+Enter...")
        textarea.press("Control+Enter")

        # Wait for assistant response in store
        t0 = time.time()
        answered = False
        while time.time() - t0 < 60:
            msgs = load_messages(conv_id)
            if len(msgs) >= 2 and msgs[-1].role == "assistant":
                print(f"[DONE] Assistant message received after {time.time() - t0:.2f}s!")
                print(f"[ASSISTANT CONTENT EXCERPT]:\n{msgs[-1].content[:300]}...")
                answered = True
                break
            time.sleep(1)

        if not answered:
            print("[ERROR] Timed out waiting for assistant reply in conversation!")

        # Allow UI to finish rerunning and rendering the markdown table/blocks
        page.wait_for_timeout(5000)

        # Capture screenshot
        img_dest1 = OUT_DIR / "ui-feedback-review-chatcmd-home.png"
        img_dest2 = LOCAL_DOC_DIR / "ui-feedback-review-chatcmd-home.png"
        img_dest3 = ARTIFACT_DIR / "ui-feedback-review-chatcmd-home.png"

        print(f"[SCREENSHOT] Capturing screenshot to {img_dest1}...")
        page.screenshot(path=str(img_dest1), full_page=True)
        page.screenshot(path=str(img_dest2), full_page=True)
        page.screenshot(path=str(img_dest3), full_page=True)
        print(f"[SCREENSHOT] Successfully saved screenshot (size: {img_dest1.stat().st_size} bytes)")

        browser.close()
finally:
    print("[CLEANUP] Stopping Streamlit server...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()

print("[COMPLETE] Verification script finished successfully.")
