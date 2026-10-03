import base64

import pytest

from aios_habit import chat_action
from aios_habit.chat_action import (
    BLOCK_CHART,
    BLOCK_MARKDOWN,
    BLOCK_TABLE,
    ChatAction,
    ChatActionBlock,
    ChatActionOutcome,
    ChatActionRequest,
)
from aios_habit.feature_flags import (
    FEATURE_CHAT_ACTION,
    get_feature_snapshot,
    override_feature_flags,
    reset_feature_flags,
)


@pytest.fixture(autouse=True)
def _clean_state():
    reset_feature_flags()
    chat_action.reset_actions()
    yield
    reset_feature_flags()
    chat_action.reset_actions()


@pytest.fixture()
def _isolated_stores(tmp_path, monkeypatch):
    """Point the daily_next_actions stores at a temp dir (same pattern as
    tests/test_daily_next_actions.py) so nothing touches real local_cases data."""
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))
    monkeypatch.setattr("aios_habit.source_ingest.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.source_ingest.SOURCES_FILE", tmp_path / "sources.jsonl")
    monkeypatch.setattr("aios_habit.source_ingest.NOTEBOOK_ASSETS_DIR", tmp_path / "notebook_assets")
    monkeypatch.setattr("aios_habit.notebook_index.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.notebook_index.CHUNKS_FILE", tmp_path / "source_chunks.jsonl")
    monkeypatch.setattr("aios_habit.notebook_import_store.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.notebook_import_store.IMPORTS_FILE", tmp_path / "notebook_bridge_imports.jsonl")
    monkeypatch.setattr("aios_habit.case_store.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.case_store.CASES_FILE", tmp_path / "cases.jsonl")
    monkeypatch.setattr("aios_habit.case_store.EVIDENCE_FILE", tmp_path / "evidence.jsonl")
    monkeypatch.setattr("aios_habit.case_store.ASSETS_DIR", tmp_path / "assets")
    return tmp_path


def _request(question: str, **kwargs) -> ChatActionRequest:
    return ChatActionRequest(question=question, **kwargs)


def test_normalize_text_strips_diacritics_and_case():
    assert chat_action.normalize_text("  Tiếp   theo NÊN làm gì? ") == "tiep theo nen lam gi?"
    assert chat_action.normalize_text("Đường") == "duong"


def test_register_and_match_action_by_hint():
    action = ChatAction(name="chao", title="Chào", hints=("xin chào",), handler=lambda request: None)
    chat_action.register_action(action)
    assert action.hints == ("xin chao",)
    hit = chat_action.match_action(_request("Xin chào bạn nhé"))
    assert hit is not None and hit.name == "chao"
    assert chat_action.match_action(_request("câu hỏi khác")) is None


def test_dispatch_returns_handler_outcome_and_forwards_context():
    seen = {}

    def handler(request):
        seen["question"] = request.question
        seen["notebook_id"] = request.notebook_id
        return ChatActionOutcome(
            action="demo",
            title="Kết quả",
            blocks=(ChatActionBlock(BLOCK_MARKDOWN, text="nội dung"),),
        )

    chat_action.register_action(ChatAction(name="demo", title="Demo", hints=("bảng thử",), handler=handler))
    outcome = chat_action.dispatch(_request("Cho tôi bảng thử", notebook_id="NB-1"))
    assert outcome is not None and outcome.action == "demo"
    assert seen == {"question": "Cho tôi bảng thử", "notebook_id": "NB-1"}


def test_dispatch_falls_through_when_handler_raises_or_no_match():
    def boom(request):
        raise RuntimeError("hỏng")

    chat_action.register_action(ChatAction(name="boom", title="Hỏng", hints=("kích nổ",), handler=boom))
    assert chat_action.dispatch(_request("kích nổ ngay")) is None
    assert chat_action.dispatch(_request("không liên quan")) is None


def test_dispatch_survives_builtin_import_failure(monkeypatch):
    monkeypatch.setattr(chat_action, "BUILTIN_ACTION_MODULES", ("aios_habit.khong_ton_tai_abc",))
    assert chat_action.dispatch(_request("bất kỳ")) is None


def test_block_validation():
    with pytest.raises(ValueError):
        ChatActionBlock("unknown")
    with pytest.raises(ValueError):
        ChatActionBlock(BLOCK_TABLE)
    with pytest.raises(ValueError):
        ChatAction(name="x", title="X", hints=(), handler=lambda request: None)


def test_render_outcome_markdown_and_table_escape():
    outcome = ChatActionOutcome(
        action="demo",
        title="Bảng thử",
        blocks=(
            ChatActionBlock(BLOCK_MARKDOWN, text="Mở đầu"),
            ChatActionBlock(
                BLOCK_TABLE,
                headers=("#", "Việc"),
                rows=[("1", "a | b"), ("2", "x\ny")],
                caption="Nguồn",
            ),
        ),
    )
    rendered = chat_action.render_outcome(outcome)
    assert rendered.startswith("**Bảng thử**")
    assert "Mở đầu" in rendered
    assert "| # | Việc |" in rendered
    assert "| --- | --- |" in rendered
    assert r"| 1 | a \| b |" in rendered
    assert "| 2 | x y |" in rendered
    assert rendered.endswith("*Nguồn*")


def test_render_chart_block_embeds_png_data_uri():
    png = b"\x89PNG\r\n\x1a\npayload"
    outcome = ChatActionOutcome(
        action="c",
        title="Biểu đồ",
        blocks=(ChatActionBlock(BLOCK_CHART, image_png=png, caption="Độ lệch"),),
    )
    rendered = chat_action.render_outcome(outcome)
    assert "data:image/png;base64," + base64.b64encode(png).decode("ascii") in rendered
    assert "Độ lệch" in rendered


def test_render_chart_block_refuses_oversized_image(monkeypatch):
    monkeypatch.setattr(chat_action, "CHART_MAX_BYTES", 8)
    outcome = ChatActionOutcome(
        action="c",
        title="Biểu đồ",
        blocks=(ChatActionBlock(BLOCK_CHART, image_png=b"x" * 9, caption="To"),),
    )
    rendered = chat_action.render_outcome(outcome)
    assert "data:image" not in rendered
    assert "quá lớn" in rendered


def test_builtin_action_matches_and_renders_next_step_table(_isolated_stores):
    chat_action.load_builtin_actions()
    outcome = chat_action.dispatch(
        _request("Tiếp theo nên làm gì?", notebook_id="NB-123", workspace_id="default")
    )
    assert outcome is not None
    assert outcome.action == "goi_y_viec_tiep_theo"
    tables = [block for block in outcome.blocks if block.kind == BLOCK_TABLE]
    assert len(tables) == 1
    assert tables[0].headers == ("#", "Việc nên làm tiếp")
    assert tables[0].rows[0][1] == "Nạp tài liệu nguồn vào Sổ tri thức."
    rendered = chat_action.render_outcome(outcome)
    assert "Việc nên làm tiếp" in rendered
    assert "| 1 | Nạp tài liệu nguồn vào Sổ tri thức. |" in rendered


def test_builtin_action_matches_unaccented_question(_isolated_stores):
    chat_action.load_builtin_actions()
    outcome = chat_action.dispatch(_request("tiep theo nen lam gi", notebook_id="NB-123"))
    assert outcome is not None and outcome.action == "goi_y_viec_tiep_theo"


def test_builtin_action_without_notebook_returns_guidance(_isolated_stores):
    chat_action.load_builtin_actions()
    outcome = chat_action.dispatch(_request("Gợi ý việc nên làm tiếp"))
    assert outcome is not None
    assert all(block.kind == BLOCK_MARKDOWN for block in outcome.blocks)
    assert "Chưa có sổ tri thức nào đang mở" in chat_action.render_outcome(outcome)


def test_handle_chat_text_saves_messages_and_reports_handled(_isolated_stores):
    saved = []
    handled = chat_action.handle_chat_text(
        "Tiếp theo nên làm gì?",
        conversation_id="C1",
        notebook_id="NB-123",
        workspace_id="default",
        save_user=lambda content: saved.append(("user", content)),
        save_assistant=lambda content: saved.append(("assistant", content)),
    )
    assert handled is True
    assert saved[0] == ("user", "Tiếp theo nên làm gì?")
    assert "Việc nên làm tiếp" in saved[1][1]


def test_handle_chat_text_ignores_unrelated_question(_isolated_stores):
    saved = []
    handled = chat_action.handle_chat_text(
        "Cho tôi tóm tắt tài liệu",
        save_user=lambda content: saved.append(content),
        save_assistant=lambda content: saved.append(content),
    )
    assert handled is False
    assert saved == []


def test_chat_action_flag_off_by_default(monkeypatch):
    monkeypatch.delenv("AIOS_FEATURE_CHAT_ACTION", raising=False)
    reset_feature_flags()
    assert chat_action.chat_action_enabled() is False


def test_chat_action_flag_respects_override():
    with override_feature_flags(chat_action=True):
        assert chat_action.chat_action_enabled() is True
    with override_feature_flags(chat_action=False):
        assert chat_action.chat_action_enabled() is False


def test_feature_snapshot_includes_chat_action():
    snapshot = get_feature_snapshot()
    assert FEATURE_CHAT_ACTION in snapshot.to_dict()
    assert snapshot.is_enabled(FEATURE_CHAT_ACTION) is snapshot.chat_action
