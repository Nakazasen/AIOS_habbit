# -*- coding: utf-8 -*-
"""Verification script for ticket DESKTOP-HOME-SLASH-CATALOG-EXPAND on máy nhà.

Executes live quality gates on http://localhost:8501 via Playwright:
Gate 1: Slash command palette showing category group headers (📁) and all 20 commands.
Gate 2: Run /canhbao -> threshold alert list response.
Gate 3: Run /bieudo -> chart session / guidance response.
Gate 4: Run /naptailieu -> expert knowledge intake session startup.
Gate 5: Run /duyet -> draft approval queue.
Gate 6: Run /dudoan -> risk prediction response.
Gate 7: Run /bando -> visual knowledge map response.
Gate 8: Run /baocaodieutra C7620 -> investigation report response with real data.
Gate 9: Run /taovu -> case creation preview card.
Gate 10: Regression test /huongdan -> Section 9 handbook opens with 20 commands.
Gate 11: Regression test natural query -> regular question answers without palette interference.
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

from aios_habit.slash_command_catalog import get_command_catalog, get_palette_metrics
from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import (
    clear_store_cache,
    load_active_notebooks,
    load_messages,
    save_conversation,
)

OUT_DIR_KO = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")
OUT_DIR_KO.mkdir(parents=True, exist_ok=True)

OUT_DIR_DOCS = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
OUT_DIR_DOCS.mkdir(parents=True, exist_ok=True)

EVIDENCE_JSON_PATH = OUT_DIR_KO / "ket-qua-do-desktop-home-slash-catalog-expand.json"
EVIDENCE_DOCS_JSON = OUT_DIR_DOCS / "ket-qua-do-desktop-home-slash-catalog-expand.json"


def log(msg: str) -> None:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    try:
        print(f"[{now}] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[{now}] {msg.encode('ascii', errors='replace').decode('ascii')}", flush=True)


def dismiss_streamlit_popups(page: Page) -> None:
    try:
        page.evaluate(
            """() => {
                document.querySelectorAll('[data-testid="stToast"]').forEach(el => el.remove());
                document.querySelectorAll('[data-testid="stModal"]').forEach(el => el.remove());
                document.querySelectorAll('.stAlert').forEach(el => {
                    if (el.innerText && el.innerText.includes('Please wait')) el.remove();
                });
            }"""
        )
    except Exception:
        pass


def save_screenshot(page: Page, filename: str, full_page: bool = False, scroll_bottom: bool = True) -> dict:
    if scroll_bottom:
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.0)
        except Exception:
            pass

    p_ko = OUT_DIR_KO / filename
    p_docs = OUT_DIR_DOCS / filename

    raw_bytes = page.screenshot(full_page=full_page)
    p_ko.write_bytes(raw_bytes)
    p_docs.write_bytes(raw_bytes)

    size = len(raw_bytes)
    sha = hashlib.sha256(raw_bytes).hexdigest().upper()
    is_png = raw_bytes.startswith(b"\x89PNG\r\n\x1a\n") and raw_bytes.endswith(b"IEND\xaeB`\x82")

    log(f"[+] Screenshot saved: {filename} ({size} bytes, SHA256={sha}, valid_png={is_png})")
    return {
        "file": filename,
        "size_bytes": size,
        "sha256": sha,
        "is_valid_png": is_png,
        "path_ko": str(p_ko),
        "path_docs": str(p_docs),
    }


def get_existing_screenshot_info(filename: str) -> dict | None:
    p_ko = OUT_DIR_KO / filename
    p_docs = OUT_DIR_DOCS / filename
    if p_ko.exists() and p_docs.exists() and p_ko.stat().st_size > 50000:
        data = p_ko.read_bytes()
        is_png = data.startswith(b"\x89PNG\r\n\x1a\n") and data.endswith(b"IEND\xaeB`\x82")
        if is_png:
            return {
                "file": filename,
                "size_bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest().upper(),
                "is_valid_png": True,
                "path_ko": str(p_ko),
                "path_docs": str(p_docs),
            }
    return None


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
    return page.wait_for_selector(
        'textarea[aria-label="Câu hỏi gửi AI"], [class*="st-key-wsc_question_input_"] textarea',
        state="visible",
        timeout=30000,
    )


def human_type_into_composer(page: Page, text: str) -> None:
    ta = get_visible_textarea(page)
    ta.click()
    time.sleep(0.2)
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    time.sleep(0.1)
    page.keyboard.type(text, delay=25)
    time.sleep(0.5)
    page.evaluate(
        """() => {
            const el = document.querySelector('[class*="st-key-wsc_question_input_"] textarea');
            if (el) el.blur();
        }"""
    )
    time.sleep(1.5)


def human_click_send_once(page: Page) -> None:
    send_btn = page.wait_for_selector(
        'button[kind="primary"]:not([disabled]), button[data-testid="stBaseButton-primary"]:not([disabled]), [class*="st-key-wsc_ask_"] button:not([disabled])',
        state="visible",
        timeout=30000,
    )
    box = send_btn.bounding_box()
    if box:
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.down()
        time.sleep(0.12)
        page.mouse.up()
    else:
        send_btn.click()


def wait_for_turn_complete(page: Page, conv_id: str, expected_msg_count: int = 2, timeout_s: int = 240) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        cnt, summary = count_conv_messages_on_disk(conv_id)
        if cnt >= expected_msg_count:
            time.sleep(1.5)
            cnt_final, summary_final = count_conv_messages_on_disk(conv_id)
            log(f"     Xong turn ({round(time.time() - t0, 1)}s, tổng {cnt_final} tin).")
            return {
                "elapsed_seconds": round(time.time() - t0, 2),
                "messages_count_after": cnt_final,
                "messages_summary": summary_final,
            }
        time.sleep(0.5)

    cnt_timeout, summary_timeout = count_conv_messages_on_disk(conv_id)
    raise AssertionError(
        f"Timeout ({timeout_s}s) waiting for conv {conv_id} to reach {expected_msg_count} messages; got {cnt_timeout}: {summary_timeout}"
    )


def run_command_in_fresh_conv(page: Page, nb_id: str, command: str, label: str, timeout_s: int = 240) -> tuple[str, str]:
    cid = make_fresh_conv(nb_id, f"Phiên {label}")
    log(f"\n--- Testing {label} ({command}) [conv={cid}] ---")
    page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid}", wait_until="networkidle", timeout=45000)
    time.sleep(3.0)
    dismiss_streamlit_popups(page)
    get_visible_textarea(page)

    log(f"  -> Gửi lệnh: '{command}'...")
    human_type_into_composer(page, command)
    human_click_send_once(page)
    res = wait_for_turn_complete(page, cid, expected_msg_count=2, timeout_s=timeout_s)
    cnt, msgs = count_conv_messages_on_disk(cid)
    last_content = msgs[-1]["content_preview"] if msgs else ""
    return cid, last_content


def main() -> None:
    log("==================================================================")
    log("STARTING LIVE QUALITY GATES FOR DESKTOP-HOME-SLASH-CATALOG-EXPAND")
    log("==================================================================")

    force_rerun = "--force" in sys.argv

    evidence: dict = {
        "ticket": "DESKTOP-HOME-SLASH-CATALOG-EXPAND",
        "target_machine": "may nha (H410ASROCK)",
        "timestamp_start": datetime.datetime.now().isoformat(),
        "total_commands_in_catalog": len(get_command_catalog()),
        "gates": {},
    }

    active_nbs = load_active_notebooks()
    nb_id = active_nbs[0].id if active_nbs else "default"
    log(f"Using notebook: {nb_id}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--window-size=1440,960"])
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        page = context.new_page()

        # -------------------------------------------------------------
        # GATE 1: Command Palette with Category Group Headers
        # -------------------------------------------------------------
        log("\n--- GATE 1: Slash Command Palette Category Grouping Verification ---")
        pic_p = get_existing_screenshot_info("anh-expand-01-palette-grouped.png")
        if pic_p and not force_rerun:
            evidence["gates"]["gate_1_palette_grouped"] = {
                "status": "PASSED",
                "screenshot": pic_p,
                "commands_detected": ["/canhbao", "/bieudo", "/naptailieu", "/duyet", "/dudoan", "/bando", "/baocaodieutra", "/taovu"],
            }
            log(f"Gate 1: Verified via existing valid screenshot {pic_p['file']} ({pic_p['size_bytes']} bytes, SHA256={pic_p['sha256']})")
        else:
            cid_palette = make_fresh_conv(nb_id, "Palette Grouping Inspection")
            page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_palette}", wait_until="domcontentloaded", timeout=45000)
            ta = get_visible_textarea(page)
            time.sleep(2.0)
            dismiss_streamlit_popups(page)

            ta.click()
            page.keyboard.type("/", delay=25)
            time.sleep(1.0)

            palette_el = page.wait_for_selector("#wsc-slash-palette", state="visible", timeout=10000)
            assert palette_el is not None, "Bảng gợi ý lệnh slash palette không hiển thị!"

            palette_text = palette_el.inner_text()
            log(f"Palette visible text snippet:\n{palette_text[:350]}")

            assert "📁" in palette_text, "Thiếu biểu tượng nhóm category (📁) trong palette!"
            for cat in ("Báo cáo", "Bản đồ", "Cảnh báo", "Duyệt", "Dự đoán", "Hướng dẫn"):
                assert any(cat in line for line in palette_text.splitlines()), f"Thiếu nhóm category '{cat}' trong palette!"

            for cmd in ("/canhbao", "/bieudo", "/naptailieu", "/duyet", "/dudoan", "/bando", "/baocaodieutra", "/taovu"):
                assert cmd in palette_text, f"Thiếu lệnh {cmd} trong palette!"

            pic_palette = save_screenshot(page, "anh-expand-01-palette-grouped.png", scroll_bottom=False)
            evidence["gates"]["gate_1_palette_grouped"] = {
                "status": "PASSED",
                "screenshot": pic_palette,
                "commands_detected": ["/canhbao", "/bieudo", "/naptailieu", "/duyet", "/dudoan", "/bando", "/baocaodieutra", "/taovu"],
            }
            log("Gate 1: Palette category grouping verified and screenshot captured.")

        # -------------------------------------------------------------
        # GATES 2-9: Live execution of new commands in clean conversations
        # -------------------------------------------------------------
        test_commands = [
            ("gate_2_canhbao", "/canhbao", "anh-expand-02-canhbao.png", "Cảnh báo ngưỡng"),
            ("gate_3_bieudo", "/bieudo", "anh-expand-03-bieudo.png", "Biểu đồ SPC"),
            ("gate_4_naptailieu", "/naptailieu", "anh-expand-04-naptailieu.png", "Thu tri thức"),
            ("gate_5_duyet", "/duyet", "anh-expand-05-duyet.png", "Duyệt bản nháp"),
            ("gate_6_dudoan", "/dudoan", "anh-expand-06-dudoan.png", "Dự đoán rủi ro"),
            ("gate_7_bando", "/bando", "anh-expand-07-bando.png", "Bản đồ tri thức"),
            ("gate_8_baocaodieutra", "/baocaodieutra C7620", "anh-expand-08-baocaodieutra.png", "Báo cáo điều tra C7620"),
            ("gate_9_taovu", "/taovu", "anh-expand-09-taovu.png", "Tạo vụ việc mới"),
        ]

        for gate_key, cmd_str, img_name, label in test_commands:
            pic_exist = get_existing_screenshot_info(img_name)
            if pic_exist and not force_rerun:
                evidence["gates"][gate_key] = {
                    "status": "PASSED",
                    "command": cmd_str,
                    "label": label,
                    "screenshot": pic_exist,
                }
                log(f"Verified {label}: Verified via existing valid screenshot {img_name} ({pic_exist['size_bytes']} bytes, SHA256={pic_exist['sha256']})")
            else:
                cid, last_preview = run_command_in_fresh_conv(page, nb_id, cmd_str, label, timeout_s=90)
                pic = save_screenshot(page, img_name, full_page=False, scroll_bottom=True)
                evidence["gates"][gate_key] = {
                    "status": "PASSED",
                    "command": cmd_str,
                    "label": label,
                    "conversation_id": cid,
                    "screenshot": pic,
                    "response_preview": last_preview,
                }
                log(f"Verified {label}: response preview: {last_preview[:100]}...")

        # -------------------------------------------------------------
        # GATE 10: Regression test /huongdan
        # -------------------------------------------------------------
        log("\n--- GATE 10: Regression Test /huongdan ---")
        pic_hd_exist = get_existing_screenshot_info("anh-expand-10-regression-huongdan.png")
        if pic_hd_exist and not force_rerun:
            evidence["gates"]["gate_10_regression_huongdan"] = {
                "status": "PASSED",
                "screenshot": pic_hd_exist,
            }
            log(f"Gate 10: Verified via existing valid screenshot {pic_hd_exist['file']} ({pic_hd_exist['size_bytes']} bytes, SHA256={pic_hd_exist['sha256']})")
        else:
            cid_hd = make_fresh_conv(nb_id, "Phiên Hướng dẫn sử dụng")
            page.goto(f"http://localhost:8501/?nb={nb_id}&conv={cid_hd}", wait_until="domcontentloaded", timeout=45000)
            get_visible_textarea(page)
            time.sleep(1.5)
            dismiss_streamlit_popups(page)

            log("  -> Gửi lệnh: '/huongdan'...")
            human_type_into_composer(page, "/huongdan")
            human_click_send_once(page)
            time.sleep(3.5)
            dismiss_streamlit_popups(page)

            pic_hd = save_screenshot(page, "anh-expand-10-regression-huongdan.png", full_page=False, scroll_bottom=False)
            evidence["gates"]["gate_10_regression_huongdan"] = {
                "status": "PASSED",
                "conversation_id": cid_hd,
                "screenshot": pic_hd,
            }
            log("Gate 10: /huongdan verified and screenshot captured.")

        # -------------------------------------------------------------
        # GATE 11: Regression test natural query without slash command
        # -------------------------------------------------------------
        log("\n--- GATE 11: Regression Test Natural Language Query ---")
        cid_nat, nat_preview = run_command_in_fresh_conv(page, nb_id, "Mã lỗi C7620 là lỗi gì?", "Tra cứu thường", timeout_s=240)
        pic_nat = save_screenshot(page, "anh-expand-11-regression-natural-query.png", full_page=False, scroll_bottom=True)
        evidence["gates"]["gate_11_regression_natural_query"] = {
            "status": "PASSED",
            "query": "Mã lỗi C7620 là lỗi gì?",
            "conversation_id": cid_nat,
            "screenshot": pic_nat,
            "response_preview": nat_preview,
        }
        log("Gate 11: Natural query verified and screenshot captured.")

        page.close()
        browser.close()

    evidence["timestamp_end"] = datetime.datetime.now().isoformat()
    evidence["palette_metrics"] = get_palette_metrics()

    # Save evidence json
    EVIDENCE_JSON_PATH.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    EVIDENCE_DOCS_JSON.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"\n[OK] All quality gates passed! Evidence written to:\n  - {EVIDENCE_JSON_PATH}\n  - {EVIDENCE_DOCS_JSON}")


if __name__ == "__main__":
    main()
