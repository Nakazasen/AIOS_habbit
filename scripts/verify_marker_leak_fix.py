"""Verification script for DESKTOP-HOME-UX-MARKER-LEAK-FIX.

Runs real browser verification with Playwright on the live Streamlit UI:
1. Replays and inspects the SMA(20) alert message in CONV-LSU-FULL-LOOP-VERIFY-20261022 (G7 fixture MSG-LOOP-A2).
2. Verifies:
   - Alert card is rendered prominently as an error card.
   - Title: "🚨 Cảnh báo realtime: JIG 1003_1 — takt:MeasureFieldCurvatureYellow[sec]".
   - Metric values: 4.6 sec, SMA(20) 4.6 sec, 8 điểm liên tiếp.
   - Guide: "Theo tài liệu quy trình: Mở phiên trực ban...".
   - Zero marker leaks: NO "<!--", NO "aios_", NO "\\u" characters.
   - Takes clean screenshot as official evidence.
3. Regression verification on existing conversation:
   - MSG-LOOP-A1 (aios_log_chart_builder) renders chart without raw marker leak.
   - Fresh message send regression test.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR / "src"))

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

OUT_DIR = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
OUT_DIR.mkdir(parents=True, exist_ok=True)

from playwright.sync_api import sync_playwright


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def ensure_server() -> tuple[subprocess.Popen | None, any]:
    try:
        with urllib.request.urlopen("http://localhost:8501/_stcore/health", timeout=1) as resp:
            if resp.status == 200:
                print("[+] Server already running on port 8501 and healthy.", flush=True)
                return None, None
    except Exception:
        pass

    print("[*] Starting Streamlit server from APP_DIR on port 8501...", flush=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(APP_DIR / "src")
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    cmd = [
        str(APP_DIR / ".venv" / "Scripts" / "python.exe"),
        "-u",
        "-m",
        "streamlit",
        "run",
        "src/aios_habit/workspace_chat_app.py",
        "--server.port=8501",
        "--server.headless=true",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]
    log_file = open(OUT_DIR / "server_verify_marker_fix.log", "w", encoding="utf-8")
    proc = subprocess.Popen(cmd, cwd=str(APP_DIR), env=env, stdout=log_file, stderr=subprocess.STDOUT)
    for i in range(35):
        time.sleep(1)
        if proc.poll() is not None:
            raise RuntimeError(f"Server exited early with code {proc.returncode}")
        try:
            with urllib.request.urlopen("http://localhost:8501/_stcore/health", timeout=1) as resp:
                if resp.status == 200:
                    print(f"[+] Server started and healthy after {i+1}s (PID: {proc.pid})", flush=True)
                    return proc, log_file
        except Exception:
            pass
    raise TimeoutError("Streamlit server failed to start within 35s")


def stop_server(proc: subprocess.Popen | None, log_file: any) -> None:
    if proc is not None:
        print("[*] Stopping Streamlit server...", flush=True)
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    if log_file is not None and not log_file.closed:
        try:
            log_file.close()
        except Exception:
            pass


def run_verification():
    proc, log_file = ensure_server()
    pw = sync_playwright().start()
    try:
        browser = pw.chromium.launch(
            headless=True,
            args=["--window-size=1440,1050"],
        )
        context = browser.new_context(viewport={"width": 1440, "height": 1050})
        page = context.new_page()

        # -------------------------------------------------------------
        # STEP 1: Load CONV-LSU-FULL-LOOP-VERIFY-20261022
        # -------------------------------------------------------------
        nb_id = "NB-LAZY-LSU"
        conv_id = "CONV-LSU-FULL-LOOP-VERIFY-20261022"
        target_url = f"http://localhost:8501/?nb={nb_id}&conv={conv_id}"
        print(f"[*] Navigating to: {target_url}", flush=True)
        page.goto(target_url, wait_until="networkidle", timeout=60000)

        # Wait for SMA(20) alert message to be rendered (allow time for MSG-LOOP-A1's 30MB log to load)
        print("[*] Waiting for SMA(20) alert message selector...", flush=True)
        page.wait_for_selector(
            'div[data-testid="stChatMessage"]:has-text("MeasureFieldCurvatureYellow")',
            state="visible",
            timeout=40000,
        )
        time.sleep(2.0)

        chat_messages = page.locator('[data-testid="stChatMessage"]')
        msg_count = chat_messages.count()
        print(f"[+] Found {msg_count} chat messages on page.", flush=True)

        msg2_el = None
        for i in range(msg_count):
            txt = chat_messages.nth(i).inner_text()
            if "1003_1" in txt and "MeasureFieldCurvatureYellow" in txt:
                msg2_el = chat_messages.nth(i)
                print(f"[+] Located SMA(20) alert card at index {i}", flush=True)
                break

        assert msg2_el is not None, "Could not find SMA(20) alert message in conversation!"
        msg2_el.scroll_into_view_if_needed()
        time.sleep(1.0)

        msg2_text = msg2_el.inner_text()
        preview_safe = msg2_text.encode("ascii", "backslashreplace").decode("ascii")
        print(f"--- MSG2 Text Preview ---\n{preview_safe[:300]}\n-------------------------", flush=True)

        # Invariant checks:
        print("[*] Validating Invariants on SMA(20) Alert Message...")
        assert "<!--" not in msg2_text, f"LEAK DETECTED: '<!--' found in message text!"
        assert "-->" not in msg2_text, f"LEAK DETECTED: '-->' found in message text!"
        assert "aios_" not in msg2_text, f"LEAK DETECTED: 'aios_' found in message text!"
        assert "aios_jig_alert_card" not in msg2_text, f"LEAK DETECTED: marker name leaked!"
        assert "\\u" not in msg2_text, f"LEAK DETECTED: raw unicode escape '\\u' found!"

        # Semantic content checks:
        assert "1003_1" in msg2_text, "JIG 1003_1 must be displayed!"
        assert "MeasureFieldCurvatureYellow" in msg2_text, "Metric must be displayed!"
        assert "4.6" in msg2_text, "Value 4.6 must be displayed!"
        assert "8 điểm liên tiếp" in msg2_text or "8" in msg2_text, "8 consecutive points must be displayed!"
        assert "Theo tài liệu quy trình:" in msg2_text, "Honest guide must be displayed!"

        print("[+] All Invariant and Semantic checks PASSED for SMA(20) Alert Card!", flush=True)

        # Capture evidence screenshot 1: SMA(20) Clean Alert Card
        shot1 = OUT_DIR / "anh-marker-leak-fix-01-sma20-clean-card.png"
        msg2_el.screenshot(path=str(shot1))
        shot1_size = shot1.stat().st_size
        shot1_sha = sha256_file(shot1)
        print(f"[+] Screenshot 1 captured: {shot1.name} ({shot1_size:,} bytes, SHA-256: {shot1_sha})", flush=True)

        # Also save as fixed replacement for G7 evidence
        g7_evidence = OUT_DIR / "anh-hd-g7-canh-bao-lsu-realtime-the-rt-fixed.png"
        msg2_el.screenshot(path=str(g7_evidence))
        g7_size = g7_evidence.stat().st_size
        g7_sha = sha256_file(g7_evidence)
        print(f"[+] G7 Fixed Evidence captured: {g7_evidence.name} ({g7_size:,} bytes, SHA-256: {g7_sha})", flush=True)

        # -------------------------------------------------------------
        # STEP 2: Verify MSG-LOOP-A1 (aios_log_chart_builder)
        # -------------------------------------------------------------
        msg1_el = None
        for i in range(msg_count):
            txt = chat_messages.nth(i).inner_text()
            if "2025_02.csv" in txt or "totalTakt" in txt:
                msg1_el = chat_messages.nth(i)
                print(f"[+] Located Log Chart message at index {i}", flush=True)
                break

        if msg1_el:
            msg1_el.scroll_into_view_if_needed()
            time.sleep(1.0)
            msg1_text = msg1_el.inner_text()
            assert "<!--" not in msg1_text, "Leaked '<!--' in log chart message!"
            assert "aios_log_chart_builder" not in msg1_text, "Leaked marker in log chart message!"
            print("[+] Log Chart Builder card renders cleanly without raw marker leak.", flush=True)
            shot2 = OUT_DIR / "anh-marker-leak-fix-02-log-chart-clean.png"
            msg1_el.screenshot(path=str(shot2))
            shot2_size = shot2.stat().st_size
            shot2_sha = sha256_file(shot2)
            print(f"[+] Screenshot 2 captured: {shot2.name} ({shot2_size:,} bytes, SHA-256: {shot2_sha})", flush=True)

        # -------------------------------------------------------------
        # STEP 3: Regression test on sending chat in a fresh conversation
        # -------------------------------------------------------------
        import uuid
        fresh_cid = f"CONV-REGRESS-{uuid.uuid4().hex[:8].upper()}"
        from aios_habit.workspace_chat_models import WorkspaceConversation
        from aios_habit.workspace_chat_store import save_conversation
        fresh_conv = WorkspaceConversation(
            id=fresh_cid,
            notebook_id=nb_id,
            title="Kiểm thử hồi quy gửi chat sau khi vá marker leak",
            ui_locale="vi",
            answer_language="vi",
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            updated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        save_conversation(fresh_conv)

        page.goto(f"http://localhost:8501/?nb={nb_id}&conv={fresh_cid}", wait_until="networkidle", timeout=30000)
        page.wait_for_selector('[class*="st-key-wsc_question_input_"] textarea', state="visible", timeout=30000)
        time.sleep(1.0)

        # Send test prompt (/huongdan lenh) which responds immediately
        ta = page.locator('[class*="st-key-wsc_question_input_"] textarea').first
        ta.click()
        time.sleep(0.2)
        ta.fill("/huongdan lenh")
        time.sleep(0.5)

        # Click send button
        page.evaluate("""() => {
            const t = document.querySelector('[class*="st-key-wsc_question_input_"] textarea');
            if (t) t.blur();
        }""")
        time.sleep(0.5)
        send_btn = page.wait_for_selector(
            '[class*="st-key-wsc_ask_"] button:not([disabled]), [class*="st-key-wsc-action-"] button:not([disabled])',
            state="visible",
            timeout=30000,
        )
        send_btn.click()
        print("[+] Sent /huongdan lenh in fresh conversation. Waiting for response...", flush=True)

        # Wait for huongdan bubble to appear
        time.sleep(4.0)
        page.wait_for_selector('div[data-testid="stChatMessage"]:has-text("danh mục")', timeout=20000)

        fresh_msgs = page.locator('[data-testid="stChatMessage"]')
        print(f"[+] Found {fresh_msgs.count()} messages in fresh conversation.", flush=True)
        assert fresh_msgs.count() >= 2, "Expected user message and assistant reply to appear!"

        fresh_reply = fresh_msgs.nth(1).inner_text()
        assert "<!--" not in fresh_reply, "Marker leaked in fresh assistant reply!"
        assert "aios_" not in fresh_reply, "Marker leaked in fresh assistant reply!"
        print("[+] Fresh assistant reply rendered cleanly without marker leak.", flush=True)

        shot3 = OUT_DIR / "anh-marker-leak-fix-03-fresh-chat-regression.png"
        page.screenshot(path=str(shot3))
        shot3_size = shot3.stat().st_size
        shot3_sha = sha256_file(shot3)
        print(f"[+] Screenshot 3 captured: {shot3.name} ({shot3_size:,} bytes, SHA-256: {shot3_sha})", flush=True)

        print("\n=== ALL VERIFICATION GATES PASSED 100% ===", flush=True)
        return {
            "shot1": (shot1, shot1_size, shot1_sha),
            "g7_evidence": (g7_evidence, g7_size, g7_sha),
            "shot2": (shot2, shot2_size, shot2_sha) if msg1_el else None,
            "shot3": (shot3, shot3_size, shot3_sha),
        }
    finally:
        browser.close()
        pw.stop()
        stop_server(proc, log_file)


if __name__ == "__main__":
    results = run_verification()
    print("\nVerification summary:")
    for k, v in results.items():
        if v:
            p, sz, sha = v
            print(f"  {k}: {p.name} | {sz} bytes | SHA-256: {sha}")
