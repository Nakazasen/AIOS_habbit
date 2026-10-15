"""Tests for DESKTOP-EVIDENCE-DATE-REDACT-FIX-HOME:
Verifying that date strings (yyyy/mm/dd, yyyy-mm-dd, dd/mm/yyyy) in evidence
text are NOT redacted as local paths, while actual local paths (Windows drive,
UNC, user home, Unix) and credentials remain strictly redacted.
"""
from __future__ import annotations

import time
import pytest
from aios_habit.brain_gateway import (
    BrainGateway,
    BrainRequest,
    GatewaySource,
    OwnerConsent,
    PRIVACY_CLOUD_SAFE,
    PRIVACY_LOCAL_ONLY,
    PRIVACY_MACHINE_ONLY,
    PRIVACY_PUBLIC,
    WORKSPACE_CHAT_EXTERNAL_ROUTER_DESTINATION,
    calculate_source_set_hash,
    sanitize_text,
)


# =============================================================================
# 1. Test hai chieu (a): Chuoi ngay khong bi che
# =============================================================================

def test_date_yyyy_mm_dd_slash_not_redacted():
    """Chuoi ngay dang yyyy/mm/dd khong bi che boi bat ky pattern nao."""
    text = "Ngay kiem tra: 2026/08/20 va 2026/08/21."
    sanitized = sanitize_text(text)
    assert "2026/08/20" in sanitized
    assert "2026/08/21" in sanitized
    assert "[REDACTED_LOCAL_PATH]" not in sanitized


def test_date_yyyy_mm_dd_dash_not_redacted():
    """Chuoi ngay dang yyyy-mm-dd khong bi che."""
    text = "Thoi diem ghi nhan loi: 2026-08-20 den 2026-08-25."
    sanitized = sanitize_text(text)
    assert "2026-08-20" in sanitized
    assert "2026-08-25" in sanitized
    assert "[REDACTED_LOCAL_PATH]" not in sanitized


def test_date_dd_mm_yyyy_slash_and_dash_not_redacted():
    """Chuoi ngay dang dd/mm/yyyy va dd-mm-yyyy khong bi che."""
    text = "Dot thu nghiem: 20/08/2026 va 21-08-2026."
    sanitized = sanitize_text(text)
    assert "20/08/2026" in sanitized
    assert "21-08-2026" in sanitized
    assert "[REDACTED_LOCAL_PATH]" not in sanitized


def test_date_single_digit_month_day_not_redacted():
    """Chuoi ngay dang yyyy/m/d va d/m/yyyy khong bi che."""
    text = "Moc thoi gian: 2026/8/20 va 1/8/2026."
    sanitized = sanitize_text(text)
    assert "2026/8/20" in sanitized
    assert "1/8/2026" in sanitized
    assert "[REDACTED_LOCAL_PATH]" not in sanitized


def test_date_in_csv_evidence_line_not_redacted():
    """Dau vet thuc te tu tep 2026_08_UnitTest.csv chua ngay va gio giu nguyen."""
    csv_line = "2026/08/20,09:40:32,61C999999902, UnitTest,33.8,NG,NG,OK,NG,NG"
    sanitized = sanitize_text(csv_line)
    assert "2026/08/20" in sanitized
    assert "09:40:32" in sanitized
    assert "61C999999902" in sanitized
    assert "[REDACTED_LOCAL_PATH]" not in sanitized


def test_serial_61c999999902_four_rows_evidence_dates_preserved():
    """Doi chieu du kien chat che theo ve: serial 61C999999902 co 4 dong
    (20/08 mot dong, 21/08 ba dong) qua khau che van giu nguyen 100% cac moc ngay.
    """
    evidence = (
        "Bao cao phan dinh serial 61C999999902 tu 2026_08_UnitTest.csv:\n"
        "- 2026/08/20 09:40:32: TotalJudge=NG (Black=NG, Cyan=OK, Magenta=NG, Yellow=NG)\n"
        "- 2026/08/21 19:53:10: TotalJudge=NG (Black=NG, Cyan=OK, Magenta=NG, Yellow=NG)\n"
        "- 2026/08/21 19:54:01: TotalJudge=NG (Black=NG, Cyan=OK, Magenta=NG, Yellow=NG)\n"
        "- 2026/08/21 19:56:14: TotalJudge=NG (Black=NG, Cyan=OK, Magenta=NG, Yellow=NG)\n"
        "Ket luan: 4 dong du lieu (20/08 co 1 dong, 21/08 co 3 dong)."
    )
    sanitized = sanitize_text(evidence)
    assert sanitized.count("2026/08/20") == 1
    assert sanitized.count("2026/08/21") == 3
    assert "20/08 co 1 dong" in sanitized
    assert "21/08 co 3 dong" in sanitized
    assert "[REDACTED_LOCAL_PATH]" not in sanitized


def test_dates_in_punctuation_and_brackets_not_redacted():
    """Cac chuoi ngay nam trong ngoac don, ngoac vuong, dau phay, cham phay."""
    text = "Cac moc: (2026/08/20), [2026/08/21], '2026/08/22', \"2026/08/23\"; 2026/08/24."
    sanitized = sanitize_text(text)
    assert "(2026/08/20)" in sanitized
    assert "[2026/08/21]" in sanitized
    assert "'2026/08/22'" in sanitized
    assert '"2026/08/23"' in sanitized
    assert "2026/08/24" in sanitized
    assert "[REDACTED_LOCAL_PATH]" not in sanitized


# =============================================================================
# 2. Test hai chieu (b): Duong dan cuc bo that VAN PHAI BI CHE
# =============================================================================

def test_windows_drive_paths_redacted():
    """Duong dan o dia Windows (gach cheo xuoi hoac nguoc) van bi che."""
    text_bs = r"Tep duoc luu tai D:\Sandbox\AIOS_habbit\data\secrets.txt tren may."
    sanitized_bs = sanitize_text(text_bs)
    assert r"D:\Sandbox" not in sanitized_bs
    assert "[REDACTED_LOCAL_PATH]" in sanitized_bs

    text_fs = "Tep duoc luu tai C:/Users/Admin/Documents/config.yaml tren may."
    sanitized_fs = sanitize_text(text_fs)
    assert "C:/Users/Admin" not in sanitized_fs
    assert "[REDACTED_LOCAL_PATH]" in sanitized_fs


def test_unc_paths_redacted():
    """Duong dan UNC (\\\\server\\share hoac //server/share) phai bi che."""
    unc_bs = r"Truy cap kho share tai \\filestore.local\production\logs\2026_08.log."
    sanitized_unc_bs = sanitize_text(unc_bs)
    assert r"\\filestore.local" not in sanitized_unc_bs
    assert "[REDACTED_LOCAL_PATH]" in sanitized_unc_bs

    unc_fs = "//smbserver/share/engineering/spec.xlsx"
    sanitized_unc_fs = sanitize_text(unc_fs)
    assert "//smbserver" not in sanitized_unc_fs
    assert "[REDACTED_LOCAL_PATH]" in sanitized_unc_fs


def test_user_home_paths_redacted():
    """Duong dan thu muc nguoi dung (~/...) phai bi che."""
    text = "Cau hinh nguoi dung tai ~/.aios/settings.json va ~/workspace/data.csv."
    sanitized = sanitize_text(text)
    assert "~/.aios" not in sanitized
    assert "~/workspace" not in sanitized
    assert "[REDACTED_LOCAL_PATH]" in sanitized


def test_unix_absolute_paths_redacted():
    """Duong dan Unix tuyet doi (/home/..., /var/log/..., /etc/...) phai bi che."""
    text = "Xem nhat ky tai /var/log/nginx/access.log hoac /home/deploy/app.py."
    sanitized = sanitize_text(text)
    assert "/var/log" not in sanitized
    assert "/home/deploy" not in sanitized
    assert "[REDACTED_LOCAL_PATH]" in sanitized


def test_unix_path_containing_date_folders_is_still_redacted():
    """Neu chuoi la mot duong dan that chua thu muc nam/thang/ngay thi TOAN BO duong dan phai bi che."""
    path_with_date = "Nhat ky loi tai /var/log/production/2026/08/20/error.log duoc tao."
    sanitized = sanitize_text(path_with_date)
    assert "/var/log" not in sanitized
    assert "error.log" not in sanitized
    assert "[REDACTED_LOCAL_PATH]" in sanitized


# =============================================================================
# 3. Test bao ve an toan: Khong noi long cac lop che khac (keys, tokens, secrets)
# =============================================================================

def test_api_keys_and_tokens_remain_redacted():
    """Lop che API keys (sk-..., AIza...) va token/secret van hoat dong 100% nhu cu."""
    dummy_pw = "UltraSecret123!"
    dummy_tok = "prod_token_abcdef1234567890"
    text = (
        "Khoa OpenAI: " + "sk-abcdef1234567890abcdef1234567890, "
        "Khoa Google: " + "AIzaSyD1234567890abcdef1234567890, "
        + "pass" + "word='" + dummy_pw + "', "
        + "api_" + "key=\"" + dummy_tok + "\"."
    )
    sanitized = sanitize_text(text)
    assert "sk-abcdef" not in sanitized
    assert "AIzaSyD" not in sanitized
    assert dummy_pw not in sanitized
    assert dummy_tok not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized
    assert "[REDACTED_SECRET]" in sanitized


# =============================================================================
# 4. Test tich hop BrainGateway end-to-end
# =============================================================================

def test_brain_gateway_preflight_preserves_dates_in_question_and_sources(monkeypatch):
    """BrainGateway preflight_check phai giu nguyen ngay trong question va outbound sources
    nhung che dung duong dan cuc bo va key.
    """
    monkeypatch.setenv("AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS", "1")

    question = (
        "Trong tệp 2026_08_UnitTest.csv, serial 61C999999902 ngày 2026/08/20 "
        "và 2026/08/21 có kết quả ra sao? Đường dẫn lưu tại D:\\Sandbox\\data.csv."
    )
    secret_val = "secret12345678"
    source_text = (
        "Serial 61C999999902: 2026/08/20 TotalJudge=NG; 2026/08/21 TotalJudge=NG. "
        + "Tệp gốc tại /var/storage/units/2026_08_UnitTest.csv với "
        + "api_" + "key='" + secret_val + "'."
    )
    s = GatewaySource(
        source_id="src_1",
        source_scope="notebook",
        source_type="csv",
        title="2026_08_UnitTest.csv",
        privacy_label=PRIVACY_LOCAL_ONLY,
        text=source_text,
    )
    req = BrainRequest(
        question=question,
        sources=(s,),
        consent=None,
        router_enabled=True,
        destination=WORKSPACE_CHAT_EXTERNAL_ROUTER_DESTINATION,
    )
    gw = BrainGateway()
    decision = gw.preflight_check(req)

    assert decision.allowed
    payload = decision.sanitized_payload
    assert payload is not None

    # Question: giu nguyen ngay, che duong dan Windows
    assert "2026/08/20" in payload.sanitized_question
    assert "2026/08/21" in payload.sanitized_question
    assert "61C999999902" in payload.sanitized_question
    assert r"D:\Sandbox" not in payload.sanitized_question
    assert "[REDACTED_LOCAL_PATH]" in payload.sanitized_question

    # Source: giu nguyen ngay, che duong dan Unix va secret
    sanitized_src = payload.sanitized_sources[0].text
    assert "2026/08/20" in sanitized_src
    assert "2026/08/21" in sanitized_src
    assert "61C999999902" in sanitized_src
    assert "/var/storage" not in sanitized_src
    assert "secret12345678" not in sanitized_src
    assert "[REDACTED_LOCAL_PATH]" in sanitized_src
    assert "[REDACTED_SECRET]" in sanitized_src
