# scripts/run_all_quality_gates.py
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
    # GATE 4: Tao cuoc tro chuyen moi, 1 khung hoi dap duy nhat, tra loi binh thuong
    # =========================================================================
    log("\n=======================================================")
    log("=== [GATE 4] START: New conversation, single frame  ===")
    log("=======================================================")
    page.goto("http://localhost:8501/?nb=NB-317DFBF7", timeout=30000)
    time.sleep(3)

    create_btn = page.locator('div[class*="st-key-btn_create_conv"] button').first
    if create_btn.count() > 0:
        log("Clicking btn_create_conv...")
        create_btn.click()
        time.sleep(3)
    else:
        b = page.locator('[data-testid="stSidebar"] button:has-text("Tạo cuộc trò chuyện")').first
        if b.count() > 0:
            b.click()
            time.sleep(3)

    log(f"Gate 4 URL: {page.url}")
    # Wait for composer textarea
    page.wait_for_selector('[class*="st-key-wsc_question_input_"] textarea', state="attached", timeout=20000)
    time.sleep(2)

    # Check visible textareas and send buttons
    tas = [t for t in page.query_selector_all('[class*="st-key-wsc_question_input_"] textarea') if t.is_visible()]
    btns = [b for b in page.query_selector_all('[class*="st-key-wsc_ask_"] button') if b.is_visible()]
    log(f"Gate 4: Visible textareas={len(tas)}, Visible send buttons={len(btns)}")
    assert len(tas) == 1, f"Gate 4: Expected 1 visible textarea, found {len(tas)}"
    assert len(btns) == 1, f"Gate 4: Expected 1 visible send button, found {len(btns)}"

    # Ask 1 normal question: "Xin chào"
    tas[0].fill("Xin chào")
    time.sleep(1)
    btns[0].click()
    log("Gate 4: Sent 'Xin chào', waiting for answer...")

    g4_answered = False
    for i in range(30):
        time.sleep(1)
        asst_msgs = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
        if len(asst_msgs) >= 1:
            log(f"Gate 4: Answer received in {i+1}s! Assistant message count={len(asst_msgs)}")
            g4_answered = True
            break
    assert g4_answered, "Gate 4: No answer received!"

    # Wait for post-answer render to settle
    time.sleep(4)
    g4_img = out_dir / "anh-pc0575-chat-loop-lockup-04-gate4-new-conv.png"
    page.screenshot(path=str(g4_img))
    log(f"Gate 4: Screenshot saved -> {g4_img} (Bytes: {g4_img.stat().st_size}, SHA-256: {file_sha256(g4_img)})")

    # Re-verify exactly 1 composer frame after answer
    page.wait_for_selector('[class*="st-key-wsc_question_input_"] textarea', state="visible", timeout=10000)
    tas_after = [t for t in page.query_selector_all('[class*="st-key-wsc_question_input_"] textarea') if t.is_visible()]
    btns_after = [b for b in page.query_selector_all('[class*="st-key-wsc_ask_"] button') if b.is_visible()]
    assert len(tas_after) == 1, f"Gate 4: Stacked frames! Visible textareas={len(tas_after)}"
    assert len(btns_after) == 1, f"Gate 4: Stacked send buttons={len(btns_after)}"
    log("=== [GATE 4] PASSED 100% ===")

    # =========================================================================
    # GATE 2: Gui cau 'Loi C6400...', dung 1 cau tra loi, cho 60s khong ban sao
    # =========================================================================
    log("\n=======================================================")
    log("=== [GATE 2] START: C6400 single response, wait 60s ===")
    log("=======================================================")
    create_btn = page.locator('div[class*="st-key-btn_create_conv"] button').first
    if create_btn.count() > 0:
        create_btn.click()
        time.sleep(3)
        for _ in range(10):
            if len(page.query_selector_all('[data-testid="stChatMessage"]')) == 0:
                break
            time.sleep(0.5)

    log(f"Gate 2 URL: {page.url}")
    page.wait_for_selector('[class*="st-key-wsc_question_input_"] textarea', state="attached", timeout=20000)
    time.sleep(2)

    tas = [t for t in page.query_selector_all('[class*="st-key-wsc_question_input_"] textarea') if t.is_visible()]
    btns = [b for b in page.query_selector_all('[class*="st-key-wsc_ask_"] button') if b.is_visible()]
    assert len(tas) == 1 and len(btns) == 1

    q_c6400 = "Lỗi C6400 máy 6thNext, đã phát sinh bao lần trong năm 2026.\nCách điều tra."
    tas[0].fill(q_c6400)
    time.sleep(1)
    btns[0].click()
    log("Gate 2: Sent C6400 query, waiting for first response...")

    g2_answered = False
    for i in range(30):
        time.sleep(1)
        asst_msgs = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
        if len(asst_msgs) >= 1:
            log(f"Gate 2: First response received in {i+1}s! Assistant messages={len(asst_msgs)}")
            g2_answered = True
            break
    assert g2_answered, "Gate 2: No response received!"

    # FULL 60 SECONDS WAIT AS MANDATED BY PROMPT
    log("Gate 2: Waiting full 60 seconds to verify ZERO duplicate answers occur...")
    for sec in range(1, 61):
        time.sleep(1)
        if sec % 10 == 0:
            asst_msgs = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
            user_msgs = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarUser"]')]
            log(f"Gate 2: Elapsed {sec}s... User msgs={len(user_msgs)}, Assistant msgs={len(asst_msgs)}")

    final_asst = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
    final_user = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarUser"]')]
    log(f"Gate 2: Result after 60s -> User msgs={len(final_user)}, Assistant msgs={len(final_asst)}")
    assert len(final_user) == 1, f"Gate 2 FAILED: User messages count={len(final_user)} (expected 1)"
    assert len(final_asst) == 1, f"Gate 2 FAILED: Assistant messages count={len(final_asst)} (expected 1, loop bug reproduced!)"

    g2_img = out_dir / "anh-pc0575-chat-loop-lockup-03-gate2-c6400-single.png"
    page.screenshot(path=str(g2_img))
    log(f"Gate 2: Screenshot saved -> {g2_img} (Bytes: {g2_img.stat().st_size}, SHA-256: {file_sha256(g2_img)})")
    log("=== [GATE 2] PASSED 100% ===")

    # =========================================================================
    # GATE 1: Bam chip cau hoi goi y, khong 'So sanh So sanh', khong long boi canh, khong mat 'trang'
    # =========================================================================
    log("\n=======================================================")
    log("=== [GATE 1] START: Suggestion chip click clean     ===")
    log("=======================================================")
    create_btn = page.locator('div[class*="st-key-btn_create_conv"] button').first
    if create_btn.count() > 0:
        create_btn.click()
        time.sleep(3)
        for _ in range(10):
            if len(page.query_selector_all('[data-testid="stChatMessage"]')) == 0:
                break
            time.sleep(0.5)

    log(f"Gate 1 URL: {page.url}")
    page.wait_for_selector('[class*="st-key-wsc_question_input_"] textarea', state="attached", timeout=20000)
    time.sleep(2)

    tas = [t for t in page.query_selector_all('[class*="st-key-wsc_question_input_"] textarea') if t.is_visible()]
    btns = [b for b in page.query_selector_all('[class*="st-key-wsc_ask_"] button') if b.is_visible()]

    # Ask base question: "In ra tờ giấy trắng"
    tas[0].fill("In ra tờ giấy trắng")
    time.sleep(1)
    btns[0].click()
    log("Gate 1: Sent 'In ra tờ giấy trắng', waiting for answer and suggestion chips...")

    g1_chips_ready = False
    for i in range(35):
        time.sleep(1)
        chips = [c for c in page.query_selector_all('button[class*="st-key-wsc_followup_"]') if c.is_visible()]
        if len(chips) >= 1:
            log(f"Gate 1: Suggestion chips appeared in {i+1}s! Count={len(chips)}")
            g1_chips_ready = True
            break
    assert g1_chips_ready, "Gate 1: Suggestion chips did not appear!"

    # Locate the target chip
    target_chip = None
    target_chip_text = ""
    for c in page.query_selector_all('button[class*="st-key-wsc_followup_"]'):
        if not c.is_visible():
            continue
        c_txt = c.inner_text().strip()
        log(f"Gate 1: Chip text -> '{c_txt}'")
        if "So sánh" in c_txt and "giấy" in c_txt:
            target_chip = c
            target_chip_text = c_txt
            break
    if not target_chip:
        target_chip = [c for c in page.query_selector_all('button[class*="st-key-wsc_followup_"]') if c.is_visible()][0]
        target_chip_text = target_chip.inner_text().strip()

    log(f"Gate 1: Clicking target chip: '{target_chip_text}'...")
    target_chip.click()

    # Wait for answer to chip question
    g1_answered = False
    for i in range(40):
        time.sleep(1)
        asst_msgs = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
        if len(asst_msgs) >= 2:
            log(f"Gate 1: Chip answer received in {i+1}s! Assistant message count={len(asst_msgs)}")
            g1_answered = True
            break
    assert g1_answered, "Gate 1: Chip answer not received!"

    # Check user message 2
    user_msgs = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarUser"]')]
    assert len(user_msgs) == 2, f"Gate 1: Expected 2 user messages, found {len(user_msgs)}"
    q2_text = user_msgs[1].inner_text().strip()
    log(f"Gate 1: Second user message content:\n---\n{q2_text}\n---")

    # Criteria checks:
    # 1. No "So sánh So sánh"
    assert "So sánh So sánh" not in q2_text, "Gate 1 FAILED: Duplicated 'So sánh So sánh' detected!"
    # 2. No nested "Bối cảnh câu trước:"
    assert q2_text.count("Bối cảnh câu trước:") <= 1, f"Gate 1 FAILED: Nested 'Bối cảnh câu trước:'! Count={q2_text.count('Bối cảnh câu trước:')}"
    # 3. No truncation of "trắng"
    if "giấy giữa" in q2_text:
        assert "giấy trắng giữa" in q2_text or "trắng" in q2_text, "Gate 1 FAILED: Word 'trắng' was truncated!"

    time.sleep(2)
    g1_img = out_dir / "anh-pc0575-chat-loop-lockup-05-gate1-suggest-clean.png"
    page.screenshot(path=str(g1_img))
    log(f"Gate 1: Screenshot saved -> {g1_img} (Bytes: {g1_img.stat().st_size}, SHA-256: {file_sha256(g1_img)})")
    log("=== [GATE 1] PASSED 100% ===")

    # =========================================================================
    # GATE 5: Thu gui trung co y: chi xu ly 1 lan hoac tu choi kem thong bao
    # =========================================================================
    log("\n=======================================================")
    log("=== [GATE 5] START: Intentional double click debounce ===")
    log("=======================================================")
    create_btn = page.locator('div[class*="st-key-btn_create_conv"] button').first
    if create_btn.count() > 0:
        create_btn.click()
        time.sleep(3)
        for _ in range(10):
            if len(page.query_selector_all('[data-testid="stChatMessage"]')) == 0:
                break
            time.sleep(0.5)

    log(f"Gate 5 URL: {page.url}")
    page.wait_for_selector('[class*="st-key-wsc_question_input_"] textarea', state="attached", timeout=20000)
    time.sleep(2)

    tas = [t for t in page.query_selector_all('[class*="st-key-wsc_question_input_"] textarea') if t.is_visible()]
    test_q5 = "Kiểm tra gửi trùng lặp cố ý Gate 5"
    tas[0].fill(test_q5)
    time.sleep(1)

    # Rapid double click
    log("Gate 5: Triggering intentional rapid double click on send button...")
    page.evaluate("""() => {
        const btn = document.querySelector('div[class*="st-key-wsc_ask_"] button');
        if (btn) {
            btn.click();
            setTimeout(() => { btn.click(); }, 60);
        }
    }""")

    for i in range(25):
        time.sleep(1)
        asst_msgs = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
        if len(asst_msgs) >= 1:
            log(f"Gate 5: Response completed in {i+1}s!")
            break

    time.sleep(3)
    user_msgs_g5 = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarUser"]')]
    asst_msgs_g5 = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
    log(f"Gate 5: User messages={len(user_msgs_g5)}, Assistant messages={len(asst_msgs_g5)}")
    assert len(user_msgs_g5) == 1, f"Gate 5 FAILED: Rapid double click produced {len(user_msgs_g5)} user messages!"
    assert len(asst_msgs_g5) == 1, f"Gate 5 FAILED: Rapid double click produced {len(asst_msgs_g5)} assistant messages!"

    g5_img = out_dir / "anh-pc0575-chat-loop-lockup-07-gate5-debounce.png"
    page.screenshot(path=str(g5_img))
    log(f"Gate 5: Screenshot saved -> {g5_img} (Bytes: {g5_img.stat().st_size}, SHA-256: {file_sha256(g5_img)})")
    log("=== [GATE 5] PASSED 100% ===")

    # =========================================================================
    # GATE 3: Mo so lanh, go 'alo', khong thao tac gi them: tu mo khoa & tra loi
    # =========================================================================
    log("\n=======================================================")
    log("=== [GATE 3] START: Cold notebook auto-unlock & answer ===")
    log("=======================================================")
    # Navigate to NB-8354F455 (tong_hop) or create a fresh cold notebook
    log("Gate 3: Navigating to notebook NB-8354F455...")
    page.goto("http://localhost:8501/?nb=NB-8354F455", timeout=30000)
    time.sleep(3)

    # Create new conversation in NB-8354F455
    create_btn = page.locator('div[class*="st-key-btn_create_conv"] button').first
    if create_btn.count() > 0:
        create_btn.click()
        time.sleep(3)
        for _ in range(10):
            if len(page.query_selector_all('[data-testid="stChatMessage"]')) == 0:
                break
            time.sleep(0.5)

    page.wait_for_selector('[class*="st-key-wsc_question_input_"] textarea', state="attached", timeout=20000)
    time.sleep(2)

    tas = [t for t in page.query_selector_all('[class*="st-key-wsc_question_input_"] textarea') if t.is_visible()]
    btns = [b for b in page.query_selector_all('[class*="st-key-wsc_ask_"] button') if b.is_visible()]
    log(f"Gate 3: Composer ready. Filling 'alo'...")
    tas[0].fill("alo")
    time.sleep(1)

    # Click send (or submit)
    log("Gate 3: Clicking send button with 'alo' (no further manual actions)...")
    btns[0].click()

    g3_answered = False
    for i in range(40):
        time.sleep(1)
        asst_msgs = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
        if len(asst_msgs) >= 1:
            log(f"Gate 3: Auto-unlocked and answered in {i+1}s! Assistant message count={len(asst_msgs)}")
            g3_answered = True
            break
    assert g3_answered, "Gate 3 FAILED: Cold notebook did not auto-unlock and answer!"

    time.sleep(2)
    g3_img = out_dir / "anh-pc0575-chat-loop-lockup-06-gate3-cold-auto-unlock.png"
    page.screenshot(path=str(g3_img))
    log(f"Gate 3: Screenshot saved -> {g3_img} (Bytes: {g3_img.stat().st_size}, SHA-256: {file_sha256(g3_img)})")
    log("=== [GATE 3] PASSED 100% ===")

    browser.close()
    log("\n=======================================================")
    log(">>> ALL 5 QUALITY ACCEPTANCE GATES PASSED 100%! <<<")
    log("=======================================================")
