"""Script do thuc nghiem nap am theo nhu cau (Lazy Warming) tren may nha.
Ticket: DESKTOP-SPEED-LAZY-WARM-HOME
Moi truong: May nha h410asrock (CPU-only, BB-CONFIG-PARITY-01)

Quy trinh do:
1. Don dep sach toan bo tien trinh streamlit va bge_subprocess_worker cu.
2. Theo doi dong thoi gian daemon log + named pipe cua ca 4 khoi (lsu, dieu_tra_loi, tong_hop, tri_thuc) va lay mau RAM (psutil) moi 0.5s.
3. Pha 1 (Mo app + mo so dau tien thuoc khoi LSU - NB-LAZY-LSU 'Dieu tra loi LSU'):
   - Xac minh CHI DUY NHAT 1 worker (lsu) duoc sinh ra khi mo app + mo so dau tien; 3 khoi con lai (dieu_tra_loi, tong_hop, tri_thuc) KHONG sinh worker (0 worker).
   - Do thoi gian tu luc mo app -> worker lsu san sang (so voi thoi gian nap thuan init_ms cua 1 khoi + <= 45s).
   - Do RAM dinh cua ung dung khi mo 1 so (Streamlit + 1 worker <= 3.5 GB) va RAM toan he thong.
   - Hoi Luot 1 (C7620 tren khoi LSU) de xac minh san sang tra loi chinh xac.
4. Pha 2 (Chuyen sang so thu 2 thuoc khoi chua nap - NB-LAZY-DTL 'So Dieu tra loi' -> dieu_tra_loi):
   - Chuyen so sang NB-LAZY-DTL, kich hoat nap am theo nhu cau (on-demand warming) cho dieu_tra_loi.
   - Gui Luot 2 (JAM4212) ngay khi vua chuyen so, chup anh dong trang thai UI 'Dang nap bo doc cho kho Dieu tra loi...' va ghi nhan WORKER_WARM_LOOP_STEP.
   - Do thoi gian nap khi chuyen so sang khoi khac, RAM dinh 2 worker, va xac minh 2 khoi chua dung (tong_hop, tri_thuc) van = 0 worker.
5. Pha 3 (Cau hoi can khoi thu 3 chua nap - tong_hop):
   - Hoi Luot 3 (TH01 Touch Panel Storage) tren khoi tong_hop, xac minh tu dong nap khoi tong_hop theo nhu cau, cho san sang va tra loi chinh xac, khong bo sot khoi.
   - Xac minh khoi tri_thuc (khong dung trong phien) van KHONG bi nap (0 worker).
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
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

import psutil

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

from aios_habit.workspace_chat_models import DocumentNotebook, WorkspaceConversation
from aios_habit.workspace_chat_store import save_notebook, save_conversation, load_messages
from aios_habit.workspace_chat_rag_v2_adapter import (
    WorkspaceChatRagV2CanaryConfig,
    _resolve_target_pipe_config,
)
from aios_habit.rag_v2.bge_subprocess_client import (
    _pipe_instance_available,
    pipe_name_for_config,
)
from playwright.sync_api import sync_playwright

PORT = 8572
URL = f"http://localhost:{PORT}"

OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SERVER_LOG_FILE = OUT_DIR / "server_desktop_speed_lazy_warm_home.log"
SESSION_LOG_FILE = OUT_DIR / "session_desktop_speed_lazy_warm_home.log"
JSON_RESULT_FILE = OUT_DIR / "ket-qua-desktop-speed-lazy-warm-home.json"

SCREENSHOT_P1 = OUT_DIR / "anh-lazy-warm-01-open-nb1-lsu.png"
SCREENSHOT_P2_WARM = OUT_DIR / "anh-lazy-warm-02a-warming-dtl.png"
SCREENSHOT_P2_DONE = OUT_DIR / "anh-lazy-warm-02b-switch-nb2-dtl.png"
SCREENSHOT_P3_DONE = OUT_DIR / "anh-lazy-warm-03-cross-tonghop.png"

COLLECTIONS = ("lsu", "dieu_tra_loi", "tong_hop", "tri_thuc")


def resolve_collection_pipes_and_logs() -> tuple[dict[str, str], dict[str, Path]]:
    cfg = WorkspaceChatRagV2CanaryConfig.from_env()
    pipes: dict[str, str] = {}
    logs: dict[str, Path] = {}
    for col in COLLECTIONS:
        p_cfg = _resolve_target_pipe_config(cfg, collection_id=col)
        pipes[col] = pipe_name_for_config(p_cfg)
        logs[col] = Path(p_cfg.runtime_root) / "logs" / "bge_worker_daemon.stderr.log"
    return pipes, logs


PIPE_NAMES, DAEMON_LOGS = resolve_collection_pipes_and_logs()

QUESTION_C7620 = (
    "Mã lỗi C7620 trên dòng máy in Kyocera là lỗi gì, "
    "nguyên nhân và đối sách xử lý ra sao?"
)
QUESTION_JAM4212 = (
    "Theo báo cáo điều tra KTD-2026-06-0647 trên máy Iris2024-C33, "
    "hiện tượng và nguyên nhân gây ra mã lỗi kẹt giấy JAM4212 là gì?"
)
QUESTION_TH01 = (
    "Theo tài liệu Tab led cam ung.pdf (Touch Panel Specification), "
    "điều kiện nhiệt độ và độ ẩm tiêu chuẩn để bảo quản (Storage) touch panel là bao nhiêu?"
)


def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(SESSION_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


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


def kill_server(proc: subprocess.Popen) -> None:
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


class WorkerAndRamTracker:
    """Theo doi tien trinh nap 4 khoi va dung luong RAM (App RAM + System RAM)."""

    def __init__(self, initial_offsets: dict[str, int]) -> None:
        self.offsets = dict(initial_offsets)
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.current_phase = "startup"
        self.timeline: dict[str, dict[str, Any]] = {
            col: {
                "pipe_name": PIPE_NAMES[col],
                "log_path": str(DAEMON_LOGS[col]),
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
            for col in COLLECTIONS
        }
        self.phase_ram_stats: dict[str, dict[str, Any]] = {}
        self._ensure_phase_bucket("startup")

    def _ensure_phase_bucket(self, phase: str) -> None:
        if phase not in self.phase_ram_stats:
            self.phase_ram_stats[phase] = {
                "peak_app_rss_mb": 0.0,
                "peak_app_rss_gb": 0.0,
                "peak_streamlit_rss_mb": 0.0,
                "peak_workers_rss_mb": 0.0,
                "max_worker_count": 0,
                "worker_peaks_mb": {},
                "peak_system_used_gb": 0.0,
                "peak_system_percent": 0.0,
                "min_system_avail_gb": 999.0,
                "samples": 0,
            }

    def set_phase(self, phase: str) -> None:
        with self.lock:
            self._ensure_phase_bucket(phase)
            self.current_phase = phase
        log(f"[PHASE] Chuyen sang pha do: {phase}")

    def snapshot_workers_spawned(self) -> dict[str, bool]:
        with self.lock:
            return {
                col: (
                    self.timeline[col]["spawn_ts"] is not None
                    or self.timeline[col]["pipe_available_ts"] is not None
                )
                for col in COLLECTIONS
            }

    def _sample_ram(self) -> None:
        try:
            vm = psutil.virtual_memory()
            sys_used_gb = (vm.total - vm.available) / (1024 ** 3)
            sys_avail_gb = vm.available / (1024 ** 3)
            sys_pct = float(vm.percent)

            streamlit_mb = 0.0
            workers_mb = 0.0
            worker_pids_mb: dict[str, float] = {}

            for proc in psutil.process_iter(["pid", "name", "cmdline", "memory_info"]):
                try:
                    cmdline_list = proc.info.get("cmdline") or []
                    if not cmdline_list:
                        continue
                    cmdline = " ".join(cmdline_list)
                    mem_info = proc.info.get("memory_info")
                    if mem_info is None:
                        continue
                    rss_mb = mem_info.rss / (1024 ** 2)
                    if "bge_subprocess_worker" in cmdline and rss_mb > 20.0:
                        workers_mb += rss_mb
                        matched_col = f"pid_{proc.info['pid']}"
                        for col, pipe_str in PIPE_NAMES.items():
                            pipe_tail = pipe_str.split("\\")[-1]
                            if pipe_tail in cmdline:
                                matched_col = f"{col} (PID {proc.info['pid']})"
                                break
                        worker_pids_mb[matched_col] = round(rss_mb, 1)
                    elif "workspace_chat_app.py" in cmdline and rss_mb > 20.0:
                        streamlit_mb += rss_mb
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            total_app_mb = streamlit_mb + workers_mb
            total_app_gb = total_app_mb / 1024.0

            with self.lock:
                bucket = self.phase_ram_stats[self.current_phase]
                bucket["samples"] += 1
                if total_app_mb > bucket["peak_app_rss_mb"]:
                    bucket["peak_app_rss_mb"] = round(total_app_mb, 1)
                    bucket["peak_app_rss_gb"] = round(total_app_gb, 3)
                if streamlit_mb > bucket["peak_streamlit_rss_mb"]:
                    bucket["peak_streamlit_rss_mb"] = round(streamlit_mb, 1)
                if workers_mb > bucket["peak_workers_rss_mb"]:
                    bucket["peak_workers_rss_mb"] = round(workers_mb, 1)
                if len(worker_pids_mb) > bucket["max_worker_count"]:
                    bucket["max_worker_count"] = len(worker_pids_mb)
                for k, v in worker_pids_mb.items():
                    if v > bucket["worker_peaks_mb"].get(k, 0.0):
                        bucket["worker_peaks_mb"][k] = v
                if sys_used_gb > bucket["peak_system_used_gb"]:
                    bucket["peak_system_used_gb"] = round(sys_used_gb, 2)
                if sys_pct > bucket["peak_system_percent"]:
                    bucket["peak_system_percent"] = round(sys_pct, 1)
                if sys_avail_gb < bucket["min_system_avail_gb"]:
                    bucket["min_system_avail_gb"] = round(sys_avail_gb, 2)
        except Exception:
            pass

    def run_poll(self) -> None:
        last_ram_poll = 0.0
        while not self.stop_event.is_set():
            now_dt = datetime.now()
            now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

            # Doc cac dong moi tu daemon logs (khong goi WaitNamedPipeW de tranh tranh chap pipe)
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
                                    self.timeline[col]["pipe_available_ts"] = event_ts
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
                                    log(
                                        f"[TIMELINE] Khoi '{col}' DAT TRANG THAI SAN SANG/RESIDENT "
                                        f"(init_total={ms_val}ms) tai: {event_ts}"
                                    )
                except Exception:
                    pass

            now_mono = time.monotonic()
            if now_mono - last_ram_poll >= 0.5:
                self._sample_ram()
                last_ram_poll = now_mono

            time.sleep(0.1)

    def stop(self) -> None:
        self.stop_event.set()


def parse_conv_markers(log_file: Path, conv_id: str) -> dict[str, Any]:
    res: dict[str, Any] = {
        "conv_id": conv_id,
        "qa_start_line": "",
        "micro_line": "",
        "warm_loop_lines": [],
        "first_token_line": "",
        "complete_line": "",
        "total_s": None,
        "ttft_s": None,
        "warm_wait_s": 0.0,
    }
    if not log_file.exists():
        return res
    text = log_file.read_text(encoding="utf-8", errors="replace")
    in_window = False
    for raw in text.splitlines():
        line = raw.strip()
        if "[STREAMING_QA_START]" in line:
            if f"conv={conv_id}" in line:
                in_window = True
                res["qa_start_line"] = line
            else:
                in_window = False
        if not in_window:
            continue
        if "[WORKER_WARM_LOOP_STEP]" in line and line not in res["warm_loop_lines"]:
            res["warm_loop_lines"].append(line)
            m_w = re.search(r"elapsed_wait_s=([\d\.]+)", line)
            if m_w:
                res["warm_wait_s"] = max(res["warm_wait_s"], float(m_w.group(1)))
        if "[RETRIEVAL_MICRO_TIMING]" in line and not res["micro_line"]:
            res["micro_line"] = line
        if "[STREAMING_QA_FIRST_TOKEN]" in line and f"conv={conv_id}" in line and not res["first_token_line"]:
            res["first_token_line"] = line
            m_t = re.search(r"ttft_s=([\d\.]+)", line)
            if m_t:
                res["ttft_s"] = float(m_t.group(1))
        if "[STREAMING_QA_COMPLETE]" in line and f"conv={conv_id}" in line and not res["complete_line"]:
            res["complete_line"] = line
            m_tot = re.search(r"total_s=([\d\.]+)", line)
            if m_tot:
                res["total_s"] = float(m_tot.group(1))
            in_window = False
    return res


def submit_question_and_wait(
    page: Any,
    conv_id: str,
    question: str,
    *,
    capture_warming_screenshot: Path | None = None,
    done_screenshot: Path | None = None,
    timeout_s: float = 360.0,
) -> dict[str, Any]:
    page.wait_for_selector('textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"]', timeout=45000)
    textarea = page.locator('textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"]').first
    textarea.wait_for(state="visible", timeout=30000)
    textarea.click()
    textarea.fill(question)
    page.wait_for_timeout(400)

    t_fire = datetime.now()
    t_fire_str = t_fire.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log(f"[TURN_FIRE] conv={conv_id} tai {t_fire_str}: {question}")

    send_btn = page.locator(f'[class*="st-key-wsc_ask_{conv_id}"] button, [class*="st-key-wsc-action-"] button').first
    if send_btn.count() > 0:
        send_btn.click(force=True)
    else:
        textarea.press("Control+Enter")

    warming_ui_captured = False
    warming_ui_text = ""
    user_msg_confirmed = False

    t_watch = time.time()
    while time.time() - t_watch < timeout_s:
        if not user_msg_confirmed and (time.time() - t_watch) >= 8.0:
            msgs_now = load_messages(conv_id)
            if any(m.role == "user" for m in msgs_now):
                user_msg_confirmed = True
            else:
                try:
                    val = textarea.input_value()
                    if val:
                        log(f"[RETRY_SEND] Textarea van con text cho conv={conv_id}, gui lai...")
                        if send_btn.count() > 0:
                            send_btn.click(force=True)
                        else:
                            textarea.press("Control+Enter")
                except Exception:
                    pass
                user_msg_confirmed = True

        if not warming_ui_captured:
            try:
                body_text = page.locator("body").inner_text(timeout=1500)
                for line in body_text.splitlines():
                    if "Đang nạp bộ đọc cho kho" in line:
                        warming_ui_text = line.strip()
                        warming_ui_captured = True
                        log(f"[UI_WARMING_INDICATOR] Bat duoc dong trang thai tren giao dien: {warming_ui_text}")
                        if capture_warming_screenshot is not None:
                            page.screenshot(path=str(capture_warming_screenshot))
                            log(f"[SCREENSHOT] Da chup anh UI warming tai: {capture_warming_screenshot}")
                        break
            except Exception:
                pass

        markers = parse_conv_markers(SERVER_LOG_FILE, conv_id)
        if markers["complete_line"]:
            log(f"[TURN_DONE] {markers['complete_line']}")
            break
        page.wait_for_timeout(500)

    page.wait_for_timeout(2500)
    if done_screenshot is not None:
        page.screenshot(path=str(done_screenshot))
        log(f"[SCREENSHOT] Da chup anh hoan tat luot tai: {done_screenshot}")

    msgs = load_messages(conv_id)
    ast_msgs = [m for m in msgs if m.role == "assistant"]
    ans_text = ast_msgs[-1].content if ast_msgs else ""
    markers = parse_conv_markers(SERVER_LOG_FILE, conv_id)
    markers["t_fire"] = t_fire_str
    markers["warming_ui_text"] = warming_ui_text
    markers["answer_length"] = len(ans_text)
    markers["answer_preview"] = ans_text[:350]
    return markers


def main() -> None:
    if SESSION_LOG_FILE.exists():
        SESSION_LOG_FILE.unlink()

    log("=" * 88)
    log("BAT DAU DO THUC NGHIEM: DESKTOP-SPEED-LAZY-WARM-HOME")
    log("=" * 88)
    git_head = get_git_head()
    log(f"[GIT] Commit HEAD: {git_head}")
    for col in COLLECTIONS:
        log(f"[CONFIG] Khoi '{col}': pipe={PIPE_NAMES[col]} | log={DAEMON_LOGS[col]}")

    # Sao luu notebooks.jsonl de khoi phuc sau phien do
    notebooks_backup = store.NOTEBOOKS_FILE.read_bytes() if store.NOTEBOOKS_FILE.exists() else b""

    nb1_id = "NB-LAZY-LSU"
    nb2_id = "NB-LAZY-DTL"

    try:
        save_notebook(DocumentNotebook(
            id=nb1_id,
            title="Điều tra lỗi LSU",
            description="Sổ kiểm tra nạp ấm theo nhu cầu khối LSU",
            collection_id="lsu",
        ))
        save_notebook(DocumentNotebook(
            id=nb2_id,
            title="Sổ Điều tra lỗi",
            description="Sổ kiểm tra chuyển sổ nạp ấm theo nhu cầu khối Điều tra lỗi",
            collection_id="dieu_tra_loi",
        ))

        kill_all_workers_and_servers()

        initial_offsets: dict[str, int] = {}
        for col, path in DAEMON_LOGS.items():
            initial_offsets[col] = path.stat().st_size if path.exists() else 0

        vm_before = psutil.virtual_memory()
        log(
            f"[RAM_BASELINE] System RAM truoc khi mo app: "
            f"used={(vm_before.total - vm_before.available) / (1024**3):.2f} GB / "
            f"{vm_before.total / (1024**3):.2f} GB ({vm_before.percent:.1f}%)"
        )

        tracker = WorkerAndRamTracker(initial_offsets)
        tracker_thread = threading.Thread(target=tracker.run_poll, daemon=True)
        tracker_thread.start()

        # =========================================================================
        # PHA 1: MO APP + MO SO DAU TIEN (NB-LAZY-LSU -> KHOI LSU)
        # =========================================================================
        tracker.set_phase("phase1_open_first_notebook_lsu")
        t_start_app = datetime.now()
        t_start_app_str = t_start_app.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log(f"[PHASE 1] Khoi dong Streamlit server tai {t_start_app_str}...")
        server_proc = start_server(PORT, SERVER_LOG_FILE)

        if not wait_for_server(PORT, timeout=90):
            log("[ERROR] Streamlit server khong phan hoi sau 90s!")
            kill_server(server_proc)
            tracker.stop()
            sys.exit(1)

        t_server_ready = datetime.now()
        t_server_ready_str = t_server_ready.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log(
            f"[PHASE 1] Server san sang sau {(t_server_ready - t_start_app).total_seconds():.2f}s "
            f"tai {t_server_ready_str}"
        )

        conv1_id = f"CONV-LAZY-P1-LSU-{uuid.uuid4().hex[:6].upper()}"
        conv2_id = f"CONV-LAZY-P2-DTL-{uuid.uuid4().hex[:6].upper()}"
        conv3_id = f"CONV-LAZY-P3-TH-{uuid.uuid4().hex[:6].upper()}"

        save_conversation(WorkspaceConversation(
            id=conv1_id,
            notebook_id=nb1_id,
            title="Pha 1 - Mở sổ đầu tiên LSU (C7620)",
            ai_mode="grounded",
        ))
        save_conversation(WorkspaceConversation(
            id=conv2_id,
            notebook_id=nb2_id,
            title="Pha 2 - Chuyển sang sổ Điều tra lỗi (JAM4212)",
            ai_mode="grounded",
        ))
        save_conversation(WorkspaceConversation(
            id=conv3_id,
            notebook_id=nb2_id,
            title="Pha 3 - Câu hỏi sang khối Tổng hợp (TH01)",
            ai_mode="grounded",
        ))

        phase1_summary: dict[str, Any] = {}
        phase2_summary: dict[str, Any] = {}
        phase3_summary: dict[str, Any] = {}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1600, "height": 1000})
            page = context.new_page()

            nav1_url = f"{URL}/?nb={nb1_id}&conv={conv1_id}&block=lsu"
            log(f"[PHASE 1] Mo so dau tien tren giao dien: {nav1_url}")
            page.goto(nav1_url, wait_until="networkidle", timeout=60000)
            page.wait_for_selector('textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"]', timeout=45000)

            # Cho worker LSU dat trang thai san sang
            log("[PHASE 1] Dang cho worker khoi 'lsu' nap xong...")
            t_wait_lsu = time.time()
            p1_warming_ui_text = ""
            while time.time() - t_wait_lsu < 180:
                if not p1_warming_ui_text:
                    try:
                        btxt = page.locator("body").inner_text(timeout=1500)
                        for ln in btxt.splitlines():
                            if "Đang nạp bộ đọc cho kho" in ln:
                                p1_warming_ui_text = ln.strip()
                                log(f"[PHASE 1 UI] {p1_warming_ui_text}")
                                break
                    except Exception:
                        pass
                with tracker.lock:
                    if tracker.timeline["lsu"]["ready_ts"] is not None:
                        break
                page.wait_for_timeout(300)

            t_lsu_ready_dt = datetime.now()
            with tracker.lock:
                lsu_info = dict(tracker.timeline["lsu"])
            spawned_after_p1_warm = tracker.snapshot_workers_spawned()
            log(f"[PHASE 1] Trang thai worker cac khoi sau khi nap so 1: {spawned_after_p1_warm}")

            # Tinh thoi gian tu mo app den san sang
            lsu_ready_ts_str = lsu_info.get("ready_ts")
            if lsu_ready_ts_str:
                lsu_ready_dt = datetime.strptime(lsu_ready_ts_str, "%Y-%m-%d %H:%M:%S.%f")
            else:
                lsu_ready_dt = t_lsu_ready_dt
            open_to_ready_s = (lsu_ready_dt - t_start_app).total_seconds()
            pure_lsu_init_s = (lsu_info.get("init_total_ms") or 0.0) / 1000.0
            overhead_over_pure_s = open_to_ready_s - pure_lsu_init_s
            log(
                f"[PHASE 1 METRIC] Mo app -> LSU san sang: {open_to_ready_s:.2f}s "
                f"(Nap thuan 1 khoi: {pure_lsu_init_s:.2f}s, Chenh lech khoi dong: +{overhead_over_pure_s:.2f}s <= 45s)"
            )

            # Hoi Luot 1 (C7620) tren so 1 (LSU da am)
            turn1_res = submit_question_and_wait(
                page,
                conv1_id,
                QUESTION_C7620,
                done_screenshot=SCREENSHOT_P1,
            )
            spawned_after_p1_turn = tracker.snapshot_workers_spawned()
            with tracker.lock:
                p1_ram = dict(tracker.phase_ram_stats["phase1_open_first_notebook_lsu"])

            phase1_summary = {
                "notebook_id": nb1_id,
                "target_collection": "lsu",
                "t_start_app": t_start_app_str,
                "t_server_ready": t_server_ready_str,
                "lsu_spawn_ts": lsu_info.get("spawn_ts"),
                "lsu_ready_ts": lsu_ready_ts_str,
                "pure_init_s": round(pure_lsu_init_s, 3),
                "app_open_to_ready_s": round(open_to_ready_s, 3),
                "overhead_over_pure_s": round(overhead_over_pure_s, 3),
                "workers_spawned_after_open": spawned_after_p1_warm,
                "workers_spawned_after_turn1": spawned_after_p1_turn,
                "warming_ui_text_on_open": p1_warming_ui_text,
                "ram": p1_ram,
                "turn1_c7620": turn1_res,
            }

            # =========================================================================
            # PHA 2: CHUYEN SO SANG KHOI CHUA NAP (NB-LAZY-DTL -> KHOI DIEU_TRA_LOI)
            # =========================================================================
            tracker.set_phase("phase2_switch_notebook_dieu_tra_loi")
            t_switch_nb2 = datetime.now()
            t_switch_nb2_str = t_switch_nb2.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            nav2_url = f"{URL}/?nb={nb2_id}&conv={conv2_id}&block=dieu_tra_loi"
            log(f"[PHASE 2] Chuyen sang so thu 2 (NB-LAZY-DTL / dieu_tra_loi) tai {t_switch_nb2_str}: {nav2_url}")
            page.goto(nav2_url, wait_until="networkidle", timeout=60000)

            # Gui ngay cau hoi JAM4212 khi dieu_tra_loi dang nap am theo nhu cau
            turn2_res = submit_question_and_wait(
                page,
                conv2_id,
                QUESTION_JAM4212,
                capture_warming_screenshot=SCREENSHOT_P2_WARM,
                done_screenshot=SCREENSHOT_P2_DONE,
            )

            with tracker.lock:
                dtl_info = dict(tracker.timeline["dieu_tra_loi"])
                p2_ram = dict(tracker.phase_ram_stats["phase2_switch_notebook_dieu_tra_loi"])
            spawned_after_p2 = tracker.snapshot_workers_spawned()

            dtl_ready_ts_str = dtl_info.get("ready_ts")
            if dtl_ready_ts_str:
                dtl_ready_dt = datetime.strptime(dtl_ready_ts_str, "%Y-%m-%d %H:%M:%S.%f")
                switch_to_ready_s = (dtl_ready_dt - t_switch_nb2).total_seconds()
            else:
                switch_to_ready_s = 0.0
            pure_dtl_init_s = (dtl_info.get("init_total_ms") or 0.0) / 1000.0
            log(
                f"[PHASE 2 METRIC] Chuyen so -> dieu_tra_loi san sang: {switch_to_ready_s:.2f}s "
                f"(Nap thuan dieu_tra_loi: {pure_dtl_init_s:.2f}s) | Workers spawned: {spawned_after_p2}"
            )

            phase2_summary = {
                "notebook_id": nb2_id,
                "target_collection": "dieu_tra_loi",
                "t_switch_notebook": t_switch_nb2_str,
                "dtl_spawn_ts": dtl_info.get("spawn_ts"),
                "dtl_ready_ts": dtl_ready_ts_str,
                "pure_init_s": round(pure_dtl_init_s, 3),
                "switch_to_ready_s": round(switch_to_ready_s, 3),
                "workers_spawned_after_phase2": spawned_after_p2,
                "ram": p2_ram,
                "turn2_jam4212": turn2_res,
            }

            # =========================================================================
            # PHA 3: CAU HOI CAN KHOI THU 3 CHUA NAP (TONG_HOP)
            # =========================================================================
            tracker.set_phase("phase3_cross_collection_tong_hop")
            t_switch_p3 = datetime.now()
            t_switch_p3_str = t_switch_p3.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            nav3_url = f"{URL}/?nb={nb2_id}&conv={conv3_id}&block=tong_hop"
            log(f"[PHASE 3] Chuyen sang khoi thu 3 chua nap (tong_hop) tai {t_switch_p3_str}: {nav3_url}")
            page.goto(nav3_url, wait_until="networkidle", timeout=60000)

            turn3_res = submit_question_and_wait(
                page,
                conv3_id,
                QUESTION_TH01,
                done_screenshot=SCREENSHOT_P3_DONE,
            )

            with tracker.lock:
                th_info = dict(tracker.timeline["tong_hop"])
                p3_ram = dict(tracker.phase_ram_stats["phase3_cross_collection_tong_hop"])
            spawned_after_p3 = tracker.snapshot_workers_spawned()

            th_ready_ts_str = th_info.get("ready_ts")
            if th_ready_ts_str:
                th_ready_dt = datetime.strptime(th_ready_ts_str, "%Y-%m-%d %H:%M:%S.%f")
                p3_switch_to_ready_s = (th_ready_dt - t_switch_p3).total_seconds()
            else:
                p3_switch_to_ready_s = 0.0
            pure_th_init_s = (th_info.get("init_total_ms") or 0.0) / 1000.0
            log(
                f"[PHASE 3 METRIC] Chuyen khoi -> tong_hop san sang: {p3_switch_to_ready_s:.2f}s "
                f"(Nap thuan tong_hop: {pure_th_init_s:.2f}s) | Workers spawned: {spawned_after_p3}"
            )

            phase3_summary = {
                "notebook_id": nb2_id,
                "target_collection": "tong_hop",
                "t_switch_block": t_switch_p3_str,
                "th_spawn_ts": th_info.get("spawn_ts"),
                "th_ready_ts": th_ready_ts_str,
                "pure_init_s": round(pure_th_init_s, 3),
                "switch_to_ready_s": round(p3_switch_to_ready_s, 3),
                "workers_spawned_after_phase3": spawned_after_p3,
                "ram": p3_ram,
                "turn3_th01": turn3_res,
            }

            browser.close()

        tracker.stop()
        kill_server(server_proc)
        kill_all_workers_and_servers()

        with tracker.lock:
            final_timeline = dict(tracker.timeline)

        result_payload = {
            "ma_ve": "DESKTOP-SPEED-LAZY-WARM-HOME",
            "thoi_diem": datetime.now(timezone.utc).isoformat(),
            "git_head": git_head,
            "ram_baseline_system_used_gb": round((vm_before.total - vm_before.available) / (1024**3), 2),
            "ram_baseline_system_total_gb": round(vm_before.total / (1024**3), 2),
            "phase1_open_first_notebook_lsu": phase1_summary,
            "phase2_switch_notebook_dieu_tra_loi": phase2_summary,
            "phase3_cross_collection_tong_hop": phase3_summary,
            "timeline_4_khoi": final_timeline,
        }

        with open(JSON_RESULT_FILE, "w", encoding="utf-8") as f:
            json.dump(result_payload, f, ensure_ascii=False, indent=2)
        log(f"[JSON] Da luu ket qua do tai: {JSON_RESULT_FILE}")

    finally:
        kill_all_workers_and_servers()
        if notebooks_backup:
            store.NOTEBOOKS_FILE.write_bytes(notebooks_backup)
            log("[CLEANUP] Da khoi phuc tep notebooks.jsonl ve trang thai ban dau.")


if __name__ == "__main__":
    main()
