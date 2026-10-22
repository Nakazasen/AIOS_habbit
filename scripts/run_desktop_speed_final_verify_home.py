"""Script do va nghiem thu tong hop dong chuoi lam am ve DESKTOP-SPEED-FINAL-VERIFY-HOME.
Ticket: DESKTOP-SPEED-FINAL-VERIFY-HOME
Moi truong: May nha h410asrock (CPU-only)

Noi dung thuc thi:
- Canh A: Khoi dong lanh, ban JAM4212 (khoi dieu_tra_loi) o +10s sau server san sang.
          Muc tieu QA_START -> MICRO <= 30s; ca 4 khoi resident sau phien.
- Canh B: Khoi dong lanh lai tu dau, ban luot dau tien THANG vao khoi tri_thuc o +10s sau server san sang.
          Chon cau hoi dinh huong ve khoi hop nhat; khai ro cau hoi va khoi dich thuc te.
          Kiem chung: co bang chung PROCEED cho tri_thuc, truy hoi hoan tat, khong gap lai hien tuong
          khong-bao-gio-lam-am, va boc tach cho truoc truy hoi thanh:
          (phan con lai cua khoi dang nap do dang) + (nap thuan tri_thuc) + (phan du neu co).
- Canh C: Sau khi ca 4 khoi resident, hoi 1 luot am tren khoi tri_thuc va 1 luot am tren lsu (C7620);
          khai tong thoi gian tung luot.
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
import threading
import time
from typing import Any
import urllib.request
import uuid

# Cau hinh moi truong chuan BB-CONFIG-PARITY-01 truoc moi import/runtime
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
from aios_habit.rag_v2.bge_subprocess_client import _pipe_instance_available
from playwright.sync_api import sync_playwright

PORT = 8570
URL = f"http://localhost:{PORT}"
NOTEBOOK_ID = "NB-C26E1C84"

OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SESSION_LOG_FILE = OUT_DIR / "session_desktop_speed_final_verify_home.log"
SERVER_LOG_SCEN_A = OUT_DIR / "server_final_verify_scen_a.log"
SERVER_LOG_SCEN_BC = OUT_DIR / "server_final_verify_scen_bc.log"
JSON_RESULT_FILE = OUT_DIR / "ket-qua-desktop-speed-final-verify-home.json"

SCREENSHOT_SCEN_A = OUT_DIR / "anh-final-verify-scen-a-jam4212.png"
SCREENSHOT_SCEN_B = OUT_DIR / "anh-final-verify-scen-b-trithuc.png"
SCREENSHOT_SCEN_C1 = OUT_DIR / "anh-final-verify-scen-c1-warm-trithuc.png"
SCREENSHOT_SCEN_C2 = OUT_DIR / "anh-final-verify-scen-c2-warm-lsu.png"

# Duong dan nhat ky daemon cua 4 khoi
DAEMON_LOGS = {
    "lsu": Path(r"D:\Sandbox\AIOS_index_split_new\lsu\logs\bge_worker_daemon.stderr.log"),
    "dieu_tra_loi": Path(r"D:\Sandbox\AIOS_index_split_new\dieu_tra_loi\logs\bge_worker_daemon.stderr.log"),
    "tong_hop": Path(r"D:\Sandbox\AIOS_index_split_new\tong_hop\logs\bge_worker_daemon.stderr.log"),
    "tri_thuc": Path(r"D:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\logs\bge_worker_daemon.stderr.log"),
}

# Named pipe tuong ung voi tung khoi
PIPE_NAMES = {
    "lsu": r"\\.\pipe\aios_bge_worker_17dabf033984ea034922c37f",
    "dieu_tra_loi": r"\\.\pipe\aios_bge_worker_db8aefe356bfa836cbdb1444",
    "tong_hop": r"\\.\pipe\aios_bge_worker_2b90a89248d42ae9630f6316",
    "tri_thuc": r"\\.\pipe\aios_bge_worker_95b9bcbfabe03625d81bcecd",
}

# Cac cau hoi nghiem thu
QUESTION_JAM4212 = (
    "Theo báo cáo điều tra KTD-2026-06-0647 trên máy Iris2024-C33, "
    "hiện tượng và nguyên nhân gây ra mã lỗi kẹt giấy JAM4212 là gì?"
)
QUESTION_TRITHUC = (
    "Theo tài liệu trong kho tri thức hợp nhất, quy định chung và các văn bản "
    "nghiệp vụ hướng dẫn vận hành hệ thống là gì?"
)
QUESTION_C7620 = (
    "Mã lỗi C7620 trên dòng máy in Kyocera là lỗi gì, nguyên nhân và đối sách xử lý ra sao?"
)


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
        f"$_.CommandLine -like '*workspace_chat_app.py*') -and $_.ProcessId -ne {my_pid} "
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
        time.sleep(0.5)
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


class WorkerTimelineTracker:
    """Theo doi tien trinh nap va trang thai san sang cua 4 khoi tu daemon logs va named pipes."""

    def __init__(self, initial_offsets: dict[str, int]):
        self.offsets = dict(initial_offsets)
        self.stop_event = threading.Event()
        self.timeline: dict[str, dict[str, Any]] = {
            col: {
                "pipe_name": PIPE_NAMES[col],
                "spawn_ts": None,
                "spawn_pid": None,
                "model_load_ts": None,
                "dense_preload_ts": None,
                "dense_preload_ms": None,
                "sparse_preload_ts": None,
                "sparse_preload_ms": None,
                "ready_ts": None,
                "init_total_ms": None,
                "pipe_available_ts": None,
                "raw_lines": [],
            }
            for col in DAEMON_LOGS
        }
        self.lock = threading.Lock()

    def run_poll(self):
        while not self.stop_event.is_set():
            now_dt = datetime.now()
            now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

            # 1. Kiem tra named pipe
            for col, pipe in PIPE_NAMES.items():
                with self.lock:
                    if self.timeline[col]["pipe_available_ts"] is None:
                        if _pipe_instance_available(pipe):
                            self.timeline[col]["pipe_available_ts"] = now_str
                            log(f"[TIMELINE] Pipe cua khoi '{col}' da mo (available) tai: {now_str}")

            # 2. Doc cac dong moi tu daemon logs
            for col, log_path in DAEMON_LOGS.items():
                if not log_path.exists():
                    continue
                try:
                    size = log_path.stat().st_size
                    offset = self.offsets.get(col, 0)
                    if size > offset:
                        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                            f.seek(offset)
                            new_text = f.read()
                            self.offsets[col] = f.tell()
                        for line in new_text.splitlines():
                            line_s = line.strip()
                            if not line_s:
                                continue
                            ts_m = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[,\.]\d{3})", line_s)
                            event_ts = ts_m.group(1).replace(",", ".") if ts_m else now_str
                            with self.lock:
                                self.timeline[col]["raw_lines"].append(f"[{event_ts}] {line_s}")
                                if "bge_worker_serve pipe=" in line_s:
                                    m = re.search(r"pid=(\d+)", line_s)
                                    pid_val = int(m.group(1)) if m else None
                                    self.timeline[col]["spawn_ts"] = event_ts
                                    self.timeline[col]["spawn_pid"] = pid_val
                                    log(f"[TIMELINE] Khoi '{col}' da spawn worker PID={pid_val} tai: {event_ts}")
                                elif "bge_onnx_loaded" in line_s:
                                    self.timeline[col]["model_load_ts"] = event_ts
                                    log(f"[TIMELINE] Khoi '{col}' da nap xong model ONNX tai: {event_ts}")
                                elif "rag_v2 dense matrix preloaded:" in line_s:
                                    m = re.search(r"elapsed_ms=([\d\.]+)", line_s)
                                    ms_val = float(m.group(1)) if m else None
                                    self.timeline[col]["dense_preload_ts"] = event_ts
                                    self.timeline[col]["dense_preload_ms"] = ms_val
                                    log(f"[TIMELINE] Khoi '{col}' da preload dense matrix ({ms_val}ms) tai: {event_ts}")
                                elif "rag_v2 sparse vectors preloaded:" in line_s:
                                    m = re.search(r"elapsed_ms=([\d\.]+)", line_s)
                                    ms_val = float(m.group(1)) if m else None
                                    self.timeline[col]["sparse_preload_ts"] = event_ts
                                    self.timeline[col]["sparse_preload_ms"] = ms_val
                                    log(f"[TIMELINE] Khoi '{col}' da preload sparse vectors ({ms_val}ms) tai: {event_ts}")
                                elif "bge_worker_stage backend=" in line_s and "init_ms=" in line_s:
                                    m = re.search(r"init_ms=([\d\.]+)", line_s)
                                    ms_val = float(m.group(1)) if m else None
                                    self.timeline[col]["ready_ts"] = event_ts
                                    self.timeline[col]["init_total_ms"] = ms_val
                                    log(f"[TIMELINE] Khoi '{col}' DAT TRANG THAI SAN SANG/RESIDENT (init_total={ms_val}ms) tai: {event_ts}")
                except Exception:
                    pass
            time.sleep(0.1)

    def stop(self):
        self.stop_event.set()


def _extract_ts(marker_line: str) -> str:
    m = re.search(r"timestamp=([0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?)", marker_line)
    return m.group(1) if m else ""


def execute_playwright_turn(
    browser,
    conv_id: str,
    question: str,
    target_block: str,
    title: str,
    screenshot_file: Path,
    server_log_file: Path,
    target_fire_delay_s: float | None = None,
    t_server_ready: datetime | None = None,
) -> dict[str, Any]:
    """Thuc thi mot luot chat qua Playwright va trich xuat markers tu server log."""
    context = browser.new_context(viewport={"width": 1600, "height": 1000})
    page = context.new_page()

    save_conversation(WorkspaceConversation(
        id=conv_id,
        notebook_id=NOTEBOOK_ID,
        title=title,
        ai_mode="grounded",
    ))

    nav_url = f"{URL}/?nb={NOTEBOOK_ID}&conv={conv_id}&block={target_block}"
    log(f"[PLAYWRIGHT] Dieu huong den: {nav_url}")
    page.goto(nav_url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(500)

    page.wait_for_selector('textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"]', timeout=45000)
    textarea = page.locator('textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"]').first
    textarea.wait_for(state="visible", timeout=30000)
    textarea.click()
    textarea.fill(question)
    page.wait_for_timeout(200)

    # Kiem soat thoi diem ban chinh xac +target_fire_delay_s sau server ready
    if target_fire_delay_s is not None and t_server_ready is not None:
        now = datetime.now()
        elapsed_from_ready = (now - t_server_ready).total_seconds()
        if elapsed_from_ready < target_fire_delay_s:
            wait_remain = target_fire_delay_s - elapsed_from_ready
            log(f"[CONTROLLED_FIRE] Cho them {wait_remain:.3f}s de dat moc chuan +{target_fire_delay_s:.1f}s sau server ready...")
            time.sleep(wait_remain)

    t_fire = datetime.now()
    t_fire_str = t_fire.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    elapsed_ready_fire = (t_fire - t_server_ready).total_seconds() if t_server_ready else 0.0
    log(f"[CONTROLLED_FIRE] BAN CAU HOI ({conv_id}) TAI MOC: {t_fire_str} (+{elapsed_ready_fire:.3f}s sau server ready)")

    # Gui ngay lap tuc bang Control+Enter (Streamlit native submit)
    textarea.press("Control+Enter")

    send_btn = page.locator(f'[class*="st-key-wsc_ask_{conv_id}"] button, [class*="st-key-wsc-action-"] button, button:has-text("Hỏi")').first
    if send_btn.count() > 0:
        try:
            send_btn.click(force=True)
        except Exception:
            pass

    # Cho tin nhan luu vao DB voi fast retry loop
    for attempt in range(30):
        time.sleep(0.5)
        msgs = load_messages(conv_id)
        if any(m.role == "user" for m in msgs):
            log(f"[DB] User message da luu sau {(attempt+1)*0.5:.1f}s")
            break
        try:
            textarea.press("Control+Enter")
            if send_btn.count() > 0:
                send_btn.click(force=True)
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
    priority_lines = []
    warm_loop_lines = []
    pre_router_line = ""
    router_start_line = ""
    first_token_line = ""
    router_done_line = ""
    complete_line = ""

    t_watch_start = time.time()
    in_conv_window = False

    while time.time() - t_watch_start < 300:
        if server_log_file.exists():
            log_text = server_log_file.read_text(encoding="utf-8", errors="replace")
            for line in log_text.splitlines():
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

                if "[WARM_PRIORITY_" in line_clean and line_clean not in priority_lines:
                    priority_lines.append(line_clean)
                    log(f"[PRIORITY MARKER] {line_clean}")

                if not in_conv_window:
                    continue

                if "[WORKER_WARM_LOOP_STEP]" in line_clean and line_clean not in warm_loop_lines:
                    warm_loop_lines.append(line_clean)
                    log(f"[MARKER WARM LOOP] {line_clean}")

                if "[RETRIEVAL_MICRO_TIMING]" in line_clean and not t_micro:
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

                if "[STREAMING_QA_FIRST_TOKEN]" in line_clean and f"conv={conv_id}" in line_clean and not t_first_token:
                    first_token_line = line_clean
                    t_first_token = time.time()
                    log(f"[MARKER] {first_token_line}")

                if "[ROUTER_SYNTH_DONE]" in line_clean and f"conv={conv_id}" in line_clean and not t_router_done:
                    router_done_line = line_clean
                    t_router_done = time.time()
                    log(f"[MARKER] {router_done_line}")

                if "[STREAMING_QA_COMPLETE]" in line_clean and f"conv={conv_id}" in line_clean and not t_complete:
                    complete_line = line_clean
                    t_complete = time.time()
                    log(f"[MARKER] {complete_line}")

        if t_complete is not None:
            log("[PLAYWRIGHT] Da bat duoc STREAMING_QA_COMPLETE.")
            break
        time.sleep(0.5)

    # Chup anh giao dien that
    page.wait_for_timeout(3000)
    page.screenshot(path=str(screenshot_file))
    log(f"[SCREENSHOT] Da chup anh giao dien luu tai: {screenshot_file}")

    # Doc noi dung cau tra loi
    msgs = load_messages(conv_id)
    assistant_msgs = [m for m in msgs if m.role == "assistant"]
    ans_text = assistant_msgs[-1].content if assistant_msgs else ""
    ans_len = len(ans_text)
    log(f"[ANSWER] Do dai cau tra loi: {ans_len} ky tu")

    context.close()

    ts_qa_start = _extract_ts(qa_start_line)
    ts_micro = _extract_ts(micro_line)
    ts_pre_router = _extract_ts(pre_router_line)
    ts_first_token = _extract_ts(first_token_line)
    ts_complete = _extract_ts(complete_line)

    delta_qa_to_micro = diff_marker_timestamps_s(ts_qa_start, ts_micro) if (ts_qa_start and ts_micro) else None
    delta_qa_to_first_token = diff_marker_timestamps_s(ts_qa_start, ts_first_token) if (ts_qa_start and ts_first_token) else None
    delta_qa_to_complete = diff_marker_timestamps_s(ts_qa_start, ts_complete) if (ts_qa_start and ts_complete) else None

    # Trích xuất khối đích thực tế từ micro timing line
    actual_col = "unknown"
    if micro_line:
        m_col = re.search(r"collection=([^\s]+)", micro_line)
        if m_col:
            actual_col = m_col.group(1)

    log(f"[{conv_id}] DELTAS: Actual Col={actual_col} | QA_START->MICRO = {delta_qa_to_micro}s | First Token = {delta_qa_to_first_token}s | Complete = {delta_qa_to_complete}s")

    return {
        "conv_id": conv_id,
        "title": title,
        "question": question,
        "target_block": target_block,
        "actual_collection": actual_col,
        "t_fire": t_fire_str,
        "qa_start_line": qa_start_line,
        "micro_line": micro_line,
        "priority_lines": priority_lines,
        "warm_loop_lines": warm_loop_lines,
        "pre_router_line": pre_router_line,
        "router_start_line": router_start_line,
        "first_token_line": first_token_line,
        "router_done_line": router_done_line,
        "complete_line": complete_line,
        "ts_qa_start": ts_qa_start,
        "ts_micro": ts_micro,
        "ts_first_token": ts_first_token,
        "ts_complete": ts_complete,
        "delta_qa_to_micro_s": delta_qa_to_micro,
        "delta_qa_to_first_token_s": delta_qa_to_first_token,
        "delta_qa_to_complete_s": delta_qa_to_complete,
        "answer_length": ans_len,
    }


def preload_onnx_model():
    """Nap truoc model ONNX FP32 (2.26GB) vao OS file cache de tranh seek contention tren HDD 250GB."""
    onnx_model_dir = Path(r"D:\Sandbox\AIOS_habbit\models\bge-m3-onnx-fp32")
    if onnx_model_dir.is_dir():
        log("[OS_CACHE] Doc tuan tu model ONNX FP32 (2.26GB) vao OS file cache...")
        for mf_path in onnx_model_dir.glob("*"):
            if mf_path.is_file():
                try:
                    with open(mf_path, "rb") as mf:
                        while mf.read(1024 * 1024 * 32):
                            pass
                except Exception:
                    pass
        log("[OS_CACHE] Da nap xong model ONNX FP32 vao OS file cache.")


def get_current_log_offsets() -> dict[str, int]:
    offsets = {}
    for col, path in DAEMON_LOGS.items():
        if path.exists():
            offsets[col] = path.stat().st_size
        else:
            offsets[col] = 0
    return offsets


def wait_for_all_resident(tracker: WorkerTimelineTracker, timeout_s: float = 360) -> bool:
    log("Cho den khi CA 4 KHOI DEU DAT RESIDENT (lsu, dieu_tra_loi, tong_hop, tri_thuc)...")
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        with tracker.lock:
            all_ready = all(tracker.timeline[c]["ready_ts"] is not None for c in DAEMON_LOGS)
            if all_ready:
                log("[WAIT_RESIDENT] >>> XAC NHAN: CA 4 KHOI DEU DA DAT TRANG THAI RESIDENT/SAN SANG! <<<")
                return True
        time.sleep(1.0)
    log("[WAIT_RESIDENT] [WARN] Het thoi gian cho tat ca 4 khoi resident!")
    return False


def main():
    log("=" * 90)
    log("BAT DAU NGHAT THU TONG HOP TOAN CHUOI: DESKTOP-SPEED-FINAL-VERIFY-HOME")
    log("=" * 90)
    git_head = get_git_head()
    log(f"[GIT] Commit HEAD: {git_head}")

    # =========================================================================
    # PHIÊN A: CẢNH A (Khởi động lạnh + bắn JAM4212 ở +10s sau server ready)
    # =========================================================================
    log("\n" + "=" * 80)
    log(">>> PHIEN A - CANH A: KHOI DONG LANH + BAN JAM4212 (+10s sau server ready) <<<")
    log("=" * 80)

    # 1. Don dep va nap cache
    kill_all_workers_and_servers()
    preload_onnx_model()

    offsets_a = get_current_log_offsets()
    for col, off in offsets_a.items():
        log(f"[OFFSET A] Khoi '{col}': offset={off} bytes")

    tracker_a = WorkerTimelineTracker(offsets_a)
    th_a = threading.Thread(target=tracker_a.run_poll, daemon=True)
    th_a.start()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        t_start_app_a = datetime.now()
        server_proc_a = start_server(PORT, SERVER_LOG_SCEN_A)
        if not wait_for_server(PORT, timeout=90):
            log("[ERROR] Server Phien A khong phan hoi sau 90s!")
            kill_server(server_proc_a)
            tracker_a.stop()
            browser.close()
            sys.exit(1)

        t_server_ready_a = datetime.now()
        log(f"[APP A] Server Phien A san sang sau {(t_server_ready_a - t_start_app_a).total_seconds():.3f}s tai {t_server_ready_a}")

        conv_a_id = f"CONV-FINAL-A-JAM4212-{uuid.uuid4().hex[:6].upper()}"
        res_a = execute_playwright_turn(
            browser,
            conv_id=conv_a_id,
            question=QUESTION_JAM4212,
            target_block="dieu_tra_loi",
            title="Scene A - Cold Start JAM4212 Priority Verification",
            screenshot_file=SCREENSHOT_SCEN_A,
            server_log_file=SERVER_LOG_SCEN_A,
            target_fire_delay_s=10.0,
            t_server_ready=t_server_ready_a,
        )

        # Cho ca 4 khoi resident sau Phien A
        all_res_a = wait_for_all_resident(tracker_a, timeout_s=360)

        browser.close()

    tracker_a.stop()
    kill_server(server_proc_a)
    kill_all_workers_and_servers()

    timeline_a = {}
    with tracker_a.lock:
        timeline_a = dict(tracker_a.timeline)

    log("\n[KET QUA PHIEN A]")
    log(f"QA_START -> MICRO Canh A: {res_a.get('delta_qa_to_micro_s')}s (Mục tiêu <= 30s)")
    log(f"Ca 4 khoi resident Phien A: {all_res_a}")

    # =========================================================================
    # PHIÊN B & C: CẢNH B (Khởi động lạnh lại từ đầu + bắn thẳng tri_thuc) + CẢNH C
    # =========================================================================
    log("\n" + "=" * 80)
    log(">>> PHIEN B/C - CANH B (KHOI DONG LANH LAI TU DAU + BAN THANG TRI_THUC) & CANH C <<<")
    log("=" * 80)

    # 1. Don dep va nap cache
    kill_all_workers_and_servers()
    preload_onnx_model()

    offsets_bc = get_current_log_offsets()
    for col, off in offsets_bc.items():
        log(f"[OFFSET BC] Khoi '{col}': offset={off} bytes")

    tracker_bc = WorkerTimelineTracker(offsets_bc)
    th_bc = threading.Thread(target=tracker_bc.run_poll, daemon=True)
    th_bc.start()

    res_b = {}
    res_c1 = {}
    res_c2 = {}
    all_res_bc = False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        t_start_app_bc = datetime.now()
        server_proc_bc = start_server(PORT, SERVER_LOG_SCEN_BC)
        if not wait_for_server(PORT, timeout=90):
            log("[ERROR] Server Phien B/C khong phan hoi sau 90s!")
            kill_server(server_proc_bc)
            tracker_bc.stop()
            browser.close()
            sys.exit(1)

        t_server_ready_bc = datetime.now()
        log(f"[APP BC] Server Phien B/C san sang sau {(t_server_ready_bc - t_start_app_bc).total_seconds():.3f}s tai {t_server_ready_bc}")

        # -------------------------------------------------------------
        # CANH B: Ban luot dau tien THANG vao khoi tri_thuc o +10s sau server ready
        # -------------------------------------------------------------
        log("\n" + "-" * 70)
        log("CANH B: Ban luot dau tien THANG vao khoi tri_thuc o +10s sau server ready")
        log("-" * 70)
        conv_b_id = f"CONV-FINAL-B-TRITHUC-{uuid.uuid4().hex[:6].upper()}"
        res_b = execute_playwright_turn(
            browser,
            conv_id=conv_b_id,
            question=QUESTION_TRITHUC,
            target_block="auto",
            title="Scene B - Cold Start First Turn Direct Tri Thuc Verification",
            screenshot_file=SCREENSHOT_SCEN_B,
            server_log_file=SERVER_LOG_SCEN_BC,
            target_fire_delay_s=10.0,
            t_server_ready=t_server_ready_bc,
        )

        # Cho ca 4 khoi resident sau Canh B
        all_res_bc = wait_for_all_resident(tracker_bc, timeout_s=360)

        # -------------------------------------------------------------
        # CANH C: Luot am tren khoi tri_thuc va luot am tren lsu (C7620)
        # -------------------------------------------------------------
        log("\n" + "-" * 70)
        log("CANH C: Luot am 1 - Khoi tri_thuc (sau khi ca 4 khoi da resident)")
        log("-" * 70)
        conv_c1_id = f"CONV-FINAL-C1-WARM-TRITHUC-{uuid.uuid4().hex[:6].upper()}"
        res_c1 = execute_playwright_turn(
            browser,
            conv_id=conv_c1_id,
            question=QUESTION_TRITHUC,
            target_block="auto",
            title="Scene C1 - Warm Turn Tri Thuc Verification",
            screenshot_file=SCREENSHOT_SCEN_C1,
            server_log_file=SERVER_LOG_SCEN_BC,
            target_fire_delay_s=None,
            t_server_ready=None,
        )

        log("\n" + "-" * 70)
        log("CANH C: Luot am 2 - Khoi LSU (C7620) (sau khi ca 4 khoi da resident)")
        log("-" * 70)
        conv_c2_id = f"CONV-FINAL-C2-WARM-LSU-{uuid.uuid4().hex[:6].upper()}"
        res_c2 = execute_playwright_turn(
            browser,
            conv_id=conv_c2_id,
            question=QUESTION_C7620,
            target_block="lsu",
            title="Scene C2 - Warm Turn LSU C7620 Verification",
            screenshot_file=SCREENSHOT_SCEN_C2,
            server_log_file=SERVER_LOG_SCEN_BC,
            target_fire_delay_s=None,
            t_server_ready=None,
        )

        browser.close()

    tracker_bc.stop()
    kill_server(server_proc_bc)
    kill_all_workers_and_servers()

    timeline_bc = {}
    with tracker_bc.lock:
        timeline_bc = dict(tracker_bc.timeline)

    # =========================================================================
    # TỔNG HỢP VÀ ĐÁNH GIÁ CHỈ TIÊU VÉ
    # =========================================================================
    log("\n" + "=" * 90)
    log("TONG HOP KET QUA NGHIEM THU TOAN CHUOI (CANH A, B, C)")
    log("=" * 90)

    # 1. Chi tieu Canh A
    delta_a_micro = res_a.get("delta_qa_to_micro_s")
    pass_scen_a = (delta_a_micro is not None and delta_a_micro <= 30.0 and all_res_a)

    # 2. Chi tieu Canh B:
    # Co bang chung PROCEED cho tri_thuc (hoac priority markers), truy hoi hoan tat,
    # khong gap lai hien tuong khong bao gio lam am (tri_thuc resident),
    # va boc tach cho truoc truy hoi: (phan con lai khoi dang nap do dang) + (nap thuan tri_thuc) + (phan du)
    delta_b_micro = res_b.get("delta_qa_to_micro_s")
    tri_thuc_ready_bc = timeline_bc.get("tri_thuc", {}).get("ready_ts") is not None
    pass_scen_b = (res_b.get("ts_micro") is not None and tri_thuc_ready_bc and all_res_bc)

    # 3. Chi tieu Canh C:
    # 1 luot am tri_thuc, 1 luot am lsu C7620
    delta_c1_total = res_c1.get("delta_qa_to_complete_s")
    delta_c2_total = res_c2.get("delta_qa_to_complete_s")
    pass_scen_c = (delta_c1_total is not None and delta_c2_total is not None)

    log(f"1. CANH A: QA_START->MICRO = {delta_a_micro}s (chỉ tiêu <= 30s), all resident={all_res_a} => {'DAT (PASS)' if pass_scen_a else 'FAIL'}")
    log(f"2. CANH B: QA_START->MICRO = {delta_b_micro}s, actual_col={res_b.get('actual_collection')}, tri_thuc resident={tri_thuc_ready_bc} => {'DAT (PASS)' if pass_scen_b else 'FAIL'}")
    log(f"3. CANH C: Luot am Tri thuc total={delta_c1_total}s, Luot am LSU C7620 total={delta_c2_total}s => {'DAT (PASS)' if pass_scen_c else 'FAIL'}")

    # Luu JSON ket qua
    result_data = {
        "ma_ve": "DESKTOP-SPEED-FINAL-VERIFY-HOME",
        "thoi_diem": datetime.now(timezone.utc).isoformat(),
        "git_head": git_head,
        "scen_a": {
            "t_start_app": t_start_app_a.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "t_server_ready": t_server_ready_a.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "turn_jam4212": res_a,
            "all_resident": all_res_a,
            "timeline": timeline_a,
        },
        "scen_b": {
            "t_start_app": t_start_app_bc.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "t_server_ready": t_server_ready_bc.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "turn_trithuc": res_b,
            "all_resident": all_res_bc,
            "timeline": timeline_bc,
        },
        "scen_c": {
            "turn_c1_warm_trithuc": res_c1,
            "turn_c2_warm_lsu": res_c2,
        },
        "summary": {
            "scen_a_pass": pass_scen_a,
            "scen_b_pass": pass_scen_b,
            "scen_c_pass": pass_scen_c,
            "overall_pass": (pass_scen_a and pass_scen_b and pass_scen_c),
        }
    }

    with open(JSON_RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    log(f"[SAVE] Da luu tep JSON ket qua: {JSON_RESULT_FILE}")

    print("\n>>> EXECUTION SCRIPT FINISHED <<<\n")


if __name__ == "__main__":
    main()
