"""Script nghiem thu song cho ve DESKTOP-SPEED-PRESYNTH-MARKERS-HOME tai may nha.

Quy trinh:
1. Khoi dong server Streamlit tren cong 8565 voi cau hinh BB-CONFIG-PARITY-01.
2. Lam am worker khoi 'tong_hop' va xac nhan probe >0 chunks.
3. Hoi cau TH01 qua giao dien Playwright voi ma hoi thoai doc lap.
4. Trich xuat toan bo chuoi marker co timestamp trong nhat ky server.
5. Lap bang quy trach chang sau-truy-hoi tinh bang HIEU TIMESTAMP TRUC TIEP.
"""
from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request
import uuid

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
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
store.TEMPORARY_SOURCES_FILE = store.LOCAL_CHAT_DIR / "temporary_sources.jsonl"
store.NOTEBOOK_SOURCES_FILE = store.LOCAL_CHAT_DIR / "notebook_sources.jsonl"
store.SOURCE_SELECTIONS_FILE = store.LOCAL_CHAT_DIR / "conversation_source_selections.jsonl"
store.TRACES_FILE = store.LOCAL_CHAT_DIR / "traces.jsonl"
store.EXTERNAL_AI_USAGE_FILE = store.LOCAL_CHAT_DIR / "external_ai_usage.jsonl"

from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import save_conversation, load_messages
from aios_habit.streaming_markers import parse_marker_timestamp, diff_marker_timestamps_s
from playwright.sync_api import sync_playwright

PORT = 8565
URL = f"http://localhost:{PORT}"
NOTEBOOK_ID = "NB-C26E1C84"
OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua")
OUT_DIR.mkdir(parents=True, exist_ok=True)
SERVER_LOG_FILE = OUT_DIR / "server_presynth_markers_live_session.log"
SCREENSHOT_FILE = OUT_DIR / "anh-presynth-th01-live.png"

QUESTION_TH01 = (
    "Theo tài liệu Tab led cam ung.pdf (Touch Panel Specification), điều kiện "
    "nhiệt độ và độ ẩm tiêu chuẩn để bảo quản (Storage) touch panel là bao nhiêu?"
)


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


def start_server(port: int) -> subprocess.Popen:
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
    env["AIOS_AI_BACKEND"] = "nakazasen_router"
    env["AIOS_RAGV2_WORKER_PERSIST"] = "1"
    env["AIOS_FEATURE_CHAT_ACTION"] = "1"
    env["AIOS_DOMAIN_ROUTING_ENABLED"] = "1"
    env["AIOS_STREAM_SYNTHESIS"] = "1"
    env["AIOS_FEATURE_ANSWER_DRAFT_FALLBACK"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"

    if SERVER_LOG_FILE.exists():
        try:
            SERVER_LOG_FILE.unlink()
        except Exception:
            pass

    log_handle = open(SERVER_LOG_FILE, "a", encoding="utf-8")
    cmd = [
        str(APP_DIR / ".venv" / "Scripts" / "python.exe"),
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
    proc = subprocess.Popen(
        cmd,
        cwd=APP_DIR,
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
    )
    return proc


def kill_server(proc: subprocess.Popen):
    if proc:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
                proc.wait(timeout=3)
            except Exception:
                pass


def warm_up_tong_hop() -> int:
    from aios_habit.workspace_chat_rag_v2_adapter import (
        ensure_workspace_chat_worker_warming,
        probe_workspace_chat_worker,
        _pipeline_config,
        WorkspaceChatRagV2CanaryConfig,
    )
    cfg = WorkspaceChatRagV2CanaryConfig.from_env()
    p_cfg_tong_hop = _pipeline_config(cfg, cfg.requested_profile, read_only=True, collection_id="tong_hop")
    print("[WARM] Kich hoat lam am BGE persistent worker cho khoi 'tong_hop'...")
    ensure_workspace_chat_worker_warming(blocking=False, pipe_config=p_cfg_tong_hop)

    t_start = time.time()
    while time.time() - t_start < 300:
        res = probe_workspace_chat_worker(question="touch panel specification", domain="tong_hop")
        c_cnt = int(res.get("chunks", 0))
        if res.get("ready") and c_cnt > 0:
            print(f"[WARM] Worker 'tong_hop' da san sang: {c_cnt} chunks! (ok=True)")
            return c_cnt
        print(f"[WARM] Dang nap worker 'tong_hop'... chunks={c_cnt}, cho 5s...")
        time.sleep(5.0)
    return 0


def main():
    print("=" * 80)
    print("NGHIEM THU SONG: DESKTOP-SPEED-PRESYNTH-MARKERS-HOME")
    print("=" * 80)

    # 1. Khoi dong server
    print(f"\n[1] Khoi dong Streamlit server tren cong {PORT}...")
    server_proc = start_server(PORT)
    if not wait_for_server(PORT, timeout=90):
        print(f"[ERROR] Khong the ket noi toi server tai {URL}")
        kill_server(server_proc)
        sys.exit(1)
    print(f"[SERVER] Server san sang tai {URL} (PID={server_proc.pid})")
    time.sleep(2.0)

    try:
        # 2. Lam am khoi tong_hop
        print("\n[2] Lam am khoi 'tong_hop'...")
        chunks_th = warm_up_tong_hop()
        if chunks_th <= 0:
            print("[ERROR] Khoi 'tong_hop' khong the lam am (>0 chunks)!")
            kill_server(server_proc)
            sys.exit(1)

        # 3. Chuan bi hoi thoai TH01
        conv_id = f"CONV-LIVE-PRESYNTH-{uuid.uuid4().hex[:6].upper()}"
        save_conversation(WorkspaceConversation(
            id=conv_id,
            notebook_id=NOTEBOOK_ID,
            title="Live Verify Presynth Markers TH01",
            ai_mode="grounded",
        ))
        print(f"\n[3] Da tao hoi thoai: {conv_id} tren notebook {NOTEBOOK_ID}")

        # 4. Gui cau hoi TH01 qua Playwright
        print(f"\n[4] Dieu huong va gui cau hoi TH01 qua Playwright...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1600, "height": 1000})
            page = context.new_page()

            nav_url = f"{URL}/?nb={NOTEBOOK_ID}&conv={conv_id}&block=tong_hop"
            print(f"[NAV] Mo URL: {nav_url}")
            page.goto(nav_url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)

            page.wait_for_selector('textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"]', timeout=30000)
            textarea = page.locator('textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"]').first
            textarea.fill(QUESTION_TH01)
            page.wait_for_timeout(500)

            send_btn = page.locator(
                f'[class*="st-key-wsc_ask_{conv_id}"] button, [class*="st-key-wsc-action-"] button'
            ).first
            if send_btn.count() > 0:
                send_btn.click()
            else:
                textarea.press("Control+Enter")
            print(f"[SEND] Da gui cau hoi TH01...")

            # Cho luu DB
            for attempt in range(5):
                time.sleep(1.0)
                msgs = load_messages(conv_id)
                if any(m.role == "user" for m in msgs):
                    print(f"[DB] Tin nhan user da luu thanh cong (lan {attempt+1})")
                    break
                textarea.press("Control+Enter")
                page.wait_for_timeout(1000)

            # Cho assistant hoan tat
            print("[WAIT] Dang cho assistant tra loi...")
            t0 = time.time()
            completed = False
            while time.time() - t0 < 300:
                msgs = load_messages(conv_id)
                if len(msgs) >= 2 and msgs[-1].role == "assistant":
                    completed = True
                    time.sleep(2)
                    break
                page.wait_for_timeout(1000)

            dur = time.time() - t0
            print(f"[RESULT] Luot hoan tat sau {dur:.2f}s (completed={completed})")

            # Chup anh bang chung
            try:
                page.locator("body").screenshot(path=str(SCREENSHOT_FILE), timeout=15000)
                print(f"[SCREENSHOT] Da chup anh bang chung: {SCREENSHOT_FILE.name}")
            except Exception as e:
                print(f"[WARN] Khong the chup anh: {e}")

            browser.close()

        # 5. Doc nhat ky server va trich xuat marker
        print("\n[5] Doc nhat ky server va trich xuat chuoi marker...")
        time.sleep(1.0)
        with open(SERVER_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            lines = [l.strip() for l in f if l.strip()]

        print(f"[LOG] Tong so dong nhat ky: {len(lines)}")
        matching_markers = []
        for l in lines:
            if (f"conv={conv_id}" in l) or ("[RETRIEVAL_MICRO_TIMING]" in l and "collection=tong_hop" in l):
                matching_markers.append(l)

        print("\n--- CAC DONG MARKER CUA HOI THOAI TH01 ---")
        for m in matching_markers:
            print(m)

        # 6. Lap bang quy trach bang phep tru timestamp truc tiep
        print("\n" + "=" * 90)
        print("BANG QUY TRACH CHIEU SAU BANG HIEU TIMESTAMP TRUC TIEP")
        print("=" * 90)

        marker_dict = {}
        for l in matching_markers:
            # Match timestamp
            ts_m = re.search(r"timestamp=(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})", l)
            ts = ts_m.group(1) if ts_m else None
            if "[STREAMING_QA_START]" in l:
                marker_dict["STREAMING_QA_START"] = (l, ts)
            elif "[RETRIEVAL_MICRO_TIMING]" in l:
                marker_dict["RETRIEVAL_MICRO_TIMING"] = (l, ts)
            elif "[PRE_SYNTH_STEP]" in l:
                step_m = re.search(r"step=([a-zA-Z0-9_]+)", l)
                if step_m:
                    marker_dict[f"PRE_SYNTH_STEP:{step_m.group(1)}"] = (l, ts)
            elif "[ROUTER_SYNTH_START]" in l:
                marker_dict["ROUTER_SYNTH_START"] = (l, ts)
            elif "[STREAMING_QA_FIRST_TOKEN]" in l:
                marker_dict["STREAMING_QA_FIRST_TOKEN"] = (l, ts)
            elif "[ROUTER_SYNTH_DONE]" in l:
                marker_dict["ROUTER_SYNTH_DONE"] = (l, ts)
            elif "[STREAMING_QA_COMPLETE]" in l:
                marker_dict["STREAMING_QA_COMPLETE"] = (l, ts)

        ordered_keys = [
            ("STREAMING_QA_START", "Bat dau turn chat"),
            ("RETRIEVAL_MICRO_TIMING", "Truy hoi xong (BGE hybrid)"),
            ("PRE_SYNTH_STEP:retrieval_received", "Nhan xong ket qua truy hoi"),
            ("PRE_SYNTH_STEP:sources_formatted", "Format nguon trich xong"),
            ("PRE_SYNTH_STEP:domain_badge_attached", "Gan badge domain xong"),
            ("PRE_SYNTH_STEP:executor_enqueued", "Day vao executor (enqueue)"),
            ("PRE_SYNTH_STEP:executor_task_started", "Executor bat dau chay tac vu"),
            ("PRE_SYNTH_STEP:route_privacy_done", "Route chain + privacy xong"),
            ("PRE_SYNTH_STEP:pre_router", "Ngay truoc router"),
            ("ROUTER_SYNTH_START", "Router synth bat dau"),
            ("STREAMING_QA_FIRST_TOKEN", "Ky tu dau tien ve UI (TTFT)"),
            ("ROUTER_SYNTH_DONE", "Router tong hop xong"),
            ("STREAMING_QA_COMPLETE", "Hoan tat toan bo turn"),
        ]

        print(f"{'STT':<4} | {'Moc marker':<36} | {'Timestamp':<24} | {'Hieu thoi gian (s)':<18}")
        print("-" * 90)

        prev_ts = None
        stt = 1
        for k, desc in ordered_keys:
            if k in marker_dict:
                raw, ts = marker_dict[k]
                diff_str = "-"
                if prev_ts and ts:
                    diff_val = diff_marker_timestamps_s(prev_ts, ts)
                    diff_str = f"+{diff_val:.3f}s"
                prev_ts = ts
                print(f"{stt:<4} | {desc:<36} | {str(ts):<24} | {diff_str:<18}")
                stt += 1
            else:
                print(f"{stt:<4} | {desc + ' (CHUA CO)':<36} | {'-':<24} | {'-':<18}")
                stt += 1

        print("=" * 90)

    finally:
        print(f"\n[DONE] Dung server Streamlit (PID={server_proc.pid})...")
        kill_server(server_proc)


if __name__ == "__main__":
    main()
