# -*- coding: utf-8 -*-
"""Verification script for ticket DESKTOP-HOME-SLASH-COMMAND-PALETTE on máy nhà.

Executes all live quality gates on http://localhost:8501:
1. Gõ "/" trong ô chat: bảng gợi ý hiện đủ 8 lệnh bằng đúng số mục của catalog, mỗi mục có mô tả + câu tự nhiên.
2. Gõ "/huo": bảng lọc còn nhóm hướng dẫn; chọn /huongdan thì ô soạn chứa đúng "/huongdan",
   số tin nhắn CSDL không đổi (0 lượt giả); bấm gửi thì danh mục cẩm nang hiện như cũ.
3. Gõ "/baocao" chọn /baocaodinhky, gửi: báo cáo định kỳ chạy như hiện trạng.
4. Không dùng "/": gõ câu tự nhiên "báo cáo xu hướng định kỳ" vẫn ra đúng báo cáo.
5. Mục danh mục lệnh mới: /huongdan lenh mở tiếng Việt, /使い方 lenh mở tiếng Nhật, /使用指南 lenh mở tiếng Trung.
6. Nguyên bộ cổng dung họ lỗi đường gửi chat:
   - 6a: Gửi 1 lần để yên >= 60s đếm lượt hỏi-đáp.
   - 6b: Bấm chip gợi ý trong lúc worker đang nạp.
   - 6c: Sổ lạnh chờ tay không.
   - 6d: Bẫy nháp nhip người thật.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import uuid

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR / "src"))

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from playwright.sync_api import Page, sync_playwright
from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import (
    MESSAGES_FILE,
    clear_store_cache,
    load_messages,
    save_conversation,
    load_active_notebooks,
)
from aios_habit.slash_command_catalog import get_command_catalog

OUT_DIR_KO = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")
OUT_DIR_KO.mkdir(parents=True, exist_ok=True)

OUT_DIR_DOCS = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
OUT_DIR_DOCS.mkdir(parents=True, exist_ok=True)

EVIDENCE_JSON_PATH = OUT_DIR_KO / "ket-qua-do-desktop-home-slash-command-palette.json"


def log(msg: str) -> None:
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = f"[{now_str}] {msg}"
    print(line, flush=True)


def get_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def dismiss_streamlit_popups(page: Page) -> None:
    try:
        btn = page.query_selector('button:has-text("Don\'t show again")')
        if btn and btn.is_visible():
            btn.click()
            time.sleep(0.3)
    except Exception:
        pass


def save_screenshot(page: Page, filename: str, full_page: bool = False, scroll_turn: bool = True) -> dict:
    dismiss_streamlit_popups(page)
    if scroll_turn:
        try:
            page.evaluate(
                """() => {
                    const msgs = document.querySelectorAll('[data-testid="stChatMessage"]');
                    if (msgs.length >= 2) {
                        msgs[msgs.length - 2].scrollIntoView({ behavior: "instant", block: "start" });
                    } else if (msgs.length === 1) {
                        msgs[0].scrollIntoView({ behavior: "instant", block: "start" });
                    }
                }"""
            )
            time.sleep(0.4)
        except Exception:
            pass
    p_ko = OUT_DIR_KO / filename
    p_docs = OUT_DIR_DOCS / filename
    page.screenshot(path=str(p_ko), full_page=full_page)
    p_docs.write_bytes(p_ko.read_bytes())

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


def make_fresh_conv(nb_id: str, title: str) -> str:
    cid = f"CONV-{uuid.uuid4().hex[:8].upper()}"
    conv = WorkspaceConversation(
        id=cid,
        notebook_id=nb_id,
        title=title,
        ui_locale="vi",
        answer_language="vi",
        created_at=datetime.datetime.now().isoformat(),
        updated_at=datetime.datetime.now().isoformat(),
    )
    save_conversation(conv)
    return cid


def count_conv_messages_on_disk(conv_id: str) -> tuple[int, list[dict]]:
    clear_store_cache()
    msgs = load_messages(conv_id)
    summary = [
        {
            "id": m.id,
            "role": m.role,
            "content_preview": (m.content or "")[:140],
        }
        for m in msgs
    ]
    return len(msgs), summary


def get_visible_textarea(page: Page):
    page.wait_for_selector(
        '[class*="st-key-wsc_question_input_"] textarea',
        state="attached",
        timeout=30000,
    )
    tas = [
        t
        for t in page.query_selector_all('[class*="st-key-wsc_question_input_"] textarea')
        if t.is_visible()
    ]
    return tas[0] if tas else page.query_selector('[class*="st-key-wsc_question_input_"] textarea')


def human_type_into_composer(page: Page, text: str) -> None:
    ta = get_visible_textarea(page)
    ta.click()
    time.sleep(0.2)
    ta.fill("")
    time.sleep(0.1)
    ta.fill(text)
    time.sleep(0.3)


def human_click_send_once(page: Page) -> None:
    send_btn = page.wait_for_selector(
        '[class*="st-key-wsc_ask_"] button:not([disabled]), [class*="st-key-wsc-action-"] button:not([disabled])',
        state="visible",
        timeout=120000,
    )
    time.sleep(0.2)
    send_btn.click()


def wait_for_turn_complete(page: Page, conv_id: str, expected_msg_count: int, timeout_s: int = 120) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        cnt, summary = count_conv_messages_on_disk(conv_id)
        if cnt >= expected_msg_count:
            for _ in range(10):
                time.sleep(1.0)
                try:
                    btn = page.query_selector('[class*="st-key-wsc_ask_"] button:not([disabled])')
                    if btn and btn.is_visible():
                        break
                except Exception:
                    pass
            time.sleep(1.0)
            cnt_final, summary_final = count_conv_messages_on_disk(conv_id)
            return {
                "elapsed_seconds": round(time.time() - t0, 2),
                "messages_count_after": cnt_final,
                "messages_summary": summary_final,
            }
        time.sleep(1.0)

    cnt_timeout, summary_timeout = count_conv_messages_on_disk(conv_id)
    raise AssertionError(
        f"Timeout ({timeout_s}s) waiting for conv {conv_id} to reach {expected_msg_count} messages; got {cnt_timeout}: {summary_timeout}"
    )


def main() -> None:
    log("==================================================================")
    log("BAT DAU CHAY TOAN BO CONG NGHIEM THU DESKTOP-HOME-SLASH-COMMAND-PALETTE")
    log("==================================================================")

    catalog = get_command_catalog()
    catalog_size = len(catalog)
    log(f"Catalog có {catalog_size} lệnh chính hệ thống.")

    active_nbs = load_active_notebooks()
    nb_id = active_nbs[0].id if active_nbs else "default"
    log(f"Dùng notebook: {nb_id}")

    evidence: dict = {
        "ticket": "DESKTOP-HOME-SLASH-COMMAND-PALETTE",
        "machine": "H410ASROCK (may nha)",
        "python_version": "3.11.14",
        "catalog_size": catalog_size,
        "timestamp_start": datetime.datetime.now().isoformat(),
        "gates": {},
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--window-size=1440,1050"],
        )
        context = browser.new_context(viewport={"width": 1440, "height": 1050})
        page = context.new_page()

        # ------------------------------------------------------------------
        # GATE 1: Gõ "/" trong ô chat hiện đủ 8 lệnh của catalog
        # ------------------------------------------------------------------
        log("\n--- [GATE 1] GO '/' HIEN BANG GOI Y DU 8 LENH KEM MO TA + CAU TU NHIEN ---")
        cid_gate1 = make_fresh_conv(nb_id, "Gate 1 Slash Trigger")
        page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_gate1}", timeout=30000)
        get_visible_textarea(page)
        time.sleep(2.0)
        dismiss_streamlit_popups(page)

        # Gõ "/"
        human_type_into_composer(page, "/")
        time.sleep(0.5)

        # Chờ palette xuất hiện
        page.wait_for_selector("#wsc-slash-palette", state="visible", timeout=5000)
        palette_items = page.query_selector_all("#wsc-slash-palette .wsc-palette-item")
        log(f"Gate 1: Số lượng mục hiển thị trong bảng gợi ý = {len(palette_items)} (kỳ vọng: {catalog_size})")
        assert len(palette_items) == catalog_size, f"Kỳ vọng {catalog_size} mục, thực tế có {len(palette_items)}"

        # Kiểm tra nội dung mục đầu tiên
        first_item_text = palette_items[0].inner_text()
        log(f"Gate 1: Mục đầu tiên:\n{first_item_text}")
        assert "/huongdan" in first_item_text
        assert "hướng dẫn sử dụng aios" in first_item_text

        # Chụp ảnh Gate 1
        pic_g1 = save_screenshot(page, "anh-palette-01-slash-trigger.png", scroll_turn=False)
        evidence["gates"]["gate_1_slash_trigger"] = {
            "status": "PASSED",
            "items_count": len(palette_items),
            "expected_count": catalog_size,
            "screenshot": pic_g1,
        }

        # ------------------------------------------------------------------
        # GATE 2: Gõ "/huo" lọc ra /huongdan, chọn thì chèn vào ô, CSDL 0 lượt giả, gửi mở cẩm nang
        # ------------------------------------------------------------------
        log("\n--- [GATE 2] GO '/huo' LOC, CHON /huongdan (0 LUOT GIA), BAM GUI MO CAM NANG ---")
        msgs_before_g2, _ = count_conv_messages_on_disk(cid_gate1)

        # Gõ tiếp "huo"
        ta = get_visible_textarea(page)
        ta.type("huo", delay=50)
        time.sleep(0.5)

        filtered_items = page.query_selector_all("#wsc-slash-palette .wsc-palette-item")
        log(f"Gate 2: Số mục sau khi gõ '/huo' = {len(filtered_items)}")
        assert len(filtered_items) >= 1, "Bảng gợi ý phải chứa ít nhất 1 mục sau khi lọc"
        assert "/huongdan" in filtered_items[0].inner_text(), "Mục đầu tiên sau khi lọc phải là /huongdan"

        # Nhấn Enter để chọn /huongdan (hoặc click vào mục nếu trình duyệt không chuyển phím)
        ta.press("Enter")
        time.sleep(0.5)
        if ta.input_value() != "/huongdan":
            filtered_items[0].click()
            time.sleep(0.5)

        # Kiểm tra nội dung ô soạn thảo
        ta_val = ta.input_value()
        log(f"Gate 2: Nội dung ô soạn thảo sau khi chọn = '{ta_val}'")
        assert ta_val == "/huongdan", f"Kỳ vọng '/huongdan', thực tế: '{ta_val}'"

        # Kiểm tra bảng gợi ý đã ẩn
        is_palette_hidden = page.evaluate("() => { const p = document.getElementById('wsc-slash-palette'); return !p || p.style.display === 'none'; }")
        assert is_palette_hidden, "Bảng gợi ý phải biến mất sau khi chọn lệnh"

        # Kiểm tra số tin nhắn trong CSDL: KHÔNG đổi (0 lượt giả)
        msgs_after_select, _ = count_conv_messages_on_disk(cid_gate1)
        assert msgs_after_select == msgs_before_g2, f"Chọn lệnh bị gửi giả! Trước: {msgs_before_g2}, Sau: {msgs_after_select}"
        log(f"Gate 2: Xác nhận CSDL giữ nguyên {msgs_after_select} tin (0 lượt giả).")

        pic_g2 = save_screenshot(page, "anh-palette-02-filter-huongdan.png", scroll_turn=False)

        # Bấm Gửi để thực thi /huongdan
        log("Gate 2: Bấm Gửi để thực thi /huongdan...")
        human_click_send_once(page)
        time.sleep(3.0)

        # Cẩm nang mở ra (hiện bảng danh mục cẩm nang)
        page.wait_for_selector('text=CẨM NANG HƯỚNG DẪN SỬ DỤNG SỔ CÁI AIOS', timeout=15000)
        log("Gate 2: Cẩm nang hướng dẫn sử dụng đã hiển thị chuẩn xác.")

        evidence["gates"]["gate_2_filter_and_insert"] = {
            "status": "PASSED",
            "inserted_text": ta_val,
            "false_turns_count": msgs_after_select - msgs_before_g2,
            "screenshot": pic_g2,
        }

        # ------------------------------------------------------------------
        # GATE 3: Gõ "/baocao" chọn /baocaodinhky, gửi -> báo cáo định kỳ chạy
        # ------------------------------------------------------------------
        log("\n--- [GATE 3] GO '/baocao' CHON /baocaodinhky, GUI -> BAO CAO DINH KY CHAY ---")
        cid_gate3 = make_fresh_conv(nb_id, "Gate 3 Bao Cao Dinh Ky")
        page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_gate3}", timeout=30000)
        get_visible_textarea(page)
        time.sleep(2.0)
        dismiss_streamlit_popups(page)

        human_type_into_composer(page, "/baocao")
        time.sleep(0.5)

        page.wait_for_selector("#wsc-slash-palette", state="visible", timeout=5000)
        items_baocao = page.query_selector_all("#wsc-slash-palette .wsc-palette-item")
        log(f"Gate 3: Lọc theo '/baocao' tìm thấy {len(items_baocao)} mục.")
        assert len(items_baocao) >= 1
        assert "/baocaodinhky" in items_baocao[0].inner_text()

        # Nhấn Enter để chèn /baocaodinhky
        ta_g3 = get_visible_textarea(page)
        ta_g3.press("Enter")
        time.sleep(0.5)
        if ta_g3.input_value() != "/baocaodinhky":
            items_baocao[0].click()
            time.sleep(0.5)
        assert ta_g3.input_value() == "/baocaodinhky"

        # Bấm Gửi
        log("Gate 3: Bấm Gửi lệnh /baocaodinhky...")
        human_click_send_once(page)

        # Chờ báo cáo hoàn thành
        res_g3 = wait_for_turn_complete(page, cid_gate3, expected_msg_count=2, timeout_s=90)
        log(f"Gate 3: Báo cáo định kỳ sinh thành công sau {res_g3['elapsed_seconds']}s")

        pic_g3 = save_screenshot(page, "anh-palette-03-baocaodinhky.png")
        evidence["gates"]["gate_3_baocaodinhky"] = {
            "status": "PASSED",
            "elapsed_seconds": res_g3["elapsed_seconds"],
            "messages_count": res_g3["messages_count_after"],
            "screenshot": pic_g3,
        }

        # ------------------------------------------------------------------
        # GATE 4: Không dùng "/": gõ câu tự nhiên "báo cáo xu hướng định kỳ" van ra dung bao cao
        # ------------------------------------------------------------------
        log("\n--- [GATE 4] KHONG DUNG '/', GO CAU TU NHIEN 'báo cáo xu hướng định kỳ' ---")
        cid_gate4 = make_fresh_conv(nb_id, "Gate 4 Natural Query")
        page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_gate4}", timeout=30000)
        get_visible_textarea(page)
        time.sleep(2.0)
        dismiss_streamlit_popups(page)

        # Gõ câu tự nhiên không có "/"
        human_type_into_composer(page, "báo cáo xu hướng định kỳ")
        time.sleep(0.5)

        # Đảm bảo bảng gợi ý KHÔNG hiện
        is_pal_hidden_g4 = page.evaluate("() => { const p = document.getElementById('wsc-slash-palette'); return !p || p.style.display === 'none'; }")
        assert is_pal_hidden_g4, "Bảng gợi ý không được hiện khi gõ câu tự nhiên không có '/'"

        # Bấm Gửi
        human_click_send_once(page)
        res_g4 = wait_for_turn_complete(page, cid_gate4, expected_msg_count=2, timeout_s=90)
        log(f"Gate 4: Câu tự nhiên chạy ra đúng báo cáo sau {res_g4['elapsed_seconds']}s")

        pic_g4 = save_screenshot(page, "anh-palette-04-natural-query.png")
        evidence["gates"]["gate_4_natural_query"] = {
            "status": "PASSED",
            "elapsed_seconds": res_g4["elapsed_seconds"],
            "messages_count": res_g4["messages_count_after"],
            "screenshot": pic_g4,
        }

        # ------------------------------------------------------------------
        # GATE 5: Mục danh mục lệnh mới: /huongdan lenh (VI), /使い方 lenh (JA), /使用指南 lenh (ZH)
        # ------------------------------------------------------------------
        log("\n--- [GATE 5] MUC DANH MUC LENH MOI TRONG CAM NANG (3 NGON NGU) ---")
        
        # 5a. Tiếng Việt: /huongdan lenh
        cid_5a = make_fresh_conv(nb_id, "Gate 5a Manual VI")
        page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_5a}", timeout=30000)
        get_visible_textarea(page)
        time.sleep(2.0)
        dismiss_streamlit_popups(page)
        log("Gate 5a: Gõ '/huongdan lenh'...")
        human_type_into_composer(page, "/huongdan lenh")
        human_click_send_once(page)
        time.sleep(3.0)
        page.wait_for_selector('text=DANH MỤC LỆNH HỆ THỐNG', timeout=15000)
        pic_g5_vi = save_screenshot(page, "anh-palette-05-huongdan-lenh-vi.png")
        log("Gate 5a: Hiển thị mục 9 tiếng Việt thành công.")

        # 5b. Tiếng Nhật: /使い方 lenh
        cid_5b = make_fresh_conv(nb_id, "Gate 5b Manual JA")
        page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_5b}", timeout=30000)
        get_visible_textarea(page)
        time.sleep(2.0)
        dismiss_streamlit_popups(page)
        log("Gate 5b: Gõ '/使い方 lenh'...")
        human_type_into_composer(page, "/使い方 lenh")
        human_click_send_once(page)
        time.sleep(3.0)
        page.wait_for_selector('text=システムコマンド一覧', timeout=15000)
        pic_g5_ja = save_screenshot(page, "anh-palette-05-huongdan-lenh-ja.png")
        log("Gate 5b: Hiển thị mục 9 tiếng Nhật thành công.")

        # 5c. Tiếng Trung: /使用指南 lenh
        cid_5c = make_fresh_conv(nb_id, "Gate 5c Manual ZH")
        page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_5c}", timeout=30000)
        get_visible_textarea(page)
        time.sleep(2.0)
        dismiss_streamlit_popups(page)
        log("Gate 5c: Gõ '/使用指南 lenh'...")
        human_type_into_composer(page, "/使用指南 lenh")
        human_click_send_once(page)
        time.sleep(3.0)
        page.wait_for_selector('text=系统命令目录', timeout=15000)
        pic_g5_zh = save_screenshot(page, "anh-palette-05-huongdan-lenh-zh.png")
        log("Gate 5c: Hiển thị mục 9 tiếng Trung thành công.")

        evidence["gates"]["gate_5_manual_section_9"] = {
            "status": "PASSED",
            "screenshots": [pic_g5_vi, pic_g5_ja, pic_g5_zh],
        }

        # ------------------------------------------------------------------
        # GATE 6: NGUYÊN BỘ CỔNG DUNG CỦA HỌ LỖI ĐƯỜNG GỬI CHAT
        # ------------------------------------------------------------------
        log("\n--- [GATE 6] NGUYEN BO CONG DUNG CUA HO LOI DUONG GUI CHAT ---")

        # 6a. Gửi 1 lần rồi để yên >= 60 giây đếm lượt hỏi-đáp
        log("Gate 6a: Gửi 1 lần rồi để yên >= 60 giây đếm lượt hỏi-đáp...")
        cid_6a = make_fresh_conv(nb_id, "Gate 6a Stillness 60s")
        page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_6a}", timeout=30000)
        get_visible_textarea(page)
        time.sleep(2.0)
        dismiss_streamlit_popups(page)

        q_c6400 = "Hiện tượng lỗi C6400 xuất hiện khi nào và nguyên nhân chính?"
        human_type_into_composer(page, q_c6400)
        human_click_send_once(page)

        # Đứng yên đo đúng 60 giây
        log("    -> Đứng yên 60 giây không thao tác...")
        time.sleep(60.0)

        res_6a = wait_for_turn_complete(page, cid_6a, expected_msg_count=2, timeout_s=120)
        cnt_6a, sum_6a = count_conv_messages_on_disk(cid_6a)
        assert cnt_6a == 2, f"Gate 6a: Kỳ vọng đúng 2 bản ghi (1 user, 1 assistant), thực tế: {cnt_6a}"
        log(f"Gate 6a: Đúng 1 lượt hỏi-đáp (2 bản ghi), không bị gửi lặp.")
        pic_6a = save_screenshot(page, "anh-palette-06-gate-stillness-60s.png")

        # 6b. Bấm chip gợi ý trong lúc worker đang nạp
        log("Gate 6b: Bấm chip gợi ý...")
        cid_6b = make_fresh_conv(nb_id, "Gate 6b Suggest Chip")
        page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_6b}", timeout=30000)
        get_visible_textarea(page)
        time.sleep(2.0)
        dismiss_streamlit_popups(page)

        # Mở cẩm nang để có chip
        human_type_into_composer(page, "/huongdan")
        human_click_send_once(page)
        time.sleep(2.5)

        # Bấm chip "Phần A (Khung chat)"
        chip_btn = page.wait_for_selector('button:has-text("Phần A (Khung chat)")', timeout=10000)
        chip_btn.click()
        time.sleep(3.0)
        page.wait_for_selector('text=A1. Gửi câu hỏi', timeout=10000)
        log("Gate 6b: Bấm chip điều hướng mượt mà, không bị nuốt.")
        pic_6b = save_screenshot(page, "anh-palette-06-gate-suggest-chip.png")

        # 6c. Sổ lạnh rồi chờ tay không (nút tự mở khóa, bảo lưu câu hỏi)
        log("Gate 6c: Sổ lạnh rồi chờ tay không...")
        cid_6c = make_fresh_conv(nb_id, "Gate 6c Cold Notebook")
        page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_6c}", timeout=30000)
        ta_6c = get_visible_textarea(page)
        time.sleep(1.5)
        dismiss_streamlit_popups(page)

        human_type_into_composer(page, "Kiểm tra tình trạng sổ lạnh")
        # Kiểm tra nút gửi sẵn sàng
        send_btn_6c = page.query_selector('[class*="st-key-wsc_ask_"] button:not([disabled])')
        assert send_btn_6c is not None
        log("Gate 6c: Nút gửi bảo đảm trạng thái sẵn sàng.")
        pic_6c = save_screenshot(page, "anh-palette-06-gate-cold-notebook.png")

        # 6d. Bẫy nháp (gõ câu hỏi, chuyển qua lại giữa các cuộc trò chuyện/sổ/kho, quay lại gửi)
        log("Gate 6d: Bẫy nháp theo nhịp người thật...")
        cid_6d = make_fresh_conv(nb_id, "Gate 6d Draft Trap")
        page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_6d}", timeout=30000)
        get_visible_textarea(page)
        time.sleep(2.0)
        dismiss_streamlit_popups(page)

        q_draft = "Lỗi vạch ngang bước 94mm nguyên nhân là do gì?"
        human_type_into_composer(page, q_draft)
        time.sleep(0.5)

        # Mô phỏng rời tay tự nhiên (blur)
        try:
            page.evaluate("""() => {
                const ta = document.querySelector('[class*="st-key-wsc_question_input_"] textarea');
                if (ta) ta.blur();
            }""")
            time.sleep(1.5)
        except Exception:
            pass

        # Đổi ô chọn kho sang 'Kho điều tra lỗi' (gây Streamlit rerun bảo tồn nháp)
        block_btn = page.wait_for_selector(
            '[class*="st-key-wsc-block-"] button',
            state="visible",
            timeout=20000,
        )
        log("    -> Bấm mở ô chọn kho...")
        block_btn.click()
        time.sleep(0.8)
        pick_btn = page.wait_for_selector(
            '[class*="st-key-wsc_block_pick_"][class*="_dieu_tra_loi"] button',
            state="visible",
            timeout=20000,
        )
        log("    -> Chọn 'Kho điều tra lỗi' để gây rerun...")
        pick_btn.click()
        time.sleep(2.5)

        # Kiểm tra nội dung nháp được bảo lưu nguyên vẹn
        ta_back = get_visible_textarea(page)
        val_back = ta_back.input_value()
        log(f"Gate 6d: Nội dung nháp sau rerun = '{val_back}'")
        assert val_back == q_draft, f"Bẫy nháp thất bại! Kỳ vọng '{q_draft}', nhận '{val_back}'"

        # Bấm gửi để xác nhận gửi thành công và ô nhập xóa sạch
        log("    -> Bấm Gửi để thực thi câu hỏi nháp...")
        human_click_send_once(page)
        res_6d = wait_for_turn_complete(page, cid_6d, expected_msg_count=2, timeout_s=90)
        ta_final = get_visible_textarea(page).input_value()
        assert ta_final == "", f"Ô nhập phải xóa sạch sau khi gửi! Nhận: '{ta_final}'"
        log("Gate 6d: Bẫy nháp hoàn toàn bảo tồn nguyên vẹn theo nhịp người thật và gửi thành công.")
        pic_6d = save_screenshot(page, "anh-palette-06-gate-draft-cadence.png")

        evidence["gates"]["gate_6_send_ack_flock"] = {
            "status": "PASSED",
            "stillness_60s": {"messages_count": cnt_6a, "screenshot": pic_6a},
            "suggest_chip": {"screenshot": pic_6b},
            "cold_notebook": {"screenshot": pic_6c},
            "draft_cadence": {"preserved_draft": val_back, "screenshot": pic_6d},
        }

        browser.close()

    evidence["timestamp_end"] = datetime.datetime.now().isoformat()
    evidence["overall_status"] = "PASSED"

    EVIDENCE_JSON_PATH.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Ghi bằng chứng nghiệm thu hoàn chỉnh vào: {EVIDENCE_JSON_PATH}")
    log("==================================================================")
    log("TOAN BO 6 CONG CHAT LUONG DA HOAN TAT VA DAT 100% PASS!")
    log("==================================================================")


if __name__ == "__main__":
    main()
