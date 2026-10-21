# -*- coding: utf-8 -*-
"""Browser verification script for ticket DESKTOP-HOME-LESSON-FORGET-PANEL-CLARITY.

Verifies:
1. Case (a) - Question without lesson:
   - Panel shows "Vì sao AIOS nhớ điều này?" and single status "Chưa có bài học đã xác nhận cho câu hỏi này."
   - Forget action is completely hidden: NO preview box, NO empty quotes '“”', NO confirm button.
   - Screenshot 1: anh-desktop-lesson-forget-01-no-lesson-clean.png
2. Case (b) - Question with confirmed lesson:
   - Panel shows real lesson content, clear consequence explanation ("từ nay AIOS không dùng bài học này trả lời nữa, lịch sử vẫn giữ để khôi phục được").
   - Click "Quên bài học này" activates clear preview box with real statement and confirm/cancel buttons.
   - Screenshot 2: anh-desktop-lesson-forget-02-with-lesson-clear.png
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
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

from aios_habit.workspace_chat_models import ChatMessage, WorkspaceConversation
from aios_habit.workspace_chat_store import save_conversation, save_message
from aios_habit.workspace_memory_service import (
    append_memory_decision,
    default_decisions_path,
    default_pending_drafts_path,
    make_memory_decision,
    set_workspace_memory_enabled_preference,
)

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


PORT = find_free_port()
URL = f"http://localhost:{PORT}"
OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")
OUT_DIR.mkdir(parents=True, exist_ok=True)
SERVER_LOG = OUT_DIR / "server_lesson_forget_panel_clarity.log"


def log(msg: str) -> None:
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_str}] {msg}", flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


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

    if SERVER_LOG.exists():
        try:
            SERVER_LOG.unlink()
        except Exception:
            pass

    log_handle = open(SERVER_LOG, "a", encoding="utf-8")
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
    log(f"Khởi động Streamlit tại port {PORT}...")
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


def main() -> int:
    log("=== BẮT ĐẦU KIỂM CHỨNG BROWSER CHO DESKTOP-HOME-LESSON-FORGET-PANEL-CLARITY ===")

    # 1. Bật tính năng ghi nhớ & đảm bảo bài học mẫu có trong decisions log
    set_workspace_memory_enabled_preference(True)

    # Đảm bảo bài học có trong scope workspace:mom_opcenter
    dec_path = default_decisions_path()
    sample_statement = "Khi bảo dưỡng máy nén khí phải xả áp bình tích trước khi mở van"
    sample_decision = make_memory_decision(
        action="confirm",
        statement=sample_statement,
        scope="workspace:mom_opcenter",
        evidence_refs=("user_confirm",),
        applies_when="Bảo dưỡng máy nén khí",
        title="Bảo dưỡng máy nén khí",
        memory_id="mem_compressor_test",
    )
    append_memory_decision(sample_decision, path=dec_path)

    # Xóa file pending_drafts cũ nếu có
    pending_path = default_pending_drafts_path()
    if pending_path.exists():
        try:
            pending_path.unlink()
        except Exception:
            pass

    # 2. Khởi tạo 2 hội thoại kiểm thử
    nb_id = "mom_opcenter"
    conv_no_lesson = f"CONV-NOLS-{uuid.uuid4().hex[:6].upper()}"
    save_conversation(
        WorkspaceConversation(
            id=conv_no_lesson,
            notebook_id=nb_id,
            title="Kiểm chứng 1: Không có bài học",
            ai_mode="grounded",
        )
    )
    msg_no_u = ChatMessage(
        id=f"msg_u_{uuid.uuid4().hex[:6]}",
        conversation_id=conv_no_lesson,
        role="user",
        content="Hôm nay thời tiết thế nào?",
    )
    msg_no_a = ChatMessage(
        id=f"msg_a_{uuid.uuid4().hex[:6]}",
        conversation_id=conv_no_lesson,
        role="assistant",
        content="Tôi là trợ lý AIOS. Hôm nay thời tiết thuận lợi cho ca làm việc.",
    )
    save_message(msg_no_u)
    save_message(msg_no_a)

    conv_with_lesson = f"CONV-WITHLS-{uuid.uuid4().hex[:6].upper()}"
    save_conversation(
        WorkspaceConversation(
            id=conv_with_lesson,
            notebook_id=nb_id,
            title="Kiểm chứng 2: Có bài học thật",
            ai_mode="grounded",
        )
    )
    msg_with_u = ChatMessage(
        id=f"msg_u_{uuid.uuid4().hex[:6]}",
        conversation_id=conv_with_lesson,
        role="user",
        content="Bảo dưỡng máy nén khí cần lưu ý điều gì?",
    )
    msg_with_a = ChatMessage(
        id=f"msg_a_{uuid.uuid4().hex[:6]}",
        conversation_id=conv_with_lesson,
        role="assistant",
        content="Khi bảo dưỡng máy nén khí, bạn cần tuân thủ quy tắc an toàn đã được ghi nhớ: phải xả áp bình tích trước khi mở van.",
    )
    save_message(msg_with_u)
    save_message(msg_with_a)

    # 3. Khởi động server
    proc = start_server()
    try:
        if not wait_for_server(URL, timeout_s=60.0):
            log("[FAIL] Không thể kết nối tới server Streamlit sau 60s")
            return 1
        log(f"[OK] Server Streamlit đã sẵn sàng tại {URL}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # -------------------------------------------------------------
            # BƯỚC 1: Kiểm chứng câu hỏi KHÔNG CÓ BÀI HỌC (Case a)
            # -------------------------------------------------------------
            log("--- [BƯỚC 1] Mở hội thoại không có bài học ---")
            ctx1 = browser.new_context(viewport={"width": 1400, "height": 900})
            page1 = ctx1.new_page()
            url1 = f"{URL}/?nb={nb_id}&conv={conv_no_lesson}"
            page1.goto(url1, wait_until="networkidle", timeout=60000)
            page1.wait_for_timeout(3000)

            # Chờ panel xuất hiện
            log("Chờ dòng tiêu đề panel...")
            page1.wait_for_selector('text="Vì sao AIOS nhớ điều này?"', timeout=20000)
            page1.wait_for_selector('text="Chưa có bài học đã xác nhận cho câu hỏi này."', timeout=20000)

            # Kiểm tra KHÔNG CÓ hộp xem trước quên bài học, KHÔNG CÓ nút Xác nhận, KHÔNG CÓ chuỗi rỗng ""
            body_text_1 = page1.inner_text("body")
            assert "Chưa có bài học đã xác nhận cho câu hỏi này." in body_text_1
            assert 'Xem trước: AIOS sẽ ngừng dùng bài học “”.' not in body_text_1
            assert 'ngừng dùng bài học “”.' not in body_text_1
            assert "Xem trước: AIOS sẽ ngừng dùng bài học" not in body_text_1

            # Nút xác nhận quên không được hiện
            confirm_btns = page1.locator('[class*="st-key-wsc_memory_confirm"] button')
            assert confirm_btns.count() == 0, "Lỗi: Nút Xác nhận quên vẫn xuất hiện khi không có bài học!"

            ss1_path = OUT_DIR / "anh-desktop-lesson-forget-01-no-lesson-clean.png"
            page1.screenshot(path=str(ss1_path), full_page=True)
            log(f"[OK] Đã chụp ảnh Case (a): {ss1_path.name}")
            ctx1.close()

            # -------------------------------------------------------------
            # BƯỚC 2: Kiểm chứng câu hỏi CÓ BÀI HỌC THẬT (Case b)
            # -------------------------------------------------------------
            log("--- [BƯỚC 2] Mở hội thoại có bài học thật ---")
            ctx2 = browser.new_context(viewport={"width": 1400, "height": 900})
            page2 = ctx2.new_page()
            url2 = f"{URL}/?nb={nb_id}&conv={conv_with_lesson}"
            page2.goto(url2, wait_until="networkidle", timeout=60000)
            page2.wait_for_timeout(3000)

            page2.wait_for_selector('text="Vì sao AIOS nhớ điều này?"', timeout=20000)
            log("Chờ nội dung bài học thật xuất hiện trên panel...")
            page2.wait_for_selector(f'text="{sample_statement}"', timeout=20000)

            body_text_2 = page2.inner_text("body")
            assert sample_statement in body_text_2
            assert "từ nay AIOS không dùng bài học này trả lời nữa" in body_text_2
            assert "lịch sử vẫn giữ để khôi phục được" in body_text_2

            # Tìm và click nút "Quên bài học này"
            forget_btn = page2.locator('button:has-text("Quên bài học này")').first
            forget_btn.wait_for(state="visible", timeout=10000)
            log("Click nút 'Quên bài học này'...")
            forget_btn.click(force=True)
            page2.wait_for_timeout(2000)

            # Chờ hộp xem trước và nút xác nhận quên xuất hiện
            log("Chờ hộp xem trước quên với nội dung thật...")
            page2.wait_for_selector('text=Xem trước: AIOS sẽ ngừng dùng bài học', timeout=20000)
            page2.wait_for_selector('[class*="st-key-wsc_memory_confirm"] button', timeout=20000)
            page2.wait_for_selector('[class*="st-key-wsc_memory_cancel"] button', timeout=20000)

            body_after_click = page2.inner_text("body")
            assert "Xem trước: AIOS sẽ ngừng dùng bài học" in body_after_click
            assert sample_statement in body_after_click
            assert "Từ nay AIOS không dùng bài học này để trả lời nữa" in body_after_click
            assert "Lịch sử quyết định vẫn được giữ để có thể khôi phục khi cần" in body_after_click
            log(f"[DEBUG] Box text verified: {sample_statement[:30]}...")

            ss2_path = OUT_DIR / "anh-desktop-lesson-forget-02-with-lesson-clear.png"
            page2.screenshot(path=str(ss2_path), full_page=True)
            log(f"[OK] Đã chụp ảnh Case (b): {ss2_path.name}")
            ctx2.close()

            browser.close()

        log("=== KIỂM CHỨNG BROWSER HOÀN TẤT THÀNH CÔNG 100% ===")
        log(f"Ảnh 1: {ss1_path.name} ({ss1_path.stat().st_size} bytes) | SHA-256: {sha256_file(ss1_path)}")
        log(f"Ảnh 2: {ss2_path.name} ({ss2_path.stat().st_size} bytes) | SHA-256: {sha256_file(ss2_path)}")
        return 0
    finally:
        kill_server(proc)


if __name__ == "__main__":
    sys.exit(main())
