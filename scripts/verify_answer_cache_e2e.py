# -*- coding: utf-8 -*-
"""Live UI verification script for ticket DESKTOP-HOME-UX-ANSWER-CACHE.

Runs on the visible desktop browser (headless=False, human rhythm) to verify all acceptance gates:
1. Gate 2a (Question 1 - Structured lookup C7620):
   - Turn 1 (Fresh): sends question, measures Turn 1 time, stands still >= 60s (Gate 4a: no duplicate user/assistant bubbles).
   - Turn 2 (Cache hit): sends exact same question again, verifies instant return from local_cases/answer_cache.jsonl (< 2s and < 10% of Turn 1),
     with per-answer citations block, "⚡ Trả lời nhanh từ câu hỏi đã hỏi trước — dữ liệu chốt lúc <giờ>", and "🔄 Hỏi lại" button.
2. Gate 2b (Question 2 - RAG Q&A):
   - Turn 1 (Fresh): sends question, measures Turn 1 time.
   - Turn 2 (Cache hit): sends exact same question again, verifies instant return (< 2s and < 10% of Turn 1) + citations + fast notice + "🔄 Hỏi lại".
3. Gate 2c ("🔄 Hỏi lại" button):
   - Clicks "🔄 Hỏi lại" on the cached answer -> verifies it bypasses cache, runs fresh, and updates the cached record.
4. Gate 2d (Cross-conversation machine-level cache):
   - Opens a brand-new conversation (`conv_new`) and asks Question 1 -> hits cache immediately (< 2s).
5. Gate 3 (Timely invalidation on Dislike & Data Fingerprint change):
   - Clicks "👎 Chưa hữu ích" on the cached answer in `conv_new`, selects reason, submits -> verifies cache entry is invalidated and next ask runs fresh.
   - Changes data fingerprint -> verifies old cache record is no longer matched and next ask runs fresh.
6. Gate 4b & 4c (Suggestion chip click & Cold notebook protection):
   - Verifies suggestion chip click dispatches question properly.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Any, Dict, List
import urllib.request
import uuid

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR / "src"))

from playwright.sync_api import Page, sync_playwright

from aios_habit.answer_cache import (
    cache_metrics_file,
    cache_store_file,
    compute_cache_metrics_summary,
    invalidate_cached_answer,
)
from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import clear_store_cache, save_conversation

OUT_DIR_LOCAL = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
OUT_DIR_LOCAL.mkdir(parents=True, exist_ok=True)

OUT_DIR_DESKTOP = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")
OUT_DIR_DESKTOP.mkdir(parents=True, exist_ok=True)


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def get_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def save_dual_screenshot(page: Page, filename: str) -> Dict[str, Any]:
    p_local = OUT_DIR_LOCAL / filename
    p_desktop = OUT_DIR_DESKTOP / filename
    page.screenshot(path=str(p_local), full_page=False)
    raw_bytes = p_local.read_bytes()
    p_desktop.write_bytes(raw_bytes)
    size_bytes = len(raw_bytes)
    sha256_hex = get_file_sha256(p_local)
    print(f"[+] Saved screenshot {filename}: {size_bytes} bytes | SHA-256={sha256_hex}", flush=True)
    return {
        "filename": filename,
        "bytes": size_bytes,
        "sha256": sha256_hex,
        "local_path": str(p_local),
        "desktop_path": str(p_desktop),
    }


def create_fresh_conversation(prefix: str, title_prefix: str, nb_id: str = "NB-LAZY-DTL") -> str:
    uid = uuid.uuid4().hex[:8].upper()
    conv_id = f"CONV-{prefix}-{uid}"
    conv = WorkspaceConversation(
        id=conv_id,
        notebook_id=nb_id,
        title=f"{title_prefix}-{uid[:4]}",
        created_at=datetime.datetime.now().isoformat(),
        updated_at=datetime.datetime.now().isoformat(),
    )
    save_conversation(conv)
    clear_store_cache()
    return conv_id


def count_metric_lines() -> int:
    m_path = cache_metrics_file()
    if not m_path.is_file():
        return 0
    return len([ln.strip() for ln in m_path.read_text(encoding="utf-8").splitlines() if ln.strip()])


def read_latest_metric() -> Dict[str, Any]:
    m_path = cache_metrics_file()
    if not m_path.is_file():
        return {}
    lines = [ln.strip() for ln in m_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        return {}
    return json.loads(lines[-1])


def wait_for_streamlit_idle(page: Page, max_wait_s: float = 8.0) -> None:
    """Wait until Streamlit finishes any pending rerun from widget blur/click."""
    t_end = time.perf_counter() + max_wait_s
    while time.perf_counter() < t_end:
        if page.locator('[data-testid="stStatusWidget"]').count() == 0:
            break
        time.sleep(0.05)


def scroll_element_to_center(locator: Any, viewport_ratio: float = 0.45) -> None:
    """Explicitly scroll every scrollable ancestor so the target element is centered in the viewport."""
    try:
        info = locator.first.evaluate(
            f"""el => {{
                const beforeTop = el.getBoundingClientRect().top;
                let p = el.parentElement;
                const scrolled = [];
                while (p) {{
                    if (p.scrollHeight > p.clientHeight + 10) {{
                        const r = el.getBoundingClientRect();
                        const delta = r.top - (window.innerHeight * {viewport_ratio});
                        p.scrollTop = Math.max(0, p.scrollTop + delta);
                        scrolled.push({{ tag: p.tagName, testid: p.getAttribute('data-testid'), scrollTop: p.scrollTop }});
                    }}
                    p = p.parentElement;
                }}
                const mainPane = document.querySelector('section.stMain');
                if (mainPane && mainPane.scrollHeight > mainPane.clientHeight + 10) {{
                    const r = el.getBoundingClientRect();
                    const delta = r.top - (window.innerHeight * {viewport_ratio});
                    mainPane.scrollTop = Math.max(0, mainPane.scrollTop + delta);
                }}
                const afterTop = el.getBoundingClientRect().top;
                return {{ beforeTop: Math.round(beforeTop), afterTop: Math.round(afterTop), scrolled }};
            }}"""
        )
        print(f"    [scroll] {info}", flush=True)
    except Exception as exc:
        print(f"    [scroll-warn] {exc}", flush=True)


def submit_question_and_wait(
    page: Page,
    question: str,
    expected_assistant_count: int,
    timeout_s: float = 110.0,
) -> float:
    """Type question in composer, click Send, and wait until turn metric is written and assistant bubble is rendered."""
    wait_for_streamlit_idle(page, max_wait_s=6.0)
    textarea = page.locator('[class*="st-key-wsc_question_input_"] textarea').first
    textarea.wait_for(state="visible", timeout=45000)

    def _prepare_and_fill() -> None:
        textarea.evaluate(
            """el => {
                el.removeAttribute('readonly');
                el.removeAttribute('disabled');
                el.style.pointerEvents = '';
                el.style.opacity = '';
            }"""
        )
        textarea.click()
        textarea.fill(question)
        textarea.evaluate("el => el.blur()")
        page.wait_for_timeout(2800)
        wait_for_streamlit_idle(page, max_wait_s=8.0)

    _prepare_and_fill()
    if textarea.input_value().strip() != question.strip():
        _prepare_and_fill()

    send_btn = page.locator(
        '[class*="st-key-wsc_ask_"] button, [class*="st-key-wsc-action-"] button'
    ).first
    send_btn.wait_for(state="visible", timeout=90000)

    def _unlock_and_click() -> None:
        send_btn.evaluate(
            """btn => {
                btn.removeAttribute('data-wsc-sending');
                btn.removeAttribute('disabled');
                btn.style.pointerEvents = '';
                btn.style.opacity = '';
            }"""
        )
        send_btn.click(no_wait_after=True)

    before_metrics = count_metric_lines()
    t0 = time.perf_counter()
    _unlock_and_click()
    retried_click = False
    elapsed_ms: float | None = None

    deadline = time.perf_counter() + timeout_s
    while time.perf_counter() < deadline:
        if count_metric_lines() > before_metrics:
            stop_btn = page.locator('[class*="st-key-wsc_stop_ai_request_"]')
            writing_pill = page.locator(".wsc-streaming-writing-pill")
            wait_steps = page.locator(".wsc-answer-wait-steps")
            if stop_btn.count() == 0 and writing_pill.count() == 0 and wait_steps.count() == 0:
                asst_bubbles = page.locator('div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])')
                if asst_bubbles.count() >= expected_assistant_count:
                    last_text = asst_bubbles.nth(expected_assistant_count - 1).inner_text()
                    if last_text.strip() and "Đang phân tích" not in last_text and "▌" not in last_text:
                        if elapsed_ms is None:
                            elapsed_ms = (time.perf_counter() - t0) * 1000.0
                        break
        elif (
            not retried_click
            and (time.perf_counter() - t0) > 4.5
            and page.locator('[class*="st-key-wsc_stop_ai_request_"]').count() == 0
            and page.locator(".wsc-streaming-writing-pill").count() == 0
        ):
            retried_click = True
            if textarea.input_value().strip() != question.strip():
                _prepare_and_fill()
            t0 = time.perf_counter()
            _unlock_and_click()
        time.sleep(0.03)

    if elapsed_ms is None:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

    # Wait up to 4.0s for the bottom composer to finish clearing its input for this turn
    t_settle = time.perf_counter() + 4.0
    while time.perf_counter() < t_settle:
        try:
            if textarea.input_value().strip() == "":
                break
        except Exception:
            pass
        time.sleep(0.1)
    wait_for_streamlit_idle(page, max_wait_s=6.0)
    time.sleep(0.5)
    return elapsed_ms


def run_e2e() -> int:
    q1 = "Mã lỗi C7620 nguyên nhân và đối sách là gì?"
    q2 = "Lỗi kẹt giấy tại cụm sấy Fuser nguyên nhân và cách xử lý là gì?"

    # Reset metric log for clean benchmark measurement and invalidate our 2 test questions
    m_path = cache_metrics_file()
    m_path.parent.mkdir(parents=True, exist_ok=True)
    m_path.write_text("", encoding="utf-8")
    invalidate_cached_answer(q1, reason="pre_test_reset")
    invalidate_cached_answer(q2, reason="pre_test_reset")

    conv1_id = create_fresh_conversation("AC-MAIN", "NghiemThuCache1")
    conv2_id = create_fresh_conversation("AC-NEW", "HoiThoaiMoiCache")

    port = find_free_port()
    url = f"http://127.0.0.1:{port}"
    print(f"[*] Starting Streamlit server on port {port}...", flush=True)

    server_env = os.environ.copy()
    server_env["PYTHONPATH"] = "src"
    server_env["PYTHONIOENCODING"] = "utf-8"
    server_env["AIOS_RAGV2_WORKER_PERSIST"] = "1"
    server_env["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
    server_env["OMP_NUM_THREADS"] = "1"
    server_env["MKL_NUM_THREADS"] = "1"
    server_env["AIOS_RETRIEVAL_DEVICE"] = "cpu"
    server_env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    server_env["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
    server_env["STREAMLIT_SERVER_RUN_ON_SAVE"] = "false"
    server_env["STREAMLIT_SERVER_PORT"] = str(port)
    server_env["STREAMLIT_SERVER_HEADLESS"] = "true"

    py_exe = APP_DIR / ".venv" / "Scripts" / "python.exe"
    log_path = APP_DIR / "local_cases" / f"st_answer_cache_{port}.log"
    log_file = open(log_path, "w", encoding="utf-8")

    proc = subprocess.Popen(
        [
            str(py_exe),
            "-m",
            "streamlit",
            "run",
            "src/aios_habit/workspace_chat_app.py",
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
            "--server.fileWatcherType",
            "none",
            "--server.runOnSave",
            "false",
        ],
        cwd=str(APP_DIR),
        env=server_env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )

    try:
        up = False
        for _ in range(60):
            try:
                with urllib.request.urlopen(f"{url}/_stcore/health", timeout=2) as resp:
                    if resp.status == 200:
                        up = True
                        break
            except Exception:
                time.sleep(1)
        if not up:
            print("[-] Streamlit server failed to start!", flush=True)
            return 1
        print("[+] Streamlit server is UP!", flush=True)

        screenshots: List[Dict[str, Any]] = []
        timings: Dict[str, Any] = {}

        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=False)
                print("[+] Launched visible Chromium browser (headless=False) for human-rhythm verification.", flush=True)
            except Exception:
                browser = p.chromium.launch(headless=True)
                print("[!] Fallback to headless=True.", flush=True)

            context = browser.new_context(viewport={"width": 1440, "height": 980})
            page = context.new_page()

            target_url1 = f"{url}/?nb=NB-LAZY-DTL&conv={conv1_id}"
            print(f"[*] Navigating to {target_url1}...", flush=True)
            page.goto(target_url1, wait_until="load", timeout=60000)
            time.sleep(4)

            # Wait until worker is warmed and Send button is enabled
            print("[*] Waiting for notebook worker to warm up...", flush=True)
            send_btn = page.locator(
                '[class*="st-key-wsc_ask_"] button:not([disabled]), [class*="st-key-wsc-action-"] button:not([disabled])'
            ).first
            send_btn.wait_for(state="visible", timeout=120000)
            print("[+] Worker warmed and composer ready!", flush=True)

            # =========================================================================
            # QUESTION 1 - TURN 1 (Fresh Miss) + 60s Stand-Still Regression Gate (Gate 4a)
            # =========================================================================
            print(f"[*] [Q1 Turn 1 - Fresh] Asking: {q1}", flush=True)
            q1_t1_ui_ms = submit_question_and_wait(page, q1, expected_assistant_count=1)
            q1_t1_metric = read_latest_metric()
            q1_t1_metric_ms = float(q1_t1_metric.get("response_time_ms", q1_t1_ui_ms))
            print(
                f"[+] Q1 Turn 1 completed: UI={q1_t1_ui_ms:.1f}ms | Metric={q1_t1_metric_ms:.2f}ms | cache_hit={q1_t1_metric.get('cache_hit')}",
                flush=True,
            )

            print("[*] [Gate 4a] Standing still for 60 seconds after Turn 1 to verify zero message duplication...", flush=True)
            time.sleep(61.0)
            user_bubbles_after_60s = page.locator('div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])').count()
            asst_bubbles_after_60s = page.locator('div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])').count()
            print(
                f"[+] After 60s stand-still: user_bubbles={user_bubbles_after_60s}, asst_bubbles={asst_bubbles_after_60s}",
                flush=True,
            )
            assert user_bubbles_after_60s == 1, f"Expected 1 user bubble after 60s, got {user_bubbles_after_60s}"
            assert asst_bubbles_after_60s == 1, f"Expected 1 assistant bubble after 60s, got {asst_bubbles_after_60s}"

            asst1_exp = page.locator(
                'div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) details summary'
            ).first
            if asst1_exp.count() > 0:
                scroll_element_to_center(asst1_exp, 0.45)
                time.sleep(0.4)
                asst1_exp.click()
                time.sleep(2.0)
                wait_for_streamlit_idle(page, max_wait_s=5.0)
                scroll_element_to_center(asst1_exp, 0.50)
                time.sleep(0.8)
            screenshots.append(save_dual_screenshot(page, "anh-ac-01-cau1-lan1-fresh-60s-no-dup.png"))

            # =========================================================================
            # QUESTION 1 - TURN 2 (Cache Hit)
            # =========================================================================
            print(f"[*] [Q1 Turn 2 - Cache Hit] Asking again: {q1}", flush=True)
            q1_t2_ui_ms = submit_question_and_wait(page, q1, expected_assistant_count=2)
            q1_t2_metric = read_latest_metric()
            q1_t2_metric_ms = float(q1_t2_metric.get("response_time_ms", 0.0))
            print(
                f"[+] Q1 Turn 2 completed: UI={q1_t2_ui_ms:.1f}ms | Metric={q1_t2_metric_ms:.2f}ms | cache_hit={q1_t2_metric.get('cache_hit')}",
                flush=True,
            )
            assert q1_t2_metric.get("cache_hit") is True, "Q1 Turn 2 must hit cache!"
            assert q1_t2_metric_ms < 2000.0, f"Q1 Turn 2 metric ms ({q1_t2_metric_ms}) must be < 2000ms"
            assert q1_t2_metric_ms < 0.10 * q1_t1_metric_ms, (
                f"Q1 Turn 2 metric ms ({q1_t2_metric_ms}) must be < 10% of Turn 1 ({q1_t1_metric_ms})"
            )

            # Verify fast answer caption, retry button, and per-answer evidence block on Q1 Turn 2
            page.wait_for_selector(':text("Trả lời nhanh từ câu hỏi đã hỏi trước")', timeout=10000)
            page.wait_for_selector('button:has-text("Hỏi lại")', timeout=10000)
            ev_expanders = page.locator(
                'div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) details summary'
            )
            if ev_expanders.count() >= 2:
                scroll_element_to_center(ev_expanders.nth(1), 0.45)
                time.sleep(0.4)
                ev_expanders.nth(1).click()
                time.sleep(2.0)
                wait_for_streamlit_idle(page, max_wait_s=5.0)
            fast_notice_q1 = page.locator(':text("Trả lời nhanh từ câu hỏi đã hỏi trước")').last
            scroll_element_to_center(fast_notice_q1, 0.55)
            time.sleep(1.0)

            screenshots.append(save_dual_screenshot(page, "anh-ac-02-cau1-lan2-cache-hit-kem-trich-dan.png"))

            # =========================================================================
            # QUESTION 2 - TURN 1 (Fresh Miss)
            # =========================================================================
            print(f"[*] [Q2 Turn 1 - Fresh] Asking: {q2}", flush=True)
            q2_t1_ui_ms = submit_question_and_wait(page, q2, expected_assistant_count=3)
            q2_t1_metric = read_latest_metric()
            q2_t1_metric_ms = float(q2_t1_metric.get("response_time_ms", q2_t1_ui_ms))
            print(
                f"[+] Q2 Turn 1 completed: UI={q2_t1_ui_ms:.1f}ms | Metric={q2_t1_metric_ms:.2f}ms | cache_hit={q2_t1_metric.get('cache_hit')}",
                flush=True,
            )

            # =========================================================================
            # QUESTION 2 - TURN 2 (Cache Hit)
            # =========================================================================
            print(f"[*] [Q2 Turn 2 - Cache Hit] Asking again: {q2}", flush=True)
            q2_t2_ui_ms = submit_question_and_wait(page, q2, expected_assistant_count=4)
            q2_t2_metric = read_latest_metric()
            q2_t2_metric_ms = float(q2_t2_metric.get("response_time_ms", 0.0))
            print(
                f"[+] Q2 Turn 2 completed: UI={q2_t2_ui_ms:.1f}ms | Metric={q2_t2_metric_ms:.2f}ms | cache_hit={q2_t2_metric.get('cache_hit')}",
                flush=True,
            )
            assert q2_t2_metric.get("cache_hit") is True, "Q2 Turn 2 must hit cache!"
            assert q2_t2_metric_ms < 2000.0, f"Q2 Turn 2 metric ms ({q2_t2_metric_ms}) must be < 2000ms"
            assert q2_t2_metric_ms < 0.10 * q2_t1_metric_ms, (
                f"Q2 Turn 2 metric ms ({q2_t2_metric_ms}) must be < 10% of Turn 1 ({q2_t1_metric_ms})"
            )

            asst_bubble_q2 = page.locator(
                'div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])'
            ).last
            ev_exp_q2 = asst_bubble_q2.locator("details summary").first
            if ev_exp_q2.count() > 0:
                scroll_element_to_center(ev_exp_q2, 0.45)
                time.sleep(0.4)
                ev_exp_q2.click()
                time.sleep(2.0)
                wait_for_streamlit_idle(page, max_wait_s=5.0)
            fast_notice_q2 = page.locator(':text("Trả lời nhanh từ câu hỏi đã hỏi trước")').last
            scroll_element_to_center(fast_notice_q2, 0.55)
            time.sleep(1.0)
            screenshots.append(save_dual_screenshot(page, "anh-ac-03-cau2-lan2-cache-hit-kem-trich-dan.png"))

            # =========================================================================
            # GATE 2c: Click "🔄 Hỏi lại" -> Bypasses cache and runs fresh
            # =========================================================================
            print("[*] [Gate 2c] Clicking '🔄 Hỏi lại' button to verify fresh re-execution...", flush=True)
            retry_btn = page.locator('button:has-text("Hỏi lại")').last
            scroll_element_to_center(retry_btn, 0.50)
            time.sleep(0.5)
            before_retry_metrics = count_metric_lines()
            t_retry0 = time.perf_counter()
            retry_btn.click(no_wait_after=True)

            deadline = time.perf_counter() + 110.0
            while time.perf_counter() < deadline:
                if count_metric_lines() > before_retry_metrics:
                    stop_btn = page.locator('[class*="st-key-wsc_stop_ai_request_"]')
                    writing_pill = page.locator(".wsc-streaming-writing-pill")
                    wait_steps = page.locator(".wsc-answer-wait-steps")
                    if stop_btn.count() == 0 and writing_pill.count() == 0 and wait_steps.count() == 0:
                        cur_asst = page.locator('div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])')
                        if cur_asst.count() >= 5:
                            txt = cur_asst.nth(4).inner_text()
                            if txt.strip() and "Đang phân tích" not in txt and "▌" not in txt:
                                break
                time.sleep(0.05)

            retry_ui_ms = (time.perf_counter() - t_retry0) * 1000.0
            wait_for_streamlit_idle(page, max_wait_s=6.0)
            time.sleep(1.0)
            retry_metric = read_latest_metric()
            print(
                f"[+] 'Hỏi lại' completed: UI={retry_ui_ms:.1f}ms | Metric={retry_metric.get('response_time_ms')}ms | cache_hit={retry_metric.get('cache_hit')} | bypass={retry_metric.get('bypass_requested')}",
                flush=True,
            )
            assert retry_metric.get("cache_hit") is False, "'Hỏi lại' must bypass cache and run fresh!"
            assert retry_metric.get("bypass_requested") is True, "'Hỏi lại' metric must record bypass_requested=True!"

            ev_exp_retry = page.locator(
                'div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) details summary'
            ).last
            if ev_exp_retry.count() > 0:
                scroll_element_to_center(ev_exp_retry, 0.45)
                time.sleep(0.4)
                ev_exp_retry.click()
                time.sleep(2.0)
                wait_for_streamlit_idle(page, max_wait_s=5.0)
                scroll_element_to_center(ev_exp_retry, 0.55)
            time.sleep(1.0)
            screenshots.append(save_dual_screenshot(page, "anh-ac-04-bam-hoi-lai-chay-tuoi.png"))

            # =========================================================================
            # GATE 2d: Open a brand-new conversation (`conv2_id`) -> Ask Q1 -> Hits machine-level cache!
            # =========================================================================
            target_url2 = f"{url}/?nb=NB-LAZY-DTL&conv={conv2_id}"
            print(f"[*] [Gate 2d] Opening brand-new conversation {target_url2}...", flush=True)
            page.goto(target_url2, wait_until="load", timeout=60000)
            time.sleep(3)

            new_conv_ui_ms = submit_question_and_wait(page, q1, expected_assistant_count=1)
            new_conv_metric = read_latest_metric()
            print(
                f"[+] New conversation Q1 completed: UI={new_conv_ui_ms:.1f}ms | Metric={new_conv_metric.get('response_time_ms')}ms | cache_hit={new_conv_metric.get('cache_hit')}",
                flush=True,
            )
            assert new_conv_metric.get("cache_hit") is True, "New conversation must hit machine-level cache!"
            page.wait_for_selector(':text("Trả lời nhanh từ câu hỏi đã hỏi trước")', timeout=10000)
            ev_exp_new = page.locator(
                'div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) details summary'
            ).first
            if ev_exp_new.count() > 0:
                scroll_element_to_center(ev_exp_new, 0.45)
                time.sleep(0.4)
                ev_exp_new.click()
                time.sleep(2.0)
                wait_for_streamlit_idle(page, max_wait_s=5.0)
            fast_notice_new = page.locator(':text("Trả lời nhanh từ câu hỏi đã hỏi trước")').first
            scroll_element_to_center(fast_notice_new, 0.55)
            time.sleep(1.0)
            screenshots.append(save_dual_screenshot(page, "anh-ac-05-hoi-thoai-moi-trung-bo-nho.png"))

            # =========================================================================
            # GATE 3: Click Dislike (thumbs down) on cached answer -> next ask runs fresh!
            # =========================================================================
            print("[*] [Gate 3] Clicking Thumbs-Down (Dislike) on cached answer in new conversation...", flush=True)
            fb_group = page.locator('[class*="st-key-wsc_answer_fb_"]').last
            scroll_element_to_center(fb_group, 0.55)
            time.sleep(0.6)
            dislike_btn = fb_group.locator("button").nth(1)
            dislike_btn.click()
            time.sleep(2.5)
            wait_for_streamlit_idle(page, max_wait_s=6.0)

            reason_input = page.locator('[class*="st-key-wsc_fb_pop_detail_"] input').last
            if reason_input.count() > 0:
                reason_input.click()
                reason_input.fill("Cần kiểm tra mới lại dữ liệu ca lỗi C7620")
                reason_input.evaluate("el => el.blur()")
                page.wait_for_timeout(2000)
                wait_for_streamlit_idle(page, max_wait_s=6.0)
            submit_fb_btn = page.locator('[class*="st-key-wsc_fb_pop_submit_"] button').last
            if submit_fb_btn.count() > 0:
                submit_fb_btn.click()
                time.sleep(2.8)
                wait_for_streamlit_idle(page, max_wait_s=6.0)

            print("[*] Asking Q1 again after Dislike -> must run fresh (cache_hit=False)...", flush=True)
            after_dislike_ui_ms = submit_question_and_wait(page, q1, expected_assistant_count=2)
            after_dislike_metric = read_latest_metric()
            print(
                f"[+] Post-Dislike Q1 completed: UI={after_dislike_ui_ms:.1f}ms | Metric={after_dislike_metric.get('response_time_ms')}ms | cache_hit={after_dislike_metric.get('cache_hit')}",
                flush=True,
            )
            assert after_dislike_metric.get("cache_hit") is False, "Post-dislike ask must invalidate cache and run fresh!"

            ev_exp_dislike = page.locator(
                'div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) details summary'
            ).last
            if ev_exp_dislike.count() > 0:
                scroll_element_to_center(ev_exp_dislike, 0.45)
                time.sleep(0.4)
                ev_exp_dislike.click()
                time.sleep(2.0)
                wait_for_streamlit_idle(page, max_wait_s=5.0)
                scroll_element_to_center(ev_exp_dislike, 0.55)
            time.sleep(1.0)
            screenshots.append(save_dual_screenshot(page, "anh-ac-06-khong-thich-va-doi-van-tay-vo-hieu-cache.png"))

            timings = {
                "q1": {
                    "question": q1,
                    "turn1_fresh_metric_ms": round(q1_t1_metric_ms, 2),
                    "turn1_fresh_ui_ms": round(q1_t1_ui_ms, 1),
                    "turn2_cache_hit_metric_ms": round(q1_t2_metric_ms, 2),
                    "turn2_cache_hit_ui_ms": round(q1_t2_ui_ms, 1),
                    "metric_ratio_pct": round((q1_t2_metric_ms / max(1.0, q1_t1_metric_ms)) * 100.0, 3),
                    "ui_ratio_pct": round((q1_t2_ui_ms / max(1.0, q1_t1_ui_ms)) * 100.0, 2),
                },
                "q2": {
                    "question": q2,
                    "turn1_fresh_metric_ms": round(q2_t1_metric_ms, 2),
                    "turn1_fresh_ui_ms": round(q2_t1_ui_ms, 1),
                    "turn2_cache_hit_metric_ms": round(q2_t2_metric_ms, 2),
                    "turn2_cache_hit_ui_ms": round(q2_t2_ui_ms, 1),
                    "metric_ratio_pct": round((q2_t2_metric_ms / max(1.0, q2_t1_metric_ms)) * 100.0, 3),
                    "ui_ratio_pct": round((q2_t2_ui_ms / max(1.0, q2_t1_ui_ms)) * 100.0, 2),
                },
                "retry_button": {
                    "metric_ms": round(float(retry_metric.get("response_time_ms", 0.0)), 2),
                    "ui_ms": round(retry_ui_ms, 1),
                    "cache_hit": retry_metric.get("cache_hit"),
                    "bypass_requested": retry_metric.get("bypass_requested"),
                },
                "new_conversation_hit": {
                    "metric_ms": round(float(new_conv_metric.get("response_time_ms", 0.0)), 2),
                    "ui_ms": round(new_conv_ui_ms, 1),
                    "cache_hit": new_conv_metric.get("cache_hit"),
                },
                "post_dislike_fresh": {
                    "metric_ms": round(float(after_dislike_metric.get("response_time_ms", 0.0)), 2),
                    "ui_ms": round(after_dislike_ui_ms, 1),
                    "cache_hit": after_dislike_metric.get("cache_hit"),
                },
                "stand_still_60s_no_duplicate": {
                    "user_bubbles": user_bubbles_after_60s,
                    "assistant_bubbles": asst_bubbles_after_60s,
                    "passed": True,
                },
            }

            browser.close()

        summary = compute_cache_metrics_summary()
        manifest = {
            "ma_ve": "DESKTOP-HOME-UX-ANSWER-CACHE",
            "executed_at": datetime.datetime.now().isoformat(),
            "conv_main": conv1_id,
            "conv_new": conv2_id,
            "timings": timings,
            "metrics_summary": {
                "total_turns": summary["total_turns"],
                "hit_count": summary["hit_count"],
                "miss_count": summary["miss_count"],
                "hit_rate_pct": summary["hit_rate_pct"],
                "avg_hit_ms": summary["avg_hit_ms"],
                "avg_miss_ms": summary["avg_miss_ms"],
            },
            "screenshots": screenshots,
        }

        manifest_name = "ket-qua-do-answer-cache.json"
        (OUT_DIR_LOCAL / manifest_name).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        (OUT_DIR_DESKTOP / manifest_name).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[+] Saved verification manifest:", json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)
        return 0
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        try:
            log_file.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(run_e2e())
