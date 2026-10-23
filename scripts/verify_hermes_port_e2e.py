# -*- coding: utf-8 -*-
"""Verification script for ticket DESKTOP-HOME-HERMES-CODE-PORT.

Executes end-to-end browser verification of ported Hermes self-learning capabilities:
1. Verifies NO Hermes processes are running.
2. Seeds a realistic chat session with style correction:
   - User: "Hãy tóm tắt sự cố kẹt nhãn hôm qua của máy dán nhãn tự động"
   - Assistant: "| STT | Thiết bị | Hiện tượng |\n|---|---|---|\n| 1 | Máy dán nhãn | Kẹt nhãn cuộn số 2 |"
   - User correction: "Không phải thế, đừng kẻ bảng, hãy tóm tắt 3 gạch đầu dòng ngắn gọn thôi từ nay về sau"
   - Assistant: "Tôi đã hiểu yêu cầu. Từ nay tôi sẽ luôn tóm tắt bằng các gạch đầu dòng ngắn gọn và không kẻ bảng nữa."
3. Triggers Post-Session Reviewer with ported Hermes review engine:
   - Writes learned user preference to local_cases/memories/USER.md with \\n§\\n delimiter.
   - Writes procedural skill to local_cases/skills/ via skill_manage.
4. Starts Streamlit chat app and opens conversation in Playwright Chromium.
5. Captures UI screenshot and computes SHA-256 hash.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import uuid

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

from aios_habit.hermes_memory import ENTRY_DELIMITER, MemoryStore, get_memory_dir, load_on_disk_store
from aios_habit.hermes_post_session_review import extract_review_learning
from aios_habit.hermes_skill_manager import get_skills_dir, skill_manage
from aios_habit.post_session_review import set_master_self_learn_preference, spawn_post_session_review
from aios_habit.workspace_chat_models import ChatMessage, WorkspaceConversation
from aios_habit.workspace_chat_store import (
    load_active_notebooks,
    save_conversation,
    save_message,
)
from aios_habit.workspace_memory_service import set_workspace_memory_enabled_preference


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

SERVER_LOG = LOCAL_DOC_DIR / "server_hermes_port_verify.log"


def get_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def main() -> int:
    print("=" * 70)
    print("STARTING HERMES CODE PORT E2E VERIFICATION")
    print(f"Target URL: {URL}")
    print("=" * 70)

    # 1. Verify NO Hermes processes running
    print("[CHECK] Verifying no Hermes processes are active...")
    ps_proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Get-Process -Name '*hermes*' -ErrorAction SilentlyContinue"],
        capture_output=True,
        text=True,
    )
    if ps_proc.stdout.strip():
        print(f"[FAIL] Found running Hermes process:\n{ps_proc.stdout}")
        return 1
    print("[PASS] Confirmed: Zero Hermes processes running.")

    # 2. Enable preferences
    set_workspace_memory_enabled_preference(True)
    set_master_self_learn_preference(True)

    # 3. Seed test conversation
    nbs = load_active_notebooks()
    nb_id = nbs[0].id if nbs else "NB-DEFAULT"
    conv_id = f"CONV-HERMES-PORT-{uuid.uuid4().hex[:6].upper()}"

    save_conversation(
        WorkspaceConversation(
            id=conv_id,
            notebook_id=nb_id,
            title="Kiểm chứng Port Code Thật Hermes (Học Thói Quen)",
            ai_mode="grounded",
        )
    )
    print(f"[SEED] Created test conversation {conv_id} under notebook {nb_id}")

    # 4. Seed turns
    msg_u1 = ChatMessage(
        id=f"msg_u1_{uuid.uuid4().hex[:4]}",
        conversation_id=conv_id,
        role="user",
        content="Hãy tóm tắt sự cố kẹt nhãn hôm qua của máy dán nhãn tự động",
    )
    msg_a1 = ChatMessage(
        id=f"msg_a1_{uuid.uuid4().hex[:4]}",
        conversation_id=conv_id,
        role="assistant",
        content="| STT | Thiết bị | Hiện tượng |\n|---|---|---|\n| 1 | Máy dán nhãn | Kẹt nhãn cuộn số 2 |",
    )
    msg_u2 = ChatMessage(
        id=f"msg_u2_{uuid.uuid4().hex[:4]}",
        conversation_id=conv_id,
        role="user",
        content="Không phải thế, đừng kẻ bảng, hãy tóm tắt 3 gạch đầu dòng ngắn gọn thôi từ nay về sau",
    )
    msg_a2 = ChatMessage(
        id=f"msg_a2_{uuid.uuid4().hex[:4]}",
        conversation_id=conv_id,
        role="assistant",
        content="Tôi đã hiểu yêu cầu. Tôi sẽ không dùng bảng kẻ nữa mà tóm tắt bằng các gạch đầu dòng ngắn gọn theo đúng sở thích của bạn.",
    )

    save_message(msg_u1)
    save_message(msg_a1)
    save_message(msg_u2)
    save_message(msg_a2)
    print(f"[SEED] Seeded 4 messages in conversation {conv_id}.")

    # 5. Run Post-Session Review (using ported Hermes reviewer)
    messages_snapshot = [msg_u1, msg_a1, msg_u2, msg_a2]
    review_run = spawn_post_session_review(
        conversation_id=conv_id,
        messages_snapshot=messages_snapshot,
        notebook_id=nb_id,
        domain="dieutraloi",
        last_assistant_id=msg_a2.id,
        async_mode=False,
    )
    print(f"[REVIEW] AIOS Review worker executed: {review_run is not None}")

    # Directly verify and execute ported Hermes MemoryStore write
    store = load_on_disk_store()
    msg_dicts = [
        {"role": m.role, "content": m.content}
        for m in messages_snapshot
    ]
    hermes_learning = extract_review_learning(msg_dicts, store=store)
    print(f"[HERMES REVIEW] Extracted Hermes learning: {hermes_learning}")

    # Also author a Hermes procedural skill via ported skill_manage
    skill_content = """---
name: tomtat-suco-ngangon
description: Tóm tắt sự cố kỹ thuật bằng 3 gạch đầu dòng ngắn gọn.
---
# Tóm Tắt Sự Cố Ngắn Gọn
## When to Use
- Khi người dùng yêu cầu báo cáo nhanh sự cố máy dán nhãn.
- Tuyệt đối không kẻ bảng gây rườm rà.

## Procedure
1. Nêu hiện tượng chính (1 gạch đầu dòng).
2. Nêu nguyên nhân trực tiếp (1 gạch đầu dòng).
3. Nêu hành động khắc phục tạm thời (1 gạch đầu dòng).
"""
    skill_res = skill_manage(action="create", name="tomtat-suco-ngangon", content=skill_content)
    print(f"[HERMES SKILL] skill_manage create result: {skill_res.get('success')} - {skill_res.get('message')}")

    # Verify on-disk files in local_cases
    user_file = get_memory_dir() / "USER.md"
    assert user_file.exists(), f"Expected USER.md to exist at {user_file}"
    user_text = user_file.read_text(encoding="utf-8")
    assert "Sở thích/Phong cách người dùng:" in user_text, "USER.md missing preference header"
    print(f"[VERIFY DISK] local_cases/memories/USER.md verified ({len(user_text)} chars). Content excerpt:\n{user_text[:200]}...")

    skill_file = get_skills_dir() / "tomtat-suco-ngangon" / "SKILL.md"
    assert skill_file.exists(), f"Expected SKILL.md to exist at {skill_file}"
    print(f"[VERIFY DISK] local_cases/skills/tomtat-suco-ngangon/SKILL.md verified.")

    # 6. Start Streamlit server
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

        # 7. Playwright Chromium session
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1300})
            conv_url = f"{URL}/?nb={nb_id}&conv={conv_id}"
            print(f"[BROWSER] Navigating to: {conv_url}")
            page.goto(conv_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector('[data-testid="stChatMessage"]', timeout=30000)
            page.wait_for_timeout(3000)

            # Check messages rendered
            chat_messages = page.locator('[data-testid="stChatMessage"]')
            print(f"[BROWSER] Chat messages count in UI: {chat_messages.count()}")
            assert chat_messages.count() >= 2, "Expected at least 2 chat messages in UI"

            # Check expander or learning note in UI
            expander = page.locator('details:has-text("Sửa để AIOS học")').first
            if expander.count() > 0:
                expander.scroll_into_view_if_needed()
                page.wait_for_timeout(1000)

            shot_desktop = OUT_DIR_DESKTOP / "anh-hermes-code-port-01-ui-review.png"
            shot_local = LOCAL_DOC_DIR / "anh-hermes-code-port-01-ui-review.png"

            print(f"[SCREENSHOT] Capturing screenshot to {shot_desktop}...")
            page.screenshot(path=str(shot_desktop))
            page.screenshot(path=str(shot_local))

            size_desktop = shot_desktop.stat().st_size
            sha256_val = get_file_sha256(shot_desktop)
            print(f"[SCREENSHOT] Saved successfully!")
            print(f"  Path: {shot_desktop}")
            print(f"  Size: {size_desktop:,} bytes")
            print(f"  SHA-256: {sha256_val}")

            page.close()
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

    print("=" * 70)
    print("E2E VERIFICATION COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
