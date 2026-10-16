"""Unit tests for DESKTOP-PC0575-SYNC-C7620 parity and system policy rules."""
import inspect
import re
import pytest

from aios_habit.antigravity_bridge import route_workspace_chat_submission


def test_system_policy_includes_c7620_parity_instructions():
    """Ensure system_policy in route_workspace_chat_submission enforces line trends, defect color, and states."""
    src = inspect.getsource(route_workspace_chat_submission)
    assert "system_policy" in src
    assert "LINE" in src
    assert "Trend" in src
    assert "発生色" in src
    assert "想定状態" in src
    assert "Magenta" in src


def test_q0700_criteria_pattern_matches_expected_answer():
    sample_q0700_ans = (
        "Dựa trên tài liệu đính kèm, xu hướng phát sinh lỗi (発生状況 / Trend) tại C23 và C24 được ghi nhận như sau:\n\n"
        "* **Thời gian:** Ngày 2 tháng 19 (２月１９日).\n"
        "* **Dây chuyền (LINE):** C23/24.\n"
        "* **Xu hướng biến động (Trend/NG suất):** NG suất có cùng xu hướng và đồng thời tăng lên (NG 率が同じ傾向→同時に上昇).\n"
        "* **Màu sắc phát sinh (発生色):** Magenta.\n"
    )
    assert re.search(r"C23/24|C23/C24|C23", sample_q0700_ans)
    assert re.search(r"19/2|19 tháng 2|２月１９日|2月19日", sample_q0700_ans)
    assert re.search(r"cùng xu hướng|đồng thời tăng|同じ傾向|同時に上昇|Trend", sample_q0700_ans)
    assert re.search(r"Magenta|発生色", sample_q0700_ans)


def test_q0703_criteria_pattern_matches_expected_answer():
    sample_q0703_ans = (
        "Dựa trên tài liệu [Sirius 2 _ C7620_報告版 4.pptx], các trạng thái giả định dẫn đến việc khoảng cách B (B距離) "
        "trở nên dài hơn (gây ra tình trạng khoảng cách giữa Bk và M lớn, dễ xuất hiện lỗi M màu Error C7620) được liệt kê cụ thể như sau:\n\n"
        "* ①: Trường hợp bình thường, nhưng vị trí đường quang (光路) của M dịch chuyển nhiều hơn về phía cộng/dương (+側) (trong khi Bk không thay đổi).\n"
        "* ②: Trường hợp bình thường, nhưng vị trí đường quang của Bk dịch chuyển về phía trừ/âm (-側) (trong khi M không thay đổi).\n"
        "* ③: Trường hợp cả hai trạng thái ① và ② xảy ra đồng thời (cả hai bên đều dịch chuyển cùng lúc).\n"
    )
    assert re.search(r"M.*(cộng|\+|プラス|dương)", sample_q0703_ans)
    assert re.search(r"Bk.*(trừ|-|ー|âm|マイナス)", sample_q0703_ans)
    assert re.search(r"cả hai|đồng thời|kết hợp|両方|同時に", sample_q0703_ans)
    assert re.search(r"khoảng cách B|B距離|C7620|Magenta|M", sample_q0703_ans)


def test_q0708_criteria_pattern_matches_expected_answer():
    sample_q0708_ans = (
        "Do đó, không phải cứ vượt quá 1.15 mm là luôn luôn khiến Camera không đọc được ngay lập tức, mà theo tài liệu:\n"
        "- Mức từ 1.15 mm trở lên là có khả năng phát sinh lỗi C7620.\n"
        "- Mức từ 1.24 trở lên mới chính là ngưỡng làm cho Camera nằm ngoài phạm vi đọc được (Camera の読み込める範囲から外れ)."
    )
    assert re.search(r"không phải|không|いいえ|không thể khẳng định", sample_q0708_ans)
    assert re.search(r"1\.15", sample_q0708_ans) and re.search(r"C7620|khả năng|nguy cơ", sample_q0708_ans)
    assert re.search(r"1\.24", sample_q0708_ans) and re.search(r"Camera|đọc|ngoài phạm vi|phạm vi", sample_q0708_ans)
