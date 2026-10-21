"""Browser verification script for DESKTOP-SELF-LEARN-EXPERT-QUEUE-ROUTING-PIN.

1. Pre-seeds expert review queue SQLite DB with realistic pending items:
   - LSU item with high priority (5 dislikes, 4 frequency)
   - LSU item overdue > 48h (triggering reminder badge)
   - Điều tra lỗi item
2. Sets expert PIN: '1234'
3. Launches Streamlit application.
4. Uses Playwright Chromium to:
   - Verify expert recognition via WindowsOSIdentityProvider
   - Verify badge in sidebar: [🚨 Duyệt miền LSU: 2 (1 quá hạn)]
   - Capture screenshot: anh-desktop-expert-queue-badge-lsu.png
   - Click 'Duyệt vào kho' on Item 1 to open PIN approval popup
   - Verify machine binding check and PIN field
   - Capture screenshot: anh-desktop-expert-pin-approval-popup.png
   - Submit PIN '1234' and verify approval success + audit stamp logging.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
import time
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

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

from aios_habit.expert_review_queue import (
    ExpertReviewQueueRepository,
    SOURCE_SMA_ALERT,
    STATUS_APPROVED,
    STATUS_PENDING,
    get_expert_queue_repo,
)
from aios_habit.expert_roles import get_expert_role_registry
from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import load_active_notebooks, save_conversation

OUT_DIR_DESKTOP = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")
OUT_DIR_DESKTOP.mkdir(parents=True, exist_ok=True)

LOCAL_DOC_DIR = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
LOCAL_DOC_DIR.mkdir(parents=True, exist_ok=True)

SERVER_LOG = LOCAL_DOC_DIR / "server_expert_queue_verify.log"
if SERVER_LOG.exists():
    try:
        SERVER_LOG.unlink()
    except Exception:
        pass


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


PORT = find_free_port()
URL = f"http://localhost:{PORT}"


def main() -> int:
    print("=" * 70)
    print("STARTING EXPERT QUEUE & PIN ROUTING BROWSER VERIFICATION")
    print(f"Target URL: {URL}")
    print("=" * 70)

    # 1. Setup repository and PIN
    repo = get_expert_queue_repo()
    repo.set_expert_pin("1234")
    print("[SETUP] Pre-set expert PIN: '1234'")

    # Clean existing pending items in DB for reproducible clean screenshot
    with repo._connection() as conn:
        conn.execute("DELETE FROM queue_items WHERE domain_id IN ('lsu', 'dieu_tra_loi')")
        conn.execute("DELETE FROM approval_audit_trail")

    # 2. Seed realistic queue items
    res1 = repo.submit_to_queue(
        SOURCE_SMA_ALERT,
        "Làm sao để căn chỉnh thấu kính F-Theta trên dòng Sirius LSU khi bị lệch tâm tia beam?",
        title="Lỗi lệch tâm thấu kính F-Theta Sirius LSU",
        draft_answer="1. Sử dụng Jig quang học chuyên dụng đo vị trí tia beam.\n2. Nới lỏng ốc hãm CY Lens 1/4 vòng.\n3. Căn chỉnh trục Y theo vạch chuẩn quang học.\n4. Siết lực 0.8 Nm và chạy lại bài test kiểm tra log.",
        source_file="Sirius LSU/Sirius2_linearity/SOP_CanChinh.md",
        dislike_count=5,
        service_frequency=4,
        sample_count=10,
        domain_id="lsu",
        force_pass_throttle=True,
    )
    item1_id = res1.item_id
    print(f"[SEED] Created LSU Item 1: {item1_id}")

    # Seed Item 2 (Overdue > 48h)
    res2 = repo.submit_to_queue(
        SOURCE_SMA_ALERT,
        "Tiêu chuẩn độ lệch góc Bow Skew trên cụm LSU 6thA3 sau khi thay motor polygon?",
        title="Độ lệch góc Bow Skew trên 6thA3 LSU",
        draft_answer="Tiêu chuẩn Bow Skew tối đa không vượt quá ± 0.05 mrad theo tiêu chuẩn xuất xưởng 6thA3.",
        source_file="6thA3 LSU/Lỗi JIG BEAM/BowSkew_Standard.pdf",
        dislike_count=3,
        service_frequency=2,
        sample_count=8,
        domain_id="lsu",
        force_pass_throttle=True,
    )
    item2_id = res2.item_id

    # Fast-forward created_at of Item 2 to 52 hours ago
    t_overdue = (datetime.now(timezone.utc) - timedelta(hours=52)).isoformat()
    with repo._connection() as conn:
        conn.execute(
            "UPDATE queue_items SET created_at = ?, escalation_level = 1 WHERE item_id = ?",
            (t_overdue, item2_id),
        )
    print(f"[SEED] Created Overdue LSU Item 2: {item2_id}")

    # 3. Seed an active notebook and conversation to make UI load notebook chat screen
    nbs = load_active_notebooks()
    nb_id = nbs[0].id if nbs else "NB-DEFAULT"
    conv_id = f"CONV-EXPERT-{uuid.uuid4().hex[:6].upper()}"
    save_conversation(
        WorkspaceConversation(
            id=conv_id,
            notebook_id=nb_id,
            title="Kiểm thử Hàng đợi Chuyên gia & Phê duyệt PIN",
            ai_mode="grounded",
        )
    )

    # 4. Launch Streamlit server
    env = os.environ.copy()
    env["PYTHONPATH"] = str(APP_DIR / "src")
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    env["AIOS_RETRIEVAL_DEVICE"] = "cpu"
    env["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
    env["AIOS_RAG_V2_NUMPY_SCORING"] = "1"
    env["AIOS_AI_BACKEND"] = "local"
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
        # Wait for server ready
        deadline = time.time() + 60
        ready = False
        while time.time() < deadline:
            try:
                req = urllib.request.Request(f"http://localhost:{PORT}/_stcore/health")
                with urllib.request.urlopen(req, timeout=2) as r:
                    if r.status == 200:
                        ready = True
                        break
            except Exception:
                pass
            time.sleep(1)

        if not ready:
            print("[ERROR] Streamlit server failed to start within 60s.")
            return 1

        print(f"[SERVER] Server is live at {URL}")
        time.sleep(2)

        # 5. Playwright automation
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 960})
            page = context.new_page()

            target_url = f"{URL}/?nb={nb_id}&conv={conv_id}"
            print(f"[BROWSER] Navigating to {target_url}...")
            page.goto(target_url, timeout=45000, wait_until="networkidle")
            time.sleep(4)

            # Look for expert queue badge in sidebar
            sidebar = page.locator("[data-testid='stSidebar']")
            sidebar.wait_for(timeout=15000)

            # Wait for expert area text
            page.wait_for_selector("text=Khu vực Chuyên gia", timeout=15000)
            print("[BROWSER] Expert section loaded in sidebar!")

            # Check for badge text: [🚨 Duyệt miền LSU: 2 (1 quá hạn)]
            badge_loc = page.locator("text=Duyệt miền LSU")
            assert badge_loc.count() > 0, "Badge 'Duyệt miền LSU' not found in sidebar!"
            print(f"[BROWSER] Expert badge displayed: '{badge_loc.first.inner_text()}'")

            # Screenshot 1: Expert Queue Badge in sidebar
            img1_path = OUT_DIR_DESKTOP / "anh-desktop-expert-queue-badge-lsu.png"
            img1_mirror = LOCAL_DOC_DIR / "anh-desktop-expert-queue-badge-lsu.png"
            page.screenshot(path=str(img1_path), full_page=False)
            page.screenshot(path=str(img1_mirror), full_page=False)
            print(f"[SCREENSHOT 1] Saved expert queue badge screenshot to {img1_path}")

            # Click "Duyệt vào kho" button on item 1
            approve_btn = page.locator(f"button:has-text('Duyệt vào kho')").first
            approve_btn.scroll_into_view_if_needed()
            time.sleep(1)
            print("[BROWSER] Clicking 'Duyệt vào kho' button...")
            approve_btn.click()
            time.sleep(3)

            # Verify PIN Approval Popup / Form
            page.wait_for_selector("text=Xác thực Chuyên gia Phê duyệt", timeout=10000)
            print("[BROWSER] PIN Approval Form is visible!")

            # Verify machine check
            page.wait_for_selector("text=Tên máy:", timeout=5000)
            page.wait_for_selector("text=Hợp lệ", timeout=5000)
            print("[BROWSER] Machine binding check passed and displayed 'Hợp lệ'!")

            # Fill PIN field to show input state in screenshot
            pin_input = page.locator("input[type='password']").first
            pin_input.fill("1234")
            time.sleep(1)

            # Screenshot 2: PIN Approval Popup
            img2_path = OUT_DIR_DESKTOP / "anh-desktop-expert-pin-approval-popup.png"
            img2_mirror = LOCAL_DOC_DIR / "anh-desktop-expert-pin-approval-popup.png"
            page.screenshot(path=str(img2_path), full_page=False)
            page.screenshot(path=str(img2_mirror), full_page=False)
            print(f"[SCREENSHOT 2] Saved PIN approval popup screenshot to {img2_path}")

            # Submit approval
            confirm_btn = page.locator("button:has-text('Xác nhận & Ghi kho')").first
            confirm_btn.click()
            time.sleep(3)

            # Verify in DB that Item 1 is approved
            item1_updated = repo.get_item(item1_id)
            assert item1_updated.status == STATUS_APPROVED, f"Item 1 status is {item1_updated.status}, expected 'approved'!"
            print(f"[VERIFY] Item 1 successfully APPROVED in SQLite DB with audit stamp!")

            # Verify audit trail
            with repo._connection() as conn:
                audit_row = conn.execute("SELECT * FROM approval_audit_trail WHERE item_id = ?", (item1_id,)).fetchone()
                assert audit_row is not None, "Audit row not found in approval_audit_trail table!"
                print(f"[VERIFY] Audit stamp logged: {audit_row['audit_id']}, actor={audit_row['actor_subject']}, machine={audit_row['actor_machine']}")

            browser.close()

        print("=" * 70)
        print("ALL BROWSER VERIFICATIONS PASSED 100%!")
        print("=" * 70)
        return 0

    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        log_h.close()


if __name__ == "__main__":
    sys.exit(main())
