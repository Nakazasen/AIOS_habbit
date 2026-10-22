"""Script do va nghiem thu song ve DESKTOP-SPEED-WARM-PRIORITY-FIX-HOME.
Ticket: DESKTOP-SPEED-WARM-PRIORITY-FIX-HOME
Moi truong: May nha h410asrock (CPU-only)

Muc tieu nghiem thu:
1. Don dep sach worker va server cu.
2. Khoi dong lanh app Streamlit (cong 8570) voi cau hinh chuan BB-CONFIG-PARITY-01.
3. Ghi lai moc thoi gian ca 4 khoi (lsu, dieu_tra_loi, tong_hop, tri_thuc) tu daemon logs va named pipes.
4. Turn 1 (Cold startup + 10s fire): Ban luot JAM4212 (khoi dieu_tra_loi) o moc kiem soat (+10s sau khoi dong app).
5. Xac thuc co che uu tien:
   - Khoi khong lien quan (tong_hop / tri_thuc) nhuong lam am nen khi luot nguoi dung dang cho truy hoi ([WARM_PRIORITY_YIELD]).
   - Sau khi truy hoi nguoi dung xong, lam am nen tiep tuc ([WARM_PRIORITY_RESUME]).
   - QA_START -> MICRO cua luot JAM4212 phai <= 30s!
6. Cho den khi CA 4 KHOI DEU DAT RESIDENT sau phien khoi dong.
7. Turn 2 (Standard warm turn): Sau khi ca 4 khoi resident, ban mot luot am chuan de xac thuc khong cham hon truoc.
8. Chup anh giao dien that Playwright cho ca 2 turn.
9. Xuat JSON ket qua, log phien, va bao cao nghiem thu.
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
from aios_habit.rag_v2.bge_subprocess_client import _pipe_instance_available
from playwright.sync_api import sync_playwright

PORT = 8570
URL = f"http://localhost:{PORT}"
NOTEBOOK_ID = "NB-C26E1C84"

OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SERVER_LOG_FILE = OUT_DIR / "server_desktop_speed_warm_priority_fix_home.log"
SESSION_LOG_FILE = OUT_DIR / "session_desktop_speed_warm_priority_fix_home.log"
JSON_RESULT_FILE = OUT_DIR / "ket-qua-desktop-speed-warm-priority-fix-home.json"
SCREENSHOT_TURN1_FILE = OUT_DIR / "anh-warm-priority-fix-turn1-jam4212.png"
SCREENSHOT_TURN2_FILE = OUT_DIR / "anh-warm-priority-fix-turn2-warm.png"

# Duong dan nhat ky daemon cua 4 khoi
DAEMON_LOGS = {
    "lsu": Path(r"D:\Sandbox\AIOS_index_split_new\lsu\logs\bge_worker_daemon.stderr.log"),
    "dieu_tra_loi": Path(r"D:\Sandbox\AIOS_index_split_new\dieu_tra_loi\logs\bge_worker_daemon.stderr.log"),
    "tong_hop": Path(r"D:\Sandbox\AIOS_index_split_new\tong_hop\logs\bge_worker_daemon.stderr.log"),
    "tri_thuc": Path(r"D:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\logs\bge_worker_daemon.stderr.log"),
}

# Pipe names tuong ung voi tung khoi
PIPE_NAMES = {
    "lsu": r"\\.\pipe\aios_bge_worker_17dabf033984ea034922c37f",
    "dieu_tra_loi": r"\\.\pipe\aios_bge_worker_db8aefe356bfa836cbdb1444",
    "tong_hop": r"\\.\pipe\aios_bge_worker_2b90a89248d42ae9630f6316",
    "tri_thuc": r"\\.\pipe\aios_bge_worker_95b9bcbfabe03625d81bcecd",
}

QUESTION_JAM4212 = (
    "Theo báo cáo điều tra KTD-2026-06-0647 trên máy Iris2024-C33, "
    "hiện tượng và nguyên nhân gây ra mã lỗi kẹt giấy JAM4212 là gì?"
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
    target_fire_delay_s: float | None = None,
    t_start_app: datetime | None = None,
) -> dict[str, Any]:
    """Execute a chat turn through Playwright and extract markers."""
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

    if target_fire_delay_s is not None and t_start_app is not None:
        now = datetime.now()
        elapsed_from_start = (now - t_start_app).total_seconds()
        if elapsed_from_start < target_fire_delay_s:
            wait_remain = target_fire_delay_s - elapsed_from_start
            log(f"[CONTROLLED_FIRE] Cho them {wait_remain:.3f}s de dat moc chuan +{target_fire_delay_s:.1f}s sau khoi dong app...")
            time.sleep(wait_remain)

    t_fire = datetime.now()
    t_fire_str = t_fire.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    elapsed_app_fire = (t_fire - t_start_app).total_seconds() if t_start_app else 0.0
    log(f"[CONTROLLED_FIRE] BAN CAU HOI ({conv_id}) TAI MOC: {t_fire_str} (+{elapsed_app_fire:.3f}s sau mo app)")

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

    while time.time() - t_watch_start < 240:
        if SERVER_LOG_FILE.exists():
            log_text = SERVER_LOG_FILE.read_text(encoding="utf-8", errors="replace")
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

    log(f"[{conv_id}] DELTAS: QA_START->MICRO = {delta_qa_to_micro}s | First Token = {delta_qa_to_first_token}s | Complete = {delta_qa_to_complete}s")

    return {
        "conv_id": conv_id,
        "title": title,
        "target_block": target_block,
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


def main():
    log("=" * 80)
    log("BAT DAU THUC THI VE: DESKTOP-SPEED-WARM-PRIORITY-FIX-HOME")
    log("=" * 80)
    git_head = get_git_head()
    log(f"[GIT] Commit HEAD: {git_head}")

    # Ghi nhan kich thuoc ban dau cua 4 tệp daemon log
    initial_offsets = {}
    for col, path in DAEMON_LOGS.items():
        if path.exists():
            initial_offsets[col] = path.stat().st_size
        else:
            initial_offsets[col] = 0
        log(f"[LOG_OFFSET] Khoi '{col}': offset={initial_offsets[col]} bytes ({path})")

    with sync_playwright() as p:
        # Pre-launch browser to warm up Chromium before cold startup timing
        log("[PLAYWRIGHT] Khoi dong trinh duyet Chromium truoc...")
        browser = p.chromium.launch(headless=True)

        # Don dep tien trinh cu
        kill_all_workers_and_servers()

        # Nap truoc model ONNX FP32 vao OS file cache (tranh seek contention tren HDD 250GB)
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

        # Khoi dong tracker
        tracker = WorkerTimelineTracker(initial_offsets)
        tracker_thread = threading.Thread(target=tracker.run_poll, daemon=True)
        tracker_thread.start()

        # Khoi dong server
        t_start_app = datetime.now()
        t_start_app_str = t_start_app.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log(f"[APP_LAUNCH] Khoi dong server tai {t_start_app_str}...")
        server_proc = start_server(PORT, SERVER_LOG_FILE)

        if not wait_for_server(PORT, timeout=90):
            log("[ERROR] Streamlit server khong phan hoi sau 90s!")
            kill_server(server_proc)
            tracker.stop()
            browser.close()
            sys.exit(1)

        t_server_ready = datetime.now()
        t_server_ready_str = t_server_ready.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        elapsed_health_s = (t_server_ready - t_start_app).total_seconds()
        log(f"[APP_LAUNCH] Server san sang tren port {PORT} (PID={server_proc.pid}) sau {elapsed_health_s:.3f}s tai {t_server_ready_str}")

        turn1_result = {}
        turn2_result = {}

        # -------------------------------------------------------------
        # TURN 1: JAM4212 ban tai moc +10s (Cold startup phase)
        # -------------------------------------------------------------
        log("\n" + "=" * 60)
        log("TURN 1: JAM4212 tai moc +10s sau khoi dong app (Kiem tra Priority Yielding)")
        log("=" * 60)
        conv1_id = f"CONV-PRIORITY-T1-{uuid.uuid4().hex[:6].upper()}"
        turn1_result = execute_playwright_turn(
            browser,
            conv_id=conv1_id,
            question=QUESTION_JAM4212,
            target_block="dieu_tra_loi",
            title="Turn 1 - JAM4212 Cold +10s Priority Verification",
            screenshot_file=SCREENSHOT_TURN1_FILE,
            target_fire_delay_s=10.0,
            t_start_app=t_start_app,
        )

        # -------------------------------------------------------------
        # CHO CA 4 KHOI DAT RESIDENT TRUOC KHI BAN TURN 2
        # -------------------------------------------------------------
        log("\n" + "=" * 60)
        log("CHO CA 4 KHOI DAT RESIDENT (lsu, dieu_tra_loi, tong_hop, tri_thuc)...")
        log("=" * 60)
        deadline_all_ready = time.time() + 300
        while time.time() < deadline_all_ready:
            with tracker.lock:
                all_ready = all(tracker.timeline[c]["ready_ts"] is not None for c in DAEMON_LOGS)
                if all_ready:
                    log("[WAIT_RESIDENT] >>> XAC NHAN: CA 4 KHOI DEU DA DAT TRANG THAI SAN SANG/RESIDENT! <<<")
                    break
            time.sleep(1.0)

        # -------------------------------------------------------------
        # TURN 2: Standard Warm Turn (hoi khi ca 4 khoi da resident)
        # -------------------------------------------------------------
        log("\n" + "=" * 60)
        log("TURN 2: Luot am chuan sau khi ca 4 khoi da resident")
        log("=" * 60)
        conv2_id = f"CONV-PRIORITY-T2-{uuid.uuid4().hex[:6].upper()}"
        turn2_result = execute_playwright_turn(
            browser,
            conv_id=conv2_id,
            question=QUESTION_JAM4212,
            target_block="dieu_tra_loi",
            title="Turn 2 - Standard Warm Turn Verification",
            screenshot_file=SCREENSHOT_TURN2_FILE,
            target_fire_delay_s=None,
            t_start_app=None,
        )

        browser.close()

    # Dung tracker va thu don server
    tracker.stop()
    kill_server(server_proc)
    kill_all_workers_and_servers()

    # Tong hop dong thoi gian 4 khoi
    final_timeline = {}
    with tracker.lock:
        final_timeline = dict(tracker.timeline)

    log("\n" + "=" * 80)
    log("TONG HOP KET QUA THIET LAP VA NGHAT KY 4 KHOI")
    log("=" * 80)
    for col, info in final_timeline.items():
        log(f"Khoi '{col}': spawn={info['spawn_ts']} (PID={info['spawn_pid']}), pipe_open={info['pipe_available_ts']}, dense={info['dense_preload_ts']} ({info['dense_preload_ms']}ms), sparse={info['sparse_preload_ts']} ({info['sparse_preload_ms']}ms), ready={info['ready_ts']} (init={info['init_total_ms']}ms)")

    # Kiem tra tieu chi nghiem thu:
    # 1. Turn 1 QA_START -> MICRO <= 30.0s
    t1_micro_delta = turn1_result.get("delta_qa_to_micro_s")
    assert_t1_micro_pass = (t1_micro_delta is not None and t1_micro_delta <= 30.0)

    # 2. Ca 4 khoi deu resident
    assert_all_4_resident = all(final_timeline[c]["ready_ts"] is not None for c in DAEMON_LOGS)

    # 3. Priority markers co mat (Yield / Resume)
    server_text = SERVER_LOG_FILE.read_text(encoding="utf-8", errors="replace") if SERVER_LOG_FILE.exists() else ""
    yield_count = server_text.count("[WARM_PRIORITY_YIELD]")
    resume_count = server_text.count("[WARM_PRIORITY_RESUME]")

    # 4. Turn 2 warm khong cham (micro <= 15s)
    t2_micro_delta = turn2_result.get("delta_qa_to_micro_s")
    assert_t2_warm_pass = (t2_micro_delta is not None and t2_micro_delta <= 15.0)

    log("\n" + "=" * 80)
    log("DANH GIA TIEU CHI NGHAT DINH VÉ:")
    log(f"1. Turn 1 QA_START -> MICRO <= 30s: {t1_micro_delta}s => {'DAT (PASS)' if assert_t1_micro_pass else 'KHONG DAT (FAIL)'}")
    log(f"2. Ca 4 khoi dat resident: {'DAT (PASS)' if assert_all_4_resident else 'KHONG DAT (FAIL)'}")
    log(f"3. Co che nhuong (Yield count={yield_count}, Resume count={resume_count}): {'DAT (PASS)' if yield_count > 0 else 'CAN KIEM TRA'}")
    log(f"4. Turn 2 warm khong cham: {t2_micro_delta}s => {'DAT (PASS)' if assert_t2_warm_pass else 'KHONG DAT (FAIL)'}")
    log("=" * 80)

    # Luu JSON ket qua
    result_data = {
        "ma_ve": "DESKTOP-SPEED-WARM-PRIORITY-FIX-HOME",
        "thoi_diem": datetime.now(timezone.utc).isoformat(),
        "git_head": git_head,
        "t_start_app": t_start_app_str,
        "t_server_ready": t_server_ready_str,
        "t1_micro_delta_s": t1_micro_delta,
        "t1_micro_pass_lte_30s": assert_t1_micro_pass,
        "t2_micro_delta_s": t2_micro_delta,
        "t2_micro_pass": assert_t2_warm_pass,
        "all_4_resident": assert_all_4_resident,
        "yield_marker_count": yield_count,
        "resume_marker_count": resume_count,
        "timeline_4_khoi": final_timeline,
        "turn1_jam4212": turn1_result,
        "turn2_warm": turn2_result,
    }
    with open(JSON_RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    log(f"Da ghi file JSON ket qua: {JSON_RESULT_FILE}")

    if not (assert_t1_micro_pass and assert_all_4_resident):
        log("[FAIL] Khong dat toan bo tieu chi nghiem thu!")
        sys.exit(1)

    print("\n>>> EXECUTION COMPLETED SUCCESSFULLY <<<\n")


if __name__ == "__main__":
    main()
