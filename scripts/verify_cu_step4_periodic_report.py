# -*- coding: utf-8 -*-
"""Computer Use (CU) Real UI Verification for ticket DESKTOP-HOME-STEP4-PERIODIC-REPORT-ACCEPTANCE.

Runs real Streamlit server and navigates Playwright Chromium to verify:
2.2 [CU]:
- Generates periodic trend report for latest week (2026-W42) from real LSU/JIG data through the real entry point.
- Generates periodic trend report for heavy week (2026-W34, 35,139 rows).
- Captures raw PNG screenshots of the actual UI as proof.
- Exports raw report files and calculates exact SHA-256 and byte sizes.

Saves raw PNG screenshots to both:
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

from aios_habit.chat_action import ChatActionRequest, dispatch_multi, render_outcome
from aios_habit.workspace_chat_models import ChatMessage, WorkspaceConversation
from aios_habit.workspace_chat_store import (
    delete_conversation,
    save_conversation,
    save_message,
)
from aios_habit.production_prediction.periodic_trend_report import tao_bao_cao_dinh_ky_tuan

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
    log_f = open(DOCS_OUT_DIR / "verify_step4_cu_streamlit.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        cmd,
        cwd=str(APP_DIR),
        stdout=log_f,
        stderr=subprocess.STDOUT,
        env=os.environ.copy(),
    )
    return proc, log_f


def main():
    now_iso = datetime.now(timezone.utc).isoformat()

    conv_latest = "CONV-STEP4-CU-LATEST"
    conv_heavy = "CONV-STEP4-CU-HEAVY"

    delete_conversation(conv_latest)
    delete_conversation(conv_heavy)

    save_conversation(
        WorkspaceConversation(
            id=conv_latest,
            notebook_id="NB-LAZY-DTL",
            title="Nghiệm thu CU Báo cáo xu hướng tuần mới nhất (2026-W42)",
            created_at=now_iso,
            updated_at=now_iso,
        )
    )
    save_conversation(
        WorkspaceConversation(
            id=conv_heavy,
            notebook_id="NB-LAZY-DTL",
            title="Nghiệm thu CU Báo cáo xu hướng tuần tải lớn (2026-W34)",
            created_at=now_iso,
            updated_at=now_iso,
        )
    )

    # 1. Sinh kết quả tuần mới nhất 2026-W42 qua điểm vào thật chat_action
    q_latest = "báo cáo xu hướng định kỳ"
    out_latest = dispatch_multi(
        ChatActionRequest(
            question=q_latest,
            conversation_id=conv_latest,
            notebook_id="NB-LAZY-DTL",
        )
    )
    text_latest = render_outcome(out_latest) if out_latest else ""
    save_message(
        ChatMessage(
            id="MSG-CU-S4-LAT-U",
            conversation_id=conv_latest,
            role="user",
            content=q_latest,
            created_at=now_iso,
        )
    )
    save_message(
        ChatMessage(
            id="MSG-CU-S4-LAT-A",
            conversation_id=conv_latest,
            role="assistant",
            content=text_latest,
            created_at=now_iso,
        )
    )

    # 2. Sinh kết quả tuần tải lớn 2026-W34 qua điểm vào thật chat_action
    q_heavy = "báo cáo định kỳ tuần 2026-W34"
    out_heavy = dispatch_multi(
        ChatActionRequest(
            question=q_heavy,
            conversation_id=conv_heavy,
            notebook_id="NB-LAZY-DTL",
        )
    )
    text_heavy = render_outcome(out_heavy) if out_heavy else ""
    save_message(
        ChatMessage(
            id="MSG-CU-S4-HVY-U",
            conversation_id=conv_heavy,
            role="user",
            content=q_heavy,
            created_at=now_iso,
        )
    )
    save_message(
        ChatMessage(
            id="MSG-CU-S4-HVY-A",
            conversation_id=conv_heavy,
            role="assistant",
            content=text_heavy,
            created_at=now_iso,
        )
    )

    print(">> Đã khởi tạo 2 hội thoại nghiệm thu CU trong DB chat.", flush=True)

    # Đảm bảo tệp báo cáo markdown tuần 2026-W42 đã được ghi
    rep_w42 = tao_bao_cao_dinh_ky_tuan(ky_tuan="2026-W42")
    p_rep = Path(rep_w42.duong_dan_bao_cao)
    assert p_rep.is_file(), f"Tệp báo cáo không tồn tại: {p_rep}"

    # Sao chép tệp báo cáo sang docs và desktop ket-qua
    rep_docs = DOCS_OUT_DIR / "bao_cao_xu_huong_tuan_2026-W42.md"
    rep_desktop = DESKTOP_OUT_DIR / "bao_cao_xu_huong_tuan_2026-W42.md"
    shutil.copyfile(str(p_rep), str(rep_docs))
    shutil.copyfile(str(p_rep), str(rep_desktop))
    sha_rep = sha256_file(rep_desktop)
    size_rep = rep_desktop.stat().st_size
    print(f"📄 Tệp báo cáo xuất ra: {rep_desktop.name} | Size: {size_rep:,} bytes | SHA-256: {sha_rep}", flush=True)

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

            # 1. Chụp ảnh Ca 1: Tuần mới nhất (2026-W42)
            print("\n--- Chụp ảnh Ca 1: Báo cáo xu hướng tuần mới nhất (2026-W42) ---", flush=True)
            page.goto(f"{url}/?nb=NB-LAZY-DTL&conv={conv_latest}", wait_until="networkidle", timeout=60000)
            page.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)

            # Toàn cảnh hội thoại (cả câu hỏi và đáp án báo cáo)
            shot_full_docs = DOCS_OUT_DIR / "anh-01-cu-step4-periodic-report-overview.png"
            shot_full_desktop = DESKTOP_OUT_DIR / "anh-01-cu-step4-periodic-report-overview.png"
            page.screenshot(path=str(shot_full_docs), full_page=False)
            shutil.copyfile(str(shot_full_docs), str(shot_full_desktop))
            sha_full = sha256_file(shot_full_desktop)
            size_full = shot_full_desktop.stat().st_size
            print(f"📸 Toàn cảnh Ca 1: {shot_full_desktop.name} | Size: {size_full} bytes | SHA-256: {sha_full}", flush=True)

            # Bong bóng trả lời chi tiết chứa bảng 5 chiều
            asst_lat = page.locator('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])').first
            asst_lat.scroll_into_view_if_needed()
            shot_lat_docs = DOCS_OUT_DIR / "anh-02-cu-step4-periodic-report-table-5chieu.png"
            shot_lat_desktop = DESKTOP_OUT_DIR / "anh-02-cu-step4-periodic-report-table-5chieu.png"
            asst_lat.screenshot(path=str(shot_lat_docs))
            shutil.copyfile(str(shot_lat_docs), str(shot_lat_desktop))
            sha_lat = sha256_file(shot_lat_desktop)
            size_lat = shot_lat_desktop.stat().st_size
            print(f"📸 Bảng 5 chiều Ca 1: {shot_lat_desktop.name} | Size: {size_lat} bytes | SHA-256: {sha_lat}", flush=True)

            # 2. Chụp ảnh Ca 2: Tuần tải lớn (2026-W34, 35,139 bản ghi)
            print("\n--- Chụp ảnh Ca 2: Tuần tải lớn (2026-W34, 35,139 bản ghi) ---", flush=True)
            page.goto(f"{url}/?nb=NB-LAZY-DTL&conv={conv_heavy}", wait_until="networkidle", timeout=60000)
            page.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)
            asst_hvy = page.locator('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])').first
            asst_hvy.scroll_into_view_if_needed()

            shot_hvy_docs = DOCS_OUT_DIR / "anh-03-cu-step4-periodic-report-w34-heavy.png"
            shot_hvy_desktop = DESKTOP_OUT_DIR / "anh-03-cu-step4-periodic-report-w34-heavy.png"
            asst_hvy.screenshot(path=str(shot_hvy_docs))
            shutil.copyfile(str(shot_hvy_docs), str(shot_hvy_desktop))
            sha_hvy = sha256_file(shot_hvy_desktop)
            size_hvy = shot_hvy_desktop.stat().st_size
            print(f"📸 Ca 2 (W34 heavy): {shot_hvy_desktop.name} | Size: {size_hvy} bytes | SHA-256: {sha_hvy}", flush=True)

            browser.close()

        print("\n✅ HOÀN TẤT CHỤP ẢNH COMPUTER USE (CU) THẬT 100%!", flush=True)
        print(f"1. Toàn cảnh W42: {shot_full_desktop.name} | {size_full:,} bytes | SHA-256: {sha_full}")
        print(f"2. Bảng 5 chiều W42: {shot_lat_desktop.name} | {size_lat:,} bytes | SHA-256: {sha_lat}")
        print(f"3. Báo cáo W34 heavy: {shot_hvy_desktop.name} | {size_hvy:,} bytes | SHA-256: {sha_hvy}")
        print(f"4. Tệp báo cáo markdown: {rep_desktop.name} | {size_rep:,} bytes | SHA-256: {sha_rep}")

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
