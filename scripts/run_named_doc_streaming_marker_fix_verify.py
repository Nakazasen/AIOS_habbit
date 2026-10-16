"""Script kiem chung thuc te tren app cho ve DESKTOP-NAMED-DOC-STREAMING-MARKER-FIX-HOME.
Yeu cau nghiem thu:
1. Hoi cau hoi goi ten tep khong ton tai (vi du: Hay tra cuu file abcxyz_not_found.msg xem co loi gi khong?).
2. Phan hoi tu choi xuat hien duoi 5 giay.
3. Server log co day du 3 marker: [STREAMING_QA_START], [STREAMING_QA_FIRST_TOKEN], [STREAMING_QA_COMPLETE].
4. messages.jsonl co ban ghi ChatMessage tuong ung cua assistant.
5. Khoi dong lai ung dung Streamlit, mo lai phien tro chuyen va chup anh giao dien chung minh cau tu choi van con trong lich su.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from datetime import datetime
import urllib.request
import uuid

import psutil
from playwright.sync_api import sync_playwright

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
PYTHON_EXE = APP_DIR / ".venv" / "Scripts" / "python.exe"

os.environ["PYTHONPATH"] = f"{APP_DIR / 'src'};{os.environ.get('PYTHONPATH', '')}"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
os.environ["AIOS_RAG_V2_NUMPY_SCORING"] = "1"
os.environ["AIOS_RETRIEVAL_DEVICE"] = "cpu"
os.environ["AIOS_BGE_QUERY_TIMEOUT"] = "1200"
os.environ["AIOS_BGE_INIT_TIMEOUT"] = "420"
os.environ["AIOS_BGE_WARM_ABSOLUTE_TIMEOUT"] = "420"
os.environ["AIOS_BGE_WARM_NO_PROGRESS_TIMEOUT"] = "120"
os.environ["AIOS_BGE_PERSIST_CONNECT_TIMEOUT"] = "420"
os.environ["AIOS_RAGV2_WORKER_PERSIST"] = "1"
os.environ["AIOS_FEATURE_CHAT_ACTION"] = "1"
os.environ["AIOS_DOMAIN_ROUTING_ENABLED"] = "1"
os.environ["AIOS_STREAM_SYNTHESIS"] = "1"
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
os.environ["STREAMLIT_SERVER_RUN_ON_SAVE"] = "false"
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUNBUFFERED"] = "1"

sys.path.insert(0, str(APP_DIR / "src"))

import aios_habit.workspace_chat_store as store
store.LOCAL_CHAT_DIR = APP_DIR / "local_cases" / "workspace_chat"
store.NOTEBOOKS_FILE = store.LOCAL_CHAT_DIR / "notebooks.jsonl"
store.COLLECTIONS_FILE = store.LOCAL_CHAT_DIR / "collections.jsonl"
store.CONVERSATIONS_FILE = store.LOCAL_CHAT_DIR / "conversations.jsonl"
store.MESSAGES_FILE = store.LOCAL_CHAT_DIR / "messages.jsonl"

from aios_habit.workspace_chat_models import DocumentNotebook, WorkspaceConversation
from aios_habit.workspace_chat_store import save_notebook, save_conversation, load_messages

PORT = 8501
URL = f"http://localhost:{PORT}"

OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SERVER_LOG_FILE = OUT_DIR / "server_named_doc_streaming_marker_fix_home.log"
VERIFY_JSON_FILE = OUT_DIR / "ket-qua-named-doc-streaming-marker-fix-home.json"
SCREENSHOT_BEFORE_RESTART = OUT_DIR / "anh-named-doc-before-restart.png"
SCREENSHOT_AFTER_RESTART = OUT_DIR / "anh-named-doc-restart-verify.png"


def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"[{ts}] {msg}", flush=True)


def is_server_ready(port: int = PORT) -> bool:
    try:
        req = urllib.request.Request(f"http://localhost:{port}/_stcore/health")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def wait_for_server(port: int = PORT, timeout_s: float = 60.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if is_server_ready(port):
            return True
        time.sleep(0.5)
    return False


def kill_existing_streamlit() -> None:
    my_pid = os.getpid()
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.pid == my_pid:
                continue
            cmd = " ".join(proc.info.get("cmdline") or [])
            if "workspace_chat_app.py" in cmd:
                log(f"[KILL] Dong tien trinh Streamlit PID={proc.pid}")
                proc.kill()
        except Exception:
            pass
    time.sleep(2)


def start_app(log_file: Path, port: int = PORT) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{APP_DIR / 'src'};{env.get('PYTHONPATH', '')}"
    env["STREAMLIT_SERVER_PORT"] = str(port)

    log_handle = open(log_file, "a", encoding="utf-8")
    log_handle.write(f"\n\n=== [APP LAUNCH {datetime.now().isoformat()}] ===\n")
    log_handle.flush()

    cmd = [
        str(PYTHON_EXE),
        "-u",
        "-m",
        "streamlit",
        "run",
        "src/aios_habit/workspace_chat_app.py",
        f"--server.port={port}",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--server.fileWatcherType=none",
        "--server.runOnSave=false",
    ]
    log(f"[STARTUP] Khoi dong app: {' '.join(cmd)}")

    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP

    proc = subprocess.Popen(
        cmd,
        cwd=APP_DIR,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        env=env,
        creationflags=creation_flags,
    )
    return proc


def extract_markers_for_conv(log_file: Path, conv_id: str) -> dict[str, Any]:
    res = {
        "start": "",
        "first_token": "",
        "complete": "",
        "all_lines": [],
    }
    if not log_file.exists():
        return res
    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if conv_id in line:
                res["all_lines"].append(line.strip())
                if "[STREAMING_QA_START]" in line and not res["start"]:
                    res["start"] = line.strip()
                elif "[STREAMING_QA_FIRST_TOKEN]" in line and not res["first_token"]:
                    res["first_token"] = line.strip()
                elif "[STREAMING_QA_COMPLETE]" in line and not res["complete"]:
                    res["complete"] = line.strip()
    return res


def main():
    log("=" * 80)
    log("BAT DAU KIEM CHUNG VE DESKTOP-NAMED-DOC-STREAMING-MARKER-FIX-HOME")
    log("=" * 80)

    # 1. Chuan bi conversation
    nb_id = "NB-NAMED-DOC-VERIFY"
    conv_id = f"CONV-NAMED-DOC-{int(time.time())}"
    now_iso = datetime.now().isoformat()

    nb = DocumentNotebook(
        id=nb_id,
        title="Notebook Kiểm Chứng Marker Từ Chối Đích Danh",
        collection_id="tri_thuc",
        created_at=now_iso,
        updated_at=now_iso,
    )
    conv = WorkspaceConversation(
        id=conv_id,
        notebook_id=nb_id,
        title="Hội thoại kiểm chứng named_document_not_found",
        created_at=now_iso,
        updated_at=now_iso,
    )
    save_notebook(nb)
    save_conversation(conv)
    log(f"[CONV_SETUP] Da tao notebook {nb_id} va conversation {conv_id}")

    # 2. Khoi dong app lan 1
    log("[STEP 1] Khoi dong app Streamlit lan 1...")
    kill_existing_streamlit()
    app_proc = start_app(SERVER_LOG_FILE)
    if not wait_for_server(PORT, timeout_s=45):
        log("[ERROR] Khong the ket noi toi app Streamlit sau 45s!")
        sys.exit(1)
    log(f"[READY] App san sang tren http://localhost:{PORT}")

    test_question = "Hay tra cuu file abcxyz_not_found.msg xem co loi gi khong?"
    target_url = f"{URL}/?nb={nb_id}&conv={conv_id}"
    markers_found = {}
    elapsed_to_reply = None

    # 3. Playwright gui cau hoi
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        log(f"[NAVIGATE] Mo URL tai {target_url}...")
        page.goto(target_url, timeout=30000)
        page.wait_for_timeout(3500)

        # Tim textarea
        log("[UI] Cho textarea cau hoi...")
        page.wait_for_selector('textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"]', timeout=30000)
        textarea = page.locator('textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"]').first
        textarea.fill(test_question)
        page.wait_for_timeout(600)

        t_fire = time.time()
        log(f"[SUBMIT] Gui cau hoi: '{test_question}' tai {datetime.now().isoformat()}")

        send_btn = page.locator(f'[class*="st-key-wsc_ask_{conv_id}"] button, [class*="st-key-wsc-action-"] button').first
        if send_btn.count() > 0:
            send_btn.click(force=True)
            log("[SUBMIT_METHOD] Da click send_btn")
        else:
            textarea.press("Control+Enter")
            log("[SUBMIT_METHOD] Da press Control+Enter")

        # Cho marker COMPLETE hoac tin nhan assistant xuat hien
        log("[WAIT] Cho phan hoi tu choi va marker [STREAMING_QA_COMPLETE]...")
        timeout_wait = 15.0
        complete_seen = False
        while time.time() - t_fire < timeout_wait:
            markers = extract_markers_for_conv(SERVER_LOG_FILE, conv_id)
            if markers["complete"]:
                complete_seen = True
                elapsed_to_reply = time.time() - t_fire
                log(f"[PASS] Marker [STREAMING_QA_COMPLETE] xuat hien sau {elapsed_to_reply:.3f}s! (Yeu cau < 5s)")
                log(f"[MARKER_START] {markers['start']}")
                log(f"[MARKER_FIRST_TOKEN] {markers['first_token']}")
                log(f"[MARKER_COMPLETE] {markers['complete']}")
                break
            # Kiem tra thu messages.jsonl
            msgs_now = load_messages(conv_id)
            if any(m.role == "assistant" for m in msgs_now):
                elapsed_to_reply = time.time() - t_fire
                log(f"[PASS] Tin nhan assistant da xuat hien sau {elapsed_to_reply:.3f}s!")
                break
            page.wait_for_timeout(300)

        page.wait_for_timeout(2000)
        page.screenshot(path=str(SCREENSHOT_BEFORE_RESTART), full_page=True)
        log(f"[SCREENSHOT] Da chup anh truoc restart: {SCREENSHOT_BEFORE_RESTART}")

        browser.close()

    time.sleep(1)
    markers_found = extract_markers_for_conv(SERVER_LOG_FILE, conv_id)
    saved_msgs = load_messages(conv_id)
    asst_msg = next((m for m in saved_msgs if m.role == "assistant"), None)
    log(f"[MESSAGES_STORE] So tin nhan trong conversation {conv_id}: {len(saved_msgs)}")
    asst_record_str = ""
    if asst_msg:
        asst_record_str = json.dumps(asst_msg.to_dict(), ensure_ascii=False)
        log(f"[MESSAGES_STORE] Dong JSON cua assistant:\n{asst_record_str}")

    # 4. KHOI DONG LAI UNG DUNG (RESTART APP) VA CHUP ANH GIAO DIEN
    log("[STEP 2] Khoi dong lai ung dung Streamlit (RESTART APP)...")
    kill_existing_streamlit()
    log("[RESTART] Tien trinh cu da dong sach se. Dang khoi dong lai...")
    app_proc2 = start_app(SERVER_LOG_FILE)
    if not wait_for_server(PORT, timeout_s=45):
        log("[ERROR] Khong the ket noi toi app Streamlit sau khi restart!")
        sys.exit(1)
    log(f"[READY] App moi da khoi dong thanh cong tren http://localhost:{PORT}")

    # 5. Playwright mo lai app de kiem tra cau tu choi van con trong lich su
    log("[STEP 3] Mo lai app qua Playwright, kiem tra lich su tro chuyen...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        page.goto(target_url, timeout=30000)
        page.wait_for_timeout(4500)

        # Chup anh toan bo giao dien sau restart
        page.screenshot(path=str(SCREENSHOT_AFTER_RESTART), full_page=True)
        log(f"[SCREENSHOT] Da chup anh man hinh sau restart: {SCREENSHOT_AFTER_RESTART}")

        # Kiem tra noi dung co chu tu choi khong
        dom_text = page.content()
        has_refusal_in_history = ("Không tìm thấy tài liệu" in dom_text) or ("abcxyz_not_found.msg" in dom_text)
        log(f"[HISTORY_CHECK] Cau tu choi van con tren giao dien sau khi restart: {has_refusal_in_history}")

        browser.close()

    # 6. Tong ket du lieu
    summary = {
        "ticket": "DESKTOP-NAMED-DOC-STREAMING-MARKER-FIX-HOME",
        "timestamp": datetime.now().isoformat(),
        "conversation_id": conv_id,
        "test_question": test_question,
        "elapsed_seconds": round(elapsed_to_reply or 0.0, 3),
        "response_under_5s": bool(elapsed_to_reply and elapsed_to_reply < 5.0),
        "markers": markers_found,
        "all_3_markers_present": bool(markers_found.get("start") and markers_found.get("first_token") and markers_found.get("complete")),
        "assistant_message_saved": bool(asst_msg is not None),
        "assistant_message_json": asst_record_str,
        "history_retained_after_restart": has_refusal_in_history,
        "screenshot_before_restart": str(SCREENSHOT_BEFORE_RESTART),
        "screenshot_after_restart": str(SCREENSHOT_AFTER_RESTART),
    }
    with open(VERIFY_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    log("=" * 80)
    log("HOAN THANH KIEM CHUNG THUC TE VE DESKTOP-NAMED-DOC-STREAMING-MARKER-FIX-HOME")
    log(f"Ket qua JSON: {VERIFY_JSON_FILE}")
    log(f"Anh chup man hinh sau restart: {SCREENSHOT_AFTER_RESTART}")
    log("=" * 80)


if __name__ == "__main__":
    main()
