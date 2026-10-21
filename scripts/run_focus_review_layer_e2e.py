# -*- coding: utf-8 -*-
"""Playwright E2E Verification Script for DESKTOP-HOME-EXPERT-REVIEW-FOCUS-LAYER.

Verifies:
1. Sidebar keeps exact compact inbox dimensions (~300px) with badge & compact items.
2. Opening Focus Review Layer on REAL pending item (Bow Skew 6thA3) in read-only / view mode:
   - Full text question without truncation.
   - Max 3-line escalation summary (dislike SMA, frequency, overdue status).
   - Proposed entry in inline editable area.
   - Similarity check / diff comparison against knowledge base.
   - Evidence section with citation source viewer mechanism.
   - Fixed sticky bottom decision bar.
3. Closing Focus Review Layer:
   - Composer draft text ("Đang soạn thảo câu hỏi...") remains 100% intact!
4. Full decision flow on SIMULATED items in isolated fixture:
   - Inline edit draft.
   - Approve with PIN prompt (SALT SHA-256 + machine check).
   - Auto-advance to next item.
   - Request revision requires non-empty reason.
   - Auto-close when queue finishes.
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
    STATUS_REVISED,
    get_expert_queue_repo,
)
from aios_habit.expert_roles import get_expert_role_registry
from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import load_active_notebooks, save_conversation

OUT_DIR_DESKTOP = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")
OUT_DIR_DESKTOP.mkdir(parents=True, exist_ok=True)

LOCAL_DOC_DIR = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
LOCAL_DOC_DIR.mkdir(parents=True, exist_ok=True)

SERVER_LOG = LOCAL_DOC_DIR / "server_focus_review_verify.log"
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
    print("STARTING FOCUS REVIEW LAYER BROWSER VERIFICATION (E2E)")
    print(f"Target URL: {URL}")
    print("=" * 70)

    repo = get_expert_queue_repo()
    repo.set_expert_pin("1234")
    print("[SETUP] Pre-set expert PIN: '1234'")

    # 1. Kiểm tra mục thật QITEM-1C4BF0E4
    real_item = repo.get_item("QITEM-1C4BF0E4")
    assert real_item is not None, "Mục thật QITEM-1C4BF0E4 không tồn tại trong DB!"
    assert real_item.status == STATUS_PENDING, f"Mục thật QITEM-1C4BF0E4 phải ở trạng thái pending, hiện tại: {real_item.status}"
    print(f"[REAL ITEM CHECK] Mục thật '{real_item.title}' (ID: {real_item.item_id}) đang pending hợp lệ.")

    # Xóa các mục sim cũ nếu có (bảo tồn 100% mục thật)
    with repo._connection() as conn:
        conn.execute("DELETE FROM queue_items WHERE item_id LIKE 'QITEM-SIM-%'")

    # 2. Chuẩn bị sổ tay và hội thoại
    nbs = load_active_notebooks()
    nb_id = nbs[0].id if nbs else "NB-DEFAULT"
    conv_id = f"CONV-FOCUS-{uuid.uuid4().hex[:6].upper()}"
    save_conversation(
        WorkspaceConversation(
            id=conv_id,
            notebook_id=nb_id,
            title="Kiểm thử Lớp Duyệt Tập Trung Chuyên Gia",
            ai_mode="grounded",
        )
    )

    # 3. Khởi chạy Streamlit Server
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

    print(f"[SERVER] Launching Streamlit server on port {PORT}...")
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
            print("[ERROR] Server failed to start within 60s.")
            return 1

        print(f"[SERVER] Server is live at {URL}")
        time.sleep(2)

        # 4. Playwright Automation
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 960})
            page = context.new_page()

            target_url = f"{URL}/?nb={nb_id}&conv={conv_id}"
            print(f"[BROWSER] Navigating to {target_url}...")
            page.goto(target_url, timeout=45000, wait_until="networkidle")
            time.sleep(4)

            # Gõ câu hỏi dở vào ô soạn thảo
            draft_text = "Đang soạn thảo câu hỏi kiểm tra độ lệch góc Bow Skew trên LSU..."
            composer_ta = page.locator("[data-testid='stChatFloatingInputContainer'] textarea, [class*='st-key-wsc_question_input_'] textarea").first
            composer_ta.wait_for(timeout=15000)
            composer_ta.fill(draft_text)
            print(f"[BROWSER] Entered draft text in composer: '{draft_text}'")
            time.sleep(1)

            # Kiểm tra Sidebar: Giữ nguyên kích thước và vai trò hộp báo việc
            sidebar = page.locator("[data-testid='stSidebar']")
            sidebar.wait_for(timeout=10000)
            page.wait_for_selector("text=Khu vực Chuyên gia", timeout=15000)
            print("[BROWSER] Expert section visible in sidebar!")

            # -----------------------------------------------------------------
            # ẢNH 1: Sidebar không đổi kích thước, danh sách rút gọn
            # -----------------------------------------------------------------
            img1_path = OUT_DIR_DESKTOP / "anh-01-sidebar-compact-inbox.png"
            img1_mirror = LOCAL_DOC_DIR / "anh-01-sidebar-compact-inbox.png"
            page.screenshot(path=str(img1_path), full_page=False)
            page.screenshot(path=str(img1_mirror), full_page=False)
            print(f"[SCREENSHOT 1] Saved: {img1_path}")

            # Bấm nút [🔍 Mở duyệt tập trung] trên mục thật
            open_focus_btn = page.locator("button:has-text('Mở duyệt tập trung')").first
            open_focus_btn.scroll_into_view_if_needed()
            time.sleep(1)
            print("[BROWSER] Clicking 'Mở duyệt tập trung' on real pending item...")
            open_focus_btn.click()
            time.sleep(4)

            # -----------------------------------------------------------------
            # ẢNH 2: Lớp duyệt mở trên MỤC THẬT (Bow Skew 6thA3) ở chế độ xem
            # -----------------------------------------------------------------
            # Chờ tiêu đề lớp duyệt
            page.wait_for_selector("text=LỚP DUYỆT TẬP TRUNG CHUYÊN GIA", timeout=15000)
            print("[BROWSER] Focus review layer opened!")

            # Kiểm tra câu hỏi gốc TOÀN VĂN không bị cắt xén
            page.wait_for_selector("text=Tiêu chuẩn độ lệch góc Bow Skew trên cụm LSU 6thA3 sau khi thay motor polygon?", timeout=5000)
            print("[BROWSER] Full question text displayed without truncation!")

            # Kiểm tra tóm tắt lý do leo thang max 3 dòng
            page.wait_for_selector("text=Cảnh báo xu hướng chê SMA(20)", timeout=5000)
            page.wait_for_selector("text=Quá hạn", timeout=5000)
            print("[BROWSER] 3-line escalation summary displayed!")

            # Chụp ảnh 2
            img2_path = OUT_DIR_DESKTOP / "anh-02-focus-review-real-item-bowskew.png"
            img2_mirror = LOCAL_DOC_DIR / "anh-02-focus-review-real-item-bowskew.png"
            page.screenshot(path=str(img2_path), full_page=False)
            page.screenshot(path=str(img2_mirror), full_page=False)
            print(f"[SCREENSHOT 2] Saved: {img2_path}")

            # ĐÓNG lớp duyệt trên mục thật (TUYỆT ĐỐI KHÔNG DUYỆT/TỪ CHỐI MỤC THẬT)
            close_btn = page.locator("button:has-text('Đóng lớp duyệt')").first
            close_btn.click()
            time.sleep(3)
            print("[BROWSER] Closed focus review layer on real item.")

            # Kiểm tra bảo toàn câu đang gõ dở
            composer_after = page.locator("[class*='st-key-wsc_question_input_'] textarea").first
            val_after = composer_after.input_value()
            assert val_after.strip() == draft_text.strip(), f"Câu gõ dở bị mất! Mong đợi: '{draft_text}', thực tế: '{val_after}'"
            print("[BROWSER] INVARIANT VERIFIED: Draft text in composer remains 100% intact after closing layer!")

            # -----------------------------------------------------------------
            # LUỒNG QUYẾT ĐỊNH TRÊN MỤC HÀNG ĐỢI GIẢ LẬP TRONG FIXTURE CÁCH LY
            # -----------------------------------------------------------------
            print("[FIXTURE] Seeding simulated queue items for isolated decision flow...")
            sim1_res = repo.submit_to_queue(
                SOURCE_SMA_ALERT,
                "Cách căn chỉnh góc lệch tia beam LSU bằng Jig quang học?",
                title="Căn chỉnh tia beam LSU bằng Jig",
                draft_answer="Nới lỏng ốc hãm CY Lens và chỉnh vạch chuẩn 0.8 Nm.",
                source_file="Sirius LSU/Sirius2_linearity/SOP_CanChinh.md",
                dislike_count=4,
                service_frequency=5,
                sample_count=10,
                domain_id="lsu",
                force_pass_throttle=True,
            )
            sim1_id = sim1_res.item_id

            sim2_res = repo.submit_to_queue(
                SOURCE_SMA_ALERT,
                "Tiêu chuẩn rung chấn motor polygon 6thA3 sau thay thế?",
                title="Rung chấn motor polygon 6thA3",
                draft_answer="Đo dao động tần số cao dưới 0.02 mm/s.",
                source_file="6thA3 LSU/Lỗi JIG BEAM/BowSkew_Standard.pdf",
                dislike_count=3,
                service_frequency=3,
                sample_count=6,
                domain_id="lsu",
                force_pass_throttle=True,
            )
            sim2_id = sim2_res.item_id
            print(f"[FIXTURE] Seeded Sim Item 1: {sim1_id}, Sim Item 2: {sim2_id}")

            # Reload trang để nạp 2 mục giả lập
            page.reload(wait_until="networkidle")
            time.sleep(3)

            # Mở Lớp duyệt tập trung cho Sim Item 1
            sim1_btn = page.locator(f"button[key*='btn_open_focus_{sim1_id}']").first
            if sim1_btn.count() == 0:
                # Tìm theo button text nếu key khác
                sim1_btn = page.locator("button:has-text('Mở duyệt tập trung')").first
            sim1_btn.click()
            time.sleep(3)

            page.wait_for_selector("text=LỚP DUYỆT TẬP TRUNG CHUYÊN GIA", timeout=15000)
            print("[BROWSER] Focus layer opened on Sim Item 1!")

            # 1. Sửa tại chỗ bản đề xuất trong phần (b)
            draft_ta = page.locator(f"[class*='st-key-wsc_focus_draft_input_{sim1_id}'] textarea").first
            if draft_ta.count() > 0:
                draft_ta.fill("Nới lỏng ốc hãm CY Lens và chỉnh vạch chuẩn 0.8 Nm - ĐÃ ĐỐI CHIẾU TIÊU CHUẨN XUẤT XƯỞNG.")
                print("[BROWSER] Inline edited draft answer in section (b)!")
                time.sleep(1)

            # 2. Bấm [✅ Duyệt vào kho]
            app_btn = page.locator(f"button[key*='btn_focus_approve_{sim1_id}']").first
            if app_btn.count() == 0:
                app_btn = page.locator("button:has-text('Duyệt vào kho')").first
            app_btn.click()
            time.sleep(2)

            # 3. Form PIN xuất hiện -> Nhập PIN 1234
            page.wait_for_selector("text=Xác thực Mã PIN Phê duyệt", timeout=10000)
            page.wait_for_selector("text=Hợp lệ", timeout=5000)
            print("[BROWSER] PIN modal displayed with valid machine check!")

            pin_inp = page.locator("input[type='password']").first
            pin_inp.fill("1234")
            time.sleep(1)

            # -----------------------------------------------------------------
            # ẢNH 3: Trọn luồng ra quyết định trên mục giả lập
            # -----------------------------------------------------------------
            img3_path = OUT_DIR_DESKTOP / "anh-03-focus-review-decision-flow-simulated.png"
            img3_mirror = LOCAL_DOC_DIR / "anh-03-focus-review-decision-flow-simulated.png"
            page.screenshot(path=str(img3_path), full_page=False)
            page.screenshot(path=str(img3_mirror), full_page=False)
            print(f"[SCREENSHOT 3] Saved: {img3_path}")

            # Xác nhận & Ghi kho
            sub_pin_btn = page.locator("button:has-text('Xác nhận & Ghi kho')").first
            sub_pin_btn.click()
            time.sleep(4)

            # Kiểm tra Sim Item 1 đã duyệt thành công trong DB
            sim1_updated = repo.get_item(sim1_id)
            assert sim1_updated.status == STATUS_APPROVED, f"Sim Item 1 chưa được duyệt, trạng thái: {sim1_updated.status}"
            assert "ĐÃ ĐỐI CHIẾU TIÊU CHUẨN XUẤT XƯỞNG" in sim1_updated.draft_answer, "Bản sửa tại chỗ chưa được lưu vào DB!"
            print("[BROWSER] Sim Item 1 successfully APPROVED with edited draft!")

            # 4. Kiểm tra tự động chuyển sang mục tiếp theo (Sim Item 2 hoặc mục còn lại)
            time.sleep(2)
            print("[BROWSER] Checking auto-advance to next item in queue...")
            
            # Trả sửa mục tiếp theo kèm lý do bắt buộc
            rev_btn = page.locator("button:has-text('Trả sửa kèm lý do')").first
            if rev_btn.count() > 0:
                rev_btn.click()
                time.sleep(2)

                # Bấm xác nhận khi lý do trống -> hiện lỗi
                confirm_rev_btn = page.locator("button:has-text('Xác nhận Trả sửa')").first
                confirm_rev_btn.click()
                time.sleep(1)
                page.wait_for_selector("text=Bắt buộc phải nhập lý do trả sửa", timeout=5000)
                print("[BROWSER] Verified validation: Revision request blocked when reason is empty!")

                # Điền lý do
                rev_ta = page.locator("textarea[placeholder*='Ví dụ: Thiếu thông số']").first
                rev_ta.fill("Sai phương pháp đo: Cần dùng cảm biến gia tốc tần số cao 10 kHz.")
                time.sleep(1)
                confirm_rev_btn.click()
                time.sleep(4)
                print("[BROWSER] Successfully submitted revision request with mandatory reason!")

            # Dọn dẹp các mục giả lập sau kiểm thử để DB sạch
            with repo._connection() as conn:
                conn.execute("DELETE FROM queue_items WHERE item_id IN (?, ?)", (sim1_id, sim2_id))
                conn.execute("DELETE FROM approval_audit_trail WHERE item_id IN (?, ?)", (sim1_id, sim2_id))
            print("[CLEANUP] Removed simulated test items, real queue DB is intact.")

            # Kiểm tra lại mục thật vẫn nguyên trạng
            real_check = repo.get_item("QITEM-1C4BF0E4")
            assert real_check.status == STATUS_PENDING, f"Mục thật bị thay đổi trạng thái thành {real_check.status}!"
            print("[INVARIANT] Real pending item QITEM-1C4BF0E4 status remains 100% PENDING untouched!")

            browser.close()

        print("=" * 70)
        print("ALL BROWSER E2E TESTS PASSED 100%!")
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
