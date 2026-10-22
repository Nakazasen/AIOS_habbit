# scripts/test_gate5_and_gate3.py
import time
import sys
import hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright

def log(msg):
    sys.stdout.buffer.write((str(msg) + "\n").encode("utf-8", errors="replace"))
    sys.stdout.flush()

def file_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

out_dir = Path(r"D:\Sandbox\AIOS_habbit\docs\phieu-viec\ket-qua")
out_dir.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 950})

    # =========================================================================
    # GATE 5: Intentional double click debounce
    # =========================================================================
    log("\n=== [GATE 5 START] Intentional double click debounce ===")
    page.goto("http://localhost:8501/?nb=NB-317DFBF7", timeout=30000)
    time.sleep(3)

    new_btn = page.query_selector('button:has-text("mới"), button:has-text("Cuộc trò chuyện mới"), button:has-text("Hội thoại mới")')
    if new_btn:
        log(f"Gate 5: Found new conv button: '{new_btn.inner_text().strip()}', clicking...")
        new_btn.click()
        time.sleep(3)

    log(f"Gate 5 Active URL: {page.url}")
    page.wait_for_selector('[class*="st-key-wsc_question_input_"] textarea', state="attached", timeout=20000)
    time.sleep(2)

    # Verify conversation starts fresh
    msgs_before = page.query_selector_all('[data-testid="stChatMessage"]')
    log(f"Gate 5: Messages before ask: {len(msgs_before)}")

    tas = [t for t in page.query_selector_all('[class*="st-key-wsc_question_input_"] textarea') if t.is_visible()]
    btns = [b for b in page.query_selector_all('[class*="st-key-wsc_ask_"] button, [class*="st-key-wsc-action-"] button') if b.is_visible()]
    assert len(tas) >= 1 and len(btns) >= 1, "Gate 5: Input or button not found!"

    tas[0].fill("Kiểm tra gửi trùng lặp cố ý Gate 5")
    time.sleep(1)

    log("Gate 5: Triggering intentional rapid clicks on Ask button...")
    # Double click rapidly
    btns[0].click()
    try:
        btns[0].click(timeout=300)
    except Exception:
        pass

    log("Gate 5: Waiting up to 60s for assistant response...")
    g5_answered = False
    for sec in range(1, 61):
        time.sleep(1)
        asst = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
        if sec % 5 == 0 or len(asst) > 0:
            log(f"[{sec}s] Assistant msgs={len(asst)}")
        if len(asst) >= 1:
            log(f"Gate 5: Assistant replied at {sec}s!")
            g5_answered = True
            break
    assert g5_answered, "Gate 5: Assistant did not respond within 60s!"

    time.sleep(3)
    user_msgs_g5 = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarUser"]')]
    asst_msgs_g5 = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
    log(f"Gate 5: User messages count = {len(user_msgs_g5)}, Assistant messages count = {len(asst_msgs_g5)}")

    assert len(user_msgs_g5) == 1, f"Gate 5 FAILED: Expected 1 user message, found {len(user_msgs_g5)}"
    assert len(asst_msgs_g5) == 1, f"Gate 5 FAILED: Expected 1 assistant message, found {len(asst_msgs_g5)}"

    g5_img = out_dir / "anh-pc0575-chat-loop-lockup-07-gate5-debounce.png"
    page.screenshot(path=str(g5_img))
    log(f"Gate 5: Screenshot saved -> {g5_img} (Bytes: {g5_img.stat().st_size}, SHA-256: {file_sha256(g5_img)})")
    log("=== [GATE 5] PASSED 100% ===")

    # =========================================================================
    # GATE 3: Cold notebook auto-unlock on 'alo'
    # =========================================================================
    log("\n=== [GATE 3 START] Cold notebook auto-unlock & answer ===")
    page.goto("http://localhost:8501/?nb=NB-LAZY-LSU", timeout=30000)
    time.sleep(3)

    new_btn3 = page.query_selector('button:has-text("mới"), button:has-text("Cuộc trò chuyện mới"), button:has-text("Hội thoại mới")')
    if new_btn3:
        log(f"Gate 3: Found new conv button: '{new_btn3.inner_text().strip()}', clicking...")
        new_btn3.click()
        time.sleep(3)

    log(f"Gate 3 Active URL: {page.url}")
    page.wait_for_selector('[class*="st-key-wsc_question_input_"] textarea', state="attached", timeout=20000)
    time.sleep(2)

    tas3 = [t for t in page.query_selector_all('[class*="st-key-wsc_question_input_"] textarea') if t.is_visible()]
    btns3 = [b for b in page.query_selector_all('[class*="st-key-wsc_ask_"] button, [class*="st-key-wsc-action-"] button') if b.is_visible()]
    assert len(tas3) >= 1 and len(btns3) >= 1, "Gate 3: Input or button not found!"

    log("Gate 3: Filling 'alo'...")
    tas3[0].fill("alo")
    time.sleep(1)

    log("Gate 3: Clicking Ask button with 'alo' (no further manual actions)...")
    btns3[0].click()

    log("Gate 3: Waiting up to 60s for cold notebook auto-unlock & answer...")
    g3_answered = False
    for sec in range(1, 61):
        time.sleep(1)
        asst = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
        if sec % 5 == 0 or len(asst) > 0:
            log(f"[{sec}s] Assistant msgs={len(asst)}")
        if len(asst) >= 1:
            log(f"Gate 3: Auto-unlocked and answered at {sec}s! Count={len(asst)}")
            g3_answered = True
            break
    assert g3_answered, "Gate 3 FAILED: Cold notebook did not auto-unlock and answer within 60s!"

    time.sleep(3)
    g3_img = out_dir / "anh-pc0575-chat-loop-lockup-06-gate3-cold-auto-unlock.png"
    page.screenshot(path=str(g3_img))
    log(f"Gate 3: Screenshot saved -> {g3_img} (Bytes: {g3_img.stat().st_size}, SHA-256: {file_sha256(g3_img)})")
    log("=== [GATE 3] PASSED 100% ===")

    browser.close()
