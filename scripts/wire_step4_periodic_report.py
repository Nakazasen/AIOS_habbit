# -*- coding: utf-8 -*-
"""Wire step4 periodic report into chat_action.py, chat_intent_router.py, and workspace_chat_app.py."""

from pathlib import Path

APP_DIR = Path(r"D:\Sandbox\AIOS_habbit")

# 1. Update chat_action.py
chat_action_file = APP_DIR / "src" / "aios_habit" / "chat_action.py"
ca_text = chat_action_file.read_text(encoding="utf-8")

if "chat_action_periodic_report" not in ca_text:
    target_module = '"aios_habit.chat_action_log_stream",'
    replacement_module = (
        '"aios_habit.chat_action_log_stream",\n'
        '    # DESKTOP-HOME-STEP4-PERIODIC-REPORT-ACCEPTANCE: bao cao xu huong dinh ky theo tuan\n'
        '    "aios_habit.chat_action_periodic_report",'
    )
    ca_text = ca_text.replace(target_module, replacement_module, 1)

target_re = "# Case form (Step 0)"
if "Periodic trend report (Step 4)" not in ca_text and target_re in ca_text:
    replacement_re = (
        "# Periodic trend report (Step 4)\n"
        '    r"^(?:bao\\s+cao\\s+xu\\s+huong|sinh\\s+bao\\s+cao\\s+xu\\s+huong|bao\\s+cao\\s+dinh\\s+ky|xuat\\s+bao\\s+cao\\s+xu\\s+huong|sinh\\s+bao\\s+cao\\s+dinh\\s+ky)\\b|" \\\n'
        '    # Case form (Step 0)'
    )
    ca_text = ca_text.replace(target_re, replacement_re, 1)

chat_action_file.write_text(ca_text, encoding="utf-8")
print("1. chat_action.py updated successfully.")

# 2. Update chat_intent_router.py
router_file = APP_DIR / "src" / "aios_habit" / "chat_intent_router.py"
router_text = router_file.read_text(encoding="utf-8")

if "BAO_CAO_XU_HUONG" not in router_text:
    # Add constant
    target_const = 'XU_HUONG_LOG_TINH = "xu_huong_log_tinh"'
    replacement_const = (
        'BAO_CAO_XU_HUONG = "bao_cao_xu_huong"    # periodic trend report (Step 4)\n'
        'XU_HUONG_LOG_TINH = "xu_huong_log_tinh"'
    )
    router_text = router_text.replace(target_const, replacement_const, 1)

    # Add to TAT_CA_Y_DINH
    target_all = "    XU_HUONG_LOG_TINH,\n"
    replacement_all = "    BAO_CAO_XU_HUONG,\n    XU_HUONG_LOG_TINH,\n"
    router_text = router_text.replace(target_all, replacement_all, 1)

    # Add to _QUY_TAC
    target_rule = "    (\n        XU_HUONG_LOG_TINH,"
    replacement_rule = (
        '    (\n'
        '        BAO_CAO_XU_HUONG,\n'
        '        (\n'
        '            "bao cao xu huong dinh ky",\n'
        '            "báo cáo xu hướng định kỳ",\n'
        '            "sinh bao cao xu huong dinh ky",\n'
        '            "sinh báo cáo xu hướng định kỳ",\n'
        '            "xuat bao cao xu huong dinh ky",\n'
        '            "xuất báo cáo xu hướng định kỳ",\n'
        '            "bao cao xu huong tuan",\n'
        '            "báo cáo xu hướng tuần",\n'
        '            "bao cao dinh ky tuan",\n'
        '            "báo cáo định kỳ tuần",\n'
        '            "sinh bao cao xu huong",\n'
        '            "sinh báo cáo xu hướng",\n'
        '            "xuat bao cao xu huong",\n'
        '            "xuất báo cáo xu hướng",\n'
        '            "bao cao xu huong",\n'
        '            "báo cáo xu hướng",\n'
        '            "bao cao dinh ky",\n'
        '            "báo cáo định kỳ",\n'
        '            "/baocaoxuhuong",\n'
        '            "/baocaodinhky",\n'
        '        ),\n'
        '    ),\n'
        '    (\n'
        '        XU_HUONG_LOG_TINH,'
    )
    router_text = router_text.replace(target_rule, replacement_rule, 1)
    router_file.write_text(router_text, encoding="utf-8")
    print("2. chat_intent_router.py updated successfully.")
else:
    print("2. chat_intent_router.py already contains BAO_CAO_XU_HUONG.")

# 3. Update workspace_chat_app.py
app_file = APP_DIR / "src" / "aios_habit" / "workspace_chat_app.py"
app_text = app_file.read_text(encoding="utf-8")

if "BAO_CAO_XU_HUONG" not in app_text:
    # Add import in _xu_ly_y_dinh_chat
    target_import = "        XU_HUONG_LOG_TINH,\n"
    replacement_import = "        BAO_CAO_XU_HUONG,\n        XU_HUONG_LOG_TINH,\n"
    app_text = app_text.replace(target_import, replacement_import, 1)

    # Add handler branch in _xu_ly_mot_y_dinh
    target_branch = "    if y_dinh == XU_HUONG_LOG_TINH:"
    replacement_branch = (
        '    if y_dinh == BAO_CAO_XU_HUONG:\n'
        '        try:\n'
        '            import re\n'
        '            from aios_habit.production_prediction.periodic_trend_report import tao_bao_cao_dinh_ky_tuan\n'
        '            m_week = re.search(r"\\b(20\\d\\d-[wW]\\d{2})\\b", q_text, re.IGNORECASE)\n'
        '            ky_tuan = m_week.group(1).upper() if m_week else None\n'
        '            res = tao_bao_cao_dinh_ky_tuan(ky_tuan=ky_tuan)\n'
        '            return res.bao_cao_markdown\n'
        '        except Exception as exc:\n'
        '            return f"⚠️ Không thể sinh báo cáo xu hướng định kỳ: {exc}"\n'
        '    if y_dinh == XU_HUONG_LOG_TINH:'
    )
    app_text = app_text.replace(target_branch, replacement_branch, 1)
    app_file.write_text(app_text, encoding="utf-8")
    print("3. workspace_chat_app.py updated successfully.")
else:
    print("3. workspace_chat_app.py already contains BAO_CAO_XU_HUONG.")
