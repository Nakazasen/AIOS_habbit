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

cid = "CONV-ED99859A"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--window-size=1440,960"])
    context = browser.new_context(viewport={"width": 1440, "height": 960})
    page = context.new_page()
    page.goto(f"http://localhost:8501/?nb=mom_opcenter&conv={cid}", wait_until="networkidle", timeout=45000)
    time.sleep(3)

    # Locate the skill application badge/header
    badge = page.locator("h3:has-text('Áp dụng kỹ năng cá nhân đã tạo')").first
    badge.wait_for(state="visible", timeout=15000)
    print("Found skill application header:", badge.inner_text())

    # Scroll badge into view near the top of viewport so the full procedure is visible
    badge.scroll_into_view_if_needed()
    time.sleep(1.5)

    raw_bytes = page.screenshot(full_page=False)
    p_docs = DIR_DOCS / "anh-user-skill-04-applied-evidence.png"
    p_ko = DIR_KO / "anh-user-skill-04-applied-evidence.png"
    p_docs.write_bytes(raw_bytes)
    p_ko.write_bytes(raw_bytes)

    size = len(raw_bytes)
    sha = hashlib.sha256(raw_bytes).hexdigest().upper()
    print(f"[OK] Saved anh-user-skill-04-applied-evidence.png: {size:,} bytes | SHA256={sha}")
    browser.close()
