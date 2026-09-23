"""Browser smoke for Goal 007 — modern chat composer.

    uv run --with playwright --no-sync python scripts/smoke_007_modern_chat_composer.py --headed
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_SCRIPT = REPO_ROOT / "src" / "aios_habit" / "workspace_chat_app.py"
DEFAULT_PORT = 8538
NOTEBOOK_TITLE = "SMOKE-007 modern composer"

# Seeded conversation used by the deterministic UI scenarios (S7-S9). The
# answer and its evidence trace are written straight into the isolated store so
# bubbles, the answer measure, and the evidence-graph canvas can be checked
# without any reachable answer provider.
SEED_NOTEBOOK_ID = "smoke007seed"
SEED_CONVERSATION_ID = "smoke007seedconv"
SEED_USER_MESSAGE_ID = "MSG-SEED007-USER"
SEED_ASSISTANT_MESSAGE_ID = "MSG-SEED007-ASSISTANT"
SEED_TRACE_ID = "trc_smoke007seed0001"
SEED_ANSWER = (
    "Theo quy trình siết bu-lông nắp máy ở tài liệu [1], thứ tự siết theo hình sao "
    "và siết hai lượt. Hướng dẫn kiểm tra mô-men nằm trong tài liệu [2]."
)

_SEED_SCRIPT = r'''
import sys
from pathlib import Path

sys.path.insert(0, r"{src_root}")

from aios_habit.evidence_trace import build_evidence_trace_from_citations
from aios_habit.workspace_chat_models import ChatMessage, DocumentNotebook, WorkspaceConversation
from aios_habit.workspace_chat_store import (
    init_chat_store,
    save_conversation,
    save_evidence_trace,
    save_message,
    save_notebook,
)

init_chat_store()
save_notebook(DocumentNotebook(id=r"{nb}", title="SMOKE-007 bang chung", description="So gieo san cho smoke 007"))
save_conversation(WorkspaceConversation(
    id=r"{conv}",
    notebook_id=r"{nb}",
    title="SMOKE-007 co trich dan",
    ui_locale="vi",
    answer_language="vi",
))
save_message(ChatMessage(
    id=r"{user_msg}",
    conversation_id=r"{conv}",
    role="user",
    content="Siet bu-long nap may theo thu tu nao?",
))
evidence_items = [
    {{
        "id": "SRC-SEED-1",
        "source_id": "SRC-SEED-1",
        "title": "SMOKE007_quy_trinh_siet_bu_long.txt",
        "text": "Siet bu-long nap may theo thu tu hinh sao, siet hai luot: luot dau 40% mo-men, luot sau dat mo-men danh dinh.",
        "citation_id": "[1]",
    }},
    {{
        "id": "SRC-SEED-2",
        "source_id": "SRC-SEED-2",
        "title": "SMOKE007_kiem_tra_mo_men.txt",
        "text": "Kiem tra mo-men bang can luc sau khi siet du 24 gio, ghi ket qua vao phieu theo doi.",
        "citation_id": "[2]",
    }},
]
trace = build_evidence_trace_from_citations(
    query="Siet bu-long nap may theo thu tu nao?",
    answer_text={answer},
    evidence_items=evidence_items,
    notebook_id=r"{nb}",
    conversation_id=r"{conv}",
    user_message_id=r"{user_msg}",
    assistant_message_id=r"{assistant_msg}",
    ui_locale="vi",
    answer_language="vi",
    provenance={{"operational_mode": "direct", "provider_name": "SMOKE-007 seed", "model_name": "deterministic_seed"}},
    trace_id=r"{trace_id}",
)
save_evidence_trace(trace)
save_message(ChatMessage(
    id=r"{assistant_msg}",
    conversation_id=r"{conv}",
    role="assistant",
    content={answer},
    trace_id=trace.trace_id,
))
print("SEED_OK", trace.trace_id, trace.metadata.get("status"), trace.metadata.get("cited_count"))
'''


def _seed_conversation(cwd: Path) -> str:
    """Seed a notebook, conversation, answer, and valid evidence trace into the isolated store."""
    script = _SEED_SCRIPT.format(
        src_root=str(REPO_ROOT / "src"),
        nb=SEED_NOTEBOOK_ID,
        conv=SEED_CONVERSATION_ID,
        user_msg=SEED_USER_MESSAGE_ID,
        assistant_msg=SEED_ASSISTANT_MESSAGE_ID,
        trace_id=SEED_TRACE_ID,
        answer=repr(SEED_ANSWER),
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0 or "SEED_OK" not in (proc.stdout or ""):
        raise RuntimeError(f"Khong gieo duoc du lieu smoke: {proc.stdout} {proc.stderr}")
    return (proc.stdout or "").strip()

def _write_png(path: Path, width: int = 48, height: int = 48) -> None:
    import struct
    import zlib

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + (b"\x22\x88\xcc" * width) for _ in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _ensure_playwright() -> None:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _wait_http(port: int, timeout_s: float = 90.0) -> None:
    deadline = time.time() + timeout_s
    url = f"http://127.0.0.1:{port}"
    while time.time() < deadline:
        if _port_open(port):
            try:
                urllib.request.urlopen(url, timeout=1)
                return
            except Exception:
                pass
        time.sleep(0.4)
    raise RuntimeError(f"Streamlit chua san sang tren cong {port}")


def _wait_port_free(port: int, timeout_s: float = 20.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if not _port_open(port):
            return
        time.sleep(0.3)
    raise RuntimeError(f"Cong {port} van bi chiem")


def _start_streamlit(cwd: Path, port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(APP_SCRIPT),
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
            "--server.fileWatcherType",
            "none",
        ],
        cwd=str(cwd),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _wait_http(port)
    return proc


def _stop_streamlit(proc: subprocess.Popen | None, port: int) -> None:
    if proc is not None and os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, text=True)
    elif proc is not None:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
    _wait_port_free(port)


def _dump(page, out_dir: Path, name: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        page.screenshot(path=str(out_dir / f"{name}.png"), full_page=True)
        (out_dir / f"{name}.html").write_text(page.content(), encoding="utf-8")
    except Exception:
        pass


def _body(page) -> str:
    return page.locator("body").inner_text(timeout=15_000)


def _wait_script_idle(page, timeout_ms: int = 20_000) -> None:
    page.get_by_placeholder("Nhập câu hỏi bạn muốn AI hỗ trợ...").wait_for(timeout=timeout_ms)
    page.wait_for_timeout(2000)


def _open_notebook(page) -> None:
    page.wait_for_selector("text=Sổ tài liệu của tôi", timeout=60_000)
    page.get_by_text("Tạo sổ tài liệu mới", exact=False).first.click()
    page.wait_for_timeout(400)
    title = page.get_by_label("Tên sổ")
    title.click()
    title.fill(NOTEBOOK_TITLE)
    page.get_by_role("button", name="Tạo sổ tài liệu").first.click()
    page.wait_for_timeout(1200)
    page.get_by_role("button", name=f"Mở sổ {NOTEBOOK_TITLE}").first.click(timeout=20_000)
    page.wait_for_timeout(1200)
    if "Tạo cuộc trò chuyện mới ngay" in _body(page):
        page.get_by_role("button", name="Tạo cuộc trò chuyện mới ngay").first.click()
        page.wait_for_timeout(1200)
    _wait_script_idle(page)


def _ask(page, question: str) -> None:
    # A held question leaves a second composer in the DOM, so pick the visible one.
    area = page.locator(
        'textarea[placeholder="Nhập câu hỏi bạn muốn AI hỗ trợ..."]:visible'
    ).last
    area.click()
    area.fill(question)
    area.press("Control+Enter")
    page.wait_for_timeout(1200)
    page.evaluate(
        """() => {
          const nodes = Array.from(document.querySelectorAll('[class*="st-key-wsc-action-"] button'));
          const visible = nodes.filter((el) => el.getClientRects().length > 0);
          const target = visible.at(-1) || nodes.at(-1);
          if (target) target.click();
        }"""
    )
    page.wait_for_timeout(1800)


def _upload_sources(page, paths: list[Path]) -> None:
    """Add document sources through the real ingestion widgets (QA2 needs a non-ready source)."""
    # Click the leaf label, then its enclosing <summary>: a broad match would
    # hit a page-wide container div instead of the expander toggle.
    opened = page.evaluate(
        """() => {
          const label = 'Thêm tài liệu/ảnh để AI tham khảo';
          const leaf = Array.from(document.querySelectorAll('p, span'))
            .find((el) => (el.innerText || '').trim().includes(label));
          if (!leaf) return 'leaf_missing';
          const summary = leaf.closest('summary');
          if (!summary) return 'summary_missing';
          summary.click();
          return 'clicked';
        }"""
    )
    page.wait_for_timeout(2000)
    details_open = page.evaluate(
        """() => {
          const box = Array.from(document.querySelectorAll('[data-testid="stExpander"]'))
            .find((el) => (el.innerText || '').includes('Thêm tài liệu/ảnh để AI tham khảo'));
          if (!box) return 'box_missing';
          const d = box.querySelector('details');
          return d && d.hasAttribute('open') ? 'open' : 'closed';
        }"""
    )
    if details_open != "open":
        raise RuntimeError(f"Khong mo duoc khu them tai lieu: {opened}/{details_open}")

    tab = page.locator('[role="tab"]').filter(has_text="Thêm tài liệu / ảnh").first
    tab.click(timeout=15_000)
    page.wait_for_timeout(1500)
    file_input = page.locator('input[type="file"]')
    file_input.first.wait_for(state="attached", timeout=15_000)
    file_input.first.set_input_files([str(path) for path in paths])
    page.wait_for_timeout(1500)
    page.evaluate(
        """() => {
          const labels = Array.from(document.querySelectorAll('label'));
          const hit = labels.find((el) => (el.innerText || '').includes('Dùng các tài liệu này trong câu trả lời'));
          if (!hit) return;
          const box = hit.querySelector('input[type="checkbox"]');
          if (box && !box.checked) box.click();
        }"""
    )
    page.wait_for_timeout(1000)
    page.evaluate(
        """() => {
          const btn = Array.from(document.querySelectorAll('button'))
            .find((el) => (el.innerText || '').includes('Đọc và thêm vào nguồn tạm'));
          if (btn) { btn.scrollIntoView({block: 'center'}); btn.click(); }
        }"""
    )
    page.wait_for_timeout(4000)


def run_smoke(*, headed: bool, port: int, out_dir: Path) -> dict:
    from playwright.sync_api import sync_playwright

    results: list[dict] = []
    work = Path(tempfile.mkdtemp(prefix="aios_smoke_007_"))
    png_path = work / "smoke007.png"
    _write_png(png_path)
    seed_report = _seed_conversation(work)
    proc = None
    url = f"http://127.0.0.1:{port}"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not headed)
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        page = context.new_page()
        page.set_default_timeout(25_000)
        try:
            if _port_open(port):
                raise RuntimeError(f"Cong {port} dang bi chiem")
            proc = _start_streamlit(work, port)
            page.goto(url, wait_until="domcontentloaded")
            _open_notebook(page)
            _dump(page, out_dir, "00_composer")
            body = _body(page)

            has_input = page.get_by_placeholder("Nhập câu hỏi bạn muốn AI hỗ trợ...").count() > 0
            has_send = page.locator('[class*="st-key-wsc-action-"] button').count() > 0
            has_attach = page.locator('[class*="st-key-wsc-attachment-"]').count() > 0
            has_hint = "Ctrl+" in body
            has_model = "Cầu nối Gemini Web" in body or "Gemini Web" in body
            results.append(
                {
                    "name": "S1_compact_composer",
                    "status": "PASS" if has_input and has_send and has_attach and has_hint else "FAIL",
                    "detail": f"input={has_input} send={has_send} attach={has_attach} hint={has_hint} model={has_model}",
                }
            )

            # Empty submit
            _ask(page, "")
            _dump(page, out_dir, "01_empty")
            empty_body = _body(page)
            empty_ok = "Nhập câu hỏi" in empty_body
            results.append(
                {
                    "name": "S2_empty_guidance",
                    "status": "PASS" if empty_ok else "FAIL",
                    "detail": "Hien huong dan khi gui rong" if empty_ok else "Khong thay huong dan noi dung trong",
                }
            )

            # Model picker options
            model_box = page.locator('[class*="st-key-wsc-composer-"] [data-testid="stSelectbox"]').first
            model_box.click(timeout=12_000)
            page.wait_for_timeout(400)
            picker = _body(page)
            _dump(page, out_dir, "02_model_picker")
            has_gemini = "Gemini Web" in picker
            has_cagent = "C-AGENT" in picker
            has_router = "Nakazasen" in picker
            page.keyboard.press("Escape")
            results.append(
                {
                    "name": "S3_model_picker",
                    "status": "PASS" if has_gemini and has_cagent and has_router else "FAIL",
                    "detail": f"gemini={has_gemini} cagent={has_cagent} router={has_router}",
                }
            )

            # Send a real question. Streamlit may keep widget text after submit;
            # the product signal is the existing no-sources path ("Thiếu ngữ cảnh").
            token = "SMOKE007 composer gui bang nut"
            _ask(page, token)
            processed = False
            leftover = ""
            send_body = ""
            deadline = time.time() + 10
            while time.time() < deadline:
                send_body = _body(page)
                leftover = page.get_by_placeholder("Nhập câu hỏi bạn muốn AI hỗ trợ...").input_value()
                if "Thiếu ngữ cảnh" in send_body:
                    processed = True
                    break
                page.wait_for_timeout(400)
            _dump(page, out_dir, "03_send")
            results.append(
                {
                    "name": "S4_send_question",
                    "status": "PASS" if processed else "FAIL",
                    "detail": (
                        f"processed={processed} missing_context={'Thiếu ngữ cảnh' in send_body} "
                        f"leftover={leftover!r}"
                    ),
                }
            )

            # Attachment popover + thumbnail
            attach_btn = page.locator('[class*="st-key-wsc-attachment-"] button').first
            attach_btn.click()
            page.wait_for_timeout(700)
            popover_text = _body(page)
            has_paste = "Dán ảnh" in popover_text
            file_input = page.locator('input[type="file"]')
            if file_input.count():
                file_input.last.set_input_files(str(png_path))
                page.wait_for_timeout(1500)
            page.keyboard.press("Escape")
            page.wait_for_timeout(1000)
            _dump(page, out_dir, "04_attach")
            after_attach = _body(page)
            has_thumb = page.locator('[data-testid="stImage"] img').count() > 0
            has_remove = "Bỏ ảnh" in after_attach
            has_file = "smoke007.png" in after_attach or "clipboard-image" in after_attach
            crashed_img = "Traceback" in after_attach
            results.append(
                {
                    "name": "S5_attachment_thumbnail",
                    "status": "FAIL" if crashed_img else ("PASS" if has_thumb or has_remove or has_file else "FAIL"),
                    "detail": f"paste={has_paste} thumb={has_thumb} remove={has_remove} file={has_file} traceback={crashed_img}",
                }
            )
            if has_remove:
                page.evaluate(
                    """() => {
                      const btn = Array.from(document.querySelectorAll('button'))
                        .find((el) => (el.innerText || '').includes('Bỏ ảnh'));
                      if (btn) btn.click();
                    }"""
                )
                page.wait_for_timeout(800)

            # 360 px viewport
            page.set_viewport_size({"width": 360, "height": 740})
            page.wait_for_timeout(700)
            _dump(page, out_dir, "05_narrow")
            narrow_input = page.get_by_placeholder("Nhập câu hỏi bạn muốn AI hỗ trợ...").count() > 0
            narrow_send = page.locator('[class*="st-key-wsc-action-"] button').count() > 0
            results.append(
                {
                    "name": "S6_narrow_360",
                    "status": "PASS" if narrow_input and narrow_send else "FAIL",
                    "detail": f"input={narrow_input} send={narrow_send}",
                }
            )

            # S7 - light workbench surface (US12-14) measured from computed style,
            # not from source text.
            page.set_viewport_size({"width": 1400, "height": 900})
            page.wait_for_timeout(600)
            surfaces = page.evaluate(
                """() => {
                  const hex = (c) => {
                    const m = (c || '').match(/rgba?\\(([^)]+)\\)/);
                    if (!m) return c || '';
                    const p = m[1].split(',').map((v) => v.trim());
                    const to = (v) => ('0' + parseInt(v, 10).toString(16)).slice(-2);
                    return '#' + to(p[0]) + to(p[1]) + to(p[2]);
                  };
                  const opaqueWalk = (el) => {
                    let node = el;
                    while (node) {
                      const bg = getComputedStyle(node).backgroundColor || '';
                      const m = bg.match(/rgba?\\(([^)]+)\\)/);
                      const alpha = m && m[1].split(',').length === 4 ? parseFloat(m[1].split(',')[3]) : 1;
                      if (bg && bg !== 'rgba(0, 0, 0, 0)' && alpha > 0.9) return hex(bg);
                      node = node.parentElement;
                    }
                    return '';
                  };
                  const appView = document.querySelector('[data-testid="stAppViewContainer"]');
                  const main = document.querySelector('section.stMain') || document.body;
                  const mainStyle = getComputedStyle(main);
                  const baseFont = parseFloat(getComputedStyle(appView).fontSize)
                    || parseFloat(mainStyle.fontSize) || 0;
                  const navRadio = document.querySelector('[class*="st-key-wsc_sidebar_nav_cluster"]');
                  const navText = navRadio ? (navRadio.innerText || '') : '';
                  const remoteFontLoaded = Array.from(document.fonts || []).some(
                    (f) => /googleapis|gstatic/i.test(f.family || '')
                  );
                  return {
                    app_view_bg: appView ? hex(getComputedStyle(appView).backgroundColor) : '',
                    resolved_bg: opaqueWalk(main),
                    main_text: hex(mainStyle.color),
                    base_font_px: baseFont,
                    nav_text: navText,
                    remote_font: /fonts\\.googleapis\\.com|fonts\\.gstatic\\.com/.test(document.documentElement.innerHTML || ''),
                    remote_font_loaded: remoteFontLoaded,
                    reduced_motion_rules: Array.from(document.styleSheets).some((sheet) => {
                      try {
                        return Array.from(sheet.cssRules || []).some((r) => (r.conditionText || '').includes('prefers-reduced-motion'));
                      } catch (e) { return false; }
                    }),
                  };
                }"""
            )
            nav_ok = all(
                label in (surfaces.get("nav_text") or "")
                for label in ("Hỏi tài liệu", "Hồ sơ và tri thức", "Công cụ nâng cao")
            )
            light_ok = (
                (surfaces.get("app_view_bg") or "").lower() == "#f8fafc"
                and (surfaces.get("resolved_bg") or "").lower() == "#f8fafc"
                and (surfaces.get("main_text") or "").lower() == "#020617"
                and (surfaces.get("base_font_px") or 0) >= 16
                and not surfaces.get("remote_font")
                and not surfaces.get("remote_font_loaded")
            )
            _dump(page, out_dir, "06_light_theme")
            results.append(
                {
                    "name": "S7_light_theme_and_navigation",
                    "status": "PASS" if light_ok and nav_ok else "FAIL",
                    "detail": (
                        f"app_view_bg={surfaces.get('app_view_bg')} resolved_bg={surfaces.get('resolved_bg')} "
                        f"main_text={surfaces.get('main_text')} font_px={surfaces.get('base_font_px')} "
                        f"remote_font={surfaces.get('remote_font')} reduced_motion={surfaces.get('reduced_motion_rules')} nav_ok={nav_ok}"
                    ),
                }
            )

            # S8 - answer screen (QA1-QA3) on a seeded conversation with a valid
            # evidence trace. No answer provider is involved.
            page.goto(f"{url}/?nb={SEED_NOTEBOOK_ID}&conv={SEED_CONVERSATION_ID}", wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            _dump(page, out_dir, "07_answer_screen")
            answer_text = _body(page)
            bubble_geometry = page.evaluate(
                """() => {
                  const rect = (el) => {
                    if (!el) return null;
                    const r = el.getBoundingClientRect();
                    return {w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.x)};
                  };
                  const user = document.querySelector('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])');
                  const assistant = document.querySelector('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])');
                  const userStyle = user ? getComputedStyle(user) : null;
                  const assistantStyle = assistant ? getComputedStyle(assistant) : null;
                  const longPara = Array.from(document.querySelectorAll('[data-testid="stChatMessageContent"] [data-testid="stMarkdown"] p'))
                    .map((p) => p.getBoundingClientRect().width);
                  return {
                    user_rect: rect(user), assistant_rect: rect(assistant),
                    user_bg: userStyle ? userStyle.backgroundColor : '',
                    user_border_right: userStyle ? userStyle.borderRightWidth : '',
                    assistant_bg: assistantStyle ? assistantStyle.backgroundColor : '',
                    assistant_border_left: assistantStyle ? assistantStyle.borderLeftWidth : '',
                    max_paragraph_width: longPara.length ? Math.round(Math.max(...longPara)) : 0,
                  };
                }"""
            )
            has_latest_badge = "Câu trả lời mới nhất" in answer_text
            bubbles_differ = (
                bubble_geometry.get("user_bg") != bubble_geometry.get("assistant_bg")
                and bubble_geometry.get("user_border_right") not in (None, "", "0px")
                and bubble_geometry.get("assistant_border_left") not in (None, "", "0px")
            )
            answer_measure_ok = 0 < (bubble_geometry.get("max_paragraph_width") or 0) <= 760
            # The answer is stored whole: no truncation of a long answer.
            answer_complete = (
                "thứ tự siết theo hình sao" in answer_text
                and "Hướng dẫn kiểm tra mô-men" in answer_text
            )
            results.append(
                {
                    "name": "S8_bubbles_and_answer_measure",
                    "status": "PASS" if bubbles_differ and answer_measure_ok and has_latest_badge and answer_complete else "FAIL",
                    "detail": (
                        f"bubbles_differ={bubbles_differ} latest_badge={has_latest_badge} answer_complete={answer_complete} "
                        f"measure_ok={answer_measure_ok} para_w={bubble_geometry.get('max_paragraph_width')} "
                        f"user_bg={bubble_geometry.get('user_bg')} assistant_bg={bubble_geometry.get('assistant_bg')}"
                    ),
                }
            )

            # S9 - evidence graph canvas (commit 83a62c6) inside the real chat.
            graph_button = page.get_by_role("button", name=re.compile("Xem đồ thị bằng chứng"))
            graph_present = graph_button.count() > 0
            clicked = False
            canvas = {}
            if graph_present:
                graph_button.first.click()
                page.wait_for_timeout(6000)
                clicked = True
                _dump(page, out_dir, "08_evidence_graph")
                canvas = page.evaluate(
                    """() => {
                      const frames = Array.from(document.querySelectorAll('iframe'));
                      const rect = (el) => {
                        if (!el) return null;
                        const r = el.getBoundingClientRect();
                        return {w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.x)};
                      };
                      return {
                        iframes: frames.map((f) => rect(f)),
                        chat_iframe_min_width_zero: Array.from(document.styleSheets).some((sheet) => {
                          try {
                            return Array.from(sheet.cssRules || []).some((r) => (r.cssText || '').includes('stChatMessage') && (r.cssText || '').includes('min-width: 0'));
                          } catch (e) { return false; }
                        }),
                      };
                    }"""
                )
                # Measure the .flowsint layout inside the graph iframe itself.
                try:
                    frame = page.frames[-1]
                    canvas["flowsint"] = frame.evaluate(
                        """() => {
                          const rect = (el) => {
                            if (!el) return null;
                            const r = el.getBoundingClientRect();
                            return {w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.x)};
                          };
                          const sidebar = rect(document.querySelector('.flowsint-sidebar'));
                          const canvasR = rect(document.querySelector('.flowsint-canvas-wrapper'));
                          const svg = rect(document.querySelector('.scene-board svg'));
                          const covers = (rail) => {
                            if (!rail || !canvasR) return false;
                            return Math.min(rail.x + rail.w, canvasR.x + canvasR.w) - Math.max(rail.x, canvasR.x) > 2;
                          };
                          const text = document.body.innerText || '';
                          const layoutHtml = (document.querySelector('.flowsint-layout') || document.body).innerHTML || '';
                          const groupTitles = Array.from(document.querySelectorAll('.entity-group-label'))
                            .map((el) => (el.innerText || '').trim());
                          return {
                            sidebar, canvas: canvasR, svg,
                            sidebar_covers_canvas: covers(sidebar),
                            horizontal_overflow: document.documentElement.scrollWidth > window.innerWidth + 2,
                            entity_items: document.querySelectorAll('.entity-item').length,
                            scene_nodes: document.querySelectorAll('.scene-node').length,
                            group_titles: groupTitles,
                            has_citations_group: groupTitles.some((s) => s.toUpperCase().includes('TRÍCH DẪN')),
                            has_sources_group: groupTitles.some((s) => s.toUpperCase().includes('NGUỒN TÀI LIỆU')),
                            mentions_seed_source: layoutHtml.includes('SMOKE007_quy_trinh_siet_bu_long'),
                            inspector_present: !!document.querySelector('.flowsint-inspector'),
                            text_length: text.length,
                          };
                        }""")

                except Exception as exc:
                    canvas["flowsint_error"] = str(exc)
            flowsint = canvas.get("flowsint") or {}
            canvas_ok = (
                graph_present
                and clicked
                and (flowsint.get("svg") or {}).get("w", 0) >= 200
                and not flowsint.get("sidebar_covers_canvas", True)
                and not flowsint.get("horizontal_overflow", True)
            )
            graph_evidence_ok = (
                (flowsint.get("entity_items") or 0) >= 6
                and (flowsint.get("scene_nodes") or 0) >= 1
                and flowsint.get("has_citations_group")
                and flowsint.get("has_sources_group")
                and flowsint.get("mentions_seed_source")
                and flowsint.get("inspector_present")
            )
            _dump(page, out_dir, "08b_evidence_graph_nodes")
            results.append(
                {
                    "name": "S9_evidence_graph_canvas",
                    "status": "PASS" if canvas_ok and graph_evidence_ok else "FAIL",
                    "detail": (
                        f"button={graph_present} clicked={clicked} iframes={len(canvas.get('iframes', []))} "
                        f"evidence_ok={graph_evidence_ok} "
                        f"entities={flowsint.get('entity_items')} nodes={flowsint.get('scene_nodes')} "
                        f"groups={flowsint.get('group_titles')} "
                        f"seed_source={flowsint.get('mentions_seed_source')} inspector={flowsint.get('inspector_present')} "
                        f"geometry={ {k: flowsint.get(k) for k in ('sidebar', 'canvas', 'svg', 'sidebar_covers_canvas', 'horizontal_overflow')} }"
                    ),
                }
            )

            # S10 - the graph close control removes the canvas again.
            close_ok = False
            if canvas_ok:
                page.get_by_role("button", name=re.compile("Đóng đồ thị bằng chứng")).first.click()
                page.wait_for_timeout(3000)
                _dump(page, out_dir, "09_graph_closed")
                reopen = page.get_by_role("button", name=re.compile("Xem đồ thị bằng chứng"))
                close_ok = reopen.count() > 0
            results.append(
                {
                    "name": "S10_evidence_graph_closes",
                    "status": "PASS" if close_ok else "FAIL",
                    "detail": f"reopener_back={close_ok}",
                }
            )

            # S11 - QA2 waiting steps in the live DOM. A brand-new source is not
            # ready yet, so the question is held and the assistant bubble must
            # show the real three steps with only the current one active.
            fixture = REPO_ROOT / "tests" / "fixtures" / "incremental_source_prep" / "SMOKE005_THUY_LUC.txt"
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            _open_notebook(page)
            _upload_sources(page, [fixture])
            _dump(page, out_dir, "10_sources_added")
            source_added = page.evaluate(
                """() => {
                  const t = document.body.innerText || '';
                  return {
                    manager: (t.match(/Quản lý tài liệu[^\\n]*/) || [''])[0],
                    none_left: t.includes('Chưa có nguồn nào.'),
                    filename: t.includes('SMOKE005_THUY_LUC'),
                  };
                }"""
            )
            # QA2 part A: while the new source is still being prepared the app must
            # hold the question with a Vietnamese explanation, not a fake progress bar.
            _ask(page, "Siết bu-lông nắp SMOKE005 theo hình sao thế nào?")
            held_state: dict = {}
            deadline = time.time() + 40
            while time.time() < deadline:
                page.wait_for_timeout(1000)
                held_state = page.evaluate(
                    """() => {
                      const text = document.body.innerText || '';
                      return {
                        held: text.includes('AIOS đang chuẩn bị tài liệu liên quan'),
                        cancel: text.includes('Hủy câu hỏi đang chờ'),
                        percent_claim: /\\b\\d{1,3}\\s*%\\b/.test(text),
                      };
                    }"""
                )
                if held_state.get("held") or held_state.get("cancel"):
                    break
            _dump(page, out_dir, "11_question_held")
            held_ok = bool(
                held_state.get("held") or held_state.get("cancel")
            ) and not held_state.get("percent_claim")
            results.append(
                {
                    "name": "S11a_question_held_no_fake_progress",
                    "status": "PASS" if held_ok else "FAIL",
                    "detail": f"source_added={source_added} state={held_state}",
                }
            )

            # QA2 part B: the three waiting steps must appear from the real
            # "AI is working" state, with only the last step active.
            ready = None
            waited = 0.0
            deadline = time.time() + 600
            while time.time() < deadline:
                page.wait_for_timeout(5000)
                waited += 5
                ratio = page.evaluate(
                    """() => {
                      const m = (document.body.innerText || '')
                        .match(/Tài liệu sẵn sàng để tìm kiếm:\\s*(\\d+)\\s*\\/\\s*(\\d+)/);
                      return m ? [Number(m[1]), Number(m[2])] : null;
                    }"""
                )
                if ratio and ratio[0] >= 1:
                    ready = ratio
                    break
            _dump(page, out_dir, "12_source_ready")
            steps: dict = {}
            if ready:
                _ask(page, "Siết bu-lông nắp SMOKE005 theo hình sao thế nào?")
                deadline = time.time() + 60
                while time.time() < deadline:
                    page.wait_for_timeout(700)
                    steps = page.evaluate(
                        """() => {
                          const text = document.body.innerText || '';
                          const dots = (label) => {
                            const idx = text.indexOf(label);
                            if (idx < 0) return null;
                            return text.slice(Math.max(0, idx - 3), idx).includes('●');
                          };
                          return {
                            spinner: text.includes('AIOS đang phân tích và tìm kiếm câu trả lời'),
                            title: text.includes('Đang xử lý câu hỏi'),
                            find: dots('Tìm nguồn'),
                            read: dots('Đọc trích đoạn'),
                            synth: dots('Tổng hợp trả lời'),
                            percent_claim: /\\b\\d{1,3}\\s*%\\b/.test(text),
                          };
                        }"""
                    )
                    if steps.get("title"):
                        break
            _dump(page, out_dir, "13_answer_wait_steps")
            flags = [steps.get("find"), steps.get("read"), steps.get("synth")]
            active = [i for i, v in enumerate(flags) if v is True]
            steps_ok = bool(steps.get("title")) and active == [2] and not steps.get("percent_claim")
            results.append(
                {
                    "name": "S11b_three_waiting_steps_real_state",
                    "status": "PASS" if steps_ok else "FAIL",
                    "detail": f"ready={ready} waited_s={waited} steps={steps} active={active}",
                }
            )
        except Exception as exc:
            _dump(page, out_dir, "zz_crash")
            results.append({"name": "CRASH", "status": "FAIL", "detail": str(exc)})
        finally:
            try:
                context.close()
                browser.close()
            except Exception:
                pass
            _stop_streamlit(proc, port)

    statuses = [item["status"] for item in results if item["name"] != "CRASH"]
    crashed = any(item["name"] == "CRASH" for item in results)
    overall = "PASS" if statuses and all(status == "PASS" for status in statuses) and not crashed else "FAIL"
    return {
        "feature": "007-modern-chat-composer",
        "overall": overall,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "work_dir": str(work),
        "artifacts": str(out_dir),
        "seed": seed_report,
        "scenarios": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Browser smoke Goal 007")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--out-dir", default=str(REPO_ROOT / "local_runs" / "smoke_007"))
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _ensure_playwright()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = run_smoke(headed=args.headed, port=args.port, out_dir=out_dir)
    (out_dir / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Tong: {report['overall']}")
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
