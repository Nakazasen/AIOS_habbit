"""Script đo thực nghiệm kiểm chứng đồng bộ cụm khử trùng hiển thị (DEDUP) trên PC0575.
Vé: DESKTOP-PC0575-SYNC-DEDUP
Máy thực thi: KDTVN-PC0575 (Intel Core i5-8265U @ 1.60GHz, 16.0 GB RAM, Windows 11 Pro 64-bit, CPU-only)

Mục tiêu kiểm chứng:
1. Một đáp án AI chỉ còn đúng 1 dòng miễn trừ ('Đây là câu trả lời do AI tạo...').
2. Một đáp án có biểu đồ JIG chỉ còn đúng 1 biểu đồ (không lặp lại data URI base64).
3. Bất biến đáp án dự phòng cục bộ (local_grounded_fallback) không dòng miễn trừ giữ nguyên (0 dòng).
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any
import urllib.request
import uuid

import psutil

# Cấu hình môi trường chuẩn BB-CONFIG-PARITY-01 cho PC0575 (CPU-only)
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
os.environ["AIOS_AI_BACKEND"] = "gemini_web"
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

from aios_habit.workspace_chat_models import DocumentNotebook, WorkspaceConversation, ChatMessage
from aios_habit.workspace_chat_store import save_notebook, save_conversation, save_message, load_messages
from playwright.sync_api import sync_playwright

PORT = 8501
URL = f"http://localhost:{PORT}"
SIDECAR_PORT = 8585

OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua")
OUT_DIR.mkdir(parents=True, exist_ok=True)
DOCS_OUT_DIR = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
DOCS_OUT_DIR.mkdir(parents=True, exist_ok=True)

SERVER_LOG_FILE = OUT_DIR / "server_desktop_pc0575_sync_dedup.log"
SESSION_LOG_FILE = OUT_DIR / "session_desktop_pc0575_sync_dedup.log"
JSON_RESULT_FILE = OUT_DIR / "ket-qua-do-desktop-pc0575-sync-dedup.json"

SCREENSHOT_READY = OUT_DIR / "anh-pc0575-dedup-00-app-ready.png"
SCREENSHOT_AI = OUT_DIR / "anh-pc0575-dedup-01-ai-disclaimer.png"
SCREENSHOT_JIG = OUT_DIR / "anh-pc0575-dedup-02-jig-chart.png"
SCREENSHOT_LOCAL = OUT_DIR / "anh-pc0575-dedup-03-local-fallback.png"


def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(SESSION_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(64 * 1024):
            h.update(chunk)
    return h.hexdigest().upper()


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
    log("Dọn dẹp sạch toàn bộ tiến trình streamlit, sidecar và bge_subprocess_worker cũ...")
    my_pid = os.getpid()
    ps_cmd = (
        f"$procs = Get-CimInstance Win32_Process | Where-Object {{ "
        f"($_.CommandLine -like '*bge_subprocess_worker*' -or "
        f"$_.CommandLine -like '*workspace_chat_app.py*' -or "
        f"$_.CommandLine -like '*antigravity_sidecar_daemon*') -and $_.ProcessId -ne {my_pid} "
        f"}}; "
        f"foreach ($p in $procs) {{ Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }}"
    )
    subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
    time.sleep(2.0)
    log("Đã dọn dẹp sạch các tiến trình cũ.")


def ensure_sidecar_running() -> subprocess.Popen | None:
    health_url = f"http://127.0.0.1:{SIDECAR_PORT}/health"
    try:
        req = urllib.request.Request(health_url)
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("status") == "direct_ready":
                    log(f"[SIDECAR] Đã có sidecar đang chạy ở port {SIDECAR_PORT} (direct_ready).")
                    return None
    except Exception:
        pass

    log(f"[SIDECAR] Khởi động Antigravity sidecar daemon tại port {SIDECAR_PORT} (mode=direct)...")
    sidecar_script = APP_DIR / "scripts" / "antigravity_sidecar_daemon.py"
    cmd = [
        str(PYTHON_EXE),
        str(sidecar_script),
        "--port",
        str(SIDECAR_PORT),
        "--mode",
        "direct",
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=APP_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            req = urllib.request.Request(health_url)
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("status") == "direct_ready":
                        log(f"[SIDECAR] Sidecar đã sẵn sàng tại port {SIDECAR_PORT}!")
                        return proc
        except Exception:
            pass
        time.sleep(0.4)
    log("[SIDECAR_WARN] Không nhận được phản hồi 200 từ sidecar sau 15s!")
    return proc


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
    log(f"[STARTUP] Chạy Streamlit: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        cwd=APP_DIR,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        env=env,
    )
    return proc


def kill_proc(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def parse_conv_markers(server_log: Path, conv_id: str) -> dict[str, Any]:
    res: dict[str, Any] = {
        "qa_start_line": "",
        "complete_line": "",
        "ok": False,
    }
    if not server_log.exists():
        return res
    try:
        with open(server_log, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return res

    for ln in lines:
        if f"[STREAMING_QA_START] conv={conv_id}" in ln:
            res["qa_start_line"] = ln.strip()
        elif f"[STREAMING_QA_COMPLETE] conv={conv_id}" in ln:
            res["complete_line"] = ln.strip()
            if "ok=True" in ln:
                res["ok"] = True
    return res


def submit_question_and_wait(
    page: Any,
    conv_id: str,
    question: str,
    *,
    done_screenshot: Path | None = None,
    timeout_s: float = 300.0,
    is_jig_chart: bool = False,
) -> dict[str, Any]:
    composer_selector = 'textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"], textarea[placeholder*="Nhập câu hỏi"], [class*="st-key-wsc_question_input"] textarea'
    log(f"[WAIT_COMPOSER] Chờ composer cho conv={conv_id}...")
    page.wait_for_selector(composer_selector, timeout=60000)
    textarea = page.locator(composer_selector).first
    textarea.wait_for(state="visible", timeout=20000)
    textarea.click()
    textarea.fill(question)
    page.wait_for_timeout(300)

    t_fire = datetime.now()
    log(f"[SUBMIT] conv={conv_id}: {question}")

    send_btn = page.locator(
        f'[class*="st-key-wsc_ask_{conv_id}"] button, '
        f'[class*="st-key-wsc-action-{conv_id}"] button, '
        f'[class*="st-key-wsc-action-"] button'
    ).first
    if send_btn.count() > 0:
        send_btn.click(force=True)
    else:
        textarea.press("Control+Enter")

    t_watch = time.time()
    while time.time() - t_watch < timeout_s:
        if is_jig_chart:
            msgs = load_messages(conv_id)
            ast_msgs = [m for m in msgs if m.role == "assistant"]
            if ast_msgs and ("biểu đồ" in ast_msgs[-1].content.lower() or "data:image/png;base64" in ast_msgs[-1].content):
                log(f"[JIG_DONE] Đã nhận câu trả lời biểu đồ JIG cho conv={conv_id}")
                break
        else:
            markers = parse_conv_markers(SERVER_LOG_FILE, conv_id)
            if markers["complete_line"]:
                log(f"[QA_DONE] {markers['complete_line']}")
                break
        page.wait_for_timeout(500)

    # Chờ giao diện Streamlit hoàn tất rerun và render xong toàn bộ components
    page.wait_for_timeout(4000)
    if done_screenshot is not None:
        try:
            page.screenshot(path=str(done_screenshot))
            log(f"[SCREENSHOT] Đã chụp ảnh hoàn tất: {done_screenshot}")
        except Exception as e:
            log(f"[SCREENSHOT_WARN] {e}")

    msgs = load_messages(conv_id)
    ast_msgs = [m for m in msgs if m.role == "assistant"]
    ans_text = ast_msgs[-1].content if ast_msgs else ""

    return {
        "conv_id": conv_id,
        "question": question,
        "answer_text": ans_text,
        "answer_length": len(ans_text),
    }


def main() -> None:
    if SESSION_LOG_FILE.exists():
        SESSION_LOG_FILE.unlink()

    log("=" * 80)
    log("BẮT ĐẦU ĐO THỰC NGHIỆM: DESKTOP-PC0575-SYNC-DEDUP")
    log("=" * 80)
    git_head = get_git_head()
    log(f"[GIT] Commit HEAD PC0575: {git_head}")

    nb_id = "NB-PC0575-DEDUP"
    save_notebook(DocumentNotebook(
        id=nb_id,
        title="Sổ Kiểm tra Đồng bộ Khử trùng (DEDUP)",
        description="Sổ kiểm chứng khử trùng disclaimer và khử trùng biểu đồ JIG trên PC0575",
        collection_id="lsu",
    ))

    cid_ai = f"CONV-PC0575-DEDUP-AI-{uuid.uuid4().hex[:6].upper()}"
    save_conversation(WorkspaceConversation(
        id=cid_ai,
        notebook_id=nb_id,
        title="Kiểm tra Khử trùng Disclaimer AI",
        ai_mode="grounded",
    ))

    cid_jig = f"CONV-PC0575-DEDUP-JIG-{uuid.uuid4().hex[:6].upper()}"
    save_conversation(WorkspaceConversation(
        id=cid_jig,
        notebook_id=nb_id,
        title="Kiểm tra Khử trùng Biểu đồ JIG",
        ai_mode="grounded",
    ))

    cid_local = f"CONV-PC0575-DEDUP-LOCAL-{uuid.uuid4().hex[:6].upper()}"
    save_conversation(WorkspaceConversation(
        id=cid_local,
        notebook_id=nb_id,
        title="Kiểm tra Bất biến Local Fallback (0 disclaimer)",
        ai_mode="grounded",
    ))
    save_message(ChatMessage(
        id=f"MSG-U-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=cid_local,
        role="user",
        content="Tra cứu tài liệu dự phòng nội bộ",
    ))
    save_message(ChatMessage(
        id=f"MSG-A-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=cid_local,
        role="assistant",
        content="Đây là bản tổng hợp cục bộ từ trích đoạn tài liệu kỹ thuật trên máy, không qua mô hình AI.",
    ))

    kill_all_workers_and_servers()
    sidecar_proc = ensure_sidecar_running()

    log(f"[STARTUP] Khởi động Streamlit server trên cổng {PORT}...")
    server_proc = start_server(PORT, SERVER_LOG_FILE)

    if not wait_for_server(PORT, timeout=90):
        log("[ERROR] Streamlit server không phản hồi sau 90s!")
        kill_proc(server_proc)
        kill_proc(sidecar_proc)
        sys.exit(1)

    log("[STARTUP] Server đã sẵn sàng!")

    eval_results: dict[str, Any] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1600, "height": 1000})
        page = context.new_page()

        # Step 0: App ready screenshot
        first_url = f"{URL}/?nb={nb_id}&conv={cid_ai}&block=lsu"
        log(f"[NAV_FIRST] Điều hướng: {first_url}")
        page.goto(first_url, wait_until="domcontentloaded", timeout=60000)
        composer_sel = 'textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"], textarea[placeholder*="Nhập câu hỏi"], [class*="st-key-wsc_question_input"] textarea'
        page.wait_for_selector(composer_sel, timeout=60000)
        page.wait_for_timeout(2000)
        page.screenshot(path=str(SCREENSHOT_READY))
        log(f"[SCREENSHOT] App Ready: {SCREENSHOT_READY}")

        # Chờ worker LSU ấm trước khi gửi lượt đo
        from aios_habit.workspace_chat_rag_v2_adapter import is_workspace_chat_worker_warmed
        log("[WARM_WAIT] Chờ worker khối LSU sẵn sàng trước khi gửi lượt đo...")
        t_w = time.time()
        while time.time() - t_w < 90:
            if is_workspace_chat_worker_warmed(collection_id="lsu"):
                log(f"[WARM_WAIT] Worker LSU đã sẵn sàng sau {(time.time() - t_w):.2f}s!")
                break
            page.wait_for_timeout(500)

        # Step 1: AI answer disclaimer check
        log("\n" + "=" * 60)
        log("KIỂM CHỨNG 1: KHỬ TRÙNG DÒNG MIỄN TRỪ AI (AI DISCLAIMER)")
        log("=" * 60)
        res_ai = submit_question_and_wait(
            page,
            cid_ai,
            "C23とC24ではどのような発生Trendでしたか。",
            done_screenshot=SCREENSHOT_AI,
            timeout_s=300.0,
            is_jig_chart=False,
        )
        page.wait_for_timeout(3000)

        # Đếm số lần xuất hiện dòng disclaimer dưới đáp án AI trong cột chat
        # Bộ đếm định vị chính xác caption trong vùng chat (AI answer header/badge)
        chat_disclaimer_loc = page.locator(
            'div:has-text("Đã trả lời bằng AI") ~ div:has-text("Đây là câu trả lời do AI tạo"), '
            'div:has-text("Đã trả lời bằng AI") + div:has-text("Đây là câu trả lời do AI tạo"), '
            'div[data-testid="stChatMessage"] ~ div :text("Đây là câu trả lời do AI tạo"), '
            'div[data-testid="stCaptionContainer"]:has-text("Đây là câu trả lời do AI tạo")'
        )
        disclaimer_count = chat_disclaimer_loc.count()
        if disclaimer_count == 0:
            # Fallback regex đếm trên toàn bộ các stCaptionContainer hiển thị
            all_captions = page.locator('div[data-testid="stCaptionContainer"]').all_text_contents()
            disclaimer_captions = [c for c in all_captions if "Đây là câu trả lời do AI tạo" in c or "AIによって生成された回答です" in c]
            disclaimer_count = len(disclaimer_captions)

        log(f"[DEDUP_AI] Số dòng miễn trừ AI dưới câu trả lời: {disclaimer_count}")
        ai_dedup_passed = (disclaimer_count == 1)
        log(f"[DEDUP_AI] Kết quả kiểm chứng Disclaimer: {'ĐẠT (chính xác 1 dòng)' if ai_dedup_passed else f'KHÔNG ĐẠT ({disclaimer_count} dòng)'}")

        eval_results["ai_disclaimer"] = {
            "conversation_id": cid_ai,
            "question": "C23とC24ではどのような発生Trendでしたか。",
            "answer_length": res_ai["answer_length"],
            "disclaimer_count": disclaimer_count,
            "expected_count": 1,
            "passed": ai_dedup_passed,
            "screenshot": str(SCREENSHOT_AI),
            "screenshot_sha256": compute_sha256(SCREENSHOT_AI) if SCREENSHOT_AI.exists() else "",
        }

        # Step 2: JIG chart duplicate check
        log("\n" + "=" * 60)
        log("KIỂM CHỨNG 2: KHỬ TRÙNG BIỂU ĐỒ JIG")
        log("=" * 60)
        jig_url = f"{URL}/?nb={nb_id}&conv={cid_jig}&block=lsu"
        page.goto(jig_url, wait_until="domcontentloaded", timeout=60000)
        res_jig = submit_question_and_wait(
            page,
            cid_jig,
            "vẽ biểu đồ bowskew cho JIG-01",
            done_screenshot=SCREENSHOT_JIG,
            timeout_s=90.0,
            is_jig_chart=True,
        )
        page.wait_for_timeout(2000)

        # Đếm số ảnh biểu đồ xuất hiện trong câu trả lời
        ans_jig_text = res_jig.get("answer_text", "")
        text_chart_count = ans_jig_text.count("data:image/png;base64")
        dom_chart_imgs = page.locator('img[src*="data:image/png;base64"], img[alt*="biểu đồ"]').count()

        log(f"[DEDUP_JIG] Số lượng biểu đồ trong text lưu trữ: {text_chart_count}")
        log(f"[DEDUP_JIG] Số thẻ img biểu đồ trên DOM giao diện: {dom_chart_imgs}")
        jig_dedup_passed = (text_chart_count == 1 and dom_chart_imgs == 1)
        log(f"[DEDUP_JIG] Kết quả kiểm chứng Biểu đồ JIG: {'ĐẠT (chính xác 1 biểu đồ)' if jig_dedup_passed else f'KHÔNG ĐẠT (text={text_chart_count}, dom={dom_chart_imgs})'}")

        eval_results["jig_chart"] = {
            "conversation_id": cid_jig,
            "question": "vẽ biểu đồ bowskew cho JIG-01",
            "answer_length": len(ans_jig_text),
            "chart_count_text": text_chart_count,
            "chart_count_dom": dom_chart_imgs,
            "expected_count": 1,
            "passed": jig_dedup_passed,
            "screenshot": str(SCREENSHOT_JIG),
            "screenshot_sha256": compute_sha256(SCREENSHOT_JIG) if SCREENSHOT_JIG.exists() else "",
        }

        # Step 3: Local fallback invariant check
        log("\n" + "=" * 60)
        log("KIỂM CHỨNG 3: BẤT BIẾN LOCAL FALLBACK (0 DISCLAIMER)")
        log("=" * 60)
        local_url = f"{URL}/?nb={nb_id}&conv={cid_local}&block=lsu"
        page.goto(local_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector(composer_sel, timeout=60000)
        page.wait_for_timeout(2000)
        page.screenshot(path=str(SCREENSHOT_LOCAL))
        log(f"[SCREENSHOT] Local Fallback UI: {SCREENSHOT_LOCAL}")

        # Kiểm tra bất biến: trên bubble trả lời của local fallback không có caption disclaimer
        local_chat_captions = page.locator(
            'div[data-testid="stChatMessage"]:has-text("Đây là bản tổng hợp cục bộ") div[data-testid="stCaptionContainer"]'
        ).all_text_contents()
        local_disclaimer_count = sum(1 for c in local_chat_captions if "Đây là câu trả lời do AI tạo" in c)
        log(f"[LOCAL_FALLBACK] Số dòng miễn trừ trong bubble local fallback: {local_disclaimer_count}")

        # Kiểm tra thêm AST invariant trực tiếp từ file source theo FR-030
        app_src = (APP_DIR / "src" / "aios_habit" / "workspace_chat_app.py").read_text(encoding="utf-8")
        loc_idx = app_src.find('badge_data.get("operational_mode") == "local_grounded_fallback"')
        next_br_idx = app_src.find('elif (', loc_idx)
        loc_block = app_src[loc_idx:next_br_idx]
        ast_invariant_passed = ("ai_disclaimer" not in loc_block and "render_ai_answer_header" not in loc_block)
        log(f"[LOCAL_FALLBACK] Kiểm tra AST source invariant: {'ĐẠT (0 disclaimer)' if ast_invariant_passed else 'KHÔNG ĐẠT'}")

        local_passed = (local_disclaimer_count == 0 and ast_invariant_passed)
        log(f"[LOCAL_FALLBACK] Kết quả kiểm chứng Bất biến Local Fallback: {'ĐẠT (0 dòng disclaimer)' if local_passed else 'KHÔNG ĐẠT'}")

        eval_results["local_fallback"] = {
            "conversation_id": cid_local,
            "disclaimer_count": local_disclaimer_count,
            "expected_count": 0,
            "ast_invariant_passed": ast_invariant_passed,
            "passed": local_passed,
            "screenshot": str(SCREENSHOT_LOCAL),
            "screenshot_sha256": compute_sha256(SCREENSHOT_LOCAL) if SCREENSHOT_LOCAL.exists() else "",
        }

        browser.close()

    kill_proc(server_proc)
    kill_proc(sidecar_proc)
    kill_all_workers_and_servers()

    # Lưu kết quả đo JSON
    final_data = {
        "ma_ve": "DESKTOP-PC0575-SYNC-DEDUP",
        "thoi_diem": datetime.now(timezone.utc).isoformat(),
        "git_head": git_head,
        "eval_results": eval_results,
        "all_passed": all(v.get("passed", False) for v in eval_results.values()),
    }

    with open(JSON_RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    with open(DOCS_OUT_DIR / "ket-qua-do-desktop-pc0575-sync-dedup.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    # Đồng bộ ảnh sang docs/phieu-viec/ket-qua
    for shot in (SCREENSHOT_READY, SCREENSHOT_AI, SCREENSHOT_JIG, SCREENSHOT_LOCAL):
        if shot.exists():
            target = DOCS_OUT_DIR / shot.name
            target.write_bytes(shot.read_bytes())

    log("=" * 80)
    log(f"HOÀN TẤT ĐO THỰC NGHIỆM! Tổng kết: {'TẤT CẢ ĐẠT' if final_data['all_passed'] else 'CÓ MỤC CHƯA ĐẠT'}")
    log(f"Kết quả JSON: {JSON_RESULT_FILE}")
    log("=" * 80)


if __name__ == "__main__":
    main()
