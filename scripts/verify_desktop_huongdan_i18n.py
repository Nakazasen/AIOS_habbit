# -*- coding: utf-8 -*-
"""Deterministic verification & evidence collection script for ticket DESKTOP-HOME-HUONGDAN-I18N.

Runs on Python 3.11 with Playwright on the real desktop display.
Executes all 5 acceptance gates:
- Gate 1: Type /使い方 -> Japanese menu in chat; open section C4 -> Japanese text, stats 136 / FY27H2/263 / 30.075 preserved, real image displays.
- Gate 2: Type /使用指南 -> Chinese menu in chat; open any section (e.g. C4) -> Chinese text & real image.
- Gate 3 (Vietnamese regression): Type /huongdan -> Vietnamese menu; open C4 -> matches original Vietnamese manual.
- Gate 4 (Submission stillness): Send /使い方 once and leave untouched for >= 60 seconds: appears once, no doubling, UI not locked.
- Gate 5 (Zero fake turns): Count SQLite messages before/after all 3 language flows: fake turns created = 0.
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
import uuid

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

from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import (
    clear_store_cache,
    load_messages,
    save_conversation,
)
from aios_habit.huongdan_command import get_huongdan_metrics

OUT_DIR_KO = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")
OUT_DIR_DOCS = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
OUT_DIR_KO.mkdir(parents=True, exist_ok=True)
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
    p_docs = OUT_DIR_DOCS / filename

    page.screenshot(path=str(p_ko), full_page=full_page)
    p_docs.write_bytes(p_ko.read_bytes())

    if mirror_filenames:
        for mf in mirror_filenames:
            m_ko = OUT_DIR_KO / mf
            m_docs = OUT_DIR_DOCS / mf
            m_ko.write_bytes(p_ko.read_bytes())
            m_docs.write_bytes(p_ko.read_bytes())
            log(f"    [Mirror] Copied {filename} -> {mf}")

    data = p_ko.read_bytes()
    size = len(data)
    is_png = data[:4] == b"\x89PNG"
    sha = get_file_sha256(p_ko)
    log(f"[+] Screenshot: {filename} ({size:,} bytes, SHA256={sha}, valid_png={is_png})")
    return {
        "file": filename,
        "size_bytes": size,
        "sha256": sha,
        "is_valid_png": is_png,
    }


def send_input_on_page(page: Page, text: str, delay_ms: int = 40) -> None:
    ta = page.locator('div[class*="st-key-wsc_question_input_"] textarea, textarea[aria-label="Câu hỏi gửi AI"]').first
    ta.wait_for(state="visible", timeout=30000)
    ta.click()
    time.sleep(0.3)
    ta.fill("")
    time.sleep(0.2)
    for ch in text:
        ta.type(ch, delay=delay_ms)
    time.sleep(0.5)
    ta.evaluate("el => el.blur()")
    time.sleep(0.8)

    btn = page.locator('div[class*="st-key-wsc_ask_"] button:not([disabled]), div[class*="st-key-wsc-action-"] button:not([disabled])').first
    btn.wait_for(state="visible", timeout=15000)
    btn.click()
    log(f"    -> Đã bấm Gửi: '{text}'")


def scroll_to_top_of_last_message(page: Page) -> None:
    page.evaluate("""() => {
        const msgs = document.querySelectorAll('[data-testid="stChatMessage"]');
        if (msgs.length) {
            msgs[msgs.length - 1].scrollIntoView({ behavior: "instant", block: "start" });
            window.scrollBy(0, -60);
        }
    }""")
    time.sleep(0.8)


def main():
    log("================================================================================")
    log("=== BẮT ĐẦU NGHIỆM THU VÉ DESKTOP-HOME-HUONGDAN-I18N TRÊN GIAO DIỆN THẬT ===")
    log("================================================================================")
    results = {}

    with sync_playwright() as p:
        log("[*] Khởi động trình duyệt Chromium trên desktop hiển thị thật...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        page = context.new_page()

        nb_target = "NB-LAZY-LSU"
        conv_id = f"CONV-I18N-{uuid.uuid4().hex[:8].upper()}"
        save_conversation(
            WorkspaceConversation(
                id=conv_id,
                notebook_id=nb_target,
                title="Nghiệm thu Hướng dẫn đa ngữ /使い方 /使用指南 /huongdan",
                ui_locale="vi",
                answer_language="vi",
            )
        )
        log(f"    -> Đã khởi tạo cuộc trò chuyện sạch cho nghiệm thu: {conv_id}")

        page.goto(f"http://localhost:8501/?nb={nb_target}&conv={conv_id}", wait_until="domcontentloaded", timeout=60000)
        time.sleep(4)

        # -----------------------------------------------------------------
        # CỔNG 4: Gửi /使い方 đúng 1 lần rồi để yên >= 60 giây không thao tác
        # -----------------------------------------------------------------
        log("\n--- [CỔNG 4] Gửi /使い方 đúng 1 lần, chờ tĩnh >= 60s (không nhân đôi, không khóa giao diện) ---")
        t_send_g4 = time.time()
        send_input_on_page(page, "/使い方")

        # Đợi danh mục tiếng Nhật xuất hiện
        page.locator('text=AIOS台帳 総合利用マニュアル').first.wait_for(timeout=30000)
        log("    -> Đã xuất hiện danh mục cẩm nang tiếng Nhật trong khung chat!")

        elapsed_g4 = time.time() - t_send_g4
        rem_g4 = 61.0 - elapsed_g4
        if rem_g4 > 0:
            log(f"    -> Chờ giữ nguyên tay không trong {rem_g4:.1f}s để đủ >= 60s nghiệm thu...")
            time.sleep(rem_g4)

        asst_bubbles = page.locator('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])')
        user_bubbles = page.locator('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])')
        assert asst_bubbles.count() == 1, f"Lỗi nhân đôi: có {asst_bubbles.count()} bong bóng assistant"
        assert user_bubbles.count() == 0, f"Lỗi tạo tin nhắn user: có {user_bubbles.count()} tin nhắn user"

        scroll_to_top_of_last_message(page)
        shot4 = save_screenshot(page, "anh-hd-i18n-04-submission-stillness-60s.png")
        results["GATE_4_SUBMISSION_STILLNESS_60S"] = {
            "verdict": "DAT",
            "conversation_id": conv_id,
            "waited_seconds": round(time.time() - t_send_g4, 1),
            "asst_bubbles_count": asst_bubbles.count(),
            "user_bubbles_count": user_bubbles.count(),
            "screenshot": shot4,
        }

        # -----------------------------------------------------------------
        # CỔNG 1: Tiếng Nhật: Mở mục C4 -> chữ tiếng Nhật, số liệu 136 / FY27H2/263 / 30.075, ảnh hiện thật
        # -----------------------------------------------------------------
        log("\n--- [CỔNG 1] Mở mục C4 tiếng Nhật (/使い方 C4) ---")
        send_input_on_page(page, "/使い方 C4")
        time.sleep(3)

        page.locator('text=C4. 自動分類とステップ5再発警告カード（C7620）').first.wait_for(timeout=25000)
        log("    -> Đã xuất hiện tiêu đề C4 tiếng Nhật!")

        asst_text_ja = page.locator('[data-testid="stChatMessage"]').last.inner_text()
        assert "ステップ5再発警告カード" in asst_text_ja, "Thiếu văn bản tiếng Nhật về thẻ cảnh báo tái phát"
        assert "136" in asst_text_ja, "Thiếu số liệu 136 lần"
        assert "FY27H2/263" in asst_text_ja, "Thiếu ca gần nhất FY27H2/263"
        assert "30.075" in asst_text_ja or "30,075" in asst_text_ja, "Thiếu số liệu 30.075 ca"

        # Kiểm tra ảnh minh họa hiển thị thật qua data URI
        c4_img_ja = page.locator('img[src^="data:image/png;base64,"]').first
        c4_img_ja.wait_for(state="visible", timeout=10000)
        box_ja = c4_img_ja.bounding_box()
        assert box_ja is not None and box_ja["width"] > 100 and box_ja["height"] > 50, (
            f"Ảnh minh họa tiếng Nhật không hiển thị kích thước thật: {box_ja}"
        )
        log(f"    -> Ảnh minh họa hiển thị thật: {box_ja['width']:.1f}px x {box_ja['height']:.1f}px")

        scroll_to_top_of_last_message(page)
        shot1 = save_screenshot(page, "anh-hd-i18n-01-japanese-c4.png")
        results["GATE_1_JAPANESE_MANUAL"] = {
            "verdict": "DAT",
            "section": "C4",
            "has_136": "136" in asst_text_ja,
            "has_case_id": "FY27H2/263" in asst_text_ja,
            "has_30k": "30.075" in asst_text_ja or "30,075" in asst_text_ja,
            "img_width": round(box_ja["width"], 1),
            "img_height": round(box_ja["height"], 1),
            "screenshot": shot1,
        }

        # -----------------------------------------------------------------
        # CỔNG 2: Tiếng Trung: /使用指南 -> danh mục; mở mục C4 -> chữ tiếng Trung
        # -----------------------------------------------------------------
        log("\n--- [CỔNG 2] Tiếng Trung: Gõ /使用指南 -> danh mục; mở C4 -> tiếng Trung ---")
        send_input_on_page(page, "/使用指南")
        time.sleep(3)

        page.locator('text=AIOS 台账综合使用指南').first.wait_for(timeout=25000)
        log("    -> Đã xuất hiện danh mục cẩm nang tiếng Trung!")

        # Mở C4 tiếng Trung
        send_input_on_page(page, "/使用指南 C4")
        time.sleep(3)

        page.locator('text=C4. 自动分类与第5步复发预警卡片(C7620)').first.wait_for(timeout=25000)
        log("    -> Đã xuất hiện C4 tiếng Trung!")

        asst_text_zh = page.locator('[data-testid="stChatMessage"]').last.inner_text()
        assert "复发预警卡片" in asst_text_zh, "Thiếu văn bản tiếng Trung về thẻ cảnh báo tái phát"
        assert "136" in asst_text_zh, "Thiếu số liệu 136 lần trong bản tiếng Trung"
        assert "FY27H2/263" in asst_text_zh, "Thiếu mã vụ FY27H2/263 trong bản tiếng Trung"

        c4_img_zh = page.locator('img[src^="data:image/png;base64,"]').first
        c4_img_zh.wait_for(state="visible", timeout=10000)
        box_zh = c4_img_zh.bounding_box()
        assert box_zh is not None and box_zh["width"] > 100, f"Ảnh C4 tiếng Trung không hiển thị: {box_zh}"

        scroll_to_top_of_last_message(page)
        shot2 = save_screenshot(page, "anh-hd-i18n-02-chinese-menu-and-section.png")
        results["GATE_2_CHINESE_MANUAL"] = {
            "verdict": "DAT",
            "section": "C4",
            "has_136": "136" in asst_text_zh,
            "has_case_id": "FY27H2/263" in asst_text_zh,
            "img_width": round(box_zh["width"], 1),
            "screenshot": shot2,
        }

        # -----------------------------------------------------------------
        # CỔNG 3: Hồi quy tiếng Việt (/huongdan & /huongdan C4)
        # -----------------------------------------------------------------
        log("\n--- [CỔNG 3] Hồi quy tiếng Việt: /huongdan & /huongdan C4 ---")
        send_input_on_page(page, "/huongdan")
        time.sleep(3)

        page.locator('text=CẨM NANG HƯỚNG DẪN SỬ DỤNG SỔ CÁI AIOS').first.wait_for(timeout=25000)
        log("    -> Đã xuất hiện danh mục tiếng Việt!")

        send_input_on_page(page, "/huongdan C4")
        time.sleep(3)

        page.locator('text=C4. Phân loại tự động & Thẻ Cảnh báo Tái phát Bước 5 (C7620)').first.wait_for(timeout=25000)
        log("    -> Đã xuất hiện C4 tiếng Việt!")

        asst_text_vi = page.locator('[data-testid="stChatMessage"]').last.inner_text()
        assert "Thẻ Cảnh báo Tái phát Bước 5" in asst_text_vi
        assert "136" in asst_text_vi

        scroll_to_top_of_last_message(page)
        shot3 = save_screenshot(page, "anh-hd-i18n-03-vietnamese-regression.png")
        results["GATE_3_VIETNAMESE_REGRESSION"] = {
            "verdict": "DAT",
            "section": "C4",
            "screenshot": shot3,
        }

        # -----------------------------------------------------------------
        # CỔNG 5: Đếm tin nhắn CSDL trước/sau ca 3 luồng: số lượt giả tạo ra = 0
        # -----------------------------------------------------------------
        log("\n--- [CỔNG 5] Đếm tin nhắn CSDL hội thoại: số lượt giả tạo ra = 0 ---")
        clear_store_cache()
        msgs_before = load_messages(conv_id)
        log(f"    -> Số tin nhắn trong CSDL {conv_id} TRƯỚC câu hỏi RAG: {len(msgs_before)}")
        assert len(msgs_before) == 0, f"Lỗi: Các lệnh hướng dẫn đã lưu {len(msgs_before)} tin nhắn giả vào CSDL!"

        q_normal = "Báo cáo xu hướng định kỳ"
        send_input_on_page(page, q_normal)

        t0_rag = time.time()
        rag_answered = False
        while time.time() - t0_rag < 60:
            time.sleep(2)
            clear_store_cache()
            msgs_now = load_messages(conv_id)
            if len(msgs_now) >= 2:
                rag_answered = True
                break

        log(f"    -> AI đã trả lời câu hỏi bình thường sau {time.time() - t0_rag:.1f}s.")
        assert rag_answered, "AI không trả lời được câu hỏi bình thường sau khi dùng lệnh cẩm nang"

        clear_store_cache()
        msgs_after = load_messages(conv_id)
        log(f"    -> Số tin nhắn trong CSDL {conv_id} SAU câu hỏi RAG: {len(msgs_after)}")
        assert len(msgs_after) == 2, f"Kỳ vọng đúng 2 tin nhắn trong CSDL, thực tế có {len(msgs_after)}"
        assert msgs_after[0].role == "user" and msgs_after[0].content == q_normal
        assert msgs_after[1].role == "assistant"

        scroll_to_top_of_last_message(page)
        shot5 = save_screenshot(page, "anh-hd-i18n-05-zero-fake-turns.png")
        results["GATE_5_ZERO_FAKE_TURNS"] = {
            "verdict": "DAT",
            "msgs_before_normal_q": len(msgs_before),
            "msgs_after_normal_q": len(msgs_after),
            "fake_turns_created": 0,
            "screenshot": shot5,
        }

        browser.close()

    metrics = get_huongdan_metrics()
    log(f"\n[+] Số liệu metrics thu thập được: {metrics}")
    results["METRICS"] = metrics

    res_path = OUT_DIR_DOCS / "verification_desktop_huongdan_i18n.json"
    res_ko_path = OUT_DIR_KO / "verification_desktop_huongdan_i18n.json"
    with open(res_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    shutil.copyfile(str(res_path), str(res_ko_path))

    log("\n================================================================================")
    log("=== TẤT CẢ 5 CỔNG NGHIỆM THU ĐÃ ĐẠT 100% ===")
    log(f"=== BẰNG CHỨNG ĐÃ ĐƯỢC LƯU VÀO: {res_path} ===")
    log("================================================================================")
    return results


if __name__ == "__main__":
    main()
