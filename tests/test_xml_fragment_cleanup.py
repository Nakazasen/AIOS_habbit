from __future__ import annotations

from types import SimpleNamespace

from aios_habit.document_extractors import _clean_lines
from aios_habit.rag_v2.synthesis import _candidate_fragments, _clean_raw_fragment_markup


def test_clean_raw_fragment_markup_removes_multiline_xml_and_namespaces():
    raw = (
        '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">\n'
        '  <p:cSld>\n'
        '    <p:spTree>\n'
        '      <p:sp>\n'
        '        <p:txBody>\n'
        '          <a:p><a:r><a:t>Sirius 2 - DMT PMT và cấu tạo BOM linh kiện</a:t></a:r></a:p>\n'
        '        </p:txBody>\n'
        '      </p:sp>\n'
        '    </p:spTree>\n'
        '  </p:cSld>\n'
        '</p:sld>'
    )
    cleaned = _clean_raw_fragment_markup(raw)
    assert "<" not in cleaned
    assert ">" not in cleaned
    assert "xmlns" not in cleaned.lower()
    assert "schemas.openxmlformats" not in cleaned
    assert "Sirius 2 - DMT PMT và cấu tạo BOM linh kiện" in cleaned


def test_candidate_fragments_never_leaks_xml_tags():
    raw = (
        '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">\n'
        'DMT PMT là cụm motor điều khiển gương xoay đa giác polygon scanner trong hệ thống LSU. '
        'Điện áp cấp cho motor là 24V DC và tín hiệu điều khiển FG_LOCK đạt mức cao khi đồng tốc.\n'
        '</p:sld>'
    )
    item = SimpleNamespace(snippet=raw, text=raw)
    fragments = _candidate_fragments(item)
    assert len(fragments) >= 1
    for frag in fragments:
        assert "<" not in frag
        assert ">" not in frag
        assert "xmlns" not in frag.lower()
        assert "schemas" not in frag.lower()
    assert any("DMT PMT là cụm motor" in f for f in fragments)


def test_document_extractors_clean_lines_strips_long_xml_tags():
    long_xml_tag = (
        '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
    )
    lines = [f"{long_xml_tag}Nội dung slide kiểm tra lỗi LSU."]
    cleaned = _clean_lines(lines)
    assert len(cleaned) == 1
    assert "<" not in cleaned[0]
    assert ">" not in cleaned[0]
    assert "xmlns" not in cleaned[0]
    assert cleaned[0] == "Nội dung slide kiểm tra lỗi LSU."
