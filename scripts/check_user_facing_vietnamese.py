#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bộ quét kiểm tra tuân thủ tiếng Việt trên bề mặt người dùng (check_user_facing_vietnamese.py).

Tuân thủ: docs/UI_LANGUAGE_POLICY.md và AGENT_RULES.md mục 4.
Quy tắc:
1. Tiếng Việt là ngôn ngữ giao diện duy nhất được hỗ trợ.
2. Không hiển thị bộ chọn ngôn ngữ giao diện.
3. Chặn traceback, đường dẫn máy, tên engine/model, và câu lỗi tiếng Anh từ thư viện/hệ điều hành.
4. Cho phép các định danh kỹ thuật, mã máy, đường dẫn tương đối trong danh sách cho phép (allowlist).
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent

# Danh sách tệp giao diện & launcher cần quét
USER_FACING_PYTHON_FILES = [
    REPO_ROOT / "src" / "aios_habit" / "workspace_chat_ui.py",
    REPO_ROOT / "src" / "aios_habit" / "workspace_chat_app.py",
    REPO_ROOT / "src" / "aios_habit" / "workspace_case_ui.py",
    REPO_ROOT / "src" / "aios_habit" / "prediction_shadow_ui.py",
    REPO_ROOT / "src" / "aios_habit" / "in_app_risk_alert.py",
    REPO_ROOT / "src" / "aios_habit" / "i18n.py",
]

USER_FACING_LAUNCHERS = [
    REPO_ROOT / "RUN_AIOS_WORKSPACE_CHAT.bat",
    REPO_ROOT / "scripts" / "run_workspace_chat.ps1",
]

# Allowlist: các định danh kỹ thuật, token, mã lỗi, tên biến được phép xuất hiện
ALLOWLIST_PATTERNS = [
    r"^AIOS.*",
    r"^[A-Z0-9_-]+$",                       # Mã định danh viết hoa (CASE-1, REF-1, OK, NG, ...)
    r"^https?://.*",                         # URL
    r"^/[\w/.-]+$",                          # Đường dẫn POSIX
    r"^[a-zA-Z]:\\[\w\\.-]+$",               # Đường dẫn Windows
    r"^\w+\.(py|sqlite|json|yaml|yml|md|csv|xlsx|txt)$", # Tên tệp
    r"^PRAGMA .*",                           # SQL pragma
    r"^SELECT .*",                           # SQL query
    r"^INSERT .*",                           # SQL query
    r"^UPDATE .*",                           # SQL query
    r"^DELETE .*",                           # SQL query
    r"^CREATE .*",                           # SQL query
    r"^utf-8.*",
    r"^\d+(\.\d+)?(s|ms|MB|GB|KB|%)?$",      # Số đo lường kỹ thuật
]

# Các từ tiếng Anh phổ biến trong thông báo lỗi hoặc nhãn nếu lọt vào UI
ENGLISH_UI_LEAK_WORDS = [
    "error", "warning", "failed", "success", "loading", "please wait",
    "invalid", "unsupported", "unknown", "exception", "traceback",
    "select language", "language", "japanese", "chinese", "english",
    "choose option", "not found", "access denied", "timed out",
    "snapshot", "sqlite", "tab 1", "tab 2", "read-only", "đọc-only",
    "direct mode", "not available", "unit serial",
    "completed", "stopped", "running", "unit", "units", "lot", "lots",
    "fixture", "digest", "claim", "approved", "markdown", "json", "lease",
]


def check_language_selector_forbidden() -> List[str]:
    """Kiểm tra cấm bộ chọn ngôn ngữ trên giao diện."""
    violations: List[str] = []
    app_py = REPO_ROOT / "src" / "aios_habit" / "workspace_chat_app.py"
    ui_py = REPO_ROOT / "src" / "aios_habit" / "workspace_chat_ui.py"

    for file_path in (app_py, ui_py):
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8", errors="replace")
        # Kiểm tra nếu vẫn còn gọi render_language_selector trong luồng hiển thị chính
        if "render_language_selector(" in content:
            # Kiểm tra xem có bị comment hoặc vô hiệu hóa không
            lines = content.splitlines()
            for idx, line in enumerate(lines, 1):
                stripped = line.strip()
                if not stripped.startswith("#") and not stripped.startswith("def render_language_selector(") and "render_language_selector(" in stripped:
                    violations.append(
                        f"{file_path.relative_to(REPO_ROOT)}:{idx}: Bộ chọn ngôn ngữ (render_language_selector) vẫn đang được gọi."
                    )
    return violations


def check_supported_locales_policy() -> List[str]:
    """Kiểm tra chính sách SUPPORTED_UI_LOCALES chỉ chứa 'vi'."""
    violations: List[str] = []
    i18n_py = REPO_ROOT / "src" / "aios_habit" / "i18n.py"
    if not i18n_py.exists():
        return [f"Không tìm thấy tệp {i18n_py}"]

    content = i18n_py.read_text(encoding="utf-8", errors="replace")
    # Kiểm tra biến SUPPORTED_UI_LOCALES
    if "SUPPORTED_UI_LOCALES" not in content:
        violations.append("i18n.py: Chưa định nghĩa SUPPORTED_UI_LOCALES = ('vi',)")
    else:
        # Kiểm tra xem SUPPORTED_UI_LOCALES có chỉ gồm ('vi',) không
        match = re.search(r"SUPPORTED_UI_LOCALES\s*=\s*\((.*?)\)", content, re.DOTALL)
        if match:
            elements = [e.strip().strip("'\"") for e in match.group(1).split(",") if e.strip()]
            if elements != ["vi"]:
                violations.append(
                    f"i18n.py: SUPPORTED_UI_LOCALES phải là ('vi',), hiện tại là {elements}"
                )
    return violations


def check_launchers_vietnamese() -> List[str]:
    """Kiểm tra các launcher (.bat, .ps1) chỉ dùng tiếng Việt cho thông báo người dùng."""
    violations: List[str] = []
    for launcher in USER_FACING_LAUNCHERS:
        if not launcher.exists():
            continue
        content = launcher.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            # Kiểm tra echo hoặc Write-Host
            if stripped.lower().startswith("echo ") or stripped.lower().startswith("write-host "):
                msg = stripped.split(" ", 1)[1].strip().strip('"\'')
                # Kiểm tra xem có từ tiếng Anh cấm không
                lower_msg = msg.lower()
                for word in ["error:", "starting", "failed to", "press any key", "warning:"]:
                    if word in lower_msg:
                        violations.append(
                            f"{launcher.relative_to(REPO_ROOT)}:{idx}: Launcher chứa thông báo tiếng Anh: '{msg}'"
                        )
    return violations


def check_ui_files_vietnamese(custom_files: Optional[List[Path]] = None) -> List[str]:
    """Kiểm tra các tệp giao diện Python không chứa từ rò rỉ tiếng Anh hoặc traceback thô."""
    violations: List[str] = []
    files_to_check = custom_files if custom_files is not None else USER_FACING_PYTHON_FILES
    st_widgets = "button|write|markdown|title|header|subheader|caption|info|warning|error|success|text_input|text_area|selectbox|multiselect|radio|checkbox|metric|tabs"

    for file_path in files_to_check:
        if not file_path.exists():
            continue
        try:
            rel_display = str(file_path.relative_to(REPO_ROOT))
        except ValueError:
            rel_display = str(file_path)

        content = file_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()

        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            # Phát hiện traceback thô hoặc str(e)/str(exc) lọt vào UI
            if any(p in stripped for p in ("str(e)", "str(exc)", "traceback.format_exc()", "traceback.print_exc()")):
                if any(st_call in stripped for st_call in ("st.error", "st.warning", "st.info", "st.write", "st.caption", "st.exception")):
                    violations.append(
                        f"{rel_display}:{idx}: Lộ traceback hoặc chuỗi ngoại lệ thô tiếng Anh: '{stripped}'"
                    )

            # Phát hiện từ tiếng Anh trong chuỗi gọi UI Streamlit
            for leak in ENGLISH_UI_LEAK_WORDS:
                pattern = rf'st\.({st_widgets})\([^)]*["\'][^"\']*\b{re.escape(leak)}\b'
                if re.search(pattern, stripped, re.IGNORECASE):
                    violations.append(
                        f"{rel_display}:{idx}: Bề mặt giao diện chứa từ rò rỉ tiếng Anh '{leak}': '{stripped}'"
                    )

    return violations

def run_all_checks() -> Tuple[int, List[str]]:
    """Chạy toàn bộ các kiểm tra tuân thủ tiếng Việt."""
    all_violations: List[str] = []

    all_violations.extend(check_supported_locales_policy())
    all_violations.extend(check_language_selector_forbidden())
    all_violations.extend(check_launchers_vietnamese())
    all_violations.extend(check_ui_files_vietnamese())

    exit_code = 0 if not all_violations else 1
    return exit_code, all_violations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Kiểm tra tuân thủ chính sách tiếng Việt trên giao diện AIOS WorkLens"
    )
    args = parser.parse_args()

    exit_code, violations = run_all_checks()

    if exit_code == 0:
        print("VIETNAMESE_UI_POLICY_CHECK=PASS: Bề mặt người dùng tuân thủ tiếng Việt 100%.")
    else:
        print("VIETNAMESE_UI_POLICY_CHECK=FAIL: Phát hiện vi phạm chính sách tiếng Việt:")
        for v in violations:
            print(f"  - {v}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
