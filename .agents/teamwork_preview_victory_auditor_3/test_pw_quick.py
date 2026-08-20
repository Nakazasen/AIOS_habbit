import sys, time
from playwright.sync_api import sync_playwright

print('Starting playwright test...', flush=True)
with sync_playwright() as p:
    print('Launching chromium...', flush=True)
    browser = p.chromium.launch(headless=True)
    print('Chromium launched!', flush=True)
    page = browser.new_page()
    print('New page created!', flush=True)
    browser.close()
print('Finished cleanly!', flush=True)
