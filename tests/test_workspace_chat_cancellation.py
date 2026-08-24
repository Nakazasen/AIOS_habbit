"""Cancellation contract for a Workspace Chat provider request."""

from threading import Event

from aios_habit.antigravity_bridge import route_workspace_chat_submission


def test_cancelled_request_does_not_contact_or_persist_a_provider_response() -> None:
    cancellation_event = Event()
    cancellation_event.set()

    ok, success_message, badge, error_message = route_workspace_chat_submission(
        question="Should not be sent",
        evidence_items=[],
        packed_sources=(),
        conversation_id="conv-cancelled",
        notebook_id="nb-cancelled",
        retrieval_applied=False,
        retrieved_sources=(),
        retrieval_summary="",
        current_keys=(),
        chat_history=(),
        user_raw_input="Should not be sent",
        cancellation_event=cancellation_event,
    )

    assert ok is False
    assert success_message == ""
    assert badge is None
    assert error_message == "Đã dừng yêu cầu AI."
