from types import SimpleNamespace

from aios_habit.workspace_chat_connector_guard import (
    connector_blocks_image_files,
    image_files_blocked_message,
    source_looks_like_image_file,
)


def test_gemini_and_router_block_images_cagent_allows():
    assert connector_blocks_image_files("gemini_web") is True
    assert connector_blocks_image_files("nakazasen_router") is True
    assert connector_blocks_image_files("cagent_api") is False


def test_image_source_blocked_for_gemini_not_for_cagent():
    image = SimpleNamespace(source_type="png", title="so-do.png")
    text = SimpleNamespace(source_type="docx", title="sop.docx")
    assert source_looks_like_image_file(image) is True
    assert source_looks_like_image_file(text) is False
    assert image_files_blocked_message("gemini_web", (image, text))
    assert image_files_blocked_message("nakazasen_router", (image,))
    assert image_files_blocked_message("cagent_api", (image, text)) is None
    assert image_files_blocked_message("gemini_web", (text,)) is None
