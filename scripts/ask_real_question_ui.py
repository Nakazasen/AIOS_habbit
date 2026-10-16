# -*- coding: utf-8 -*-
"""Script gui 1 cau hoi that qua giao dien Streamlit bang Playwright.
Nghiem thu ve DESKTOP-PC0575-UI-RENDER-FIX tren so NB-E35A7BEE.
"""

import json
import os
import sys
import time
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
sys.path.insert(0, str(APP_DIR / "src"))

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

import aios_habit.workspace_chat_store as store
from aios_habit.local_jsonl import clear_jsonl_cache
from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import load_messages, save_conversation

URL = "http://localhost:8501"
TARGET_NB = "NB-E35A7BEE"
OUTPUT_DIR = Path("D:/Sandbox/aios-dieu-phoi/hop-thu/lan-desktop-pc0575/ket-qua")


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def ask_real_question() -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conv_id = f"CONV-RENDERFIX-{uuid.uuid4().hex[:6].upper()}"
    question = "Các yếu tố ảnh hưởng đến đường kính chùm tia Beam và các bước kiểm soát trong điều tra lỗi LSU là gì?"

    log(f"=== GUI CAU HOI THAT QUA GIAO DIEN (PLAYWRIGHT) ===")
    log(f"So: {TARGET_NB} | Hoi thoai moi: {conv_id}")
    log(f"Cau hoi: '{question}'")

    # Tao conversation moi trong so
    new_conv = WorkspaceConversation(
        id=conv_id,
        notebook_id=TARGET_NB,
        title="Test Render Fix LSU Question",
        ai_mode="grounded",
    )
    save_conversation(new_conv)
    log(f"Da tao va luu hoi thoai moi: {conv_id}")

    target_url = f"{URL}/?nb={TARGET_NB}&conv={conv_id}&block=lsu"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        log(f"Dieu huong den: {target_url}")
        t_nav_start = time.time()
        page.goto(target_url, wait_until="networkidle", timeout=120000)

        composer_selector = 'textarea[aria-label*="Câu hỏi"], textarea[placeholder*="Nhập câu hỏi"], [class*="st-key-wsc_question_input_"] textarea, [data-testid="stChatInput"] textarea'
        try:
            page.wait_for_selector(composer_selector, timeout=60000)
        except Exception:
            composer_selector = 'textarea'
            page.wait_for_selector(composer_selector, timeout=60000)

        t_ready = round(time.time() - t_nav_start, 2)
        log(f"Giao dien hoi thoai da san sang sau: {t_ready}s")

        page.wait_for_timeout(2000)

        # Nhap cau hoi vao textarea cua composer
        textarea = page.locator(composer_selector).last
        try:
            textarea.click(force=True, timeout=5000)
            textarea.fill(question)
        except Exception:
            page.evaluate(f"""() => {{
                const els = document.querySelectorAll('textarea');
                const el = els[els.length - 1];
                if (el) {{
                    el.value = {json.dumps(question)};
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }}""")

        page.wait_for_timeout(1000)

        # Gui cau hoi
        t_ask_start = time.time()
        try:
            textarea.press("Control+Enter")
        except Exception:
            pass

        send_btn = page.locator(f'[class*="st-key-wsc_ask_{conv_id}"] button, [class*="st-key-wsc-action-"] button, button[data-testid="stBaseButton-primary"]').first
        if send_btn.count() > 0:
            try:
                send_btn.click(force=True)
                log("Da click nut gui tren giao dien!")
            except Exception as e:
                log(f"Click send button fallback: {e}")
        else:
            log("Da gui cau hoi qua Control+Enter!")

        # Cho luu tin nhan user
        user_saved = False
        for _ in range(30):
            time.sleep(0.5)
            clear_jsonl_cache()
            msgs = load_messages(conv_id)
            if any(m.role == "user" for m in msgs):
                user_saved = True
                log("User message da duoc luu vao CSDL thanh cong!")
                break
            # Thử gửi lại nếu chưa ăn
            try:
                textarea.press("Control+Enter")
                if send_btn.count() > 0:
                    send_btn.click(force=True)
            except Exception:
                pass

        if not user_saved:
            log("[CANH BAO] Khong thay user message trong DB!")

        # Cho tro ly sinh dap an hoan tat
        log("Dang cho tro ly xu ly va sinh cau tra loi tu kho LSU...")
        assistant_msg = None
        t_wait_start = time.time()
        while time.time() - t_wait_start < 180:
            time.sleep(2.0)
            clear_jsonl_cache()
            msgs = load_messages(conv_id)
            asst = [m for m in msgs if m.role == "assistant" and len(m.content or "") > 50]
            if asst:
                assistant_msg = asst[-1]
                log(f"Tro ly da tra loi xong sau: {time.time() - t_ask_start:.2f}s!")
                break

        t_total_qa = round(time.time() - t_ask_start, 2)

        # Chup anh giao dien co cau tra loi
        page.wait_for_timeout(3000)
        shot_path = OUTPUT_DIR / "anh-pc0575-ui-real-qa-live.png"
        try:
            page.screenshot(path=str(shot_path), full_page=False)
            log(f"Da luu anh chup ket qua QA: {shot_path}")
        except Exception as e:
            log(f"Khong the chup anh QA: {e}")

        browser.close()

    answer_content = assistant_msg.content if assistant_msg else ""
    trace_id = getattr(assistant_msg, "trace_id", None) if assistant_msg else None

    result = {
        "conversation_id": conv_id,
        "question": question,
        "time_to_ready_s": t_ready,
        "qa_duration_s": t_total_qa,
        "has_answer": bool(assistant_msg),
        "answer_length": len(answer_content),
        "answer_preview": answer_content[:500] if answer_content else "",
        "full_answer": answer_content,
        "trace_id": trace_id,
        "screenshot_path": str(shot_path),
    }

    res_file = OUTPUT_DIR / "ket-qua-do-ui-real-qa.json"
    res_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"Da ghi ket qua hoi that vao: {res_file}")
    return result


if __name__ == "__main__":
    res = ask_real_question()
    print("\n--- KET QUA HOI THAT ---")
    print("Conversation ID:", res["conversation_id"])
    print("Has Answer:", res["has_answer"])
    print("QA Duration:", res["qa_duration_s"], "s")
    print("Answer Length:", res["answer_length"])
    print("Trace ID:", res["trace_id"])
    print("Preview:\n", res["answer_preview"])
