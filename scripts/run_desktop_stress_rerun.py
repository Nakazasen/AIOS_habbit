"""Script thuc thi do kiem suc chiu tai & toc do giao dien that (Desktop Stress Runner R2).
Tickets: DESKTOP-STRESS-HARNESS-FIX-HOME / DESKTOP-STRESS-RERUN-R2-HOME
Moi truong: May nha h410asrock (CPU-only theo bien ban BB-CONFIG-PARITY-01)

Cac cai tien ky thuat cot loi (Harness Fix R2):
(a) Buoc tien tram: Lam am worker cua moi kho (lsu, dieu_tra_loi, tong_hop, tri_thuc)
    va cho den khi banner nap mo hinh tren giao dien bien mat hoan toan truoc Luot 1.
(b) Het gio cho luot dau tien cua moi kho la 600 giay.
(c) Truoc khi restore_chat_store, sao chep traces.jsonl va messages.jsonl vao thu muc ket qua.
(d) Bang tong hop bo sung: phan bo theo tung kho va tach nhom ai_backend local voi LLM
    kem ty le dat tu khoa trong tung nhom.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import mmap
import os
from pathlib import Path
import re
import shutil
import statistics
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
os.environ["AIOS_BGE_INIT_TIMEOUT"] = "600"
os.environ["AIOS_BGE_WARM_ABSOLUTE_TIMEOUT"] = "600"
os.environ["AIOS_BGE_WARM_NO_PROGRESS_TIMEOUT"] = "180"
os.environ["AIOS_BGE_PERSIST_CONNECT_TIMEOUT"] = "600"
os.environ["AIOS_AI_BACKEND"] = "local"
os.environ["AIOS_FEATURE_CHAT_ACTION"] = "1"
os.environ["AIOS_DOMAIN_ROUTING_ENABLED"] = "1"
os.environ["AIOS_STREAM_SYNTHESIS"] = "1"
os.environ["AIOS_FEATURE_ANSWER_DRAFT_FALLBACK"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUNBUFFERED"] = "1"

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
PYTHON_EXE = APP_DIR / ".venv" / "Scripts" / "python.exe"
os.chdir(APP_DIR)

sys.path.insert(0, str(APP_DIR / "src"))
sys.path.insert(0, str(Path(__file__).parent))

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
store.TRACES_FILE = store.LOCAL_CHAT_DIR / "traces.jsonl"

from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import (
    save_conversation,
    load_messages,
    load_conversation_traces,
)
from aios_habit.streaming_markers import diff_marker_timestamps_s
from aios_habit.rag_v2.bge_subprocess_client import _pipe_instance_available
from aios_habit.index_domain import extract_exact_mechanical_identifiers
from aios_habit.rag_v2.structured_query import query_might_be_structured_excel
from aios_habit.workspace_chat_rag_v2_adapter import (
    ensure_workspace_chat_worker_warming,
    is_workspace_chat_worker_warmed,
)
from playwright.sync_api import sync_playwright

PORT = 8570
URL = f"http://localhost:{PORT}"

OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua")
OUT_DIR.mkdir(parents=True, exist_ok=True)

QUESTIONS_JSONL = OUT_DIR / "bo-cau-hoi-hoi-quy-120-desktop-home.jsonl"
SESSION_LOG_FILE = OUT_DIR / "session_stress_rerun_fixed_scoring_home.log"
SERVER_LOG_FILE = OUT_DIR / "server_stress_rerun_fixed_scoring_home.log"
RAW_TURNS_JSONL = OUT_DIR / "du-lieu-tho-tung-luot-stress-rerun-fixed-scoring-home.jsonl"
RAW_TURNS_CSV = OUT_DIR / "du-lieu-tho-tung-luot-stress-rerun-fixed-scoring-home.csv"
SUMMARY_JSON = OUT_DIR / "ket-qua-stress-rerun-fixed-scoring-home.json"
REPORT_MD = OUT_DIR / "DESKTOP-STRESS-RERUN-FIXED-SCORING-HOME.md"

BACKUP_DIR = APP_DIR / "local_cases" / "workspace_chat_backup_stress"

DAEMON_LOGS = {
    "lsu": Path(r"D:\Sandbox\AIOS_index_split_new\lsu\logs\bge_worker_daemon.stderr.log"),
    "dieu_tra_loi": Path(r"D:\Sandbox\AIOS_index_split_new\dieu_tra_loi\logs\bge_worker_daemon.stderr.log"),
    "tong_hop": Path(r"D:\Sandbox\AIOS_index_split_new\tong_hop\logs\bge_worker_daemon.stderr.log"),
    "tri_thuc": Path(r"C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\logs\bge_worker_daemon.stderr.log"),
}

PIPE_NAMES = {
    "lsu": r"\\.\pipe\aios_bge_m3_rag_v2_worker_pipe_bge_m3_hybrid_lsu",
    "dieu_tra_loi": r"\\.\pipe\aios_bge_m3_rag_v2_worker_pipe_bge_m3_hybrid_dieu_tra_loi",
    "tong_hop": r"\\.\pipe\aios_bge_m3_rag_v2_worker_pipe_bge_m3_hybrid_tong_hop",
    "tri_thuc": r"\\.\pipe\aios_bge_m3_rag_v2_worker_pipe_bge_m3_hybrid_tri_thuc",
}

SCREENSHOT_TURNS = {1, 2, 3, 4, 5, 8, 19, 20, 25, 50, 75, 100, 124}


_current_session_log: Path = SESSION_LOG_FILE


def set_current_session_log(p: Path) -> None:
    global _current_session_log
    _current_session_log = p


def log(msg: str) -> None:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    formatted = f"[{now_str}] {msg}"
    print(formatted, flush=True)
    try:
        with open(_current_session_log, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass


def get_git_head() -> str:
    try:
        res = subprocess.run(
            ["git", "-C", str(APP_DIR), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception as exc:
        log(f"[WARN] Khong the lay Git HEAD: {exc}")
        return "UNKNOWN"


def backup_chat_store() -> list[str]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backed_up = []
    for fname in ("conversations.jsonl", "messages.jsonl", "traces.jsonl", "evidence_traces.jsonl"):
        src = store.LOCAL_CHAT_DIR / fname
        dst = BACKUP_DIR / fname
        if src.exists():
            shutil.copy2(src, dst)
            backed_up.append(fname)
    log(f"[BACKUP] Da sao luu {len(backed_up)} tep store vao {BACKUP_DIR}")
    return backed_up


def restore_chat_store(backed_up: list[str]) -> None:
    for fname in ("conversations.jsonl", "messages.jsonl", "traces.jsonl", "evidence_traces.jsonl"):
        src = BACKUP_DIR / fname
        dst = store.LOCAL_CHAT_DIR / fname
        if fname in backed_up and src.exists():
            shutil.copy2(src, dst)
        elif fname not in backed_up and dst.exists():
            try:
                dst.unlink()
            except Exception:
                pass
    log("[RESTORE] Da khoi phuc nguyen trang cac tep store trong local_cases/workspace_chat.")


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


def start_server(port: int, log_file: Path, ai_backend: str = "local") -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(APP_DIR / "src")
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    env["AIOS_RETRIEVAL_DEVICE"] = "cpu"
    env["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
    env["AIOS_RAG_V2_NUMPY_SCORING"] = "1"
    env["AIOS_BGE_QUERY_TIMEOUT"] = "1200"
    env["AIOS_BGE_INIT_TIMEOUT"] = "600"
    env["AIOS_BGE_WARM_ABSOLUTE_TIMEOUT"] = "600"
    env["AIOS_BGE_WARM_NO_PROGRESS_TIMEOUT"] = "180"
    env["AIOS_BGE_PERSIST_CONNECT_TIMEOUT"] = "600"
    env["AIOS_RAGV2_WORKER_PERSIST"] = "1"
    env["AIOS_FEATURE_CHAT_ACTION"] = "1"
    env["AIOS_DOMAIN_ROUTING_ENABLED"] = "1"
    env["AIOS_STREAM_SYNTHESIS"] = "1"
    env["AIOS_FEATURE_ANSWER_DRAFT_FALLBACK"] = "1"
    env["AIOS_AI_BACKEND"] = ai_backend
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
    log(f"[STARTUP] Chay lenh (backend={ai_backend}): {' '.join(cmd)}")
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


_OS_CACHE_READ_LOCK = threading.Lock()
_PINNED_MMAPS: list[tuple[str, Any, Any]] = []
_HOT_TOUCH_STOP = threading.Event()


def _keep_pinned_mmaps_hot() -> None:
    while not _HOT_TOUCH_STOP.is_set():
        with _OS_CACHE_READ_LOCK:
            snapshot = list(_PINNED_MMAPS)
        if not snapshot:
            break
        acc = 0
        for col, _f_obj, mm_obj in snapshot:
            try:
                sz = mm_obj.size()
                for pos in range(0, sz, 65536):
                    acc ^= mm_obj[pos]
            except Exception:
                pass
        time.sleep(0.6)


def preload_onnx_model(
    db_order: list[str] | None = None,
    include_onnx: bool = True,
    pin_cols: set[str] | None = None,
) -> None:
    with _OS_CACHE_READ_LOCK:
        if include_onnx:
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
        if db_order:
            for col in db_order:
                if col not in DAEMON_LOGS:
                    continue
                db_path = DAEMON_LOGS[col].parent.parent / "library.sqlite"
                if db_path.is_file():
                    try:
                        sz_gb = db_path.stat().st_size / (1024**3)
                        if pin_cols and col in pin_cols:
                            log(f"[OS_CACHE] Doc tuan tu & ghim read-only mmap {col}/library.sqlite ({sz_gb:.2f}GB)...")
                            f_obj = open(db_path, "rb")
                            while f_obj.read(1024 * 1024 * 32):
                                pass
                            f_obj.seek(0)
                            mm_obj = mmap.mmap(f_obj.fileno(), 0, access=mmap.ACCESS_READ)
                            sz_bytes = mm_obj.size()
                            acc = 0
                            for pos in range(0, sz_bytes, 65536):
                                acc ^= mm_obj[pos]
                            _PINNED_MMAPS.append((col, f_obj, mm_obj))
                            log(f"[OS_CACHE] Da ghim mmap {col}/library.sqlite ({sz_gb:.2f}GB, checksum={acc}).")
                        else:
                            log(f"[OS_CACHE] Doc tuan tu {col}/library.sqlite ({sz_gb:.2f}GB) vao OS file cache...")
                            with open(db_path, "rb") as dbf:
                                while dbf.read(1024 * 1024 * 32):
                                    pass
                    except Exception as exc:
                        log(f"[OS_CACHE] [WARN] Khong the nap truoc {col}: {exc}")
        if _PINNED_MMAPS:
            _HOT_TOUCH_STOP.clear()
            threading.Thread(target=_keep_pinned_mmaps_hot, daemon=True).start()


def release_pinned_mmaps() -> None:
    _HOT_TOUCH_STOP.set()
    with _OS_CACHE_READ_LOCK:
        while _PINNED_MMAPS:
            col, f_obj, mm_obj = _PINNED_MMAPS.pop()
            try:
                mm_obj.close()
            except Exception:
                pass
            try:
                f_obj.close()
            except Exception:
                pass
            log(f"[OS_CACHE] Da giai phong read-only mmap cho khoi '{col}'.")


def get_current_log_offsets() -> dict[str, int]:
    offsets = {}
    for col, path in DAEMON_LOGS.items():
        if path.exists():
            offsets[col] = path.stat().st_size
        else:
            offsets[col] = 0
    return offsets


class WorkerTimelineTracker:
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

    def snapshot_line_counts(self) -> dict[str, int]:
        with self.lock:
            return {col: len(self.timeline[col]["raw_lines"]) for col in DAEMON_LOGS}

    def get_lines_since(self, snap: dict[str, int]) -> dict[str, list[str]]:
        with self.lock:
            return {
                col: list(self.timeline[col]["raw_lines"][snap.get(col, 0):])
                for col in DAEMON_LOGS
            }

    def run_poll(self) -> None:
        while not self.stop_event.is_set():
            now_dt = datetime.now()
            now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

            for col, pipe in list(PIPE_NAMES.items()):
                with self.lock:
                    if self.timeline[col]["pipe_available_ts"] is None:
                        if _pipe_instance_available(pipe):
                            self.timeline[col]["pipe_available_ts"] = now_str
                            log(f"[TIMELINE] Pipe cua khoi '{col}' da mo (available) tai: {now_str}")

            for col, log_path in DAEMON_LOGS.items():
                if not log_path.exists():
                    continue
                try:
                    size = log_path.stat().st_size
                    offset = self.offsets.get(col, 0)
                    if size > offset:
                        with open(log_path, "rb") as f:
                            f.seek(offset)
                            new_bytes = f.read()
                        self.offsets[col] = size
                        text = new_bytes.decode("utf-8", errors="replace")
                        for line in text.splitlines():
                            line_s = line.strip()
                            if not line_s:
                                continue
                            with self.lock:
                                self.timeline[col]["raw_lines"].append(line_s)
                                if "bge_subprocess_worker started" in line_s:
                                    self.timeline[col]["spawn_ts"] = now_str
                                    m = re.search(r"pid=(\d+)", line_s)
                                    if m:
                                        self.timeline[col]["spawn_pid"] = int(m.group(1))
                                if "model_load_ms" in line_s and not self.timeline[col]["model_load_ts"]:
                                    self.timeline[col]["model_load_ts"] = now_str
                                if "preload_stage=dense" in line_s and not self.timeline[col]["dense_preload_ts"]:
                                    self.timeline[col]["dense_preload_ts"] = now_str
                                    m = re.search(r"elapsed_ms=([\d\.]+)", line_s)
                                    if m:
                                        self.timeline[col]["dense_preload_ms"] = float(m.group(1))
                                if "preload_stage=sparse" in line_s and not self.timeline[col]["sparse_preload_ts"]:
                                    self.timeline[col]["sparse_preload_ts"] = now_str
                                    m = re.search(r"elapsed_ms=([\d\.]+)", line_s)
                                    if m:
                                        self.timeline[col]["sparse_preload_ms"] = float(m.group(1))
                                if "bge_subprocess_worker ready" in line_s and not self.timeline[col]["ready_ts"]:
                                    self.timeline[col]["ready_ts"] = now_str
                                    m = re.search(r"init_ms=([\d\.]+)", line_s)
                                    if m:
                                        self.timeline[col]["init_total_ms"] = float(m.group(1))
                                    log(f"[TIMELINE] Khoi '{col}' READY (init_ms={self.timeline[col]['init_total_ms']}) tai {now_str}")
                except Exception:
                    pass
            time.sleep(0.1)

    def stop(self) -> None:
        self.stop_event.set()


def wait_for_all_resident(tracker: WorkerTimelineTracker, timeout_s: float = 600) -> bool:
    """Cho den khi ca 4 kho deu dat trang thai resident / san sang (hoac qua is_workspace_chat_worker_warmed)."""
    log("Cho den khi CA 4 KHOI DEU DAT RESIDENT (lsu, dieu_tra_loi, tong_hop, tri_thuc)...")
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        all_ready = True
        with tracker.lock:
            for c in DAEMON_LOGS:
                has_ready_ts = (tracker.timeline[c]["ready_ts"] is not None)
                if not has_ready_ts:
                    if not is_workspace_chat_worker_warmed(collection_id=c):
                        all_ready = False
                        break
        if all_ready:
            log("[WAIT_RESIDENT] >>> XAC NHAN: CA 4 KHOI DEU DA DAT TRANG THAI RESIDENT/SAN SANG! <<<")
            return True
        time.sleep(0.5)
    log("[WAIT_RESIDENT] [WARN] Het thoi gian cho tat ca 4 khoi resident!")
    return False


def _extract_ts(marker_line: str) -> str:
    m = re.search(r"timestamp=([0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?)", marker_line)
    return m.group(1) if m else ""


def _parse_float_kv(line: str, key: str) -> float:
    m = re.search(rf"{re.escape(key)}=([\d\.]+)", line)
    return float(m.group(1)) if m else 0.0


def _norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def normalize_keyword_text(text: str) -> str:
    r"""Chuẩn hóa khoảng trắng đơn vị đo trước khi khớp từ khóa.
    Tách số (nguyên hoặc thập phân) và đơn vị đo (chữ cái / %) bằng biểu thức chính quy:
    re.sub(r'(\d+(?:[.,]\d+)?)\s*([a-zA-Z%]+)', r'\1 \2', text)
    giúp các cặp định dạng '3s'/'3 s', '1.1mm'/'1.1 mm', '64.09Dot'/'64.09 dot', '5.9Dot'/'5.9 dot'
    được tính là khớp. (Ticket: DESKTOP-BENCHMARK-KEYWORD-TOLERANCE-NORM-FIX-HOME)
    """
    if not text:
        return ""
    t = text.lower()
    t = re.sub(r"(\d+(?:[.,]\d+)?)\s*([a-zA-Z%]+)", r"\1 \2", t)
    return re.sub(r"\s+", " ", t).strip()


def evaluate_checkpoint(
    q_item: dict[str, Any],
    ans_text: str,
    trace_titles: list[str],
    trace_snippets: list[str],
    canary_sources: list[str],
) -> dict[str, Any]:
    """Kich ban cham da sua theo dung 4 tieu chi chat luong:
    (a) Cong thuc VA: checkpoint_pass = doc_matched AND keywords_pass, bao rieng tung dieu kien.
    (b) Bo toan bo hardcode ngoai le theo ma cau hoi.
    (c) Regex trich truong nguon file trong trace va ans_text dung dinh dang thuc te.
    (d) Nguong tu khoa chi tinh trong DAP AN (ans_text), khong tinh trong trace/canary.
    """
    exp = q_item.get("dap_an_ky_vong", {})
    raw_target_docs = exp.get("tai_lieu_muc_tieu", [])
    if isinstance(raw_target_docs, str):
        target_docs = [raw_target_docs.strip()] if raw_target_docs.strip() else []
    else:
        target_docs = [str(d).strip() for d in (raw_target_docs or []) if str(d).strip()]
    target_doc_str = "; ".join(target_docs)

    keywords = [str(k).strip() for k in (exp.get("tu_khoa_bat_buoc") or []) if str(k).strip()]

    # 1. Trich xuat toan bo nguon ung vien tu trace_titles, canary_sources va citations trong ans_text
    extracted_sources: list[str] = list(trace_titles) + list(canary_sources)

    fn_patterns = [
        r"(?:\[\d+\]\s*\*\*?([^\*\n\r]+?\.(?:pptx|xlsx|xlsm|xls|csv|pdf|txt|msg|html|png))\*\*?)",
        r"(?:出典ファイル|来源文件|Nguồn chuẩn|Nguồn file|Tài liệu chuẩn|Nguồn)[：:]\s*`?([^`\n\r]+?\.(?:pptx|xlsx|xlsm|xls|csv|pdf|txt|msg|html|png))`?",
        r"`([^`\n\r]+?\.(?:pptx|xlsx|xlsm|xls|csv|pdf|txt|msg|html|png))`",
        r"\b([\w\-. ]+\.(?:pptx|xlsx|xlsm|xls|csv|pdf|txt|msg|html))\b",
    ]
    for pat in fn_patterns:
        for m in re.finditer(pat, ans_text, flags=re.IGNORECASE):
            s_name = m.group(1).strip()
            if s_name and s_name not in extracted_sources:
                extracted_sources.append(s_name)

    # 2. Kiem tra tai lieu muc tieu (doc_matched)
    doc_matched = False
    matched_target_doc = ""
    matched_via_candidate = ""
    for td in target_docs:
        td_norm = _norm_text(td)
        td_stem_norm = _norm_text(Path(td).stem) if td else ""
        td_norm_alt = td_norm.replace(" ", "_")
        td_norm_space = td_norm.replace("_", " ")

        if not td_norm:
            continue

        for cand in extracted_sources + [ans_text]:
            c_norm = _norm_text(cand)
            c_norm_space = c_norm.replace("_", " ")
            if (
                td_norm in c_norm
                or td_norm_alt in c_norm
                or td_norm_space in c_norm_space
                or (td_stem_norm and len(td_stem_norm) >= 4 and (td_stem_norm in c_norm_space or td_stem_norm in c_norm))
            ):
                doc_matched = True
                matched_target_doc = td
                matched_via_candidate = cand[:100]
                break
        if doc_matched:
            break

    # 3. Kiem tra tu khoa bat buoc: CHỈ TÍNH TRONG ĐÁP ÁN (ans_text), KHÔNG TÍNH TRONG TRACE
    # Chuan hoa khoang trang don vi do truoc khi khop tu khoa (DESKTOP-BENCHMARK-KEYWORD-TOLERANCE-NORM-FIX-HOME)
    ans_norm = normalize_keyword_text(ans_text)
    matched_keywords = []
    for kw in keywords:
        kw_norm = normalize_keyword_text(kw)
        if kw_norm and kw_norm in ans_norm:
            matched_keywords.append(kw)

    kw_count = len(matched_keywords)
    kw_total = len(keywords)
    kw_pass_min = (kw_count >= 1) if kw_total > 0 else True
    kw_pass_majority = (kw_count >= ((kw_total + 1) // 2)) if kw_total > 0 else True
    kw_pass_strict = (kw_count == kw_total) if kw_total > 0 else True

    keywords_pass = kw_pass_min
    checkpoint_pass = bool(doc_matched and keywords_pass)

    return {
        "target_doc": target_doc_str,
        "doc_matched": doc_matched,
        "matched_target_doc": matched_target_doc,
        "matched_via_candidate": matched_via_candidate,
        "keywords_expected": keywords,
        "keywords_matched": matched_keywords,
        "keywords_count": kw_count,
        "keywords_total": kw_total,
        "keywords_pass": keywords_pass,
        "keywords_pass_min": kw_pass_min,
        "keywords_pass_majority": kw_pass_majority,
        "keywords_pass_strict": kw_pass_strict,
        "checkpoint_pass": checkpoint_pass,
    }


_HOST_QUERIED_COLLECTIONS: set[str] = set()


def _normalize_q_item(raw: dict[str, Any]) -> dict[str, Any]:
    t_idx = int(raw.get("turn_order") or raw.get("turn_index") or raw.get("stt") or 0)
    qid = str(raw.get("ma_cau") or raw.get("question_id"))
    raw_phase = str(raw.get("phase") or "")
    phase = "cold" if ("cold" in raw_phase or t_idx <= 4) else "warm"
    target_block = str(raw.get("khoi_tri_thuc") or raw.get("target_block"))
    ui_block_param = str(raw.get("ui_block_param") or target_block)
    notebook_id = str(raw.get("notebook_id"))
    question = str(raw.get("cau_hoi") or raw.get("question"))
    return {
        **raw,
        "turn_index": t_idx,
        "question_id": qid,
        "phase": phase,
        "target_block": target_block,
        "ui_block_param": ui_block_param,
        "notebook_id": notebook_id,
        "question": question,
    }


def execute_ui_turn(
    page,
    tracker: WorkerTimelineTracker,
    q_item: dict[str, Any],
    server_log_file: Path,
    screenshot_file: Path | None = None,
    target_fire_delay_s: float | None = None,
    t_server_ready: datetime | None = None,
    turn_timeout_s: float = 420.0,
) -> dict[str, Any]:
    q_item = _normalize_q_item(q_item)
    turn_idx = int(q_item["turn_index"])
    qid = str(q_item["question_id"])
    phase = str(q_item["phase"])
    notebook_id = str(q_item["notebook_id"])
    target_block = str(q_item["target_block"])
    ui_block_param = str(q_item.get("ui_block_param") or target_block)
    question = str(q_item["question"])

    conv_id = f"CONV-STRESS-RERUN-T{turn_idx:03d}-{qid}-{uuid.uuid4().hex[:6].upper()}"
    title = f"Stress Rerun T{turn_idx:03d} [{phase.upper()}] {qid} ({target_block})"

    save_conversation(WorkspaceConversation(
        id=conv_id,
        notebook_id=notebook_id,
        title=title,
        ai_mode="grounded",
    ))

    nav_url = f"{URL}/?nb={notebook_id}&conv={conv_id}&block={ui_block_param}"
    log(f"[T{turn_idx:03d}/{qid}] Navigate: {nav_url} (turn_timeout={turn_timeout_s:.0f}s)")
    page.goto(nav_url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(500)

    # Cho bat ky banner nap mo hinh (neu co) bien mat truoc khi tuong tac de tranh bi nuot click
    for _ in range(30):
        try:
            content = page.content()
            has_banner = any(kw.lower() in content.lower() for kw in ["đang nạp bộ đọc", "đang nạp mô hình", "bge-m3 & chỉ mục", "読取エンジン"])
            if not has_banner:
                break
        except Exception:
            break
        page.wait_for_timeout(500)

    page.wait_for_selector('textarea[placeholder*="Nhập câu hỏi"]', timeout=45000)
    textarea = page.locator('textarea[placeholder*="Nhập câu hỏi"]').first
    textarea.wait_for(state="visible", timeout=30000)
    textarea.click()
    textarea.fill(question)
    try:
        textarea.dispatch_event("input")
        textarea.dispatch_event("change")
        textarea.evaluate("el => el.blur()")
    except Exception:
        pass
    page.wait_for_timeout(350)

    if target_fire_delay_s is not None and t_server_ready is not None:
        now = datetime.now()
        elapsed_from_ready = (now - t_server_ready).total_seconds()
        if elapsed_from_ready < target_fire_delay_s:
            wait_remain = target_fire_delay_s - elapsed_from_ready
            log(f"[T{turn_idx:03d}] Cho them {wait_remain:.3f}s de dat moc +{target_fire_delay_s:.1f}s sau server ready...")
            time.sleep(wait_remain)

    server_log_offset = server_log_file.stat().st_size if server_log_file.exists() else 0
    daemon_snap = tracker.snapshot_line_counts()

    t_fire_dt = datetime.now()
    t_fire_perf = time.perf_counter()
    t_fire_str = t_fire_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log(f"[T{turn_idx:03d}/{qid}] FIRE ({conv_id}) block={target_block} nb={notebook_id} at {t_fire_str}")

    ask_btn = page.locator(f'[class*="st-key-wsc_ask_{conv_id}"] button, [class*="st-key-wsc-action-"] button').first
    if ask_btn.count() > 0:
        try:
            ask_btn.click()
        except Exception:
            textarea.press("Control+Enter")
    else:
        textarea.press("Control+Enter")

    qa_start_line = ""
    micro_line = ""
    first_token_line = ""
    complete_line = ""
    draft_complete_line = ""
    sync_action_complete = False
    priority_lines: list[str] = []
    warm_loop_lines: list[str] = []
    pre_synth_lines: list[str] = []
    canary_sources: list[str] = []

    t_watch_start = time.time()
    last_msg_check = t_watch_start
    retry_stage = 0
    in_conv_window = False
    scan_offset = server_log_offset

    # 2(b) Su dung bien turn_timeout_s (600s cho luot dau tien moi kho, 420s cho cac luot sau)
    while time.time() - t_watch_start < turn_timeout_s:
        if server_log_file.exists():
            try:
                with open(server_log_file, "rb") as sf:
                    sf.seek(scan_offset)
                    raw_bytes = sf.read()
                last_nl = raw_bytes.rfind(b"\n")
                if last_nl != -1:
                    complete_bytes = raw_bytes[: last_nl + 1]
                    scan_offset += len(complete_bytes)
                    complete_chunk = complete_bytes.decode("utf-8", errors="replace")
                else:
                    complete_chunk = ""
            except Exception:
                complete_chunk = ""

            if complete_chunk:
                for line in complete_chunk.splitlines():
                    line_clean = line.strip()
                    if not line_clean:
                        continue
                    if "[STREAMING_QA_START]" in line_clean:
                        if f"conv={conv_id}" in line_clean:
                            in_conv_window = True
                            if not qa_start_line:
                                qa_start_line = line_clean
                        else:
                            in_conv_window = False

                    if "[WARM_PRIORITY_" in line_clean and line_clean not in priority_lines:
                        priority_lines.append(line_clean)

                    if not in_conv_window:
                        continue

                    if "[WORKER_WARM_LOOP_STEP]" in line_clean and line_clean not in warm_loop_lines:
                        warm_loop_lines.append(line_clean)

                    if "workspace_chat_rag_v2 {" in line_clean:
                        try:
                            j_str = line_clean.split("workspace_chat_rag_v2 ", 1)[1]
                            j_obj = json.loads(j_str)
                            for s_title in j_obj.get("top_sources", []) or []:
                                if s_title not in canary_sources:
                                    canary_sources.append(str(s_title))
                        except Exception:
                            pass

                    if "[RETRIEVAL_MICRO_TIMING]" in line_clean and not micro_line:
                        micro_line = line_clean

                    if "[PRE_SYNTH_STEP]" in line_clean and f"conv={conv_id}" in line_clean:
                        pre_synth_lines.append(line_clean)

                    if "[STREAMING_QA_FIRST_TOKEN]" in line_clean and f"conv={conv_id}" in line_clean and not first_token_line:
                        first_token_line = line_clean

                    if "[DRAFT_FALLBACK_COMPLETE]" in line_clean and f"conv={conv_id}" in line_clean and not draft_complete_line:
                        draft_complete_line = line_clean

                    if "[STREAMING_QA_COMPLETE]" in line_clean and f"conv={conv_id}" in line_clean and not complete_line:
                        complete_line = line_clean

        if complete_line or draft_complete_line:
            break

        now_ts = time.time()
        if now_ts - last_msg_check >= 1.0:
            last_msg_check = now_ts
            elapsed_watch = now_ts - t_watch_start
            msgs = load_messages(conv_id)
            has_assistant = any(m.role == "assistant" and (m.content or "").strip() for m in msgs)
            has_user = any(m.role == "user" for m in msgs)
            if has_assistant and not qa_start_line and elapsed_watch >= 1.5:
                sync_action_complete = True
                break
            if not has_user and not qa_start_line:
                if (retry_stage == 0 and elapsed_watch >= 12.0) or (retry_stage == 1 and elapsed_watch >= 25.0) or (retry_stage == 2 and elapsed_watch >= 40.0):
                    retry_stage += 1
                    log(f"[T{turn_idx:03d}/{qid}] [RETRY_SUBMIT #{retry_stage}] Chua thay user msg sau {elapsed_watch:.1f}s, gui lai tren UI...")
                    try:
                        textarea = page.locator('textarea[placeholder*="Nhập câu hỏi"]').first
                        if textarea.count() > 0:
                            textarea.click()
                            textarea.fill(question)
                            try:
                                textarea.dispatch_event("input")
                                textarea.dispatch_event("change")
                                textarea.evaluate("el => el.blur()")
                            except Exception:
                                pass
                            page.wait_for_timeout(250)
                        ask_btn_retry = page.locator(f'[class*="st-key-wsc_ask_{conv_id}"] button, [class*="st-key-wsc-action-"] button').first
                        if ask_btn_retry.count() > 0:
                            ask_btn_retry.click()
                        else:
                            textarea.press("Control+Enter")
                    except Exception as exc:
                        log(f"[T{turn_idx:03d}/{qid}] [RETRY_SUBMIT_ERR] {exc}")

        time.sleep(0.15)

    ans_text = ""
    for _ in range(50):
        msgs = load_messages(conv_id)
        assistant_msgs = [m for m in msgs if m.role == "assistant" and (m.content or "").strip()]
        if assistant_msgs:
            ans_text = assistant_msgs[-1].content
            break
        time.sleep(0.15)

    t_ui_done_perf = time.perf_counter()
    t_ui_done_dt = datetime.now()
    t_ui_done_str = t_ui_done_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    ui_e2e_s = round(t_ui_done_perf - t_fire_perf, 3)

    if screenshot_file is not None:
        page.wait_for_timeout(1200)
        try:
            page.screenshot(path=str(screenshot_file), timeout=12000)
            log(f"[SCREENSHOT] T{turn_idx:03d} -> {screenshot_file.name}")
        except Exception as ss_exc:
            log(f"[SCREENSHOT_WARN] T{turn_idx:03d} page.screenshot timeout ({ss_exc}), dung CDP captureScreenshot fallback...")
            try:
                import base64
                cdp = page.context.new_cdp_session(page)
                res = cdp.send("Page.captureScreenshot", {"format": "png"})
                screenshot_file.write_bytes(base64.b64decode(res["data"]))
                cdp.detach()
                log(f"[SCREENSHOT] T{turn_idx:03d} (CDP) -> {screenshot_file.name}")
            except Exception as cdp_exc:
                log(f"[SCREENSHOT_ERR] T{turn_idx:03d} CDP fallback error: {cdp_exc}")
    else:
        page.wait_for_timeout(150)

    daemon_new_lines = tracker.get_lines_since(daemon_snap)

    trace_titles: list[str] = []
    trace_snippets: list[str] = []
    for _ in range(25):
        try:
            traces = load_conversation_traces(conv_id)
            if traces:
                for tr in traces:
                    for node in getattr(tr, "nodes", []) or []:
                        if getattr(node, "node_type", "") in ("source", "citation", "evidence"):
                            nt = str(getattr(node, "title", "") or getattr(node, "label", "") or "")
                            ns = str(getattr(node, "snippet", "") or getattr(node, "content", "") or "")
                            np = str(getattr(node, "source_path", "") or "")
                            if nt and nt not in trace_titles:
                                trace_titles.append(nt)
                            if np and np not in trace_titles:
                                trace_titles.append(np)
                            if ns:
                                trace_snippets.append(ns)
                if trace_titles or trace_snippets:
                    break
        except Exception:
            pass
        time.sleep(0.2)

    ts_qa_start = _extract_ts(qa_start_line)
    ts_micro = _extract_ts(micro_line)
    ts_first_token = _extract_ts(first_token_line)
    ts_complete = _extract_ts(complete_line or draft_complete_line)

    if sync_action_complete and not ts_qa_start:
        ts_qa_start = t_fire_str
        ts_first_token = t_ui_done_str
        ts_complete = t_ui_done_str

    delta_qa_to_micro = diff_marker_timestamps_s(ts_qa_start, ts_micro) if (ts_qa_start and ts_micro) else 0.0
    delta_qa_to_first_token = diff_marker_timestamps_s(ts_qa_start, ts_first_token) if (ts_qa_start and ts_first_token) else None
    delta_qa_to_complete = diff_marker_timestamps_s(ts_qa_start, ts_complete) if (ts_qa_start and ts_complete) else None
    if delta_qa_to_complete is None and (complete_line or draft_complete_line):
        m_tot = re.search(r"total_s=([\d\.]+)", complete_line or draft_complete_line)
        if m_tot:
            delta_qa_to_complete = float(m_tot.group(1))
    if delta_qa_to_complete is None and sync_action_complete:
        delta_qa_to_complete = ui_e2e_s
    if delta_qa_to_first_token is None and delta_qa_to_complete is not None:
        delta_qa_to_first_token = delta_qa_to_complete

    if sync_action_complete and not micro_line:
        actual_col = "chat_action_sync"
    elif draft_complete_line and not micro_line:
        actual_col = "draft_fallback"
    else:
        actual_col = "unknown"

    pipe_wait_ms = _parse_float_kv(micro_line, "pipe_wait_ms")
    coverage_verify_ms = _parse_float_kv(micro_line, "coverage_verify_ms")
    embed_ms = _parse_float_kv(micro_line, "embed_ms")
    dense_ms = _parse_float_kv(micro_line, "dense_ms")
    sparse_ms = _parse_float_kv(micro_line, "sparse_ms")
    fuse_ms = _parse_float_kv(micro_line, "fuse_ms")

    micro_sum_ms = pipe_wait_ms + coverage_verify_ms + embed_ms + dense_ms + sparse_ms + fuse_ms
    pure_retrieval_s = round(micro_sum_ms / 1000.0, 3)
    pre_retrieval_wait_s = round(max(0.0, delta_qa_to_micro - pure_retrieval_s), 3)

    if micro_line:
        m_col = re.search(r"collection=([^\s]+)", micro_line)
        if m_col:
            actual_col = m_col.group(1)

    daemon_col = actual_col if actual_col in DAEMON_LOGS else (target_block if target_block in DAEMON_LOGS else "tri_thuc")
    col_daemon_lines = daemon_new_lines.get(daemon_col, [])

    worker_search_ms = 0.0
    worker_synth_ms = 0.0
    for dl in col_daemon_lines:
        if "worker_search_ms=" in dl:
            worker_search_ms += _parse_float_kv(dl, "worker_search_ms")
        if "worker_synth_ms=" in dl:
            worker_synth_ms += _parse_float_kv(dl, "worker_synth_ms")

    dense_resident = any("dense_resident=1" in dl or "dense_resident=True" in dl for dl in col_daemon_lines)
    is_first_host_query_for_col = daemon_col not in _HOST_QUERIED_COLLECTIONS
    if daemon_col in DAEMON_LOGS:
        _HOST_QUERIED_COLLECTIONS.add(daemon_col)

    exact_ids = tuple(extract_exact_mechanical_identifiers(question))
    is_struct_excel = bool(query_might_be_structured_excel(question))

    reasons = []
    if warm_loop_lines or priority_lines:
        reasons.append(f"cold_worker_init(col={daemon_col})")
    if is_first_host_query_for_col:
        reasons.append(f"first_query_host_scan(col={daemon_col})")
    if exact_ids:
        reasons.append(f"exact_id_scan(ids={list(exact_ids)})")
    if is_struct_excel:
        reasons.append("structured_excel_probe")
    if pipe_wait_ms > 1000.0:
        reasons.append(f"pipe_wait_ms={pipe_wait_ms:.1f}ms")

    pre_retrieval_attribution = "; ".join(reasons) if reasons else ("none (<=5s)" if pre_retrieval_wait_s <= 5.0 else "unattributed")

    cp_eval = evaluate_checkpoint(
        q_item=q_item,
        ans_text=ans_text,
        trace_titles=trace_titles,
        trace_snippets=trace_snippets,
        canary_sources=canary_sources,
    )

    turn_ok = bool((complete_line or draft_complete_line or sync_action_complete) and len(ans_text.strip()) > 0)

    # 2(d) Bóc tách ai_backend thực tế và phân nhóm local vs LLM
    m_backend = re.search(r"backend=([^\s]+)", qa_start_line)
    if m_backend:
        backend_val = m_backend.group(1)
    elif sync_action_complete:
        backend_val = "chat_action_sync"
    elif draft_complete_line:
        backend_val = "draft_fallback"
    else:
        backend_val = os.environ.get("AIOS_AI_BACKEND", "local")

    is_local_backend = (
        backend_val in ("local", "draft_fallback", "chat_action_sync")
        or "local" in backend_val
        or ans_text.startswith("Dựa trên các trích đoạn tài liệu")
    )
    backend_group = "local" if is_local_backend else "llm"

    log(
        f"[T{turn_idx:03d}/{qid}] DONE ok={turn_ok} col={actual_col} backend={backend_val} ({backend_group}) | "
        f"UI_E2E={ui_e2e_s:.3f}s | QA->MICRO={delta_qa_to_micro:.3f}s (pure_ret={pure_retrieval_s:.3f}s, pre_wait={pre_retrieval_wait_s:.3f}s) | "
        f"QA->COMPLETE={delta_qa_to_complete}s | ans_len={len(ans_text)} | "
        f"DOC_OK={cp_eval['doc_matched']} KW_PASS={cp_eval['keywords_pass']} ({cp_eval['keywords_count']}/{cp_eval['keywords_total']}) | "
        f"CP_PASS={cp_eval['checkpoint_pass']}"
    )

    return {
        "turn_index": turn_idx,
        "phase": phase,
        "question_id": qid,
        "conv_id": conv_id,
        "notebook_id": notebook_id,
        "target_block": target_block,
        "ui_block_param": ui_block_param,
        "actual_collection": actual_col,
        "ai_backend": backend_val,
        "backend_group": backend_group,
        "question": question,
        "t_fire": t_fire_str,
        "t_ui_done": t_ui_done_str,
        "ui_e2e_s": ui_e2e_s,
        "turn_timeout_s": turn_timeout_s,
        "ts_qa_start": ts_qa_start,
        "ts_micro": ts_micro,
        "ts_first_token": ts_first_token,
        "ts_complete": ts_complete,
        "delta_qa_to_micro_s": delta_qa_to_micro,
        "pure_retrieval_s": pure_retrieval_s,
        "pre_retrieval_wait_s": pre_retrieval_wait_s,
        "pre_retrieval_attribution": pre_retrieval_attribution,
        "delta_qa_to_first_token_s": delta_qa_to_first_token,
        "delta_qa_to_complete_s": delta_qa_to_complete,
        "pipe_wait_ms": pipe_wait_ms,
        "coverage_verify_ms": coverage_verify_ms,
        "embed_ms": embed_ms,
        "dense_ms": dense_ms,
        "sparse_ms": sparse_ms,
        "fuse_ms": fuse_ms,
        "worker_search_ms": round(worker_search_ms, 2),
        "worker_synth_ms": round(worker_synth_ms, 2),
        "dense_resident": dense_resident,
        "turn_completed": turn_ok,
        "answer_length": len(ans_text),
        "answer_preview": ans_text[:350].replace("\n", " "),
        "raw_answer": ans_text,
        "trace_titles": trace_titles[:10],
        "trace_snippets": [s[:200] for s in trace_snippets[:5]],
        "canary_sources": canary_sources[:8],
        "target_doc": cp_eval["target_doc"],
        "doc_matched": cp_eval["doc_matched"],
        "matched_target_doc": cp_eval["matched_target_doc"],
        "matched_via_candidate": cp_eval["matched_via_candidate"],
        "keywords_expected": cp_eval["keywords_expected"],
        "keywords_matched": cp_eval["keywords_matched"],
        "keywords_count": cp_eval["keywords_count"],
        "keywords_total": cp_eval["keywords_total"],
        "keywords_pass": cp_eval["keywords_pass"],
        "keywords_pass_min": cp_eval["keywords_pass_min"],
        "keywords_pass_majority": cp_eval["keywords_pass_majority"],
        "keywords_pass_strict": cp_eval["keywords_pass_strict"],
        "checkpoint_pass": cp_eval["checkpoint_pass"],
        "qa_start_line": qa_start_line,
        "micro_line": micro_line,
        "first_token_line": first_token_line,
        "complete_line": complete_line or draft_complete_line or ("CHAT_ACTION_SYNC_COMPLETE" if sync_action_complete else ""),
        "daemon_lines": col_daemon_lines,
        "screenshot_file": str(screenshot_file.name) if screenshot_file else "",
    }


def compute_dist_stats(vals: list[float]) -> dict[str, Any]:
    if not vals:
        return {"count": 0, "min": None, "median": None, "p95": None, "max": None, "mean": None}
    s = sorted(vals)
    n = len(s)
    med = round(statistics.median(s), 3)
    idx_95 = min(n - 1, max(0, int(round(0.95 * (n - 1)))))
    p95 = round(s[idx_95], 3)
    return {
        "count": n,
        "min": round(s[0], 3),
        "median": med,
        "p95": p95,
        "max": round(s[-1], 3),
        "mean": round(statistics.mean(s), 3),
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def preflight_warmup_workers_and_wait_ui(context, tracker: WorkerTimelineTracker) -> None:
    """2(a) Buoc tien tram: lam am worker cua moi kho va cho den khi banner nap mo hinh bien mat."""
    log("=" * 95)
    log("[PREFLIGHT] BAT DAU BUOC TIEN TRAM: LAM AM WORKER CUA MOI KHO VA KIEM TRA GIAO DIEN")
    log("=" * 95)

    for col in ("lsu", "dieu_tra_loi", "tong_hop", "tri_thuc"):
        log(f"[PREFLIGHT] Kich hoat lam am worker cho kho '{col}' (blocking=True, timeout=600s)...")
        try:
            ok = ensure_workspace_chat_worker_warming(
                collection_id=col,
                blocking=True,
                timeout_s=600.0,
            )
            log(f"[PREFLIGHT] Ket qua lam am kho '{col}': {ok}")
        except Exception as exc:
            log(f"[PREFLIGHT_WARN] Khong the goi ensure_workspace_chat_worker_warming cho '{col}': {exc}")

    # Cho den khi ca 4 worker deu dat trang thai RESIDENT/READY
    all_ready = wait_for_all_resident(tracker, timeout_s=600.0)
    release_pinned_mmaps()
    log(f"[PREFLIGHT] Ket qua cho 4 worker resident: all_ready={all_ready}")

    # Mo giao dien tren tab tam thoi va cho den khi banner nap mo hinh tren giao dien bien mat hoan toan truoc Luot 1
    log("[PREFLIGHT] Mo giao dien Streamlit tren tab tam thoi de xac nhan banner nap mo hinh...")
    temp_page = context.new_page()
    try:
        temp_page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        temp_page.wait_for_timeout(1000)

        deadline = time.time() + 180.0
        banner_keywords = [
            "đang nạp bộ đọc",
            "đang nạp mô hình",
            "bge-m3 & chỉ mục",
            "đang khởi tạo tiến trình đọc",
            "読取エンジン",
            "bge-m3モデルと索引を読み込み中",
        ]
        banner_disappeared = False
        while time.time() < deadline:
            try:
                content = temp_page.content()
                has_banner = any(kw.lower() in content.lower() for kw in banner_keywords)
                if not has_banner:
                    banner_disappeared = True
                    log("[PREFLIGHT] >>> XAC NHAN: Banner nap mo hinh tren giao dien da bien mat hoan toan! <<<")
                    break
            except Exception:
                pass
            temp_page.wait_for_timeout(1000)

        if not banner_disappeared:
            log("[PREFLIGHT] [WARN] Het thoi gian cho banner bien mat, tien hanh sang Luot 1...")
    finally:
        try:
            temp_page.close()
        except Exception:
            pass

    log("=" * 95)
    log("[PREFLIGHT] HOAN TAT BUOC TIEN TRAM. GIAO DIEN & WORKER HOAN TOAN SAN SANG CHO LUOT 1!")
    log("=" * 95)


def run_stress_suite(
    limit: int | None = None,
    report_name: str | None = None,
    skip_preflight: bool = False,
    override_backend: str | None = None,
    run_tag: str | None = None,
) -> dict[str, Any]:
    tag_suffix = f"_{run_tag.lower()}" if run_tag else ""
    tag_dash = f"-{run_tag.lower()}" if run_tag else ""

    session_log_file = OUT_DIR / f"session_stress_rerun{tag_suffix}.log" if run_tag else SESSION_LOG_FILE
    server_log_file = OUT_DIR / f"server_stress_rerun{tag_suffix}.log" if run_tag else SERVER_LOG_FILE
    raw_turns_jsonl = OUT_DIR / f"du-lieu-tho-tung-luot-stress-rerun{tag_dash}.jsonl" if run_tag else RAW_TURNS_JSONL
    raw_turns_csv = OUT_DIR / f"du-lieu-tho-tung-luot-stress-rerun{tag_dash}.csv" if run_tag else RAW_TURNS_CSV
    summary_json = OUT_DIR / f"ket-qua-stress-rerun{tag_dash}.json" if run_tag else SUMMARY_JSON

    set_current_session_log(session_log_file)

    if session_log_file.exists():
        session_log_file.unlink()
    if raw_turns_jsonl.exists():
        raw_turns_jsonl.unlink()

    report_path = (OUT_DIR / report_name) if report_name else REPORT_MD

    log("=" * 95)
    log(f"BAT DAU CHAY STRESS TAI MAY NHA (limit={limit or 'ALL'}, report={report_path.name})")
    log("=" * 95)

    git_head = get_git_head()
    ai_backend = override_backend or os.environ.get("AIOS_AI_BACKEND", "local")
    os.environ["AIOS_AI_BACKEND"] = ai_backend
    log(f"[META] Git HEAD AIOS_habbit: {git_head} | AI Backend: {ai_backend}")

    all_raw_questions = [
        _normalize_q_item(json.loads(line))
        for line in QUESTIONS_JSONL.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if limit is not None and limit > 0:
        questions = all_raw_questions[:limit]
        log(f"[SUITE] Da lay {len(questions)} / {len(all_raw_questions)} cau hoi (theo gioi han --limit {limit})")
    else:
        questions = all_raw_questions
        log(f"[SUITE] Da nap toan bo {len(questions)} cau hoi hoi quy tu {QUESTIONS_JSONL}")

    backed_up_files = backup_chat_store()
    all_turn_records: list[dict[str, Any]] = []
    screenshot_hashes: list[dict[str, str]] = []
    all_resident_achieved = False
    t_start_app_str = ""
    t_server_ready_str = ""
    timeline_snapshot: dict[str, Any] = {}

    first_seen_blocks: set[str] = set()

    server_proc = None
    tracker = None

    try:
        kill_all_workers_and_servers()
        preload_onnx_model(["tong_hop", "dieu_tra_loi", "lsu"], include_onnx=True, pin_cols={"tong_hop", "dieu_tra_loi"})

        offsets = get_current_log_offsets()
        for col, off in offsets.items():
            log(f"[DAEMON_OFFSET] {col}: {off} bytes")

        tracker = WorkerTimelineTracker(offsets)
        th = threading.Thread(target=tracker.run_poll, daemon=True)
        th.start()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1600, "height": 1000})
            t_start_app = datetime.now()
            t_start_app_str = t_start_app.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            server_proc = start_server(PORT, server_log_file, ai_backend=ai_backend)
            if not wait_for_server(PORT, timeout=90):
                raise RuntimeError("Streamlit server khong phan hoi tren cong 8570 sau 90s!")

            t_server_ready = datetime.now()
            t_server_ready_str = t_server_ready.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            log(f"[SERVER_READY] Server san sang sau {(t_server_ready - t_start_app).total_seconds():.3f}s tai {t_server_ready_str}")

            # 2(a) Buoc tien tram: lam am worker va cho banner bien mat truoc Luot 1
            if not skip_preflight:
                preflight_warmup_workers_and_wait_ui(context, tracker)
                all_resident_achieved = True
            else:
                log("[PREFLIGHT] Bo qua buoc tien tram theo tham so --skip-preflight.")

            page = context.new_page()

            for q_item in questions:
                t_idx = int(q_item["turn_index"])
                qid = str(q_item["question_id"])
                phase = str(q_item["phase"])
                blk = str(q_item["target_block"])

                # 2(b) Het gio cho luot dau tien cua moi kho la 600 giay
                if blk not in first_seen_blocks:
                    first_seen_blocks.add(blk)
                    turn_timeout = 600.0
                    log(f"[T{t_idx:03d}/{qid}] Day la luot dau tien cua kho '{blk}' -> Dat turn_timeout = 600s")
                else:
                    turn_timeout = 420.0

                shot_path = None
                if t_idx in SCREENSHOT_TURNS:
                    shot_path = OUT_DIR / f"anh-stress-rerun{tag_dash}-t{t_idx:03d}-{phase}-{blk}-{qid.lower()}.png"

                fire_delay = 5.0 if t_idx == 1 else None
                rec = execute_ui_turn(
                    page=page,
                    tracker=tracker,
                    q_item=q_item,
                    server_log_file=server_log_file,
                    screenshot_file=shot_path,
                    target_fire_delay_s=fire_delay,
                    t_server_ready=t_server_ready if t_idx == 1 else None,
                    turn_timeout_s=turn_timeout,
                )
                all_turn_records.append(rec)

                with open(raw_turns_jsonl, "a", encoding="utf-8") as jf:
                    jf.write(json.dumps(rec, ensure_ascii=False) + "\n")

                if shot_path and shot_path.exists():
                    screenshot_hashes.append({
                        "turn_index": t_idx,
                        "question_id": qid,
                        "phase": phase,
                        "target_block": blk,
                        "file": shot_path.name,
                        "sha256": sha256_file(shot_path),
                    })

                # Refresh Chromium DOM sau moi 30 luot
                if t_idx in (35, 65, 95):
                    try:
                        page.close()
                    except Exception:
                        pass
                    page = context.new_page()

            try:
                page.close()
            except Exception:
                pass
            context.close()
            browser.close()

        with tracker.lock:
            timeline_snapshot = {
                col: {k: v for k, v in info.items() if k != "raw_lines"}
                for col, info in tracker.timeline.items()
            }

    finally:
        release_pinned_mmaps()
        if tracker is not None:
            tracker.stop()
        if server_proc is not None:
            kill_server(server_proc)
        kill_all_workers_and_servers()

        # 2(c) Truoc khi restore_chat_store, sao chep traces.jsonl va messages.jsonl vao thu muc ket qua
        try:
            curr_traces = store.LOCAL_CHAT_DIR / "traces.jsonl"
            curr_messages = store.LOCAL_CHAT_DIR / "messages.jsonl"
            if curr_traces.exists():
                shutil.copy2(curr_traces, OUT_DIR / "traces.jsonl")
                if run_tag:
                    shutil.copy2(curr_traces, OUT_DIR / f"traces{tag_suffix}.jsonl")
                    log(f"[PRESERVE] Da sao chep traces.jsonl ({curr_traces.stat().st_size} bytes) vao {OUT_DIR / f'traces{tag_suffix}.jsonl'} va traces.jsonl")
                else:
                    log(f"[PRESERVE] Da sao chep traces.jsonl ({curr_traces.stat().st_size} bytes) vao {OUT_DIR / 'traces.jsonl'}")
            else:
                log(f"[PRESERVE_WARN] Tep traces.jsonl khong ton tai tai {curr_traces}!")

            if curr_messages.exists():
                shutil.copy2(curr_messages, OUT_DIR / "messages.jsonl")
                if run_tag:
                    shutil.copy2(curr_messages, OUT_DIR / f"messages{tag_suffix}.jsonl")
                    log(f"[PRESERVE] Da sao chep messages.jsonl ({curr_messages.stat().st_size} bytes) vao {OUT_DIR / f'messages{tag_suffix}.jsonl'} va messages.jsonl")
                else:
                    log(f"[PRESERVE] Da sao chep messages.jsonl ({curr_messages.stat().st_size} bytes) vao {OUT_DIR / 'messages.jsonl'}")
            else:
                log(f"[PRESERVE_WARN] Tep messages.jsonl khong ton tai tai {curr_messages}!")
        except Exception as pres_exc:
            log(f"[PRESERVE_ERR] Loi khi sao chep traces/messages truoc restore: {pres_exc}")

        restore_chat_store(backed_up_files)

    # Xuat CSV du lieu tho tung luot
    csv_fields = [
        "turn_index", "phase", "question_id", "conv_id", "notebook_id",
        "target_block", "ui_block_param", "actual_collection", "ai_backend", "backend_group",
        "t_fire", "t_ui_done", "ui_e2e_s", "turn_timeout_s",
        "ts_qa_start", "ts_micro", "ts_first_token", "ts_complete",
        "delta_qa_to_micro_s", "pure_retrieval_s", "pre_retrieval_wait_s",
        "delta_qa_to_first_token_s", "delta_qa_to_complete_s",
        "worker_search_ms", "worker_synth_ms",
        "turn_completed", "answer_length",
        "doc_matched", "matched_target_doc",
        "keywords_count", "keywords_total",
        "keywords_pass", "keywords_pass_min", "keywords_pass_majority", "keywords_pass_strict",
        "checkpoint_pass", "target_doc", "question", "answer_preview",
    ]
    with open(raw_turns_csv, "w", encoding="utf-8-sig", newline="") as cf:
        writer = csv.DictWriter(cf, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        for r in all_turn_records:
            writer.writerow({k: r.get(k, "") for k in csv_fields})

    # Tinh toan thong ke tong hop
    total_turns = len(all_turn_records)
    completed_turns = sum(1 for r in all_turn_records if r["turn_completed"])
    doc_matched_count = sum(1 for r in all_turn_records if r["doc_matched"])
    kw_pass_count = sum(1 for r in all_turn_records if r["keywords_pass"])
    both_passed_count = sum(1 for r in all_turn_records if r["checkpoint_pass"])

    kw_pass_majority_count = sum(1 for r in all_turn_records if r["keywords_pass_majority"])
    kw_pass_strict_count = sum(1 for r in all_turn_records if r["keywords_pass_strict"])
    both_majority_count = sum(1 for r in all_turn_records if r["doc_matched"] and r["keywords_pass_majority"])
    both_strict_count = sum(1 for r in all_turn_records if r["doc_matched"] and r["keywords_pass_strict"])

    warm_turns = [r for r in all_turn_records if r["phase"] == "warm"]
    cold_turns = [r for r in all_turn_records if r["phase"] == "cold"]

    warm_ui_e2e = [float(r["ui_e2e_s"]) for r in warm_turns if r.get("ui_e2e_s") is not None]
    warm_qa_to_complete = [float(r["delta_qa_to_complete_s"]) for r in warm_turns if r.get("delta_qa_to_complete_s") is not None]
    warm_qa_to_first_token = [float(r["delta_qa_to_first_token_s"]) for r in warm_turns if r.get("delta_qa_to_first_token_s") is not None]
    warm_qa_to_micro = [float(r["delta_qa_to_micro_s"]) for r in warm_turns if r.get("delta_qa_to_micro_s") is not None]
    warm_pure_ret = [float(r["pure_retrieval_s"]) for r in warm_turns if r.get("pure_retrieval_s") is not None]
    warm_pre_wait = [float(r["pre_retrieval_wait_s"]) for r in warm_turns if r.get("pre_retrieval_wait_s") is not None]

    # 2(d) - Tinh toan phan bo theo tung kho
    warehouses = ["lsu", "dieu_tra_loi", "tong_hop", "tri_thuc"]
    by_warehouse: dict[str, dict[str, Any]] = {}
    for w in warehouses:
        w_records = [r for r in all_turn_records if r.get("target_block") == w]
        w_tot = len(w_records)
        w_doc = sum(1 for r in w_records if r.get("doc_matched"))
        w_kw = sum(1 for r in w_records if r.get("keywords_pass"))
        w_both = sum(1 for r in w_records if r.get("checkpoint_pass"))
        by_warehouse[w] = {
            "total": w_tot,
            "doc_matched_count": w_doc,
            "doc_matched_pct": round(w_doc / w_tot * 100.0, 2) if w_tot else 0.0,
            "keywords_pass_count": w_kw,
            "keywords_pass_pct": round(w_kw / w_tot * 100.0, 2) if w_tot else 0.0,
            "both_passed_count": w_both,
            "both_passed_pct": round(w_both / w_tot * 100.0, 2) if w_tot else 0.0,
        }

    # 2(d) - Tach nhom ai_backend local voi LLM kem ty le dat tu khoa trong tung nhom
    by_backend_group: dict[str, dict[str, Any]] = {}
    for bg, label in [("local", "Cục bộ (ai_backend local)"), ("llm", "Mô hình ngôn ngữ lớn (LLM)")]:
        bg_records = [r for r in all_turn_records if r.get("backend_group") == bg]
        bg_tot = len(bg_records)
        bg_doc = sum(1 for r in bg_records if r.get("doc_matched"))
        bg_kw = sum(1 for r in bg_records if r.get("keywords_pass"))
        bg_both = sum(1 for r in bg_records if r.get("checkpoint_pass"))
        by_backend_group[bg] = {
            "label": label,
            "total": bg_tot,
            "doc_matched_count": bg_doc,
            "doc_matched_pct": round(bg_doc / bg_tot * 100.0, 2) if bg_tot else 0.0,
            "keywords_pass_count": bg_kw,
            "keywords_pass_pct": round(bg_kw / bg_tot * 100.0, 2) if bg_tot else 0.0,
            "both_passed_count": bg_both,
            "both_passed_pct": round(bg_both / bg_tot * 100.0, 2) if bg_tot else 0.0,
        }

    # Phan loai cac cau that bai
    failed_turns = [r for r in all_turn_records if not r["checkpoint_pass"]]
    failed_classification: list[dict[str, Any]] = []
    for r in failed_turns:
        t_idx = r["turn_index"]
        qid = r["question_id"]
        doc_ok = r["doc_matched"]
        kw_ok = r["keywords_pass"]
        traces = r.get("trace_titles", [])

        category = "Lỗi hệ thống"
        reason = ""
        if not doc_ok:
            if qid in ("Q0718", "Q0828"):
                reason = f"Q0718/Q0828 chua truy hoi duoc tai lieu dich {r.get('target_doc')}, tra ve {traces}"
            else:
                reason = f"Truy hoi lech hoac thieu trace tai lieu dich: got {traces}, target={r.get('target_doc')}"
        elif not kw_ok:
            category = "Lỗi thiếu từ khóa trong đáp án"
            reason = f"Dap an khong chua tu khoa bat buoc: expected {r.get('keywords_expected')}, got 0 matches"

        failed_classification.append({
            "turn_index": t_idx,
            "question_id": qid,
            "target_block": r["target_block"],
            "target_doc": r["target_doc"],
            "doc_matched": doc_ok,
            "keywords_matched": r["keywords_matched"],
            "keywords_expected": r["keywords_expected"],
            "category": category,
            "reason": reason,
            "answer_preview": r["answer_preview"],
            "trace_titles": traces,
        })

    q0718_rec = next((r for r in all_turn_records if r["question_id"] == "Q0718"), {})
    q0828_rec = next((r for r in all_turn_records if r["question_id"] == "Q0828"), {})

    q0718_status = {
        "question_id": "Q0718",
        "turn_index": q0718_rec.get("turn_index"),
        "target_doc_expected": q0718_rec.get("target_doc"),
        "doc_matched": q0718_rec.get("doc_matched"),
        "matched_target_doc": q0718_rec.get("matched_target_doc"),
        "matched_via_candidate": q0718_rec.get("matched_via_candidate"),
        "trace_titles": q0718_rec.get("trace_titles"),
        "keywords_expected": q0718_rec.get("keywords_expected"),
        "keywords_matched": q0718_rec.get("keywords_matched"),
        "checkpoint_pass": q0718_rec.get("checkpoint_pass"),
        "answer_preview": q0718_rec.get("answer_preview"),
    } if q0718_rec else {}

    q0828_status = {
        "question_id": "Q0828",
        "turn_index": q0828_rec.get("turn_index"),
        "target_doc_expected": q0828_rec.get("target_doc"),
        "doc_matched": q0828_rec.get("doc_matched"),
        "matched_target_doc": q0828_rec.get("matched_target_doc"),
        "matched_via_candidate": q0828_rec.get("matched_via_candidate"),
        "trace_titles": q0828_rec.get("trace_titles"),
        "keywords_expected": q0828_rec.get("keywords_expected"),
        "keywords_matched": q0828_rec.get("keywords_matched"),
        "checkpoint_pass": q0828_rec.get("checkpoint_pass"),
        "answer_preview": q0828_rec.get("answer_preview"),
    } if q0828_rec else {}

    if report_name:
        ticket_val = Path(report_name).stem
    elif limit is not None:
        ticket_val = f"DESKTOP-STRESS-HARNESS-TRIAL-{limit}{('-' + run_tag.upper()) if run_tag else ''}"
    else:
        ticket_val = f"DESKTOP-STRESS-RERUN-FIXED-SCORING-HOME{('-' + run_tag.upper()) if run_tag else ''}"

    summary_payload = {
        "ticket": ticket_val,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": git_head,
        "ai_backend": ai_backend,
        "t_start_app": t_start_app_str,
        "t_server_ready": t_server_ready_str,
        "all_4_workers_resident": all_resident_achieved,
        "worker_timeline": timeline_snapshot,
        "counts": {
            "total_turns": total_turns,
            "cold_turns": len(cold_turns),
            "warm_turns": len(warm_turns),
            "completed_turns": completed_turns,
            "doc_matched_count": doc_matched_count,
            "doc_matched_pct": round(doc_matched_count / total_turns * 100.0, 2) if total_turns else 0.0,
            "keywords_pass_count": kw_pass_count,
            "keywords_pass_pct": round(kw_pass_count / total_turns * 100.0, 2) if total_turns else 0.0,
            "both_passed_count": both_passed_count,
            "both_passed_pct": round(both_passed_count / total_turns * 100.0, 2) if total_turns else 0.0,
            "both_majority_count": both_majority_count,
            "both_majority_pct": round(both_majority_count / total_turns * 100.0, 2) if total_turns else 0.0,
            "both_strict_count": both_strict_count,
            "both_strict_pct": round(both_strict_count / total_turns * 100.0, 2) if total_turns else 0.0,
        },
        "by_warehouse": by_warehouse,
        "by_backend_group": by_backend_group,
        "timing_stats_warm": {
            "ui_e2e_s": compute_dist_stats(warm_ui_e2e),
            "delta_qa_to_complete_s": compute_dist_stats(warm_qa_to_complete),
            "delta_qa_to_first_token_s": compute_dist_stats(warm_qa_to_first_token),
            "delta_qa_to_micro_s": compute_dist_stats(warm_qa_to_micro),
            "pure_retrieval_s": compute_dist_stats(warm_pure_ret),
            "pre_retrieval_wait_s": compute_dist_stats(warm_pre_wait),
        },
        "q0718_status": q0718_status,
        "q0828_status": q0828_status,
        "failed_turns": failed_classification,
        "screenshots": screenshot_hashes,
    }

    with open(summary_json, "w", encoding="utf-8") as sf:
        json.dump(summary_payload, sf, ensure_ascii=False, indent=2)

    log("=" * 95)
    log(f"KET QUA: Total={total_turns} | DocMatched={doc_matched_count}/{total_turns} ({summary_payload['counts']['doc_matched_pct']}%) | "
        f"KeywordsPass={kw_pass_count}/{total_turns} ({summary_payload['counts']['keywords_pass_pct']}%) | "
        f"BothPass={both_passed_count}/{total_turns} ({summary_payload['counts']['both_passed_pct']}%)")
    log(f"Phan bo theo kho: {json.dumps(by_warehouse, ensure_ascii=False)}")
    log(f"Phan bo backend: {json.dumps(by_backend_group, ensure_ascii=False)}")
    log("=" * 95)

    try:
        from generate_stress_rerun_report import generate_report
        generate_report(
            summary_path=summary_json,
            raw_path=raw_turns_jsonl,
            report_path=report_path,
            questions_path=QUESTIONS_JSONL,
        )
        log(f"[REPORT] Da sinh bao cao tai {report_path}")
    except Exception as rep_exc:
        log(f"[REPORT_ERR] Loi khi sinh bao cao: {rep_exc}")

    return summary_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Chay kich ban kiem thu ap luc giao dien that R2")
    parser.add_argument("--limit", type=int, default=None, help="Gioi han so cau can chay (vi du: 8)")
    parser.add_argument("--report-name", type=str, default=None, help="Ten tep bao cao MD xuat ra")
    parser.add_argument("--skip-preflight", action="store_true", help="Bo qua buoc tien tram lam am worker")
    parser.add_argument("--ai-backend", type=str, default=None, help="Ghi de AI backend (local, cagent_api, ...)")
    parser.add_argument("--tag", "--run-tag", dest="run_tag", type=str, default=None, help="Hau to phan biet dot chay (vi du: r2)")
    args = parser.parse_args()

    run_stress_suite(
        limit=args.limit,
        report_name=args.report_name,
        skip_preflight=args.skip_preflight,
        override_backend=args.ai_backend,
        run_tag=args.run_tag,
    )


if __name__ == "__main__":
    main()
