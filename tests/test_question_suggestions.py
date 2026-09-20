from aios_habit.question_suggestions import (
    citation_labels_of,
    followup_suggestions,
    opening_suggestions,
)


def test_opening_needs_enabled_sources():
    assert opening_suggestions([]) == []
    assert opening_suggestions(["  ", ""]) == []


def test_opening_single_source_names_it():
    out = opening_suggestions(["Huong dan JIG"])
    assert len(out) == 3
    assert all("Huong dan JIG" in question for question in out)


def test_opening_multi_source_compares_first_two():
    out = opening_suggestions(["Tai lieu A", "Tai lieu B", "Tai lieu C", "Tai lieu D"])
    assert len(out) == 3
    assert "Tai lieu A" in out[1] and "Tai lieu B" in out[1]


def test_followup_without_citations_stays_generic():
    out = followup_suggestions([])
    assert len(out) == 3


def test_followup_names_shown_citations():
    out = followup_suggestions(["[1]", "[2]"])
    assert "[1]" in out[0]
    assert "[2]" in out[2]


def test_citation_labels_accept_dicts_and_objects():
    class Fake:
        citation_label = "[3]"

    assert citation_labels_of([{"citation_label": "[1]"}, Fake(), {"nope": 1}]) == ["[1]", "[3]"]


def test_citation_labels_accept_app_badge_dicts():
    items = [
        {"citation_id": "[1]", "title": "Tai lieu A"},
        {"citation_id": "[2]", "title": "Tai lieu B"},
        {"title": "Khong co ma"},
    ]
    assert citation_labels_of(items) == ["[1]", "[2]"]
    out = followup_suggestions(citation_labels_of(items))
    assert "[1]" in out[0] and "[2]" in out[2]


def test_followup_names_documents_not_codes():
    from aios_habit.question_suggestions import followup_suggestions_from_items

    items = [
        {"citation_id": "[1]", "title": "Huong dan su dung Matecon v001.pdf"},
        {"citation_id": "[2]", "title": "Quy tac danh so vi tri gia WMS dai ten rat dai de can cat bot.pdf"},
    ]
    out = followup_suggestions_from_items(items)
    assert len(out) == 3
    assert "[1]" not in out[0] and "[2]" not in out[2]
    assert "Matecon" in out[0]
    assert ".pdf" not in out[0]


def test_short_name_readable_for_filenames():
    from aios_habit.question_suggestions import _short_source_name

    assert _short_source_name("Luu_trinh_loi_phat_sinh_khi_do.pdf") == "Luu trinh loi phat sinh khi do"
    short_jp = _short_source_name("マテコン操作手順書_v001_生産技術_TV.pdf")
    assert ".pdf" not in short_jp and "_" not in short_jp


def test_contextual_followups_stay_on_topic():
    from aios_habit.question_suggestions import contextual_followups, contextual_send_text

    items = [
        {"citation_id": "[1]", "title": "Huong dan Matecon.pdf"},
        {"citation_id": "[2]", "title": "Quy tac WMS.pdf"},
    ]
    out = contextual_followups(items, "Smart Factory là gì?")
    assert len(out) == 3
    assert all("Smart Factory" in display for display, _send in out)
    display, send = out[0]
    assert "…" not in send and "Huong dan Matecon" in send
    sent = contextual_send_text(send, "Smart Factory là gì?", "Smart Factory liên quan tự động hóa.")
    assert "Smart Factory là gì?" in sent
    assert "tự động hóa" in sent
