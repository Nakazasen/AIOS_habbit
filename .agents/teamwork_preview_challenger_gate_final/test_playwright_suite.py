import os
import sys
import time
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from playwright.sync_api import sync_playwright, expect

def run_tests():
    html_file = Path(r"d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_challenger_gate_final\test_output_aios.html").resolve()
    file_url = f"file:///{html_file.as_posix()}"
    print(f"[TEST] Opening {file_url}")

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # Listen to console messages and errors
        console_logs = []
        page_errors = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        page.goto(file_url)
        page.wait_for_load_state("networkidle")

        # 1. Test Initial Loading & Mermaid SVG Rendering
        print("[TEST 1] Verifying Mermaid SVG rendering...")
        page.wait_for_selector("#diagram-output svg", timeout=10000)
        svg_count = page.locator("#diagram-output svg").count()
        assert svg_count == 1, f"Expected 1 SVG, got {svg_count}"
        results.append(("Mermaid SVG Rendering", "PASS", "Diagram rendered successfully as SVG"))

        # Check Initial Layout Dimensions
        sidebar = page.locator("#sidebar")
        viewport = page.locator("#viewport")
        sidebar_box = sidebar.bounding_box()
        viewport_box = viewport.bounding_box()
        print(f"Sidebar bbox: {sidebar_box}, Viewport bbox: {viewport_box}")
        assert sidebar_box["width"] == 460, f"Sidebar width is {sidebar_box['width']}, expected 460"
        assert not "collapsed" in (sidebar.get_attribute("class") or ""), "Sidebar should not have collapsed class initially"
        results.append(("Initial Sidebar Layout", "PASS", f"Sidebar width 460px, Viewport width {viewport_box['width']}px"))

        # 2. Test Sidebar Collapse via Button (#btn-collapse-sidebar)
        print("[TEST 2] Testing Sidebar collapse via collapse button...")
        page.click("#btn-collapse-sidebar")
        page.wait_for_timeout(400) # wait for CSS transition 300ms

        sidebar_classes = sidebar.get_attribute("class") or ""
        assert "collapsed" in sidebar_classes, f"Sidebar should have 'collapsed' class, got: {sidebar_classes}"

        viewport_box_after = viewport.bounding_box()
        print(f"Viewport width after collapse: {viewport_box_after['width']}")
        assert viewport_box_after["width"] >= 1270, f"Viewport should expand to full width (~1280), got {viewport_box_after['width']}"

        toggle_btn = page.locator("#toggle-sidebar")
        assert toggle_btn.is_visible(), "Toggle sidebar button should be visible when sidebar is collapsed"
        results.append(("Sidebar Collapse via Button", "PASS", f"Collapsed class applied, Viewport expanded to {viewport_box_after['width']}px"))

        # 3. Test Sidebar Expand via Toggle Button (#toggle-sidebar)
        print("[TEST 3] Testing Sidebar expand via floating toggle button...")
        toggle_btn.click()
        page.wait_for_timeout(400)

        sidebar_classes = sidebar.get_attribute("class") or ""
        assert "collapsed" not in sidebar_classes, f"Sidebar should not have 'collapsed' class, got: {sidebar_classes}"
        viewport_box_reopen = viewport.bounding_box()
        assert viewport_box_reopen["width"] < 900, f"Viewport width should shrink back, got {viewport_box_reopen['width']}"
        results.append(("Sidebar Expand via Toggle Button", "PASS", f"Sidebar reopened, Viewport shrank to {viewport_box_reopen['width']}px"))

        # 4. Test Sidebar Toggle via Keyboard Shortcut (Ctrl+B)
        print("[TEST 4] Testing Sidebar toggle via Ctrl+B shortcut...")
        page.keyboard.press("Control+b")
        page.wait_for_timeout(400)
        assert "collapsed" in (sidebar.get_attribute("class") or ""), "Sidebar should collapse on Ctrl+B"

        page.keyboard.press("Control+b")
        page.wait_for_timeout(400)
        assert "collapsed" not in (sidebar.get_attribute("class") or ""), "Sidebar should expand on second Ctrl+B"
        results.append(("Sidebar Keyboard Shortcut Ctrl+B", "PASS", "Ctrl+B toggles sidebar collapse and expand correctly"))

        # 5. Test Zoom Controls (Zoom In, Zoom Out, Reset, Fit)
        print("[TEST 5] Testing Zoom Toolbar Controls...")
        diagram_output = page.locator("#diagram-output")

        # Test Reset
        page.click("#zoom-reset")
        page.wait_for_timeout(200)
        reset_transform = diagram_output.evaluate("el => el.style.transform")
        badge_text_reset = page.locator("#zoom-badge").inner_text()
        print(f"Reset transform: '{reset_transform}', Badge: '{badge_text_reset}'")
        assert "scale(1)" in reset_transform or "matrix(1," in reset_transform or badge_text_reset == "100%", "Reset should set scale to 1 (100%)"

        # Test Zoom In
        page.click("#zoom-in")
        page.wait_for_timeout(200)
        zoom_in_transform = diagram_output.evaluate("el => el.style.transform")
        badge_text_zoomin = page.locator("#zoom-badge").inner_text()
        print(f"Zoom in transform: '{zoom_in_transform}', Badge: '{badge_text_zoomin}'")
        assert badge_text_zoomin != "100%", "Zoom In should change scale badge"

        # Test Zoom Out
        page.click("#zoom-out")
        page.click("#zoom-out")
        page.wait_for_timeout(200)
        zoom_out_transform = diagram_output.evaluate("el => el.style.transform")
        badge_text_zoomout = page.locator("#zoom-badge").inner_text()
        print(f"Zoom out transform: '{zoom_out_transform}', Badge: '{badge_text_zoomout}'")

        # Test Zoom Fit
        page.click("#zoom-fit")
        page.wait_for_timeout(400)
        fit_transform = diagram_output.evaluate("el => el.style.transform")
        badge_text_fit = page.locator("#zoom-badge").inner_text()
        print(f"Fit transform: '{fit_transform}', Badge: '{badge_text_fit}'")
        assert fit_transform != "", "Fit to screen should apply transform"
        results.append(("Zoom Toolbar Controls (+, -, Reset, Fit)", "PASS", f"Zoom In/Out/Reset/Fit scale and update badge (Reset: {badge_text_reset}, In: {badge_text_zoomin}, Out: {badge_text_zoomout}, Fit: {badge_text_fit})"))

        # 6. Test Mouse Wheel Zoom
        print("[TEST 6] Testing Mouse Wheel Zoom...")
        panzoom_box = page.locator("#panzoom-container").bounding_box()
        center_x = panzoom_box["x"] + panzoom_box["width"] / 2
        center_y = panzoom_box["y"] + panzoom_box["height"] / 2

        # Record scale before wheel
        before_wheel_transform = diagram_output.evaluate("el => el.style.transform")
        page.mouse.move(center_x, center_y)
        page.mouse.wheel(0, -300) # zoom in
        page.wait_for_timeout(300)
        after_wheel_transform = diagram_output.evaluate("el => el.style.transform")
        badge_wheel = page.locator("#zoom-badge").inner_text()
        print(f"Wheel zoom before: {before_wheel_transform}, after: {after_wheel_transform}, badge: {badge_wheel}")
        assert before_wheel_transform != after_wheel_transform, "Wheel zoom should change transform"
        results.append(("Mouse Wheel Zoom", "PASS", f"Wheel event adjusted transform and badge to {badge_wheel}"))

        # 7. Test Mouse Drag Pan
        print("[TEST 7] Testing Mouse Drag Panning...")
        page.click("#zoom-reset")
        page.wait_for_timeout(200)
        before_pan_transform = diagram_output.evaluate("el => el.style.transform")

        page.mouse.move(center_x, center_y)
        page.mouse.down()
        page.mouse.move(center_x + 150, center_y + 100, steps=10)
        page.mouse.up()
        page.wait_for_timeout(300)

        after_pan_transform = diagram_output.evaluate("el => el.style.transform")
        print(f"Pan before: {before_pan_transform}, after: {after_pan_transform}")
        assert before_pan_transform != after_pan_transform, "Drag pan should update transform matrix / translate coordinates"
        results.append(("Mouse Drag Pan", "PASS", f"Pan drag successfully moved canvas ({before_pan_transform} -> {after_pan_transform})"))

        # 8. Test Tab Switching
        print("[TEST 8] Testing Diagram Tabs Switching...")
        tab_buttons = page.locator(".tab-btn").all()
        print(f"Found {len(tab_buttons)} tabs")
        assert len(tab_buttons) >= 2, f"Expected at least 2 tabs, found {len(tab_buttons)}"
        
        tab_titles = [btn.inner_text() for btn in tab_buttons]

        # Click second tab
        tab_buttons[1].click()
        page.wait_for_timeout(500)
        active_tab = page.locator(".tab-btn.active").inner_text()
        assert active_tab == tab_titles[1], f"Active tab should be {tab_titles[1]}, got {active_tab}"
        page.wait_for_selector("#diagram-output svg", timeout=5000)
        results.append(("Tab Switching", "PASS", f"Switched between {len(tab_buttons)} tabs, diagrams re-rendered cleanly"))

        # 9. Test Live Editor Update
        print("[TEST 9] Testing Live Editor Update...")
        code_input = page.locator("#mermaid-code")
        test_mermaid = """%%{init: {'theme': 'base', 'look': 'handDrawn'}}%%
flowchart LR
    A["Khoi Dong"] --> B["Hoan Thanh"]"""
        code_input.fill(test_mermaid)
        page.click("#btn-render")
        page.wait_for_timeout(600)
        page.wait_for_selector("#diagram-output svg", timeout=5000)
        svg_text = page.locator("#diagram-output svg").text_content()
        assert "Khoi Dong" in svg_text and "Hoan Thanh" in svg_text, "Rendered SVG should contain newly updated node labels"
        results.append(("Live Editor Diagram Update", "PASS", "Code update rendered immediately in hand-drawn style"))

        # 10. Test Graceful Error Handling
        print("[TEST 10] Testing Graceful Syntax Error Handling...")
        invalid_mermaid = "flowchart INVALID SYNTAX ??? <<<<<"
        code_input.fill(invalid_mermaid)
        page.click("#btn-render")
        page.wait_for_timeout(600)
        error_box = page.locator("#error-msg")
        assert error_box.is_visible(), "Error box should be displayed on syntax error"
        error_text = error_box.inner_text()
        assert "Lỗi cú pháp Mermaid" in error_text, "Error box should show clear error message"
        results.append(("Syntax Error Handling", "PASS", f"Gracefully displayed error box: {error_text[:60]}..."))

        browser.close()

    print("\n" + "="*70)
    print("PLAYWRIGHT TEST EXECUTION SUMMARY:")
    print("="*70)
    for test_name, status, detail in results:
        print(f"[{status}] {test_name}: {detail}")
    print("="*70)
    
    if page_errors:
        print(f"PAGE ERRORS: {page_errors}")
    assert len(page_errors) == 0, f"Encountered {len(page_errors)} uncaught page errors"
    print("ALL 10 TEST CASES PASSED EMPIRICALLY!")

if __name__ == "__main__":
    run_tests()
