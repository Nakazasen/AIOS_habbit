"""Script thuc thi dong bo va do lai cho ve DESKTOP-PC0575-SYNC-GROUPD.
May dich: KDTVN-PC0575 (Intel Core i5-8265U, 16GB RAM, CPU-only).
Ban sua: 674940e4 (DESKTOP-SPEED-GROUPD-SYNTH-FIX-HOME)
- Kiem tra 4 cau hoi hoi dap that qua UI:
  1. TT13 (tri_thuc): wsc-045417eda8a424bb68259105.txt
  2. TT18 (tri_thuc): wsc-48c40c0b3b6b5a4f1681f66d.txt
  3. TT20 (tri_thuc): wsc-0e3642278207c7c84eba8acd.txt / wsc-c714c329588af1673186fed9.txt
  4. OOS4 (dieu_tra_loi auto): KTD-2025-07-0678-Iris2024-C33-A1-C6770.xlsx
- Tieu chi: 4/4 cau dat ca tai lieu dich (doc_matched) VA nguong tu khoa (keywords_matched).
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
from typing import Any, Optional
import urllib.request
import uuid

# Cau hinh moi truong chuan BB-CONFIG-PARITY-01
os.environ["AIOS_RAGV2_WORKER_PERSIST"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["AIOS_RETRIEVAL_DEVICE"] = "cpu"
os.environ["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
os.environ["AIOS_RAG_V2_NUMPY_SCORING"] = "1"
os.environ["AIOS_BGE_QUERY_TIMEOUT"] = "1800"
os.environ["AIOS_BGE_INIT_TIMEOUT"] = "1200"
os.environ["AIOS_BGE_WARM_ABSOLUTE_TIMEOUT"] = "1200"
os.environ["AIOS_BGE_WARM_NO_PROGRESS_TIMEOUT"] = "600"
os.environ["AIOS_BGE_PERSIST_CONNECT_TIMEOUT"] = "1200"
os.environ["AIOS_AI_BACKEND"] = "local"
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
from aios_habit.workspace_chat_rag_v2_adapter import (
    WorkspaceChatRagV2CanaryConfig,
    _warmup_pipeline_config,
    _pipeline_config,
)
from aios_habit.local_jsonl import clear_jsonl_cache
from playwright.sync_api import sync_playwright

PORT = 8501
URL = f"http://127.0.0.1:{PORT}"

OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua")
OUT_DIR.mkdir(parents=True, exist_ok=True)

DOCS_OUT_DIR = Path(r"D:\Sandbox\AIOS_habbit\docs\phieu-viec\ket-qua")
DOCS_OUT_DIR.mkdir(parents=True, exist_ok=True)

SERVER_LOG_FILE = OUT_DIR / "server_desktop_pc0575_sync_groupd.log"
SESSION_LOG_FILE = OUT_DIR / "session_desktop_pc0575_sync_groupd.log"
JSON_RESULT_FILE = OUT_DIR / "ket-qua-do-desktop-pc0575-sync-groupd.json"

DAEMON_LOGS = {
    "tri_thuc": Path(r"D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\logs\bge_worker_daemon.stderr.log"),
    "tong_hop": Path(r"D:\Sandbox\AIOS_habbit\scratch\restore-index-split\blocks\tong_hop\logs\bge_worker_daemon.stderr.log"),
    "lsu": Path(r"D:\Sandbox\AIOS_habbit\scratch\restore-index-split\blocks\lsu\logs\bge_worker_daemon.stderr.log"),
    "dieu_tra_loi": Path(r"D:\Sandbox\AIOS_habbit\scratch\restore-index-split\blocks\dieu_tra_loi\logs\bge_worker_daemon.stderr.log"),
}

from aios_habit.rag_v2.bge_subprocess_client import pipe_name_for_config

_CANARY_CFG = WorkspaceChatRagV2CanaryConfig.from_env()
PIPE_CONFIGS = {
    "tri_thuc": _warmup_pipeline_config(_CANARY_CFG),
    "tong_hop": _pipeline_config(_CANARY_CFG, "bge_m3_hybrid", read_only=True, collection_id="tong_hop"),
    "lsu": _pipeline_config(_CANARY_CFG, "bge_m3_hybrid", read_only=True, collection_id="lsu"),
    "dieu_tra_loi": _pipeline_config(_CANARY_CFG, "bge_m3_hybrid", read_only=True, collection_id="dieu_tra_loi"),
}
PIPE_NAMES = {col: pipe_name_for_config(cfg) for col, cfg in PIPE_CONFIGS.items()}


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(SESSION_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def kill_all_workers_and_servers():
    log("Don dep sach toan bo tien trinh streamlit va bge_subprocess_worker cu...")
    my_pid = os.getpid()
    ps_cmd = (
        f"$procs = Get-CimInstance Win32_Process | Where-Object {{ "
        f"($_.CommandLine -like '*bge_subprocess_worker*' -or "
        f"$_.CommandLine -like '*workspace_chat_app.py*' -or "
        f"$_.CommandLine -like '*streamlit*') -and $_.ProcessId -ne {my_pid} "
        f"}}; "
        f"foreach ($p in $procs) {{ Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }}"
    )
    subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
    time.sleep(2.0)
    log("Da don dep sach cac tien trinh cu.")


def wait_for_server(port: int, timeout: int = 120) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/_stcore/health")
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
    env["AIOS_BGE_QUERY_TIMEOUT"] = "1800"
    env["AIOS_BGE_INIT_TIMEOUT"] = "1200"
    env["AIOS_BGE_WARM_ABSOLUTE_TIMEOUT"] = "1200"
    env["AIOS_BGE_WARM_NO_PROGRESS_TIMEOUT"] = "600"
    env["AIOS_BGE_PERSIST_CONNECT_TIMEOUT"] = "1200"
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
        str(APP_DIR / "src" / "aios_habit" / "workspace_chat_app.py"),
        "--server.port",
        str(port),
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
    """Theo doi tien trinh nap va trang thai san sang cua cac khoi tu daemon logs va named pipes."""

    def __init__(self, initial_offsets: dict[str, int]):
        self.offsets = dict(initial_offsets)
        self.stop_event = threading.Event()
        self.timeline: dict[str, dict[str, Any]] = {
            col: {
                "pipe_name": PIPE_NAMES[col],
                "spawn_ts": None,
                "spawn_pid": None,
                "ready_ts": None,
                "init_total_ms": None,
                "pipe_available_ts": None,
            }
            for col in DAEMON_LOGS
        }
        self.lock = threading.Lock()

    def run_poll(self):
        while not self.stop_event.is_set():
            now_dt = datetime.now()
            now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

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
                                if "bge_worker_serve pipe=" in line_s and "already exists" not in line_s:
                                    m = re.search(r"pid=(\d+)", line_s)
                                    pid_val = int(m.group(1)) if m else None
                                    if self.timeline[col]["spawn_ts"] is None:
                                        self.timeline[col]["spawn_ts"] = event_ts
                                        self.timeline[col]["spawn_pid"] = pid_val
                                    log(f"[TIMELINE] Khoi '{col}' da spawn worker PID={pid_val} tai: {event_ts}")
                                elif "bge_worker_stage backend=" in line_s and "init_ms=" in line_s:
                                    m = re.search(r"init_ms=([\d\.]+)", line_s)
                                    ms_val = float(m.group(1)) if m else None
                                    if self.timeline[col]["ready_ts"] is None:
                                        self.timeline[col]["ready_ts"] = event_ts
                                        self.timeline[col]["init_total_ms"] = ms_val
                                    log(f"[TIMELINE] >>> Khoi '{col}' DAT TRANG THAI SAN SANG (init_total={ms_val}ms) tai: {event_ts} <<<")
                except Exception:
                    pass

            for col in DAEMON_LOGS:
                with self.lock:
                    if self.timeline[col]["pipe_available_ts"] is None:
                        pipe_path = self.timeline[col]["pipe_name"]
                        if _pipe_instance_available(pipe_path):
                            self.timeline[col]["pipe_available_ts"] = now_str
                            log(f"[NAMED_PIPE] Named Pipe cua khoi '{col}' da AVAILABLE tai: {now_str}")

            time.sleep(0.1)

    def is_col_ready(self, col: str) -> bool:
        with self.lock:
            return self.timeline[col]["ready_ts"] is not None or _pipe_instance_available(self.timeline[col]["pipe_name"])

    def is_ready_for_cols(self, cols: list[str]) -> bool:
        with self.lock:
            return all(
                self.timeline[c]["ready_ts"] is not None or _pipe_instance_available(self.timeline[c]["pipe_name"])
                for c in cols
            )


def _extract_ts(marker_line: str) -> str | None:
    if not marker_line:
        return None
    m = re.search(r"timestamp=(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})", marker_line)
    return m.group(1) if m else None


def evaluate_turn_scoring(
    answer_text: str,
    target_docs: list[str],
    keywords: list[str],
    trace_id: str | None = None,
) -> dict[str, Any]:
    matched_docs = []
    trace_sources = []
    if trace_id:
        try:
            traces_path = APP_DIR / "local_cases" / "workspace_chat" / "traces.jsonl"
            if traces_path.exists():
                with open(traces_path, "r", encoding="utf-8", errors="replace") as tf:
                    for line in tf:
                        if trace_id in line:
                            data = json.loads(line)
                            for node in data.get("nodes", []):
                                if node.get("node_type") == "source":
                                    for key in ("title", "label", "source_path"):
                                        val = node.get(key)
                                        if val:
                                            trace_sources.append(str(val))
        except Exception as e:
            log(f"[WARN] Khong the doc trace sources: {e}")

    search_corpus = (answer_text + " " + " ".join(trace_sources)).lower()
    for td in target_docs:
        td_clean = td.strip()
        td_stem = td_clean.split(".")[0]
        if td_clean.lower() in search_corpus or td_stem.lower() in search_corpus:
            matched_docs.append(td)
    doc_matched = len(matched_docs) > 0

    matched_keywords = []
    for kw in keywords:
        if kw.lower() in answer_text.lower():
            matched_keywords.append(kw)
    kw_ratio = len(matched_keywords) / len(keywords) if keywords else 0.0
    keywords_matched = len(matched_keywords) >= 2 or kw_ratio >= 0.40
    verdict_and = doc_matched and keywords_matched

    return {
        "doc_matched": doc_matched,
        "matched_docs": matched_docs,
        "trace_sources": trace_sources,
        "keywords_matched": keywords_matched,
        "matched_keywords": matched_keywords,
        "total_keywords": len(keywords),
        "matched_keyword_count": len(matched_keywords),
        "keyword_ratio": kw_ratio,
        "keyword_ratio_pct": f"{kw_ratio * 100:.1f}%",
        "verdict_and": verdict_and,
    }


def execute_playwright_turn(
    browser,
    conv_id: str,
    notebook_id: str,
    question: str,
    target_block: str,
    title: str,
    target_docs: list[str],
    keywords: list[str],
    screenshot_file: Path,
    server_log_file: Path,
) -> dict[str, Any]:
    """Thuc thi mot luot chat qua Playwright va cham diem doc + keywords."""
    log("\n" + "=" * 70)
    log(f"BAT DAU LUOT CHAT: {title}")
    log(f"Conv ID: {conv_id} | Notebook: {notebook_id} | Block: {target_block}")
    log(f"Target docs: {target_docs}")
    log(f"Keywords: {keywords}")
    log("=" * 70)

    context = browser.new_context(viewport={"width": 1600, "height": 1000})
    page = context.new_page()

    save_conversation(WorkspaceConversation(
        id=conv_id,
        notebook_id=notebook_id,
        title=title,
        ai_mode="grounded",
    ))

    nav_url = f"{URL}/?nb={notebook_id}&conv={conv_id}&block={target_block}"
    log(f"[PLAYWRIGHT] Dieu huong den: {nav_url}")
    for attempt in range(5):
        try:
            page.goto(nav_url, wait_until="domcontentloaded", timeout=60000)
            break
        except Exception as e:
            log(f"[PLAYWRIGHT] Lan {attempt+1} goto failed ({e}), cho 2s thu lai...")
            time.sleep(2.0)
    else:
        page.goto(nav_url, wait_until="domcontentloaded", timeout=60000)

    clear_jsonl_cache()
    initial_user_msgs = sum(1 for m in load_messages(conv_id) if m.role == "user")

    textarea = page.locator('textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"], textarea[placeholder*="Nhập câu hỏi"]').first
    textarea.wait_for(state="visible", timeout=120000)

    send_btn = page.locator(
        f'[class*="st-key-wsc_ask_{conv_id}"] button, '
        f'[class*="st-key-wsc-action-{conv_id}"] button, '
        f'[class*="st-key-wsc-action-"] button'
    ).first
    send_btn.wait_for(state="visible", timeout=120000)
    page.wait_for_timeout(500)

    textarea.fill(question)
    page.wait_for_timeout(500)

    t_fire = datetime.now()
    t_fire_str = t_fire.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log(f"[CONTROLLED_FIRE] >>> BAN CAU HOI ({conv_id}) TAI MOC: {t_fire_str} <<<")

    clicked = False
    try:
        send_btn.click(force=True, timeout=10000)
        clicked = True
        log(f"[PLAYWRIGHT] Da click send_btn ({conv_id})!")
    except Exception as e:
        log(f"[PLAYWRIGHT] Click send_btn exception ({e}), thu dispatch click qua JS...")
        try:
            page.evaluate(
                f"""() => {{
                    const btn = document.querySelector('[class*="st-key-wsc_ask_{conv_id}"] button, [class*="st-key-wsc-action-{conv_id}"] button, [class*="st-key-wsc-action-"] button');
                    if (btn) {{ btn.click(); return true; }}
                    return false;
                }}"""
            )
            clicked = True
        except Exception as e2:
            log(f"[PLAYWRIGHT] JS click exception ({e2})")

    if not clicked:
        try:
            textarea.press("Control+Enter")
            log("[PLAYWRIGHT] Da bam Control+Enter qua textarea!")
        except Exception as e:
            log(f"[PLAYWRIGHT] Textarea press exception: {e}")

    for attempt in range(60):
        time.sleep(0.5)
        clear_jsonl_cache()
        msgs = load_messages(conv_id)
        cur_user_msgs = sum(1 for m in msgs if m.role == "user")
        if cur_user_msgs > initial_user_msgs:
            log(f"[DB] User message moi da luu sau {(attempt+1)*0.5:.1f}s")
            break
        if attempt >= 4 and attempt % 4 == 0:
            try:
                cur_val = textarea.input_value()
                if not cur_val.strip():
                    log("[PLAYWRIGHT] Textarea da trong, tiep tuc cho user message vao DB...")
                else:
                    log(f"[PLAYWRIGHT] Re-triggering send attempt {attempt}...")
                    textarea.focus()
                    textarea.press("Control+Enter")
                    send_btn.click(force=True, timeout=5000)
            except Exception:
                pass
    else:
        log("[WARN] Timeout 30s cho user message luu vao DB!")

    qa_start_line = None
    micro_line = None
    first_token_line = None
    complete_line = None

    t_watch_start = time.time()
    in_conv_window = False
    watch_timeout_s = 600

    while time.time() - t_watch_start < watch_timeout_s:
        if server_log_file.exists():
            log_text = server_log_file.read_text(encoding="utf-8", errors="replace")
            for line in log_text.splitlines():
                line_clean = line.strip()
                if "[STREAMING_QA_START]" in line_clean:
                    if f"conv={conv_id}" in line_clean:
                        in_conv_window = True
                        if not qa_start_line:
                            qa_start_line = line_clean
                            log(f"[MARKER DETECTED] QA_START: {qa_start_line}")
                    else:
                        in_conv_window = False

                if not in_conv_window:
                    continue

                if "[RETRIEVAL_MICRO_TIMING]" in line_clean and not micro_line:
                    micro_line = line_clean
                    log(f"[MARKER DETECTED] MICRO: {micro_line}")

                if "[STREAMING_QA_FIRST_TOKEN]" in line_clean and f"conv={conv_id}" in line_clean and not first_token_line:
                    first_token_line = line_clean
                    log(f"[MARKER DETECTED] FIRST_TOKEN: {first_token_line}")

                if (("[STREAMING_QA_COMPLETE]" in line_clean and f"conv={conv_id}" in line_clean) or
                    ("[DRAFT_FALLBACK_COMPLETE]" in line_clean and f"conv={conv_id}" in line_clean)) and not complete_line:
                    complete_line = line_clean
                    log(f"[MARKER DETECTED] COMPLETE: {complete_line}")

            if qa_start_line and micro_line and complete_line:
                log(f"[TURN DONE] Luot {conv_id} da hoan tat day du!")
                break

        time.sleep(0.5)

    ans_text = ""
    ans_trace_id = None
    for _ in range(30):
        clear_jsonl_cache()
        msgs = load_messages(conv_id)
        ast = [m for m in msgs if m.role == "assistant" and len(m.content or "") > 0]
        if ast:
            ans_text = ast[-1].content
            ans_trace_id = getattr(ast[-1], "trace_id", None)
            break
        time.sleep(0.5)

    try:
        page.wait_for_timeout(2000)
        page.screenshot(path=str(screenshot_file), animations="disabled", timeout=60000)
        # Copy sang docs thu muc
        docs_screenshot = DOCS_OUT_DIR / screenshot_file.name
        shutil.copy2(screenshot_file, docs_screenshot)
        log(f"[SCREENSHOT] Da chup anh giao dien: {screenshot_file} va sao chep sang {docs_screenshot}")
    except Exception as exc:
        log(f"[SCREENSHOT] Khong the chup anh: {exc}")

    page.close()
    context.close()

    ts_qa_start = _extract_ts(qa_start_line)
    ts_micro = _extract_ts(micro_line)
    ts_first_token = _extract_ts(first_token_line)
    ts_complete = _extract_ts(complete_line)

    delta_qa_to_micro = diff_marker_timestamps_s(ts_qa_start, ts_micro) if (ts_qa_start and ts_micro) else None
    delta_qa_to_first_token = diff_marker_timestamps_s(ts_qa_start, ts_first_token) if (ts_qa_start and ts_first_token) else None
    delta_qa_to_complete = diff_marker_timestamps_s(ts_qa_start, ts_complete) if (ts_qa_start and ts_complete) else None

    actual_col = "unknown"
    micro_stats: dict[str, str] = {}
    if micro_line:
        m_col = re.search(r"collection=([^\s]+)", micro_line)
        if m_col:
            actual_col = m_col.group(1)
        for k in [
            "pipe_wait_ms",
            "coverage_verify_ms",
            "lexical_ms",
            "embed_ms",
            "dense_ms",
            "sparse_ms",
            "fuse_ms",
            "context_expand_ms",
            "collection",
            "dense_resident",
        ]:
            m_stat = re.search(rf"{k}=([^\s]+)", micro_line)
            if m_stat:
                micro_stats[k] = m_stat.group(1)

    app_total_s = None
    if complete_line:
        m_tot = re.search(r"total_s=([0-9\.]+)", complete_line)
        if m_tot:
            app_total_s = float(m_tot.group(1))

    ttft_s = None
    if first_token_line:
        m_tt = re.search(r"ttft_s=([0-9\.]+)", first_token_line)
        if m_tt:
            ttft_s = float(m_tt.group(1))

    scoring = evaluate_turn_scoring(ans_text, target_docs, keywords, trace_id=ans_trace_id)

    log(f"[{conv_id}] KET QUA CHAM DIEM:")
    log(f"  doc_matched: {scoring['doc_matched']} (matched: {scoring['matched_docs']})")
    log(f"  keywords_matched: {scoring['keywords_matched']} ({scoring['matched_keyword_count']}/{scoring['total_keywords']} = {scoring['keyword_ratio_pct']}: {scoring['matched_keywords']})")
    log(f"  VERDICT AND: {scoring['verdict_and']}")
    log(f"  QA_START->MICRO: {delta_qa_to_micro}s | ttft_s: {ttft_s}s | total_s: {app_total_s}s")
    log(f"  Answer preview (first 200 chars): {ans_text[:200]}")

    return {
        "conv_id": conv_id,
        "notebook_id": notebook_id,
        "title": title,
        "question": question,
        "target_block": target_block,
        "actual_collection": actual_col,
        "t_fire": t_fire_str,
        "app_total_s": app_total_s,
        "ttft_s": ttft_s,
        "delta_qa_to_micro_s": delta_qa_to_micro,
        "delta_qa_to_first_token_s": delta_qa_to_first_token,
        "delta_qa_to_complete_s": delta_qa_to_complete,
        "micro_stats": micro_stats,
        "answer_length": len(ans_text),
        "answer_text": ans_text,
        "answer_preview": ans_text[:300] if ans_text else "",
        "scoring": scoring,
    }


def main():
    log("=" * 80)
    log("BAT DAU THUC THI VE DESKTOP-PC0575-SYNC-GROUPD (COMMIT 674940e4)")
    log("=" * 80)

    git_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=APP_DIR, capture_output=True, text=True
    ).stdout.strip()
    log(f"Git HEAD hien tai: {git_head}")

    kill_all_workers_and_servers()

    initial_offsets = {}
    for col, log_path in DAEMON_LOGS.items():
        if log_path.exists():
            initial_offsets[col] = log_path.stat().st_size
        else:
            initial_offsets[col] = 0

    tracker = WorkerTimelineTracker(initial_offsets)
    poll_thread = threading.Thread(target=tracker.run_poll, daemon=True)
    poll_thread.start()

    log("\n" + "=" * 80)
    log(">>> KHOI DONG SERVER STREAMLIT CHO VE SYNC-GROUPD <<<")
    log("=" * 80)

    t_start_app = datetime.now()
    server_proc = start_server(PORT, SERVER_LOG_FILE, ai_backend="local")

    if not wait_for_server(PORT, timeout=120):
        log("[ERROR] Server khong phan hoi sau 120s!")
        kill_server(server_proc)
        tracker.stop_event.set()
        sys.exit(1)

    t_server_ready = datetime.now()
    elapsed_ready = (t_server_ready - t_start_app).total_seconds()
    log(f"[APP] Server san sang sau {elapsed_ready:.3f}s tai {t_server_ready}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        log("[WARMUP] Mo trang NB-8354F455 de kich hoat spawn va preload cac worker...")
        warm_ctx = browser.new_context(viewport={"width": 1600, "height": 1000})
        warm_page = warm_ctx.new_page()
        try:
            warm_page.goto(f"{URL}/?nb=NB-8354F455", wait_until="domcontentloaded", timeout=60000)
            warm_ta = warm_page.locator('textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"], textarea[placeholder*="Nhập câu hỏi"]').first
            warm_ta.wait_for(state="visible", timeout=60000)
            warm_page.wait_for_timeout(2000)
            log("[WARMUP] Trang NB-8354F455 da render xong composer va kich hoat cac worker!")
        except Exception as e:
            log(f"[WARMUP] Chu y khi mo trang warmup: {e}")
        finally:
            warm_page.close()
            warm_ctx.close()

        log("\nCho khoi tri_thuc va dieu_tra_loi san sang...")
        for waited_s in range(900):
            if tracker.is_ready_for_cols(["tri_thuc", "dieu_tra_loi"]):
                log(f"[OK] Ca tri_thuc va dieu_tra_loi da san sang sau {waited_s}s!")
                break
            time.sleep(2.0)
        else:
            log("[WARN] Timeout 900s cho tri_thuc va dieu_tra_loi, van tiep tuc do theo thuc te...")

        # Danh sach 4 cau hoi kiem chung Group D
        results = []

        # 1. Turn 1: TT13 (tri_thuc)
        res_tt13 = execute_playwright_turn(
            browser,
            conv_id="CONV-SYNC-GROUPD-TT13",
            notebook_id="NB-8354F455",
            question="Trong tài liệu 通函 管理 システム ・基本機能一覧 (wsc-045417eda8a424bb68259105.txt), hệ quản trị cơ sở dữ liệu nào được sử dụng để đăng ký thùng mới (新規通函)?",
            target_block="tri_thuc",
            title="Group D - TT13 (tri_thuc - wsc-045417eda8a424bb68259105.txt)",
            target_docs=["wsc-045417eda8a424bb68259105.txt", "wsc-3b0a03602329b711cca4928c.txt"],
            keywords=["MySQL", "通函", "新規通函", "PRIMARY FEED P ASSY", "部品箱"],
            screenshot_file=OUT_DIR / "anh-pc0575-sync-groupd-tt13.png",
            server_log_file=SERVER_LOG_FILE,
        )
        results.append(res_tt13)
        time.sleep(2.0)

        # 2. Turn 2: TT18 (tri_thuc)
        res_tt18 = execute_playwright_turn(
            browser,
            conv_id="CONV-SYNC-GROUPD-TT18",
            notebook_id="NB-8354F455",
            question="Theo tài liệu cấu hình liên kết chỉ thị sản xuất sang MOM Opcenter (wsc-48c40c0b3b6b5a4f1681f66d.txt), việc phán định một chỉ thị có được liên kết sang MOM hay không dựa vào thiết lập nào trên máy chủ VN2?",
            target_block="tri_thuc",
            title="Group D - TT18 (tri_thuc - wsc-48c40c0b3b6b5a4f1681f66d.txt)",
            target_docs=["wsc-48c40c0b3b6b5a4f1681f66d.txt", "wsc-015a1b6d9a94dc147ca10588.txt"],
            keywords=["MRP", "製造バージョン", "連携条件マスタ", "VN2", "MES", "OPCENTER Execution CORE", "T_IF_PROD_RESULT"],
            screenshot_file=OUT_DIR / "anh-pc0575-sync-groupd-tt18.png",
            server_log_file=SERVER_LOG_FILE,
        )
        results.append(res_tt18)
        time.sleep(2.0)

        # 3. Turn 3: TT20 (tri_thuc)
        res_tt20 = execute_playwright_turn(
            browser,
            conv_id="CONV-SYNC-GROUPD-TT20",
            notebook_id="NB-8354F455",
            question="Trong tài liệu thuyết trình KDC Tính phương hướng của AMS (wsc-0e3642278207c7c84eba8acd.txt / wsc-c714c329588af1673186fed9.txt), mã dự án / khu vực 3 chữ cái nào được nêu trong slide đầu tiên?",
            target_block="tri_thuc",
            title="Group D - TT20 (tri_thuc - wsc-0e3642278207c7c84eba8acd.txt)",
            target_docs=["wsc-0e3642278207c7c84eba8acd.txt", "wsc-c714c329588af1673186fed9.txt"],
            keywords=["3DA", "AMS", "KDC"],
            screenshot_file=OUT_DIR / "anh-pc0575-sync-groupd-tt20.png",
            server_log_file=SERVER_LOG_FILE,
        )
        results.append(res_tt20)
        time.sleep(2.0)

        # 4. Turn 4: OOS4 (dieu_tra_loi / auto)
        res_oos4 = execute_playwright_turn(
            browser,
            conv_id="CONV-SYNC-GROUPD-OOS4",
            notebook_id="NB-8354F455",
            question="Trong báo cáo điều tra lỗi C6770 (KTD-2025-07-0678) của dòng máy Iris2024, hiện tượng lỗi khi thực hiện U155 và nguyên nhân phát sinh âm thanh lạ từ PWB IH là gì?",
            target_block="auto",
            title="Group D - OOS4 (dieu_tra_loi auto - KTD-2025-07-0678-Iris2024-C33-A1-C6770.xlsx)",
            target_docs=["KTD-2025-07-0678-Iris2024-C33-A1-C6770.xlsx"],
            keywords=["C6770", "KTD-2025-07-0678", "Iris2024"],
            screenshot_file=OUT_DIR / "anh-pc0575-sync-groupd-oos4.png",
            server_log_file=SERVER_LOG_FILE,
        )
        results.append(res_oos4)
        time.sleep(2.0)

        # 5. Turn 5: L2 Diagnostic (lsu)
        res_l2 = execute_playwright_turn(
            browser,
            conv_id="CONV-SYNC-GROUPD-L2-DIAG",
            notebook_id="NB-8354F455",
            question="Trong báo cáo điều tra lỗi C7620 (KTD-2026-02-0244) của cụm LSU Iris2024, kết quả kiểm tra cho thấy giắc cắm nào bị tuột/lỏng dẫn đến mất tín hiệu?",
            target_block="lsu",
            title="Group D - L2 Diagnostic (lsu - KTD-2026-02-0244)",
            target_docs=["KTD-2026-02-0244-Iris2024-C32-A2-C7620.xlsx", "KTD-2026-0500_Sirius2_C7620_B3_toner Empty.xlsx"],
            keywords=["YC5", "302XD93130", "POLYGON", "C7620", "KTD-2026-02-0244", "FFC", "Sirius", "LSU"],
            screenshot_file=OUT_DIR / "anh-pc0575-sync-groupd-l2-diag.png",
            server_log_file=SERVER_LOG_FILE,
        )
        results.append(res_l2)

        browser.close()

    tracker.stop_event.set()
    kill_server(server_proc)
    kill_all_workers_and_servers()

    log("\n" + "=" * 80)
    log("TONG HOP KET QUA 4 CAU DO LAI (GROUP D) TAI PC0575:")
    log("=" * 80)
    target_results = results[:4]
    diag_results = results[4:]

    total_target_passed = sum(1 for r in target_results if r["scoring"]["verdict_and"])
    for r in results:
        sc = r["scoring"]
        passed = sc["verdict_and"]
        tag = "[MUC TIEU]" if r in target_results else "[DIAGNOSTIC]"
        log(f"{tag} - {r['conv_id']}: doc_matched={sc['doc_matched']} ({sc['matched_docs']}) | keywords_matched={sc['keywords_matched']} ({sc['matched_keyword_count']}/{sc['total_keywords']} = {sc['keyword_ratio_pct']}: {sc['matched_keywords']}) | VERDICT AND = {'PASS' if passed else 'FAIL'}")

    log(f"\nTong so cau muc tieu dat PASS (doc_matched VA keywords_matched): {total_target_passed}/4 ({total_target_passed/4*100:.1f}%)")

    final_payload = {
        "ma_ve": "DESKTOP-PC0575-SYNC-GROUPD",
        "trang_thai": "HOAN_THANH" if total_target_passed == 4 else "CHUA_DAT",
        "git_head": git_head,
        "thoi_diem": datetime.now(timezone.utc).isoformat(),
        "target_passed": total_target_passed,
        "target_total": 4,
        "target_results": target_results,
        "diagnostic_results": diag_results,
        "results": results,
    }

    with open(JSON_RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    docs_json = DOCS_OUT_DIR / JSON_RESULT_FILE.name
    with open(docs_json, "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    log(f"Da ghi du lieu ket qua JSON: {JSON_RESULT_FILE} va {docs_json}")


if __name__ == "__main__":
    main()
