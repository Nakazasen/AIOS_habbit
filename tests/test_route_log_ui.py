from aios_habit.ai_router import RouterAttempt, RouterResult
from aios_habit.route_log_ui import format_route_log_for_ui, route_attempt_status_to_vi, sanitize_route_log_text


def test_company_route_log_fallback_is_safe_and_vietnamese():
    meta = {
        "used_fallback": True,
        "provider_name": "Dữ liệu cục bộ",
        "safety_status": "Không gửi ra ngoài vì đây là tài liệu công ty/mật.",
        "attempts": [{"provider_name": "Gemini", "status": "blocked", "reason_vi": "Không gửi ra ngoài vì đây là tài liệu công ty/mật."}],
    }
    ui = format_route_log_for_ui(meta)
    assert ui["title"] == "Nhật ký AI đã dùng"
    assert ui["external_status"] == "Không gửi ra ngoài"
    assert ui["summary_badge"] == "Tự đổi về dữ liệu cục bộ"
    assert "công ty/mật" in ui["reason"]
    joined = str(ui)
    assert "local_only" not in joined
    assert "cloud_allowed" not in joined


def test_normal_external_route_log_shows_allowed_external_source():
    result = RouterResult("ok", "Groq", "llama", False, "external_allowed_normal_docs", [RouterAttempt("groq", "Groq", "llama", "success", "Đã dùng nguồn AI phù hợp cho tài liệu thường.")])
    result.route_summary_vi = "Nhật ký AI đã dùng\nCó gửi ra ngoài không: Có, vì đây là tài liệu thường"
    ui = format_route_log_for_ui(result)
    assert ui["summary_badge"] == "Đã dùng nguồn AI ngoài"
    assert ui["external_status"] == "Có dùng nguồn AI ngoài vì đây là tài liệu thường"
    assert ui["main_provider"] == "Groq"
    assert ui["attempts"][0]["status_vi"] == "Thành công"


def test_failover_route_log_says_source_changed():
    meta = {"used_fallback": False, "provider_name": "Groq", "safety_status": "external_allowed_normal_docs", "attempts": [{"provider_name":"Gemini", "status":"failed", "reason_vi":"quota"}, {"provider_name":"Groq", "status":"success", "reason_vi":"ok"}]}
    ui = format_route_log_for_ui(meta)
    assert ui["fallback_status"] == "Đã tự đổi nguồn"
    assert [a["status_vi"] for a in ui["attempts"]] == ["Lỗi", "Thành công"]


def test_route_log_sanitizer_masks_secrets_and_raw_labels():
    text = "local_only cloud_allowed provider policy route policy sk-abcdef123456 AIza1234567890abcdef nvapi-secret123 Authorization: Bearer token123"
    clean = sanitize_route_log_text(text)
    assert "local_only" not in clean
    assert "cloud_allowed" not in clean
    assert "provider policy" not in clean.lower()
    assert "route policy" not in clean.lower()
    assert "sk-abcdef" not in clean
    assert "AIza" not in clean
    assert "nvapi-" not in clean
    assert "Authorization" not in clean


def test_attempt_status_to_vietnamese():
    assert route_attempt_status_to_vi("success") == "Thành công"
    assert route_attempt_status_to_vi("blocked") == "Bị chặn an toàn"
    assert route_attempt_status_to_vi("cooldown") == "Đang tạm nghỉ"
