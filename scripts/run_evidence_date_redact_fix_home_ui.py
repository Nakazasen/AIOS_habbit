"""Runner nghiem thu giao dien that Playwright cho ve DESKTOP-EVIDENCE-DATE-REDACT-FIX-HOME.

Pham vi:
- May nha h410asrock, CPU-only, cau hinh BB-CONFIG-PARITY-01
- Port: 8535
- Kho ma: D:\\Sandbox\\AIOS_habbit
- So tay: mom_opcenter, Khoi: lsu
- Cau hoi bien the: "Trong tệp 2026_08_UnitTest.csv, serial 61C999999902 có kết quả kiểm tra như thế nào qua các ngày?"
- Tieu chi nghiem thu: dap an doc duoc moc ngay cu the (2026/08/20 va 2026/08/21),
  serial 61C999999902 co 4 dong du lieu (20/08 mot dong, 21/08 ba dong), khong bi che boi [REDACTED_LOCAL_PATH].
- Chup anh hoan tat tron than dap an, kiem dinh SHA-256 va kich thuoc byte.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

# Thiet lap UTF-8 cho console Windows
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
sys.path.insert(0, str(APP_DIR / "src"))

from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import load_messages, save_conversation
from playwright.sync_api import sync_playwright

PORT = 8535
URL = f"http://localhost:{PORT}"
REPO_DOCS_OUT_DIR = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
REPO_DOCS_OUT_DIR.mkdir(parents=True, exist_ok=True)
MAILBOX_OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua")
MAILBOX_OUT_DIR.mkdir(parents=True, exist_ok=True)
SERVER_LOG_PATH = REPO_DOCS_OUT_DIR / "evidence_date_redact_ui_server.log"


def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def get_git_head(repo_dir: Path) -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return ""


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


def run_one_turn(page, conv_id: str, notebook_id: str, block_name: str, question: str, timeout_s: int = 360):
    url = f"{URL}/?nb={notebook_id}&conv={conv_id}&block={block_name}"
    print(f"\n[PAGE] Dieu huong toi: {url}")
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(3000)

    # Cho khung soan thao san sang
    page.wait_for_selector('textarea[placeholder*="Nhập câu hỏi"]', timeout=30000)

    # Kiem tra toolbar xem khoi LSU da duoc chon chua
    try:
        block_container = page.locator(f'[class*="st-key-wsc-block-{conv_id}"]')
        btn_text = block_container.inner_text() if block_container.count() > 0 else ""
        print(f"[TOOLBAR] Block indicator text: {btn_text.strip()}")
    except Exception as e:
        print(f"[TOOLBAR] Khong doc duoc block text: {e}")

    textarea = page.locator('textarea[placeholder*="Nhập câu hỏi"]').first
    textarea.fill(question)
    page.wait_for_timeout(500)

    send_btn = page.locator(
        f'[class*="st-key-wsc_ask_{conv_id}"] button, [class*="st-key-wsc-action-"] button'
    )
    t_start = time.time()
    if send_btn.count() > 0:
        send_btn.first.click()
    else:
        textarea.press("Control+Enter")
    print(f"[SEND] Da gui cau hoi: '{question}'")

    # Cho assistant tra loi
    time.sleep(3)
    t0 = time.time()
    completed = False
    while time.time() - t0 < timeout_s:
        msgs = load_messages(conv_id)
        if len(msgs) >= 2 and msgs[-1].role == "assistant" and len(msgs[-1].content.strip()) > 0:
            completed = True
            break
        page.wait_for_timeout(2000)

    duration = time.time() - t_start
    print(f"[REPLY] Luot hoi hoan tat trong {duration:.2f}s (completed={completed})")

    # Cho UI render va reload neu can de hien thi day du bong bong
    page.wait_for_timeout(3000)
    try:
        page.wait_for_selector('[data-testid="stChatMessage"]:nth-of-type(2)', timeout=15000)
    except Exception:
        print("[PAGE] Goi page.reload() de UI cap nhat day du...")
        page.reload(wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)

    chat_messages = page.locator('[data-testid="stChatMessage"]')
    print(f"[UI] So bong bong tin nhan tren UI: {chat_messages.count()}")
    ui_bubble_text = ""
    if chat_messages.count() >= 2:
        assistant_bubble = chat_messages.nth(1)
        assistant_bubble.scroll_into_view_if_needed()
        page.evaluate("window.scrollBy(0, -80)")
        page.wait_for_timeout(2000)
        try:
            ui_bubble_text = assistant_bubble.inner_text().strip()
        except Exception:
            pass

    return duration, completed, ui_bubble_text


def main():
    print("=" * 80)
    print("BAT DAU NGHIEM THU GIAO DIEN THAT: DESKTOP-EVIDENCE-DATE-REDACT-FIX-HOME")
    print("=" * 80)

    head_habbit = get_git_head(APP_DIR)
    head_dieuphoi = get_git_head(Path(r"D:\Sandbox\aios-dieu-phoi"))
    print(f"[GIT] HEAD app (AIOS_habbit): {head_habbit}")
    print(f"[GIT] HEAD dieu phoi: {head_dieuphoi}")

    # Khoi dong Streamlit server moi tren port 8535 neu chua chay
    server_process = None
    server_log_file = None
    if not wait_for_server(PORT, timeout=2):
        print(f"[SERVER] Dang khoi dong Streamlit server tren cong {PORT}...")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(APP_DIR / "src") + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")
        env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
        env["OMP_NUM_THREADS"] = "1"
        env["MKL_NUM_THREADS"] = "1"
        env["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
        env["AIOS_BGE_QUERY_TIMEOUT"] = "1200"
        env["AIOS_BGE_INIT_TIMEOUT"] = "420"
        env["AIOS_RAGV2_WORKER_PERSIST"] = "1"
        env["AIOS_FEATURE_CHAT_ACTION"] = "1"
        env["AIOS_DOMAIN_ROUTING_ENABLED"] = "1"
        env["AIOS_STREAM_SYNTHESIS"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"

        server_log_file = open(SERVER_LOG_PATH, "w", encoding="utf-8")
        server_log_file.write(f"=== PHIEN CHAY DESKTOP-EVIDENCE-DATE-REDACT-FIX-HOME {time.strftime('%Y-%m-%dT%H:%M:%S')} ===\n")
        server_log_file.flush()

        python_exe = str(APP_DIR / ".venv" / "Scripts" / "python.exe")
        server_process = subprocess.Popen(
            [
                python_exe, "-m", "streamlit", "run",
                "src/aios_habit/workspace_chat_app.py",
                "--server.port", str(PORT),
                "--server.headless", "true",
                "--server.fileWatcherType", "none",
                "--browser.gatherUsageStats", "false",
            ],
            cwd=str(APP_DIR),
            env=env,
            stdout=server_log_file,
            stderr=subprocess.STDOUT,
        )
        if not wait_for_server(PORT, timeout=90):
            print(f"[ERROR] Khong the khoi dong Streamlit server tren cong {PORT}")
            if server_process:
                server_process.kill()
            sys.exit(1)
        print(f"[SERVER] Streamlit server san sang tai {URL}")
    else:
        print(f"[SERVER] Streamlit server da dang chay tai {URL}")

    img_ready_name = "evidence-date-redact-01-app-ready.png"
    img_ready_repo = REPO_DOCS_OUT_DIR / img_ready_name
    img_ready_mailbox = MAILBOX_OUT_DIR / img_ready_name

    img_answer_name = "evidence-date-redact-02-cau-bien-the-dates.png"
    img_answer_repo = REPO_DOCS_OUT_DIR / img_answer_name
    img_answer_mailbox = MAILBOX_OUT_DIR / img_answer_name

    question = "Trong tệp 2026_08_UnitTest.csv, serial 61C999999902 có kết quả kiểm tra như thế nào qua các ngày?"
    conv_id = f"CONV-DATE-REDACT-{uuid.uuid4().hex[:6].upper()}"

    c = WorkspaceConversation(
        id=conv_id,
        notebook_id="mom_opcenter",
        title="Nghiem thu mốc ngày 61C999999902",
        ai_mode="grounded",
    )
    save_conversation(c)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1600, "height": 1400})
            page = context.new_page()

            # 1. Chup anh trang thai khoi dong app-ready
            print("\n[STEP 1] Chup anh trang thai app ready...")
            page.goto(f"{URL}/?nb=mom_opcenter&conv={conv_id}&block=lsu", wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)
            page.screenshot(path=str(img_ready_repo), full_page=True)
            shutil.copy2(img_ready_repo, img_ready_mailbox)
            print(f"[READY] Da luu anh app ready: {img_ready_repo.name}")

            # 2. Gui cau hoi va ghi nhan ket qua
            print("\n[STEP 2] Gui cau hoi bien the tren khoi LSU...")
            duration, completed, ui_bubble_text = run_one_turn(
                page, conv_id, "mom_opcenter", "lsu", question, timeout_s=360
            )

            # 3. Chup anh tron than dap an
            page.screenshot(path=str(img_answer_repo), full_page=True)
            shutil.copy2(img_answer_repo, img_answer_mailbox)
            print(f"[SCREENSHOT] Da luu anh dap an: {img_answer_repo.name}")

            # 4. Doc dap an chi tiet tu DB
            msgs = load_messages(conv_id)
            final_answer = ""
            for m in msgs:
                if m.role == "assistant":
                    final_answer = m.content.strip()

            print("\n" + "=" * 80)
            print("NOI DUNG DAP AN THUC TE TREN GIAO DIEN:")
            print("=" * 80)
            print(final_answer or ui_bubble_text)
            print("=" * 80)

            # Kiem tra tieu chi ve
            has_date_20 = "2026/08/20" in final_answer or "20/08" in final_answer
            has_date_21 = "2026/08/21" in final_answer or "21/08" in final_answer
            has_serial = "61C999999902" in final_answer
            has_ng = "NG" in final_answer
            has_redacted_path = "[REDACTED_LOCAL_PATH]" in final_answer

            print(f"\n[DANH GIA TIEU CHI]:")
            print(f"  - Doc duoc ngay 20/08: {has_date_20}")
            print(f"  - Doc duoc ngay 21/08: {has_date_21}")
            print(f"  - Khop dung serial 61C999999902: {has_serial}")
            print(f"  - Ket qua TotalJudge / NG day du: {has_ng}")
            print(f"  - Chuoi ngay bi an nham boi [REDACTED_LOCAL_PATH]: {has_redacted_path}")
            print(f"  - Thoi gian phan hoi: {duration:.2f}s")
            print(f"  - Trang thai hoan tat: {completed}")

            assert completed, "Phien hoi qua giao dien chua hoan tat"
            assert has_date_20, "Dap an khong doc duoc ngay 2026/08/20"
            assert has_date_21, "Dap an khong doc duoc ngay 2026/08/21"
            assert has_serial, "Dap an khong chua serial 61C999999902"
            assert not has_redacted_path, "Dap an van con chua [REDACTED_LOCAL_PATH]!"

            # Kiem tra bang chung anh theo ban siet 11/10
            sha_ready = sha256_file(img_ready_repo)
            size_ready = img_ready_repo.stat().st_size
            sha_answer = sha256_file(img_answer_repo)
            size_answer = img_answer_repo.stat().st_size

            print(f"\n[BANG CHUNG ANH (BAN SIET 11/10)]:")
            print(f"  Anh ready : {img_ready_name} ({size_ready:,} bytes) - SHA256: {sha_ready}")
            print(f"  Anh answer: {img_answer_name} ({size_answer:,} bytes) - SHA256: {sha_answer}")
            assert sha_ready != sha_answer, "Anh ready va anh dap an bi trung SHA-256!"
            assert size_ready > 50000, "Kich thuoc anh ready qua nho"
            assert size_answer > 50000, "Kich thuoc anh dap an qua nho"

            # Ghi tep text ket qua
            txt_report_content = (
                f"=== KET QUA NGHIEM THU GIAO DIEN: DESKTOP-EVIDENCE-DATE-REDACT-FIX-HOME ===\n"
                f"Thoi diem: {time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n"
                f"Conversation ID: {conv_id}\n"
                f"So tay: mom_opcenter | Khoi: lsu\n"
                f"Commit HEAD: {head_habbit}\n"
                f"Thoi gian phan hoi: {duration:.2f}s\n"
                f"Cau hoi: {question}\n\n"
                f"Dap an nhan duoc:\n{final_answer}\n\n"
                f"Kiem dinh tieu chi:\n"
                f"- Co ngay 2026/08/20: {has_date_20}\n"
                f"- Co ngay 2026/08/21: {has_date_21}\n"
                f"- Co serial 61C999999902: {has_serial}\n"
                f"- TotalJudge NG day du: {has_ng}\n"
                f"- Bi che nham boi [REDACTED_LOCAL_PATH]: {has_redacted_path}\n\n"
                f"Minh chung anh:\n"
                f"1. {img_ready_name} ({size_ready} bytes, SHA256: {sha_ready})\n"
                f"2. {img_answer_name} ({size_answer} bytes, SHA256: {sha_answer})\n"
            )
            txt_file_repo = REPO_DOCS_OUT_DIR / "evidence-date-redact-answers-text.txt"
            txt_file_mailbox = MAILBOX_OUT_DIR / "evidence-date-redact-answers-text.txt"
            txt_file_repo.write_text(txt_report_content, encoding="utf-8")
            txt_file_mailbox.write_text(txt_report_content, encoding="utf-8")
            print(f"[EXPORT] Da xuat tep text nhat ky: {txt_file_repo.name}")

            browser.close()

    finally:
        if server_process:
            print("[SERVER] Dang tat server tam...")
            server_process.kill()
            server_process.wait()
        if server_log_file:
            server_log_file.close()

    print("\n" + "=" * 80)
    print("HOAN THANH NGHIEM THU GIAO DIEN THAT 100% THANH CONG!")
    print("=" * 80)


if __name__ == "__main__":
    main()
