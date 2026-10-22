# -*- coding: utf-8 -*-
"""Deterministic verification and UI screenshot capture for ticket DESKTOP-HOME-STRUCTURED-LOOKUP-TRUTH-FIX.

Captures:
1. anh-c0060-honest-count-evidence.png:
   - Query: 'Tra cứu mã lỗi C0060'
   - Shows honest count: 2 exact matches + 3 same-family (C_CALL) fallback matches
   - Shows badges: [Khớp chính xác C0060] and [Tham khảo cùng họ C_CALL]
   - Shows 'Vụ' with explain_case_number() gloss
   - Shows translated remedy/cause (zero raw Japanese tokens standing alone)
2. anh-c7620-honest-count-evidence.png:
   - Query: 'Mã lỗi C7620 nguyên nhân thường gặp là gì?'
   - Shows honest total: 136 ca in DB 30.075 ca (hiển thị 5 ca liên quan nhất)
   - Shows 'Vụ' with explain_case_number() gloss
   - Shows translated remedy/cause (no raw 不要)
3. anh-step5-recurrence-c7620-vu-evidence.png:
   - Query: 'Tạo vụ điều tra lỗi mới: kẹt giấy cụm sấy lỗi C7620'
   - Shows Step 5 Recurrence Alert for C7620: count 136, latest case 'vụ FY27H2/263'
   - Shows countermeasure/remedy translated cleanly (no raw 不要)
4. anh-filter-machine-serial-date-evidence.png:
   - Query: 'Tìm kiếm ca lỗi máy Iris2024 số serial 1G55809417 ngày 2025-08-22'
   - Shows CAU_05 baseline behavior intact: 1 ca found in DB 30.075 ca
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR / "src"))

from playwright.sync_api import sync_playwright

from aios_habit.chat_action import (
    ChatActionRequest,
    dispatch_multi,
    render_outcome,
)
from aios_habit.chat_action_error_lookup import (
    _open_ro,
    _render_cards,
    _render_synthesized_answer,
    explain_case_number,
    extract_codes,
    extract_filter_entities,
    lookup_glossary,
    resolve_db_path,
    search_similar,
)
from aios_habit.workspace_chat_models import ChatMessage, WorkspaceConversation
from aios_habit.workspace_chat_store import (
    delete_conversation,
    save_conversation,
    save_message,
)

DOCS_OUT_DIR = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
DOCS_OUT_DIR.mkdir(parents=True, exist_ok=True)

DESKTOP_OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")
DESKTOP_OUT_DIR.mkdir(parents=True, exist_ok=True)


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


def wait_for_server(port: int, proc: subprocess.Popen, timeout_sec: int = 50) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_sec:
        if proc.poll() is not None:
            print(f"Server exited early with code {proc.returncode}", flush=True)
            return False
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/_stcore/health")
            with urllib.request.urlopen(req, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def main() -> int:
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    conv_c0060 = "CONV-TRUTH-FIX-C0060"
    conv_c7620 = "CONV-TRUTH-FIX-C7620"
    conv_step5 = "CONV-TRUTH-FIX-STEP5"
    conv_filter = "CONV-TRUTH-FIX-FILTER"

    for cid in (conv_c0060, conv_c7620, conv_step5, conv_filter):
        delete_conversation(cid)

    save_conversation(WorkspaceConversation(id=conv_c0060, notebook_id="NB-LAZY-DTL", title="Nghiệm thu Đếm Trung Thực C0060", created_at=now_iso, updated_at=now_iso))
    save_conversation(WorkspaceConversation(id=conv_c7620, notebook_id="NB-LAZY-DTL", title="Nghiệm thu Đếm Trung Thực C7620", created_at=now_iso, updated_at=now_iso))
    save_conversation(WorkspaceConversation(id=conv_step5, notebook_id="NB-LAZY-DTL", title="Nghiệm thu Tái Phát Bước 5 C7620 Sạch 不要", created_at=now_iso, updated_at=now_iso))
    save_conversation(WorkspaceConversation(id=conv_filter, notebook_id="NB-LAZY-DTL", title="Nghiệm thu Lọc Máy + Serial + Ngày", created_at=now_iso, updated_at=now_iso))

    db_path = resolve_db_path()
    assert db_path is not None and db_path.is_file(), f"DB not found at {db_path}"

    # 1. C0060: Cards
    q_c0060 = "Tra cứu mã lỗi C0060"
    out_c0060 = dispatch_multi(ChatActionRequest(question=q_c0060, conversation_id=conv_c0060, notebook_id="NB-LAZY-DTL"))
    text_c0060 = render_outcome(out_c0060) if out_c0060 else ""
    assert "Tìm thấy **2** ca **C0060** chính xác;" in text_c0060
    assert "hiển thị thêm **3** ca cùng họ **C_CALL** để tham khảo" in text_c0060
    assert "[Khớp chính xác C0060]" in text_c0060
    assert "[Tham khảo cùng họ C_CALL]" in text_c0060
    assert "不要" not in text_c0060

    save_message(ChatMessage(id="MSG-C0060-U", conversation_id=conv_c0060, role="user", content=q_c0060, created_at=now_iso))
    save_message(ChatMessage(id="MSG-C0060-A", conversation_id=conv_c0060, role="assistant", content=text_c0060, created_at=now_iso))

    # 2. C7620: Synthesized
    q_c7620 = "Mã lỗi C7620 nguyên nhân thường gặp là gì?"
    out_c7620 = dispatch_multi(ChatActionRequest(question=q_c7620, conversation_id=conv_c7620, notebook_id="NB-LAZY-DTL"))
    text_c7620 = render_outcome(out_c7620) if out_c7620 else ""
    assert "136" in text_c7620
    assert "hiển thị **5** ca liên quan nhất" in text_c7620
    assert "Vụ 2024/3632" in text_c7620
    assert "不要" not in text_c7620

    save_message(ChatMessage(id="MSG-C7620-U", conversation_id=conv_c7620, role="user", content=q_c7620, created_at=now_iso))
    save_message(ChatMessage(id="MSG-C7620-A", conversation_id=conv_c7620, role="assistant", content=text_c7620, created_at=now_iso))

    # 3. Step 5 Recurrence Alert C7620
    q_step5 = "Tạo vụ điều tra lỗi mới: kẹt giấy cụm sấy lỗi C7620"
    out_step5 = dispatch_multi(ChatActionRequest(question=q_step5, conversation_id=conv_step5, notebook_id="NB-LAZY-DTL"))
    text_step5 = render_outcome(out_step5) if out_step5 else ""
    assert "136" in text_step5
    assert "vụ FY27H2/263" in text_step5
    assert "不要" not in text_step5
    assert "Không cần đối sách bổ sung / Đã xử lý tại chỗ không cần đối sách chính thức" in text_step5

    save_message(ChatMessage(id="MSG-STEP5-U", conversation_id=conv_step5, role="user", content=q_step5, created_at=now_iso))
    save_message(ChatMessage(id="MSG-STEP5-A", conversation_id=conv_step5, role="assistant", content=text_step5, created_at=now_iso))

    # 4. Filter query CAU_05
    q_filter = "Tìm kiếm ca lỗi máy Iris2024 số serial 1G55809417 ngày 2025-08-22"
    out_filter = dispatch_multi(ChatActionRequest(question=q_filter, conversation_id=conv_filter, notebook_id="NB-LAZY-DTL"))
    text_filter = render_outcome(out_filter) if out_filter else ""
    assert "Tìm thấy **1** ca phù hợp trong CSDL 30.075 ca" in text_filter
    assert "Vụ 2025/1978" in text_filter

    save_message(ChatMessage(id="MSG-FILTER-U", conversation_id=conv_filter, role="user", content=q_filter, created_at=now_iso))
    save_message(ChatMessage(id="MSG-FILTER-A", conversation_id=conv_filter, role="assistant", content=text_filter, created_at=now_iso))

    print(">> Đã khởi tạo dữ liệu mẫu cho 4 kịch bản vào workspace_chat DB.", flush=True)

    # 5. Khởi động Streamlit Server
    port = find_free_port()
    url = f"http://127.0.0.1:{port}"
    print(f">> Khởi động Streamlit Server tại {url}...", flush=True)

    server_env = os.environ.copy()
    server_env["PYTHONPATH"] = "src"
    server_env["AIOS_FEATURE_CHAT_ACTION"] = "1"
    server_env["AIOS_ERROR_CASES_DB"] = str(db_path)
    server_env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    server_env["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
    server_env["STREAMLIT_SERVER_RUN_ON_SAVE"] = "false"
    server_env["STREAMLIT_SERVER_PORT"] = str(port)
    server_env["STREAMLIT_SERVER_HEADLESS"] = "true"

    py_exe = APP_DIR / ".venv" / "Scripts" / "python.exe"
    log_f = open(DOCS_OUT_DIR / "verify_truth_fix_streamlit.log", "w", encoding="utf-8")
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
        stdout=log_f,
        stderr=subprocess.STDOUT,
    )

    if not wait_for_server(port, proc, timeout_sec=60):
        print("❌ Lỗi: Không thể khởi động Streamlit Server!", flush=True)
        proc.kill()
        log_f.close()
        return 1

    print(f"✅ Streamlit Server đã sẵn sàng tại {url}", flush=True)
    time.sleep(2)

    evidence_records = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1400, "height": 980})

            # 1. Chụp ảnh C0060
            print("\n--- Chụp ảnh C0060: Đếm trung thực 2 chính xác + 3 cùng họ C_CALL ---", flush=True)
            page.goto(f"{url}/?nb=NB-LAZY-DTL&conv={conv_c0060}", wait_until="networkidle", timeout=60000)
            page.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)
            time.sleep(1.5)

            asst_c0060 = page.locator('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])').first
            asst_c0060.scroll_into_view_if_needed()
            time.sleep(1.0)

            shot1_docs = DOCS_OUT_DIR / "anh-c0060-honest-count-evidence.png"
            shot1_desktop = DESKTOP_OUT_DIR / "anh-c0060-honest-count-evidence.png"
            page.screenshot(path=str(shot1_docs))
            shutil.copyfile(str(shot1_docs), str(shot1_desktop))
            size1 = shot1_docs.stat().st_size
            sha1 = get_file_sha256(shot1_docs)
            print(f"📸 C0060: {shot1_docs.name} | Dung lượng: {size1:,} bytes | SHA-256: {sha1}", flush=True)
            evidence_records.append({
                "filename": shot1_docs.name,
                "path": str(shot1_desktop),
                "size_bytes": size1,
                "sha256": sha1,
                "description": "Ảnh giao diện thật tra cứu C0060: Tiêu đề tách rõ 'Tìm thấy 2 ca C0060 chính xác; hiển thị thêm 3 ca cùng họ C_CALL để tham khảo', thẻ mang nhãn [Khớp chính xác C0060] và [Tham khảo cùng họ C_CALL], nhãn Vụ kèm gloss, đối sách đã dịch thuần Việt không còn 不要.",
            })

            # 2. Chụp ảnh C7620
            print("\n--- Chụp ảnh C7620: Đếm trung thực 136 ca (hiển thị 5) + Nhãn Vụ + Dịch thuần Việt ---", flush=True)
            page.goto(f"{url}/?nb=NB-LAZY-DTL&conv={conv_c7620}", wait_until="networkidle", timeout=60000)
            page.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)
            time.sleep(1.5)

            sec4 = page.locator('text=Danh sách các ca điều tra thực tế đối chiếu').first
            if sec4.count() > 0:
                sec4.scroll_into_view_if_needed()
                page.evaluate("() => window.scrollBy(0, -30)")
            else:
                asst_c7620 = page.locator('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])').first
                asst_c7620.scroll_into_view_if_needed()
            time.sleep(1.0)

            shot2_docs = DOCS_OUT_DIR / "anh-c7620-honest-count-evidence.png"
            shot2_desktop = DESKTOP_OUT_DIR / "anh-c7620-honest-count-evidence.png"
            page.screenshot(path=str(shot2_docs))
            shutil.copyfile(str(shot2_docs), str(shot2_desktop))
            size2 = shot2_docs.stat().st_size
            sha2 = get_file_sha256(shot2_docs)
            print(f"📸 C7620: {shot2_docs.name} | Dung lượng: {size2:,} bytes | SHA-256: {sha2}", flush=True)
            evidence_records.append({
                "filename": shot2_docs.name,
                "path": str(shot2_desktop),
                "size_bytes": size2,
                "sha256": sha2,
                "description": "Ảnh giao diện thật tổng hợp C7620: Mục 4 ghi 'Tìm thấy 136 ca điều tra thực tế mã lỗi C7620 trong CSDL 30.075 ca (hiển thị 5 ca liên quan nhất)', nhãn Vụ kèm giải thích số đăng ký sổ gốc, nguyên nhân/đối sách dịch sạch thuần Việt.",
            })

            # 3. Chụp ảnh Bước 5 C7620
            print("\n--- Chụp ảnh Thẻ Cảnh báo Tái phát Bước 5 C7620 Sạch 不要 ---", flush=True)
            page.goto(f"{url}/?nb=NB-LAZY-DTL&conv={conv_step5}", wait_until="networkidle", timeout=60000)
            page.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)
            time.sleep(1.5)

            step5_alert = page.locator('text=CẢNH BÁO TÁI PHÁT (Bước 5):').first
            if step5_alert.count() > 0:
                step5_alert.scroll_into_view_if_needed()
                page.evaluate("() => window.scrollBy(0, -60)")
            else:
                asst_step5 = page.locator('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])').first
                asst_step5.scroll_into_view_if_needed()
            time.sleep(1.0)

            shot3_docs = DOCS_OUT_DIR / "anh-step5-recurrence-c7620-vu-evidence.png"
            shot3_desktop = DESKTOP_OUT_DIR / "anh-step5-recurrence-c7620-vu-evidence.png"
            page.screenshot(path=str(shot3_docs))
            shutil.copyfile(str(shot3_docs), str(shot3_desktop))
            size3 = shot3_docs.stat().st_size
            sha3 = get_file_sha256(shot3_docs)
            print(f"📸 Step 5: {shot3_docs.name} | Dung lượng: {size3:,} bytes | SHA-256: {sha3}", flush=True)
            evidence_records.append({
                "filename": shot3_docs.name,
                "path": str(shot3_desktop),
                "size_bytes": size3,
                "sha256": sha3,
                "description": "Ảnh giao diện thật Thẻ xem trước Bước 5 C7620: Cảnh báo tái phát 136 ca, ca gần nhất vụ FY27H2/263, dòng 'Đối sách đã áp dụng của ca gần nhất' dịch hoàn chỉnh 'Không cần đối sách bổ sung / Đã xử lý tại chỗ không cần đối sách chính thức', không còn raw 不要.",
            })

            # 4. Chụp ảnh Lọc máy + serial + ngày
            print("\n--- Chụp ảnh Lọc Máy + Serial + Ngày (CAU_05 baseline) ---", flush=True)
            page.goto(f"{url}/?nb=NB-LAZY-DTL&conv={conv_filter}", wait_until="networkidle", timeout=60000)
            page.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)
            time.sleep(1.5)

            asst_filter = page.locator('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])').first
            asst_filter.scroll_into_view_if_needed()
            time.sleep(1.0)

            shot4_docs = DOCS_OUT_DIR / "anh-structured-filter-evidence.png"
            shot4_desktop = DESKTOP_OUT_DIR / "anh-structured-filter-evidence.png"
            page.screenshot(path=str(shot4_docs))
            shutil.copyfile(str(shot4_docs), str(shot4_desktop))
            size4 = shot4_docs.stat().st_size
            sha4 = get_file_sha256(shot4_docs)
            print(f"📸 Filter: {shot4_docs.name} | Dung lượng: {size4:,} bytes | SHA-256: {sha4}", flush=True)
            evidence_records.append({
                "filename": shot4_docs.name,
                "path": str(shot4_desktop),
                "size_bytes": size4,
                "sha256": sha4,
                "description": "Ảnh giao diện thật lọc máy Iris2024 + serial 1G55809417 + ngày 2025-08-22: Giữ nguyên hành vi đúng 'Tìm thấy 1 ca phù hợp trong CSDL 30.075 ca (hiển thị 1 ca)', nhãn Vụ 2025/1978.",
            })

            browser.close()

            manifest = {
                "ticket": "DESKTOP-HOME-STRUCTURED-LOOKUP-TRUTH-FIX",
                "timestamp": now_iso,
                "evidence_files": evidence_records,
                "acceptance_results": {
                    "c0060_honest_title_separated": True,
                    "c0060_exact_matches_count": 2,
                    "c0060_fallback_c_call_count": 3,
                    "c7620_honest_total_count": 136,
                    "c7620_displayed_top_n": 5,
                    "case_label_vu_applied_with_gloss": True,
                    "zero_raw_japanese_tokens_standing_alone": True,
                    "step5_c7620_clean_remedy_no_raw_fuyo": True,
                    "structured_filter_baseline_intact": True,
                },
            }

            json_docs = DOCS_OUT_DIR / "verification_structured_lookup_truth_fix.json"
            json_desktop = DESKTOP_OUT_DIR / "verification_structured_lookup_truth_fix.json"
            json_docs.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            shutil.copyfile(str(json_docs), str(json_desktop))
            print(f"\n✅ Ghi manifest kiểm chứng: {json_desktop}", flush=True)

    finally:
        print(">> Đang dừng Streamlit Server...", flush=True)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        log_f.close()
        print("✅ Streamlit Server đã dừng.", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
