# -*- coding: utf-8 -*-
"""Deterministic verification and UI screenshot capture for ticket DESKTOP-HOME-CASE-LABEL-VU-FIX.

1. Generates synthesized answer for C6770:
   - Verifies cards display 'Vụ <số>' with dynamic number format explanation.
   - Verifies 0 occurrences of 'Phiếu'.
   - Preserves Machine | Serial | Date and citation lines.
2. Generates Step 5 Recurrence Alert for C7620:
   - Verifies recurrence count is 136.
   - Verifies latest case uses 'vụ FY27H2/263' and '*(từ vụ `FY27H2/263`)*'.
3. Stores conversations and messages into workspace_chat_store.
4. Starts Streamlit server.
5. Launches headless Playwright browser to capture real UI screenshots:
   - anh-c6770-case-label-vu-evidence.png
   - anh-step5-recurrence-c7620-vu-evidence.png
6. Saves files to both docs/phieu-viec/ket-qua/ and aios-dieu-phoi-desktop/hop-thu/lan-desktop/ket-qua/.
7. Computes exact file size and SHA-256 for all submitted artifacts.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR / "src"))

from playwright.sync_api import sync_playwright

from aios_habit.chat_action import (
    ChatActionRequest,
    dispatch_multi,
    render_outcome,
)
from aios_habit.chat_action_error_lookup import (
    _open_ro,
    _render_synthesized_answer,
    explain_case_number,
    extract_codes,
    lookup_glossary,
    resolve_db_path,
    search_similar,
)
from aios_habit.workspace_chat_models import ChatMessage, WorkspaceConversation
from aios_habit.workspace_chat_store import (
    delete_conversation,
    save_conversation,
    save_message,
)

DOCS_OUT_DIR = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
DOCS_OUT_DIR.mkdir(parents=True, exist_ok=True)

DESKTOP_OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")
DESKTOP_OUT_DIR.mkdir(parents=True, exist_ok=True)


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def get_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def wait_for_server(port: int, proc: subprocess.Popen, timeout_sec: int = 50) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_sec:
        if proc.poll() is not None:
            print(f"Server exited early with code {proc.returncode}", flush=True)
            return False
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/_stcore/health")
            with urllib.request.urlopen(req, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def main() -> int:
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    conv_c6770 = "CONV-CASE-LABEL-VU-C6770"
    conv_step5 = "CONV-CASE-LABEL-VU-STEP5"

    delete_conversation(conv_c6770)
    delete_conversation(conv_step5)

    save_conversation(
        WorkspaceConversation(
            id=conv_c6770,
            notebook_id="NB-LAZY-DTL",
            title="Nghiệm thu Nhãn Vụ C6770",
            created_at=now_iso,
            updated_at=now_iso,
        )
    )
    save_conversation(
        WorkspaceConversation(
            id=conv_step5,
            notebook_id="NB-LAZY-DTL",
            title="Nghiệm thu Tái Phát Bước 5 C7620",
            created_at=now_iso,
            updated_at=now_iso,
        )
    )

    # 1. Sinh đáp án C6770
    q_c6770 = "Mã lỗi C6770 nguyên nhân là gì?"
    req_c6770 = ChatActionRequest(
        question=q_c6770,
        notebook_id="NB-LAZY-DTL",
    )
    conn_c6770 = _open_ro(resolve_db_path(req_c6770))
    codes = extract_codes(q_c6770)
    cases, _, total = search_similar(conn_c6770, q_c6770)
    gloss = lookup_glossary(conn_c6770, codes)
    text_c6770 = _render_synthesized_answer(cases, codes, gloss, total, q_c6770)
    conn_c6770.close()

    # Kiểm tra đáp án C6770
    assert "Vụ" in text_c6770, "Thiếu nhãn 'Vụ' trong thẻ ca!"
    assert "Phiếu" not in text_c6770, "Còn tồn tại chữ 'Phiếu' trong đáp án C6770!"
    assert "phiếu" not in text_c6770, "Còn tồn tại chữ 'phiếu' trong đáp án C6770!"
    assert "Số đăng ký vụ việc trong sổ gốc" in text_c6770, "Thiếu dòng giải thích dạng số đăng ký!"
    assert "- **Máy:**" in text_c6770, "Bị mất dòng Máy | Serial | Ngày!"
    assert "- **Báo cáo gốc:**" in text_c6770, "Bị mất dòng trích dẫn nguồn gốc!"

    save_message(
        ChatMessage(
            id="MSG-C6770-USER",
            conversation_id=conv_c6770,
            role="user",
            content=q_c6770,
            created_at=now_iso,
        )
    )
    save_message(
        ChatMessage(
            id="MSG-C6770-ASST",
            conversation_id=conv_c6770,
            role="assistant",
            content=text_c6770,
            created_at=now_iso,
        )
    )

    # 2. Sinh đáp án C7620 Cảnh báo tái phát Bước 5
    q_step5 = "Tạo vụ điều tra lỗi mới: kẹt giấy cụm sấy lỗi C7620"
    out_step5 = dispatch_multi(
        ChatActionRequest(
            question=q_step5,
            conversation_id=conv_step5,
            notebook_id="NB-LAZY-DTL",
        )
    )
    text_step5 = render_outcome(out_step5) if out_step5 else ""

    # Kiểm tra đáp án Bước 5 C7620
    assert "136" in text_step5, "Số lượng ca tái phát C7620 không khớp 136!"
    assert "vụ FY27H2/263" in text_step5, "Không dùng nhãn 'vụ FY27H2/263' cho ca gần nhất!"
    assert "(từ vụ `FY27H2/263`)" in text_step5, "Thiếu nhãn '(từ vụ `FY27H2/263`)'!"

    save_message(
        ChatMessage(
            id="MSG-STEP5-USER",
            conversation_id=conv_step5,
            role="user",
            content=q_step5,
            created_at=now_iso,
        )
    )
    save_message(
        ChatMessage(
            id="MSG-STEP5-ASST",
            conversation_id=conv_step5,
            role="assistant",
            content=text_step5,
            created_at=now_iso,
        )
    )

    print(">> Đã khởi tạo dữ liệu mẫu cho cả 2 kịch bản trong DB chat.", flush=True)

    # 3. Khởi động Streamlit Server
    port = find_free_port()
    url = f"http://127.0.0.1:{port}"
    print(f">> Khởi động Streamlit Server tại {url}...", flush=True)

    server_env = os.environ.copy()
    server_env["PYTHONPATH"] = "src"
    server_env["AIOS_FEATURE_CHAT_ACTION"] = "1"
    server_env["AIOS_ERROR_CASES_DB"] = r"C:\tmp\kdtps_standard\error_cases_reconciled.db"
    server_env["AIOS_RAGV2_WORKER_PERSIST"] = "1"
    server_env["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
    server_env["OMP_NUM_THREADS"] = "1"
    server_env["MKL_NUM_THREADS"] = "1"
    server_env["AIOS_RETRIEVAL_DEVICE"] = "cpu"
    server_env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    server_env["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
    server_env["STREAMLIT_SERVER_RUN_ON_SAVE"] = "false"
    server_env["STREAMLIT_SERVER_PORT"] = str(port)
    server_env["STREAMLIT_SERVER_HEADLESS"] = "true"

    py_exe = APP_DIR / ".venv" / "Scripts" / "python.exe"
    log_f = open(DOCS_OUT_DIR / "verify_case_label_vu_streamlit.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        [
            str(py_exe),
            "-m",
            "streamlit",
            "run",
            "src/aios_habit/workspace_chat_app.py",
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
            "--server.fileWatcherType",
            "none",
            "--server.runOnSave",
            "false",
        ],
        cwd=str(APP_DIR),
        env=server_env,
        stdout=log_f,
        stderr=subprocess.STDOUT,
    )

    if not wait_for_server(port, proc, timeout_sec=60):
        print("❌ Lỗi: Không thể khởi động Streamlit Server!", flush=True)
        proc.kill()
        log_f.close()
        return 1

    print(f"✅ Streamlit Server đã sẵn sàng tại {url}", flush=True)
    time.sleep(2)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1400, "height": 980})

            # 4. Chụp ảnh C6770
            print("\n--- Chụp ảnh Đáp án C6770: Nhãn Vụ + Dòng giải thích ---", flush=True)
            page.goto(f"{url}/?nb=NB-LAZY-DTL&conv={conv_c6770}", wait_until="networkidle", timeout=60000)
            page.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)
            time.sleep(1.5)

            sec4 = page.locator('text=Danh sách các ca điều tra thực tế đối chiếu').first
            if sec4.count() > 0:
                sec4.scroll_into_view_if_needed()
                page.evaluate("() => window.scrollBy(0, -30)")
            else:
                asst_c6770 = page.locator('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])').first
                asst_c6770.scroll_into_view_if_needed()
            time.sleep(1.0)

            shot1_docs = DOCS_OUT_DIR / "anh-c6770-case-label-vu-evidence.png"
            shot1_desktop = DESKTOP_OUT_DIR / "anh-c6770-case-label-vu-evidence.png"
            page.screenshot(path=str(shot1_docs))
            shutil.copyfile(str(shot1_docs), str(shot1_desktop))
            size1 = shot1_docs.stat().st_size
            sha1 = get_file_sha256(shot1_docs)
            print(f"📸 C6770: {shot1_docs.name} | Dung lượng: {size1:,} bytes | SHA-256: {sha1}", flush=True)

            # 5. Chụp ảnh Bước 5 C7620
            print("\n--- Chụp ảnh Thẻ Cảnh báo Tái phát Bước 5 C7620 ---", flush=True)
            page.goto(f"{url}/?nb=NB-LAZY-DTL&conv={conv_step5}", wait_until="networkidle", timeout=60000)
            page.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)
            time.sleep(1.5)

            step5_alert = page.locator('text=CẢNH BÁO TÁI PHÁT (Bước 5):').first
            if step5_alert.count() > 0:
                step5_alert.scroll_into_view_if_needed()
                page.evaluate("() => window.scrollBy(0, -60)")
            else:
                asst_step5 = page.locator('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])').first
                asst_step5.scroll_into_view_if_needed()
            time.sleep(1.0)

            shot2_docs = DOCS_OUT_DIR / "anh-step5-recurrence-c7620-vu-evidence.png"
            shot2_desktop = DESKTOP_OUT_DIR / "anh-step5-recurrence-c7620-vu-evidence.png"
            page.screenshot(path=str(shot2_docs))
            shutil.copyfile(str(shot2_docs), str(shot2_desktop))
            size2 = shot2_docs.stat().st_size
            sha2 = get_file_sha256(shot2_docs)
            print(f"📸 Step 5: {shot2_docs.name} | Dung lượng: {size2:,} bytes | SHA-256: {sha2}", flush=True)

            browser.close()

            # Ghi báo cáo JSON
            manifest = {
                "ticket": "DESKTOP-HOME-CASE-LABEL-VU-FIX",
                "timestamp": now_iso,
                "evidence_files": [
                    {
                        "filename": shot1_docs.name,
                        "path": str(shot1_desktop),
                        "size_bytes": size1,
                        "sha256": sha1,
                        "description": "Ảnh giao diện thật đáp án C6770: mọi thẻ ca mang nhãn 'Vụ <số>' kèm dòng giải thích số đăng ký sổ gốc, không còn chữ 'Phiếu'",
                    },
                    {
                        "filename": shot2_docs.name,
                        "path": str(shot2_desktop),
                        "size_bytes": size2,
                        "sha256": sha2,
                        "description": "Ảnh giao diện thật Thẻ xem trước Bước 5 C7620: cảnh báo tái phát 136 ca, vụ gần nhất FY27H2/263",
                    },
                ],
                "acceptance_results": {
                    "c6770_has_vu_label": True,
                    "c6770_has_explanation_line": True,
                    "c6770_zero_phieu_occurrences": True,
                    "c6770_provenance_intact": True,
                    "step5_c7620_recurrence_count": 136,
                    "step5_c7620_latest_case_ref": "FY27H2/263",
                    "step5_c7620_has_vu_label": True,
                },
            }

            json_docs = DOCS_OUT_DIR / "verification_case_label_vu.json"
            json_desktop = DESKTOP_OUT_DIR / "verification_case_label_vu.json"
            json_docs.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            shutil.copyfile(str(json_docs), str(json_desktop))
            print(f"✅ Ghi manifest kiểm chứng: {json_desktop}", flush=True)

    finally:
        print(">> Đang dừng Streamlit Server...", flush=True)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        log_f.close()
        print("✅ Streamlit Server đã dừng.", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
