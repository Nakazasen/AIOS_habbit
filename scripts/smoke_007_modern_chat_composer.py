"""Browser smoke for Goal 007 — modern chat composer.

    uv run --with playwright --no-sync python scripts/smoke_007_modern_chat_composer.py --headed
"""

from __future__ import annotations

import argparse
import json
import os
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
    area = page.get_by_placeholder("Nhập câu hỏi bạn muốn AI hỗ trợ...")
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


def run_smoke(*, headed: bool, port: int, out_dir: Path) -> dict:
    from playwright.sync_api import sync_playwright

    results: list[dict] = []
    work = Path(tempfile.mkdtemp(prefix="aios_smoke_007_"))
    png_path = work / "smoke007.png"
    _write_png(png_path)
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
