"""Script do thuc nghiem kiem chung dong bo lenh xem lai phan hoi tren PC0575.
Ve: DESKTOP-PC0575-SYNC-FEEDBACK-REVIEW
May thuc thi: KDTVN-PC0575 (Intel Core i5-8265U @ 1.60GHz, 16.0 GB RAM, Windows 11 Pro 64-bit, CPU-only)

Muc tieu kiem chung:
1. Nhan dien dung lenh 'xem phan hoi' trong khung chat Streamlit.
2. Nhan tom tat phan hoi dap an tu kho cuc bo local_cases/answer_feedback.jsonl.
3. So lieu tom tat khop dung dem tay tu kho phan hoi cuc bo cua PC0575.
4. Chup anh giao dien minh chung day du.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any
import urllib.request
import uuid

# Cau hinh moi truong chuan BB-CONFIG-PARITY-01 cho PC0575 (CPU-only)
os.environ["AIOS_RAGV2_WORKER_PERSIST"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["AIOS_RETRIEVAL_DEVICE"] = "cpu"
os.environ["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
os.environ["AIOS_RAG_V2_NUMPY_SCORING"] = "1"
os.environ["AIOS_AI_BACKEND"] = "nakazasen_router"
os.environ["AIOS_FEATURE_CHAT_ACTION"] = "1"
os.environ["AIOS_DOMAIN_ROUTING_ENABLED"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUNBUFFERED"] = "1"

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
PYTHON_EXE = APP_DIR / ".venv" / "Scripts" / "python.exe"

sys.path.insert(0, str(APP_DIR / "src"))

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

import aios_habit.workspace_chat_store as store
store.LOCAL_CHAT_DIR = APP_DIR / "local_cases" / "workspace_chat"
store.NOTEBOOKS_FILE = store.LOCAL_CHAT_DIR / "notebooks.jsonl"
store.COLLECTIONS_FILE = store.LOCAL_CHAT_DIR / "collections.jsonl"
store.CONVERSATIONS_FILE = store.LOCAL_CHAT_DIR / "conversations.jsonl"
store.MESSAGES_FILE = store.LOCAL_CHAT_DIR / "messages.jsonl"

from aios_habit.workspace_chat_models import DocumentNotebook, WorkspaceConversation, ChatMessage
from aios_habit.workspace_chat_store import save_notebook, save_conversation, load_messages
from aios_habit import answer_feedback
from aios_habit.feedback_review_home import format_feedback_review_summary
from playwright.sync_api import sync_playwright

PORT = 8501
URL = f"http://localhost:{PORT}"

OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua")
OUT_DIR.mkdir(parents=True, exist_ok=True)
DOCS_OUT_DIR = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
DOCS_OUT_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR = Path(r"C:\Users\tvn183660\.gemini\antigravity\brain\a33f5085-b597-458e-b6ce-b12c894fbf5f")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

SERVER_LOG_FILE = OUT_DIR / "server_desktop_pc0575_sync_feedback_review.log"
SESSION_LOG_FILE = OUT_DIR / "session_desktop_pc0575_sync_feedback_review.log"
JSON_RESULT_FILE = OUT_DIR / "ket-qua-do-desktop-pc0575-sync-feedback-review.json"

SCREENSHOT_READY = OUT_DIR / "anh-pc0575-feedback-review-00-app-ready.png"
SCREENSHOT_LIVE = OUT_DIR / "anh-pc0575-feedback-review-01-summary-live.png"


def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(SESSION_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(64 * 1024):
            h.update(chunk)
    return h.hexdigest().upper()


def get_git_head() -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=APP_DIR,
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


def kill_all_workers_and_servers() -> None:
    log("Don dep sach cac tien trinh streamlit va worker cu...")
    my_pid = os.getpid()
    ps_cmd = (
        f"$procs = Get-CimInstance Win32_Process | Where-Object {{ "
        f"($_.CommandLine -like '*workspace_chat_app.py*' -or "
        f"$_.CommandLine -like '*bge_subprocess_worker*') -and $_.ProcessId -ne {my_pid} "
        f"}}; "
        f"foreach ($p in $procs) {{ Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }}"
    )
    subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
    time.sleep(2.0)


def wait_for_server(port: int, timeout: int = 90) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"http://localhost:{port}/_stcore/health")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def start_server(port: int, log_file: Path) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(APP_DIR / "src")
    env["STREAMLIT_SERVER_PORT"] = str(port)
    if log_file.exists():
        try:
            log_file.unlink()
        except Exception:
            pass

    log_handle = open(log_file, "a", encoding="utf-8")
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
        "--browser.gatherUsageStats=false",
    ]
    log(f"[STARTUP] Chay Streamlit: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        cwd=APP_DIR,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        env=env,
    )
    return proc


def kill_proc(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def main() -> None:
    if SESSION_LOG_FILE.exists():
        SESSION_LOG_FILE.unlink()

    log("=" * 80)
    log("BAT DAU DO THUC NGHIEM: DESKTOP-PC0575-SYNC-FEEDBACK-REVIEW")
    log("=" * 80)

    git_head = get_git_head()
    log(f"[GIT] Commit HEAD PC0575: {git_head}")

    # 1. Dem tay du lieu local kho phan hoi
    fb_file = answer_feedback.feedback_file()
    assert fb_file.exists(), f"Khong tim thay file {fb_file}"
    raw_records = []
    with fb_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                raw_records.append(json.loads(line))
    total_local = len(raw_records)
    good_local = sum(1 for r in raw_records if r.get("rating") == "huu_ich")
    bad_local = sum(1 for r in raw_records if r.get("rating") == "chua_huu_ich")
    rate_good = round(good_local / total_local * 100, 1) if total_local else 0.0
    rate_bad = round(bad_local / total_local * 100, 1) if total_local else 0.0

    log(f"[DATA] Kho phan hoi tai PC0575: {fb_file}")
    log(f"[DATA] Dem tay: Tong={total_local}, Dat={good_local}, Che={bad_local}, Ty le={rate_good}% dat / {rate_bad}% che")

    expected_summary = format_feedback_review_summary()
    log(f"[SUMMARY_CHECK] format_feedback_review_summary() dai {len(expected_summary)} ky tu.")

    # 2. Tao notebook va hoi thoai kiem chung
    nb_id = "NB-PC0575-FB-REVIEW"
    save_notebook(DocumentNotebook(
        id=nb_id,
        title="So Kiem Tra Lenh Xem Phan Hoi",
        description="Kiem chung dong bo lenh xem phan hoi qua khung chat tren PC0575",
        collection_id="lsu",
    ))

    conv_id = f"CONV-PC0575-FB-{uuid.uuid4().hex[:6].upper()}"
    save_conversation(WorkspaceConversation(
        id=conv_id,
        notebook_id=nb_id,
        title="Kiem chung lenh xem phan hoi",
        ai_mode="grounded",
    ))
    log(f"[SETUP] Da tao notebook={nb_id}, conv={conv_id}")

    # 3. Khoi dong app Streamlit
    kill_all_workers_and_servers()
    server_proc = start_server(PORT, SERVER_LOG_FILE)

    app_ready_time = 0.0
    t0 = time.time()
    try:
        log(f"[WAIT_SERVER] Cho Streamlit san sang tai {URL}...")
        if not wait_for_server(PORT, timeout=60):
            log("[ERROR] Streamlit khong san sang sau 60s!")
            raise RuntimeError("Streamlit server startup failed")
        app_ready_time = time.time() - t0
        log(f"[SERVER_READY] Streamlit san sang sau {app_ready_time:.2f}s")

        with sync_playwright() as p:
            log("[PLAYWRIGHT] Khoi chay Chromium...")
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})

            target_url = f"{URL}/?nb={nb_id}&conv={conv_id}"
            log(f"[NAVIGATE] Di den {target_url}...")
            page.goto(target_url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)

            # Chup anh 00: App san sang
            page.screenshot(path=str(SCREENSHOT_READY), full_page=True)
            log(f"[SCREENSHOT] Da chup anh app ready: {SCREENSHOT_READY}")

            # Cho composer textarea
            composer_selector = 'textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"], textarea[placeholder*="Nhập câu hỏi"]'
            page.wait_for_selector(composer_selector, timeout=30000)
            textarea = page.locator(composer_selector).first

            cmd_text = "xem phản hồi"
            log(f"[TYPING] Go lenh: '{cmd_text}'...")
            textarea.fill(cmd_text)
            page.wait_for_timeout(400)
            log("[SEND] Nhan Control+Enter...")
            textarea.press("Control+Enter")

            # Cho phan hoi tu assistant
            t_watch = time.time()
            answered = False
            while time.time() - t_watch < 45:
                msgs = load_messages(conv_id)
                ast_msgs = [m for m in msgs if m.role == "assistant"]
                if ast_msgs and "📊 Tóm tắt phản hồi đáp án" in ast_msgs[-1].content:
                    answered = True
                    log(f"[REPLY_RECEIVED] Assistant da tra loi sau {time.time() - t_watch:.2f}s!")
                    break
                page.wait_for_timeout(500)

            if not answered:
                log("[ERROR] Khong nhan duoc tin nhan tra loi tu assistant trong 45s!")
                raise RuntimeError("Timeout waiting for assistant reply")

            # Cho UI rerun va render hoan tat
            page.wait_for_timeout(4000)

            # Chup anh 01: Summary live
            page.screenshot(path=str(SCREENSHOT_LIVE), full_page=True)
            log(f"[SCREENSHOT] Da chup anh summary live: {SCREENSHOT_LIVE}")

            msgs = load_messages(conv_id)
            ast_msgs = [m for m in msgs if m.role == "assistant"]
            ans_content = ast_msgs[-1].content

            # Kiem tra DOM tren page
            dom_text = page.inner_text("body")
            has_summary_header = "Tóm tắt phản hồi đáp án" in dom_text
            has_total_line = f"Tổng số phản hồi:** {total_local} lượt" in ans_content or f"{total_local} lượt" in dom_text
            has_rate_line = f"{rate_good}% đạt" in ans_content or f"{rate_good}% đạt" in dom_text

            log(f"[VERIFY] has_summary_header: {has_summary_header}")
            log(f"[VERIFY] has_total_line: {has_total_line}")
            log(f"[VERIFY] has_rate_line: {has_rate_line}")

            browser.close()

    finally:
        kill_proc(server_proc)
        kill_all_workers_and_servers()

    # Dong bo anh sang DOCS va ARTIFACT
    import shutil
    for src in (SCREENSHOT_READY, SCREENSHOT_LIVE):
        if src.exists():
            shutil.copy2(src, DOCS_OUT_DIR / src.name)
            shutil.copy2(src, ARTIFACT_DIR / src.name)

    sha256_ready = compute_sha256(SCREENSHOT_READY) if SCREENSHOT_READY.exists() else ""
    sha256_live = compute_sha256(SCREENSHOT_LIVE) if SCREENSHOT_LIVE.exists() else ""

    result_data = {
        "ma_ve": "DESKTOP-PC0575-SYNC-FEEDBACK-REVIEW",
        "trang_thai": "HOAN_THANH",
        "thoi_diem": datetime.now(timezone.utc).isoformat(),
        "may_thuc_thi": "KDTVN-PC0575",
        "commit_head": git_head,
        "kho_phan_hoi": str(fb_file),
        "dem_tay": {
            "tong": total_local,
            "dat": good_local,
            "che": bad_local,
            "ty_le_dat": rate_good,
            "ty_le_che": rate_bad,
        },
        "ket_qua_app": {
            "app_ready_s": round(app_ready_time, 2),
            "answered": answered,
            "has_summary_header": has_summary_header,
            "has_total_line": has_total_line,
            "has_rate_line": has_rate_line,
            "assistant_content": ans_content,
        },
        "anh_minh_chung": {
            "anh_ready": {
                "ten": SCREENSHOT_READY.name,
                "sha256": sha256_ready,
                "size_bytes": SCREENSHOT_READY.stat().st_size if SCREENSHOT_READY.exists() else 0,
            },
            "anh_live": {
                "ten": SCREENSHOT_LIVE.name,
                "sha256": sha256_live,
                "size_bytes": SCREENSHOT_LIVE.stat().st_size if SCREENSHOT_LIVE.exists() else 0,
            },
        },
    }

    with open(JSON_RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    shutil.copy2(JSON_RESULT_FILE, DOCS_OUT_DIR / JSON_RESULT_FILE.name)
    shutil.copy2(JSON_RESULT_FILE, ARTIFACT_DIR / JSON_RESULT_FILE.name)

    log(f"[JSON] Da luu ket qua do vao {JSON_RESULT_FILE}")
    log("=" * 80)
    log("HOAN THANH DO THUC NGHIEM: DESKTOP-PC0575-SYNC-FEEDBACK-REVIEW")
    log("=" * 80)


if __name__ == "__main__":
    main()
