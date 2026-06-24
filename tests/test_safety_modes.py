from aios_habit.safety_modes import (
    SAFETY_MODE_AUTO,
    SAFETY_MODE_COMPANY,
    SAFETY_MODE_NORMAL,
    get_safety_mode_options,
    privacy_level_to_safety_mode_label,
    safety_mode_to_privacy_level,
    suggest_safety_mode,
)


def test_safety_mode_options_are_vietnamese():
    assert get_safety_mode_options() == [
        "Tự động",
        "Tài liệu công ty / tài liệu mật",
        "Tài liệu thường",
    ]


def test_company_paths_suggest_company_safe():
    assert suggest_safety_mode(path="D:/Sandbox/MOM_WMS_QLLSSX/tailieugoc") == SAFETY_MODE_COMPANY
    assert suggest_safety_mode(name="ERP production report") == SAFETY_MODE_COMPANY
    assert suggest_safety_mode(notebook_name="Hồ sơ khách hàng nội bộ") == SAFETY_MODE_COMPANY


def test_public_demo_paths_suggest_normal():
    assert suggest_safety_mode(name="synthetic demo public sample") == SAFETY_MODE_NORMAL
    assert suggest_safety_mode(path="tests/sample_personal_notes.md") == SAFETY_MODE_NORMAL


def test_unknown_suggests_auto():
    assert suggest_safety_mode(name="ghi chú mới") == SAFETY_MODE_AUTO


def test_safety_modes_map_to_internal_privacy_levels():
    assert safety_mode_to_privacy_level(SAFETY_MODE_COMPANY) == "local_only"
    assert safety_mode_to_privacy_level(SAFETY_MODE_NORMAL) == "cloud_allowed"
    assert safety_mode_to_privacy_level(SAFETY_MODE_AUTO, {"name": "MOM report"}) == "local_only"
    assert safety_mode_to_privacy_level(SAFETY_MODE_AUTO, {"name": "demo public"}) == "cloud_allowed"


def test_internal_privacy_levels_map_to_vietnamese_labels():
    assert privacy_level_to_safety_mode_label("local_only") == SAFETY_MODE_COMPANY
    assert privacy_level_to_safety_mode_label("redacted_export") == SAFETY_MODE_COMPANY
    assert privacy_level_to_safety_mode_label("cloud_allowed") == SAFETY_MODE_NORMAL
