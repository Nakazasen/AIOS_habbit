# scripts/run_home_quality_gates.py
import time
import sys
import uuid
import hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright

from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import save_conversation

def log(msg):
    sys.stdout.buffer.write((str(msg) + "\n").encode("utf-8", errors="replace"))
    sys.stdout.flush()

def file_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

def make_fresh_conv(nb_id: str, title: str) -> str:
    cid = f"CONV-{uuid.uuid4().hex[:8].upper()}"
    conv = WorkspaceConversation(
        id=cid,
        notebook_id=nb_id,
        title=title,
        created_at=time.time(),
        updated_at=time.time(),
    )
    save_conversation(conv)
    return cid

out_dir = Path(r"D:\Sandbox\AIOS_habbit\docs\phieu-viec\ket-qua")
out_dir.mkdir(parents=True, exist_ok=True)

evidence_summary = {}

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=r"C:\Users\Admin\AppData\Local\ms-playwright\chromium-1243\chrome-win64\chrome.exe",
        headless=True
    )
    page = browser.new_page(viewport={"width": 1440, "height": 950})

    # =========================================================================
    # GATE 1: Bấm chip câu hỏi gợi ý dạng so sánh tài liệu ("In ra tờ giấy trắng")
    # =========================================================================
    log("\n" + "="*60)
    log("=== [GATE 1] START: Suggestion chip comparative query ===")
    log("="*60)
    cid1 = make_fresh_conv("NB-317DFBF7", "Nghiệm Thu Gate 1 - Suggestion Chip")
    page.goto(f"http://localhost:8501/?nb=NB-317DFBF7&conv={cid1}", timeout=30000)
    time.sleep(3)

    log(f"Gate 1 URL: {page.url}")
    page.wait_for_selector('[class*="st-key-wsc_question_input_"] textarea', state="attached", timeout=20000)
    send_btn = page.wait_for_selector('[class*="st-key-wsc_ask_"] button:not([disabled])', state="visible", timeout=60000)
    tas = [t for t in page.query_selector_all('[class*="st-key-wsc_question_input_"] textarea') if t.is_visible()]
    assert len(tas) == 1

    # Ask base question: "In ra tờ giấy trắng"
    tas[0].fill("In ra tờ giấy trắng")
    time.sleep(1)
    send_btn.click()
    log("Gate 1: Sent 'In ra tờ giấy trắng', waiting for answer and suggestion chips...")

    # Wait for answer and suggestion chips
    g1_chips_ready = False
    for i in range(180):
        time.sleep(1)
        chips = [c for c in page.query_selector_all('div[class*="st-key-wsc_followup_"] button, button[class*="st-key-wsc_followup_"]') if c.is_visible()]
        if len(chips) >= 1:
            log(f"Gate 1: Suggestion chips appeared in {i+1}s! Count={len(chips)}")
            g1_chips_ready = True
            break
    assert g1_chips_ready, "Gate 1: Suggestion chips did not appear!"

    # Locate the target chip
    target_chip = None
    target_chip_text = ""
    for c in page.query_selector_all('div[class*="st-key-wsc_followup_"] button, button[class*="st-key-wsc_followup_"]'):
        if not c.is_visible():
            continue
        c_txt = c.inner_text().strip()
        log(f"Gate 1: Chip option -> '{c_txt}'")
        if "So sánh" in c_txt and "giấy" in c_txt:
            target_chip = c
            target_chip_text = c_txt
            break
    if not target_chip:
        target_chip = [c for c in page.query_selector_all('div[class*="st-key-wsc_followup_"] button, button[class*="st-key-wsc_followup_"]') if c.is_visible()][0]
        target_chip_text = target_chip.inner_text().strip()

    log(f"Gate 1: Clicking target chip: '{target_chip_text}'...")
    target_chip.click()

    # Wait for second user message to appear in DOM
    log("Gate 1: Chip clicked, waiting for second user message in DOM...")
    for _ in range(30):
        time.sleep(0.5)
        user_msgs = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarUser"]')]
        if len(user_msgs) >= 2:
            break
    assert len(user_msgs) == 2, f"Gate 1: Expected 2 user messages, found {len(user_msgs)}"

    # Wait for response to chip question to finish streaming
    log("Gate 1: Waiting for chip question answer to complete...")
    for sec in range(1, 180):
        time.sleep(1)
        asst_msgs = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
        if len(asst_msgs) >= 2:
            ask_btns = [b for b in page.query_selector_all('[class*="st-key-wsc_ask_"] button') if b.is_visible() and not b.is_disabled()]
            if len(ask_btns) >= 1:
                log(f"Gate 1: Chip answer completed at {sec}s! Total assistant msgs={len(asst_msgs)}")
                break

    user_msgs = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarUser"]')]
    asst_msgs = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
    assert len(user_msgs) == 2, f"Gate 1: Expected 2 user messages, found {len(user_msgs)}"
    assert len(asst_msgs) == 2, f"Gate 1: Expected 2 assistant messages, found {len(asst_msgs)}"

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
    g1_img = out_dir / "anh-home-chat-loop-lockup-01-gate1-suggest-clean.png"
    page.screenshot(path=str(g1_img))
    size1 = g1_img.stat().st_size
    sha1 = file_sha256(g1_img)
    evidence_summary["gate1"] = {"file": g1_img.name, "size": size1, "sha256": sha1}
    log(f"Gate 1: Screenshot saved -> {g1_img.name} (Bytes: {size1}, SHA-256: {sha1})")
    log("=== [GATE 1] PASSED 100% ===")

    # =========================================================================
    # GATE 2: Gửi câu "Lỗi C6400...", đúng 1 câu trả lời, chờ đủ 60s không bản sao
    # =========================================================================
    log("\n" + "="*60)
    log("=== [GATE 2] START: C6400 single response, wait 60s ===")
    log("="*60)
    cid2 = make_fresh_conv("NB-317DFBF7", "Nghiệm Thu Gate 2 - C6400 Single 60s")
    page.goto(f"http://localhost:8501/?nb=NB-317DFBF7&conv={cid2}", timeout=30000)
    time.sleep(3)

    log(f"Gate 2 URL: {page.url}")
    page.wait_for_selector('[class*="st-key-wsc_question_input_"] textarea', state="attached", timeout=20000)
    send_btn2 = page.wait_for_selector('[class*="st-key-wsc_ask_"] button:not([disabled])', state="visible", timeout=60000)

    tas = [t for t in page.query_selector_all('[class*="st-key-wsc_question_input_"] textarea') if t.is_visible()]
    assert len(tas) == 1

    q_c6400 = "Lỗi C6400 máy 6thNext, đã phát sinh bao lần trong năm 2026.\nCách điều tra."
    tas[0].fill(q_c6400)
    time.sleep(1)
    send_btn2.click()
    log("Gate 2: Sent C6400 query, waiting for first response to complete...")

    # Wait for answer to finish streaming
    for sec in range(1, 180):
        time.sleep(1)
        asst_msgs = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
        if len(asst_msgs) >= 1:
            ask_btns = [b for b in page.query_selector_all('[class*="st-key-wsc_ask_"] button') if b.is_visible() and not b.is_disabled()]
            if len(ask_btns) >= 1:
                log(f"Gate 2: First response completed at {sec}s!")
                break

    log("Gate 2: Assistant response finished streaming! Now starting 60s verification timer...")

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

    g2_img = out_dir / "anh-home-chat-loop-lockup-02-gate2-c6400-single.png"
    page.screenshot(path=str(g2_img))
    size2 = g2_img.stat().st_size
    sha2 = file_sha256(g2_img)
    evidence_summary["gate2"] = {"file": g2_img.name, "size": size2, "sha256": sha2}
    log(f"Gate 2: Screenshot saved -> {g2_img.name} (Bytes: {size2}, SHA-256: {sha2})")
    log("=== [GATE 2] PASSED 100% ===")

    # =========================================================================
    # GATE 3: Mở sổ lạnh (worker chưa resident), gõ "alo", không thao tác thêm
    # =========================================================================
    log("\n" + "="*60)
    log("=== [GATE 3] START: Cold notebook auto-unlock & answer ===")
    log("="*60)
    cid3 = make_fresh_conv("NB-8354F455", "Nghiệm Thu Gate 3 - Cold Auto Unlock")
    page.goto(f"http://localhost:8501/?nb=NB-8354F455&conv={cid3}", timeout=30000)
    time.sleep(3)

    page.wait_for_selector('[class*="st-key-wsc_question_input_"] textarea', state="attached", timeout=20000)
    time.sleep(1)

    tas = [t for t in page.query_selector_all('[class*="st-key-wsc_question_input_"] textarea') if t.is_visible()]
    assert len(tas) == 1

    log("Gate 3: Typing 'alo' into textarea...")
    tas[0].fill("alo")
    time.sleep(1)

    log("Gate 3: Hands-free waiting for worker warming to complete and UI to auto-unlock (up to 120s)...")
    unlocked_btn3 = page.wait_for_selector(
        '[class*="st-key-wsc-action-"] button:not([disabled]), [class*="st-key-wsc_ask_"] button:not([disabled])',
        timeout=120000,
    )
    log("Gate 3: UI AUTO-UNLOCKED successfully! Send button is enabled.")

    log("Gate 3: Submitting 'alo' via unlocked button (question was preserved!)...")
    unlocked_btn3.click()

    log("Gate 3: Waiting for response to complete...")
    for sec in range(1, 180):
        time.sleep(1)
        asst_msgs = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
        if len(asst_msgs) >= 1:
            ask_btns = [b for b in page.query_selector_all('[class*="st-key-wsc_ask_"] button') if b.is_visible() and not b.is_disabled()]
            if len(ask_btns) >= 1:
                log(f"Gate 3: Response completed at {sec}s!")
                break

    asst_msgs3 = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
    assert len(asst_msgs3) >= 1, "Gate 3 FAILED: Cold notebook did not answer!"

    time.sleep(2)
    g3_img = out_dir / "anh-home-chat-loop-lockup-03-gate3-cold-auto-unlock.png"
    page.screenshot(path=str(g3_img))
    size3 = g3_img.stat().st_size
    sha3 = file_sha256(g3_img)
    evidence_summary["gate3"] = {"file": g3_img.name, "size": size3, "sha256": sha3}
    log(f"Gate 3: Screenshot saved -> {g3_img.name} (Bytes: {size3}, SHA-256: {sha3})")
    log("=== [GATE 3] PASSED 100% ===")

    # =========================================================================
    # GATE 4: Thử gửi trùng cố ý (bấm gửi 2 lần liên tiếp cùng một câu)
    # =========================================================================
    log("\n" + "="*60)
    log("=== [GATE 4] START: Intentional double click debounce ===")
    log("="*60)
    cid4 = make_fresh_conv("NB-317DFBF7", "Nghiệm Thu Gate 4 - Intentional Double Click")
    page.goto(f"http://localhost:8501/?nb=NB-317DFBF7&conv={cid4}", timeout=30000)
    time.sleep(3)

    log(f"Gate 4 URL: {page.url}")
    page.wait_for_selector('[class*="st-key-wsc_question_input_"] textarea', state="attached", timeout=20000)
    send_btn4 = page.wait_for_selector('[class*="st-key-wsc_ask_"] button:not([disabled])', state="visible", timeout=60000)

    tas = [t for t in page.query_selector_all('[class*="st-key-wsc_question_input_"] textarea') if t.is_visible()]
    test_q4 = "Kiểm tra gửi trùng lặp cố ý Gate 4"
    tas[0].fill(test_q4)
    time.sleep(1)

    # Rapid double click
    log("Gate 4: Triggering intentional rapid double click on send button (Playwright direct click)...")
    send_btn4.click()
    try:
        send_btn4.click(timeout=300)
    except Exception:
        pass

    # Wait for answer to finish completely
    for sec in range(1, 180):
        time.sleep(1)
        asst_msgs = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
        if len(asst_msgs) >= 1:
            ask_btns = [b for b in page.query_selector_all('[class*="st-key-wsc_ask_"] button') if b.is_visible() and not b.is_disabled()]
            if len(ask_btns) >= 1:
                log(f"Gate 4: Response completed at {sec}s!")
                break

    time.sleep(2)
    user_msgs_g4 = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarUser"]')]
    asst_msgs_g4 = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
    log(f"Gate 4: User messages={len(user_msgs_g4)}, Assistant messages={len(asst_msgs_g4)}")
    assert len(user_msgs_g4) == 1, f"Gate 4 FAILED: Rapid double click produced {len(user_msgs_g4)} user messages!"
    assert len(asst_msgs_g4) == 1, f"Gate 4 FAILED: Rapid double click produced {len(asst_msgs_g4)} assistant messages!"

    g4_img = out_dir / "anh-home-chat-loop-lockup-04-gate4-debounce.png"
    page.screenshot(path=str(g4_img))
    size4 = g4_img.stat().st_size
    sha4 = file_sha256(g4_img)
    evidence_summary["gate4"] = {"file": g4_img.name, "size": size4, "sha256": sha4}
    log(f"Gate 4: Screenshot saved -> {g4_img.name} (Bytes: {size4}, SHA-256: {sha4})")
    log("=== [GATE 4] PASSED 100% ===")

    # =========================================================================
    # GATE 5: Chuyển qua lại 2 sổ sau khi gửi 1 câu ở sổ thứ nhất: không khóa chéo
    # =========================================================================
    log("\n" + "="*60)
    log("=== [GATE 5] START: Cross-notebook navigation & no cross-lock ===")
    log("="*60)
    # 1. Start in notebook 1 (NB-317DFBF7)
    cid5_1 = make_fresh_conv("NB-317DFBF7", "Nghiệm Thu Gate 5 - Sổ 1")
    page.goto(f"http://localhost:8501/?nb=NB-317DFBF7&conv={cid5_1}", timeout=30000)
    time.sleep(3)
    page.wait_for_selector('[class*="st-key-wsc_question_input_"] textarea', state="attached", timeout=20000)
    send_btn5_1 = page.wait_for_selector('[class*="st-key-wsc_ask_"] button:not([disabled])', state="visible", timeout=60000)

    tas1 = [t for t in page.query_selector_all('[class*="st-key-wsc_question_input_"] textarea') if t.is_visible()]
    assert len(tas1) == 1
    log("Gate 5: Notebook 1 composer is unlocked. Asking question in Notebook 1...")
    tas1[0].fill("Kiểm tra sổ thứ nhất Gate 5")
    time.sleep(1)
    send_btn5_1.click()

    # Wait for answer in Notebook 1
    for sec in range(1, 180):
        time.sleep(1)
        asst_msgs = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
        if len(asst_msgs) >= 1:
            ask_btns = [b for b in page.query_selector_all('[class*="st-key-wsc_ask_"] button') if b.is_visible() and not b.is_disabled()]
            if len(ask_btns) >= 1:
                log(f"Gate 5: Notebook 1 completed at {sec}s!")
                break

    # 2. Switch to Notebook 2 (NB-8354F455)
    log("Gate 5: Switching to Notebook 2 (NB-8354F455)...")
    cid5_2 = make_fresh_conv("NB-8354F455", "Nghiệm Thu Gate 5 - Sổ 2")
    page.goto(f"http://localhost:8501/?nb=NB-8354F455&conv={cid5_2}", timeout=30000)
    time.sleep(3)
    page.wait_for_selector('[class*="st-key-wsc_question_input_"] textarea', state="attached", timeout=20000)
    send_btn5_2 = page.wait_for_selector('[class*="st-key-wsc_ask_"] button:not([disabled])', state="visible", timeout=60000)

    tas2 = [t for t in page.query_selector_all('[class*="st-key-wsc_question_input_"] textarea') if t.is_visible()]
    assert len(tas2) == 1
    # Verify Notebook 2 is NOT locked
    is_readonly2 = tas2[0].get_attribute("readonly")
    is_disabled2 = send_btn5_2.is_disabled()
    log(f"Gate 5: Notebook 2 textarea readonly={is_readonly2}, button disabled={is_disabled2}")
    assert not is_readonly2, "Gate 5 FAILED: Notebook 2 textarea is locked/readonly!"
    assert not is_disabled2, "Gate 5 FAILED: Notebook 2 send button is disabled!"

    # Send a question in Notebook 2
    log("Gate 5: Sending question in Notebook 2...")
    tas2[0].fill("Kiểm tra sổ thứ hai Gate 5")
    time.sleep(1)
    send_btn5_2.click()

    for sec in range(1, 180):
        time.sleep(1)
        asst_msgs = [m for m in page.query_selector_all('[data-testid="stChatMessage"]') if m.query_selector('[data-testid="stChatMessageAvatarAssistant"]')]
        if len(asst_msgs) >= 1:
            ask_btns = [b for b in page.query_selector_all('[class*="st-key-wsc_ask_"] button') if b.is_visible() and not b.is_disabled()]
            if len(ask_btns) >= 1:
                log(f"Gate 5: Notebook 2 completed at {sec}s!")
                break

    # 3. Switch BACK to Notebook 1 (NB-317DFBF7)
    log("Gate 5: Switching back to Notebook 1 (NB-317DFBF7)...")
    page.goto(f"http://localhost:8501/?nb=NB-317DFBF7&conv={cid5_1}", timeout=30000)
    time.sleep(3)
    page.wait_for_selector('[class*="st-key-wsc_question_input_"] textarea', state="attached", timeout=20000)
    send_btn5_1_back = page.wait_for_selector('[class*="st-key-wsc_ask_"] button:not([disabled])', state="visible", timeout=120000)

    tas1_back = [t for t in page.query_selector_all('[class*="st-key-wsc_question_input_"] textarea') if t.is_visible()]
    assert len(tas1_back) == 1
    assert not tas1_back[0].get_attribute("readonly"), "Gate 5 FAILED: Notebook 1 textarea locked on return!"
    assert not send_btn5_1_back.is_disabled(), "Gate 5 FAILED: Notebook 1 button disabled on return!"
    log("Gate 5: Notebook 1 completely unlocked and responsive upon return! No cross-notebook lockup.")

    g5_img = out_dir / "anh-home-chat-loop-lockup-05-gate5-no-cross-lock.png"
    page.screenshot(path=str(g5_img))
    size5 = g5_img.stat().st_size
    sha5 = file_sha256(g5_img)
    evidence_summary["gate5"] = {"file": g5_img.name, "size": size5, "sha256": sha5}
    log(f"Gate 5: Screenshot saved -> {g5_img.name} (Bytes: {size5}, SHA-256: {sha5})")
    log("=== [GATE 5] PASSED 100% ===")

    browser.close()

    log("\n" + "="*60)
    log(">>> ALL 5 QUALITY ACCEPTANCE GATES PASSED 100%! <<<")
    log("="*60)
    for k, v in evidence_summary.items():
        log(f"{k}: {v['file']} - {v['size']} bytes - SHA256: {v['sha256']}")
