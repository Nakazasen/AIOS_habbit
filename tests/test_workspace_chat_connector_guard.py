from types import SimpleNamespace

from aios_habit.workspace_chat_connector_guard import (
    connector_blocks_image_files,
    image_files_blocked_message,
    source_carries_image_payload,
    source_looks_like_image_file,
)


def test_gemini_and_router_block_images_cagent_allows():
    assert connector_blocks_image_files("gemini_web") is True
    assert connector_blocks_image_files("nakazasen_router") is True
    assert connector_blocks_image_files("cagent_api") is False


def test_image_file_metadata_is_not_a_payload():
    image = SimpleNamespace(source_type="png", title="so-do.png", text="Luồng đăng ký ST-CO")
    text = SimpleNamespace(source_type="docx", title="sop.docx", text="quy trinh")
    assert source_looks_like_image_file(image) is True
    assert source_looks_like_image_file(text) is False
    assert source_carries_image_payload(image) is False
    assert source_carries_image_payload(text) is False


def test_text_question_against_mixed_library_is_not_blocked_for_gemini():
    drawing = SimpleNamespace(source_type="png", title="so-do.png", text="chu thich ban ve")
    procedure = SimpleNamespace(source_type="pdf", title="sop.pdf", text="Luong dang ky ST-CO")
    assert image_files_blocked_message("gemini_web", (drawing, procedure)) is None
    assert image_files_blocked_message("gemini_web", (drawing,)) is None
    assert image_files_blocked_message("nakazasen_router", (procedure,)) is None


def test_image_bytes_blocked_for_gemini_not_for_cagent():
    image = SimpleNamespace(source_type="png", title="so-do.png", image_bytes=b"\x89PNG")
    text = SimpleNamespace(source_type="docx", title="sop.docx", text="sop")
    assert source_carries_image_payload(image) is True
    assert image_files_blocked_message("gemini_web", (image, text))
    assert image_files_blocked_message("nakazasen_router", (image,))
    assert image_files_blocked_message("cagent_api", (image, text)) is None
    assert image_files_blocked_message("gemini_web", (text,)) is None
