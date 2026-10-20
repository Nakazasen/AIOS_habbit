# -*- coding: utf-8 -*-
"""Browser verification for ticket DESKTOP-HOME-DRAFT-STORE-SCOPE-FIX.

Automated verification with real Playwright Chromium:
1. Notebook 1: MOM / Opcenter (mom_opcenter):
   - Asks MOM-specific draft question: "Trong file cấu hình Matecon, ctrlMode = 0 và ctrlMode = 1 khác nhau thế nào?"
   - Confirms draft is SERVED with mandatory label "[Bản thảo - chưa kiểm chứng qua chuyên gia]".
   - Captures screenshot: ui-draft-scope-01-mom-served.png.
2. Notebook 2: Điều tra lỗi LSU (NB-LAZY-LSU):
   - Asks the EXACT SAME question: "Trong file cấu hình Matecon, ctrlMode = 0 và ctrlMode = 1 khác nhau thế nào?"
   - Confirms draft from MOM is BLOCKED. App delivers honest response without draft label.
   - Captures screenshot: ui-draft-scope-02-lsu-honest.png.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

# Ensure UTF-8 output on Windows console
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from playwright.sync_api import sync_playwright

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR / "src"))

from aios_habit.draft_source_layer import MANDATORY_DRAFT_LABEL
from aios_habit.final_answer_composer import deliver_5tier_ladder_answer
from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import load_active_notebooks, save_conversation

def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

PORT = find_free_port()
URL = f"http://localhost:{PORT}"

OUT_DIR_DESKTOP = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua")
OUT_DIR_DESKTOP.mkdir(parents=True, exist_ok=True)

LOCAL_DOC_DIR = APP_DIR / "docs" / "phieu-viec" / "ket-qua"
LOCAL_DOC_DIR.mkdir(parents=True, exist_ok=True)

ARTIFACT_DIR = Path(r"C:\Users\Admin\.gemini\antigravity\brain\18b369ac-30b4-4b69-a67d-f9977869aa97")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

SERVER_LOG = LOCAL_DOC_DIR / "server_draft_scope_verify.log"
if SERVER_LOG.exists():
    try:
        SERVER_LOG.unlink()
    except Exception:
        pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    print("=" * 70)
    print("STARTING DRAFT STORE SCOPE BROWSER VERIFICATION (MOM vs LSU)")
    print("=" * 70)

    # Question matching only MOM draft store
    question = "Trong file cấu hình Matecon, ctrlMode = 0 và ctrlMode = 1 khác nhau thế nào?"

    # 1. Seed Conversation in Notebook 1: MOM (mom_opcenter)
    conv_id_mom = f"CONV-SCOPE-MOM-{uuid.uuid4().hex[:6].upper()}"
    save_conversation(
        WorkspaceConversation(
            id=conv_id_mom,
            notebook_id="mom_opcenter",
            title="Kiểm tra khóa sổ - Sổ MOM",
            ai_mode="grounded",
        )
    )
    print(f"[SEED 1] Asking in MOM notebook (mom_opcenter)...")
    ok1, msg1, badge1, err1 = deliver_5tier_ladder_answer(
        question=question,
        conversation_id=conv_id_mom,
        notebook_id="mom_opcenter",
        user_raw_input=question,
    )
    assert ok1 is True, f"Failed turn 1: {err1}"
    assert badge1 is not None
    assert badge1.get("has_draft_label") is True, "MOM turn must have has_draft_label=True"
    assert "mom" in badge1.get("draft_source", "").replace("\\", "/").lower(), "MOM turn must use MOM draft"
    print(f"[SEED 1] MOM served draft successfully: {badge1.get('draft_source')}")

    # 2. Seed Conversation in Notebook 2: LSU (NB-LAZY-LSU)
    conv_id_lsu = f"CONV-SCOPE-LSU-{uuid.uuid4().hex[:6].upper()}"
    save_conversation(
        WorkspaceConversation(
            id=conv_id_lsu,
            notebook_id="NB-LAZY-LSU",
            title="Kiểm tra khóa sổ - Sổ LSU",
            ai_mode="grounded",
        )
    )
    print(f"[SEED 2] Asking SAME question in LSU notebook (NB-LAZY-LSU)...")
    ok2, msg2, badge2, err2 = deliver_5tier_ladder_answer(
        question=question,
        conversation_id=conv_id_lsu,
        notebook_id="NB-LAZY-LSU",
        user_raw_input=question,
    )
    assert ok2 is True, f"Failed turn 2: {err2}"
    assert badge2 is not None
    assert badge2.get("has_draft_label") is not True, "LSU turn MUST NOT have draft label for MOM question"
    assert badge2.get("draft_source") == "", "LSU turn MUST NOT have draft source for MOM question"
    print(f"[SEED 2] LSU correctly fell back to honest Tier 4 answer without borrowing MOM draft!")

    # 3. Start Streamlit server
    env = os.environ.copy()
    env["PYTHONPATH"] = str(APP_DIR / "src")
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    env["AIOS_RETRIEVAL_DEVICE"] = "cpu"
    env["AIOS_RAG_V2_NUMPY_DENSE"] = "1"
    env["AIOS_RAG_V2_NUMPY_SCORING"] = "1"
    env["AIOS_AI_BACKEND"] = "local"
    env["AIOS_FEATURE_CHAT_ACTION"] = "1"
    env["AIOS_DOMAIN_ROUTING_ENABLED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"

    print(f"[SERVER] Starting Streamlit on port {PORT}...")
    log_h = open(SERVER_LOG, "a", encoding="utf-8")
    cmd = [
        str(APP_DIR / ".venv" / "Scripts" / "python.exe"),
        "-u",
        "-m",
        "streamlit",
        "run",
        "src/aios_habit/workspace_chat_app.py",
        f"--server.port={PORT}",
        "--server.headless=true",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]
    proc = subprocess.Popen(cmd, cwd=APP_DIR, env=env, stdout=log_h, stderr=subprocess.STDOUT)

    results_info = {}

    try:
        deadline = time.time() + 60
        server_ready = False
        while time.time() < deadline:
            try:
                req = urllib.request.Request(f"http://localhost:{PORT}/_stcore/health")
                with urllib.request.urlopen(req, timeout=2) as r:
                    if r.status == 200:
                        server_ready = True
                        break
            except Exception:
                pass
            time.sleep(1)

        if not server_ready:
            print("[ERROR] Streamlit server did not become healthy within 60s.")
            return 1

        print(f"[SERVER] Server is UP at {URL}")
        time.sleep(2)

        # 4. Launch Playwright Chromium
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # --- SCREENSHOT 1: MOM Notebook (Draft Served) ---
            page1 = browser.new_page(viewport={"width": 1440, "height": 960})
            url_mom = f"{URL}/?nb=mom_opcenter&conv={conv_id_mom}"
            print(f"[BROWSER 1] Navigating to MOM conversation: {url_mom}")
            page1.goto(url_mom, wait_until="domcontentloaded", timeout=60000)
            page1.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)
            page1.wait_for_timeout(3000)

            # Check mandatory label is present
            label_locator = page1.locator(f':has-text("{MANDATORY_DRAFT_LABEL}")')
            assert label_locator.count() >= 1, "Missing mandatory draft label in MOM UI"
            print("[BROWSER 1] Confirmed mandatory draft label is VISIBLE in MOM notebook.")

            shot1_desktop = OUT_DIR_DESKTOP / "ui-draft-scope-01-mom-served.png"
            shot1_local = LOCAL_DOC_DIR / "ui-draft-scope-01-mom-served.png"
            shot1_artifact = ARTIFACT_DIR / "ui-draft-scope-01-mom-served.png"

            page1.screenshot(path=str(shot1_desktop), full_page=True)
            page1.screenshot(path=str(shot1_local), full_page=True)
            page1.screenshot(path=str(shot1_artifact), full_page=True)

            sha1 = sha256_file(shot1_desktop)
            results_info["shot1"] = {
                "file": "ui-draft-scope-01-mom-served.png",
                "sha256": sha1,
                "size": shot1_desktop.stat().st_size,
                "notebook": "mom_opcenter (MOM / Opcenter)",
                "status": "PHUC_VU_BAN_THAO_CO_NHAN",
            }
            print(f"[SCREENSHOT 1] Saved: {shot1_desktop} (SHA-256: {sha1})")
            page1.close()

            # --- SCREENSHOT 2: LSU Notebook (Honest Refusal - No MOM Draft) ---
            page2 = browser.new_page(viewport={"width": 1440, "height": 960})
            url_lsu = f"{URL}/?nb=NB-LAZY-LSU&conv={conv_id_lsu}"
            print(f"[BROWSER 2] Navigating to LSU conversation: {url_lsu}")
            page2.goto(url_lsu, wait_until="domcontentloaded", timeout=60000)
            page2.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)
            page2.wait_for_timeout(3000)

            # Check mandatory label is ABSENT in LSU UI
            lsu_label_count = page2.locator(f':has-text("{MANDATORY_DRAFT_LABEL}")').count()
            assert lsu_label_count == 0, "LỖI: Nhãn bản thảo MOM xuất hiện trong sổ LSU!"

            # Check honest refusal message
            refusal_locator = page2.locator(':has-text("chưa tìm thấy dữ liệu đối chiếu trực tiếp")')
            assert refusal_locator.count() >= 1, "Missing honest refusal message in LSU UI"
            print("[BROWSER 2] Confirmed MOM draft is BLOCKED and honest response is VISIBLE in LSU notebook.")

            shot2_desktop = OUT_DIR_DESKTOP / "ui-draft-scope-02-lsu-honest.png"
            shot2_local = LOCAL_DOC_DIR / "ui-draft-scope-02-lsu-honest.png"
            shot2_artifact = ARTIFACT_DIR / "ui-draft-scope-02-lsu-honest.png"

            page2.screenshot(path=str(shot2_desktop), full_page=True)
            page2.screenshot(path=str(shot2_local), full_page=True)
            page2.screenshot(path=str(shot2_artifact), full_page=True)

            sha2 = sha256_file(shot2_desktop)
            results_info["shot2"] = {
                "file": "ui-draft-scope-02-lsu-honest.png",
                "sha256": sha2,
                "size": shot2_desktop.stat().st_size,
                "notebook": "NB-LAZY-LSU (Điều tra lỗi LSU)",
                "status": "TRUNG_THUC_TU_CHOI_KHONG_MUON_BAN_THAO_SO_KHAC",
            }
            print(f"[SCREENSHOT 2] Saved: {shot2_desktop} (SHA-256: {sha2})")
            page2.close()

            browser.close()

    finally:
        print("[CLEANUP] Stopping Streamlit server...")
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        try:
            log_h.close()
        except Exception:
            pass
        print("[CLEANUP] Streamlit server stopped.")

    summary_file = LOCAL_DOC_DIR / "scope_verification_summary.json"
    summary_file.write_text(json.dumps(results_info, indent=2, ensure_ascii=False), encoding="utf-8")
    print("=" * 70)
    print("BROWSER VERIFICATION COMPLETED WITH 100% SUCCESS!")
    print(json.dumps(results_info, indent=2, ensure_ascii=False))
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
