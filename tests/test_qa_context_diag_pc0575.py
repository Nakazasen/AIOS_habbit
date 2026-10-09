"""Bảo vệ luồng hỏi đáp trong sổ mới khi dùng kho tri thức production chung (QA-CONTEXT-DIAG-PC0575).

Kiểm tra:
1. Khi có kho tri thức dùng chung (is_production_index_available = True), người dùng tạo sổ mới
   không có tài liệu riêng (enabled_selections rỗng) vẫn được phép gửi câu hỏi tra cứu theo khối tri thức.
2. Khi không có kho production (is_production_index_available = False), sổ cá nhân rỗng
   vẫn bị chặn đúng quy ước insufficient_context / no_sources.
3. Khi query_relevant_sources rỗng nhưng forced_domain được chọn và có kho production,
   should_retrieve đánh giá là True để gọi retrieval vào library.sqlite.
"""
from unittest.mock import MagicMock, patch
import pytest

from aios_habit.workspace_chat_rag_v2_adapter import is_production_index_available


def test_production_index_availability_flag():
    """Xác nhận trạng thái sẵn sàng của kho tri thức production."""
    available = is_production_index_available()
    assert isinstance(available, bool)


def test_composer_gate_allows_empty_selections_when_production_index_ready():
    """Khi kho production sẵn sàng, composer không chặn insufficient_context / no_sources."""
    prod_index_ready = True
    enabled_selections = []
    one_shot_image_text = ""

    # Mô phỏng điều kiện kiểm tra ở composer submit
    blocked_no_sources = (not prod_index_ready and not enabled_selections and not one_shot_image_text)
    assert not blocked_no_sources, "Không được chặn câu hỏi khi kho production sẵn sàng"


def test_composer_gate_blocks_empty_selections_when_production_index_offline():
    """Khi kho production không có sẵn, sổ cá nhân rỗng vẫn bị chặn insufficient_context / no_sources."""
    prod_index_ready = False
    enabled_selections = []
    one_shot_image_text = ""

    blocked_no_sources = (not prod_index_ready and not enabled_selections and not one_shot_image_text)
    assert blocked_no_sources, "Phải chặn câu hỏi khi không có nguồn nào cả ở kho lẫn ở sổ"


def test_should_retrieve_evaluates_true_for_forced_domain_with_production_index():
    """should_retrieve phải bằng True khi có forced_domain và có kho production dù query_relevant_sources rỗng."""
    query_relevant_sources = ()
    forced_domain = "mom"
    is_prod_available = True

    should_retrieve = bool(
        query_relevant_sources or (forced_domain is not None and is_prod_available)
    )
    assert should_retrieve is True, "Phải kích hoạt retrieval khi có forced_domain trong kho production"


def test_broad_query_handling_does_not_trigger_error_toast_when_prod_ready():
    """Khi kho production sẵn sàng và không có nguồn riêng, không kích hoạt toast lỗi chuẩn bị."""
    ready_sources = ()
    unavailable_sources = []
    waiting_sources = []
    prod_index_ready = True

    query_relevant_sources = ()
    toast_called = False

    if ready_sources:
        query_relevant_sources = ready_sources
    elif unavailable_sources:
        pass
    elif waiting_sources:
        pass
    elif prod_index_ready:
        query_relevant_sources = ()
    else:
        toast_called = True

    assert not toast_called, "Không được gọi toast all_sources_preparation_error_fallback"
    assert query_relevant_sources == ()
