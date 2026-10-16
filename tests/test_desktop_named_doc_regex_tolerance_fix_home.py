"""Tests for DESKTOP-NAMED-DOC-REGEX-TOLERANCE-FIX-R2-HOME.

Verifies:
1. Longest suffix matching against real document catalog (removing leading cues like 'điều tra lỗi', 'báo cáo', etc.).
2. Preservation of model code prefix ('QA_C0650' is not stripped to 'QA_0650') and tolerance when matching.
3. Accurate matching on benchmark cases: T071, T072, T076, T077, T078, T087, T110.
4. Zero false 'named_document_not_found' occurrences on these benchmark cases.
5. Regression coverage for AUTO-ROUTE-NAMED-DOC-FIX (Ha Tung cases: Tab led cam ung.pdf and honest refusal on nonexistent docs).
"""

from pathlib import Path
from aios_habit.index_domain import (
    clean_named_doc_token,
    detect_domain_from_question,
    extract_named_document_candidates,
    load_all_index_specs,
    match_named_documents,
)


def test_clean_named_doc_token_strips_cues_and_domain_names():
    # Strips leading Vietnamese/English document cues and domain phrases
    assert clean_named_doc_token("điều tra lỗi Write DP Serial NG.xlsx") == "Write DP Serial NG.xlsx"
    assert clean_named_doc_token("báo cáo điều tra lỗi Không lên nguồn.xlsx") == "Không lên nguồn.xlsx"
    assert clean_named_doc_token("theo tài liệu Tab led cam ung.pdf") == "Tab led cam ung.pdf"
    assert clean_named_doc_token("tệp TANABAN_Master.xlsx") == "TANABAN_Master.xlsx"
    assert clean_named_doc_token("email FW IRIS2020.msg") == "FW IRIS2020.msg"


def test_t071_model_code_prefix_preserved_and_matches_real_doc():
    # 1. When question contains QA_C0650_08_Dec.msg, candidate extraction preserves prefix 'C'
    q_with_c = "Trong email FW IRIS2020 (High Model) QA_C0650_08_Dec.msg, Ngô Ngọc Đức đã gửi lại file log."
    cands_with_c = extract_named_document_candidates(q_with_c)
    assert any("QA_C0650_08_Dec.msg" in c for c in cands_with_c)
    assert not any("QA_0650" in c and "C0650" not in c for c in cands_with_c)

    matched_with_c, missing_with_c = match_named_documents(q_with_c)
    assert len(matched_with_c) >= 1
    assert any("QA_C0650_08_Dec.msg" in getattr(s, "path", s).name for s in matched_with_c)
    assert len(missing_with_c) == 0

    # 2. When question contains QA_0650_08_Dec.msg (omitted 'C'), tolerance still matches real doc
    q_no_c = (
        "Trong email FW IRIS2020 (High Model) QA_0650_08_Dec.msg, Ngô Ngọc Đức đã gửi lại file log "
        "của lỗi QA cho Yasui và mã S/No máy (Serial machine) được nêu là gì?"
    )
    matched_no_c, missing_no_c = match_named_documents(q_no_c)
    assert len(matched_no_c) >= 1
    assert any("QA_C0650_08_Dec.msg" in getattr(s, "path", s).name for s in matched_no_c)
    assert len(missing_no_c) == 0

    res = detect_domain_from_question(q_no_c)
    assert res.domain == "dieu_tra_loi"
    assert res.confidence == 1.0


def test_t072_matches_real_doc_with_japanese_and_code():
    q = (
        "Trong email RE 「Iris2020下位」 エラー発生 Log QA.msg ngày 2021-11-11 về mã lỗi 6900, "
        "Horikawa Hitoshi (堀川仁志) đã phản hồi cho Fukuda (福田) rằng sẽ phối hợp với ai để "
        "kiểm tra các máy trước và sau khi phát sinh lỗi?"
    )
    matched, missing = match_named_documents(q)
    assert len(matched) >= 1
    assert any("Log C6900_QA.msg" in getattr(s, "path", s).name for s in matched)
    assert len(missing) == 0

    res = detect_domain_from_question(q)
    assert res.domain == "dieu_tra_loi"
    assert res.confidence == 1.0


def test_t076_matches_real_doc_and_strips_dieu_tra_loi():
    q = (
        "Theo báo cáo điều tra lỗi Write DP Serial NG.xlsx trên cụm DP Iris2020 (số hiệu 08-0866), "
        "lỗi xảy ra trên bản mạch PWB DRIVER ASSY có mã Item code - Rev và nhà cung cấp (Supplier) nào?"
    )
    matched, missing = match_named_documents(q)
    assert len(matched) >= 1
    top_name = getattr(matched[0], "path", matched[0]).name
    assert "Write DP Serial NG.xlsx" in top_name
    assert "08-0866" in top_name
    assert len(missing) == 0

    res = detect_domain_from_question(q)
    assert res.domain == "dieu_tra_loi"
    assert res.confidence == 1.0


def test_t077_matches_real_doc_with_disambiguation():
    q = (
        "Trong báo cáo điều tra lỗi Không lên nguồn.xlsx trên máy Iris2024 (số hiệu 05-0469, "
        "Serial J3C0053Y4242), cụm nguồn UNIT LOW VOLTAGE bị lỗi có mã linh kiện và nhà cung cấp là gì?"
    )
    matched, missing = match_named_documents(q)
    assert len(matched) >= 1
    top_name = getattr(matched[0], "path", matched[0]).name
    assert "05-0469" in top_name
    assert "Không lên nguồn.xlsx" in top_name
    assert len(missing) == 0

    res = detect_domain_from_question(q)
    assert res.domain == "dieu_tra_loi"
    assert res.confidence == 1.0


def test_t078_matches_real_doc_with_disambiguation():
    q = (
        "Trong báo cáo điều tra lỗi Không lên nguồn.xlsx trên máy Iris2024 (số hiệu 06-0639, "
        "Serial J3C0054A0873), cụm nguồn UNIT LOW VOLTAGE có nhà cung cấp (Supplier) nào?"
    )
    matched, missing = match_named_documents(q)
    assert len(matched) >= 1
    top_name = getattr(matched[0], "path", matched[0]).name
    assert "06-0639" in top_name
    assert "Không lên nguồn.xlsx" in top_name
    assert len(missing) == 0

    res = detect_domain_from_question(q)
    assert res.domain == "dieu_tra_loi"
    assert res.confidence == 1.0


def test_t087_matches_real_doc_c3501():
    q = (
        "Trong email RE IRIS2020 (Low model) Upsoft OK initial setting LCD displayed 3501.msg "
        "ngày 2021-10-21 gửi cho Ducさん, người gửi Inoue Takashi thuộc bộ phận (課) nào?"
    )
    matched, missing = match_named_documents(q)
    assert len(matched) >= 1
    assert any("C3501.msg" in getattr(s, "path", s).name for s in matched)
    assert len(missing) == 0

    res = detect_domain_from_question(q)
    assert res.domain in ("tong_hop", "dieu_tra_loi")
    assert res.confidence == 1.0


def test_t110_matches_materialized_tanaban_master():
    q = (
        "Trong tệp TANABAN_Master.xlsx (Sheet TANABAN_TSUIKA), các mã vị trí kệ từ C3A02010101 "
        "đến C3A02010201 thuộc khu vực nhà C tầng mấy và được gán mã kho nào?"
    )
    matched, missing = match_named_documents(q)
    assert len(matched) >= 1
    assert any("ef0d" in getattr(s, "document_id", "") for s in matched)
    assert len(missing) == 0

    res = detect_domain_from_question(q)
    assert res.domain in ("mom", "tri_thuc")
    assert res.confidence == 1.0


def test_ha_tung_regression_existing_and_refusal():
    # 1. Existing named doc (Tab led cam ung.pdf) routes to tong_hop with confidence 1.0
    q_existing = (
        "Theo tài liệu Tab led cam ung.pdf (Touch Panel Specification), "
        "điều kiện nhiệt độ và độ ẩm tiêu chuẩn để bảo quản (Storage) touch panel là bao nhiêu?"
    )
    matched, missing = match_named_documents(q_existing)
    assert len(matched) >= 1
    assert any("Tab led cam ung.pdf" in getattr(s, "path", s).name for s in matched)
    assert len(missing) == 0

    res_existing = detect_domain_from_question(q_existing)
    assert res_existing.domain == "tong_hop"
    assert res_existing.confidence == 1.0

    # 2. Non-existent doc must refuse honestly with confidence 0.0
    q_missing = "Theo tài liệu khong_ton_tai_123.pdf, nhiệt độ bảo quản là bao nhiêu?"
    matched_m, missing_m = match_named_documents(q_missing)
    assert len(matched_m) == 0
    assert "khong_ton_tai_123.pdf" in missing_m

    res_missing = detect_domain_from_question(q_missing)
    assert res_missing.confidence == 0.0
    assert "khong_ton_tai_123.pdf" in res_missing.reason
