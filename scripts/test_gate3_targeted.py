# scripts/test_gate3_targeted.py
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

    log("\n=== [TARGETED GATE 3 TEST: COLD NOTEBOOK AUTO-UNLOCK & ANSWER] ===")
    page.goto("http://localhost:8501/?nb=NB-LAZY-DTL", timeout=30000)
    time.sleep(3)

    new_btn = page.query_selector('button:has-text("mới"), button:has-text("Cuộc trò chuyện mới"), button:has-text("Hội thoại mới")')
    if new_btn:
        log(f"Gate 3: Clicking new conversation button '{new_btn.inner_text().strip()}'...")
        new_btn.click()
        time.sleep(3)

    log(f"Gate 3 Active URL: {page.url}")
    page.wait_for_selector('[class*="st-key-wsc_question_input_"] textarea', state="attached", timeout=20000)
    time.sleep(2)

    tas = [t for t in page.query_selector_all('[class*="st-key-wsc_question_input_"] textarea') if t.is_visible()]
    assert len(tas) >= 1, "Gate 3: Textarea not found!"

    log("Gate 3: Typing 'alo' into textarea...")
    tas[0].fill("alo")
    time.sleep(1)

    log("Gate 3: Hands-free waiting for worker warming to complete and UI to auto-unlock (up to 120s)...")
    unlocked_btn = page.wait_for_selector(
        '[class*="st-key-wsc-action-"] button:not([disabled]), [class*="st-key-wsc_ask_"] button:not([disabled])',
        timeout=120000,
    )
    log("Gate 3: UI AUTO-UNLOCKED successfully! Send button is enabled.")

    log("Gate 3: Submitting 'alo' via unlocked button...")
    unlocked_btn.click()

    log("Gate 3: Waiting up to 60s for assistant response...")
    answered = False
    for sec in range(1, 61):
        time.sleep(1)
        asst = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
        if sec % 5 == 0 or len(asst) > 0:
            log(f"[{sec}s] Assistant msgs={len(asst)}")
        if len(asst) >= 1:
            log(f"Gate 3: Assistant answered at {sec}s! Count={len(asst)}")
            answered = True
            break

    assert answered, "Gate 3 FAILED: Assistant did not respond within 60s!"

    time.sleep(3)
    g3_img = out_dir / "anh-pc0575-chat-loop-lockup-06-gate3-cold-auto-unlock.png"
    page.screenshot(path=str(g3_img))
    log(f"Gate 3: Screenshot saved -> {g3_img} (Bytes: {g3_img.stat().st_size}, SHA-256: {file_sha256(g3_img)})")
    log("=== [GATE 3] PASSED 100% ===")

    browser.close()
