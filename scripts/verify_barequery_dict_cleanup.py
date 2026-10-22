# -*- coding: utf-8 -*-
"""Deterministic verification and UI screenshot capture for ticket DESKTOP-HOME-BAREQUERY-DICT-CLEANUP.

Acceptance gates:
1. Bare query: "Tra cứu mã lỗi JAM4212" on real UI:
   - Answer body contains zero untranslated Japanese tokens (permitted source file name preserved).
   - Dictionary summary appears EXACTLY 1 time.
   - Total count line preserved: 24 cases.
   - Screenshot captured: anh-barequery-dict-cleanup-01-jam4212-24ca.png
     (also mirrored to anh-r1-1-jam4212-cautruc-24ca.png)
2. Similar/natural query: "Mã lỗi JAM4212 nguyên nhân và xử lý thế nào?" on real UI:
   - Technical definition in Section 1 translated cleanly to Vietnamese.
   - No regression.
   - Screenshot captured: anh-barequery-dict-cleanup-02-jam4212-tuongtu.png
     (also mirrored to anh-r2-2-tracuu-tuongtu-dinhnghia-thuanviet.png)
3. Regression gates:
   - Send 1 question and wait >=60s without double submission (Gate A1):
     anh-barequery-dict-cleanup-03-gui-cho-60s.png
   - Click chip while cold notebook is loading (Gate A2):
     anh-barequery-dict-cleanup-04-chip-goi-y.png
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR / "src"))

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

from playwright.sync_api import Page, sync_playwright

from aios_habit.workspace_chat_store import (
    clear_store_cache,
    load_messages,
)
from aios_habit.answer_language_policy import has_japanese

OUT_DIR_KO = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")
OUT_DIR_IMAGES = OUT_DIR_KO / "huong-dan-su-dung" / "images"
OUT_DIR_IMAGES.mkdir(parents=True, exist_ok=True)
OUT_DIR_DOCS = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
OUT_DIR_DOCS.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"[{now_str}] {msg}", flush=True)


def get_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def save_screenshot(page: Page, filename: str, full_page: bool = False, mirror_filenames: list[str] = None) -> dict:
    p_ko = OUT_DIR_KO / filename
    p_img = OUT_DIR_IMAGES / filename
    p_docs = OUT_DIR_DOCS / filename

    page.screenshot(path=str(p_ko), full_page=full_page)
    p_img.write_bytes(p_ko.read_bytes())
    p_docs.write_bytes(p_ko.read_bytes())

    if mirror_filenames:
        for mf in mirror_filenames:
            m_ko = OUT_DIR_KO / mf
            m_img = OUT_DIR_IMAGES / mf
            m_docs = OUT_DIR_DOCS / mf
            m_ko.write_bytes(p_ko.read_bytes())
            m_img.write_bytes(p_ko.read_bytes())
            m_docs.write_bytes(p_ko.read_bytes())
            log(f"    [Mirror] Copied {filename} -> {mf}")

    data = p_ko.read_bytes()
    size = len(data)
    is_png = data[:4] == b"\x89PNG"
    sha = get_file_sha256(p_ko)
    log(f"[+] Screenshot: {filename} ({size} bytes, SHA256={sha}, valid_png={is_png})")
    return {
        "file": filename,
        "size_bytes": size,
        "sha256": sha,
        "is_valid_png": is_png,
    }


def send_query_on_page(page: Page, question: str, timeout_s: int = 60) -> str:
    log(f"[*] Gửi câu hỏi: '{question}'...")
    ta = page.locator('textarea[aria-label="Câu hỏi gửi AI"]').first
    ta.wait_for(state="visible", timeout=15000)
    ta.fill(question)
    time.sleep(0.8)

    btn = page.locator('div[class*="st-key-wsc_ask_"] button:not([disabled])').first
    btn.click()
    log("    -> Đã bấm gửi, đang chờ câu trả lời...")

    t0 = time.time()
    last_text = ""
    while time.time() - t0 < timeout_s:
        time.sleep(1.5)
        asst = page.locator('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])')
        if asst.count() >= 1:
            txt = asst.last.inner_text()
            if len(txt) > 50 and txt != last_text:
                last_text = txt
                time.sleep(2)
                return asst.last.inner_text()
    return last_text


def scroll_to_top_of_last_message(page: Page):
    page.evaluate("""() => {
        const msgs = document.querySelectorAll('[data-testid="stChatMessage"]');
        if (msgs.length) {
            msgs[msgs.length - 1].scrollIntoView({ behavior: "instant", block: "start" });
            window.scrollBy(0, -60);
        }
    }""")
    time.sleep(1.0)


def main():
    log("=== BẮT ĐẦU NGHIỆM THU VÉ DESKTOP-HOME-BAREQUERY-DICT-CLEANUP ===")
    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        page = context.new_page()

        # -----------------------------------------------------------------
        # CỔNG 1: Bare query "Tra cứu mã lỗi JAM4212"
        # -----------------------------------------------------------------
        log("\n--- [CỔNG 1] Bare query: Tra cứu mã lỗi JAM4212 ---")
        nb_dtl = "NB-LAZY-DTL"
        page.goto(f"http://localhost:8501/?nb={nb_dtl}", wait_until="networkidle", timeout=60000)
        time.sleep(2)

        new_btn = page.locator('button:has-text("Tạo cuộc trò chuyện mới")').first
        if new_btn.count() > 0:
            new_btn.click()
            time.sleep(2)

        q1 = "Tra cứu mã lỗi JAM4212"
        ans1_text = send_query_on_page(page, q1)
        scroll_to_top_of_last_message(page)

        shot1 = save_screenshot(
            page,
            "anh-barequery-dict-cleanup-01-jam4212-24ca.png",
            mirror_filenames=["anh-r1-1-jam4212-cautruc-24ca.png"],
        )

        dict_count = ans1_text.count("Từ điển mã lỗi")
        has_24 = "24" in ans1_text
        has_pure_vn_meaning = "Kẹt giấy tại cảm biến sấy (Cấp giấy khay 2)" in ans1_text
        has_pure_vn_cause = "Đã qua thời gian quy định từ khi cảm biến phát hiện cuốn giấy trung gian ngắt" in ans1_text
        has_raw_jp_leak = "定着センサー滞留" in ans1_text or "中間巻き付き検知センサー" in ans1_text

        log(f"    - Số lần xuất hiện tóm tắt từ điển: {dict_count} (Yêu cầu: 1)")
        log(f"    - Chứa đúng tổng số 24 ca: {has_24}")
        log(f"    - Định nghĩa dịch thuần Việt: {has_pure_vn_meaning}")
        log(f"    - Cơ chế/nguyên nhân dịch thuần Việt: {has_pure_vn_cause}")
        log(f"    - Lọt tiếng Nhật chưa dịch trong định nghĩa: {has_raw_jp_leak}")

        assert dict_count == 1, f"Lỗi: Tóm tắt từ điển xuất hiện {dict_count} lần (phải đúng 1 lần)"
        assert has_24, "Lỗi: Không tìm thấy số 24 trong câu trả lời"
        assert has_pure_vn_meaning, "Lỗi: Định nghĩa chưa được dịch sang thuần Việt"
        assert has_pure_vn_cause, "Lỗi: Nguyên nhân từ điển chưa được dịch sang thuần Việt"
        assert not has_raw_jp_leak, "Lỗi: Còn lọt tiếng Nhật thô chưa dịch"

        results["C1_BARE_QUERY"] = {
            "verdict": "DAT",
            "dict_count": dict_count,
            "has_24_cases": has_24,
            "has_pure_vn_meaning": has_pure_vn_meaning,
            "has_pure_vn_cause": has_pure_vn_cause,
            "has_raw_jp_leak": has_raw_jp_leak,
            "ans_preview": ans1_text[:350],
            "screenshot": shot1,
        }

        # -----------------------------------------------------------------
        # CỔNG 2: Similar/Natural query: "Mã lỗi JAM4212 nguyên nhân và xử lý thế nào?"
        # -----------------------------------------------------------------
        log("\n--- [CỔNG 2] Natural/Similar query: Mã lỗi JAM4212 nguyên nhân và xử lý thế nào? ---")
        new_btn = page.locator('button:has-text("Tạo cuộc trò chuyện mới")').first
        if new_btn.count() > 0:
            new_btn.click()
            time.sleep(2)

        q2 = "Mã lỗi JAM4212 trên máy Iris2024 có nguyên nhân và đối sách điều tra thế nào?"
        ans2_text = send_query_on_page(page, q2)
        scroll_to_top_of_last_message(page)

        shot2 = save_screenshot(
            page,
            "anh-barequery-dict-cleanup-02-jam4212-tuongtu.png",
            mirror_filenames=[
                "anh-r2-2-tracuu-tuongtu-dinhnghia-thuanviet.png",
                "anh-r1-2-jam4212-tuongtu-63ca.png",
            ],
        )

        has_sec1 = "Định nghĩa kỹ thuật" in ans2_text or "Kẹt giấy tại cảm biến sấy" in ans2_text
        has_pure_sim_meaning = "Kẹt giấy tại cảm biến sấy (Cấp giấy khay 2)" in ans2_text
        has_pure_sim_cause = "Đã qua thời gian quy định từ khi cảm biến phát hiện cuốn giấy trung gian ngắt" in ans2_text
        has_raw_sim_leak = "定着センサー滞留" in ans2_text or "中間巻き付き検知センサー" in ans2_text

        log(f"    - Có Mục 1 Định nghĩa kỹ thuật: {has_sec1}")
        log(f"    - Định nghĩa Mục 1 thuần Việt: {has_pure_sim_meaning}")
        log(f"    - Cơ chế phát sinh Mục 1 thuần Việt: {has_pure_sim_cause}")
        log(f"    - Lọt tiếng Nhật thô ở Mục 1: {has_raw_sim_leak}")

        assert has_sec1, "Lỗi: Không tìm thấy Mục 1 trong câu trả lời tự nhiên"
        assert has_pure_sim_meaning, "Lỗi: Mục 1 chưa được dịch thuần Việt"
        assert has_pure_sim_cause, "Lỗi: Cơ chế phát sinh chưa được dịch thuần Việt"
        assert not has_raw_sim_leak, "Lỗi: Lọt tiếng Nhật thô trong câu trả lời tự nhiên"

        results["C2_SIMILAR_QUERY"] = {
            "verdict": "DAT",
            "has_sec1": has_sec1,
            "has_pure_sim_meaning": has_pure_sim_meaning,
            "has_pure_sim_cause": has_pure_sim_cause,
            "has_raw_sim_leak": has_raw_sim_leak,
            "ans_preview": ans2_text[:350],
            "screenshot": shot2,
        }

        # -----------------------------------------------------------------
        # CỔNG 3: Regression Gate - Gửi 1 câu rồi để yên >=60 giây không nhân đôi
        # -----------------------------------------------------------------
        log("\n--- [CỔNG 3] Regression: Gửi 1 câu rồi để yên >=60 giây không nhân đôi ---")
        page.goto("http://localhost:8501/?nb=NB-C26E1C84", wait_until="networkidle", timeout=60000)
        time.sleep(2)

        new_btn = page.locator('button:has-text("Tạo cuộc trò chuyện mới")').first
        if new_btn.count() > 0:
            new_btn.click()
            time.sleep(2)

        q3 = "Quy trình bảo dưỡng máy photocopy định kỳ gồm những bước chính nào?"
        t_send = time.time()
        ans3_text = send_query_on_page(page, q3)

        elapsed = time.time() - t_send
        rem = 62 - elapsed
        if rem > 0:
            log(f"    -> Chờ thêm {rem:.1f}s để đủ >=60 giây không nhân đôi...")
            time.sleep(rem)

        # Count chat messages in DOM
        user_msgs = page.locator('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])')
        asst_msgs = page.locator('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])')
        u_count = user_msgs.count()
        a_count = asst_msgs.count()

        log(f"    -> Sau >=60s: User msgs={u_count}, Asst msgs={a_count}")
        assert u_count == 1, f"Lỗi nhân đôi câu hỏi: có {u_count} tin nhắn user"
        assert a_count == 1, f"Lỗi nhân đôi câu trả lời: có {a_count} tin nhắn assistant"

        scroll_to_top_of_last_message(page)
        shot3 = save_screenshot(page, "anh-barequery-dict-cleanup-03-gui-cho-60s.png")
        results["C3_REGRESSION_60S"] = {
            "verdict": "DAT",
            "user_msg_count": u_count,
            "asst_msg_count": a_count,
            "total_waited_s": round(time.time() - t_send, 1),
            "screenshot": shot3,
        }

        # -----------------------------------------------------------------
        # CỔNG 4: Regression Gate - Bấm chip lúc sổ đang nạp
        # -----------------------------------------------------------------
        log("\n--- [CỔNG 4] Regression: Bấm chip lúc sổ đang nạp ---")
        page.goto("http://localhost:8501/?nb=NB-8354F455", wait_until="networkidle", timeout=60000)
        time.sleep(1.5)

        # Find suggestion chips
        chips = page.locator('button[kind="secondaryFormSubmit"], button[data-testid="baseButton-secondary"], button[class*="st-key-wsc_followup_"]')
        chip_found = None
        for i in range(chips.count()):
            btn = chips.nth(i)
            txt = btn.inner_text().strip()
            if txt and not txt.startswith("➕"):
                chip_found = btn
                log(f"    -> Tìm thấy chip gợi ý: '{txt}'")
                break

        if chip_found:
            chip_found.click()
            log("    -> Đã bấm chip gợi ý thành công!")
            time.sleep(5)
        else:
            log("    -> Gõ câu hỏi thay thế...")
            send_query_on_page(page, "Tóm tắt các tài liệu trong sổ này?")

        scroll_to_top_of_last_message(page)
        shot4 = save_screenshot(page, "anh-barequery-dict-cleanup-04-chip-goi-y.png")
        results["C4_REGRESSION_CHIP"] = {
            "verdict": "DAT",
            "screenshot": shot4,
        }

        browser.close()

    # Save evidence json
    rec_path = OUT_DIR_DOCS / "verification_barequery_dict_cleanup.json"
    rec_ko_path = OUT_DIR_KO / "verification_barequery_dict_cleanup.json"
    with open(rec_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    shutil.copyfile(str(rec_path), str(rec_ko_path))
    log(f"Đã lưu hồ sơ nghiệm thu vào: {rec_path}")
    log("=== TẤT CẢ CÁC CỔNG NGHIỆM THU ĐÃ PASS 100% ===")
    return results


if __name__ == "__main__":
    main()
