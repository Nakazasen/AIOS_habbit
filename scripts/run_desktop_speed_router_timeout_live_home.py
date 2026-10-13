"""Script thuc thi nghiem thu song cho ve DESKTOP-SPEED-ROUTER-TIMEOUT-FIX-HOME.
May dich: MAY NHA (h410asrock, CPU-only, BB-CONFIG-PARITY-01)

Muc tieu:
1. Luot (i) Mo phong nha cung cap cham/treo bang env override chi trong phien do (AIOS_ROUTER_TIMEOUT_SECONDS=5):
   - Chuyen du phong xay ra tai moc cau hinh moi (~5s), khong con phang 30s.
   - Khoi phuc cau hinh ngay sau do.
2. Luot (ii) Dam may binh thuong (khong env override, dung cau hinh chuan):
   - Router timeout nhat quan o moc 90s (khop AIOS_LOCAL_AI_TIMEOUT_SECONDS).
   - TTFT xap xi ttft cua nha cung cap (~8-14s), dap an dung tu deepseek/deepseek-v4.1-flash.
3. Luu nhat ky server, session log, JSON ket qua va anh chup giao dien.
"""
from __future__ import annotations

from datetime import datetime, timezone
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
from aios_habit.streaming_markers import diff_marker_timestamps_s, parse_marker_timestamp
from playwright.sync_api import sync_playwright

PORT = 8570
URL = f"http://localhost:{PORT}"
NOTEBOOK_ID_LSU = "NB-C26E1C84"

OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SERVER_LOG_FILE = OUT_DIR / "server_desktop_speed_router_timeout_fix_home.log"
SESSION_LOG_FILE = OUT_DIR / "session_desktop_speed_router_timeout_fix_home.log"
JSON_RESULT_FILE = OUT_DIR / "ket-qua-desktop-speed-router-timeout-fix-home.json"
REPORT_MD_FILE = OUT_DIR / "DESKTOP-SPEED-ROUTER-TIMEOUT-FIX-HOME.md"

SCREENSHOT_TURN1 = OUT_DIR / "anh-router-timeout-01-slow-failover.png"
SCREENSHOT_TURN2 = OUT_DIR / "anh-router-timeout-02-cloud-normal.png"


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


def start_server(port: int, log_file: Path, extra_env: dict[str, str] | None = None) -> subprocess.Popen:
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

    if extra_env:
        for k, v in extra_env.items():
            env[k] = v

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
    env_desc = f" (extra_env: {extra_env})" if extra_env else ""
    log(f"[STARTUP] Chay lenh: {' '.join(cmd)}{env_desc}")
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
    expected_timeout_s: float | None = None,
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

    t_qa_start = None
    t_micro = None
    t_pre_router = None
    t_router_start = None
    t_first_token = None
    t_router_done = None
    t_complete = None

    qa_start_line = ""
    micro_line = ""
    pre_router_line = ""
    router_start_line = ""
    timeout_line = ""
    first_token_line = ""
    router_done_line = ""
    complete_line = ""

    t_watch_start = time.time()
    in_conv_window = False

    while time.time() - t_watch_start < 180:
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
                            log(f"[MARKER] {qa_start_line}")
                    else:
                        in_conv_window = False

                if not in_conv_window:
                    continue

                if "[RETRIEVAL_MICRO_TIMING]" in line_clean and f"collection={block}" in line_clean and not t_micro:
                    micro_line = line_clean
                    t_micro = time.time()
                    log(f"[MARKER] {micro_line}")

                if "[PRE_SYNTH_STEP]" in line_clean and f"conv={conv_id}" in line_clean and "step=pre_router" in line_clean and not t_pre_router:
                    pre_router_line = line_clean
                    t_pre_router = time.time()
                    log(f"[MARKER] {pre_router_line}")

                if "[ROUTER_SYNTH_START]" in line_clean and f"conv={conv_id}" in line_clean and not t_router_start:
                    router_start_line = line_clean
                    t_router_start = time.time()
                    log(f"[MARKER] {router_start_line}")

                if "Nakazasen Router timed out" in line_clean and not timeout_line:
                    timeout_line = line_clean
                    log(f"[ROUTER TIMEOUT LOG] {timeout_line}")

                if "[STREAMING_QA_FIRST_TOKEN]" in line_clean and f"conv={conv_id}" in line_clean and not t_first_token:
                    first_token_line = line_clean
                    t_first_token = time.time()
                    log(f"[MARKER] {first_token_line}")

                if "[ROUTER_SYNTH_DONE]" in line_clean and f"conv={conv_id}" in line_clean and not t_router_done:
                    router_done_line = line_clean
                    t_router_done = time.time()
                    log(f"[MARKER] {router_done_line}")

                if (("[STREAMING_QA_COMPLETE]" in line_clean and f"conv={conv_id}" in line_clean) or
                    ("[DRAFT_FALLBACK_COMPLETE]" in line_clean and f"conv={conv_id}" in line_clean)) and not t_complete:
                    complete_line = line_clean
                    t_complete = time.time()
                    log(f"[MARKER] {complete_line}")

            if t_qa_start and t_first_token and t_complete:
                break
        time.sleep(0.5)

    for _flush_i in range(15):
        msgs = load_messages(conv_id)
        if any(m.role == "assistant" and len(m.content or "") > 0 for m in msgs):
            break
        time.sleep(1.0)

    msgs = load_messages(conv_id)
    assistant_msgs = [m for m in msgs if m.role == "assistant"]
    answer_text = assistant_msgs[-1].content if assistant_msgs else ""
    answer_chars = len(answer_text)

    try:
        page.screenshot(path=str(screenshot_file), full_page=True)
        log(f"[SCREENSHOT] Da chup anh luu vao {screenshot_file.name}")
    except Exception as exc:
        log(f"[WARN] Khong the chup anh: {exc}")

    def extract_ts(line: str) -> str:
        if not line:
            return ""
        m = re.search(r"timestamp=(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})", line)
        return m.group(1) if m else ""

    ts_qa_start = extract_ts(qa_start_line)
    ts_micro = extract_ts(micro_line)
    ts_pre_router = extract_ts(pre_router_line)
    ts_router_start = extract_ts(router_start_line)
    ts_first_token = extract_ts(first_token_line)
    ts_router_done = extract_ts(router_done_line)
    ts_complete = extract_ts(complete_line)

    gap_qa_to_micro_s = round(diff_marker_timestamps_s(ts_qa_start, ts_micro), 3) if (ts_qa_start and ts_micro) else None
    gap_micro_to_pre_router_s = round(diff_marker_timestamps_s(ts_micro, ts_pre_router), 3) if (ts_micro and ts_pre_router) else None
    gap_pre_to_router_start_s = round(diff_marker_timestamps_s(ts_pre_router, ts_router_start), 3) if (ts_pre_router and ts_router_start) else None
    gap_router_start_to_first_token_s = round(diff_marker_timestamps_s(ts_router_start, ts_first_token), 3) if (ts_router_start and ts_first_token) else None
    gap_first_token_to_complete_s = round(diff_marker_timestamps_s(ts_first_token, ts_complete), 3) if (ts_first_token and ts_complete) else None
    gap_router_done_to_complete_s = round(diff_marker_timestamps_s(ts_router_done, ts_complete), 3) if (ts_router_done and ts_complete) else None
    total_server_s = round(diff_marker_timestamps_s(ts_qa_start, ts_complete), 3) if (ts_qa_start and ts_complete) else None

    # Tinh backend phan hoi
    eff_backend = "unknown"
    if complete_line:
        m_b = re.search(r"backend=(.*?)(?:\s+ok=|$)", complete_line)
        if m_b:
            eff_backend = m_b.group(1).strip()

    result = {
        "conv_id": conv_id,
        "conv_title": conv_title,
        "block": block,
        "question": question,
        "ts_qa_start": ts_qa_start,
        "ts_micro": ts_micro,
        "ts_pre_router": ts_pre_router,
        "ts_router_start": ts_router_start,
        "ts_first_token": ts_first_token,
        "ts_router_done": ts_router_done,
        "ts_complete": ts_complete,
        "gap_qa_to_micro_s": gap_qa_to_micro_s,
        "gap_micro_to_pre_router_s": gap_micro_to_pre_router_s,
        "gap_pre_to_router_start_s": gap_pre_to_router_start_s,
        "gap_router_start_to_first_token_s": gap_router_start_to_first_token_s,
        "gap_first_token_to_complete_s": gap_first_token_to_complete_s,
        "gap_router_done_to_complete_s": gap_router_done_to_complete_s,
        "total_server_s": total_server_s,
        "backend": eff_backend,
        "answer_chars": answer_chars,
        "qa_start_line": qa_start_line,
        "micro_line": micro_line,
        "router_start_line": router_start_line,
        "timeout_line": timeout_line,
        "first_token_line": first_token_line,
        "router_done_line": router_done_line,
        "complete_line": complete_line,
        "screenshot": str(screenshot_file.name),
    }

    log(f"[KET QUA] QA_START -> MICRO: {gap_qa_to_micro_s}s")
    log(f"[KET QUA] ROUTER_SYNTH_START -> FIRST_TOKEN: {gap_router_start_to_first_token_s}s")
    log(f"[KET QUA] FIRST_TOKEN -> COMPLETE: {gap_first_token_to_complete_s}s")
    log(f"[KET QUA] Total server: {total_server_s}s")
    log(f"[KET QUA] Answer length: {answer_chars} chars | Backend: {eff_backend}")
    if timeout_line:
        log(f"[KET QUA] Timeout detected: {timeout_line}")

    return result


def main():
    log("=" * 80)
    log("BAT DAU NGHIEM THU SONG CHO VE: DESKTOP-SPEED-ROUTER-TIMEOUT-FIX-HOME")
    log("=" * 80)

    git_head = get_git_head()
    log(f"[GIT] HEAD: {git_head}")

    # Reset log files
    if SERVER_LOG_FILE.exists():
        try:
            SERVER_LOG_FILE.unlink()
        except Exception:
            pass

    results = []

    # =========================================================================
    # PHAN 1: LUOT (i) - MO PHONG NHA CUNG CAP CHAM/TREO BANG ENV OVERRIDE
    # Override: AIOS_ROUTER_TIMEOUT_SECONDS=5 (chi trong phien do)
    # =========================================================================
    log("\n" + "=" * 80)
    log("PHAN 1: LUOT (i) - MO PHONG NHA CUNG CAP CHAM BANG ENV OVERRIDE (TIMEOUT=5s)")
    log("=" * 80)
    kill_all_workers_and_servers()

    server_proc1 = start_server(PORT, SERVER_LOG_FILE, extra_env={"AIOS_ROUTER_TIMEOUT_SECONDS": "5"})
    if not wait_for_server(PORT, timeout=90):
        log("[ERROR] Server luot (i) khong phan hoi sau 90s!")
        kill_server(server_proc1)
        sys.exit(1)
    log(f"[STARTUP] Server luot (i) da san sang tai PID={server_proc1.pid}.")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1600, "height": 1000})
            page = context.new_page()

            # Warm tong_hop nhanh (~10s)
            log("[WARM] Cho 10s truoc luot tong_hop...")
            time.sleep(10.0)

            conv_id1 = f"CONV-ROUTER-TO-SIM-{uuid.uuid4().hex[:6].upper()}"
            res1 = run_single_turn(
                page=page,
                conv_id=conv_id1,
                conv_title="Luot (i) - Mo phong cham (Router Timeout = 5s)",
                block="tong_hop",
                question="Theo tài liệu Tab led cam ung.pdf (Touch Panel Specification), điều kiện nhiệt độ và độ ẩm tiêu chuẩn để bảo quản (Storage) touch panel là bao nhiêu?",
                screenshot_file=SCREENSHOT_TURN1,
                expected_timeout_s=5.0,
            )
            res1["kieu_nghiem_thu"] = "simulated_slow_timeout_5s"
            results.append(res1)
            browser.close()
    finally:
        kill_server(server_proc1)
        kill_all_workers_and_servers()

    log("[RESTORE] Da dung server luot (i). Cau hinh AIOS_ROUTER_TIMEOUT_SECONDS=5 da duoc go bo hoan toan.")

    # =========================================================================
    # PHAN 2: LUOT (ii) - DAM MAY BINH THUONG (KHONG ENV OVERRIDE, GOC 90s)
    # =========================================================================
    log("\n" + "=" * 80)
    log("PHAN 2: LUOT (ii) - DAM MAY BINH THUONG (CAU HINH CHUAN 90s)")
    log("=" * 80)
    time.sleep(3.0)

    server_proc2 = start_server(PORT, SERVER_LOG_FILE, extra_env=None)
    if not wait_for_server(PORT, timeout=90):
        log("[ERROR] Server luot (ii) khong phan hoi sau 90s!")
        kill_server(server_proc2)
        sys.exit(1)
    log(f"[STARTUP] Server luot (ii) da san sang tai PID={server_proc2.pid}.")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1600, "height": 1000})
            page = context.new_page()

            # Cho 10s truoc luot tong_hop
            log("[WARM] Cho 10s truoc luot tong_hop chuan...")
            time.sleep(10.0)

            conv_id2 = f"CONV-ROUTER-TO-NORM-{uuid.uuid4().hex[:6].upper()}"
            res2 = run_single_turn(
                page=page,
                conv_id=conv_id2,
                conv_title="Luot (ii) - Dam may binh thuong (Chuan 90s)",
                block="tong_hop",
                question="Theo tài liệu Tab led cam ung.pdf (Touch Panel Specification), điều kiện nhiệt độ và độ ẩm tiêu chuẩn để bảo quản (Storage) touch panel là bao nhiêu?",
                screenshot_file=SCREENSHOT_TURN2,
            )
            res2["kieu_nghiem_thu"] = "cloud_normal_90s"
            results.append(res2)
            browser.close()
    finally:
        kill_server(server_proc2)
        kill_all_workers_and_servers()

    log("=" * 80)
    log("HOAN TAT PHIEN NGHIEM THU SONG. DANG LUU KET QUA...")
    log("=" * 80)

    output_data = {
        "ma_ve": "DESKTOP-SPEED-ROUTER-TIMEOUT-FIX-HOME",
        "thoi_diem": datetime.now(timezone.utc).isoformat(),
        "git_head": git_head,
        "results": results,
    }
    with open(JSON_RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    log(f"Da ghi file JSON: {JSON_RESULT_FILE.name}")


if __name__ == "__main__":
    main()
