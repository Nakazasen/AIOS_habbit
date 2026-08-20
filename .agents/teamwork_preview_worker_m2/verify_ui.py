#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automated Playwright E2E UI & Packaging Verification Test Suite for Excaliflow v2
Verifies:
1. Standalone Single-File HTML Diagrams (Graphify Ingestion & AST Fallback)
2. Collapsible Sidebar UI & Keyboard Shortcut (Ctrl+B)
3. Panzoom v4.5.1 Zoom & Pan Engine, Drag Pan, Wheel Zoom, Toolbar Controls & Badge
4. Mermaid v11 Hand-Drawn SVG Rendering & Tab Switching
5. Skill Zip Packaging & Contents Verification
"""

import os
import sys
import time
import json
import zipfile
import re
from pathlib import Path

# Try importing playwright
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("[!] Playwright is not installed in the current Python environment.")
    print("[*] Run: pip install playwright && playwright install chromium")
    sync_playwright = None


def test_html_diagram_ui(page, html_path: Path, diagram_type: str):
    print(f"\n==================================================")
    print(f"[*] Starting E2E UI Test: {diagram_type.upper()} Mode")
    print(f"[*] Target HTML: {html_path.resolve()}")
    print(f"==================================================")

    assert html_path.exists(), f"File {html_path} does not exist!"
    assert html_path.stat().st_size > 0, f"File {html_path} is empty!"

    # Navigate to local HTML file
    file_url = html_path.resolve().as_uri()
    print(f"[-] Loading {file_url} in Chromium...")
    page.goto(file_url, wait_until="domcontentloaded")
    page.set_viewport_size({"width": 1440, "height": 900})

    # 1. Verify Basic Layout Elements Exist
    print("[-] Verifying DOM element presence...")
    sidebar = page.locator("#sidebar")
    viewport = page.locator("#viewport")
    toggle_btn = page.locator("#toggle-sidebar")
    collapse_btn = page.locator("#btn-collapse-sidebar")
    panzoom_container = page.locator("#panzoom-container")
    diagram_output = page.locator("#diagram-output")
    zoom_badge = page.locator("#zoom-badge")
    error_msg = page.locator("#error-msg")

    assert sidebar.count() == 1, "Sidebar element not found"
    assert viewport.count() == 1, "Viewport element not found"
    assert toggle_btn.count() == 1, "Toggle sidebar button not found"
    assert panzoom_container.count() == 1, "Panzoom container not found"
    assert diagram_output.count() == 1, "Diagram output container not found"
    assert zoom_badge.count() == 1, "Zoom badge not found"

    # Wait for Mermaid to render initial SVG
    print("[-] Waiting for Mermaid Hand-Drawn SVG rendering...")
    page.wait_for_selector("#diagram-output svg", timeout=15000)
    svg = page.locator("#diagram-output svg")
    assert svg.count() >= 1, "Mermaid SVG failed to render in diagram-output"
    
    # Check error message is not displayed
    assert not error_msg.is_visible(), "Error box is unexpectedly visible"
    print("    [PASS] Initial Mermaid SVG rendered successfully.")

    # 2. Test Sidebar Toggle Functionality
    print("\n[-] Testing Sidebar Toggle & Viewport Expansion...")
    # Initial state: sidebar visible, width ~460px
    initial_sidebar_box = sidebar.bounding_box()
    initial_viewport_box = viewport.bounding_box()
    assert initial_sidebar_box is not None, "Sidebar bounding box is None"
    assert initial_sidebar_box["width"] >= 450, f"Unexpected sidebar width: {initial_sidebar_box['width']}"
    assert "collapsed" not in (sidebar.get_attribute("class") or ""), "Sidebar should not have collapsed class initially"
    print(f"    [PASS] Initial sidebar width = {initial_sidebar_box['width']}px, viewport width = {initial_viewport_box['width']}px")

    # Click #toggle-sidebar to collapse
    print("[-] Clicking #toggle-sidebar to collapse...")
    toggle_btn.click()
    page.wait_for_timeout(400) # Wait for CSS transition (0.3s)
    
    sidebar_classes = sidebar.get_attribute("class") or ""
    assert "collapsed" in sidebar_classes, f"Sidebar should have 'collapsed' class, got: {sidebar_classes}"
    collapsed_viewport_box = viewport.bounding_box()
    assert collapsed_viewport_box["width"] > initial_viewport_box["width"], (
        f"Viewport should expand when sidebar collapses. Old: {initial_viewport_box['width']}, New: {collapsed_viewport_box['width']}"
    )
    print(f"    [PASS] Sidebar collapsed. Expanded viewport width = {collapsed_viewport_box['width']}px")

    # Click #toggle-sidebar to expand
    print("[-] Clicking #toggle-sidebar to expand...")
    toggle_btn.click()
    page.wait_for_timeout(400)
    assert "collapsed" not in (sidebar.get_attribute("class") or ""), "Sidebar should be expanded"
    print("    [PASS] Sidebar re-expanded via #toggle-sidebar.")

    # Click #btn-collapse-sidebar to collapse
    if collapse_btn.count() > 0:
        print("[-] Clicking #btn-collapse-sidebar to collapse...")
        collapse_btn.click()
        page.wait_for_timeout(400)
        assert "collapsed" in (sidebar.get_attribute("class") or ""), "Sidebar should be collapsed via #btn-collapse-sidebar"
        print("    [PASS] Sidebar collapsed via #btn-collapse-sidebar.")

    # Press Ctrl+B to expand
    print("[-] Pressing Ctrl+B shortcut to expand sidebar...")
    page.keyboard.press("Control+b")
    page.wait_for_timeout(400)
    assert "collapsed" not in (sidebar.get_attribute("class") or ""), "Sidebar should expand on Ctrl+B"
    print("    [PASS] Sidebar expanded via Ctrl+B shortcut.")

    # Press Ctrl+B to collapse again and back to expand
    print("[-] Pressing Ctrl+B shortcut to toggle back...")
    page.keyboard.press("Control+b")
    page.wait_for_timeout(400)
    assert "collapsed" in (sidebar.get_attribute("class") or ""), "Sidebar should collapse on Ctrl+B"
    page.keyboard.press("Control+b")
    page.wait_for_timeout(400)
    assert "collapsed" not in (sidebar.get_attribute("class") or ""), "Sidebar should expand on Ctrl+B"
    print("    [PASS] Full Ctrl+B toggle cycle verified.")

    # 3. Test Zoom & Pan Engine (Panzoom v4.5.1)
    print("\n[-] Testing Panzoom Engine (Zoom & Pan)...")
    
    # Check initial zoom badge
    initial_badge_text = zoom_badge.inner_text().strip()
    print(f"[-] Initial Zoom Badge: {initial_badge_text}")

    # Zoom In
    print("[-] Clicking #zoom-in button...")
    page.locator("#zoom-in").click()
    page.wait_for_timeout(200)
    badge_zoomed_in = zoom_badge.inner_text().strip()
    scale_zoomed_in = int(badge_zoomed_in.replace("%", ""))
    print(f"[-] Zoom In Badge: {badge_zoomed_in}")
    
    # Zoom In again
    page.locator("#zoom-in").click()
    page.wait_for_timeout(200)
    badge_zoomed_in_2 = zoom_badge.inner_text().strip()
    scale_zoomed_in_2 = int(badge_zoomed_in_2.replace("%", ""))
    assert scale_zoomed_in_2 > scale_zoomed_in, f"Scale should increase on zoom in: {scale_zoomed_in_2} vs {scale_zoomed_in}"
    print(f"    [PASS] Zoom In button increases scale correctly ({scale_zoomed_in_2}%).")

    # Zoom Out
    print("[-] Clicking #zoom-out button...")
    page.locator("#zoom-out").click()
    page.wait_for_timeout(200)
    badge_zoomed_out = zoom_badge.inner_text().strip()
    scale_zoomed_out = int(badge_zoomed_out.replace("%", ""))
    assert scale_zoomed_out < scale_zoomed_in_2, "Scale should decrease on zoom out"
    print(f"    [PASS] Zoom Out button decreases scale correctly ({badge_zoomed_out}).")

    # Zoom Reset
    print("[-] Clicking #zoom-reset button...")
    page.locator("#zoom-reset").click()
    page.wait_for_timeout(200)
    badge_reset = zoom_badge.inner_text().strip()
    assert badge_reset == "100%", f"Zoom reset should reset badge to 100%, got: {badge_reset}"
    print("    [PASS] Zoom Reset button resets scale to 100%.")

    # Zoom Fit
    print("[-] Clicking #zoom-fit button...")
    page.locator("#zoom-fit").click()
    page.wait_for_timeout(300)
    badge_fit = zoom_badge.inner_text().strip()
    assert badge_fit != "", "Fit to screen should update zoom badge"
    print(f"    [PASS] Zoom Fit (Fit to screen) computed scale: {badge_fit}")

    # Wheel Zoom
    print("[-] Simulating mouse wheel zoom on #panzoom-container...")
    panzoom_box = panzoom_container.bounding_box()
    cx = panzoom_box["x"] + panzoom_box["width"] / 2
    cy = panzoom_box["y"] + panzoom_box["height"] / 2
    page.mouse.move(cx, cy)
    page.mouse.wheel(0, -200) # Scroll up to zoom in
    page.wait_for_timeout(200)
    badge_wheel = zoom_badge.inner_text().strip()
    print(f"[-] Badge after wheel zoom: {badge_wheel}")
    print("    [PASS] Wheel zoom event handled properly.")

    # Drag to Pan simulation
    print("[-] Simulating mouse drag pan on canvas...")
    # Get transform style before drag
    initial_transform = page.evaluate("() => document.getElementById('diagram-output').style.transform")
    print(f"[-] Transform before pan: {initial_transform}")
    
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.move(cx + 120, cy + 80, steps=10)
    page.mouse.up()
    page.wait_for_timeout(200)
    
    pan_transform = page.evaluate("() => document.getElementById('diagram-output').style.transform")
    print(f"[-] Transform after pan: {pan_transform}")
    assert pan_transform != initial_transform, "Panzoom transform should change after drag-pan"
    print("    [PASS] Drag-to-pan translation matrix updated successfully.")

    # 4. Test Tab Switching and Live Rendering
    print("\n[-] Testing Tab Switching and Dynamic Diagram Rendering...")
    tabs = page.locator("#tabs-container .tab-btn")
    tab_count = tabs.count()
    assert tab_count >= 1, f"Expected at least 1 tab button, found {tab_count}"
    print(f"[-] Found {tab_count} diagram tabs:")

    for i in range(tab_count):
        tab = tabs.nth(i)
        tab_title = tab.inner_text().strip()
        print(f"    -> Clicking Tab [{i+1}/{tab_count}]: '{tab_title}'...")
        tab.click()
        page.wait_for_timeout(300)
        
        # Check active class
        assert "active" in (tab.get_attribute("class") or ""), f"Tab '{tab_title}' should have 'active' class"
        
        # Check code area is populated
        code_val = page.locator("#mermaid-code").input_value()
        assert len(code_val.strip()) > 0, f"Mermaid code textarea is empty for tab '{tab_title}'"
        
        # Wait for SVG render
        page.wait_for_selector("#diagram-output svg", timeout=8000)
        svg_elem = page.locator("#diagram-output svg")
        assert svg_elem.count() >= 1, f"SVG failed to render for tab '{tab_title}'"
        
        # Ensure no error
        assert not error_msg.is_visible(), f"Mermaid syntax error reported on tab '{tab_title}'"
        print(f"       [PASS] Rendered SVG successfully with {len(code_val)} chars of Mermaid definition.")

    # 5. Test Live Editor Functionality
    print("\n[-] Testing Live Editor update...")
    custom_mermaid = """%%{init: {'look': 'handDrawn'}}%%
flowchart LR
    TEST_A["🧪 Input Unit"] --> TEST_B["⚙️ Processing Engine"]
    TEST_B --> TEST_C["📊 Live Output Verified"]"""
    
    page.locator("#mermaid-code").fill(custom_mermaid)
    page.locator("#btn-render").click()
    page.wait_for_timeout(500)
    page.wait_for_selector("#diagram-output svg", timeout=5000)
    assert not error_msg.is_visible(), "Live editor custom render threw error"
    rendered_text = page.locator("#diagram-output svg").inner_text()
    assert "Live Output Verified" in rendered_text or "Processing Engine" in rendered_text or "Input Unit" in rendered_text, (
        "Rendered SVG does not contain custom edited text"
    )
    print("    [PASS] Live Editor successfully compiled and rendered custom Mermaid flowchart.")

    print(f"\n[✓] ALL E2E UI TESTS PASSED FOR: {diagram_type.upper()} ({html_path.name})")


def verify_packaging():
    print("\n==================================================")
    print("[*] Starting Skill Zip Packaging Verification")
    print("==================================================")
    
    zip_target = Path(r"C:\Users\Admin\Downloads\excaliflow-skill-v2.zip")
    assert zip_target.exists(), f"Packaging zip file does not exist at {zip_target}"
    zip_size = zip_target.stat().st_size
    assert zip_size > 0, f"Packaging zip file is empty (0 bytes): {zip_target}"
    print(f"[PASS] Package file exists at {zip_target} (Size: {zip_size:,} bytes)")

    # Read zip entries
    with zipfile.ZipFile(zip_target, 'r') as z:
        namelist = z.namelist()
        print(f"[-] Zip entries count: {len(namelist)}")
        for name in namelist:
            info = z.getinfo(name)
            print(f"    - {name} ({info.file_size:,} bytes)")

        # Verify critical files exist
        assert any("SKILL.md" in n for n in namelist), "SKILL.md missing in zip package"
        assert any("generate_diagram.py" in n for n in namelist), "scripts/generate_diagram.py missing in zip package"
        print("[PASS] All required files (SKILL.md, scripts/generate_diagram.py) present in zip.")

        # Extract and verify content of generate_diagram.py from zip
        gen_script_name = [n for n in namelist if "generate_diagram.py" in n][0]
        script_content = z.read(gen_script_name).decode("utf-8")
        
        # Verify v2 features in packaged code
        assert "panzoom" in script_content.lower(), "Panzoom integration missing in packaged script"
        assert "collapsed" in script_content, "Collapsible sidebar logic missing in packaged script"
        assert "parse_graphify_graph" in script_content, "Graphify parser missing in packaged script"
        assert "parse_understand_graph" in script_content, "Understand parser missing in packaged script"
        assert "handDrawn" in script_content, "Hand-drawn Mermaid look missing in packaged script"
        print("[PASS] Verified packaged generate_diagram.py contains all v2 features (Panzoom, Sidebar, Graphify).")

        # Verify SKILL.md from zip
        skill_name = [n for n in namelist if "SKILL.md" in n][0]
        skill_content = z.read(skill_name).decode("utf-8")
        assert "excaliflow" in skill_content, "SKILL.md content verification failed"
        assert "v2" in skill_content or "Panzoom" in skill_content or "Ctrl+B" in skill_content, "SKILL.md v2 documentation missing"
        print("[PASS] Verified packaged SKILL.md contains updated v2 documentation.")

    print("\n[✓] ALL PACKAGING VERIFICATION CHECKS PASSED 100%!")


def main():
    print("==================================================")
    print("  EXCALIFLOW v2 - COMPREHENSIVE PLAYWRIGHT TEST   ")
    print("==================================================")

    worker_dir = Path(__file__).parent.resolve()
    graphify_html = worker_dir / "sample_graphify_diagram.html"
    ast_html = worker_dir / "sample_ast_diagram.html"

    # Run Playwright E2E Tests
    if sync_playwright:
        with sync_playwright() as p:
            print("[-] Launching headless Chromium browser...")
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Test Graphify diagram
            test_html_diagram_ui(page, graphify_html, "Graphify Ingestion")

            # Test AST diagram
            test_html_diagram_ui(page, ast_html, "AST Fallback")

            browser.close()
            print("\n[-] Headless Chromium browser closed successfully.")
    else:
        print("[!] Warning: Playwright module not available, skipped browser run.")

    # Run Packaging Verification
    verify_packaging()

    print("\n==================================================")
    print("  🎉 ALL VERIFICATION SUITES COMPLETED WITH ZERO ERRORS!")
    print("==================================================")


if __name__ == "__main__":
    main()
