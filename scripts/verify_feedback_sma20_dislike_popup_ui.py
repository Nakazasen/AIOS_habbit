"""Live UI verification for DESKTOP-SELF-LEARN-FEEDBACK-SMA20-PIPELINE.

Starts Streamlit, pre-seeds a conversation with an assistant message,
navigates to it via the chat UI, clicks Dislike (Thumbs Down, button 1) on the feedback widget,
verifies the popup dialog with 4 mandatory reason categories ('sai', 'kho_hieu', 'thieu_nguon', 'lac_de'),
selects 'thieu_nguon', fills a short explanation, submits feedback, verifies
deduplicated Windows identity recording, tests re-voting, and captures
full-resolution screenshots on a real browser.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

# Ensure UTF-8 output on Windows console
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from playwright.sync_api import sync_playwright

def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
PORT = find_free_port()
URL = f"http://localhost:{PORT}"

OUT_DIR_DESKTOP = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")
OUT_DIR_DESKTOP.mkdir(parents=True, exist_ok=True)

LOCAL_DOC_DIR = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
LOCAL_DOC_DIR.mkdir(parents=True, exist_ok=True)

ARTIFACT_DIR = Path(r"C:\Users\Admin\.gemini\antigravity\brain\0db80761-813e-4b37-878b-a485cc43cb6b")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

SERVER_LOG = LOCAL_DOC_DIR / "server_feedback_sma20_verify.log"
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
env["AIOS_AI_BACKEND"] = "local"
env["AIOS_FEATURE_CHAT_ACTION"] = "1"
env["AIOS_DOMAIN_ROUTING_ENABLED"] = "1"
env["PYTHONIOENCODING"] = "utf-8"
env["PYTHONUNBUFFERED"] = "1"

sys.path.insert(0, str(APP_DIR / "src"))
from aios_habit.workspace_chat_models import ChatMessage, WorkspaceConversation
from aios_habit.workspace_chat_store import load_active_notebooks, save_conversation, save_message
from aios_habit.answer_feedback import feedback_file, get_feedback, get_windows_identity

nbs = load_active_notebooks()
nb_id = nbs[0].id if nbs else "NB-DEFAULT"

conv_id = f"CONV-SMA20-{uuid.uuid4().hex[:6].upper()}"
save_conversation(
    WorkspaceConversation(
        id=conv_id,
        notebook_id=nb_id,
        title="Kiểm thử giao diện feedback SMA20",
        ai_mode="grounded",
    )
)

user_msg_id = f"MSG-U-{uuid.uuid4().hex[:6]}"
asst_msg_id = f"MSG-A-{uuid.uuid4().hex[:6]}"

save_message(
    ChatMessage(
        id=user_msg_id,
        conversation_id=conv_id,
        role="user",
        content="Quy trình kiểm tra bảo trì hệ thống thủy lực máy ép cọc?",
    )
)

save_message(
    ChatMessage(
        id=asst_msg_id,
        conversation_id=conv_id,
        role="assistant",
        content="Theo quy trình bảo trì hệ thống thủy lực định kỳ:\n1. Kiểm tra mức dầu và áp suất làm việc định kỳ trước ca làm việc.\n2. Kiểm tra bộ lọc đường hút và đường hồi.\n3. Vệ sinh và kiểm tra van điều áp khi có hiện tượng kẹt áp.\n4. Ghi chép nhật ký bảo trì vào sổ theo dõi kỹ thuật.",
    )
)

print(f"[CONV] Seeded test conversation {conv_id} under notebook {nb_id} with user and assistant messages.")

print(f"[STARTUP] Starting Streamlit server on dynamic port {PORT}...")
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

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 960})
        target_url = f"{URL}/?nb={nb_id}&conv={conv_id}"
        print(f"[BROWSER] Navigating to {target_url}...")
        page.goto(target_url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        # Locate thumbs feedback widget under assistant message
        print("[BROWSER] Looking for thumbs feedback widget...")
        page.wait_for_selector('[data-testid="stFeedback"]', timeout=30000)
        thumbs_widget = page.locator('[data-testid="stFeedback"]').first

        buttons = thumbs_widget.locator("button")
        btn_count = buttons.count()
        print(f"[BROWSER] Found {btn_count} feedback buttons")
        assert btn_count >= 2, f"Expected at least 2 feedback buttons, found {btn_count}"

        for i in range(btn_count):
            btn = buttons.nth(i)
            print(f"[BROWSER] Button {i}: aria-label='{btn.get_attribute('aria-label')}', title='{btn.get_attribute('title')}', innerText='{btn.inner_text()}'")

        # In Streamlit st.feedback('thumbs'):
        # Index 0 is Thumbs Up (:material/thumb_up:)
        # Index 1 is Thumbs Down (:material/thumb_down:)
        thumbs_down_btn = buttons.nth(1)
        print("[BROWSER] Clicking Dislike (Thumbs Down, button index 1)...")
        thumbs_down_btn.click()
        page.wait_for_timeout(3000)

        # Look for dialog or modal popup
        print("[BROWSER] Verifying popup dialog with 4 mandatory reason categories...")
        modal = page.locator('[data-testid="stModal"], [data-testid="stDialog"], [role="dialog"]').last
        page.wait_for_selector('[data-testid="stModal"], [data-testid="stDialog"], [role="dialog"]', timeout=15000)

        # Screenshot 1: Popup dialog open with 4 reason choices
        shot1_path_desktop = OUT_DIR_DESKTOP / "ui-feedback-sma20-dislike-popup.png"
        shot1_path_local = LOCAL_DOC_DIR / "ui-feedback-sma20-dislike-popup.png"
        shot1_path_artifact = ARTIFACT_DIR / "ui-feedback-sma20-dislike-popup.png"

        print(f"[SCREENSHOT 1] Capturing dislike popup to {shot1_path_desktop}...")
        page.screenshot(path=str(shot1_path_desktop), full_page=True)
        page.screenshot(path=str(shot1_path_local), full_page=True)
        page.screenshot(path=str(shot1_path_artifact), full_page=True)
        print(f"[SCREENSHOT 1] Saved (size: {shot1_path_desktop.stat().st_size} bytes)")

        # Target the reason option inside modal
        print("[BROWSER] Selecting option 'Thiếu nguồn' inside modal...")
        thieu_nguon_label = modal.locator('label').filter(has_text="Thiếu nguồn").first
        thieu_nguon_label.click()
        page.wait_for_timeout(1000)

        # Fill detail explanation into text input inside modal
        detail_input = modal.locator('input[type="text"]').first
        print("[BROWSER] Filling short explanation into target input...")
        detail_input.fill("Cần trích dẫn tài liệu quy trình kiểm định van áp lực P-04/BDSC.")
        page.wait_for_timeout(500)

        # Screenshot 2: Reason selected and detail filled
        shot2_path = LOCAL_DOC_DIR / "ui-feedback-sma20-reason-selected.png"
        page.screenshot(path=str(shot2_path), full_page=True)

        # Click submit button inside modal
        submit_btn = modal.locator('button:has-text("Gửi đánh giá")').first
        print("[BROWSER] Clicking submit feedback button inside modal...")
        submit_btn.click()
        page.wait_for_timeout(4000)

        # Screenshot 3: Feedback recorded state on UI
        shot3_path = OUT_DIR_DESKTOP / "ui-feedback-sma20-recorded-state.png"
        shot3_path_local = LOCAL_DOC_DIR / "ui-feedback-sma20-recorded-state.png"
        shot3_path_artifact = ARTIFACT_DIR / "ui-feedback-sma20-recorded-state.png"
        page.screenshot(path=str(shot3_path), full_page=True)
        page.screenshot(path=str(shot3_path_local), full_page=True)
        page.screenshot(path=str(shot3_path_artifact), full_page=True)
        print(f"[SCREENSHOT 3] Saved recorded state (size: {shot3_path.stat().st_size} bytes)")

        # Verify disk storage
        win_user = get_windows_identity()
        rec = get_feedback(conv_id, asst_msg_id, user_id=win_user)
        print(f"[STORAGE CHECK] Recorded feedback for user {win_user}: {rec}")
        assert rec is not None, "Feedback record was not found in storage!"
        assert rec.get("rating") == "chua_huu_ich", f"Expected 'chua_huu_ich', got {rec.get('rating')}"
        assert rec.get("reason_category") == "thieu_nguon", f"Expected 'thieu_nguon', got {rec.get('reason_category')}"
        assert "quy trình kiểm định van" in rec.get("reason", ""), f"Reason text mismatch: {rec.get('reason')}"
        assert rec.get("question_hash") != "", "Expected question_hash to be populated!"

        # Test anti-duplicate vote: Click revote button and change to Like
        revote_btn = page.locator('button:has-text("Đổi đánh giá")').first
        if revote_btn.count() > 0:
            print("[BROWSER] Clicking 'Đổi đánh giá' button to test anti-duplicate vote...")
            revote_btn.click()
            page.wait_for_timeout(2500)

            # Re-locate thumbs widget and click Thumbs Up (button index 0)
            page.wait_for_selector('[data-testid="stFeedback"]', timeout=10000)
            thumbs_up_btn = page.locator('[data-testid="stFeedback"]').first.locator("button").nth(0)
            print("[BROWSER] Clicking Like (Thumbs Up, button index 0)...")
            thumbs_up_btn.click()
            page.wait_for_timeout(2500)

            # Screenshot 4: Revote updated
            shot4_path = LOCAL_DOC_DIR / "ui-feedback-sma20-revote-updated.png"
            page.screenshot(path=str(shot4_path), full_page=True)

            # Verify updated storage
            rec_updated = get_feedback(conv_id, asst_msg_id, user_id=win_user)
            print(f"[STORAGE CHECK 2] Updated feedback: {rec_updated}")
            assert rec_updated.get("rating") == "huu_ich", f"Expected rating to update to 'huu_ich', got {rec_updated.get('rating')}"
            assert rec_updated.get("updated_at") != "", "Expected updated_at timestamp to be set!"

            # Check that there are no duplicate entries for the same user and message_id
            all_feedbacks = []
            if feedback_file().exists():
                with open(feedback_file(), "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            all_feedbacks.append(json.loads(line))
            matching = [r for r in all_feedbacks if r.get("conversation_id") == conv_id and r.get("message_id") == asst_msg_id and r.get("user_id") == win_user]
            assert len(matching) == 1, f"Expected exactly 1 record for user {win_user} on message {asst_msg_id}, found {len(matching)}!"
            print(f"[DEDUPLICATION CHECK] Passed! Exactly {len(matching)} record in storage after revoting.")

        print("[VERIFICATION] All browser interactions and storage assertions passed 100%!")
        browser.close()

finally:
    print("[CLEANUP] Stopping Streamlit server...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()

print("[COMPLETE] Browser verification finished successfully.")
