# scripts/test_gate1_targeted.py
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

    log("=== [TARGETED GATE 1 TEST] ===")
    page.goto("http://localhost:8501/?nb=NB-317DFBF7", timeout=30000)
    time.sleep(3)

    create_btn = page.locator('div[class*="st-key-btn_create_conv"] button').first
    if create_btn.count() > 0:
        create_btn.click()
        time.sleep(3)
        for _ in range(10):
            if len(page.query_selector_all('[data-testid="stChatMessage"]')) == 0:
                break
            time.sleep(0.5)

    log(f"Active URL: {page.url}")
    page.wait_for_selector('[class*="st-key-wsc_question_input_"] textarea', state="attached", timeout=20000)
    time.sleep(2)

    tas = [t for t in page.query_selector_all('[class*="st-key-wsc_question_input_"] textarea') if t.is_visible()]
    btns = [b for b in page.query_selector_all('[class*="st-key-wsc_ask_"] button') if b.is_visible()]
    assert len(tas) == 1 and len(btns) == 1

    tas[0].fill("In ra tờ giấy trắng")
    time.sleep(1)
    btns[0].click()
    log("Sent 'In ra tờ giấy trắng', waiting up to 60s for answer and chips...")

    g1_chips_ready = False
    for sec in range(1, 61):
        time.sleep(1)
        asst = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
        chips = [c for c in page.query_selector_all('div[class*="st-key-wsc_followup_"] button') if c.is_visible()]
        if sec % 5 == 0 or len(chips) > 0:
            log(f"[{sec}s] Assistant msgs={len(asst)}, Chips={len(chips)}")
        if len(chips) >= 1:
            log(f"SUCCESS: Chips appeared at {sec}s! Count={len(chips)}")
            g1_chips_ready = True
            break

    # If chips not found with class, let's check all visible buttons on page
    if not g1_chips_ready:
        all_visible_btns = [b for b in page.query_selector_all('button') if b.is_visible()]
        log(f"Total visible buttons on page: {len(all_visible_btns)}")
        for i, b in enumerate(all_visible_btns):
            log(f"Btn {i}: '{b.inner_text().strip()[:50]}'")

    assert g1_chips_ready, "Gate 1: Chips did not appear within 60s!"

    # Locate the target chip
    target_chip = None
    target_chip_text = ""
    for c in page.query_selector_all('div[class*="st-key-wsc_followup_"] button'):
        if not c.is_visible():
            continue
        c_txt = c.inner_text().strip()
        log(f"Chip option: '{c_txt}'")
        if "So sánh" in c_txt and "giấy" in c_txt:
            target_chip = c
            target_chip_text = c_txt
            break
    if not target_chip:
        target_chip = [c for c in page.query_selector_all('div[class*="st-key-wsc_followup_"] button') if c.is_visible()][0]
        target_chip_text = target_chip.inner_text().strip()

    log(f"Clicking chip: '{target_chip_text}'...")
    target_chip.click()

    # Wait for answer to chip
    log("Waiting up to 60s for answer to suggestion chip...")
    g1_answered = False
    for sec in range(1, 61):
        time.sleep(1)
        asst_msgs = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
        if len(asst_msgs) >= 2:
            log(f"Answer to chip received at {sec}s! Total assistant msgs={len(asst_msgs)}")
            g1_answered = True
            break
    assert g1_answered, "Answer to chip not received within 60s!"

    # Verify user message 2
    user_msgs = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarUser"]')]
    assert len(user_msgs) == 2
    q2_text = user_msgs[1].inner_text().strip()
    log(f"User question 2 in DOM:\n---\n{q2_text}\n---")

    assert "So sánh So sánh" not in q2_text, "FAILED: 'So sánh So sánh' detected!"
    assert q2_text.count("Bối cảnh câu trước:") <= 1, f"FAILED: Nested context wrappers! count={q2_text.count('Bối cảnh câu trước:')}"
    if "giấy giữa" in q2_text:
        assert "giấy trắng giữa" in q2_text or "trắng" in q2_text, "FAILED: Word 'trắng' was cut!"

    time.sleep(3)
    g1_img = out_dir / "anh-pc0575-chat-loop-lockup-05-gate1-suggest-clean.png"
    page.screenshot(path=str(g1_img))
    log(f"Saved screenshot: {g1_img} (Bytes: {g1_img.stat().st_size}, SHA-256: {file_sha256(g1_img)})")
    log("=== [TARGETED GATE 1 TEST] PASSED 100%! ===")

    browser.close()
