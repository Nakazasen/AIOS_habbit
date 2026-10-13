"""Nghiem thu song dung trinh tu chan doan cho ve DESKTOP-SPEED-PROFILE-QUERY-FIX-HOME.
May dich: MAY NHA (h410asrock, CPU-only).

Quy trinh:
1. Tat sach toan bo worker named pipe va server cu.
2. Khoi dong app Streamlit (cong 8570) voi cau hinh BB-CONFIG-PARITY-01.
3. Trong khi lam am khoi dong con dang chay:
   - Ban ngay luot C7620 khoi lsu tren giao dien that Playwright.
   - Kiem tra: QA_START -> RETRIEVAL_MICRO_TIMING <= 60s, luot hoan tat co MICRO that + dap an.
   - Ban tiep luot JAM4212 khoi dieu_tra_loi tuong tu.
4. Ghi lai nhat ky server, session log va anh chup giao dien vao hop-thu/lan-desktop/ket-qua/.
"""
from __future__ import annotations

from datetime import datetime
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request
import uuid

# Set persistent worker environment BEFORE imports/runtime
os.environ["AIOS_RAGV2_WORKER_PERSIST"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["AIOS_RETRIEVAL_DEVICE"] = "cpu"
os.environ["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
os.environ["AIOS_RAG_V2_NUMPY_SCORING"] = "1"
os.environ["AIOS_BGE_QUERY_TIMEOUT"] = "1200"
os.environ["AIOS_BGE_INIT_TIMEOUT"] = "420"
os.environ["AIOS_BGE_WARM_ABSOLUTE_TIMEOUT"] = "420"
os.environ["AIOS_BGE_WARM_NO_PROGRESS_TIMEOUT"] = "120"
os.environ["AIOS_BGE_PERSIST_CONNECT_TIMEOUT"] = "420"
os.environ["AIOS_AI_BACKEND"] = "nakazasen_router"
os.environ["AIOS_FEATURE_CHAT_ACTION"] = "1"
os.environ["AIOS_DOMAIN_ROUTING_ENABLED"] = "1"
os.environ["AIOS_STREAM_SYNTHESIS"] = "1"
os.environ["AIOS_FEATURE_ANSWER_DRAFT_FALLBACK"] = "1"
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

from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import save_conversation, load_messages
from aios_habit.streaming_markers import diff_marker_timestamps_s
from playwright.sync_api import sync_playwright

PORT = 8570
URL = f"http://localhost:{PORT}"
NOTEBOOK_ID_LSU = "NB-C26E1C84"

OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SERVER_LOG_FILE = OUT_DIR / "server_desktop_speed_profile_query_verify_home.log"
SESSION_LOG_FILE = OUT_DIR / "session_desktop_speed_profile_query_verify_home.log"
SCREENSHOT_C7620 = OUT_DIR / "anh-profile-fix-c7620.png"
SCREENSHOT_JAM4212 = OUT_DIR / "anh-profile-fix-jam4212.png"

QUESTION_C7620 = "Mã lỗi C7620 trên dòng máy in Kyocera là lỗi gì, nguyên nhân và đối sách xử lý ra sao?"
QUESTION_JAM4212 = "Mã kẹt giấy JAM 4212 trên máy Kyocera là gì, vị trí kẹt và cách xử lý?"


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(SESSION_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_git_head() -> str:
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=APP_DIR, capture_output=True, text=True)
        return res.stdout.strip()
    except Exception:
        return "unknown"


def kill_all_workers_and_servers():
    log("Don dep sach toan bo tien trinh streamlit va bge_subprocess_worker cu...")
    my_pid = os.getpid()
    ps_cmd = (
        f"$procs = Get-CimInstance Win32_Process | Where-Object {{ "
        f"($_.CommandLine -like '*bge_subprocess_worker*' -or "
        f"$_.CommandLine -like '*workspace_chat_app.py*') -and $_.ProcessId -ne 16092 -and $_.ProcessId -ne {my_pid} "
        f"}}; "
        f"foreach ($p in $procs) {{ Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }}"
    )
    subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
    time.sleep(2.0)
    log("Da don dep sach cac tien trinh cu.")


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
        time.sleep(1)
    return False


def start_server(port: int, log_file: Path) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(APP_DIR / "src")
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    env["AIOS_RETRIEVAL_DEVICE"] = "cpu"
    env["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
    env["AIOS_RAG_V2_NUMPY_SCORING"] = "1"
    env["AIOS_BGE_QUERY_TIMEOUT"] = "1200"
    env["AIOS_BGE_INIT_TIMEOUT"] = "420"
    env["AIOS_BGE_WARM_ABSOLUTE_TIMEOUT"] = "420"
    env["AIOS_BGE_WARM_NO_PROGRESS_TIMEOUT"] = "120"
    env["AIOS_BGE_PERSIST_CONNECT_TIMEOUT"] = "420"
    env["AIOS_RAGV2_WORKER_PERSIST"] = "1"
    env["AIOS_FEATURE_CHAT_ACTION"] = "1"
    env["AIOS_DOMAIN_ROUTING_ENABLED"] = "1"
    env["AIOS_STREAM_SYNTHESIS"] = "1"
    env["AIOS_FEATURE_ANSWER_DRAFT_FALLBACK"] = "1"
    env["AIOS_AI_BACKEND"] = "nakazasen_router"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
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
        "--browser.gatherUsageStats=false",
    ]
    log(f"[STARTUP] Chay lenh: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        cwd=APP_DIR,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        env=env,
    )
    return proc


def kill_server(proc: subprocess.Popen):
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def run_single_turn(
    page,
    conv_id: str,
    conv_title: str,
    block: str,
    question: str,
    screenshot_file: Path,
) -> dict:
    log(f"--- BAT DAU LUOT: {conv_title} (block={block}, conv={conv_id}) ---")
    save_conversation(WorkspaceConversation(
        id=conv_id,
        notebook_id=NOTEBOOK_ID_LSU,
        title=conv_title,
        ai_mode="grounded",
    ))

    nav_url = f"{URL}/?nb={NOTEBOOK_ID_LSU}&conv={conv_id}&block={block}"
    log(f"[NAV] Dieu huong toi: {nav_url}")
    page.goto(nav_url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(2000)

    page.wait_for_selector('textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"]', timeout=45000)
    textarea = page.locator('textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"]').first
    textarea.wait_for(state="visible", timeout=30000)
    textarea.click()
    textarea.fill(question)
    page.wait_for_timeout(500)

    log(f"[SUBMIT] Gui cau hoi: '{question[:50]}...'")
    t_submit = time.time()
    send_btn = page.locator(f'[class*="st-key-wsc_ask_{conv_id}"] button, [class*="st-key-wsc-action-"] button').first
    if send_btn.count() > 0:
        send_btn.click(force=True)
    else:
        textarea.press("Control+Enter")

    # Cho tin nhan luu vao DB
    for attempt in range(25):
        time.sleep(1.0)
        msgs = load_messages(conv_id)
        if any(m.role == "user" for m in msgs):
            log(f"[DB] User message da luu sau {attempt+1}s")
            break
        if attempt == 8:
            try:
                val = textarea.input_value()
                if val:
                    log("[DB] Textarea van con text sau 8s, thu gui lai...")
                    if send_btn.count() > 0:
                        send_btn.first.click(force=True)
                    else:
                        textarea.press("Control+Enter")
            except Exception:
                pass

    # Cho STREAMING_QA_START, RETRIEVAL_MICRO_TIMING va hoan tat luot
    t_qa_start = None
    t_micro = None
    t_complete = None
    qa_start_line = ""
    micro_line = ""
    complete_line = ""

    t_watch_start = time.time()
    in_conv_window = False
    while time.time() - t_watch_start < 240:
        if SERVER_LOG_FILE.exists():
            log_text = SERVER_LOG_FILE.read_text(encoding="utf-8", errors="replace")
            lines = log_text.splitlines()
            for line in lines:
                line_clean = line.strip()
                if "[STREAMING_QA_START]" in line_clean:
                    if f"conv={conv_id}" in line_clean:
                        in_conv_window = True
                        if not t_qa_start:
                            qa_start_line = line_clean
                            t_qa_start = time.time()
                            log(f"[MARKER DETECTED] {qa_start_line}")
                    else:
                        in_conv_window = False

                if not in_conv_window:
                    continue

                if "[RETRIEVAL_MICRO_TIMING]" in line_clean and f"collection={block}" in line_clean and not t_micro:
                    micro_line = line_clean
                    t_micro = time.time()
                    log(f"[MARKER DETECTED] {micro_line}")

                if (("[STREAMING_QA_COMPLETE]" in line_clean and f"conv={conv_id}" in line_clean) or
                    ("[DRAFT_FALLBACK_COMPLETE]" in line_clean and f"conv={conv_id}" in line_clean)) and not t_complete:
                    complete_line = line_clean
                    t_complete = time.time()
                    log(f"[MARKER DETECTED] {complete_line}")

            if t_qa_start and t_micro and t_complete:
                break
        time.sleep(1.0)

    # Cho them de DB luu dap an assistant
    for _flush_i in range(15):
        msgs = load_messages(conv_id)
        if any(m.role == "assistant" and len(m.content or "") > 0 for m in msgs):
            break
        time.sleep(1.0)

    # Kiem tra tin nhan assistant trong DB
    msgs = load_messages(conv_id)
    assistant_msgs = [m for m in msgs if m.role == "assistant"]
    answer_text = assistant_msgs[-1].content if assistant_msgs else ""
    answer_chars = len(answer_text)

    # Chup anh bang chung
    try:
        page.screenshot(path=str(screenshot_file), full_page=True)
        log(f"[SCREENSHOT] Da chup anh luu vao {screenshot_file.name}")
    except Exception as exc:
        log(f"[WARN] Khong the chup anh: {exc}")

    # Tinh toan thoi gian
    ts_start_str = ""
    ts_micro_str = ""
    if qa_start_line:
        m = re.search(r"timestamp=(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})", qa_start_line)
        if m:
            ts_start_str = m.group(1)
    if micro_line:
        m = re.search(r"timestamp=(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})", micro_line)
        if m:
            ts_micro_str = m.group(1)

    if ts_start_str and ts_micro_str:
        qa_to_micro_s = round(diff_marker_timestamps_s(ts_start_str, ts_micro_str), 3)
    elif t_qa_start and t_micro:
        qa_to_micro_s = round(t_micro - t_qa_start, 3)
    else:
        qa_to_micro_s = None

    qa_to_complete_s = round(t_complete - t_qa_start, 2) if (t_qa_start and t_complete) else round(time.time() - t_submit, 2)

    result = {
        "conv_id": conv_id,
        "block": block,
        "question": question,
        "qa_start": bool(t_qa_start),
        "micro_found": bool(t_micro),
        "complete_found": bool(t_complete),
        "qa_to_micro_s": qa_to_micro_s,
        "qa_to_complete_s": qa_to_complete_s,
        "answer_chars": answer_chars,
        "qa_start_line": qa_start_line,
        "micro_line": micro_line,
        "complete_line": complete_line,
        "passed": bool(t_micro and qa_to_micro_s is not None and qa_to_micro_s <= 60.0 and answer_chars > 0),
    }

    log(f"[KET QUA] QA_START->MICRO: {result['qa_to_micro_s']}s (target <= 60s)")
    log(f"[KET QUA] QA_START->COMPLETE: {result['qa_to_complete_s']}s")
    log(f"[KET QUA] Answer length: {answer_chars} chars")
    log(f"[KET QUA] PASSED: {result['passed']}")
    return result


def main():
    log("=" * 80)
    log("BAT DAU NGHIEM THU SONG: DESKTOP-SPEED-PROFILE-QUERY-FIX-HOME")
    log("=" * 80)

    git_head = get_git_head()
    log(f"[GIT] HEAD: {git_head}")

    # 1. Tat sach toan bo worker va server cu
    kill_all_workers_and_servers()

    # 2. Khoi dong app Streamlit (cong 8570)
    log(f"[STARTUP] Khoi dong Streamlit server tai cong {PORT}...")
    server_proc = start_server(PORT, SERVER_LOG_FILE)
    if not wait_for_server(PORT, timeout=90):
        log(f"[ERROR] Server khong phan hoi sau 90s!")
        kill_server(server_proc)
        sys.exit(1)
    log("[STARTUP] Server da san sang.")
    log("[STARTUP] Cho 50s de tien trinh lam am khoi dong lsu tien vao giai doan cache preload...")
    time.sleep(50.0)

    results = {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1600, "height": 1000})
            page = context.new_page()

            # 3a. Ban ngay luot C7620 (lsu) trong khi lam am khoi dong con dang chay
            conv_c7620 = f"CONV-PROFILE-VERIFY-01-LSU-{uuid.uuid4().hex[:6].upper()}"
            res_c7620 = run_single_turn(
                page,
                conv_c7620,
                "Verify Turn 1 - C7620 (lsu)",
                "lsu",
                QUESTION_C7620,
                SCREENSHOT_C7620,
            )
            results["c7620"] = res_c7620

            # 3b. Ban luot JAM4212 (dieu_tra_loi) trong khi lam am khoi dong dieu_tra_loi dang chay
            log("[STARTUP] Cho 50s de tien trinh lam am khoi dong dieu_tra_loi tien vao giai doan cache preload...")
            time.sleep(50.0)
            conv_jam = f"CONV-PROFILE-VERIFY-02-DIEU-{uuid.uuid4().hex[:6].upper()}"
            res_jam = run_single_turn(
                page,
                conv_jam,
                "Verify Turn 2 - JAM4212 (dieu_tra_loi)",
                "dieu_tra_loi",
                QUESTION_JAM4212,
                SCREENSHOT_JAM4212,
            )
            results["jam4212"] = res_jam

            browser.close()
    finally:
        kill_server(server_proc)
        kill_all_workers_and_servers()

    log("=" * 80)
    log(f"TONG KET NGHIEM THU:")
    log(f"Turn 1 C7620 (lsu): PASSED={results.get('c7620', {}).get('passed')}, QA->MICRO={results.get('c7620', {}).get('qa_to_micro_s')}s, Len={results.get('c7620', {}).get('answer_chars')}")
    log(f"Turn 2 JAM4212 (dieu_tra_loi): PASSED={results.get('jam4212', {}).get('passed')}, QA->MICRO={results.get('jam4212', {}).get('qa_to_micro_s')}s, Len={results.get('jam4212', {}).get('answer_chars')}")
    log("=" * 80)

    # Ghi ket qua json
    out_json = OUT_DIR / "ket-qua-profile-query-fix-verify.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"git_head": git_head, "results": results}, f, indent=2, ensure_ascii=False)
    log(f"Da luu {out_json.name}")


if __name__ == "__main__":
    main()
