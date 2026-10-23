# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path
import time
import hashlib

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR / "src"))

from playwright.sync_api import sync_playwright

DIR_DOCS = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
DIR_KO = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--window-size=1440,960"])
    context = browser.new_context(viewport={"width": 1440, "height": 960})
    page = context.new_page()
    page.goto("http://localhost:8501/?nb=mom_opcenter&conv=CONV-ED99859A", wait_until="networkidle", timeout=45000)
    time.sleep(3)

    ta = page.wait_for_selector('textarea[aria-label="Câu hỏi gửi AI"], [class*="st-key-wsc_question_input_"] textarea', timeout=15000)
    ta.click()
    page.keyboard.type("/ky", delay=40)
    time.sleep(1)

    palette = page.wait_for_selector("#wsc-slash-palette", state="visible", timeout=10000)
    print("Palette display style:", palette.evaluate("el => window.getComputedStyle(el).display"))
    print("Palette box:", palette.bounding_box())
    print("Palette innerText:\n", palette.inner_text())

    # Ensure palette is centered/scrolled into view so it is clearly framed
    palette.scroll_into_view_if_needed()
    time.sleep(1.0)

    raw_bytes = page.screenshot(full_page=False)
    p_docs = DIR_DOCS / "anh-user-skill-01-palette.png"
    p_ko = DIR_KO / "anh-user-skill-01-palette.png"
    p_docs.write_bytes(raw_bytes)
    p_ko.write_bytes(raw_bytes)

    size = len(raw_bytes)
    sha = hashlib.sha256(raw_bytes).hexdigest().upper()
    print(f"[OK] Saved anh-user-skill-01-palette.png: {size:,} bytes | SHA256={sha}")
    browser.close()
