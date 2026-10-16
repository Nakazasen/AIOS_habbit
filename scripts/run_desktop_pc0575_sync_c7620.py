"""Script đo thực nghiệm kiểm chứng đồng bộ cụm C7620-CJK trên PC0575.
Vé: DESKTOP-PC0575-SYNC-C7620
Máy thực thi: KDTVN-PC0575 (Intel Core i5-8265U @ 1.60GHz, 16.0 GB RAM, Windows 11 Pro 64-bit, CPU-only)
Commit HEAD: tip mới nhất trên nhánh phieu-viec/rag-fix1 (chứa a6e8e681)

Mục tiêu kiểm chứng trên app thật:
1. Q0700: C23とC24ではどのような発生Trendでしたか。
   - Yêu cầu: đủ 4 dữ kiện (Dây chuyền C23/24, Ngày 19/2, Tỷ lệ NG cùng xu hướng tăng đồng thời, Màu phát sinh Magenta).
2. Q0703: B距離が長くなる想定状態は何ですか。
   - Yêu cầu: đủ 3 trạng thái lệch chiều cao quang đường (M lệch +, Bk lệch -, cả hai cùng lệch) và khoảng cách B dài làm tăng nguy cơ lỗi C7620 màu M.
3. Q0708: 光路高さ1.15 mmを超えると必ずCamera読取不能になりますか。
   - Yêu cầu: phân biệt đúng 1.15 mm là ngưỡng có nguy cơ phát sinh C7620, 1.24 mm mới là ngưỡng Camera vượt ngoài tầm đọc, kết luận phủ định.
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
import threading
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

from aios_habit.workspace_chat_models import DocumentNotebook, WorkspaceConversation
from aios_habit.workspace_chat_store import save_notebook, save_conversation, load_messages
from playwright.sync_api import sync_playwright

PORT = 8501
URL = f"http://localhost:{PORT}"
SIDECAR_PORT = 8585

OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SERVER_LOG_FILE = OUT_DIR / "server_desktop_pc0575_sync_c7620.log"
SESSION_LOG_FILE = OUT_DIR / "session_desktop_pc0575_sync_c7620.log"
JSON_RESULT_FILE = OUT_DIR / "ket-qua-do-desktop-pc0575-sync-c7620.json"

SCREENSHOT_READY = OUT_DIR / "anh-pc0575-c7620-00-app-ready.png"
SCREENSHOT_Q0700 = OUT_DIR / "anh-pc0575-c7620-01-q0700.png"
SCREENSHOT_Q0703 = OUT_DIR / "anh-pc0575-c7620-02-q0703.png"
SCREENSHOT_Q0708 = OUT_DIR / "anh-pc0575-c7620-03-q0708.png"

TARGET_QUESTIONS = [
    {
        "id": "Q0700",
        "question": "C23とC24ではどのような発生Trendでしたか。",
        "ref": "2月19日にC23/C24でNG率が同じTrendで同時に上昇し、発生色はMagentaです。出典ファイル：Sirius 2 _ C7620_報告版 4.pptx.",
        "screenshot": SCREENSHOT_Q0700,
        "criteria": [
            ("C23/24 hoặc C23 và C24", [r"C23/24", r"C23/C24", r"C23", r"C24"]),
            ("Ngày 19/2 (2月19日)", [r"19/2", r"19 tháng 2", r"２月１９日", r"2月19日"]),
            ("NG cùng xu hướng / đồng thời tăng", [r"cùng xu hướng", r"đồng thời tăng", r"同じ傾向", r"同時に上昇", r"Trend"]),
            ("Màu Magenta (発生色はMagenta)", [r"Magenta", r"発生色"]),
        ],
    },
    {
        "id": "Q0703",
        "question": "B距離が長くなる想定状態は何ですか。",
        "ref": "①Mの光路高さが通常よりプラス側へずれる、②Bkの光路高さがマイナス側へずれる、③その両方が同時にずれる、という3状態が示されています。B距離が長いほどC7620 M色Errorが出やすいとしています。出典ファイル：Sirius 2 _ C7620_報告版 4.pptx.",
        "screenshot": SCREENSHOT_Q0703,
        "criteria": [
            ("M lệch + (phía cộng/dương)", [r"M.*(cộng|\+|プラス|dương)", r"quang.*M.*(cộng|\+|プラス|dương)"]),
            ("Bk lệch - (phía trừ/âm)", [r"Bk.*(trừ|-|ー|âm|マイナス)", r"quang.*Bk.*(trừ|-|ー|âm|マイナス)"]),
            ("Cả hai cùng lệch đồng thời", [r"cả hai", r"đồng thời", r"kết hợp", r"両方", r"同時に"]),
            ("Khoảng cách B dài -> nguy cơ lỗi C7620 M", [r"khoảng cách B", r"B距離", r"C7620", r"Magenta", r"M"]),
        ],
    },
    {
        "id": "Q0708",
        "question": "光路高さ1.15 mmを超えると必ずCamera読取不能になりますか。",
        "ref": "いいえ。資料では1.15 mm以上はC7620発生可能性があるLevelで、Camera読取範囲外になる目安は1.24以上と記載されています。この2つのThresholdを区別する必要があります。出典ファイル：Sirius 2 _ C7620_報告版 4.pptx.",
        "screenshot": SCREENSHOT_Q0708,
        "criteria": [
            ("Kết luận phủ định (Không phải / Không)", [r"không phải", r"không", r"いいえ", r"không thể khẳng định"]),
            ("1.15 mm là ngưỡng có nguy cơ C7620", [r"1\.15", r"C7620", r"khả năng", r"nguy cơ"]),
            ("1.24 mm là ngưỡng Camera vượt ngoài tầm đọc", [r"1\.24", r"Camera", r"đọc", r"ngoài phạm vi", r"phạm vi"]),
        ],
    },
]


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
    # Chờ sidecar sẵn sàng
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
        "micro_line": "",
        "complete_line": "",
        "first_token_line": "",
        "micro_timings": {},
        "target_collection": "",
        "backend": "",
        "ok": False,
    }
    if not server_log.exists():
        return res

    try:
        with open(server_log, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return res

    found_start = False
    for ln in lines:
        if f"[STREAMING_QA_START] conv={conv_id}" in ln:
            res["qa_start_line"] = ln.strip()
            found_start = True
            m_bk = re.search(r"backend=([a-zA-Z0-9_]+)", ln)
            if m_bk:
                res["backend"] = m_bk.group(1)
        elif found_start and "[RETRIEVAL_MICRO_TIMING]" in ln and not res["micro_line"]:
            res["micro_line"] = ln.strip()
        elif found_start and f"[STREAMING_QA_FIRST_TOKEN] conv={conv_id}" in ln:
            res["first_token_line"] = ln.strip()
        elif f"[STREAMING_QA_COMPLETE] conv={conv_id}" in ln:
            res["complete_line"] = ln.strip()
            if "ok=True" in ln:
                res["ok"] = True

    if res["micro_line"]:
        m_col = re.search(r"collection=([a-zA-Z0-9_]+)", res["micro_line"])
        if m_col:
            res["target_collection"] = m_col.group(1)

        micro_dict: dict[str, float] = {}
        for k in (
            "pipe_wait_ms",
            "coverage_verify_ms",
            "lexical_ms",
            "embed_ms",
            "dense_ms",
            "sparse_ms",
            "fuse_ms",
            "context_expand_ms",
        ):
            m = re.search(rf"{k}=([\d\.]+)", res["micro_line"])
            if m:
                micro_dict[k] = float(m.group(1))
            else:
                micro_dict[k] = 0.0

        res["micro_timings"] = micro_dict
        pure_s = (
            micro_dict.get("coverage_verify_ms", 0.0)
            + micro_dict.get("lexical_ms", 0.0)
            + micro_dict.get("embed_ms", 0.0)
            + micro_dict.get("dense_ms", 0.0)
            + micro_dict.get("sparse_ms", 0.0)
            + micro_dict.get("fuse_ms", 0.0)
            + micro_dict.get("context_expand_ms", 0.0)
        ) / 1000.0
        res["pure_retrieval_s"] = round(pure_s, 4)

    return res


def submit_question_and_wait(
    page: Any,
    conv_id: str,
    question: str,
    *,
    done_screenshot: Path | None = None,
    timeout_s: float = 300.0,
) -> dict[str, Any]:
    composer_selector = 'textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"], textarea[placeholder*="Nhập câu hỏi"], [class*="st-key-wsc_question_input"] textarea'
    log(f"[WAIT_COMPOSER] Đang chờ thanh soạn thảo cho conv={conv_id}...")
    page.wait_for_selector(composer_selector, timeout=90000)
    textarea = page.locator(composer_selector).first
    textarea.wait_for(state="visible", timeout=30000)
    textarea.click()
    textarea.fill(question)
    page.wait_for_timeout(400)

    t_fire = datetime.now()
    t_fire_str = t_fire.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log(f"[TURN_FIRE] conv={conv_id} tại {t_fire_str}: {question}")

    send_btn = page.locator(
        f'[class*="st-key-wsc_ask_{conv_id}"] button, '
        f'[class*="st-key-wsc-action-{conv_id}"] button, '
        f'[class*="st-key-wsc-action-"] button'
    ).first
    if send_btn.count() > 0:
        send_btn.click(force=True)
    else:
        textarea.press("Control+Enter")

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
                        log(f"[RETRY_SEND] Textarea vẫn còn text cho conv={conv_id}, gửi lại...")
                        if send_btn.count() > 0:
                            send_btn.click(force=True)
                        else:
                            textarea.press("Control+Enter")
                except Exception:
                    pass
                user_msg_confirmed = True

        markers = parse_conv_markers(SERVER_LOG_FILE, conv_id)
        if markers["complete_line"]:
            log(f"[TURN_DONE] {markers['complete_line']}")
            break
        page.wait_for_timeout(500)

    page.wait_for_timeout(3000)
    if done_screenshot is not None:
        try:
            page.screenshot(path=str(done_screenshot))
            log(f"[SCREENSHOT] Đã chụp ảnh hoàn tất lượt tại: {done_screenshot}")
        except Exception as e:
            log(f"[SCREENSHOT_WARN] {e}")

    msgs = load_messages(conv_id)
    ast_msgs = [m for m in msgs if m.role == "assistant"]
    ans_text = ast_msgs[-1].content if ast_msgs else ""
    ast_badge = getattr(ast_msgs[-1], "model_badge", {}) if ast_msgs else {}

    markers = parse_conv_markers(SERVER_LOG_FILE, conv_id)
    markers["t_fire"] = t_fire_str
    markers["answer_length"] = len(ans_text)
    markers["answer_text"] = ans_text
    markers["answer_badge"] = ast_badge
    return markers


def main() -> None:
    if SESSION_LOG_FILE.exists():
        SESSION_LOG_FILE.unlink()

    log("=" * 88)
    log("BẮT ĐẦU ĐO THỰC NGHIỆM: DESKTOP-PC0575-SYNC-C7620")
    log("=" * 88)
    git_head = get_git_head()
    log(f"[GIT] Commit HEAD PC0575: {git_head}")

    nb_id = "NB-PC0575-C7620"
    save_notebook(DocumentNotebook(
        id=nb_id,
        title="Sổ Kiểm tra Đồng bộ C7620-CJK",
        description="Sổ kiểm tra 3 câu CJK mục tiêu về C7620 trên PC0575 (Kho LSU)",
        collection_id="lsu",
    ))

    conv_map: dict[str, str] = {}
    for item in TARGET_QUESTIONS:
        qid = item["id"]
        cid = f"CONV-PC0575-C7620-{qid}-{uuid.uuid4().hex[:6].upper()}"
        conv_map[qid] = cid
        save_conversation(WorkspaceConversation(
            id=cid,
            notebook_id=nb_id,
            title=f"{qid} - {item['question'][:30]}...",
            ai_mode="grounded",
        ))

    kill_all_workers_and_servers()

    # Khởi động sidecar trước
    sidecar_proc = ensure_sidecar_running()

    vm_before = psutil.virtual_memory()
    log(
        f"[RAM_BASELINE] System RAM trước khi mở app: "
        f"used={(vm_before.total - vm_before.available) / (1024**3):.2f} GB / "
        f"{vm_before.total / (1024**3):.2f} GB ({vm_before.percent:.1f}%)"
    )

    t_start_app = datetime.now()
    log(f"[STARTUP] Khởi động Streamlit server trên cổng {PORT}...")
    server_proc = start_server(PORT, SERVER_LOG_FILE)

    if not wait_for_server(PORT, timeout=90):
        log("[ERROR] Streamlit server không phản hồi sau 90s!")
        kill_proc(server_proc)
        kill_proc(sidecar_proc)
        sys.exit(1)

    t_server_ready = datetime.now()
    log(f"[STARTUP] Server sẵn sàng sau {(t_server_ready - t_start_app).total_seconds():.2f}s")

    results_all: list[dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1600, "height": 1000})
        page = context.new_page()

        # Mở màn hình đầu tiên kiểm tra readiness
        first_qid = TARGET_QUESTIONS[0]["id"]
        first_cid = conv_map[first_qid]
        first_url = f"{URL}/?nb={nb_id}&conv={first_cid}&block=lsu"
        log(f"[NAV_FIRST] Điều hướng màn hình đầu tiên: {first_url}")
        page.goto(first_url, wait_until="domcontentloaded", timeout=60000)

        composer_sel = 'textarea[placeholder*="Nh\u1eadp c\u00e2u h\u1ecfi"], textarea[placeholder*="Nhập câu hỏi"], [class*="st-key-wsc_question_input"] textarea'
        page.wait_for_selector(composer_sel, timeout=90000)
        page.wait_for_timeout(2000)
        page.screenshot(path=str(SCREENSHOT_READY))
        log(f"[SCREENSHOT] Đã chụp ảnh app ready: {SCREENSHOT_READY}")

        # Chờ worker lsu ấm
        from aios_habit.workspace_chat_rag_v2_adapter import is_workspace_chat_worker_warmed
        log("[WARM_WAIT] Chờ worker khối lsu sẵn sàng trước khi gửi lượt đo...")
        t_w = time.time()
        while time.time() - t_w < 90:
            if is_workspace_chat_worker_warmed(collection_id="lsu"):
                log(f"[WARM_WAIT] Worker lsu đã sẵn sàng sau {(time.time() - t_w):.2f}s!")
                break
            page.wait_for_timeout(500)

        for idx, item in enumerate(TARGET_QUESTIONS, 1):
            qid = item["id"]
            cid = conv_map[qid]
            q_text = item["question"]
            shot_path = item["screenshot"]

            nav_url = f"{URL}/?nb={nb_id}&conv={cid}&block=lsu"
            log(f"\n{'='*70}\n[TURN {idx}] {qid}: {q_text}\nURL: {nav_url}\n{'='*70}")
            page.goto(nav_url, wait_until="domcontentloaded", timeout=60000)

            turn_res = submit_question_and_wait(
                page,
                cid,
                q_text,
                done_screenshot=shot_path,
                timeout_s=360.0,
            )

            ans_text = turn_res.get("answer_text", "")
            log(f"[{qid} ANSWER] Độ dài: {len(ans_text)} ký tự")
            log(f"[{qid} PREVIEW] {ans_text[:250]}...")

            # Đánh giá tiêu chí
            criteria_eval = []
            all_pass = True
            for c_desc, patterns in item["criteria"]:
                matched = any(re.search(pat, ans_text, re.IGNORECASE) for pat in patterns)
                criteria_eval.append({
                    "criteria": c_desc,
                    "passed": matched,
                })
                if not matched:
                    all_pass = False

            log(f"[{qid} CRITERIA] Kết quả: {'ĐẠT 100%' if all_pass else 'CHƯA ĐỦ'}")
            for c in criteria_eval:
                log(f"    - {c['criteria']}: {'ĐẠT' if c['passed'] else 'THIẾU'}")

            sha_img = compute_sha256(shot_path) if shot_path.exists() else ""
            size_img = shot_path.stat().st_size if shot_path.exists() else 0

            rec = {
                "stt": idx,
                "id": qid,
                "question": q_text,
                "ref_answer": item["ref"],
                "conversation_id": cid,
                "answer_text": ans_text,
                "answer_length": len(ans_text),
                "passed": all_pass,
                "criteria_eval": criteria_eval,
                "micro_timings": turn_res.get("micro_timings", {}),
                "pure_retrieval_s": turn_res.get("pure_retrieval_s", 0.0),
                "target_collection": turn_res.get("target_collection", ""),
                "backend": turn_res.get("backend", ""),
                "ok": turn_res.get("ok", False),
                "screenshot": str(shot_path),
                "screenshot_sha256": sha_img,
                "screenshot_size_bytes": size_img,
            }
            results_all.append(rec)

        browser.close()

    kill_proc(server_proc)
    kill_proc(sidecar_proc)

    # Lưu JSON kết quả
    json_data = {
        "ma_ve": "DESKTOP-PC0575-SYNC-C7620",
        "thoi_diem": datetime.now(timezone.utc).isoformat(),
        "git_head": git_head,
        "may_thuc_thi": "KDTVN-PC0575",
        "cau_hinh": "BB-CONFIG-PARITY-01 (CPU-only, OMP=1, MKL=1, NUMPY_DENSE=1, port 8501)",
        "results": results_all,
    }
    with open(JSON_RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    log(f"\n[DONE] Đã lưu kết quả JSON tại: {JSON_RESULT_FILE}")


if __name__ == "__main__":
    main()
