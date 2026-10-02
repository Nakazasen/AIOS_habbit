"""Multi-intent dispatch (UX-CHAT-CORE): one chat message, every matching action runs."""

import pytest

from aios_habit import chat_action
from aios_habit.chat_action import (
    BLOCK_MARKDOWN,
    ChatAction,
    ChatActionBlock,
    ChatActionOutcome,
    ChatActionRequest,
)


@pytest.fixture(autouse=True)
def _clean_state():
    chat_action.reset_actions()
    yield
    chat_action.reset_actions()


def _request(question: str) -> ChatActionRequest:
    return ChatActionRequest(question=question)


def _outcome(tag: str) -> ChatActionOutcome:
    return ChatActionOutcome(
        action=tag,
        title=f"Kết quả {tag}",
        blocks=(ChatActionBlock(BLOCK_MARKDOWN, text=f"nội dung {tag}"),),
    )


def _register(name: str, hint: str, *, fallback: bool = False, fail: bool = False):
    def handler(request):
        if fail:
            raise RuntimeError("boom")
        return _outcome(name)

    chat_action.register_action(
        ChatAction(name=name, title=f"T{ name}", hints=(hint,), handler=handler, fallback=fallback)
    )


def test_match_all_returns_every_hit_in_priority_order():
    _register("a", "ve bieu do")
    _register("b", "dat nguong")
    hits = chat_action.match_all_actions(_request("vẽ biểu đồ và đặt ngưỡng giúp tôi"))
    assert [h.name for h in hits] == ["a", "b"]


def test_dispatch_multi_merges_two_intents_into_one_answer():
    _register("a", "ve bieu do")
    _register("b", "dat nguong")
    outcome = chat_action.dispatch_multi(_request("vẽ biểu đồ và đặt ngưỡng"))
    assert outcome is not None
    assert outcome.title == "Đã xử lý 2 việc trong một câu trả lời"
    assert outcome.action == "a+b"
    text = chat_action.render_outcome(outcome)
    assert "nội dung a" in text and "nội dung b" in text


def test_dispatch_multi_single_intent_behaves_like_legacy_dispatch():
    _register("a", "ve bieu do")
    outcome = chat_action.dispatch_multi(_request("vẽ biểu đồ"))
    assert outcome is not None
    assert outcome.title == "Kết quả a"


def test_dispatch_multi_returns_none_when_nothing_matches():
    _register("a", "ve bieu do")
    assert chat_action.dispatch_multi(_request("câu hỏi không liên quan")) is None


def test_fallback_action_does_not_piggyback_on_specific_action():
    _register("specific", "tra cuu")
    _register("generic", "tra cuu", fallback=True)
    outcome = chat_action.dispatch_multi(_request("tra cứu giúp tôi"))
    assert outcome is not None
    # Only the specific action answers; the generic fallback stays silent.
    assert outcome.action == "specific"


def test_fallback_action_still_answers_when_it_is_the_only_match():
    _register("specific", "bao cao")
    _register("generic", "tra cuu", fallback=True)
    outcome = chat_action.dispatch_multi(_request("tra cứu giúp tôi"))
    assert outcome is not None
    assert outcome.action == "generic"


def test_failing_handler_drops_only_its_own_section():
    _register("ok", "ve bieu do")
    _register("bad", "dat nguong", fail=True)
    outcome = chat_action.dispatch_multi(_request("vẽ biểu đồ và đặt ngưỡng"))
    assert outcome is not None
    assert outcome.action == "ok"
    assert "nội dung ok" in chat_action.render_outcome(outcome)


def test_legacy_match_action_still_first_hit_only():
    _register("a", "ve bieu do")
    _register("b", "dat nguong")
    hit = chat_action.match_action(_request("vẽ biểu đồ và đặt ngưỡng"))
    assert hit is not None and hit.name == "a"
