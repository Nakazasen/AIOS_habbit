# -*- coding: utf-8 -*-
"""Verification script for ticket DESKTOP-HOME-UX-EVIDENCE-PER-ANSWER.

Validates the full live UI acceptance flow:
1. Starts an isolated Streamlit instance on an ephemeral port.
2. Creates a fresh conversation with 5 consecutive Q&A turns, each having distinct sources and evidence traces.
3. Uses Playwright to load http://127.0.0.1:{port}/?nb=NB-LAZY-DTL&conv=<conv_id>.
4. Selects the conversation via sidebar button.
5. (Gate 1) Scrolls to Question 1: opens its in-place evidence block, verifies Answer 1's sources, clicks open source file.
   Takes Screenshot 1: anh-ev-01-cau1-evidence-in-place.png
6. (Gate 2) Scrolls down to Question 5: opens its in-place evidence block, verifies Answer 5's distinct sources.
   Takes Screenshot 2: anh-ev-02-cau5-evidence-in-place.png
7. (Gate 3) Inspects page footer: verifies NO centralized "📌 Kết quả & bằng chứng" expander is rendered at footer.
   Takes Screenshot 3: anh-ev-03-footer-no-centralized-expander.png
8. (Gate 4) Reloads the conversation: verifies per-answer evidence still opens in-place on reloaded history.
   Takes Screenshot 4: anh-ev-04-reloaded-saved-conversation.png
9. Calculates file bytes and SHA-256 checksums from the saved images.
10. Shuts down the Streamlit instance cleanly.
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
from typing import Any
import urllib.request
import uuid

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

os.environ["AIOS_RAGV2_WORKER_PERSIST"] = "1"
os.environ["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["AIOS_RETRIEVAL_DEVICE"] = "cpu"

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR / "src"))

from playwright.sync_api import sync_playwright

from aios_habit.workspace_chat_models import (
    WorkspaceConversation,
    ChatMessage,
)
from aios_habit.evidence_trace_schema import EvidenceTrace
from aios_habit.workspace_chat_store import (
    save_conversation,
    save_message,
    save_evidence_trace,
    clear_store_cache,
)

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


def setup_fresh_5_turns_conversation() -> tuple[str, str, str]:
    uid = uuid.uuid4().hex[:8].upper()
    conv_id = f"CONV-EV5Q-{uid}"
    title = f"NghiemThuBCC-{uid}"
    nb_id = "NB-LAZY-DTL"

    conv = WorkspaceConversation(
        id=conv_id,
        notebook_id=nb_id,
        title=title,
        created_at=datetime.datetime.now().isoformat(),
        updated_at=datetime.datetime.now().isoformat(),
    )
    save_conversation(conv)

    turns_data = [
        {
            "idx": 1,
            "q": "C6770 nguyên nhân thường gặp là gì?",
            "a": (
                "Mã lỗi **C6770**: Lỗi nguồn điện thấp Fuser IH.\n"
                "Cơ chế phát sinh: Sau khi bắt đầu gia nhiệt Fuser, nguồn cấp IH không đạt mức yêu cầu.\n\n"
                "- **Báo cáo gốc:** `Loi KDTPS.xlsx › History KDTPS › dòng 9609`\n"
                "- **Tài liệu tham chiếu:** `02XC_自己診断表示一覧表-Iris2020 VN.xls`"
            ),
            "trace_id": f"trc_5q_{uid}_01",
            "evidence": [
                {
                    "title": "Loi KDTPS.xlsx",
                    "text": "Vụ 2025/1155 (Iris2024 Mono / C33): Panel画面 An Error has occurred表示",
                    "location_info": "History KDTPS › dòng 9609",
                    "source_row": 9609,
                    "source_type": "db_error_case",
                },
                {
                    "title": "02XC_自己診断表示一覧表-Iris2020 VN.xls",
                    "text": "Mã C6770: Lỗi nguồn điện thấp Fuser IH",
                    "location_info": "Sheet 1 › Mục C_CALL",
                    "source_type": "glossary_document",
                },
            ],
        },
        {
            "idx": 2,
            "q": "C7620 liên quan đến cụm nào?",
            "a": (
                "Mã lỗi **C7620**: Lỗi nâng hạ khay nạp giấy 3.\n"
                "Nguyên nhân: Cảm biến vị trí giới hạn khay 3 không đổi trạng thái khi nâng hạ.\n\n"
                "- **Báo cáo gốc:** `Loi KDTPS.xlsx › History KDTPS › dòng 10530`"
            ),
            "trace_id": f"trc_5q_{uid}_02",
            "evidence": [
                {
                    "title": "Loi KDTPS.xlsx",
                    "text": "Vụ 2025/2076 (Iris2024 上位 / C33): LCC画面にAn Error has ocurred表示",
                    "location_info": "History KDTPS › dòng 10530",
                    "source_row": 10530,
                    "source_type": "db_error_case",
                },
            ],
        },
        {
            "idx": 3,
            "q": "C2152 phát sinh khi nào?",
            "a": (
                "Mã lỗi **C2152**: Lỗi động cơ chuyển làn trung gian.\n"
                "Hiện tượng: Động cơ chuyển làn M12 không quay đúng chu kỳ.\n\n"
                "- **Báo cáo gốc:** `Loi KDTPS.xlsx › History KDTPS › dòng 9918`"
            ),
            "trace_id": f"trc_5q_{uid}_03",
            "evidence": [
                {
                    "title": "Loi KDTPS.xlsx",
                    "text": "Vụ 2025/1464 (Iris2024 Mono / C33): LK phát sinh sử dụng lot tháng 6",
                    "location_info": "History KDTPS › dòng 9918",
                    "source_row": 9918,
                    "source_type": "db_error_case",
                },
            ],
        },
        {
            "idx": 4,
            "q": "Quy trình vệ sinh cụm sấy định kỳ như thế nào?",
            "a": (
                "Quy trình vệ sinh cụm sấy:\n"
                "1. Tắt công tắc nguồn phụ và rút phích cắm.\n"
                "2. Chờ 15 phút để bộ sấy nguội hoàn toàn.\n"
                "3. Dùng khăn mềm làm sạch trục sấy.\n\n"
                "- **Báo cáo gốc:** `Loi KDTPS.xlsx › History KDTPS › dòng 9918`\n"
                "- **Tài liệu tham chiếu:** `02XC_自己診断表示一覧表-Iris2020 VN.xls`"
            ),
            "trace_id": f"trc_5q_{uid}_04",
            "evidence": [
                {
                    "title": "quy_trinh_bao_tri_may_in.pdf",
                    "text": "Thao tác vệ sinh sấy cần thực hiện sau khi tắt nguồn 15 phút để tránh bỏng nhiệt.",
                    "location_info": "Trang 12 › Mục 3.1",
                    "source_type": "library_document",
                },
            ],
        },
        {
            "idx": 5,
            "q": "C6400 biện pháp xử lý tức thì là gì?",
            "a": (
                "Mã lỗi **C6400**: Sự cố điện áp cao sấy.\n"
                "Biện pháp xử lý tức thì:\n"
                "- Kiểm tra điện áp cấp nguồn và cầu chì nhiệt.\n"
                "- Ngắt kết nối bo mạch nguồn cao áp trước khi kiểm tra linh kiện.\n\n"
                "- **Báo cáo gốc:** `Loi KDTPS.xlsx › History KDTPS › dòng 9609`"
            ),
            "trace_id": f"trc_5q_{uid}_05",
            "evidence": [
                {
                    "title": "Loi KDTPS.xlsx",
                    "text": "Vụ 2025/0842: Điện áp vượt ngưỡng cho phép 240V",
                    "location_info": "History KDTPS › dòng 9609",
                    "source_row": 9609,
                    "source_type": "db_error_case",
                },
                {
                    "title": "huong_dan_an_toan_dien.docx",
                    "text": "Ngắt nguồn ngay khi có cảnh báo điện áp cao sấy để bảo vệ cụm sấy và bo mạch.",
                    "location_info": "Mục 4.2",
                    "source_type": "library_document",
                },
            ],
        },
    ]

    base_time = datetime.datetime.now() - datetime.timedelta(minutes=10)
    for t in turns_data:
        u_msg_id = f"MSG-U-{uid}-{t['idx']:02d}"
        a_msg_id = f"MSG-A-{uid}-{t['idx']:02d}"
        t_user = (base_time + datetime.timedelta(minutes=t["idx"] * 2)).isoformat()
        t_asst = (base_time + datetime.timedelta(minutes=t["idx"] * 2, seconds=10)).isoformat()

        u_msg = ChatMessage(
            id=u_msg_id,
            conversation_id=conv_id,
            role="user",
            content=t["q"],
            created_at=t_user,
        )
        save_message(u_msg)

        trace = EvidenceTrace(
            trace_id=t["trace_id"],
            notebook_id=nb_id,
            conversation_id=conv_id,
            user_message_id=u_msg_id,
            assistant_message_id=a_msg_id,
            query=t["q"],
            answer_text=t["a"],
            metadata={"evidence_items": t["evidence"]},
        )
        save_evidence_trace(trace)

        a_msg = ChatMessage(
            id=a_msg_id,
            conversation_id=conv_id,
            role="assistant",
            content=t["a"],
            trace_id=t["trace_id"],
            reply_to_message_id=u_msg_id,
            created_at=t_asst,
        )
        save_message(a_msg)

    clear_store_cache()
    print(f"[+] Prepared fresh conversation '{conv_id}' ('{title}') with 5 turns & distinct evidence traces!", flush=True)
    return conv_id, nb_id, title


def run_verification() -> int:
    port = find_free_port()
    url = f"http://127.0.0.1:{port}"
    print(f"[*] Starting Streamlit on port {port}...", flush=True)

    server_env = os.environ.copy()
    server_env["PYTHONPATH"] = "src"
    server_env["PYTHONIOENCODING"] = "utf-8"
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
    log_path = APP_DIR / "local_cases" / f"st_verify_{port}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
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
        print("[*] Waiting for Streamlit server to respond...", flush=True)
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
            print("[-] Streamlit server failed to start in 45s", flush=True)
            return 1
        print("[+] Streamlit server is UP and healthy!", flush=True)

        conv_id, nb_id, conv_title = setup_fresh_5_turns_conversation()

        results: dict[str, Any] = {
            "ma_ve": "DESKTOP-HOME-UX-EVIDENCE-PER-ANSWER",
            "status": "RUNNING",
            "started_at": datetime.datetime.now().isoformat(),
            "conversation_id": conv_id,
            "notebook_id": nb_id,
            "gates": {},
        }

        target_url = f"{url}/?nb={nb_id}&conv={conv_id}"
        print(f"[*] Connecting to Streamlit at {target_url}...", flush=True)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1080})
            page = context.new_page()

            page.goto(target_url, wait_until="load")
            time.sleep(3)

            # Ensure our conversation is selected
            print(f"[*] Ensuring conversation '{conv_id}' is selected...", flush=True)
            btn_selector = f'button:has-text("{conv_title}"), div[class*="select_conv_{conv_id}"] button, button:has-text("{conv_id}")'
            conv_btn = page.locator(btn_selector).first
            if conv_btn.count() > 0:
                print(f"[+] Found sidebar button for '{conv_title}', clicking...", flush=True)
                conv_btn.scroll_into_view_if_needed()
                conv_btn.click()
                time.sleep(3)
            else:
                print(f"[-] Button not found with selector: {btn_selector}, current URL: {page.url}", flush=True)

            # Wait for chat bubbles
            page.wait_for_selector('div[data-testid="stChatMessage"]', timeout=80000)
            chat_bubbles = page.locator('div[data-testid="stChatMessage"]')
            bubble_count = chat_bubbles.count()
            print(f"[+] Found {bubble_count} chat messages on page!", flush=True)
            for b_idx in range(bubble_count):
                b_text = chat_bubbles.nth(b_idx).inner_text().replace("\n", " ")[:60]
                print(f"    Bubble {b_idx}: {b_text}", flush=True)

            # -------------------------------------------------------------
            # Gate 1: Question 1 in-place evidence & source viewer
            # -------------------------------------------------------------
            print("\n=== GATE 1: Question 1 In-Place Evidence Verification ===", flush=True)
            a1_bubble = chat_bubbles.filter(has_text="Mã lỗi C6770").first
            a1_bubble.scroll_into_view_if_needed()
            time.sleep(1)

            ev1_expander = a1_bubble.locator('[data-testid="stExpander"]').first
            print("[*] Expanding evidence block under Answer 1...", flush=True)
            ev1_expander.scroll_into_view_if_needed()
            time.sleep(0.5)
            sum1 = ev1_expander.locator("summary").first
            if sum1.count() > 0:
                sum1.click()
            else:
                ev1_expander.click()
            time.sleep(2)

            a1_sources_text = ev1_expander.inner_text()
            print(f"[+] Answer 1 Evidence text: {a1_sources_text[:120]}...", flush=True)
            assert "Loi KDTPS.xlsx" in a1_sources_text or "9609" in a1_sources_text, "Missing Loi KDTPS in Q1 evidence"
            assert "02XC_" in a1_sources_text, "Missing 02XC_ in Q1 evidence"

            # Click source opener button
            open_src_btn_1 = ev1_expander.locator('button:has-text("02XC_"), button:has-text("Mở tệp nguồn"), button:has-text("Mở nguồn")').first
            if open_src_btn_1.count() > 0:
                print("[*] Clicking source opener button for 02XC_...", flush=True)
                open_src_btn_1.scroll_into_view_if_needed()
                open_src_btn_1.click()
                time.sleep(3)

            # Re-locate a1_bubble and ensure in-place evidence is visible in viewport
            a1_bubble = page.locator('div[data-testid="stChatMessage"]').filter(has_text="Mã lỗi C6770").first
            a1_bubble.scroll_into_view_if_needed()
            time.sleep(1)

            # Capture Screenshot 1
            img1_name = "anh-ev-01-cau1-evidence-in-place.png"
            p1_local = OUT_DIR_LOCAL / img1_name
            p1_desk = OUT_DIR_DESKTOP / img1_name
            page.screenshot(path=str(p1_local), full_page=False)
            p1_desk.write_bytes(p1_local.read_bytes())
            sha1 = get_file_sha256(p1_local)
            bytes1 = p1_local.stat().st_size
            print(f"[+] Screenshot 1 saved: {img1_name} ({bytes1} bytes, SHA-256: {sha1})", flush=True)
            results["gates"]["gate1_q1_evidence"] = {
                "passed": True,
                "screenshot": img1_name,
                "bytes": bytes1,
                "sha256": sha1,
            }

            # -------------------------------------------------------------
            # Gate 2: Question 5 in-place evidence & distinct sources
            # -------------------------------------------------------------
            print("\n=== GATE 2: Question 5 In-Place Evidence Verification ===", flush=True)
            a5_bubble = page.locator('div[data-testid="stChatMessage"]').filter(has_text="Mã lỗi C6400").first
            a5_bubble.scroll_into_view_if_needed()
            time.sleep(1)

            ev5_expander = a5_bubble.locator('[data-testid="stExpander"]').first
            print("[*] Expanding evidence block under Answer 5...", flush=True)
            ev5_expander.scroll_into_view_if_needed()
            time.sleep(0.5)
            sum5 = ev5_expander.locator("summary").first
            if sum5.count() > 0:
                sum5.click()
            else:
                ev5_expander.click()
            time.sleep(2)

            a5_sources_text = ev5_expander.inner_text()
            print(f"[+] Answer 5 Evidence text: {a5_sources_text[:120]}...", flush=True)
            assert "huong_dan_an_toan_dien.docx" in a5_sources_text or "9609" in a5_sources_text, "Missing Q5 sources"
            # Ensure zero leakage from Answer 1
            assert "02XC_" not in a5_sources_text, "Leakage detected: 02XC_ from Q1 found in Q5!"

            # Capture Screenshot 2
            img2_name = "anh-ev-02-cau5-evidence-in-place.png"
            p2_local = OUT_DIR_LOCAL / img2_name
            p2_desk = OUT_DIR_DESKTOP / img2_name
            page.screenshot(path=str(p2_local), full_page=False)
            p2_desk.write_bytes(p2_local.read_bytes())
            sha2 = get_file_sha256(p2_local)
            bytes2 = p2_local.stat().st_size
            print(f"[+] Screenshot 2 saved: {img2_name} ({bytes2} bytes, SHA-256: {sha2})", flush=True)
            results["gates"]["gate2_q5_evidence"] = {
                "passed": True,
                "screenshot": img2_name,
                "bytes": bytes2,
                "sha256": sha2,
            }

            # -------------------------------------------------------------
            # Gate 3: Footer Check - No Centralized Expander
            # -------------------------------------------------------------
            print("\n=== GATE 3: Page Footer Expander Removal Verification ===", flush=True)
            composer_el = page.locator('div[data-testid="stChatInput"], textarea, .wsc-composer-card').first
            if composer_el.count() > 0:
                composer_el.scroll_into_view_if_needed()
            else:
                page.evaluate("const el = document.querySelector('section.main') || document.documentElement; el.scrollTop = el.scrollHeight; window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)

            centralized_footer_expander = page.locator('div[data-testid="stExpander"]:has-text("Kết quả & bằng chứng")')
            footer_has_centralized = centralized_footer_expander.count() > 0
            print(f"[*] Centralized footer expander found count: {centralized_footer_expander.count()}", flush=True)
            assert not footer_has_centralized, "Found centralized 'Kết quả & bằng chứng' expander at footer! Must be removed."

            # Capture Screenshot 3
            img3_name = "anh-ev-03-footer-no-centralized-expander.png"
            p3_local = OUT_DIR_LOCAL / img3_name
            p3_desk = OUT_DIR_DESKTOP / img3_name
            page.screenshot(path=str(p3_local), full_page=False)
            p3_desk.write_bytes(p3_local.read_bytes())
            sha3 = get_file_sha256(p3_local)
            bytes3 = p3_local.stat().st_size
            print(f"[+] Screenshot 3 saved: {img3_name} ({bytes3} bytes, SHA-256: {sha3})", flush=True)
            results["gates"]["gate3_footer_no_centralized"] = {
                "passed": True,
                "screenshot": img3_name,
                "bytes": bytes3,
                "sha256": sha3,
            }

            # -------------------------------------------------------------
            # Gate 4: Reload Saved Conversation Verification
            # -------------------------------------------------------------
            print("\n=== GATE 4: Reload Saved Conversation Verification ===", flush=True)
            page.reload(wait_until="load")
            time.sleep(3)

            conv_btn_reload = page.locator(btn_selector).first
            if conv_btn_reload.count() > 0:
                conv_btn_reload.scroll_into_view_if_needed()
                conv_btn_reload.click()
                time.sleep(3)

            a1_reloaded = page.locator('div[data-testid="stChatMessage"]').filter(has_text="Mã lỗi C6770").first
            a1_reloaded.scroll_into_view_if_needed()
            time.sleep(1)
            ev1_reloaded = a1_reloaded.locator('[data-testid="stExpander"]').first
            ev1_reloaded.scroll_into_view_if_needed()
            time.sleep(0.5)
            sum_rel = ev1_reloaded.locator("summary").first
            if sum_rel.count() > 0:
                sum_rel.click()
            else:
                ev1_reloaded.click()
            time.sleep(1.5)

            reloaded_text = ev1_reloaded.inner_text()
            print(f"[+] Reloaded conversation Answer 1 evidence: {reloaded_text[:120]}...", flush=True)
            assert "Loi KDTPS.xlsx" in reloaded_text or "9609" in reloaded_text, "Failed to find sources on reloaded conversation"

            # Capture Screenshot 4
            img4_name = "anh-ev-04-reloaded-saved-conversation.png"
            p4_local = OUT_DIR_LOCAL / img4_name
            p4_desk = OUT_DIR_DESKTOP / img4_name
            page.screenshot(path=str(p4_local), full_page=False)
            p4_desk.write_bytes(p4_local.read_bytes())
            sha4 = get_file_sha256(p4_local)
            bytes4 = p4_local.stat().st_size
            print(f"[+] Screenshot 4 saved: {img4_name} ({bytes4} bytes, SHA-256: {sha4})", flush=True)
            results["gates"]["gate4_reloaded_saved_conv"] = {
                "passed": True,
                "screenshot": img4_name,
                "bytes": bytes4,
                "sha256": sha4,
            }

            browser.close()

        results["status"] = "PASSED"
        results["completed_at"] = datetime.datetime.now().isoformat()

        # Save manifests
        manifest_path_desk = OUT_DIR_DESKTOP / "ket-qua-do-evidence-per-answer.json"
        manifest_path_local = OUT_DIR_LOCAL / "ket-qua-do-evidence-per-answer.json"
        data_json = json.dumps(results, indent=2, ensure_ascii=False)
        manifest_path_desk.write_text(data_json, encoding="utf-8")
        manifest_path_local.write_text(data_json, encoding="utf-8")
        print(f"\n[+] Acceptance manifest saved: {manifest_path_desk}", flush=True)
        return 0

    finally:
        print("[*] Terminating Streamlit subprocess...", flush=True)
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
        print("[+] Streamlit subprocess terminated.", flush=True)


if __name__ == "__main__":
    sys.exit(run_verification())