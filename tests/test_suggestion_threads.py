"""Frozen thread eval for suggestion on-thread behavior (007 T017).

Replays the 5 frozen threads from tests/fixtures/suggestion_threads/v1.json
through the same pure functions the UI uses. No model, no index, fast on i5.
"""
import json
from pathlib import Path

from aios_habit.question_suggestions import (
    contextual_followups,
    contextual_send_text,
    topic_of,
)

FIXTURE = Path(__file__).parent / "fixtures" / "suggestion_threads" / "v1.json"
FIXTURE_V2 = Path(__file__).parent / "fixtures" / "suggestion_threads" / "v2.json"


def _load_threads():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["threads"]


def _load_all_threads():
    out = []
    v1 = json.loads(FIXTURE.read_text(encoding="utf-8"))["threads"]
    for thread in v1:
        out.append((thread["thread_id"], thread["turns"], [thread["source"]]))
    v2 = json.loads(FIXTURE_V2.read_text(encoding="utf-8"))["threads"]
    for thread in v2:
        out.append((thread["thread_id"], thread["turns"], thread["sources"]))
    return out


def test_fixture_has_five_threads_fifteen_questions():
    threads = _load_threads()
    assert len(threads) == 5
    assert sum(len(t["turns"]) for t in threads) == 15
    assert all(t["source"] and len(t["turns"]) == 3 for t in threads)


def test_every_turn_keeps_topic_and_full_source():
    for thread in _load_threads():
        source = thread["source"]
        items = [{"citation_id": "[1]", "title": source}]
        for turn in thread["turns"]:
            topic = topic_of(turn)
            assert topic, f"empty topic: {turn}"
            chips = contextual_followups(items, turn)
            assert len(chips) == 3, f"need 3 chips: {turn}"
            for display, send in chips:
                assert topic in display, f"chip off thread: {display}"
                assert source in send, f"send lost full title: {send}"
                assert turn[:30] in contextual_send_text(send, turn, "")


def test_send_carries_previous_answer_head():
    thread = _load_threads()[0]
    source = thread["source"]
    items = [{"citation_id": "[1]", "title": source}]
    chips = contextual_followups(items, thread["turns"][0])
    sent = contextual_send_text(chips[0][1], thread["turns"][0], "Robot dam vao thung cu tren ke.")
    assert "Robot dam" in sent


def test_all_eight_threads_stay_on_thread():
    threads = _load_all_threads()
    assert len(threads) == 8
    assert sum(len(turns) for _tid, turns, _src in threads) == 24
    for thread_id, turns, sources in threads:
        items = [
            {"citation_id": f"[{index + 1}]", "title": source}
            for index, source in enumerate(sources)
        ]
        for turn in turns:
            topic = topic_of(turn)
            assert topic, f"empty topic: {turn}"
            chips = contextual_followups(items, turn)
            assert len(chips) == 3, f"need 3 chips: {turn}"
            for display, send in chips:
                assert topic in display, f"chip off thread {thread_id}: {display}"
                assert any(source in send for source in sources), (
                    f"send lost source {thread_id}: {send}"
                )
