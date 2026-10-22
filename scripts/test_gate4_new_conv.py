# scripts/test_gate4_new_conv.py
import time
import sys
from playwright.sync_api import sync_playwright

def log(msg):
    sys.stdout.buffer.write((str(msg) + "\n").encode("utf-8", errors="replace"))
    sys.stdout.flush()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    log("Navigating to NB-317DFBF7...")
    page.goto("http://localhost:8501/?nb=NB-317DFBF7", timeout=30000)
    time.sleep(3)

    log(f"Initial URL: {page.url}")

    # Check new conv button
    new_btn = page.query_selector('button:has-text("mới"), button:has-text("Cuộc trò chuyện mới"), button:has-text("Hội thoại mới")')
    if new_btn:
        log(f"Found new button with text: '{new_btn.inner_text().strip()}', clicking...")
        new_btn.click()
        time.sleep(3)
    else:
        log("New button not found directly, checking sidebar...")

    log(f"URL after new button: {page.url}")

    # Verify exactly 1 composer textarea exists
    textareas = page.query_selector_all('[class*="st-key-wsc_question_input_"] textarea')
    log(f"Composer textareas count: {len(textareas)}")

    # Verify exactly 1 send button exists
    send_btns = page.query_selector_all('[class*="st-key-wsc_ask_"] button, [class*="st-key-wsc-action-"] button')
    log(f"Send buttons count: {len(send_btns)}")

    assert len(textareas) == 1, f"Expected 1 composer textarea, got {len(textareas)}"
    assert len(send_btns) == 1, f"Expected 1 send button, got {len(send_btns)}"

    # Ask 1 normal question: "Xin chào"
    ta = textareas[0]
    ta.fill("Xin chào")
    time.sleep(1)
    send_btn = send_btns[0]
    log("Submitting 'Xin chào'...")
    send_btn.click()

    # Wait for response bubble
    log("Waiting for answer to appear...")
    answered = False
    for i in range(25):
        time.sleep(1)
        msgs = page.query_selector_all('[data-testid="stChatMessage"]')
        # Also check if assistant message appeared
        assistant_msgs = page.query_selector_all('[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])')
        if len(assistant_msgs) >= 1:
            log(f"Assistant answered in {i+1}s! Total messages: {len(msgs)}, Assistant messages: {len(assistant_msgs)}")
            answered = True
            break

    time.sleep(2)
    screenshot_path = "docs/phieu-viec/ket-qua/anh-pc0575-chat-loop-lockup-04-gate4-new-conv.png"
    page.screenshot(path=screenshot_path)
    log(f"Saved Gate 4 screenshot: {screenshot_path}")

    # Verify UI state
    textareas_after = page.query_selector_all('[class*="st-key-wsc_question_input_"] textarea')
    log(f"Composer textareas after answer: {len(textareas_after)}")
    assert len(textareas_after) == 1, f"UI has multiple composer frames! count={len(textareas_after)}"
    assert answered, "No answer received for question!"

    browser.close()
    log("Gate 4 PASSED successfully!")
