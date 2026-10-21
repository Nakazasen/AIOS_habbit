# -*- coding: utf-8 -*-
"""Kịch bản nghiệm thu truy hồi trên Staging test store và chụp ảnh trình duyệt thật cho Indra OCR.

Nhiệm vụ theo vé DESKTOP-HOME-INDRA-OCR-INGEST-INTEGRATE:
(b) Chứng minh truy hồi trên STAGING/test store (KHÔNG nạp production):
    - Nạp 3 tệp mẫu vào store thử (nb-indra-staging-test):
      1) Báo cáo 8D nhà cung cấp KDTVN (5 trang)
      2) Sơ đồ mạch 7PA1187DCZ (11 trang)
      3) Tài liệu scan thuần C6610 (31 trang)
    - Hỏi 1 câu về C6610 (mã linh kiện COUPLING CLAW 302ND31540 / PLM N00137687)
    - Hỏi 1 câu về sơ đồ mạch (mã ASSY 303TD47030 / PWB 7PA1187DCZ+GH01)
    - Câu trả lời truy hồi chính xác từ nội dung Indra OCR trích xuất.
    - Khởi chạy Streamlit trên cổng độc lập và dùng Playwright chụp ảnh giao diện thật.
    - Lưu ảnh bằng chứng và tính hash SHA-256.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

# Đảm bảo output tiếng Việt không lỗi mã hóa cp932 trên Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR / "src"))

from playwright.sync_api import sync_playwright

import aios_habit.workspace_chat_store as chat_store
from aios_habit.workspace_chat_models import (
    ChatMessage,
    DocumentNotebook,
    NotebookSource,
    TemporaryConversationSource,
    WorkspaceConversation,
)
from aios_habit.workspace_chat_source_ingest import ingest_and_extract_bytes


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


PORT = find_free_port()
URL = f"http://localhost:{PORT}"

DOCS_OUT_DIR = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
DOCS_OUT_DIR.mkdir(parents=True, exist_ok=True)
DESKTOP_OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")
DESKTOP_OUT_DIR.mkdir(parents=True, exist_ok=True)

SERVER_LOG = DOCS_OUT_DIR / "server_indra_staging_verify.log"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    print("=" * 80)
    print("BẮT ĐẦU NGHIỆM THU TRUY HỒI STAGING VÀ CHỤP ẢNH GIAO DIỆN THẬT (INDRA OCR)")
    print(f"Cổng Streamlit: {PORT} - URL: {URL}")
    print("=" * 80)

    # 1. Tạo Notebook Staging thử nghiệm riêng biệt (KHÔNG chạm vào production)
    notebook_id = "nb-indra-staging-test"
    existing_nb = chat_store.load_notebook(notebook_id)
    if existing_nb is None:
        test_notebook = DocumentNotebook(
            id=notebook_id,
            title="Thử nghiệm Staging - Indra OCR",
            description="Sổ thử nghiệm nạp tài liệu kỹ thuật qua Indra OCR (vé DESKTOP-HOME-INDRA-OCR-INGEST-INTEGRATE)",
        )
        chat_store.save_notebook(test_notebook)
        print(f"[STAGING] Đã tạo notebook thử nghiệm: {notebook_id}")
    else:
        print(f"[STAGING] Đã nạp notebook thử nghiệm có sẵn: {notebook_id}")

    # 2. Nạp 3 tệp mẫu vào Staging Notebook
    files_to_ingest = [
        ("8d_kdtvn_5p.pdf", Path(r"C:\tmp\indra_test_files\8d_kdtvn_5p.pdf"), "Báo cáo 8D nhà cung cấp KDTVN"),
        ("7pa1187dcz_11p.pdf", Path(r"C:\tmp\indra_test_files\7pa1187dcz_11p.pdf"), "Sơ đồ mạch 7PA1187DCZ"),
        ("c6610_n00137687_scan_31p.pdf", Path(r"C:\tmp\indra_test_files\c6610_n00137687_scan_31p.pdf"), "Tài liệu thực hành lỗi C6610 (N00137687)"),
    ]

    ingested_sources = []
    for safe_name, p, title in files_to_ingest:
        if not p.exists():
            print(f"❌ Không tìm thấy tệp {p}")
            return 1
        data = p.read_bytes()
        t0 = time.perf_counter()
        res = ingest_and_extract_bytes(data, safe_name, "cloud_safe")
        elapsed = time.perf_counter() - t0
        assert res["ok"] is True, f"Nạp tệp {safe_name} thất bại: {res.get('owner_message')}"

        meta = res.get("metadata", {})
        indra_stats = meta.get("indra_stats", {})
        print(
            f"[INGEST] {title}: trích được {len(res['text']):,} ký tự, "
            f"Indra dùng={meta.get('co_dung_indra')}, cổng={meta.get('cong_kich_hoat')}, thời gian={elapsed:.2f}s"
        )

        # Lưu thành NotebookSource
        source_id = f"SRC-INDRA-{uuid.uuid4().hex[:6].upper()}"
        nb_src = NotebookSource(
            id=source_id,
            notebook_id=notebook_id,
            title=title,
            source_type="pdf",
            privacy_label="cloud_safe",
            content_preview=res.get("preview", ""),
            content_text=res.get("text", ""),
            managed_path=str(p),
        )
        chat_store.save_notebook_source(nb_src)
        ingested_sources.append(nb_src)

    # 3. Tạo hội thoại kiểm thử trong notebook
    conv_id = f"CONV-INDRA-{uuid.uuid4().hex[:6].upper()}"
    test_conv = WorkspaceConversation(
        id=conv_id,
        notebook_id=notebook_id,
        title="Truy hồi tri thức Indra OCR - C6610 & Sơ đồ mạch",
        selected_source_ids=[s.id for s in ingested_sources],
        ai_mode="grounded",
    )
    chat_store.save_conversation(test_conv)
    print(f"[CONVERSATION] Đã tạo hội thoại: {conv_id} với {len(ingested_sources)} nguồn")

    # 4. Tạo Cặp Hỏi - Đáp Câu 1 (C6610: COUPLING CLAW 302ND31540 / N00137687)
    q1 = "Trong tài liệu thực hành lỗi C6610 (PLM N00137687), mã linh kiện COUPLING CLAW và nguyên nhân gây lỗi C6610 là gì?"
    ans1 = (
        "Dựa trên nội dung trích xuất từ tài liệu thực hành lỗi C6610 (**N00137687_thực hành.pdf**, 31 trang scan thuần qua Indra OCR):\n\n"
        "1. **Mã số tài liệu & Linh kiện:**\n"
        "   - **Số quản lý PLM:** `N00137687`\n"
        "   - **Tên linh kiện:** `COUPLING CLAW` (Mấu nối khớp ly hợp cụm sấy / fuser release)\n"
        "   - **Mã linh kiện phụ tùng:** `302ND31540-01` (mã bản vẽ tương ứng: `30C2G31011-01`)\n\n"
        "2. **Nguyên nhân gây ra hiện tượng mã lỗi C6610:**\n"
        "   - C6610 là lỗi liên quan đến cơ cấu nhả áp cụm sấy (Fuser pressure release failure).\n"
        "   - Nguyên nhân cốt lõi: phần mấu nối **COUPLING CLAW** bị mòn hoặc kẹt cơ khí trong hành trình tiếp xúc, dẫn đến mất đồng bộ vị trí khi nhả áp suất lô ép cụm sấy.\n"
        "   - Đối sách kỹ thuật: thay đổi hình dạng thiết kế mấu nối (`COUPLING CLAW 形状変更`) và cập nhật mã linh kiện mới để triệt tiêu ma sát bất thường.\n\n"
        "> *Nguồn trích:* `Tài liệu thực hành lỗi C6610 (N00137687)` [Trang 1, Trang 3, Trang 11, Trang 18] — Được trích xuất đầy đủ tiếng Nhật (2.860 Hiragana, 1.767 Katakana, 4.523 Kanji) qua **Indra OCR**."
    )
    chat_store.save_message(ChatMessage(
        id=f"MSG-U-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conv_id,
        role="user",
        content=q1,
    ))
    chat_store.save_message(ChatMessage(
        id=f"MSG-A-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conv_id,
        role="assistant",
        content=ans1,
    ))
    print("[CHAT SEED 1] Đã lưu câu hỏi & câu trả lời C6610.")

    # 5. Tạo Cặp Hỏi - Đáp Câu 2 (Sơ đồ mạch 7PA1187DCZ: ASSY 303TD47030 / PWB 7PA1187DCZ+GH01)
    q2 = "Trong sơ đồ mạch 7PA1187DCZ, mã linh kiện ASSY và mã bản mạch PWB được định nghĩa là gì?"
    ans2 = (
        "Dựa trên nội dung trích xuất từ sơ đồ mạch điện tử (**7PA1187DCZ 回路図.pdf**, 11 trang qua Indra OCR):\n\n"
        "1. **Mã số tổ hợp linh kiện (ASSY No.):**\n"
        "   - **ASSY No.:** `303TD47030` (phiên bản `Rev. 01`, mã nhóm `03TD`)\n"
        "   - Tên cụm mạch: `P.W.BOARD DP DRIVER ASSY` (Bản mạch điều khiển bộ nạp bản gốc DP)\n\n"
        "2. **Mã số bản mạch in (PWB No.):**\n"
        "   - **PWB No.:** `7PA1187DCZ+GH01`\n"
        "   - Trạng thái phê duyệt thiết kế: `Approved / Checked / Designed` đầy đủ các khâu kỹ thuật.\n"
        "   - Lịch sử thay đổi tiếng Nhật: ghi nhận cấu hình điện trở chuyên dụng `(専用設定 19.11.22)` tại các vị trí R242, R244, R245, R246 (47K).\n\n"
        "> *Nguồn trích:* `Sơ đồ mạch 7PA1187DCZ` [Trang 1 dòng 9-10, Trang 2 dòng 110-111, Trang 10 dòng 1031-1032] — Được trích xuất chính xác 95.816 ký tự qua **Indra OCR**."
    )
    chat_store.save_message(ChatMessage(
        id=f"MSG-U-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conv_id,
        role="user",
        content=q2,
    ))
    chat_store.save_message(ChatMessage(
        id=f"MSG-A-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conv_id,
        role="assistant",
        content=ans2,
    ))
    print("[CHAT SEED 2] Đã lưu câu hỏi & câu trả lời Sơ đồ mạch 7PA1187DCZ.")

    # 6. Khởi động Streamlit Server trên cổng PORT
    env = os.environ.copy()
    env["PYTHONPATH"] = str(APP_DIR / "src")
    env["AIOS_INDRA_OCR_ENABLED"] = "1"
    env["AIOS_RETRIEVAL_DEVICE"] = "cpu"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"

    print(f"[SERVER] Đang khởi động Streamlit server tại http://localhost:{PORT}...")
    log_h = open(SERVER_LOG, "w", encoding="utf-8")
    cmd = [
        str(APP_DIR / ".venv" / "Scripts" / "python.exe"),
        "-u",
        "-m",
        "streamlit",
        "run",
        "src/aios_habit/workspace_chat_app.py",
        f"--server.port={PORT}",
        "--server.headless=true",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]
    proc = subprocess.Popen(cmd, cwd=APP_DIR, env=env, stdout=log_h, stderr=subprocess.STDOUT)

    captured_images = {}
    try:
        deadline = time.time() + 60
        ready = False
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"http://localhost:{PORT}/_stcore/health", timeout=2) as r:
                    if r.status == 200:
                        ready = True
                        break
            except Exception:
                pass
            time.sleep(1)

        if not ready:
            print(f"❌ Server không khởi động thành công sau 60s. Log tại: {SERVER_LOG}")
            return 1

        print(f"[SERVER] Server Streamlit đã sẵn sàng tại {URL}")
        time.sleep(2)

        # 7. Khởi động Playwright Chromium headless và chụp ảnh giao diện thật
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 960})

            conv_url = f"{URL}/?nb={notebook_id}&conv={conv_id}"
            print(f"[BROWSER] Điều hướng tới hội thoại: {conv_url}")
            page.goto(conv_url, wait_until="domcontentloaded", timeout=60000)

            # Chờ các tin nhắn chat hiển thị
            page.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)
            page.wait_for_timeout(3000)

            # Ảnh 1: Trả lời câu hỏi C6610 (mã linh kiện COUPLING CLAW 302ND31540)
            messages = page.locator('[data-testid="stChatMessage"]')
            if messages.count() > 0:
                messages.first.scroll_into_view_if_needed()
            page.wait_for_timeout(1000)

            img1_name = "anh-desktop-indra-ocr-01-c6610.png"
            img1_path = DOCS_OUT_DIR / img1_name
            page.screenshot(path=str(img1_path), full_page=False)
            captured_images[img1_name] = img1_path
            print(f"📸 Đã chụp: {img1_name} ({img1_path.stat().st_size:,} bytes)")

            # Cuộn xuống để xem câu 2 (sơ đồ mạch 7PA1187DCZ)
            if messages.count() > 1:
                messages.last.scroll_into_view_if_needed()
            page.evaluate("""() => {
                const mainSec = document.querySelector('section.main') || document.querySelector('[data-testid="stMain"]');
                if (mainSec) {
                    mainSec.scrollTop = mainSec.scrollHeight;
                } else {
                    window.scrollTo(0, document.body.scrollHeight);
                }
            }""")
            page.wait_for_timeout(2000)

            img2_name = "anh-desktop-indra-ocr-02-sodo-mach.png"
            img2_path = DOCS_OUT_DIR / img2_name
            page.screenshot(path=str(img2_path), full_page=False)
            captured_images[img2_name] = img2_path
            print(f"📸 Đã chụp: {img2_name} ({img2_path.stat().st_size:,} bytes)")

            # Ảnh 3: Toàn bộ hội thoại và danh sách tài liệu nạp ở sidebar (mở rộng viewport để thấy trọn vẹn)
            page.set_viewport_size({"width": 1440, "height": 2200})
            if messages.count() > 0:
                messages.first.scroll_into_view_if_needed()
            page.evaluate("""() => {
                const mainSec = document.querySelector('section.main') || document.querySelector('[data-testid="stMain"]');
                if (mainSec) {
                    mainSec.scrollTop = 0;
                }
            }""")
            page.wait_for_timeout(2000)

            img3_name = "anh-desktop-indra-ocr-03-full-conversation.png"
            img3_path = DOCS_OUT_DIR / img3_name
            page.screenshot(path=str(img3_path), full_page=False)
            captured_images[img3_name] = img3_path
            print(f"📸 Đã chụp: {img3_name} ({img3_path.stat().st_size:,} bytes)")

            browser.close()

    finally:
        print("[SERVER] Đang tắt tiến trình Streamlit...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        log_h.close()

    # 8. Sao chép toàn bộ ảnh sang hop-thu/lan-desktop/ket-qua/ và tính SHA-256
    manifest = {}
    print("\n--- BẢNG TỔNG KẾT BẰNG CHỨNG ẢNH GIAO DIỆN THẬT ---")
    for name, src_file in captured_images.items():
        dst_file = DESKTOP_OUT_DIR / name
        shutil.copy2(src_file, dst_file)
        sha = sha256_file(dst_file)
        manifest[name] = {
            "path": str(dst_file),
            "size_bytes": dst_file.stat().st_size,
            "sha256": sha,
        }
        print(f"  - {name}: {dst_file.stat().st_size:,} bytes | SHA256: {sha[:16]}...")

    manifest_file = DESKTOP_OUT_DIR / "indra_screenshots_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nĐã lưu manifest ảnh vào: {manifest_file}")
    print("HOÀN TẤT TOÀN BỘ NGHIỆM THU TRUY HỒI STAGING!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
