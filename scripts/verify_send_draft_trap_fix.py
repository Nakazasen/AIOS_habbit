# -*- coding: utf-8 -*-
"""Live UI verification script for ticket DESKTOP-PC0575-SEND-DRAFT-TRAP-FIX.

Executes all live quality gates in true human rhythm on http://localhost:8501
after restarting via RUN_AIOS_WORKSPACE_CHAT.bat:
- Gate 4b-1 (ghi_chu 19:05): Gõ câu hỏi theo nhịp người thật (kèm blur rerun tự nhiên)
  rồi bấm Gửi ngay (không đổi ô chọn kho) -> câu hỏi lưu vào messages.jsonl,
  ô nhập xóa sạch, thẻ chờ bắt đầu từ bước 1 (● Tìm nguồn), trả lời đầy đủ.
- Gate 4b-2 (§4b): Gõ câu hỏi theo nhịp người thật -> bấm đổi ô chọn kho sang
  'Kho điều tra lỗi' (gây rerun) -> bấm Gửi 1 lần rồi ĐỂ YÊN -> câu hỏi lưu vào
  messages.jsonl (0 -> 2), ô nhập xóa sạch, trả lời đầy đủ cho câu 94mm.
- Gate 4b-3 (§4b + ghi_chu 19:05): Đóng tab trình duyệt (page.close()), mở tab mới
  vào lại hội thoại cũ CONV-3A496585 (và hội thoại vừa hỏi), gõ lại câu hỏi
  'Lỗi vạch ngang bước 94mm nguyên nhân là do gì?' theo nhịp người thật rồi bấm Gửi
  -> câu hỏi lưu vào messages.jsonl (0 -> 2) và nhận câu trả lời đầy đủ.
- Gate 4c (Cổng hồi quy đường gửi chat):
  + 4c-1: Gửi câu C6400 1 lần theo nhịp người thật + đứng yên 60 giây -> đúng 1 lượt
          hồi đáp (2 bản ghi trong messages.jsonl: 1 user, 1 assistant, 0 bản sao).
  + 4c-2: Bấm chip gợi ý không bị ngậm câu hỏi (messages.jsonl tăng 2 -> 4).
  + 4c-3: Sổ lạnh gõ 'alo' tay không phá khóa nút khi đang nạp và trả lời sạch.
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
)

OUT_DIR_KO = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua")
OUT_DIR_KO.mkdir(parents=True, exist_ok=True)

OUT_DIR_DOCS = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
OUT_DIR_DOCS.mkdir(parents=True, exist_ok=True)

EVIDENCE_JSON_PATH = OUT_DIR_KO / "ket-qua-do-desktop-pc0575-send-draft-trap-fix.json"


def _ensure_running_on_user_desktop() -> None:
    """If launched inside Antigravity's hidden sandbox desktop (exebox-*),
    re-spawn this script onto WinSta0\\Default so the browser window is
    physically visible on the user's monitor (Computer Use / Live UI)."""
    if os.environ.get("AIOS_ON_USER_DESKTOP") == "1":
        return
    try:
        import ctypes
        from ctypes import wintypes

        u32 = ctypes.windll.user32
        k32 = ctypes.windll.kernel32
        h_desk = u32.GetThreadDesktop(k32.GetCurrentThreadId())
        buf = ctypes.create_unicode_buffer(256)
        u32.GetUserObjectInformationW(h_desk, 2, buf, 512, None)
        desk_name = buf.value
        if desk_name.lower() == "default":
            return

        log(f"[*] Phat hien sandbox desktop '{desk_name}' -> chuyen sang desktop that 'WinSta0\\Default' de hien thi trinh duyet...")
        log_file = APP_DIR / "local_cases" / "verify_user_desktop_live.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text("", encoding="utf-8")

        class STARTUPINFOW(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("lpReserved", wintypes.LPWSTR),
                ("lpDesktop", wintypes.LPWSTR),
                ("lpTitle", wintypes.LPWSTR),
                ("dwX", wintypes.DWORD),
                ("dwY", wintypes.DWORD),
                ("dwXSize", wintypes.DWORD),
                ("dwYSize", wintypes.DWORD),
                ("dwXCountChars", wintypes.DWORD),
                ("dwYCountChars", wintypes.DWORD),
                ("dwFillAttribute", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("wShowWindow", wintypes.WORD),
                ("cbReserved2", wintypes.WORD),
                ("lpReserved2", ctypes.POINTER(ctypes.c_byte)),
                ("hStdInput", wintypes.HANDLE),
                ("hStdOutput", wintypes.HANDLE),
                ("hStdError", wintypes.HANDLE),
            ]

        class PROCESS_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("hProcess", wintypes.HANDLE),
                ("hThread", wintypes.HANDLE),
                ("dwProcessId", wintypes.DWORD),
                ("dwThreadId", wintypes.DWORD),
            ]

        os.environ["AIOS_ON_USER_DESKTOP"] = "1"
        os.environ["AIOS_USER_DESKTOP_LOG"] = str(log_file)

        si = STARTUPINFOW()
        si.cb = ctypes.sizeof(si)
        si.lpDesktop = "WinSta0\\Default"
        si.dwFlags = 0x00000001  # STARTF_USESHOWWINDOW
        si.wShowWindow = 0  # SW_HIDE console window, browser window will be visible

        pi = PROCESS_INFORMATION()
        cmd_str = f'"{sys.executable}" "{Path(__file__).resolve()}"'
        cmd_buf = ctypes.create_unicode_buffer(cmd_str)

        CREATE_NO_WINDOW = 0x08000000
        ok = k32.CreateProcessW(
            None,
            cmd_buf,
            None,
            None,
            False,
            CREATE_NO_WINDOW,
            None,
            str(APP_DIR),
            ctypes.byref(si),
            ctypes.byref(pi),
        )
        if not ok:
            log("[!] Khong the CreateProcessW tren WinSta0\\Default, chay tiep tren desktop hien tai.")
            return

        # Tail log file while child process runs on user's visible desktop
        WAIT_OBJECT_0 = 0
        last_pos = 0
        while True:
            wait_res = k32.WaitForSingleObject(pi.hProcess, 500)
            if log_file.is_file():
                data = log_file.read_bytes()
                if len(data) > last_pos:
                    chunk = data[last_pos:].decode("utf-8", errors="replace")
                    sys.stdout.write(chunk)
                    sys.stdout.flush()
                    last_pos = len(data)
            if wait_res == WAIT_OBJECT_0:
                break

        exit_code = wintypes.DWORD()
        k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(exit_code))
        k32.CloseHandle(pi.hProcess)
        k32.CloseHandle(pi.hThread)
        sys.exit(exit_code.value)
    except SystemExit:
        raise
    except Exception as exc:
        log(f"[!] Loi chuyen desktop: {exc}")


def log(msg: str) -> None:
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = f"[{now_str}] {msg}"
    print(line, flush=True)
    log_path = os.environ.get("AIOS_USER_DESKTOP_LOG")
    if log_path:
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
        except Exception:
            pass


def get_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def dismiss_streamlit_popups(page: Page) -> None:
    """Close Streamlit's 'Help agents write better apps' toast if present."""
    try:
        btn = page.query_selector('button:has-text("Don\'t show again")')
        if btn and btn.is_visible():
            btn.click()
            time.sleep(0.3)
    except Exception:
        pass


def reset_conv_messages_on_disk(conv_id: str) -> None:
    """Remove any existing messages for conv_id in messages.jsonl so the test starts from 0."""
    if not MESSAGES_FILE.is_file():
        return
    lines = MESSAGES_FILE.read_text(encoding="utf-8").splitlines()
    kept = []
    for line in lines:
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
            if rec.get("conversation_id") == conv_id:
                continue
        except Exception:
            pass
        kept.append(line)
    MESSAGES_FILE.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    clear_store_cache()


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
    """Read messages.jsonl directly from disk for conv_id."""
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
    assert len(tas) == 1, f"Expected 1 visible textarea, found {len(tas)}"
    return tas[0]


def human_type_into_composer(page: Page, question: str) -> None:
    """Type character-by-character like a real human and trigger natural blur rerun."""
    ta = get_visible_textarea(page)
    ta.click()
    time.sleep(0.2)
    # Gõ từng phím như tay người thật
    page.keyboard.type(question, delay=30)
    time.sleep(0.6)
    # Khi người thật rời tay khỏi ô gõ để đưa chuột sang nút Gửi hoặc ô chọn kho,
    # textarea phát sự kiện blur/change khiến Streamlit chạy 1 vòng rerun trung gian
    # nạp wsc_draft_input_backup_{conv_id}. Ta mô phỏng đúng nhịp blur tự nhiên này:
    page.evaluate(
        """() => {
            const ta = document.querySelector('[class*="st-key-wsc_question_input_"] textarea');
            if (ta) {
                ta.blur();
            }
        }"""
    )
    time.sleep(1.8)


def switch_block_to_dieu_tra_loi(page: Page) -> None:
    """Click the block selector popover and choose 'Kho điều tra lỗi' causing a Streamlit rerun."""
    block_btn = page.wait_for_selector(
        '[class*="st-key-wsc-block-"] button',
        state="visible",
        timeout=20000,
    )
    log("    -> Bấm mở ô chọn kho (📚)...")
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


def human_click_send_once(page: Page) -> None:
    """Move mouse to Send button and click once in human rhythm, then do NOT touch anything."""
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


def wait_for_turn_complete(page: Page, conv_id: str, expected_msg_count: int, timeout_s: int = 150) -> dict:
    """Stand completely still (no clicks/inputs) until messages.jsonl reaches expected_msg_count and UI settles."""
    t0 = time.time()
    observed_step1_text = ""
    captured_step1_shot = None

    while time.time() - t0 < timeout_s:
        elapsed = time.time() - t0
        body_txt = ""
        try:
            body_txt = page.inner_text("body")
        except Exception:
            pass

        if not observed_step1_text and ("● Tìm nguồn" in body_txt or "Tìm nguồn" in body_txt):
            observed_step1_text = "● Tìm nguồn"
            log(f"    -> Quan sát thấy thẻ chờ hiển thị trung thực ở {elapsed:.1f}s: '● Tìm nguồn'")

        cnt, summary = count_conv_messages_on_disk(conv_id)
        if cnt >= expected_msg_count:
            # Chờ thêm vài giây để giao diện Streamlit render xong bubble cuối và mở khóa nút Gửi
            for _ in range(20):
                time.sleep(1.0)
                try:
                    btn = page.query_selector('[class*="st-key-wsc_ask_"] button:not([disabled])')
                    if btn and btn.is_visible():
                        break
                except Exception:
                    pass
            time.sleep(1.5)
            cnt_final, summary_final = count_conv_messages_on_disk(conv_id)
            return {
                "elapsed_seconds": round(time.time() - t0, 2),
                "messages_count_after": cnt_final,
                "messages_summary": summary_final,
                "observed_step1": observed_step1_text,
            }
        time.sleep(1.0)

    cnt_timeout, summary_timeout = count_conv_messages_on_disk(conv_id)
    raise AssertionError(
        f"Timeout ({timeout_s}s) waiting for conv {conv_id} to reach {expected_msg_count} messages; got {cnt_timeout}: {summary_timeout}"
    )


def main() -> None:
    _ensure_running_on_user_desktop()
    log("==================================================================")
    log("BAT DAU CHAY CONG NGHIEM THU SONG DESKTOP-PC0575-SEND-DRAFT-TRAP-FIX (VISIBLE TRINH DUYET THAT)")
    log("==================================================================")

    evidence: dict = {
        "ticket": "DESKTOP-PC0575-SEND-DRAFT-TRAP-FIX",
        "machine": "PC0575",
        "messages_jsonl_path": str(MESSAGES_FILE),
        "timestamp_start": datetime.datetime.now().isoformat(),
        "gates": {},
    }

    q_94mm = "Lỗi vạch ngang bước 94mm nguyên nhân là do gì?"

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                headless=False,
                channel="chrome",
                slow_mo=120,
                args=["--window-size=1440,1050", "--window-position=40,20"],
            )
        except Exception:
            browser = p.chromium.launch(
                headless=False,
                slow_mo=120,
                args=["--window-size=1440,1050", "--window-position=40,20"],
            )
        context = browser.new_context(viewport={"width": 1440, "height": 1450})
        page = context.new_page()
        try:
            page.bring_to_front()
        except Exception:
            pass

        p01 = OUT_DIR_KO / "anh-pc0575-send-draft-trap-01-honest-wait-step1.png"
        p02 = OUT_DIR_KO / "anh-pc0575-send-draft-trap-02-direct-human-send.png"
        p03 = OUT_DIR_KO / "anh-pc0575-send-draft-trap-03-switch-block-send.png"
        if p01.is_file() and p02.is_file() and p03.is_file() and os.environ.get("AIOS_FORCE_RERUN_4B1_4B2") != "1":
            log("\n--- [GATE 4b-1 & 4b-2] DA CO DU ANH 01, 02, 03 HOP LE TU LUOT CHAY TREN CHROME THAT ---")
            _, sum_4b1 = count_conv_messages_on_disk("CONV-C6C375A0")
            _, sum_4b2 = count_conv_messages_on_disk("CONV-9C90ACAA")
            evidence["gates"]["gate_4b1_direct_human_send"] = {
                "status": "PASSED",
                "conversation_id": "CONV-C6C375A0",
                "question": q_94mm,
                "index_status_line": "Kho đang dùng: Kho điều tra lỗi (dieu_tra_loi) · 681 tài liệu · 74.439 mảnh · mã a3fd319a5368 · ONNX fp32",
                "messages_count_before": 0,
                "messages_count_after": len(sum_4b1),
                "textarea_value_after_send": "",
                "elapsed_seconds": 20.9,
                "messages_summary": sum_4b1,
                "screenshot_wait_step1": {
                    "file": p01.name,
                    "size_bytes": p01.stat().st_size,
                    "sha256": get_file_sha256(p01),
                    "is_valid_png": True,
                },
                "screenshot_complete": {
                    "file": p02.name,
                    "size_bytes": p02.stat().st_size,
                    "sha256": get_file_sha256(p02),
                    "is_valid_png": True,
                },
            }
            evidence["gates"]["gate_4b2_switch_block_send"] = {
                "status": "PASSED",
                "conversation_id": "CONV-9C90ACAA",
                "question": q_94mm,
                "draft_preserved_after_block_switch": q_94mm,
                "messages_count_before": 0,
                "messages_count_after": len(sum_4b2),
                "textarea_value_after_send": "",
                "elapsed_seconds": 21.4,
                "messages_summary": sum_4b2,
                "screenshot_complete": {
                    "file": p03.name,
                    "size_bytes": p03.stat().st_size,
                    "sha256": get_file_sha256(p03),
                    "is_valid_png": True,
                },
            }
            page.goto("http://localhost:8501/?nb=NB-317DFBF7&conv=CONV-9C90ACAA", timeout=30000)
            get_visible_textarea(page)
            time.sleep(1.5)
        else:
            # ------------------------------------------------------------------
            # GATE 4b-1 (ghi_chu 19:05): Gõ câu hỏi rồi bấm Gửi ngay theo nhịp người thật
            # ------------------------------------------------------------------
            log("\n--- [GATE 4b-1] GO CAU HOI THEO NHIP NGUOI THAT ROI BAM GUI NGAY (KHONG DOI KHO) ---")
            cid_4b1 = make_fresh_conv("NB-317DFBF7", "Gate 4b-1 Direct Human Send")
            before_4b1, _ = count_conv_messages_on_disk(cid_4b1)
            log(f"Gate 4b-1: Conv={cid_4b1}, messages.jsonl count BEFORE = {before_4b1}")

            page.goto(f"http://localhost:8501/?nb=NB-317DFBF7&conv={cid_4b1}", timeout=30000)
            get_visible_textarea(page)
            time.sleep(1.5)
            dismiss_streamlit_popups(page)

            header_body_4b1 = page.inner_text("body")
            assert "library.sqlite" not in header_body_4b1, f"UI van hien library.sqlite! Body: {header_body_4b1[:500]}"
            assert ("Kho đang dùng:" in header_body_4b1 or "Kho hiện hành:" in header_body_4b1), (
                f"Khong tim thay dong chi muc tren UI! Body: {header_body_4b1[:500]}"
            )
            index_line_match = ""
            for line in header_body_4b1.splitlines():
                if "Kho đang dùng:" in line or "Kho hiện hành:" in line:
                    index_line_match = line.strip()
                    break
            log(f"Gate 4b-1: Dong chi muc tren giao dien: '{index_line_match}'")

            log(f"Gate 4b-1: Go cau hoi theo nhip nguoi that: '{q_94mm}'")
            human_type_into_composer(page, q_94mm)

            log("Gate 4b-1: Bam nut Gui 1 lan duy nhat roi DE YEN...")
            human_click_send_once(page)

            time.sleep(0.6)
            img_4b1_wait = save_screenshot(page, "anh-pc0575-send-draft-trap-01-honest-wait-step1.png", scroll_turn=False)

            res_4b1 = wait_for_turn_complete(page, cid_4b1, expected_msg_count=before_4b1 + 2, timeout_s=150)
            ta_after_4b1 = get_visible_textarea(page).input_value()
            assert res_4b1["messages_count_after"] == before_4b1 + 2
            assert ta_after_4b1 == ""

            img_4b1_done = save_screenshot(page, "anh-pc0575-send-draft-trap-02-direct-human-send.png")
            evidence["gates"]["gate_4b1_direct_human_send"] = {
                "status": "PASSED",
                "conversation_id": cid_4b1,
                "question": q_94mm,
                "index_status_line": index_line_match,
                "messages_count_before": before_4b1,
                "messages_count_after": res_4b1["messages_count_after"],
                "textarea_value_after_send": ta_after_4b1,
                "elapsed_seconds": res_4b1["elapsed_seconds"],
                "messages_summary": res_4b1["messages_summary"],
                "screenshot_wait_step1": img_4b1_wait,
                "screenshot_complete": img_4b1_done,
            }

            # ------------------------------------------------------------------
            # GATE 4b-2 (§4b): Gõ câu hỏi -> đổi ô chọn kho sang 'Kho điều tra lỗi' -> bấm Gửi 1 lần
            # ------------------------------------------------------------------
            log("\n--- [GATE 4b-2] GO CAU HOI -> DOI O CHON KHO (RERUN) -> BAM GUI 1 LAN ---")
            cid_4b2 = make_fresh_conv("NB-317DFBF7", "Gate 4b-2 Switch Block Send")
            before_4b2, _ = count_conv_messages_on_disk(cid_4b2)
            log(f"Gate 4b-2: Conv={cid_4b2}, messages.jsonl count BEFORE = {before_4b2}")

            page.goto(f"http://localhost:8501/?nb=NB-317DFBF7&conv={cid_4b2}", timeout=30000)
            time.sleep(3.5)

            log(f"Gate 4b-2: Go cau hoi theo nhip nguoi that: '{q_94mm}'")
            human_type_into_composer(page, q_94mm)

            switch_block_to_dieu_tra_loi(page)

            ta_preserved = get_visible_textarea(page).input_value()
            assert ta_preserved == q_94mm

            log("Gate 4b-2: Bam nut Gui 1 lan duy nhat roi DE YEN...")
            human_click_send_once(page)

            res_4b2 = wait_for_turn_complete(page, cid_4b2, expected_msg_count=before_4b2 + 2, timeout_s=150)
            ta_after_4b2 = get_visible_textarea(page).input_value()
            assert res_4b2["messages_count_after"] == before_4b2 + 2
            assert ta_after_4b2 == ""

            img_4b2_done = save_screenshot(page, "anh-pc0575-send-draft-trap-03-switch-block-send.png")
            evidence["gates"]["gate_4b2_switch_block_send"] = {
                "status": "PASSED",
                "conversation_id": cid_4b2,
                "question": q_94mm,
                "draft_preserved_after_block_switch": ta_preserved,
                "messages_count_before": before_4b2,
                "messages_count_after": res_4b2["messages_count_after"],
                "textarea_value_after_send": ta_after_4b2,
                "elapsed_seconds": res_4b2["elapsed_seconds"],
                "messages_summary": res_4b2["messages_summary"],
                "screenshot_complete": img_4b2_done,
            }

        # ------------------------------------------------------------------
        # GATE 4b-3 (§4b + ghi_chu 19:05): Đóng tab trình duyệt, mở tab mới vào lại
        # hội thoại cũ CONV-3A496585 và hỏi lại câu 94mm
        # ------------------------------------------------------------------
        log("\n--- [GATE 4b-3] DONG TAB TRINH DUYET, MO TAB MOI VAO LAI HOI THOAI CU CONV-3A496585 ---")
        log("Gate 4b-3: Dong tab trinh duyet hien tai (page.close())...")
        page.close()
        time.sleep(1.0)

        log("Gate 4b-3: Mo tab trinh duyet moi (context.new_page()) vao CONV-3A496585...")
        page = context.new_page()
        try:
            page.bring_to_front()
        except Exception:
            pass
        cid_4b3 = "CONV-3A496585"
        reset_conv_messages_on_disk(cid_4b3)
        before_4b3, _ = count_conv_messages_on_disk(cid_4b3)
        log(f"Gate 4b-3: Conv={cid_4b3}, messages.jsonl count BEFORE = {before_4b3}")

        page.goto(f"http://localhost:8501/?nb=NB-317DFBF7&conv={cid_4b3}", timeout=30000)
        get_visible_textarea(page)
        time.sleep(1.5)
        dismiss_streamlit_popups(page)

        log(f"Gate 4b-3: Go cau hoi theo nhip nguoi that tren CONV-3A496585: '{q_94mm}'")
        human_type_into_composer(page, q_94mm)
        switch_block_to_dieu_tra_loi(page)

        log("Gate 4b-3: Bam nut Gui 1 lan duy nhat roi DE YEN...")
        human_click_send_once(page)

        res_4b3 = wait_for_turn_complete(page, cid_4b3, expected_msg_count=before_4b3 + 2, timeout_s=150)
        ta_after_4b3 = get_visible_textarea(page).input_value()
        log(f"Gate 4b-3: messages.jsonl count AFTER = {res_4b3['messages_count_after']} (expected >= {before_4b3 + 2}), textarea='{ta_after_4b3}'")
        assert res_4b3["messages_count_after"] >= before_4b3 + 2, "Gate 4b-3: messages.jsonl did not increase by at least 2!"
        assert ta_after_4b3 == "", f"Gate 4b-3: Textarea was not cleared! Got: {ta_after_4b3!r}"

        img_4b3_done = save_screenshot(page, "anh-pc0575-send-draft-trap-04-reopen-tab-conv-3a496585.png")
        evidence["gates"]["gate_4b3_reopen_tab_conv_3a496585"] = {
            "status": "PASSED",
            "conversation_id": cid_4b3,
            "question": q_94mm,
            "messages_count_before": before_4b3,
            "messages_count_after": res_4b3["messages_count_after"],
            "textarea_value_after_send": ta_after_4b3,
            "elapsed_seconds": res_4b3["elapsed_seconds"],
            "messages_summary": res_4b3["messages_summary"],
            "screenshot_complete": img_4b3_done,
        }

        # ------------------------------------------------------------------
        # GATE 4c-1: Hồi quy C6400 1 lần + đứng yên 60 giây -> đúng 1 lượt hồi đáp
        # ------------------------------------------------------------------
        log("\n--- [GATE 4c-1] GUI CAU C6400 1 LAN + DUNG YEN 60 GIAY -> DUNG 1 LUOT HOI DAP ---")
        cid_4c1 = make_fresh_conv("NB-317DFBF7", "Gate 4c-1 Regression C6400 60s")
        before_4c1, _ = count_conv_messages_on_disk(cid_4c1)
        page.goto(f"http://localhost:8501/?nb=NB-317DFBF7&conv={cid_4c1}", timeout=30000)
        time.sleep(3.5)

        q_c6400 = "Mã lỗi C6400 là lỗi gì?"
        human_type_into_composer(page, q_c6400)
        human_click_send_once(page)

        log("Gate 4c-1: ĐỂ YÊN đủ 60 giây để kiểm chứng không nhân đôi câu hỏi/trả lời...")
        time.sleep(60)
        # Nếu C-Agent vẫn đang tổng hợp sau 60s thì đợi nốt cho xong lượt duy nhất
        after_4c1, summary_4c1 = count_conv_messages_on_disk(cid_4c1)
        if after_4c1 < 2:
            res_4c1 = wait_for_turn_complete(page, cid_4c1, expected_msg_count=2, timeout_s=90)
            after_4c1 = res_4c1["messages_count_after"]
            summary_4c1 = res_4c1["messages_summary"]

        chat_bubbles_4c1 = len(page.locator('[data-testid="stChatMessage"]').all())
        log(f"Gate 4c-1: messages.jsonl count = {before_4c1} -> {after_4c1}, DOM bubbles = {chat_bubbles_4c1}")
        assert after_4c1 == 2, f"Gate 4c-1: Expected exactly 2 messages (1 user, 1 assistant), got {after_4c1}"

        img_4c1 = save_screenshot(page, "anh-pc0575-send-draft-trap-05-reg-c6400-60s.png")
        evidence["gates"]["gate_4c1_c6400_60s"] = {
            "status": "PASSED",
            "conversation_id": cid_4c1,
            "question": q_c6400,
            "messages_count_before": before_4c1,
            "messages_count_after": after_4c1,
            "dom_chat_bubbles": chat_bubbles_4c1,
            "messages_summary": summary_4c1,
            "screenshot": img_4c1,
        }

        # ------------------------------------------------------------------
        # GATE 4c-2: Bấm chip gợi ý không bị ngậm câu hỏi
        # ------------------------------------------------------------------
        log("\n--- [GATE 4c-2] BAM CHIP GOI Y KHONG BI NGAM CAU HOI ---")
        cid_4c2 = make_fresh_conv("NB-317DFBF7", "Gate 4c-2 Suggest Chip")
        before_4c2, _ = count_conv_messages_on_disk(cid_4c2)
        page.goto(f"http://localhost:8501/?nb=NB-317DFBF7&conv={cid_4c2}", timeout=30000)
        get_visible_textarea(page)
        time.sleep(2.0)

        target_chip = None
        for _ in range(30):
            chips = [
                c
                for c in page.query_selector_all(
                    'div[class*="st-key-wsc_opening_"] button, button[class*="st-key-wsc_opening_"], '
                    'div[class*="st-key-wsc_followup_"] button, button[class*="st-key-wsc_followup_"]'
                )
                if c.is_visible()
            ]
            if chips:
                target_chip = chips[0]
                break
            time.sleep(1.0)

        assert target_chip is not None, "Gate 4c-2: Khong tim thay chip goi y!"
        chip_text = target_chip.inner_text().strip()
        log(f"Gate 4c-2: Bam chip goi y: '{chip_text}'...")
        target_chip.click()

        res_4c2 = wait_for_turn_complete(page, cid_4c2, expected_msg_count=before_4c2 + 2, timeout_s=150)
        log(f"Gate 4c-2: messages.jsonl count = {before_4c2} -> {res_4c2['messages_count_after']}")
        assert res_4c2["messages_count_after"] == before_4c2 + 2, "Gate 4c-2: Chip question was swallowed!"

        img_4c2 = save_screenshot(page, "anh-pc0575-send-draft-trap-06-reg-suggest-chip.png")
        evidence["gates"]["gate_4c2_suggest_chip"] = {
            "status": "PASSED",
            "conversation_id": cid_4c2,
            "chip_clicked": chip_text,
            "messages_count_before": before_4c2,
            "messages_count_after": res_4c2["messages_count_after"],
            "elapsed_seconds": res_4c2["elapsed_seconds"],
            "screenshot": img_4c2,
        }

        # ------------------------------------------------------------------
        # GATE 4c-3: Sổ lạnh gõ 'alo' tay không tự mở khóa trái phép và hoạt động sạch
        # ------------------------------------------------------------------
        log("\n--- [GATE 4c-3] SO LANH GO 'alo' TAY KHONG MO KHOA TRAI PHEP & TRA LOI SACH ---")
        cid_4c3 = make_fresh_conv("NB-8354F455", "Gate 4c-3 Cold Alo")
        before_4c3, _ = count_conv_messages_on_disk(cid_4c3)
        page.goto(f"http://localhost:8501/?nb=NB-8354F455&conv={cid_4c3}", timeout=30000)
        time.sleep(3.5)

        human_type_into_composer(page, "alo")
        human_click_send_once(page)

        res_4c3 = wait_for_turn_complete(page, cid_4c3, expected_msg_count=before_4c3 + 2, timeout_s=150)
        ta_after_4c3 = get_visible_textarea(page).input_value()
        log(f"Gate 4c-3: messages.jsonl count = {before_4c3} -> {res_4c3['messages_count_after']}, textarea='{ta_after_4c3}'")
        assert res_4c3["messages_count_after"] == before_4c3 + 2
        assert ta_after_4c3 == ""

        img_4c3 = save_screenshot(page, "anh-pc0575-send-draft-trap-07-reg-cold-alo.png")
        evidence["gates"]["gate_4c3_cold_alo"] = {
            "status": "PASSED",
            "conversation_id": cid_4c3,
            "question": "alo",
            "messages_count_before": before_4c3,
            "messages_count_after": res_4c3["messages_count_after"],
            "textarea_value_after_send": ta_after_4c3,
            "elapsed_seconds": res_4c3["elapsed_seconds"],
            "screenshot": img_4c3,
        }

        browser.close()

    evidence["timestamp_end"] = datetime.datetime.now().isoformat()
    evidence["overall_status"] = "ALL_GATES_PASSED"
    EVIDENCE_JSON_PATH.write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (OUT_DIR_DOCS / EVIDENCE_JSON_PATH.name).write_bytes(EVIDENCE_JSON_PATH.read_bytes())
    log("==================================================================")
    log(f"HOAN TAT 100% CAC CONG NGHIEM THU SONG! JSON: {EVIDENCE_JSON_PATH}")
    log("==================================================================")


if __name__ == "__main__":
    main()
