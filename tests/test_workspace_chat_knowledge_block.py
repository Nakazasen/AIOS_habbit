"""ROUND5-UX-COMPOSER — công tắc khối tri thức: badge đúng khối, trạng thái 3 khối.

Kiểm tra hành vi thật (không chỉ đọc mã nguồn):
- Badge "Đang tra cứu khối X." lấy từ payload định tuyến của đúng khối bị ép.
- Chế độ Tự động giữ nguyên badge + ghi chú câu hỏi mơ hồ như trước.
- Khối bị ép nhưng chưa có kho: không hiện badge, có thông báo tiếng Việt nêu tên khối.
- Hàm trạng thái sidebar trả đúng 3 khối kèm trạng thái sẵn sàng theo file kho thật.
"""
from aios_habit.index_domain import Classification, DomainRoute
from aios_habit.workspace_chat_app import (
    _knowledge_block_missing_message,
    _prefix_domain_block_badge,
)
from aios_habit.workspace_chat_rag_v2_adapter import (
    WorkspaceChatRagV2CanaryConfig,
    _domain_routing_payload,
    workspace_chat_domain_block_status,
)


def _forced_route(domain: str) -> DomainRoute:
    detected = Classification(domain, 1.0, "người dùng chọn khối")
    return DomainRoute(domain, domain, True, "người dùng chọn khối", detected)


def test_forced_block_payload_drives_the_badge_for_the_same_block() -> None:
    payload = _domain_routing_payload(_forced_route("lsu"))
    assert payload["applied"] is True
    assert payload["domain_display"] == "LSU"
    assert payload["ambiguous"] is False
    assert _prefix_domain_block_badge("", payload) == "Đang tra cứu khối LSU."


def test_badge_names_exactly_the_forced_block_and_keeps_summary() -> None:
    payload = _domain_routing_payload(_forced_route("dieu_tra_loi"))
    badge = _prefix_domain_block_badge("Tìm thấy 5 đoạn.", payload)
    assert badge == "Đang tra cứu khối Điều tra lỗi. Tìm thấy 5 đoạn."


def test_auto_mode_keeps_old_badge_and_ambiguity_note() -> None:
    detected = Classification("dieu_tra_loi", 0.1, "câu hỏi không rõ lĩnh vực")
    route = DomainRoute("dieu_tra_loi", "dieu_tra_loi", True, "chọn kho lĩnh vực", detected)
    badge = _prefix_domain_block_badge("", _domain_routing_payload(route))
    assert badge.startswith("Đang tra cứu khối Điều tra lỗi.")
    assert "chưa rõ lĩnh vực" in badge


def test_badge_is_not_added_when_no_block_was_searched() -> None:
    assert _prefix_domain_block_badge("Tìm thấy 5 đoạn.", None) == "Tìm thấy 5 đoạn."
    missing = DomainRoute(
        "tri_thuc",
        "mom",
        False,
        "khối được chọn chưa có kho trên máy này",
        Classification("mom", 1.0, "người dùng chọn khối"),
    )
    assert _prefix_domain_block_badge("x", _domain_routing_payload(missing)) == "x"


def test_missing_block_message_names_the_block_and_points_to_auto() -> None:
    payload = {"domain_routing": {"domain_display": "MOM", "applied": False}}
    message = _knowledge_block_missing_message(payload, "vi")
    assert "MOM" in message
    assert "Tự động" in message


def test_sidebar_block_status_reads_three_index_files(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aios_habit.workspace_chat_store.load_collection",
        lambda collection_id: None,
    )
    monkeypatch.setattr(
        WorkspaceChatRagV2CanaryConfig,
        "from_env",
        classmethod(lambda cls, env=None: cls(runtime_root=tmp_path)),
    )
    lsu_index = tmp_path / "bge_m3_hybrid" / "collections" / "lsu" / "library.sqlite"
    lsu_index.parent.mkdir(parents=True)
    lsu_index.write_bytes(b"x" * 8)

    status = workspace_chat_domain_block_status()
    assert [block["domain"] for block in status] == ["lsu", "dieu_tra_loi", "mom"]
    by_domain = {block["domain"]: block for block in status}
    assert by_domain["lsu"]["ready"] is True
    assert by_domain["lsu"]["size_bytes"] == 8
    assert by_domain["dieu_tra_loi"]["ready"] is False
    assert by_domain["mom"]["ready"] is False
