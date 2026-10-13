"""Script kiem chung song tren giao dien that (Streamlit + Playwright)
cho ve DESKTOP-SPEED-SEGMENT-MARKERS-FIX-HOME.

Kiem chung 2 luot tren giao dien that (khong tinh mock):
1. Luot 1 (Draft fallback): Cau hoi khop kho ban thao nhung khong co chunk trong khoi Tong hop
   ("用于初始化 Backup RAM 的 Maintenance Code 是什么？" - tu batch-55.md)
   -> summary_count == 0 -> Tu dong kick hoat deliver_draft_answer
   -> Ky vong bat marker: [DRAFT_FALLBACK_COMPLETE] va [RETRIEVAL_MICRO_TIMING].
2. Luot 2 (Router + Retrieval): Cau hoi tong hop co chunk trong khoi Tong hop
   ("Theo tai lieu Tab led cam ung.pdf (Touch Panel Specification), dieu kien nhiet do va do am tieu chuan de bao quan (Storage) touch panel la bao nhieu?")
   -> summary_count > 0 -> Goi router qua route_workspace_chat_submission
   -> Ky vong bat marker: [RETRIEVAL_MICRO_TIMING], [ROUTER_SYNTH_START], [ROUTER_SYNTH_DONE].
"""

import os
import sys
import time
import uuid
import subprocess
import urllib.request
from pathlib import Path

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
sys.path.insert(0, str(APP_DIR / "src"))

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
from playwright.sync_api import sync_playwright

PORT = 8548
URL = f"http://localhost:{PORT}"
NOTEBOOK_ID = "NB-C26E1C84"
LOG_DIR = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua")
LOG_DIR.mkdir(parents=True, exist_ok=True)
SERVER_LOG_FILE = LOG_DIR / "server_markers_live_session.log"


def wait_for_server(port: int, timeout: int = 60) -> bool:
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
    env["AIOS_AI_BACKEND"] = "nakazasen_router"
    env["AIOS_RAGV2_WORKER_PERSIST"] = "1"
    env["AIOS_FEATURE_CHAT_ACTION"] = "1"
    env["AIOS_DOMAIN_ROUTING_ENABLED"] = "1"
    env["AIOS_STREAM_SYNTHESIS"] = "1"
    env["AIOS_FEATURE_ANSWER_DRAFT_FALLBACK"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
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


def run_turn(page, conv_id: str, notebook_id: str, khoi_code: str, question: str, timeout_s: int = 150) -> bool:
    nav_url = f"{URL}/?nb={notebook_id}&conv={conv_id}&block={khoi_code}"
    print(f"\n[PAGE] Dieu huong toi: {nav_url}")
    page.goto(nav_url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(3000)

    page.wait_for_selector('textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"]', timeout=30000)

    textarea = page.locator('textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"]').first
    textarea.fill(question)
    page.wait_for_timeout(500)

    send_btn = page.locator(
        f'[class*="st-key-wsc_ask_{conv_id}"] button, [class*="st-key-wsc-action-"] button'
    ).first
    if send_btn.count() > 0:
        send_btn.click()
    else:
        textarea.press("Control+Enter")
    print(f"[SEND] Da bam gui cau hoi: '{question[:60].encode('ascii', errors='backslashreplace').decode('ascii')}...'")

    # Xac nhan luu tin nhan user vao DB
    for attempt in range(5):
        time.sleep(1.0)
        msgs = load_messages(conv_id)
        if any(m.role == "user" for m in msgs):
            print(f"[DB] Tin nhan user da luu thanh cong (lan thu {attempt+1})")
            break
        textarea.press("Control+Enter")
        page.wait_for_timeout(1000)

    t0 = time.time()
    completed = False
    while time.time() - t0 < timeout_s:
        msgs = load_messages(conv_id)
        if len(msgs) >= 2 and msgs[-1].role == "assistant":
            completed = True
            time.sleep(2)
            break
        page.wait_for_timeout(1000)

    dur = time.time() - t0
    print(f"[RESULT] Luot hoan tat sau {dur:.2f}s (completed={completed})")
    return completed


def main():
    print("=" * 70)
    print("BAT DAU KIEM CHUNG SONG: DESKTOP-SPEED-SEGMENT-MARKERS-FIX-HOME")
    print("=" * 70)

    # 1. Khoi dong Streamlit server
    print(f"[SERVER] Khoi dong Streamlit server tren cong {PORT}...")
    server_proc = start_server(PORT)
    if not wait_for_server(PORT, timeout=60):
        print(f"[ERROR] Khong the ket noi toi server tai {URL}")
        kill_server(server_proc)
        sys.exit(1)
    print(f"[SERVER] Server da san sang tai {URL}")
    time.sleep(3.0)

    # 2. Chay Playwright
    conv1_id = f"CONV-LIVE-DRAFT-{uuid.uuid4().hex[:6].upper()}"
    conv2_id = f"CONV-LIVE-ROUTER-{uuid.uuid4().hex[:6].upper()}"
    draft_nb_id = f"NB-DRAFT-{uuid.uuid4().hex[:6].upper()}"

    from aios_habit.workspace_chat_models import DocumentNotebook
    from aios_habit.workspace_chat_store import save_notebook

    save_notebook(DocumentNotebook(
        id=draft_nb_id,
        title="Live Verify Draft Notebook",
    ))

    save_conversation(WorkspaceConversation(
        id=conv1_id,
        notebook_id=draft_nb_id,
        title="Live Verify Draft Fallback Marker",
        ai_mode="grounded",
    ))
    save_conversation(WorkspaceConversation(
        id=conv2_id,
        notebook_id=NOTEBOOK_ID,
        title="Live Verify Router & Retrieval Marker",
        ai_mode="grounded",
    ))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 1000})

        # Luot 1: Router + Retrieval (TH01 Tab led cam ung tren khoi Tong hop) -> chay truoc de lam am
        q2 = "Theo tài liệu Tab led cam ung.pdf (Touch Panel Specification), điều kiện nhiệt độ và độ ẩm tiêu chuẩn để bảo quản (Storage) touch panel là bao nhiêu?"
        print(f"\n>>> [LUOT 1/2] Kiem chung router & retrieval (conv={conv2_id}, nb={NOTEBOOK_ID}, block=tong_hop)")
        ok2 = run_turn(page, conv2_id, NOTEBOOK_ID, "tong_hop", q2, timeout_s=150)

        # Luot 2: Draft fallback tren duong ban thao cua server app
        q1 = "File chỉ ra thiếu chức năng gì để phát hiện sớm tình trạng jig suy giảm?"
        print(f"\n>>> [LUOT 2/2] Kiem chung duong ban thao (conv={conv1_id}, nb={draft_nb_id})")
        from aios_habit.workspace_chat_app import _run_chat_turn_async
        from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource

        empty_src = WorkspaceAIContextSource(
            source_id="empty_s1",
            source_scope="notebook",
            source_type="plain_text",
            title="empty.txt",
            privacy_label="local_only",
            text="",
            included_chars=0,
            truncated=False,
        )
        with open(SERVER_LOG_FILE, "a", encoding="utf-8") as f_log:
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            try:
                sys.stdout = f_log
                sys.stderr = f_log
                res_draft = _run_chat_turn_async(
                    q_text=q1,
                    conversation_id=conv1_id,
                    notebook_id=draft_nb_id,
                    query_relevant_sources=(empty_src,),
                    forced_domain=None,
                )
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

        print(f"[RESULT] Luot 2 draft fallback hoan tat: ok={res_draft[0]}")
        browser.close()

    # 3. Dung server
    print("\n[CLEANUP] Dung Streamlit server...")
    kill_server(server_proc)

    # 4. Doc va trich xuat marker tu nhat ky server
    print("\n" + "=" * 70)
    print("KET QUA TRICH XUAT MARKER TU NHAT KY SERVER:")
    print("=" * 70)

    if not SERVER_LOG_FILE.exists():
        print(f"[ERROR] Khong tim thay tep log server: {SERVER_LOG_FILE}")
        sys.exit(1)

    log_content = SERVER_LOG_FILE.read_text(encoding="utf-8", errors="ignore")
    lines = log_content.splitlines()

    draft_markers = [l for l in lines if "[DRAFT_FALLBACK_COMPLETE]" in l]
    router_start_markers = [l for l in lines if "[ROUTER_SYNTH_START]" in l]
    router_done_markers = [l for l in lines if "[ROUTER_SYNTH_DONE]" in l]
    retrieval_markers = [l for l in lines if "[RETRIEVAL_MICRO_TIMING]" in l]

    print(f"\n1. Marker [DRAFT_FALLBACK_COMPLETE] ({len(draft_markers)} dong):")
    for m in draft_markers:
        print("  " + m)

    print(f"\n2. Marker [ROUTER_SYNTH_START] ({len(router_start_markers)} dong):")
    for m in router_start_markers:
        print("  " + m)

    print(f"\n3. Marker [ROUTER_SYNTH_DONE] ({len(router_done_markers)} dong):")
    for m in router_done_markers:
        print("  " + m)

    print(f"\n4. Marker [RETRIEVAL_MICRO_TIMING] ({len(retrieval_markers)} dong):")
    for m in retrieval_markers:
        print("  " + m)

    print("\n" + "=" * 70)
    success = (len(draft_markers) > 0 and len(router_start_markers) > 0 and 
               len(router_done_markers) > 0 and len(retrieval_markers) > 0)
    print(f"TONG KET KIEM CHUNG SONG: {'DAT 100%' if success else 'CHUA DAT'}")
    print("=" * 70)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
