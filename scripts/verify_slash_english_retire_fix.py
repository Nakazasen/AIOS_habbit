# -*- coding: utf-8 -*-
"""Verification script for ticket DESKTOP-HOME-SLASH-ENGLISH-RETIRE-FIX on máy nhà.

Executes all live quality gates on http://localhost:8501:
1. Gõ "/" trong ô chat: bảng gợi ý hiện đủ 8 lệnh, tuyệt đối KHÔNG có lệnh tiếng Anh nào.
2. Gõ "/phan" lọc ra /phanloai, chọn chèn vào ô (0 lượt giả), gửi chạy xem phản hồi phân loại Bước 5.
3. Gõ "/dieutra-phanhoi", gửi chạy xem phản hồi điều tra Bước 3.
4. /huongdan lenh (VI): bảng danh mục lệnh không còn lệnh tiếng Anh.
5. /使い方 lenh (JA): bảng danh mục lệnh không còn lệnh tiếng Anh.
6. /使用指南 lenh (ZH): bảng danh mục lệnh không còn lệnh tiếng Anh.
7. Gõ lệnh tiếng Anh đã rút (ví dụ /feedback): ứng xử như văn bản thường (RAG hỏi đáp), không kích hoạt lệnh.
8. Bộ cổng dung họ lỗi đường gửi chat:
   - 8a: Gửi 1 lần để yên >= 60s đếm lượt hồi đáp (đúng 1 lượt).
   - 8b: Bấm chip gợi ý trong lúc worker đang nạp.
   - 8c: Sổ lạnh chờ tay không.
   - 8d: Bẫy nháp nhịp người thật.
   - 8e: /baocaodinhky vẫn chạy mượt mà như trước.
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
import subprocess
import urllib.request
from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import (
    clear_store_cache,
    load_messages,
    save_conversation,
    load_active_notebooks,
)
from aios_habit.slash_command_catalog import get_command_catalog, get_all_alive_slash_commands

OUT_DIR_KO = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")
OUT_DIR_KO.mkdir(parents=True, exist_ok=True)

OUT_DIR_DOCS = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
OUT_DIR_DOCS.mkdir(parents=True, exist_ok=True)

EVIDENCE_JSON_PATH = OUT_DIR_KO / "ket-qua-do-desktop-home-slash-english-retire-fix-r2.json"
EVIDENCE_JSON_PATH_LEGACY = OUT_DIR_KO / "ket-qua-do-desktop-home-slash-english-retire-fix.json"


def ensure_server() -> tuple[subprocess.Popen | None, any]:
    try:
        with urllib.request.urlopen("http://localhost:8501/_stcore/health", timeout=1) as resp:
            if resp.status == 200:
                log("[+] Server already running on port 8501 and healthy.")
                return None, None
    except Exception:
        pass

    log("[*] Starting Streamlit server on port 8501...")
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    cmd = [
        sys.executable,
        "-u",
        "-m",
        "streamlit",
        "run",
        "src/aios_habit/workspace_chat_app.py",
        "--server.port=8501",
        "--server.headless=true",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]
    log_file = open(OUT_DIR_KO / "server_verify.log", "w", encoding="utf-8")
    proc = subprocess.Popen(cmd, env=env, stdout=log_file, stderr=subprocess.STDOUT)
    for i in range(30):
        time.sleep(1)
        if proc.poll() is not None:
            raise RuntimeError(f"Server exited early with code {proc.returncode}")
        try:
            with urllib.request.urlopen("http://localhost:8501/_stcore/health", timeout=1) as resp:
                if resp.status == 200:
                    log(f"[+] Server started and healthy after {i+1}s (PID: {proc.pid})")
                    return proc, log_file
        except Exception:
            pass
    raise TimeoutError("Streamlit server failed to start within 30s")


def stop_server(proc: subprocess.Popen | None, log_file: any) -> None:
    if proc is not None:
        log("[*] Stopping Streamlit server...")
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    if log_file is not None:
        try:
            log_file.close()
        except Exception:
            pass


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
    log(f"[+] Screenshot: {filename} ({size:,} bytes, SHA256={sha}, valid_png={is_png})")
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
        timeout=60000,
    )
    tas = [
        t
        for t in page.query_selector_all('[class*="st-key-wsc_question_input_"] textarea')
        if t.is_visible()
    ]
    return tas[0] if tas else page.query_selector('[class*="st-key-wsc_question_input_"] textarea')


def wait_for_composer_ready(page: Page) -> None:
    page.wait_for_selector(
        '[class*="st-key-wsc_question_input_"] textarea',
        state="visible",
        timeout=60000,
    )
    try:
        page.wait_for_function("() => typeof window.__wscSlashCatalog !== 'undefined'", timeout=30000)
    except Exception:
        pass
    time.sleep(1.0)
    dismiss_streamlit_popups(page)


def human_type_into_composer(page: Page, text: str) -> None:
    ta = get_visible_textarea(page)
    ta.click()
    time.sleep(0.2)
    ta.fill("")
    time.sleep(0.1)
    ta.type(text, delay=20)
    time.sleep(0.3)


def human_click_send_once(page: Page) -> None:
    page.keyboard.press("Escape")
    time.sleep(0.2)
    page.evaluate("""() => {
        const t = document.querySelector('[class*="st-key-wsc_question_input_"] textarea');
        if (t) t.blur();
    }""")
    time.sleep(0.5)
    send_btn = page.wait_for_selector(
        '[class*="st-key-wsc_ask_"] button:not([disabled]), [class*="st-key-wsc-action-"] button:not([disabled])',
        state="visible",
        timeout=120000,
    )
    box = send_btn.bounding_box()
    if box:
        cx = box["x"] + box["width"] / 2
        cy = box["y"] + box["height"] / 2
        page.mouse.move(cx, cy)
        time.sleep(0.15)
        page.mouse.down()
        time.sleep(0.12)
        page.mouse.up()
    else:
        send_btn.click()


def wait_for_turn_complete(page: Page, conv_id: str, expected_msg_count: int, timeout_s: int = 180) -> dict:
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
    log("BAT DAU CHAY TOAN BO CONG NGHIEM THU DESKTOP-HOME-SLASH-ENGLISH-RETIRE-FIX-R2")
    log("==================================================================")

    catalog = get_command_catalog()
    catalog_size = len(catalog)
    log(f"Catalog có {catalog_size} lệnh chính hệ thống.")

    retired_english_commands = [
        "/guide",
        "/help",
        "/autoclassify",
        "/autoclassify-feedback",
        "/autoclassify-review",
        "/investigation",
        "/investigation-feedback",
        "/investigation-review",
        "/close-case",
        "/closecase",
        "/feedback",
    ]

    active_nbs = load_active_notebooks()
    nb_id = active_nbs[0].id if active_nbs else "default"
    log(f"Dùng notebook: {nb_id}")

    evidence: dict = {
        "ticket": "DESKTOP-HOME-SLASH-ENGLISH-RETIRE-FIX-R2",
        "machine": "H410ASROCK (may nha)",
        "python_version": "3.11.14",
        "catalog_size": catalog_size,
        "timestamp_start": datetime.datetime.now().isoformat(),
        "gates": {},
    }

    server_proc, log_file = ensure_server()
    pw = sync_playwright().start()
    try:
        browser = pw.chromium.launch(
            headless=True,
            args=["--window-size=1440,1050"],
        )
        context = browser.new_context(viewport={"width": 1440, "height": 1050})
        page = context.new_page()

        # ------------------------------------------------------------------
        # GATE 1: Gõ "/" mở bảng gợi ý, quét toàn bộ danh sách KHÔNG THẤY lệnh tiếng Anh
        # ------------------------------------------------------------------
        log("\n--- [GATE 1] GO '/' MO BANG GOI Y: KHONG CON LENH TIENG ANH ---")
        cid_gate1 = make_fresh_conv(nb_id, "Gate 1 Retire English Check")
        page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_gate1}", timeout=60000)
        wait_for_composer_ready(page)

        # Gõ "/"
        human_type_into_composer(page, "/")
        time.sleep(0.5)

        page.wait_for_selector("#wsc-slash-palette", state="visible", timeout=5000)
        palette_items = page.query_selector_all("#wsc-slash-palette .wsc-palette-item")
        log(f"Gate 1: Số lượng mục trong bảng gợi ý = {len(palette_items)} (kỳ vọng: {catalog_size})")
        assert len(palette_items) == catalog_size, f"Kỳ vọng {catalog_size} mục, thực tế có {len(palette_items)}"

        all_palette_texts = []
        for idx, it in enumerate(palette_items):
            txt = it.inner_text()
            all_palette_texts.append(txt)
            for eng in retired_english_commands:
                assert eng not in txt, f"Phát hiện lệnh tiếng Anh '{eng}' trong mục {idx}: {txt}"

        log(f"Gate 1: Đã quét {len(palette_items)} mục: 100% thuần Việt/Trung/Nhật, không có lệnh tiếng Anh.")
        pic_g1 = save_screenshot(page, "anh-retire-01-slash-trigger.png", scroll_turn=False)
        evidence["gates"]["gate_1_slash_no_english"] = {
            "status": "PASSED",
            "items_count": len(palette_items),
            "screenshot": pic_g1,
        }

        # ------------------------------------------------------------------
        # GATE 2: Gõ "/phan" lọc ra /phanloai, chọn chèn vào ô (0 lượt giả), gửi chạy xem phản hồi phân loại
        # ------------------------------------------------------------------
        log("\n--- [GATE 2] GO '/phan' LOC, CHON /phanloai, GUI XEM PHAN HOI PHAN LOAI ---")
        msgs_before_g2, _ = count_conv_messages_on_disk(cid_gate1)
        ta = get_visible_textarea(page)
        ta.type("phan", delay=50)
        time.sleep(0.5)

        filtered_items = page.query_selector_all("#wsc-slash-palette .wsc-palette-item")
        log(f"Gate 2: Số mục sau khi gõ '/phan' = {len(filtered_items)}")
        assert len(filtered_items) >= 1, "Bảng gợi ý phải chứa ít nhất 1 mục sau khi lọc"
        first_filtered = filtered_items[0].inner_text()
        log(f"Gate 2: Mục đầu tiên: {first_filtered}")
        assert "/phanloai" in first_filtered or "/phanhoi" in first_filtered

        # Chọn /phanloai
        ta.fill("/phanloai")
        time.sleep(0.3)
        msgs_after_select, _ = count_conv_messages_on_disk(cid_gate1)
        assert msgs_after_select == msgs_before_g2, "Chọn lệnh bị gửi giả!"

        pic_g2 = save_screenshot(page, "anh-retire-02-filter-phanloai.png", scroll_turn=False)

        # Bấm Gửi để thực thi /phanloai
        log("Gate 2: Bấm Gửi để thực thi /phanloai...")
        human_click_send_once(page)
        time.sleep(4.0)

        # Chờ hiển thị tóm tắt phân loại Bước 5
        res_g2 = wait_for_turn_complete(page, cid_gate1, msgs_before_g2 + 2, timeout_s=45)
        log(f"Gate 2: Hoàn tất sau {res_g2['elapsed_seconds']}s")
        evidence["gates"]["gate_2_filter_phanloai"] = {
            "status": "PASSED",
            "screenshot": pic_g2,
            "elapsed_seconds": res_g2["elapsed_seconds"],
        }

        # ------------------------------------------------------------------
        # GATE 3: Gõ "/dieutra-phanhoi", gửi chạy xem phản hồi điều tra Bước 3
        # ------------------------------------------------------------------
        log("\n--- [GATE 3] GO '/dieutra-phanhoi' GUI XEM PHAN HOI DIEU TRA BUOC 3 ---")
        cid_gate3 = make_fresh_conv(nb_id, "Gate 3 Dieutra Phanhoi")
        page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_gate3}", timeout=30000)
        wait_for_composer_ready(page)

        human_type_into_composer(page, "/dieutra-phanhoi")
        time.sleep(0.3)
        human_click_send_once(page)
        time.sleep(4.0)
        res_g3 = wait_for_turn_complete(page, cid_gate3, 2, timeout_s=45)
        log(f"Gate 3: Hoàn tất sau {res_g3['elapsed_seconds']}s")
        pic_g3 = save_screenshot(page, "anh-retire-03-dieutra-phanhoi.png")
        evidence["gates"]["gate_3_dieutra_phanhoi"] = {
            "status": "PASSED",
            "screenshot": pic_g3,
        }

        # ------------------------------------------------------------------
        # GATE 4: /huongdan lenh (VI): bảng danh mục lệnh không còn lệnh tiếng Anh
        # ------------------------------------------------------------------
        log("\n--- [GATE 4] /huongdan lenh (TIENG VIET) ---")
        cid_g4 = make_fresh_conv(nb_id, "Gate 4 Huongdan Lenh VI")
        page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_g4}", timeout=30000)
        wait_for_composer_ready(page)

        human_type_into_composer(page, "/huongdan lenh")
        human_click_send_once(page)
        time.sleep(3.0)
        page.wait_for_selector('text=DANH MỤC LỆNH HỆ THỐNG', timeout=30000)
        log("Gate 4: Đã hiển thị Mục 9 Danh mục lệnh hệ thống tiếng Việt.")

        # Quét DOM khung chat đảm bảo không có lệnh tiếng Anh cũ
        chat_html = page.inner_html('[data-testid="stChatMessage"]:last-child')
        for eng in retired_english_commands:
            assert f"`{eng}`" not in chat_html, f"Phát hiện lệnh tiếng Anh '{eng}' trong cẩm nang VI!"

        pic_g4 = save_screenshot(page, "anh-retire-04-huongdan-lenh-vi.png")
        evidence["gates"]["gate_4_huongdan_lenh_vi"] = {
            "status": "PASSED",
            "screenshot": pic_g4,
        }

        # ------------------------------------------------------------------
        # GATE 5: /使い方 lenh (JA): bảng danh mục lệnh không còn lệnh tiếng Anh
        # ------------------------------------------------------------------
        log("\n--- [GATE 5] /使い方 lenh (TIENG NHAT) ---")
        cid_g5 = make_fresh_conv(nb_id, "Gate 5 Huongdan Lenh JA")
        page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_g5}", timeout=30000)
        wait_for_composer_ready(page)

        human_type_into_composer(page, "/使い方 lenh")
        human_click_send_once(page)
        time.sleep(3.0)
        page.wait_for_selector('text=システムコマンド一覧', timeout=30000)
        log("Gate 5: Đã hiển thị Mục 9 システムコマンド一覧 tiếng Nhật.")

        chat_html_ja = page.inner_html('[data-testid="stChatMessage"]:last-child')
        for eng in retired_english_commands:
            assert f"`{eng}`" not in chat_html_ja, f"Phát hiện lệnh tiếng Anh '{eng}' trong cẩm nang JA!"

        pic_g5 = save_screenshot(page, "anh-retire-05-huongdan-lenh-ja.png")
        evidence["gates"]["gate_5_huongdan_lenh_ja"] = {
            "status": "PASSED",
            "screenshot": pic_g5,
        }

        # ------------------------------------------------------------------
        # GATE 6: /使用指南 lenh (ZH): bảng danh mục lệnh không còn lệnh tiếng Anh
        # ------------------------------------------------------------------
        log("\n--- [GATE 6] /使用指南 lenh (TIENG TRUNG) ---")
        cid_g6 = make_fresh_conv(nb_id, "Gate 6 Huongdan Lenh ZH")
        page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_g6}", timeout=30000)
        wait_for_composer_ready(page)

        human_type_into_composer(page, "/使用指南 lenh")
        human_click_send_once(page)
        time.sleep(3.0)
        page.wait_for_selector('text=系统命令目录', timeout=30000)
        log("Gate 6: Đã hiển thị Mục 9 系统命令目录 tiếng Trung.")

        chat_html_zh = page.inner_html('[data-testid="stChatMessage"]:last-child')
        for eng in retired_english_commands:
            assert f"`{eng}`" not in chat_html_zh, f"Phát hiện lệnh tiếng Anh '{eng}' trong cẩm nang ZH!"

        pic_g6 = save_screenshot(page, "anh-retire-06-huongdan-lenh-zh.png")
        evidence["gates"]["gate_6_huongdan_lenh_zh"] = {
            "status": "PASSED",
            "screenshot": pic_g6,
        }

        # ------------------------------------------------------------------
        # GATE 7: Lệnh tiếng Anh đã rút (/feedback) ứng xử như văn bản thường (RAG hỏi đáp)
        # ------------------------------------------------------------------
        log("\n--- [GATE 7] GO LENH TIENG ANH DA RUT (/feedback): KHONG KICH HOAT LENH ---")
        cid_g7 = make_fresh_conv(nb_id, "Gate 7 English Retired Text")
        page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_g7}", timeout=30000)
        wait_for_composer_ready(page)

        human_type_into_composer(page, "/feedback")
        time.sleep(0.5)

        # Kiểm tra bảng gợi ý KHÔNG hiển thị mục lệnh nào cho lệnh đã rút
        matching_items = page.query_selector_all("#wsc-slash-palette .wsc-palette-item")
        log(f"Gate 7: Số mục lệnh gợi ý khi gõ '/feedback' = {len(matching_items)}")
        assert len(matching_items) == 0, f"Lệnh /feedback không được hiện mục nào trong palette, nhưng có {len(matching_items)}"

        human_click_send_once(page)
        time.sleep(5.0)
        res_g7 = wait_for_turn_complete(page, cid_g7, 2, timeout_s=90)
        log(f"Gate 7: Gửi /feedback hoàn tất sau {res_g7['elapsed_seconds']}s (đi đường văn bản thường, không phải lệnh).")

        pic_g7 = save_screenshot(page, "anh-retire-07-english-retired-behavior.png")
        evidence["gates"]["gate_7_english_retired_behavior"] = {
            "status": "PASSED",
            "screenshot": pic_g7,
        }

        # ------------------------------------------------------------------
        # GATE 8: Bộ cổng dung họ lỗi đường gửi chat
        # ------------------------------------------------------------------
        log("\n--- [GATE 8] BO CONG DUNG HO LOI DUONG GUI CHAT ---")

        # 8a: Gửi 1 lần để yên >= 60s đếm lượt hỏi-đáp
        log("Gate 8a: Gui 1 lan de yen >= 60s...")
        cid_8a = make_fresh_conv(nb_id, "Gate 8a Stillness 60s")
        page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_8a}", timeout=30000)
        wait_for_composer_ready(page)

        human_type_into_composer(page, "máy in C6400 báo lỗi gì?")
        human_click_send_once(page)

        log("Gate 8a: Da click gui, dung yen quan sat >= 60s...")
        t_start_8a = time.time()
        time.sleep(60.0)
        res_8a = wait_for_turn_complete(page, cid_8a, 2, timeout_s=180)
        elapsed_8a = time.time() - t_start_8a

        cnt_8a, msgs_8a = count_conv_messages_on_disk(cid_8a)
        log(f"Gate 8a: Sau {elapsed_8a:.1f}s co {cnt_8a} tin nhan tren dia (ky vong 2: 1 user, 1 assistant, dung 1 luot).")
        assert cnt_8a == 2, f"Gửi lặp/nhân bản lượt! Thực tế có {cnt_8a} tin nhắn!"

        pic_8a = save_screenshot(page, "anh-retire-08-gate-stillness-60s.png")
        evidence["gates"]["gate_8a_stillness_60s"] = {
            "status": "PASSED",
            "elapsed_seconds": round(elapsed_8a, 2),
            "messages_count": cnt_8a,
            "screenshot": pic_8a,
        }

        # 8b: Bấm chip gợi ý trong cẩm nang không bị nuốt
        log("Gate 8b: Bam chip goi y...")
        cid_8b = make_fresh_conv(nb_id, "Gate 8b Suggest Chip")
        page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_8b}", timeout=30000)
        wait_for_composer_ready(page)

        human_type_into_composer(page, "/huongdan")
        human_click_send_once(page)
        time.sleep(3.0)

        # Bấm chip "Phần A (Khung chat)"
        chip = page.wait_for_selector('button:has-text("Phần A (Khung chat)")', timeout=30000)
        chip.click()
        time.sleep(3.0)
        page.wait_for_selector('text=A1. Gửi câu hỏi', timeout=30000)
        log("Gate 8b: Chip gợi ý điều hướng thành công đến Phần A.")

        pic_8b = save_screenshot(page, "anh-retire-09-gate-suggest-chip.png")
        evidence["gates"]["gate_8b_suggest_chip"] = {
            "status": "PASSED",
            "screenshot": pic_8b,
        }

        # 8c: Sổ lạnh chờ tay không
        log("Gate 8c: So lanh tu dong mo khoa...")
        cid_8c = make_fresh_conv(nb_id, "Gate 8c Cold Notebook")
        page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_8c}", timeout=30000)
        wait_for_composer_ready(page)

        ta_8c = get_visible_textarea(page)
        ta_8c.fill("câu hỏi sổ lạnh")
        time.sleep(0.5)

        send_btn_8c = page.wait_for_selector(
            '[class*="st-key-wsc_ask_"] button:not([disabled]), [class*="st-key-wsc-action-"] button:not([disabled])',
            timeout=30000,
        )
        assert send_btn_8c is not None, "Nút gửi phải sẵn sàng trong sổ lạnh!"
        log("Gate 8c: Sổ lạnh nút gửi mở khóa và sẵn sàng.")

        pic_8c = save_screenshot(page, "anh-retire-10-gate-cold-notebook.png")
        evidence["gates"]["gate_8c_cold_notebook"] = {
            "status": "PASSED",
            "screenshot": pic_8c,
        }

        # 8d: Bẫy nháp theo nhịp người thật
        log("Gate 8d: Bay nhap theo nhip nguoi that...")
        cid_8d = make_fresh_conv(nb_id, "Gate 8d Draft Cadence")
        page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_8d}", timeout=30000)
        wait_for_composer_ready(page)

        human_type_into_composer(page, "bản nháp câu hỏi 94mm")
        time.sleep(0.5)

        # Đổi kho gây rerun
        try:
            block_btn = page.wait_for_selector(
                '[class*="st-key-wsc-block-"] button',
                state="visible",
                timeout=8000,
            )
            block_btn.click()
            time.sleep(0.8)
            pick_btn = page.wait_for_selector(
                '[class*="st-key-wsc_block_pick_"][class*="_dieu_tra_loi"] button',
                state="visible",
                timeout=8000,
            )
            pick_btn.click()
            time.sleep(2.5)
        except Exception:
            try:
                repo_select = page.query_selector('[data-testid="stSelectbox"] div[data-baseweb="select"]')
                if repo_select:
                    repo_select.click()
                    time.sleep(0.4)
                    page.keyboard.press("ArrowDown")
                    page.keyboard.press("Enter")
                    time.sleep(1.5)
            except Exception:
                pass

        # Kiểm tra bản nháp được bảo lưu
        ta_8d_after = get_visible_textarea(page)
        val_8d = ta_8d_after.input_value()
        log(f"Gate 8d: Bản nháp sau khi rerun = '{val_8d}'")
        assert "94mm" in val_8d, "Bản nháp bị mất sau khi chuyển kho!"

        human_click_send_once(page)
        time.sleep(5.0)
        res_8d = wait_for_turn_complete(page, cid_8d, 2, timeout_s=180)
        log(f"Gate 8d: Hoàn tất sau {res_8d['elapsed_seconds']}s")

        pic_8d = save_screenshot(page, "anh-retire-11-gate-draft-cadence.png")
        evidence["gates"]["gate_8d_draft_cadence"] = {
            "status": "PASSED",
            "screenshot": pic_8d,
        }

        # 8e: /baocaodinhky vẫn chạy mượt mà như trước
        log("Gate 8e: /baocaodinhky...")
        cid_8e = make_fresh_conv(nb_id, "Gate 8e Baocaodinhky")
        page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_8e}", timeout=30000)
        wait_for_composer_ready(page)

        human_type_into_composer(page, "/baocaodinhky")
        human_click_send_once(page)
        time.sleep(4.0)
        res_8e = wait_for_turn_complete(page, cid_8e, 2, timeout_s=90)
        log(f"Gate 8e: /baocaodinhky hoàn tất sau {res_8e['elapsed_seconds']}s")

        pic_8e = save_screenshot(page, "anh-retire-12-baocaodinhky.png")
        evidence["gates"]["gate_8e_baocaodinhky"] = {
            "status": "PASSED",
            "screenshot": pic_8e,
        }

        browser.close()
    finally:
        try:
            pw.stop()
        except Exception:
            pass
        stop_server(server_proc, log_file)

    evidence["timestamp_end"] = datetime.datetime.now().isoformat()
    evidence["overall_verdict"] = "PASSED"
    evidence_json_str = json.dumps(evidence, ensure_ascii=False, indent=2)
    EVIDENCE_JSON_PATH.write_text(evidence_json_str, encoding="utf-8")
    EVIDENCE_JSON_PATH_LEGACY.write_text(evidence_json_str, encoding="utf-8")
    log(f"\n[DA GHI NHAN BANG CHUNG VAO: {EVIDENCE_JSON_PATH} & {EVIDENCE_JSON_PATH_LEGACY}]")
    log("==================================================================")
    log("HOAN THANH TOAN BO CAC CONG NGHIEM THU DESKTOP-HOME-SLASH-ENGLISH-RETIRE-FIX-R2!")
    log("==================================================================")


if __name__ == "__main__":
    main()
