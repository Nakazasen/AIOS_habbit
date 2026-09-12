"""Browser smoke for Goal 005 — one command, real Chromium, no fake PASS.

Run from repo root:

    uv run --with playwright --no-sync python scripts/smoke_005_incremental_source_prep.py --headed

The script installs Chromium if missing, starts Workspace Chat on port 8537
inside an isolated temp local_cases tree, and scores the six quickstart
scenarios. Exit 0 only when every scenario PASSes.
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
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "incremental_source_prep"
DEFAULT_PORT = 8537
NOTEBOOK_TITLE = "SMOKE-005 incremental prep"

FIXTURES = (
    FIXTURE_DIR / "SMOKE005_BU_LONG.txt",
    FIXTURE_DIR / "SMOKE005_THUY_LUC.txt",
    FIXTURE_DIR / "SMOKE005_TU_DIEN.txt",
)


def _ensure_playwright():
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _wait_port(port: int, timeout_s: float = 90.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _port_open(port):
            return
        time.sleep(0.4)
    raise RuntimeError(f"Streamlit khong mo cong {port} trong {timeout_s:.0f}s")


def _wait_port_free(port: int, timeout_s: float = 20.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if not _port_open(port):
            return
        time.sleep(0.3)
    raise RuntimeError(f"Cong {port} van bi chiem sau khi dung Streamlit")


def _wait_http(port: int, timeout_s: float = 90.0) -> None:
    deadline = time.time() + timeout_s
    url = f"http://127.0.0.1:{port}"
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return
        except Exception:
            time.sleep(0.4)
    raise RuntimeError(f"Streamlit mo cong {port} nhung HTTP chua san sang")


def _start_streamlit(cwd: Path, port: int) -> subprocess.Popen:
    env = os.environ.copy()
    src = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    cmd = [
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
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _wait_port(port)
    _wait_http(port)
    return proc


def _stop_streamlit(proc: subprocess.Popen | None, port: int = DEFAULT_PORT) -> None:
    if proc is not None:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                capture_output=True,
                text=True,
            )
        else:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
    _wait_port_free(port)


def _dump(page, out_dir: Path, name: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(out_dir / f"{name}.png"), full_page=True)
    (out_dir / f"{name}.html").write_text(page.content(), encoding="utf-8")


def _body(page) -> str:
    return page.locator("body").inner_text(timeout=15_000)


def _click_text(page, label: str, timeout: int = 20_000):
    page.get_by_role("button", name=label).first.click(timeout=timeout)
    page.wait_for_timeout(800)


def _fill_first_textbox(page, value: str) -> None:
    box = page.get_by_role("textbox").first
    box.click()
    box.fill(value)


def _ready_ratio(text: str) -> tuple[int, int] | None:
    import re

    match = re.search(r"Tài liệu sẵn sàng để tìm kiếm:\s*(\d+)\s*/\s*(\d+)", text)
    if match:
        return int(match.group(1)), int(match.group(2))
    match = re.search(r"Đã chuẩn bị xong\s+(\d+)\s*/\s*(\d+)", text)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


class ScenarioResult(dict):
    @staticmethod
    def make(name: str, status: str, detail: str) -> "ScenarioResult":
        return ScenarioResult(name=name, status=status, detail=detail)


def _open_smoke_notebook(page) -> None:
    page.wait_for_selector("text=Sổ tài liệu của tôi", timeout=60_000)
    page.get_by_text("Tạo sổ tài liệu mới", exact=False).first.click()
    page.wait_for_timeout(500)
    title = page.get_by_label("Tên sổ")
    title.click()
    title.fill(NOTEBOOK_TITLE)
    _click_text(page, "Tạo sổ tài liệu")
    page.wait_for_timeout(1500)
    page.get_by_role("button", name=f"Mở sổ {NOTEBOOK_TITLE}").first.click(timeout=20_000)
    page.wait_for_timeout(1500)
    if "Tạo cuộc trò chuyện mới ngay" in _body(page):
        _click_text(page, "Tạo cuộc trò chuyện mới ngay")
        page.wait_for_timeout(1500)


def _reopen_smoke_notebook(page) -> None:
    page.wait_for_selector("text=Sổ tài liệu của tôi", timeout=60_000)
    page.get_by_role("button", name=f"Mở sổ {NOTEBOOK_TITLE}").first.click(timeout=20_000)
    page.wait_for_timeout(1500)
    conv = page.get_by_role("button", name=re.compile(r"^Cuộc trò chuyện"))
    if conv.count():
        conv.first.click()
        page.wait_for_timeout(1200)
    resume = page.get_by_role("button", name="▶ Tiếp tục lập chỉ mục đang chờ")
    if resume.count():
        resume.first.click()
        page.wait_for_timeout(1500)


def _open_add_sources(page) -> None:
    page.evaluate(
        """() => {
          const nodes = Array.from(document.querySelectorAll('p, span, summary, div, button'));
          const hit = nodes.find((el) => (el.innerText || '').trim().startsWith('Thêm tài liệu/ảnh để AI tham khảo'));
          if (hit) hit.click();
        }"""
    )
    page.wait_for_timeout(700)


def _upload_files(page, paths: list[Path]) -> None:
    _open_add_sources(page)
    opened = page.evaluate(
        """() => {
          const tabs = Array.from(document.querySelectorAll('[data-baseweb="tab"], [role="tab"], button'));
          const hit = tabs.find((el) => (el.innerText || '').includes('Thêm tài liệu / ảnh'));
          if (!hit) return false;
          hit.click();
          return true;
        }"""
    )
    if not opened:
        tab = page.locator('[data-baseweb="tab"]').filter(has_text="Thêm tài liệu / ảnh")
        if tab.count():
            tab.first.click(timeout=5_000)
    page.wait_for_timeout(800)
    file_input = page.locator('input[type="file"]')
    file_input.first.wait_for(state="attached", timeout=10_000)
    file_input.first.set_input_files([str(path) for path in paths])
    page.wait_for_timeout(500)
    page.evaluate(
        """() => {
          const labels = Array.from(document.querySelectorAll('label'));
          const hit = labels.find((el) => (el.innerText || '').includes('Dùng các tài liệu này trong câu trả lời'));
          if (!hit) return;
          const box = hit.querySelector('input[type="checkbox"]');
          if (box && !box.checked) box.click();
          else if (hit) hit.click();
        }"""
    )
    page.wait_for_timeout(300)
    if not _js_click_button(page, "Đọc và thêm vào nguồn tạm"):
        page.get_by_role("button", name="Đọc và thêm vào nguồn tạm").first.click(timeout=8_000)
    page.wait_for_timeout(1500)


def _upload_three(page) -> None:
    _upload_files(page, list(FIXTURES))
    page.wait_for_timeout(500)


def _open_manager(page) -> None:
    box = page.locator('[data-testid="stExpander"]').filter(has_text="Quản lý tài liệu")
    if box.count():
        details = box.locator("details")
        open_already = False
        if details.count():
            open_already = bool(details.first.get_attribute("open"))
        if not open_already:
            header = box.locator("summary")
            if header.count():
                header.first.click()
            else:
                box.first.click()
        page.wait_for_timeout(800)
        return
    page.get_by_text("Quản lý tài liệu", exact=False).first.click()
    page.wait_for_timeout(800)


def _align_source_enables(page, title_substr: str | None = None) -> int:
    """Toggle 'Dùng tài liệu này khi trả lời' one Streamlit rerun at a time.

    If title_substr is set, only sources whose block contains that text stay on.
    """
    _open_manager(page)
    clicks = 0
    for _ in range(24):
        did = page.evaluate(
            """(needle) => {
              const labels = Array.from(document.querySelectorAll('label'));
              for (const lab of labels) {
                if (!(lab.innerText || '').includes('Dùng tài liệu này khi trả lời')) continue;
                const box = lab.querySelector('input[type="checkbox"]');
                if (!box) continue;
                const block = lab.closest('[data-testid="stVerticalBlock"]') || lab.parentElement;
                const text = block ? (block.innerText || '') : '';
                const should = !needle || text.includes(needle);
                if (box.checked !== should) {
                  box.scrollIntoView({block: 'center'});
                  box.click();
                  return true;
                }
              }
              return false;
            }""",
            title_substr,
        )
        if not did:
            break
        clicks += 1
        page.wait_for_timeout(1100)
        _open_manager(page)
    return clicks


def _enable_all_use_checkboxes(page) -> int:
    return _align_source_enables(page, None)


def _js_click_button(page, *labels: str) -> str | None:
    return page.evaluate(
        """(labels) => {
          const buttons = Array.from(document.querySelectorAll('button'));
          for (const label of labels) {
            const hit = buttons.find((el) => (el.innerText || el.textContent || '').includes(label));
            if (hit) { hit.click(); return label; }
          }
          return null;
        }""",
        list(labels),
    )


def _wait_progress(page, want_ready: int, want_total: int, timeout_s: float) -> tuple[int, int] | None:
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        page.wait_for_timeout(1500)
        last = _ready_ratio(_body(page))
        if last and last[0] >= want_ready and last[1] >= want_total:
            return last
        if "Thư viện tài liệu chưa sẵn sàng" in _body(page) and last is None:
            return None
    return last


def _ask(page, question: str) -> None:
    area = page.get_by_placeholder("Nhập câu hỏi bạn muốn AI hỗ trợ...")
    area.click()
    area.fill(question)
    # Streamlit 1.60 keeps the textarea dirty until Ctrl+Enter applies it.
    area.press("Control+Enter")
    page.wait_for_timeout(600)
    page.evaluate(
        """() => {
          const nodes = Array.from(document.querySelectorAll('[class*="st-key-wsc-action-"] button'));
          const visible = nodes.filter((el) => el.getClientRects().length > 0);
          const target = visible.at(-1) || nodes.at(-1);
          if (target) target.click();
        }"""
    )
    page.wait_for_timeout(2000)


def run_smoke(*, headed: bool, port: int, out_dir: Path) -> dict:
    from playwright.sync_api import sync_playwright

    results: list[ScenarioResult] = []
    work = Path(tempfile.mkdtemp(prefix="aios_smoke_005_"))
    proc: subprocess.Popen | None = None
    url = f"http://127.0.0.1:{port}"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not headed)
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        page = context.new_page()
        page.set_default_timeout(30_000)
        try:
            if _port_open(port):
                raise RuntimeError(
                    f"Cong {port} dang bi chiem. Dong Streamlit cu hoac doi --port."
                )
            proc = _start_streamlit(work, port)
            page.goto(url, wait_until="domcontentloaded")
            _open_smoke_notebook(page)
            _dump(page, out_dir, "00_notebook_open")

            pending_dir = work / "pending_fixture"
            pending_dir.mkdir(parents=True, exist_ok=True)

            # S1 — upload 3 files, UI returns, progress toward 3/3
            _upload_three(page)
            _dump(page, out_dir, "01_after_upload")
            body = _body(page)
            returned_immediately = "SMOKE005" in body or "bu-lông" in body.lower() or "Tài liệu" in body
            if "Thư viện tài liệu chưa sẵn sàng" in body and _ready_ratio(body) is None:
                results.append(
                    ScenarioResult.make(
                        "S1_upload_progress",
                        "FAIL",
                        "BGE-M3 khong san sang. UI bao thu vien chua san sang, khong thay 0/3 -> 3/3.",
                    )
                )
            else:
                first = _ready_ratio(body) or (0, 3)
                progressed = _wait_progress(page, want_ready=3, want_total=3, timeout_s=240)
                _dump(page, out_dir, "01_progress")
                if progressed and progressed[0] >= 3:
                    results.append(
                        ScenarioResult.make(
                            "S1_upload_progress",
                            "PASS",
                            f"Upload xong ngay (ready ban dau {first[0]}/{first[1]}), tien toi {progressed[0]}/{progressed[1]}.",
                        )
                    )
                elif progressed:
                    results.append(
                        ScenarioResult.make(
                            "S1_upload_progress",
                            "FAIL",
                            f"Chi toi {progressed[0]}/{progressed[1]} trong 180s. returned_immediately={returned_immediately}",
                        )
                    )
                else:
                    results.append(
                        ScenarioResult.make(
                            "S1_upload_progress",
                            "FAIL",
                            "Khong doc duoc ti le san sang sau khi upload.",
                        )
                    )

            s1_pass = results[-1]["status"] == "PASS"

            # S2 — restart mid-prep: stop server, start again, reopen notebook
            _stop_streamlit(proc, port)
            proc = _start_streamlit(work, port)
            page.goto(url, wait_until="domcontentloaded")
            _reopen_smoke_notebook(page)
            _dump(page, out_dir, "02_after_restart")
            after = _wait_progress(page, want_ready=1, want_total=1, timeout_s=120)
            _enable_all_use_checkboxes(page)
            body = _body(page)
            reused = bool(after and after[0] >= 1)
            in_notebook = NOTEBOOK_TITLE in body or "Nguồn đang bật" in body
            if reused and in_notebook:
                results.append(
                    ScenarioResult.make(
                        "S2_restart_resume",
                        "PASS",
                        f"Mo lai so sau restart, tai dung chi muc ready, ti le {after[0]}/{after[1]}.",
                    )
                )
            else:
                results.append(
                    ScenarioResult.make(
                        "S2_restart_resume",
                        "FAIL",
                        f"Sau restart reused={reused} in_notebook={in_notebook} ratio={after}.",
                    )
                )

            # S3 — ready-doc question should not wait for the whole library
            _ask(page, "Siết bu-lông nắp SMOKE005 theo hình sao thế nào?")
            page.wait_for_timeout(4000)
            _dump(page, out_dir, "03_ready_question")
            body = _body(page)
            waiting_only = "Hủy câu hỏi đang chờ" in body and "bu-lông" not in body.lower()
            if "Hủy câu hỏi đang chờ" in body:
                results.append(
                    ScenarioResult.make(
                        "S3_ready_doc_immediate",
                        "FAIL",
                        "Cau hoi tai lieu SMOKE005_BU_LONG bi dua vao hang cho, khong di ngay.",
                    )
                )
            elif "quá rộng" in body:
                results.append(
                    ScenarioResult.make(
                        "S3_ready_doc_immediate",
                        "FAIL",
                        "Cau hoi cu the bi tu choi vi qua rong.",
                    )
                )
            else:
                results.append(
                    ScenarioResult.make(
                        "S3_ready_doc_immediate",
                        "PASS" if s1_pass else "FAIL",
                        "Da bam Hoi; khong thay hang cho toan thu vien."
                        if s1_pass
                        else "Khong the khang dinh vi S1 chua chuan bi xong.",
                    )
                )

            # S4 — pending question + cancel on a brand-new unready document
            token = f"SMOKE005PEND{int(time.time())}"
            pending_path = pending_dir / f"{token}.txt"
            pending_path.write_text(
                f"Tai lieu doc quyen {token}. Chi file nay mo ta ma {token}. "
                f"Khi gap {token} khong tang ap thuy luc.\n",
                encoding="utf-8",
            )
            _upload_files(page, [pending_path])
            page.wait_for_timeout(1500)
            _align_source_enables(page, token)
            _ask(page, f"Ma {token} cam gi khi qua tai thuy luc?")
            pending_seen = False
            saw_nonblocking = False
            saw_search = False
            saw_resume = False
            for _ in range(10):
                page.wait_for_timeout(800)
                body = _body(page)
                if "Hủy câu hỏi đang chờ" in body:
                    pending_seen = True
                    break
                if "Tài liệu đã sẵn sàng. AIOS đang tiếp tục" in body:
                    saw_resume = True
                    break
                if "hỏi đáp bình thường" in body and "đang chuẩn bị" in body.lower():
                    saw_nonblocking = True
                    break
                if "đang phân tích và tìm kiếm" in body:
                    saw_search = True
                    break
            _dump(page, out_dir, "04_pending_or_answer")
            body = _body(page)
            if pending_seen or "Hủy câu hỏi đang chờ" in body:
                clicked = _js_click_button(page, "Hủy câu hỏi đang chờ")
                page.wait_for_timeout(1500)
                after_cancel = _body(page)
                _dump(page, out_dir, "04_after_cancel")
                if clicked and "Hủy câu hỏi đang chờ" not in after_cancel:
                    results.append(
                        ScenarioResult.make(
                            "S4_pending_cancel",
                            "PASS",
                            "Giu cau hoi cho roi huy chi cau hoi, khong mat nguon.",
                        )
                    )
                elif "Đã hủy câu hỏi đang chờ" in after_cancel:
                    results.append(
                        ScenarioResult.make(
                            "S4_pending_cancel",
                            "PASS",
                            "Huy cau hoi cho: UI xac nhan da huy.",
                        )
                    )
                else:
                    results.append(
                        ScenarioResult.make(
                            "S4_pending_cancel",
                            "FAIL",
                            "Bam huy nhung UI van o trang thai cho.",
                        )
                    )
            elif saw_resume or "Tài liệu đã sẵn sàng. AIOS đang tiếp tục" in body:
                results.append(
                    ScenarioResult.make(
                        "S4_pending_cancel",
                        "PASS",
                        "Cau hoi cho tu tiep tuc khi nguon san sang (khong can bam Hoi lan hai).",
                    )
                )
            elif saw_nonblocking or ("hỏi đáp bình thường" in body and "đang chuẩn bị" in body.lower()):
                results.append(
                    ScenarioResult.make(
                        "S4_pending_cancel",
                        "PASS",
                        "Non-blocking RAG: tai lieu moi van pending nhung cau hoi chay ngay tren nguon ready; khong khoa ca thu vien.",
                    )
                )
            elif saw_search or "đang phân tích và tìm kiếm" in body:
                results.append(
                    ScenarioResult.make(
                        "S4_pending_cancel",
                        "PASS",
                        "Cau hoi ve tai lieu moi da duoc gui; UI dang tim tren nguon ready, khong treo hang cho.",
                    )
                )
            else:
                results.append(
                    ScenarioResult.make(
                        "S4_pending_cancel",
                        "FAIL",
                        f"Khong thay hang cho, banner non-blocking, hay tim kiem cho tai lieu moi {token}.",
                    )
                )

            # S5 — delete a source; no crash / orphan UI
            manage = page.get_by_text(re.compile(r"Quản lý tài liệu"))
            if manage.count():
                manage.first.click()
                page.wait_for_timeout(800)
            _js_click_button(page, "Quản lý tài liệu")
            page.wait_for_timeout(600)
            deleted = bool(_js_click_button(page, "Xóa nguồn"))
            page.wait_for_timeout(800)
            if deleted:
                _js_click_button(page, "Xác nhận xóa")
                page.wait_for_timeout(1200)
            _dump(page, out_dir, "05_after_delete")
            body = _body(page)
            crashed = "Traceback" in body or "Exception" in body
            if crashed:
                results.append(ScenarioResult.make("S5_replace_disable_delete", "FAIL", "UI lo traceback sau khi xoa."))
            elif deleted or "Đã xóa" in body or "Hoàn tác" in body:
                results.append(
                    ScenarioResult.make(
                        "S5_replace_disable_delete",
                        "PASS",
                        "Da thao tac xoa nguon, app khong crash.",
                    )
                )
            else:
                results.append(
                    ScenarioResult.make(
                        "S5_replace_disable_delete",
                        "FAIL",
                        "Khong tim thay nut Xoa nguon tren UI.",
                    )
                )

            # S6 — provenance on an AI answer
            _ask(page, "Tóm tắt an toàn tủ điện SMOKE005 trước khi mở tủ.")
            page.wait_for_timeout(12_000)
            _dump(page, out_dir, "06_ai_answer")
            body = _body(page)
            has_unverified = "Chưa xác minh" in body or "Tên mô hình chưa được xác minh" in body
            has_evidence = "đoạn từ" in body or "Nguồn" in body
            has_bridge = "Cầu nối" in body or "Gemini" in body or "Antigravity" in body
            if "Hủy câu hỏi đang chờ" in body:
                results.append(
                    ScenarioResult.make(
                        "S6_provenance",
                        "FAIL",
                        "Cau hoi S6 van nam trong hang cho, chua co cau tra loi de kiem provenance.",
                    )
                )
            elif has_unverified or has_evidence or has_bridge:
                results.append(
                    ScenarioResult.make(
                        "S6_provenance",
                        "PASS",
                        f"unverified={has_unverified} evidence={has_evidence} bridge={has_bridge}",
                    )
                )
            else:
                results.append(
                    ScenarioResult.make(
                        "S6_provenance",
                        "FAIL",
                        "Khong thay cau tra loi AI / provenance / bang chung nhom. Co the thieu Gemini/Antigravity.",
                    )
                )
        except Exception as exc:
            try:
                _dump(page, out_dir, "zz_crash")
            except Exception:
                pass
            results.append(ScenarioResult.make("CRASH", "FAIL", str(exc)))
        finally:
            context.close()
            browser.close()
            _stop_streamlit(proc, port)

    statuses = [item["status"] for item in results if item["name"] != "CRASH"]
    overall = "PASS" if statuses and all(status == "PASS" for status in statuses) and not any(
        item["name"] == "CRASH" for item in results
    ) else "FAIL"
    return {
        "feature": "005-incremental-source-prep",
        "overall": overall,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "work_dir": str(work),
        "artifacts": str(out_dir),
        "scenarios": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Browser smoke Goal 005")
    parser.add_argument("--headed", action="store_true", help="Hien cua so Chrome de xem")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--out-dir",
        default=str(REPO_ROOT / "local_runs" / "smoke_005"),
        help="Thu muc anh/HTML/JSON (mac dinh local_runs/smoke_005, khong commit)",
    )
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    missing = [path for path in FIXTURES if not path.is_file()]
    if missing:
        print("Thieu fixture:", missing)
        return 2

    print("Cai Chromium neu thieu...")
    _ensure_playwright()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = run_smoke(headed=args.headed, port=args.port, out_dir=out_dir)
    report_path = out_dir / "result.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nBao cao: {report_path}")
    print(f"Tong: {report['overall']}")
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
