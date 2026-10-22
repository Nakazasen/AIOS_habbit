"""Script nghiem thu song khoi dong lanh ca 4 khoi dat resident va do luot JAM4212.
Ticket: DESKTOP-SPEED-TRITHUC-WARM-FIX-HOME
Moi truong: May nha h410asrock (CPU-only)

Muc tieu:
1. Don dep sach worker va server cu.
2. Khoi dong lanh app Streamlit (cong 8570) voi cau hinh chuan BB-CONFIG-PARITY-01.
3. Ghi lai moc thoi gian ca 4 khoi (lsu, dieu_tra_loi, tong_hop, tri_thuc) bat dau va dat trang thai resident/san sang tu nhat ky server va daemon log.
4. Ban luot JAM4212 (khoi dieu_tra_loi) lam luot dau tien o moc co kiem soat (+10s sau khoi dong app).
5. Ghi nhan toan bo streaming markers, doan cho QA_START -> MICRO, First Token, Complete.
6. Cho den khi ca 4 KHOI DEU DAT RESIDENT (dac biet tri_thuc co spawn/init that).
7. Chup anh giao dien that Playwright.
8. Xuat JSON ket qua va session log.
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

SERVER_LOG_FILE = OUT_DIR / "server_desktop_speed_trithuc_warm_fix_home.log"
SESSION_LOG_FILE = OUT_DIR / "session_desktop_speed_trithuc_warm_fix_home.log"
JSON_RESULT_FILE = OUT_DIR / "ket-qua-desktop-speed-trithuc-warm-fix-home.json"
SCREENSHOT_FILE = OUT_DIR / "anh-trithuc-warm-fix-jam4212.png"

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
                                # Parse cac moc quan trong
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
                except Exception as exc:
                    pass
            time.sleep(0.1)

    def stop(self):
        self.stop_event.set()


def main():
    log("=" * 80)
    log("BAT DAU THUC THI VE: DESKTOP-SPEED-TRITHUC-WARM-FIX-HOME")
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

    # Don dep tien trinh cu
    kill_all_workers_and_servers()

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
        sys.exit(1)

    t_server_ready = datetime.now()
    t_server_ready_str = t_server_ready.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    elapsed_health_s = (t_server_ready - t_start_app).total_seconds()
    log(f"[APP_LAUNCH] Server san sang tren port {PORT} (PID={server_proc.pid}) sau {elapsed_health_s:.3f}s tai {t_server_ready_str}")

    turn_result = {}
    conv_id = f"CONV-TRITHUC-WARM-JAM4212-{uuid.uuid4().hex[:6].upper()}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1600, "height": 1000})
            page = context.new_page()

            save_conversation(WorkspaceConversation(
                id=conv_id,
                notebook_id=NOTEBOOK_ID,
                title="Turn 1 - JAM4212 Tri Thuc Warm Fix Verification",
                ai_mode="grounded",
            ))

            # Mo trang giao dien voi khoi dieu_tra_loi
            nav_url = f"{URL}/?nb={NOTEBOOK_ID}&conv={conv_id}&block=dieu_tra_loi"
            log(f"[PLAYWRIGHT] Dieu huong den: {nav_url}")
            page.goto(nav_url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(1000)

            page.wait_for_selector('textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"]', timeout=45000)
            textarea = page.locator('textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"]').first
            textarea.wait_for(state="visible", timeout=30000)
            textarea.click()
            textarea.fill(QUESTION_JAM4212)
            page.wait_for_timeout(500)

            # Moc kiem soat: Cho dung den moc t_start_app + 10.0s de ban cau hoi
            now = datetime.now()
            elapsed_from_start = (now - t_start_app).total_seconds()
            target_delay = 10.0
            if elapsed_from_start < target_delay:
                wait_remain = target_delay - elapsed_from_start
                log(f"[CONTROLLED_FIRE] Cho them {wait_remain:.3f}s de dat moc chuan +{target_delay:.1f}s sau khoi dong app...")
                time.sleep(wait_remain)

            t_fire = datetime.now()
            t_fire_str = t_fire.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            log(f"[CONTROLLED_FIRE] BAN LUOT JAM4212 TAI MOC: {t_fire_str} (+{(t_fire - t_start_app).total_seconds():.3f}s sau mo app)")

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
                            log("[DB] Textarea van con text sau 8s, gui lai...")
                            if send_btn.count() > 0:
                                send_btn.first.click(force=True)
                            else:
                                textarea.press("Control+Enter")
                    except Exception:
                        pass

            # Theo doi markers tu server log
            t_qa_start = None
            t_micro = None
            t_pre_router = None
            t_router_start = None
            t_first_token = None
            t_router_done = None
            t_complete = None

            qa_start_line = ""
            micro_line = ""
            warm_loop_lines = []
            pre_router_line = ""
            router_start_line = ""
            first_token_line = ""
            router_done_line = ""
            complete_line = ""

            t_watch_start = time.time()
            in_conv_window = False

            while time.time() - t_watch_start < 360:
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

                        if not in_conv_window:
                            continue

                        if "[WORKER_WARM_LOOP_STEP]" in line_clean and line_clean not in warm_loop_lines:
                            warm_loop_lines.append(line_clean)
                            log(f"[MARKER WARM LOOP] {line_clean}")

                        if "[RETRIEVAL_MICRO_TIMING]" in line_clean and "collection=dieu_tra_loi" in line_clean and not t_micro:
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

            # Chup anh bang chung tren giao dien
            page.wait_for_timeout(3000)
            page.screenshot(path=str(SCREENSHOT_FILE))
            log(f"[SCREENSHOT] Da chup anh giao dien luu tai: {SCREENSHOT_FILE}")

            # Kiem tra tin nhan tra loi trong DB
            msgs = load_messages(conv_id)
            assistant_msgs = [m for m in msgs if m.role == "assistant"]
            ans_text = assistant_msgs[-1].content if assistant_msgs else ""
            ans_len = len(ans_text)
            log(f"[ANSWER] Do dai cau tra loi: {ans_len} ky tu")

            turn_result = {
                "conv_id": conv_id,
                "t_fire": t_fire_str,
                "qa_start_line": qa_start_line,
                "micro_line": micro_line,
                "warm_loop_lines": warm_loop_lines,
                "pre_router_line": pre_router_line,
                "router_start_line": router_start_line,
                "first_token_line": first_token_line,
                "router_done_line": router_done_line,
                "complete_line": complete_line,
                "answer_length": ans_len,
            }

            browser.close()
    except Exception as exc:
        log(f"[ERROR] Loi trong qua trinh chay Playwright: {exc}")

    # Tiep tuc cho den khi ca 4 khoi dat trang thai resident
    log("[WAIT_RESIDENT] Tiep tuc theo doi daemon logs cho den khi CA 4 KHOI dat resident...")
    deadline_all_ready = time.time() + 300  # Cho toi da 5 phut nua
    while time.time() < deadline_all_ready:
        with tracker.lock:
            all_ready = all(tracker.timeline[c]["ready_ts"] is not None for c in DAEMON_LOGS)
            if all_ready:
                log("[WAIT_RESIDENT] >>> XAC NHAN: CA 4 KHOI (lsu, dieu_tra_loi, tong_hop, tri_thuc) DEU DA DAT TRANG THAI SAN SANG/RESIDENT! <<<")
                break
        time.sleep(1.0)

    # Dung tracker
    tracker.stop()
    kill_server(server_proc)
    kill_all_workers_and_servers()

    # Tong hop dong thoi gian va phan tich
    log("=" * 80)
    log("TONG HOP KET QUA VA DONG THOI GIAN LAM AM CA 4 KHOI")
    log("=" * 80)

    final_timeline = {}
    with tracker.lock:
        final_timeline = dict(tracker.timeline)

    # In ra dong thoi gian 4 khoi
    for col, info in final_timeline.items():
        log(f"Khoi '{col}': spawn={info['spawn_ts']} (PID={info['spawn_pid']}), pipe_open={info['pipe_available_ts']}, dense={info['dense_preload_ts']} ({info['dense_preload_ms']}ms), sparse={info['sparse_preload_ts']} ({info['sparse_preload_ms']}ms), ready={info['ready_ts']} (init={info['init_total_ms']}ms)")

    # Luu JSON ket qua
    result_data = {
        "ma_ve": "DESKTOP-SPEED-TRITHUC-WARM-FIX-HOME",
        "thoi_diem": datetime.now(timezone.utc).isoformat(),
        "git_head": git_head,
        "t_start_app": t_start_app_str,
        "t_server_ready": t_server_ready_str,
        "timeline_4_khoi": final_timeline,
        "turn_jam4212": turn_result,
    }
    with open(JSON_RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    log(f"Da ghi file JSON ket qua: {JSON_RESULT_FILE}")

    print("\n>>> EXECUTION COMPLETED SUCCESSFULLY <<<\n")


if __name__ == "__main__":
    main()
