"""Live Acceptance Script for DESKTOP-SPEED-WARM-ALIGNMENT-FIX-HOME.

Flow:
1. Kill all old workers and server processes cleanly.
2. Start server on port 8565 with BB-CONFIG-PARITY-01.
3. Run warming flow for tong_hop and lsu (verifying named pipes exist and is_ready is True).
4. Shoot Turn TH01 in block 'tong_hop' via Playwright.
5. Shoot Turn C7620 in block 'lsu' via Playwright.
6. Verify quality criteria:
   - WORKER_WARM_LOOP_STEP (if any) finishes with retrieval_success and elapsed_wait_s <= 10s.
   - RETRIEVAL_MICRO_TIMING is genuine and recorded for each turn.
   - STREAMING_QA_COMPLETE has ok=True.
   - No persist_timeout errors.
"""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request
import uuid

# Set persistent worker environment BEFORE imports/probe
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
os.environ["PYTHONIOENCODING"] = "utf-8"

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

from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import save_conversation, load_messages
from aios_habit.workspace_chat_rag_v2_adapter import (
    ensure_workspace_chat_worker_warming,
    probe_workspace_chat_worker,
    _pipeline_config,
    WorkspaceChatRagV2CanaryConfig,
    _SUBPROCESS_CLIENT,
)
from aios_habit.rag_v2.bge_worker_protocol import pipe_name_for_config
from aios_habit.rag_v2.bge_subprocess_client import _pipe_instance_available
from playwright.sync_api import sync_playwright

PORT = 8565
URL = f"http://localhost:{PORT}"
NOTEBOOK_ID = "NB-C26E1C84"
OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SERVER_LOG_FILE = OUT_DIR / "server_desktop_speed_warm_alignment_fix_home.log"
SESSION_LOG_FILE = OUT_DIR / "session_desktop_speed_warm_alignment_fix_home.log"
SCREENSHOT_TH01 = OUT_DIR / "anh-warm-align-01-th01-tonghop.png"
SCREENSHOT_C7620 = OUT_DIR / "anh-warm-align-02-c7620-lsu.png"

QUESTION_TH01 = (
    "Theo tài liệu Tab led cam ung.pdf (Touch Panel Specification), điều kiện "
    "nhiệt độ và độ ẩm tiêu chuẩn để bảo quản (Storage) touch panel là bao nhiêu?"
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


def kill_all_workers_and_servers():
    log("Dọn dẹp sạch toàn bộ tiến trình streamlit và bge_subprocess_worker cũ...")
    cmd = (
        'Get-CimInstance Win32_Process | Where-Object { '
        '$_.CommandLine -like "*streamlit*" -or $_.CommandLine -like "*bge_subprocess_worker*" '
        '} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }'
    )
    try:
        subprocess.run(["powershell", "-Command", cmd], capture_output=True, timeout=15)
    except Exception as e:
        log(f"Lỗi khi dọn dẹp tiến trình: {e}")
    try:
        for pid_f in Path(r"D:\AIOS_workspace_chat_rag_v2_production").glob("**/logs/*.pid"):
            try:
                pid_f.unlink()
            except Exception:
                pass
    except Exception:
        pass
    time.sleep(2.0)


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


def warm_up_collection_aligned(collection_id: str, probe_query: str) -> dict:
    cfg = WorkspaceChatRagV2CanaryConfig.from_env()
    p_cfg = _pipeline_config(cfg, cfg.requested_profile, read_only=True, collection_id=collection_id)
    p_name = pipe_name_for_config(p_cfg)
    log(f"[WARM] Kích hoạt làm ấm persistent worker cho khối '{collection_id}' (pipe={p_name})...")
    ensure_workspace_chat_worker_warming(blocking=False, pipe_config=p_cfg)

    t_start = time.time()
    while time.time() - t_start < 300:
        res = probe_workspace_chat_worker(question=probe_query, domain=collection_id)
        c_cnt = int(res.get("chunks", 0))
        pipe_ok = _pipe_instance_available(p_name)
        ready_ok = bool(_SUBPROCESS_CLIENT.is_ready(p_cfg))
        if res.get("ready") and c_cnt > 0 and pipe_ok and ready_ok:
            log(f"[WARM] Worker '{collection_id}' đã SẴN SÀNG từ góc nhìn đường lượt: {c_cnt} chunks, pipe_ok={pipe_ok}, is_ready={ready_ok} (ok=True) sau {time.time()-t_start:.2f}s!")
            return {
                "collection": collection_id,
                "pipe_name": p_name,
                "pipe_ok": pipe_ok,
                "is_ready": ready_ok,
                "chunks": c_cnt,
                "elapsed_s": round(time.time() - t_start, 2),
            }
        log(f"[WARM] Đang nạp worker '{collection_id}'... chunks={c_cnt}, pipe_ok={pipe_ok}, is_ready={ready_ok}, chờ 5s...")
        time.sleep(5.0)
    return {"collection": collection_id, "pipe_name": p_name, "pipe_ok": False, "is_ready": False, "chunks": 0, "elapsed_s": 300.0}


def execute_turn(
    page,
    conv_id: str,
    block_id: str,
    question: str,
    screenshot_file: Path,
) -> dict:
    nav_url = f"{URL}/?nb={NOTEBOOK_ID}&conv={conv_id}&block={block_id}"
    log(f"[UI] Điều hướng: {nav_url}")
    page.goto(nav_url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(4000)

    # Chờ ô nhập câu hỏi xuất hiện
    page.wait_for_selector('textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"]', timeout=30000)
    textarea = page.locator('textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"]').first
    textarea.wait_for(state="visible", timeout=30000)
    textarea.click()
    textarea.fill(question)
    page.wait_for_timeout(1000)

    log(f"[UI] Gửi câu hỏi vào khối '{block_id}'...")
    textarea.press("Control+Enter")

    # Đợi user message lưu DB
    user_saved = False
    for attempt in range(15):
        time.sleep(1.0)
        msgs = load_messages(conv_id)
        if any(m.role == "user" for m in msgs):
            log(f"[DB] Tin nhắn user đã lưu DB (sau {attempt+1}s)")
            user_saved = True
            break
        if attempt in (2, 5):
            log(f"[DB] Chưa thấy tin nhắn sau {attempt+1}s, thử nhấn Control+Enter lại...")
            textarea.click()
            textarea.press("Control+Enter")

    if not user_saved:
        log("[WARN] Chưa thấy tin nhắn user trong DB sau 15s, tiếp tục chờ...")

    # Đợi assistant phản hồi
    log(f"[UI] Đang chờ assistant phản hồi cho '{conv_id}'...")
    t0 = time.time()
    completed = False
    ans_text = ""
    while time.time() - t0 < 300:
        msgs = load_messages(conv_id)
        if len(msgs) >= 2 and msgs[-1].role == "assistant" and msgs[-1].content:
            completed = True
            ans_text = msgs[-1].content
            break
        page.wait_for_timeout(1000)

    dur = time.time() - t0
    log(f"[RESULT] Lượt '{conv_id}' hoàn tất sau {dur:.2f}s (completed={completed})")

    # Chờ giao diện render hoàn tất trước khi chụp ảnh
    page.wait_for_timeout(3000)

    # Chụp ảnh bằng chứng toàn trang
    try:
        page.screenshot(path=str(screenshot_file), full_page=True, timeout=15000)
        log(f"[SCREENSHOT] Đã chụp ảnh bằng chứng: {screenshot_file.name}")
    except Exception as e:
        log(f"[WARN] Không thể chụp ảnh: {e}")

    return {
        "conv_id": conv_id,
        "block_id": block_id,
        "completed": completed,
        "duration_s": round(dur, 2),
        "ans_length": len(ans_text),
    }


def parse_turn_markers(log_lines: list[str], conv_id: str, expected_collection: str) -> dict:
    markers = {
        "conv_id": conv_id,
        "warm_loop_step": None,
        "elapsed_wait_s": None,
        "warm_reason": None,
        "retrieval_micro": None,
        "first_token": None,
        "complete": None,
        "ok": False,
        "persist_timeout": False,
    }

    turn_started = False
    for l in log_lines:
        if f"[STREAMING_QA_START] conv={conv_id}" in l:
            turn_started = True

        if turn_started:
            if "bge_worker_persist_timeout" in l:
                markers["persist_timeout"] = True

            if "[WORKER_WARM_LOOP_STEP]" in l:
                markers["warm_loop_step"] = l.strip()
                # Parse elapsed_wait_s
                m_wait = re.search(r"elapsed_wait_s=([0-9\.]+)", l)
                if m_wait:
                    markers["elapsed_wait_s"] = float(m_wait.group(1))
                m_reason = re.search(r"reason=([a-zA-Z0-9_]+)", l)
                if m_reason:
                    markers["warm_reason"] = m_reason.group(1)

            if "[RETRIEVAL_MICRO_TIMING]" in l and f"collection={expected_collection}" in l:
                markers["retrieval_micro"] = l.strip()

            if f"[STREAMING_QA_FIRST_TOKEN] conv={conv_id}" in l:
                markers["first_token"] = l.strip()

            if f"[STREAMING_QA_COMPLETE] conv={conv_id}" in l:
                markers["complete"] = l.strip()
                if "ok=True" in l:
                    markers["ok"] = True
                break

    return markers


def main():
    if SESSION_LOG_FILE.exists():
        try:
            SESSION_LOG_FILE.unlink()
        except Exception:
            pass

    log("=" * 80)
    log("PHIÊN NGHIỆM THU SỐNG: DESKTOP-SPEED-WARM-ALIGNMENT-FIX-HOME")
    log("=" * 80)

    # 1. Dọn dẹp sạch tiến trình cũ
    kill_all_workers_and_servers()

    # 2. Khởi động Streamlit server
    log(f"\n[1] Khởi động Streamlit server trên cổng {PORT} với BB-CONFIG-PARITY-01...")
    server_proc = start_server(PORT)
    if not wait_for_server(PORT, timeout=90):
        log(f"[ERROR] Không thể kết nối tới server tại {URL}")
        kill_server(server_proc)
        sys.exit(1)
    log(f"[SERVER] Server Streamlit đã sẵn sàng tại {URL} (PID={server_proc.pid})")
    time.sleep(2.0)

    try:
        # 3. Chạy luồng làm ấm khối tong_hop và lsu
        log("\n[2] Thực hiện chuỗi làm ấm persistent worker cho 2 khối 'tong_hop' và 'lsu'...")
        warm_res_th = warm_up_collection_aligned("tong_hop", "touch panel specification")
        assert warm_res_th["is_ready"] is True, "Worker tong_hop phải sẵn sàng từ góc nhìn đường lượt!"
        assert warm_res_th["pipe_ok"] is True, "Named pipe tong_hop phải tồn tại trên OS!"
        assert warm_res_th["chunks"] > 0, "Worker tong_hop phải trả về >0 chunks!"

        warm_res_lsu = warm_up_collection_aligned("lsu", "lsu beam")
        assert warm_res_lsu["is_ready"] is True, "Worker lsu phải sẵn sàng từ góc nhìn đường lượt!"
        assert warm_res_lsu["pipe_ok"] is True, "Named pipe lsu phải tồn tại trên OS!"
        assert warm_res_lsu["chunks"] > 0, "Worker lsu phải trả về >0 chunks!"

        # Khởi chạy Playwright
        log("\n[3] Khởi chạy Playwright để bắn lượt hỏi thực tế trên UI...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1600, "height": 1200})
            page = context.new_page()

            # LƯỢT 1: TH01 trên khối tong_hop
            conv_th01 = f"CONV-WARM-ALIGN-TH01-{uuid.uuid4().hex[:6].upper()}"
            save_conversation(WorkspaceConversation(
                id=conv_th01,
                notebook_id=NOTEBOOK_ID,
                title="Warm Alignment Live Verify TH01 (tong_hop)",
                ai_mode="grounded",
            ))
            log(f"\n--- BẮT ĐẦU LƯỢT 1: TH01 trên 'tong_hop' (conv={conv_th01}) ---")
            turn1_res = execute_turn(page, conv_th01, "tong_hop", QUESTION_TH01, SCREENSHOT_TH01)

            # LƯỢT 2: C7620 trên khối lsu
            conv_c7620 = f"CONV-WARM-ALIGN-LSU-{uuid.uuid4().hex[:6].upper()}"
            save_conversation(WorkspaceConversation(
                id=conv_c7620,
                notebook_id=NOTEBOOK_ID,
                title="Warm Alignment Live Verify C7620 (lsu)",
                ai_mode="grounded",
            ))
            log(f"\n--- BẮT ĐẦU LƯỢT 2: C7620 trên 'lsu' (conv={conv_c7620}) ---")
            turn2_res = execute_turn(page, conv_c7620, "lsu", QUESTION_C7620, SCREENSHOT_C7620)

            browser.close()

        # 4. Đọc server log và kiểm tra các tiêu chí nghiệm thu
        log("\n[4] Thu thập và kiểm định toàn bộ log server...")
        time.sleep(2.0)
        with open(SERVER_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            lines = [l.strip() for l in f if l.strip()]

        markers_th01 = parse_turn_markers(lines, conv_th01, "tong_hop")
        markers_c7620 = parse_turn_markers(lines, conv_c7620, "lsu")

        log("\n--- BÁO CÁO KẾT QUẢ KIỂM ĐỊNH LƯỢT 1 (TH01 - tong_hop) ---")
        log(f"Conv ID: {conv_th01}")
        log(f"WORKER_WARM_LOOP_STEP: {markers_th01['warm_loop_step']}")
        log(f"elapsed_wait_s: {markers_th01['elapsed_wait_s']}")
        log(f"RETRIEVAL_MICRO_TIMING: {markers_th01['retrieval_micro']}")
        log(f"FIRST_TOKEN: {markers_th01['first_token']}")
        log(f"COMPLETE: {markers_th01['complete']}")
        log(f"ok=True: {markers_th01['ok']}")
        log(f"persist_timeout: {markers_th01['persist_timeout']}")

        log("\n--- BÁO CÁO KẾT QUẢ KIỂM ĐỊNH LƯỢT 2 (C7620 - lsu) ---")
        log(f"Conv ID: {conv_c7620}")
        log(f"WORKER_WARM_LOOP_STEP: {markers_c7620['warm_loop_step']}")
        log(f"elapsed_wait_s: {markers_c7620['elapsed_wait_s']}")
        log(f"RETRIEVAL_MICRO_TIMING: {markers_c7620['retrieval_micro']}")
        log(f"FIRST_TOKEN: {markers_c7620['first_token']}")
        log(f"COMPLETE: {markers_c7620['complete']}")
        log(f"ok=True: {markers_c7620['ok']}")
        log(f"persist_timeout: {markers_c7620['persist_timeout']}")

        # Đánh giá tiêu chí
        th01_pass = (
            markers_th01["ok"] is True
            and markers_th01["retrieval_micro"] is not None
            and not markers_th01["persist_timeout"]
            and (markers_th01["elapsed_wait_s"] is None or markers_th01["elapsed_wait_s"] <= 10.0)
        )
        c7620_pass = (
            markers_c7620["ok"] is True
            and markers_c7620["retrieval_micro"] is not None
            and not markers_c7620["persist_timeout"]
            and (markers_c7620["elapsed_wait_s"] is None or markers_c7620["elapsed_wait_s"] <= 10.0)
        )

        log("\n" + "=" * 80)
        log(f"TỔNG KẾT TIÊU CHÍ VÉ DESKTOP-SPEED-WARM-ALIGNMENT-FIX-HOME:")
        log(f"1. Lượt TH01 (tong_hop): {'ĐẠT' if th01_pass else 'KHÔNG ĐẠT'}")
        log(f"2. Lượt C7620 (lsu):      {'ĐẠT' if c7620_pass else 'KHÔNG ĐẠT'}")
        log("=" * 80)

        if not (th01_pass and c7620_pass):
            log("[FAIL] Phiên nghiệm thu không đạt toàn bộ tiêu chí!")
            sys.exit(1)
        else:
            log("[SUCCESS] CẢ HAI LƯỢT ĐỀU ĐẠT TOÀN DIỆN!")

    finally:
        kill_server(server_proc)
        kill_all_workers_and_servers()


if __name__ == "__main__":
    main()
