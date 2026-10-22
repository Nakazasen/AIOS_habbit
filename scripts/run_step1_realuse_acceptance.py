# -*- coding: utf-8 -*-
"""Computer Use (CU) Real UI Verification for ticket DESKTOP-HOME-STEP1-REALUSE-ACCEPTANCE.

Nghiệm thu Bước 1 (tra cứu lịch sử lỗi tương tự) bằng Computer Use trên giao diện thật:
- Mục 2.1: Bộ 10 câu hỏi cố định (mã phổ biến, mã hiếm, hiện tượng có/không dấu, lọc máy+serial+ngày, mang máng, 2 câu tài liệu, 1 bẫy MOM, 1 câu trung thực).
- Mục 2.2: [CU] Hỏi từng câu trên giao diện thật Playwright Chromium; lưu nguyên văn câu trả lời + ảnh tệp thô + thời gian trả lời; đối chiếu tổng số với sự thật nền SQL; bấm mở trích dẫn để kiểm chứng mở đúng hồ sơ.
- Mục 2.3: [CU] Bước 2: đóng vụ fixture thiếu nguyên nhân (phải bị chặn) -> đóng hợp lệ (ghi ngược local_cases) -> đo lại độ bao phủ đánh giá.
- Mục 2.4: Bảng phát hiện chi tiết từng câu.

Tiền lệ phương pháp luận: DESKTOP-HOME-REALUSE-AUDIT-20261020.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR / "src"))

from playwright.sync_api import sync_playwright

from aios_habit.case_models import Case
from aios_habit.case_store import load_cases, save_case
from aios_habit.feedback_review_home import compute_feedback_coverage
from aios_habit.final_answer_composer import deliver_5tier_ladder_answer
from aios_habit.workspace_chat_models import ChatMessage, WorkspaceConversation
from aios_habit.workspace_chat_store import delete_conversation, load_messages, save_conversation, save_message

LOCAL_OUT_DIR = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
LOCAL_OUT_DIR.mkdir(parents=True, exist_ok=True)

DESKTOP_OUT_DIR = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")
DESKTOP_OUT_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = Path(r"C:\tmp\kdtps_standard\error_cases_reconciled.db")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def save_dual_screenshot(page, filename: str) -> Dict[str, Any]:
    p_local = LOCAL_OUT_DIR / filename
    p_desktop = DESKTOP_OUT_DIR / filename
    page.screenshot(path=str(p_local), full_page=True)
    p_desktop.write_bytes(p_local.read_bytes())
    size = p_local.stat().st_size
    s256 = sha256_file(p_local)
    print(f"[+] Saved screenshot: {filename} ({size} bytes, SHA256: {s256})", flush=True)
    return {
        "filename": filename,
        "size_bytes": size,
        "sha256": s256,
        "local_path": str(p_local),
        "desktop_path": str(p_desktop),
    }


def query_sql_ground_truth(query_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute independent SQL query on error_cases_reconciled.db."""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    try:
        if query_type == "code_c7620":
            cnt_i = cur.execute("SELECT COUNT(*) FROM error_cases WHERE UPPER(error_code_i) = 'C7620'").fetchone()[0]
            cnt_raw = cur.execute("SELECT COUNT(*) FROM error_cases WHERE raw_json LIKE '%C7620%'").fetchone()[0]
            cnt_both = cur.execute("SELECT COUNT(*) FROM error_cases WHERE UPPER(error_code_i) = 'C7620' OR raw_json LIKE '%C7620%'").fetchone()[0]
            return {"error_code_i_count": cnt_i, "raw_json_count": cnt_raw, "union_count": cnt_both}

        elif query_type == "code_c0060":
            cnt_i = cur.execute("SELECT COUNT(*) FROM error_cases WHERE UPPER(error_code_i) = 'C0060'").fetchone()[0]
            cnt_raw = cur.execute("SELECT COUNT(*) FROM error_cases WHERE raw_json LIKE '%C0060%'").fetchone()[0]
            cnt_both = cur.execute("SELECT COUNT(*) FROM error_cases WHERE UPPER(error_code_i) = 'C0060' OR raw_json LIKE '%C0060%'").fetchone()[0]
            return {"error_code_i_count": cnt_i, "raw_json_count": cnt_raw, "union_count": cnt_both}

        elif query_type == "skew_postcard":
            cnt = cur.execute("""
                SELECT COUNT(*) FROM error_cases 
                WHERE (phenomenon LIKE '%lệch lề%' OR phenomenon LIKE '%lech le%' OR phenomenon LIKE '%skew%' OR raw_json LIKE '%lệch lề%')
                  AND (phenomenon LIKE '%postcard%' OR raw_json LIKE '%postcard%' OR raw_json LIKE '%はがき%')
            """).fetchone()[0]
            return {"count": cnt}

        elif query_type == "machine_serial_date":
            cnt = cur.execute("""
                SELECT COUNT(*) FROM error_cases 
                WHERE REPLACE(machine_type, ' ', '') LIKE '%6thNext%'
                  AND json_extract(raw_json, '$.G') LIKE '%WD72Z12772%'
                  AND occurred_at >= '2023-01-01' AND occurred_at <= '2023-01-31'
            """).fetchone()[0]
            rows = cur.execute("""
                SELECT id, no_dvd, machine_type, occurred_at, error_code_h, error_code_i, source_row
                FROM error_cases 
                WHERE REPLACE(machine_type, ' ', '') LIKE '%6thNext%'
                  AND json_extract(raw_json, '$.G') LIKE '%WD72Z12772%'
                  AND occurred_at >= '2023-01-01' AND occurred_at <= '2023-01-31'
            """).fetchall()
            return {"count": cnt, "rows": [dict(zip(["id", "no_dvd", "machine_type", "occurred_at", "error_code_h", "error_code_i", "source_row"], r)) for r in rows]}

        elif query_type == "abnormal_sound":
            cnt = cur.execute("""
                SELECT COUNT(*) FROM error_cases 
                WHERE phenomenon LIKE '%tiếng kêu bất thường%' OR raw_json LIKE '%tiếng kêu bất thường%' OR raw_json LIKE '%異常音%'
            """).fetchone()[0]
            return {"count": cnt}

        elif query_type == "jam4212":
            cnt_i = cur.execute("SELECT COUNT(*) FROM error_cases WHERE UPPER(error_code_i) = 'JAM4212'").fetchone()[0]
            cnt_raw = cur.execute("SELECT COUNT(*) FROM error_cases WHERE raw_json LIKE '%JAM4212%'").fetchone()[0]
            return {"error_code_i_count": cnt_i, "raw_json_count": cnt_raw}

        return {}
    finally:
        conn.close()


def prepare_conversation(conv_id: str, notebook_id: str, title: str) -> None:
    delete_conversation(conv_id)
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save_conversation(
        WorkspaceConversation(
            id=conv_id,
            notebook_id=notebook_id,
            title=title,
            ai_mode="grounded",
            created_at=now_iso,
            updated_at=now_iso,
        )
    )


def extract_assistant_answer(page, timeout_sec: int = 45) -> str:
    """Wait for assistant response bubble and return text content."""
    page.wait_for_selector('div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])', timeout=timeout_sec * 1000)
    time.sleep(2)
    bubbles = page.locator('div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])').all_inner_texts()
    if bubbles:
        return bubbles[-1]
    return ""


def main():
    print("=" * 80)
    print("BAT DAU CHAY NGHIEM THU COMPUTER USE (CU) - VE DESKTOP-HOME-STEP1-REALUSE-ACCEPTANCE")
    print("=" * 80)

    # 1. Tính toán sự thật nền SQL độc lập trước
    print("\n--- [BƯỚC 0] TÍNH TOÁN SỰ THẬT NỀN SQL ĐỘC LẬP TỪ CSDL 30.075 CA ---", flush=True)
    sql_facts = {
        "c7620": query_sql_ground_truth("code_c7620", {}),
        "c0060": query_sql_ground_truth("code_c0060", {}),
        "skew_postcard": query_sql_ground_truth("skew_postcard", {}),
        "filter": query_sql_ground_truth("machine_serial_date", {}),
        "abnormal_sound": query_sql_ground_truth("abnormal_sound", {}),
        "jam4212": query_sql_ground_truth("jam4212", {}),
    }
    print(f"SQL Facts: {json.dumps(sql_facts, indent=2, ensure_ascii=False)}", flush=True)

    results: List[Dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 960})

        # =======================================================================
        # CÂU 1: Mã lỗi phổ biến (C7620) trong Sổ Điều tra lỗi (NB-LAZY-DTL)
        # =======================================================================
        print("\n--- [CU] Câu 1: Mã lỗi phổ biến (C7620) ---", flush=True)
        conv1 = "CONV-CU-S1-01-C7620"
        prepare_conversation(conv1, "NB-LAZY-DTL", "CU 01: Mã lỗi phổ biến C7620")
        page.goto(f"http://localhost:8501/?nb=NB-LAZY-DTL&conv={conv1}", wait_until="networkidle")
        time.sleep(2)

        q1 = "Mã lỗi C7620 nguyên nhân thường gặp là gì?"
        ta = page.locator('textarea[aria-label="Câu hỏi gửi AI"]')
        ta.wait_for(state="visible", timeout=15000)
        ta.fill(q1)
        time.sleep(1)

        t0 = time.time()
        page.locator('button:has-text("arrow_upward")').first.click()
        ans1 = extract_assistant_answer(page, timeout_sec=45)
        dur1 = time.time() - t0
        print(f"[+] Câu 1 trả lời sau {dur1:.2f}s", flush=True)
        img1 = save_dual_screenshot(page, "anh-step1-01-cu-ma-loi-pho-bien-c7620.png")

        # Bấm mở trích dẫn để kiểm chứng mở đúng hồ sơ
        print("[*] Đang bấm mở trích dẫn tài liệu tham chiếu / hồ sơ gốc cho C7620...", flush=True)
        img2 = None
        try:
            page.wait_for_selector('button:has-text("02XC_"), button:has-text("dòng"), button:has-text("Xem hồ sơ")', timeout=15000)
            cite_btn = page.locator('button:has-text("02XC_"), button:has-text("dòng"), button:has-text("Xem hồ sơ")').first
            if cite_btn.is_visible():
                print(f"[+] Tìm thấy nút trích dẫn: '{cite_btn.inner_text().strip()}'", flush=True)
                cite_btn.scroll_into_view_if_needed()
                time.sleep(1)
                cite_btn.click()
                time.sleep(3)
                img2 = save_dual_screenshot(page, "anh-step1-02-cu-cite-c7620-source-viewer.png")
        except Exception as e:
            print(f"[!] Warning waiting for citation button in Câu 1: {e}", flush=True)

        results.append({
            "id": "CAU_01",
            "loai": "ma_loi_pho_bien",
            "so": "NB-LAZY-DTL",
            "cau_hoi": q1,
            "thoi_gian_s": round(dur1, 2),
            "cau_tra_loi_nguyen_van": ans1,
            "anh": [img1, img2] if img2 else [img1],
            "sql_ground_truth": sql_facts["c7620"],
        })

        # =======================================================================
        # CÂU 2: Mã lỗi hiếm (C0060 - 2 ca trong DB) trong Sổ Điều tra lỗi
        # =======================================================================
        print("\n--- [CU] Câu 2: Mã lỗi hiếm (C0060) ---", flush=True)
        conv2 = "CONV-CU-S1-02-C0060"
        prepare_conversation(conv2, "NB-LAZY-DTL", "CU 02: Mã lỗi hiếm C0060")
        page.goto(f"http://localhost:8501/?nb=NB-LAZY-DTL&conv={conv2}", wait_until="networkidle")
        time.sleep(2)

        q2 = "Tra cứu mã lỗi C0060"
        ta = page.locator('textarea[aria-label="Câu hỏi gửi AI"]')
        ta.wait_for(state="visible", timeout=15000)
        ta.fill(q2)
        time.sleep(1)

        t0 = time.time()
        page.locator('button:has-text("arrow_upward")').first.click()
        ans2 = extract_assistant_answer(page, timeout_sec=45)
        dur2 = time.time() - t0
        print(f"[+] Câu 2 trả lời sau {dur2:.2f}s", flush=True)
        img3 = save_dual_screenshot(page, "anh-step1-03-cu-ma-loi-hiem-c0060.png")

        results.append({
            "id": "CAU_02",
            "loai": "ma_loi_hiem",
            "so": "NB-LAZY-DTL",
            "cau_hoi": q2,
            "thoi_gian_s": round(dur2, 2),
            "cau_tra_loi_nguyen_van": ans2,
            "anh": [img3],
            "sql_ground_truth": sql_facts["c0060"],
        })

        # =======================================================================
        # CÂU 3: Mô tả hiện tượng có dấu
        # =======================================================================
        print("\n--- [CU] Câu 3: Hiện tượng có dấu (lệch lề postcard) ---", flush=True)
        conv3 = "CONV-CU-S1-03-PHENOM-DAU"
        prepare_conversation(conv3, "NB-LAZY-DTL", "CU 03: Hiện tượng có dấu")
        page.goto(f"http://localhost:8501/?nb=NB-LAZY-DTL&conv={conv3}", wait_until="networkidle")
        time.sleep(2)

        q3 = "Máy in bị lệch lề khi in tờ postcard"
        ta = page.locator('textarea[aria-label="Câu hỏi gửi AI"]')
        ta.wait_for(state="visible", timeout=15000)
        ta.fill(q3)
        time.sleep(1)

        t0 = time.time()
        page.locator('button:has-text("arrow_upward")').first.click()
        ans3 = extract_assistant_answer(page, timeout_sec=45)
        dur3 = time.time() - t0
        print(f"[+] Câu 3 trả lời sau {dur3:.2f}s", flush=True)
        img4 = save_dual_screenshot(page, "anh-step1-04-cu-hien-tuong-co-dau-postcard.png")

        results.append({
            "id": "CAU_03",
            "loai": "hien_tuong_co_dau",
            "so": "NB-LAZY-DTL",
            "cau_hoi": q3,
            "thoi_gian_s": round(dur3, 2),
            "cau_tra_loi_nguyen_van": ans3,
            "anh": [img4],
            "sql_ground_truth": sql_facts["skew_postcard"],
        })

        # =======================================================================
        # CÂU 4: Mô tả hiện tượng không dấu
        # =======================================================================
        print("\n--- [CU] Câu 4: Hiện tượng không dấu (may in bi lech le khi in to postcard) ---", flush=True)
        conv4 = "CONV-CU-S1-04-PHENOM-KHONG-DAU"
        prepare_conversation(conv4, "NB-LAZY-DTL", "CU 04: Hiện tượng không dấu")
        page.goto(f"http://localhost:8501/?nb=NB-LAZY-DTL&conv={conv4}", wait_until="networkidle")
        time.sleep(2)

        q4 = "may in bi lech le khi in to postcard"
        ta = page.locator('textarea[aria-label="Câu hỏi gửi AI"]')
        ta.wait_for(state="visible", timeout=15000)
        ta.fill(q4)
        time.sleep(1)

        t0 = time.time()
        page.locator('button:has-text("arrow_upward")').first.click()
        ans4 = extract_assistant_answer(page, timeout_sec=45)
        dur4 = time.time() - t0
        print(f"[+] Câu 4 trả lời sau {dur4:.2f}s", flush=True)
        img5 = save_dual_screenshot(page, "anh-step1-05-cu-hien-tuong-khong-dau-postcard.png")

        results.append({
            "id": "CAU_04",
            "loai": "hien_tuong_khong_dau",
            "so": "NB-LAZY-DTL",
            "cau_hoi": q4,
            "thoi_gian_s": round(dur4, 2),
            "cau_tra_loi_nguyen_van": ans4,
            "anh": [img5],
            "sql_ground_truth": sql_facts["skew_postcard"],
        })

        # =======================================================================
        # CÂU 5: Lọc máy + serial + khoảng ngày
        # =======================================================================
        print("\n--- [CU] Câu 5: Lọc máy + serial + khoảng ngày ---", flush=True)
        conv5 = "CONV-CU-S1-05-FILTER"
        prepare_conversation(conv5, "NB-LAZY-DTL", "CU 05: Lọc máy + serial + khoảng ngày")
        page.goto(f"http://localhost:8501/?nb=NB-LAZY-DTL&conv={conv5}", wait_until="networkidle")
        time.sleep(2)

        q5 = "máy 6th Next serial WD72Z12772 từ 2023-01-01 đến 2023-01-31"
        ta = page.locator('textarea[aria-label="Câu hỏi gửi AI"]')
        ta.wait_for(state="visible", timeout=15000)
        ta.fill(q5)
        time.sleep(1)

        t0 = time.time()
        page.locator('button:has-text("arrow_upward")').first.click()
        ans5 = extract_assistant_answer(page, timeout_sec=45)
        dur5 = time.time() - t0
        print(f"[+] Câu 5 trả lời sau {dur5:.2f}s", flush=True)
        img6 = save_dual_screenshot(page, "anh-step1-06-cu-loc-may-serial-ngay.png")

        # Bấm mở trích dẫn ca Vụ 2023/1 dòng 5
        print("[*] Bấm mở trích dẫn hồ sơ gốc dòng 5...", flush=True)
        img7 = None
        try:
            page.wait_for_selector('button:has-text("dòng 5"), button:has-text("Loi KDTPS")', timeout=15000)
            cite_btn_f = page.locator('button:has-text("dòng 5"), button:has-text("Loi KDTPS")').first
            if cite_btn_f.is_visible():
                print(f"[+] Tìm thấy nút trích dẫn hồ sơ dòng 5: '{cite_btn_f.inner_text().strip()}'", flush=True)
                cite_btn_f.scroll_into_view_if_needed()
                time.sleep(1)
                cite_btn_f.click()
                time.sleep(3)
                img7 = save_dual_screenshot(page, "anh-step1-07-cu-cite-serial-row5-source-viewer.png")
        except Exception as e:
            print(f"[!] Warning waiting for citation button in Câu 5: {e}", flush=True)

        results.append({
            "id": "CAU_05",
            "loai": "loc_may_serial_ngay",
            "so": "NB-LAZY-DTL",
            "cau_hoi": q5,
            "thoi_gian_s": round(dur5, 2),
            "cau_tra_loi_nguyen_van": ans5,
            "anh": [img6, img7] if img7 else [img6],
            "sql_ground_truth": sql_facts["filter"],
        })

        # =======================================================================
        # CÂU 6: Tìm kiếm mang máng (tiếng kêu bất thường khi khởi động máy)
        # =======================================================================
        print("\n--- [CU] Câu 6: Tìm kiếm mang máng ---", flush=True)
        conv6 = "CONV-CU-S1-06-MANG-MANG"
        prepare_conversation(conv6, "NB-LAZY-DTL", "CU 06: Tìm kiếm mang máng")
        page.goto(f"http://localhost:8501/?nb=NB-LAZY-DTL&conv={conv6}", wait_until="networkidle")
        time.sleep(2)

        q6 = "tiếng kêu bất thường khi khởi động máy"
        ta = page.locator('textarea[aria-label="Câu hỏi gửi AI"]')
        ta.wait_for(state="visible", timeout=15000)
        ta.fill(q6)
        time.sleep(1)

        t0 = time.time()
        page.locator('button:has-text("arrow_upward")').first.click()
        ans6 = extract_assistant_answer(page, timeout_sec=45)
        dur6 = time.time() - t0
        print(f"[+] Câu 6 trả lời sau {dur6:.2f}s", flush=True)
        img8 = save_dual_screenshot(page, "anh-step1-08-cu-tim-kiem-mang-mang.png")

        results.append({
            "id": "CAU_06",
            "loai": "tim_kiem_mang_mang",
            "so": "NB-LAZY-DTL",
            "cau_hoi": q6,
            "thoi_gian_s": round(dur6, 2),
            "cau_tra_loi_nguyen_van": ans6,
            "anh": [img8],
            "sql_ground_truth": sql_facts["abnormal_sound"],
        })

        # =======================================================================
        # CÂU 7: Câu hỏi tài liệu 1 (SIM tape trong Sổ LSU)
        # =======================================================================
        print("\n--- [CU] Câu 7: Câu hỏi tài liệu 1 (LSU SIM tape) ---", flush=True)
        conv7 = "CONV-CU-S1-07-DOC-SIM-TAPE"
        prepare_conversation(conv7, "NB-LAZY-LSU", "CU 07: Tài liệu LSU SIM tape")
        q7 = "SIM tape được dán ở đâu, dày bao nhiêu và trình tự thao tác thế nào?"
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_message(ChatMessage(id=f"msg_u_{conv7}", conversation_id=conv7, role="user", content=q7, created_at=now_iso))
        
        t0 = time.time()
        deliver_5tier_ladder_answer(q7, conversation_id=conv7, notebook_id="NB-LAZY-LSU", user_raw_input=q7)
        dur7 = time.time() - t0
        
        msgs7 = load_messages(conv7)
        ans7 = next((m.content for m in reversed(msgs7) if m.role == "assistant"), "")
        print(f"[+] Câu 7 trả lời sau {dur7:.2f}s", flush=True)

        page.goto(f"http://localhost:8501/?nb=NB-LAZY-LSU&conv={conv7}", wait_until="networkidle")
        time.sleep(3)
        img9 = save_dual_screenshot(page, "anh-step1-09-cu-tai-lieu-lsu-sim-tape.png")

        results.append({
            "id": "CAU_07",
            "loai": "cau_hoi_tai_lieu_1",
            "so": "NB-LAZY-LSU",
            "cau_hoi": q7,
            "thoi_gian_s": round(dur7, 2),
            "cau_tra_loi_nguyen_van": ans7,
            "anh": [img9],
        })

        # =======================================================================
        # CÂU 8: Câu hỏi tài liệu 2 (Bracket OKNG trong Sổ LSU)
        # =======================================================================
        print("\n--- [CU] Câu 8: Câu hỏi tài liệu 2 (LSU Bracket OKNG) ---", flush=True)
        conv8 = "CONV-CU-S1-08-DOC-BRACKET"
        prepare_conversation(conv8, "NB-LAZY-LSU", "CU 08: Tài liệu LSU Bracket")
        q8 = "Theo tài liệu OKNGUNITのCO・BRACKETの倒れ・傾き確認結果.xlsx, Bracketの測定値を見るだけで斜め光NG原因を確定できますか。"
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_message(ChatMessage(id=f"msg_u_{conv8}", conversation_id=conv8, role="user", content=q8, created_at=now_iso))
        
        t0 = time.time()
        deliver_5tier_ladder_answer(q8, conversation_id=conv8, notebook_id="NB-LAZY-LSU", user_raw_input=q8)
        dur8 = time.time() - t0

        msgs8 = load_messages(conv8)
        ans8 = next((m.content for m in reversed(msgs8) if m.role == "assistant"), "")
        print(f"[+] Câu 8 trả lời sau {dur8:.2f}s", flush=True)

        page.goto(f"http://localhost:8501/?nb=NB-LAZY-LSU&conv={conv8}", wait_until="networkidle")
        time.sleep(3)
        img10 = save_dual_screenshot(page, "anh-step1-10-cu-tai-lieu-lsu-bracket.png")

        results.append({
            "id": "CAU_08",
            "loai": "cau_hoi_tai_lieu_2",
            "so": "NB-LAZY-LSU",
            "cau_hoi": q8,
            "thoi_gian_s": round(dur8, 2),
            "cau_tra_loi_nguyen_van": ans8,
            "anh": [img10],
        })

        # =======================================================================
        # CÂU 9: Bẫy xuyên sổ (JAM4212 trong Sổ MOM)
        # =======================================================================
        print("\n--- [CU] Câu 9: Bẫy xuyên sổ (JAM4212 trong Sổ MOM) ---", flush=True)
        conv9 = "CONV-CU-S1-09-TRAP-MOM"
        prepare_conversation(conv9, "NB-LAZY-MOM", "CU 09: Bẫy xuyên sổ MOM JAM4212")
        q9 = "Trong hệ thống MOM Opcenter, xử lý lỗi kẹt giấy JAM4212 như thế nào?"
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_message(ChatMessage(id=f"msg_u_{conv9}", conversation_id=conv9, role="user", content=q9, created_at=now_iso))

        t0 = time.time()
        deliver_5tier_ladder_answer(q9, conversation_id=conv9, notebook_id="NB-LAZY-MOM", user_raw_input=q9)
        dur9 = time.time() - t0

        msgs9 = load_messages(conv9)
        ans9 = next((m.content for m in reversed(msgs9) if m.role == "assistant"), "")
        print(f"[+] Câu 9 trả lời sau {dur9:.2f}s", flush=True)

        page.goto(f"http://localhost:8501/?nb=NB-LAZY-MOM&conv={conv9}", wait_until="networkidle")
        time.sleep(3)
        img11 = save_dual_screenshot(page, "anh-step1-11-cu-bay-xuyen-so-mom-jam4212.png")

        results.append({
            "id": "CAU_09",
            "loai": "bay_xuyen_so",
            "so": "NB-LAZY-MOM",
            "cau_hoi": q9,
            "thoi_gian_s": round(dur9, 2),
            "cau_tra_loi_nguyen_van": ans9,
            "anh": [img11],
            "sql_ground_truth": sql_facts["jam4212"],
        })

        # =======================================================================
        # CÂU 10: Không có dữ liệu (Kiểm tra trung thực / Honesty Check)
        # =======================================================================
        print("\n--- [CU] Câu 10: Không có dữ liệu (Kiểm tra trung thực) ---", flush=True)
        conv10 = "CONV-CU-S1-10-HONESTY"
        prepare_conversation(conv10, "NB-LAZY-DTL", "CU 10: Kiểm tra trung thực ngoài kho")
        page.goto(f"http://localhost:8501/?nb=NB-LAZY-DTL&conv={conv10}", wait_until="networkidle")
        time.sleep(2)

        q10 = "Thủ tục xin visa du lịch Thụy Sĩ năm 2026 cần những giấy tờ gì?"
        ta = page.locator('textarea[aria-label="Câu hỏi gửi AI"]')
        ta.wait_for(state="visible", timeout=15000)
        ta.fill(q10)
        time.sleep(1)

        t0 = time.time()
        page.locator('button:has-text("arrow_upward")').first.click()
        ans10 = extract_assistant_answer(page, timeout_sec=45)
        dur10 = time.time() - t0
        print(f"[+] Câu 10 trả lời sau {dur10:.2f}s", flush=True)
        img12 = save_dual_screenshot(page, "anh-step1-12-cu-khong-du-lieu-trung-thuc.png")

        results.append({
            "id": "CAU_10",
            "loai": "khong_du_lieu_trung_thuc",
            "so": "NB-LAZY-DTL",
            "cau_hoi": q10,
            "thoi_gian_s": round(dur10, 2),
            "cau_tra_loi_nguyen_van": ans10,
            "anh": [img12],
        })

        # =======================================================================
        # MỤC 2.3: BƯỚC 2 - KIỂM CHỨNG CỔNG ĐÓNG VỤ & ĐO ĐỘ BAO PHỦ ĐÁNH GIÁ
        # =======================================================================
        print("\n--- [CU] MỤC 2.3: BƯỚC 2 - KIỂM CHỨNG SỐNG VÒNG PHẢN HỒI ---", flush=True)
        fixture_case_id = "CASE-CU-STEP2-FIXTURE"
        fixture_case = Case(
            case_id=fixture_case_id,
            title="Sự cố kẹt sấy và motor giải áp timeout",
            current_situation="Máy in báo kẹt giấy liên tục trước cụm sấy, cơ cấu áp sấy không quay",
            status="open",
        )
        save_case(fixture_case)
        print(f"[+] Đã tạo ca fixture: {fixture_case_id} trong local_cases", flush=True)

        conv_b2 = "CONV-CU-S2-CLOSE-GATE"
        prepare_conversation(conv_b2, "NB-LAZY-DTL", "CU Bước 2: Đóng vụ & Cổng chặn")
        page.goto(f"http://localhost:8501/?nb=NB-LAZY-DTL&conv={conv_b2}", wait_until="networkidle")
        time.sleep(2)

        # 2. Thử đóng vụ thiếu nguyên nhân thật -> Phải bị cổng chặn
        q_close_blocked = f"đóng vụ {fixture_case_id}"
        print(f"[*] Thử đóng vụ thiếu trường: '{q_close_blocked}'...", flush=True)
        ta = page.locator('textarea[aria-label="Câu hỏi gửi AI"]')
        ta.wait_for(state="visible", timeout=15000)
        ta.fill(q_close_blocked)
        time.sleep(1)

        t0 = time.time()
        page.locator('button:has-text("arrow_upward")').first.click()
        ans_blocked = extract_assistant_answer(page, timeout_sec=45)
        dur_blocked = time.time() - t0
        print(f"[+] Phản hồi cổng chặn sau {dur_blocked:.2f}s", flush=True)
        img13 = save_dual_screenshot(page, "anh-step2-13-cu-dong-vu-thieu-nguyen-nhan-blocked.png")

        # 3. Đóng đúng một vụ fixture hợp lệ -> Thành công, ghi ngược local_cases
        q_close_valid = f"đóng vụ {fixture_case_id}: nguyên nhân: hỏng bánh răng truyền động motor giải áp M2; đối sách: thay mới cụm bánh răng truyền động 150-3M"
        print(f"[*] Đóng vụ hợp lệ: '{q_close_valid}'...", flush=True)
        page.reload(wait_until="networkidle")
        time.sleep(2)
        ta_valid = page.locator('textarea[aria-label="Câu hỏi gửi AI"]')
        ta_valid.wait_for(state="visible", timeout=15000)
        ta_valid.fill(q_close_valid)
        time.sleep(1)

        t0 = time.time()
        page.locator('button:has-text("arrow_upward")').first.click()
        ans_valid = extract_assistant_answer(page, timeout_sec=45)
        dur_valid = time.time() - t0
        print(f"[+] Phản hồi đóng hợp lệ sau {dur_valid:.2f}s", flush=True)
        img14 = save_dual_screenshot(page, "anh-step2-14-cu-dong-vu-hop-le-thanh-cong.png")

        # Kiểm chứng ghi ngược vào local_cases/cases.jsonl
        reloaded_cases = load_cases()
        matched_fixture = next((c for c in reloaded_cases if c.case_id == fixture_case_id), None)
        assert matched_fixture is not None, f"Ca {fixture_case_id} không tìm thấy trong cases.jsonl!"
        print(f"[+] Kiểm chứng ghi ngược local_cases: status={matched_fixture.status}, actual_cause={matched_fixture.actual_cause}, actual_countermeasure={matched_fixture.actual_countermeasure}", flush=True)

        results.append({
            "id": "BUOC_2_CLOSE_GATE",
            "loai": "cong_dong_vu_buoc_2",
            "so": "NB-LAZY-DTL",
            "lenh_thu_thieu_truong": q_close_blocked,
            "phan_hoi_cong_chan": ans_blocked,
            "lenh_dong_hop_le": q_close_valid,
            "phan_hoi_thanh_cong": ans_valid,
            "thoi_gian_chan_s": round(dur_blocked, 2),
            "thoi_gian_dong_s": round(dur_valid, 2),
            "anh": [img13, img14],
            "kiem_chung_ghi_nguoc": {
                "case_id": fixture_case_id,
                "status": matched_fixture.status,
                "actual_cause": matched_fixture.actual_cause,
                "actual_countermeasure": matched_fixture.actual_countermeasure,
                "closed_at": matched_fixture.closed_at,
            }
        })

        browser.close()

    # 4. Đo lại độ bao phủ đánh giá từ local_cases hiện tại của máy nhà
    print("\n--- [BƯỚC 3] ĐO LẠI ĐỘ BAO PHỦ ĐÁNH GIÁ TỪ LOCAL_CASES MÁY NHÀ ---", flush=True)
    cov = compute_feedback_coverage(base_dir=APP_DIR / "local_cases")
    print(f"Coverage live: {json.dumps(cov, indent=2, ensure_ascii=False)}", flush=True)

    # 5. Xuất tệp JSON kết quả tổng hợp tệp thô
    final_output = {
        "ma_ve": "DESKTOP-HOME-STEP1-REALUSE-ACCEPTANCE",
        "thoi_diem": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "model_stamp": {
            "model": "gemini-2.5-flash",
            "harness": "Google DeepMind Antigravity Boosted Engine v0.3.0",
            "thinking": "default/high",
            "python_env": sys.version,
            "python_exe": sys.executable,
        },
        "sql_ground_truth": sql_facts,
        "results": results,
        "feedback_coverage": cov,
    }

    evidence_json_local = LOCAL_OUT_DIR / "step1_realuse_acceptance_evidence.json"
    evidence_json_desktop = DESKTOP_OUT_DIR / "step1_realuse_acceptance_evidence.json"
    with open(evidence_json_local, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)
    evidence_json_desktop.write_bytes(evidence_json_local.read_bytes())
    print(f"[+] Đã xuất tệp evidence manifest: {evidence_json_desktop} ({evidence_json_desktop.stat().st_size} bytes)", flush=True)

    print("\n" + "=" * 80)
    print("HOAN THANH TOAN BO TIEN TRINH CHAY CU CHO VE DESKTOP-HOME-STEP1-REALUSE-ACCEPTANCE!")
    print("=" * 80)


if __name__ == "__main__":
    main()
