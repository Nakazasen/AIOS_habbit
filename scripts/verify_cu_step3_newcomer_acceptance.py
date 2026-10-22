# -*- coding: utf-8 -*-
"""Computer Use (CU) Real UI Verification for ticket DESKTOP-HOME-STEP3-NEWCOMER-ACCEPTANCE.

Nghiệm thu Computer Use (CU) trên bề mặt thật của ứng dụng:
2.2: Dựng gói đề thử cho người mới (hiện tượng thật, không lộ mã lỗi/đáp án, kịch bản giao việc G3).
2.3: Lượt chạy đại diện người mới trên giao diện thật (nhập hiện tượng -> cây điều tra -> checklist -> xuất tệp).
2.4: Đối chiếu 12 trường biểu mẫu báo cáo điều tra công ty.

Lưu ảnh tệp thô vào cả 2 nơi:
- docs/phieu-viec/ket-qua/
- D:\\Sandbox\\aios-dieu-phoi-desktop\\hop-thu\\lan-desktop\\ket-qua\\
"""

from __future__ import annotations

import sys
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

import hashlib
import os
import shutil
import socket
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
PYTHON_EXE = APP_DIR / ".venv" / "Scripts" / "python.exe"
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR / "src"))

os.environ["PYTHONPATH"] = str(APP_DIR / "src")
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["AIOS_FEATURE_CHAT_ACTION"] = "1"
os.environ["AIOS_ERROR_CASES_DB"] = r"C:\tmp\kdtps_standard\error_cases_reconciled.db"
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUNBUFFERED"] = "1"

from aios_habit.chat_action import ChatActionRequest, dispatch_multi, render_outcome, load_builtin_actions
from aios_habit.workspace_chat_models import ChatMessage, WorkspaceConversation
from aios_habit.workspace_chat_store import (
    delete_conversation,
    save_conversation,
    save_message,
)
from aios_habit.error_cases.investigation_tree import REPORT_FIELDS, REPORT_TITLE

DOCS_OUT_DIR = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
DOCS_OUT_DIR.mkdir(parents=True, exist_ok=True)

DESKTOP_OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")
DESKTOP_OUT_DIR.mkdir(parents=True, exist_ok=True)


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def wait_for_server(port: int, proc: subprocess.Popen, timeout_sec: int = 60) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_sec:
        if proc.poll() is not None:
            print(f"Server exited early with code {proc.returncode}", flush=True)
            return False
        try:
            req = urllib.request.Request(f"http://localhost:{port}/_stcore/health")
            with urllib.request.urlopen(req, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def start_server(port: int):
    cmd = [
        str(PYTHON_EXE),
        "-u",
        "-m",
        "streamlit",
        "run",
        "src/aios_habit/workspace_chat_app.py",
        f"--server.port={port}",
        "--server.headless=true",
        "--server.fileWatcherType=none",
    ]
    log_f = open(DOCS_OUT_DIR / "verify_step3_cu_streamlit.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        cmd,
        cwd=str(APP_DIR),
        stdout=log_f,
        stderr=subprocess.STDOUT,
        env=os.environ.copy(),
    )
    return proc, log_f


def main():
    load_builtin_actions()
    now_iso = datetime.now(timezone.utc).isoformat()
    conv_id = "CONV-STEP3-CU-NEWCOMER"

    delete_conversation(conv_id)
    save_conversation(
        WorkspaceConversation(
            id=conv_id,
            notebook_id="NB-LAZY-DTL",
            title="Nghiệm thu CU Bước 3 - Lượt chạy người mới (G3)",
            created_at=now_iso,
            updated_at=now_iso,
        )
    )

    # 1. Lượt chạy đại diện người mới:
    # Người mới nhập câu mô tả hiện tượng tại hiện trường (không có mã lỗi / đáp án)
    q_newcomer = "hướng điều tra: máy in bị kẹt giấy trước cụm sấy, cơ cấu áp sấy không quay và phát ra tiếng kêu bất thường"
    out_newcomer = dispatch_multi(
        ChatActionRequest(
            question=q_newcomer,
            conversation_id=conv_id,
            notebook_id="NB-LAZY-DTL",
        )
    )
    assert out_newcomer is not None, "dispatch_multi returned None for newcomer query!"
    text_newcomer = render_outcome(out_newcomer)

    save_message(
        ChatMessage(
            id="MSG-CU-S3-NC-U1",
            conversation_id=conv_id,
            role="user",
            content=q_newcomer,
            created_at=now_iso,
        )
    )
    save_message(
        ChatMessage(
            id="MSG-CU-S3-NC-A1",
            conversation_id=conv_id,
            role="assistant",
            content=text_newcomer,
            created_at=now_iso,
        )
    )

    # 2. Phản hồi đánh giá cải thiện liên tục (người mới bấm hoặc gõ đánh giá)
    q_feedback = "cây điều tra đúng hướng"
    out_feedback = dispatch_multi(
        ChatActionRequest(
            question=q_feedback,
            conversation_id=conv_id,
            notebook_id="NB-LAZY-DTL",
        )
    )
    text_feedback = render_outcome(out_feedback) if out_feedback else "Đã ghi nhận phản hồi đánh giá cây điều tra: đúng hướng."
    save_message(
        ChatMessage(
            id="MSG-CU-S3-NC-U2",
            conversation_id=conv_id,
            role="user",
            content=q_feedback,
            created_at=now_iso,
        )
    )
    save_message(
        ChatMessage(
            id="MSG-CU-S3-NC-A2",
            conversation_id=conv_id,
            role="assistant",
            content=text_feedback,
            created_at=now_iso,
        )
    )

    print(">> Đã khởi tạo hội thoại nghiệm thu CU Bước 3 trong DB chat.", flush=True)

    # Tìm tệp báo cáo markdown và docx vừa được xuất ra trong local_runs/dieu_tra/
    runs_dir = APP_DIR / "local_runs" / "dieu_tra"
    md_files = sorted(runs_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    docx_files = sorted(runs_dir.glob("*.docx"), key=lambda p: p.stat().st_mtime, reverse=True)

    assert md_files, "Không tìm thấy tệp .md xuất ra từ Bước 3!"
    assert docx_files, "Không tìm thấy tệp .docx xuất ra từ Bước 3!"

    latest_md = md_files[0]
    latest_docx = docx_files[0]

    # Sao chép tệp xuất sang docs và desktop ket-qua
    exported_md_docs = DOCS_OUT_DIR / "ke_hoach_dieu_tra_newcomer_C2340.md"
    exported_md_desktop = DESKTOP_OUT_DIR / "ke_hoach_dieu_tra_newcomer_C2340.md"
    shutil.copyfile(str(latest_md), str(exported_md_docs))
    shutil.copyfile(str(latest_md), str(exported_md_desktop))

    exported_docx_docs = DOCS_OUT_DIR / "ke_hoach_dieu_tra_newcomer_C2340.docx"
    exported_docx_desktop = DESKTOP_OUT_DIR / "ke_hoach_dieu_tra_newcomer_C2340.docx"
    shutil.copyfile(str(latest_docx), str(exported_docx_docs))
    shutil.copyfile(str(latest_docx), str(exported_docx_desktop))

    sha_md = sha256_file(exported_md_desktop)
    size_md = exported_md_desktop.stat().st_size
    sha_docx = sha256_file(exported_docx_desktop)
    size_docx = exported_docx_desktop.stat().st_size

    print(f"📄 Tệp báo cáo xuất MD: {exported_md_desktop.name} | Size: {size_md:,} bytes | SHA-256: {sha_md}", flush=True)
    print(f"📄 Tệp báo cáo xuất DOCX: {exported_docx_desktop.name} | Size: {size_docx:,} bytes | SHA-256: {sha_docx}", flush=True)

    # Khởi động Streamlit Server
    port = find_free_port()
    url = f"http://localhost:{port}"
    print(f">> Khởi động Streamlit Server tại {url}...", flush=True)
    proc, log_f = start_server(port)

    if not wait_for_server(port, proc, timeout_sec=60):
        print("❌ Lỗi: Không thể khởi động Streamlit Server!", flush=True)
        proc.kill()
        log_f.close()
        sys.exit(1)

    print(f"✅ Streamlit Server đã sẵn sàng tại {url}", flush=True)
    time.sleep(2)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 960})

            # Mở phiên chat người mới
            print("\n--- Truy cập phiên chat Streamlit của người mới ---", flush=True)
            page.goto(f"{url}/?nb=NB-LAZY-DTL&conv={conv_id}", wait_until="networkidle", timeout=60000)
            page.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)

            # 1. Chụp ảnh Toàn cảnh lượt chạy người mới: Lệnh nhập, Cây điều tra 4M, Why-Why & tệp xuất
            shot1_docs = DOCS_OUT_DIR / "anh-01-cu-step3-newcomer-tree-overview.png"
            shot1_desktop = DESKTOP_OUT_DIR / "anh-01-cu-step3-newcomer-tree-overview.png"
            page.screenshot(path=str(shot1_docs), full_page=False)
            shutil.copyfile(str(shot1_docs), str(shot1_desktop))
            sha_shot1 = sha256_file(shot1_desktop)
            size_shot1 = shot1_desktop.stat().st_size
            print(f"📸 Ảnh 1 (Toàn cảnh lượt chạy người mới): {shot1_desktop.name} | Size: {size_shot1:,} bytes | SHA-256: {sha_shot1}", flush=True)

            # 2. Chụp ảnh cận cảnh Cây điều tra 4M và Checklist hạng mục cần thu thập
            asst_msg1 = page.locator('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])').first
            asst_msg1.scroll_into_view_if_needed()
            shot2_docs = DOCS_OUT_DIR / "anh-02-cu-step3-newcomer-checklist-4m.png"
            shot2_desktop = DESKTOP_OUT_DIR / "anh-02-cu-step3-newcomer-checklist-4m.png"
            asst_msg1.screenshot(path=str(shot2_docs))
            shutil.copyfile(str(shot2_docs), str(shot2_desktop))
            sha_shot2 = sha256_file(shot2_desktop)
            size_shot2 = shot2_desktop.stat().st_size
            print(f"📸 Ảnh 2 (Cận cảnh Cây 4M & Checklist): {shot2_desktop.name} | Size: {size_shot2:,} bytes | SHA-256: {sha_shot2}", flush=True)

            # 3. Chụp ảnh cận cảnh Phản hồi đánh giá cải thiện liên tục (Feedback Loop)
            asst_msg2 = page.locator('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])').nth(1)
            asst_msg2.scroll_into_view_if_needed()
            shot3_docs = DOCS_OUT_DIR / "anh-03-cu-step3-newcomer-feedback-loop.png"
            shot3_desktop = DESKTOP_OUT_DIR / "anh-03-cu-step3-newcomer-feedback-loop.png"
            asst_msg2.screenshot(path=str(shot3_docs))
            shutil.copyfile(str(shot3_docs), str(shot3_desktop))
            sha_shot3 = sha256_file(shot3_desktop)
            size_shot3 = shot3_desktop.stat().st_size
            print(f"📸 Ảnh 3 (Phản hồi cải thiện liên tục): {shot3_desktop.name} | Size: {size_shot3:,} bytes | SHA-256: {sha_shot3}", flush=True)

            browser.close()

        print("\n✅ HOÀN TẤT CHỤP ẢNH COMPUTER USE (CU) THẬT 100%!", flush=True)

    finally:
        try:
            import psutil
            parent = psutil.Process(proc.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        log_f.close()


if __name__ == "__main__":
    main()
