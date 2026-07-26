import socket
from pathlib import Path
import pytest
from dataclasses import dataclass
from aios_habit.workspace_chat_ai_answer import (
    PRIVACY_MODE_LOCAL_PREVIEW_ONLY,
    PRIVACY_MODE_CLOUD_ALLOWED,
    MAX_CONTEXT_CHARS_PER_SOURCE,
    MAX_CONTEXT_CHARS_TOTAL,
    MAX_CONTEXT_SOURCES,
    MAX_QUESTION_CHARS,
    WorkspaceAIContextSource,
    WorkspaceAIAnswerRequest,
    WorkspaceAIAnswerResult,
    WorkspaceAIProviderClient,
    is_privacy_label_cloud_allowed,
    pack_workspace_ai_context,
    build_workspace_ai_prompt,
    classify_workspace_ai_outcome,
    generate_workspace_ai_answer,
    _cap_and_pack_sources
)

# Mock classes for NotebookSource and TemporaryConversationSource
@dataclass
class MockNotebookSource:
    id: str
    notebook_id: str
    title: str
    source_type: str
    content_preview: str
    content_text: str
    privacy_label: str = "machine_only"

@dataclass
class MockTemporarySource:
    id: str
    conversation_id: str
    title: str
    source_type: str
    content_preview: str
    content_text: str
    privacy_label: str = "machine_only"

@dataclass
class MockSelection:
    source_id: str
    source_scope: str

class MockProviderClient:
    def __init__(self, response_text="Mock AI response", raise_error=False):
        self.response_text = response_text
        self.raise_error = raise_error
        self.call_count = 0
        self.last_system_prompt = None
        self.last_user_prompt = None

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        self.call_count += 1
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        if self.raise_error:
            raise RuntimeError("Fake connection error")
        return self.response_text

@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    def fail_socket(*args, **kwargs):
        raise RuntimeError("Network calls are forbidden during testing!")
    monkeypatch.setattr(socket, "socket", fail_socket)

def test_is_privacy_label_cloud_allowed():
    assert is_privacy_label_cloud_allowed("machine_only") is True
    assert is_privacy_label_cloud_allowed("cloud_allowed") is True
    assert is_privacy_label_cloud_allowed("local_only") is False
    assert is_privacy_label_cloud_allowed("confidential") is False
    assert is_privacy_label_cloud_allowed("unknown") is False
    assert is_privacy_label_cloud_allowed("") is False
    assert is_privacy_label_cloud_allowed(None) is False

def test_pack_workspace_ai_context_basic():
    ns = [MockNotebookSource("ns_1", "nb_1", "NS Title", "xlsx", "ns preview", "ns text")]
    ts = [MockTemporarySource("ts_1", "conv_1", "TS Title", "text", "ts preview", "ts text")]
    selections = [
        MockSelection("ns_1", "notebook"),
        MockSelection("ts_1", "temporary")
    ]
    q, sources, warnings = pack_workspace_ai_context("Hỏi", ns, ts, selections)
    assert q == "Hỏi"
    assert len(sources) == 2
    assert sources[0].source_id == "ns_1"
    assert sources[0].source_scope == "notebook"
    assert sources[1].source_id == "ts_1"
    assert sources[1].source_scope == "temporary"
    assert len(warnings) == 0

def test_pack_workspace_ai_context_caps_per_source():
    ns = [MockNotebookSource("ns_1", "nb_1", "NS Title", "text", "", "A" * (MAX_CONTEXT_CHARS_PER_SOURCE + 100))]
    selections = [MockSelection("ns_1", "notebook")]
    q, sources, warnings = pack_workspace_ai_context("Hỏi", ns, [], selections)
    q, sources, warnings = _cap_and_pack_sources(q, sources)
    assert len(sources) == 1
    assert sources[0].included_chars == MAX_CONTEXT_CHARS_PER_SOURCE
    assert sources[0].truncated is True
    assert any("rút gọn" in w for w in warnings)

def test_pack_workspace_ai_context_caps_total():
    ns = [
        MockNotebookSource("ns_1", "nb_1", "NS 1", "text", "", "A" * 3000),
        MockNotebookSource("ns_2", "nb_1", "NS 2", "text", "", "B" * 3500)
    ]
    selections = [
        MockSelection("ns_1", "notebook"),
        MockSelection("ns_2", "notebook")
    ]
    q, sources, warnings = pack_workspace_ai_context("Hỏi", ns, [], selections)
    q, sources, warnings = _cap_and_pack_sources(q, sources)
    assert len(sources) == 2
    assert sources[0].included_chars == 3000
    assert sources[0].truncated is False
    assert sources[1].included_chars == 3500
    assert sources[1].truncated is False

    # Test total cap: sum of multiple sources exceeds 20000
    ns_many = [MockNotebookSource(f"ns_{i}", "nb_1", f"NS {i}", "text", "", "A" * 4000) for i in range(6)]
    selections_many = [MockSelection(f"ns_{i}", "notebook") for i in range(6)]
    q, sources_many, warnings_many = pack_workspace_ai_context("Hỏi", ns_many, [], selections_many)
    q, sources_many, warnings_many = _cap_and_pack_sources(q, sources_many)
    assert sources_many[0].included_chars == 4000
    assert sources_many[4].included_chars == 4000
    assert sources_many[5].included_chars == 0
    assert sources_many[5].truncated is True
    assert any("rút gọn" in w for w in warnings_many)

def test_pack_workspace_ai_context_caps_source_count():
    ns = [MockNotebookSource(f"ns_{i}", "nb_1", f"NS {i}", "text", "", "A") for i in range(MAX_CONTEXT_SOURCES + 5)]
    selections = [MockSelection(f"ns_{i}", "notebook") for i in range(MAX_CONTEXT_SOURCES + 5)]
    q, sources, warnings = pack_workspace_ai_context("Hỏi", ns, [], selections)
    q, sources, warnings = _cap_and_pack_sources(q, sources)
    assert len(sources) == MAX_CONTEXT_SOURCES
    assert any("rút gọn" in w for w in warnings)

def test_pack_workspace_ai_context_question_cap():
    q_long = "Q" * (MAX_QUESTION_CHARS + 100)
    q, sources, warnings = pack_workspace_ai_context(q_long, [], [], [])
    q, sources, warnings = _cap_and_pack_sources(q, sources)
    assert len(q) == MAX_QUESTION_CHARS
    assert len(warnings) == 1
    assert "rút gọn" in warnings[0]

def test_pack_workspace_ai_context_text_preferred_and_preview_fallback():
    ns = [
        MockNotebookSource("ns_1", "nb_1", "NS 1", "text", "Preview content", "Text content"),
        MockNotebookSource("ns_2", "nb_1", "NS 2", "text", "Preview only", "")
    ]
    selections = [
        MockSelection("ns_1", "notebook"),
        MockSelection("ns_2", "notebook")
    ]
    q, sources, warnings = pack_workspace_ai_context("Hỏi", ns, [], selections)
    assert sources[0].text == "Text content"
    assert sources[1].text == "Preview only"

def test_pack_workspace_ai_context_empty_content_warning():
    ns = [MockNotebookSource("ns_1", "nb_1", "NS 1", "text", "", "")]
    selections = [MockSelection("ns_1", "notebook")]
    q, sources, warnings = pack_workspace_ai_context("Hỏi", ns, [], selections)
    q, sources, warnings = _cap_and_pack_sources(q, sources)
    assert len(warnings) == 1
    assert "không có nội dung" in warnings[0]

def test_pack_workspace_ai_context_unicode_preserved():
    ns = [MockNotebookSource("ns_1", "nb_1", "日本語 và Tiếng Việt", "text", "", "Nội dung 日本語")]
    selections = [MockSelection("ns_1", "notebook")]
    q, sources, warnings = pack_workspace_ai_context("質問?", ns, [], selections)
    assert q == "質問?"
    assert sources[0].title == "日本語 và Tiếng Việt"
    assert sources[0].text == "Nội dung 日本語"

def test_build_workspace_ai_prompt_format():
    srcs = (
        WorkspaceAIContextSource("ns_1", "notebook", "xlsx", "Excel Source", "machine_only", "Row 1\nRow 2", 11, False),
        WorkspaceAIContextSource("ts_1", "temporary", "text", "Temp Source", "cloud_allowed", "Text content", 12, False)
    )
    system_prompt, user_prompt = build_workspace_ai_prompt("Hỏi câu hỏi", srcs)
    assert "Bạn là trợ lý AI trong Workspace Chat." in system_prompt
    assert "CÂU HỎI:\nHỏi câu hỏi" in user_prompt
    assert "NGUỒN 1\nTiêu đề: Excel Source\nLoại: Excel" in user_prompt
    assert "NGUỒN 2\nTiêu đề: Temp Source\nLoại: Văn bản" in user_prompt
    assert "<<<SOURCE_CONTENT\nRow 1\nRow 2\nSOURCE_CONTENT" in user_prompt
    assert "<<<SOURCE_CONTENT\nText content\nSOURCE_CONTENT" in user_prompt
    # Technical IDs, scope, privacy enums must NOT be leaked in the prompts
    assert "ns_1" not in user_prompt
    assert "ts_1" not in user_prompt
    assert "notebook" not in user_prompt
    assert "temporary" not in user_prompt
    assert "machine_only" not in user_prompt
    assert "cloud_allowed" not in user_prompt

def test_generate_workspace_ai_answer_local_preview_only():
    client = MockProviderClient()
    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Hỏi",
        context_sources=(),
        privacy_mode=PRIVACY_MODE_LOCAL_PREVIEW_ONLY
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert res.externally_sent is False
    assert client.call_count == 0
    assert "Chỉ xem trước trên máy" in res.error_message

def test_generate_workspace_ai_answer_cloud_no_consent():
    client = MockProviderClient()
    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Hỏi",
        context_sources=(),
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        cloud_consent_confirmed=False
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert res.externally_sent is False
    assert client.call_count == 0
    assert "bạn chưa xác nhận" in res.error_message

def test_generate_workspace_ai_answer_cloud_fingerprint_mismatch():
    client = MockProviderClient()
    srcs = (WorkspaceAIContextSource("ns_1", "notebook", "xlsx", "Title", "machine_only", "Text", 4, False),)
    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Hỏi",
        context_sources=srcs,
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        cloud_consent_confirmed=True,
        consent_source_keys=(("notebook", "ns_different"),)
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert res.externally_sent is False
    assert client.call_count == 0
    assert "Tập nguồn đang bật đã thay đổi" in res.error_message

def test_generate_workspace_ai_answer_cloud_privacy_block_local_only():
    client = MockProviderClient()
    srcs = (WorkspaceAIContextSource("ns_1", "notebook", "xlsx", "Title", "local_only", "Text", 4, False),)
    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Hỏi",
        context_sources=srcs,
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        cloud_consent_confirmed=True,
        consent_source_keys=(("notebook", "ns_1"),)
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert res.externally_sent is False
    assert client.call_count == 0
    assert "chỉ được dùng trên máy" in res.error_message

def test_generate_workspace_ai_answer_cloud_privacy_block_confidential():
    client = MockProviderClient()
    srcs = (WorkspaceAIContextSource("ns_1", "notebook", "xlsx", "Title", "confidential", "Text", 4, False),)
    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Hỏi",
        context_sources=srcs,
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        cloud_consent_confirmed=True,
        consent_source_keys=(("notebook", "ns_1"),)
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert res.externally_sent is False
    assert client.call_count == 0
    assert "chỉ được dùng trên máy" in res.error_message

def test_generate_workspace_ai_answer_cloud_privacy_block_unknown():
    client = MockProviderClient()
    srcs = (WorkspaceAIContextSource("ns_1", "notebook", "xlsx", "Title", "unknown", "Text", 4, False),)
    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Hỏi",
        context_sources=srcs,
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        cloud_consent_confirmed=True,
        consent_source_keys=(("notebook", "ns_1"),)
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert res.externally_sent is False
    assert client.call_count == 0
    assert "chỉ được dùng trên máy" in res.error_message

def test_generate_workspace_ai_answer_cloud_empty_question():
    client = MockProviderClient()
    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="   ",
        context_sources=(),
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        cloud_consent_confirmed=True,
        consent_source_keys=()
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert res.externally_sent is False
    assert res.provider_success is False
    assert res.provider_completion_status == "not_requested"
    assert res.grounding_status == "not_assessed"
    assert res.outcome_status == "not_requested"
    assert client.call_count == 0
    assert "không được rỗng" in res.error_message

def test_generate_workspace_ai_answer_success():
    client = MockProviderClient("Phản hồi AI")
    srcs = (
        WorkspaceAIContextSource("ns_1", "notebook", "xlsx", "Sổ 1", "machine_only", "Text", 4, False),
        WorkspaceAIContextSource("ts_1", "temporary", "text", "Tạm 1", "cloud_allowed", "Text", 4, False)
    )
    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Hỏi",
        context_sources=srcs,
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        cloud_consent_confirmed=True,
        consent_source_keys=(("notebook", "ns_1"), ("temporary", "ts_1"))
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is True
    assert res.externally_sent is True
    assert client.call_count == 1
    assert "Phản hồi AI" in res.answer_text
    assert "Đây là câu trả lời do AI tạo, cần kiểm tra lại trước khi dùng." in res.answer_text
    assert res.included_source_titles == ("Sổ 1", "Tạm 1")

def test_generate_workspace_ai_answer_empty_provider_response():
    client = MockProviderClient("")
    srcs = (WorkspaceAIContextSource("ns_1", "notebook", "xlsx", "Sổ 1", "machine_only", "Text", 4, False),)
    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Hỏi",
        context_sources=srcs,
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        cloud_consent_confirmed=True,
        consent_source_keys=(("notebook", "ns_1"),)
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert res.externally_sent is True
    assert client.call_count == 1
    assert "Dịch vụ AI phản hồi rỗng." in res.error_message

def test_generate_workspace_ai_answer_provider_exception():
    client = MockProviderClient(raise_error=True)
    srcs = (WorkspaceAIContextSource("ns_1", "notebook", "xlsx", "Sổ 1", "machine_only", "Text", 4, False),)
    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Hỏi",
        context_sources=srcs,
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        cloud_consent_confirmed=True,
        consent_source_keys=(("notebook", "ns_1"),)
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert res.externally_sent is True
    assert res.provider_success is False
    assert res.provider_completion_status == "failed"
    assert res.grounding_status == "not_assessed_provider_failure"
    assert res.outcome_status == "provider_error"
    assert client.call_count == 1
    assert "Dịch vụ AI chưa phản hồi. Nội dung nguồn vẫn được giữ trong Workspace Chat; vui lòng thử lại sau." in res.error_message
    assert "Fake connection error" not in res.error_message  # no raw details leaked


def test_block_entire_request_on_one_blocked_source():
    # 9. Một source bị block thì block toàn request
    client = MockProviderClient()
    srcs = (
        WorkspaceAIContextSource("ns_1", "notebook", "xlsx", "Machine Only", "machine_only", "Text", 4, False),
        WorkspaceAIContextSource("ns_2", "notebook", "xlsx", "Local Only", "local_only", "Text", 4, False)
    )
    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Hỏi",
        context_sources=srcs,
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        cloud_consent_confirmed=True,
        consent_source_keys=(("notebook", "ns_1"), ("notebook", "ns_2"))
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert client.call_count == 0
    assert "chỉ được dùng trên máy" in res.error_message


def test_disabled_and_orphan_sources_excluded_during_packing():
    # 12. disabled/orphan/cross-scope excluded
    ns = [
        MockNotebookSource("ns_enabled", "nb_1", "NS Enabled", "xlsx", "prev", "text"),
        MockNotebookSource("ns_disabled", "nb_1", "NS Disabled", "xlsx", "prev", "text")
    ]
    ts = [
        MockTemporarySource("ts_enabled", "conv_1", "TS Enabled", "text", "prev", "text"),
        MockTemporarySource("ts_disabled", "conv_1", "TS Disabled", "text", "prev", "text")
    ]
    selections = [
        MockSelection("ns_enabled", "notebook"),
        MockSelection("ts_enabled", "temporary"),
        # orphan / cross-scope selection
        MockSelection("ts_orphan", "temporary")
    ]
    q, sources, warnings = pack_workspace_ai_context("Hỏi", ns, ts, selections)
    source_ids = {src.source_id for src in sources}
    assert "ns_enabled" in source_ids
    assert "ts_enabled" in source_ids
    assert "ns_disabled" not in source_ids
    assert "ts_disabled" not in source_ids
    assert "ts_orphan" not in source_ids


def test_xlsx_no_reparse_during_packing(monkeypatch):
    # 16. xlsx uses persisted text/preview, no reparse
    import aios_habit.workspace_chat_excel as excel
    def fail(*args, **kwargs):
        raise AssertionError("Excel reparse must not happen")
    monkeypatch.setattr(excel, "extract_xlsx_text", fail)

    ns = [MockNotebookSource("ns_1", "nb_1", "NS 1", "xlsx", "Preview text", "Text content")]
    selections = [MockSelection("ns_1", "notebook")]
    q, sources, warnings = pack_workspace_ai_context("Hỏi", ns, [], selections)
    assert sources[0].text == "Text content"


def test_no_citation_markers_generated():
    # 32. no citation markers generated
    srcs = (WorkspaceAIContextSource("ns_1", "notebook", "xlsx", "Sổ 1", "machine_only", "Text", 4, False),)
    # The client response could have citations, let's verify generate_workspace_ai_answer does not produce any citations or brackets
    client = MockProviderClient("Phản hồi AI")
    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Hỏi",
        context_sources=srcs,
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        cloud_consent_confirmed=True,
        consent_source_keys=(("notebook", "ns_1"),)
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is True
    # Verify no citation marker style in answer text
    assert "[" not in res.answer_text
    assert "]" not in res.answer_text
    assert "trích dẫn" not in res.answer_text.lower()


def test_app_imports_no_case_cockpit():
    # 42. no Case Cockpit import
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    assert "case_cockpit" not in app_source
    assert "case_ingest" not in app_source
    assert "case_store" not in app_source


def test_app_no_xlsx_reparse_in_ai_path():
    # 43. no .xlsx reparse in app AI path
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    # Phase 2H: AI-first flow uses ask_submitted pattern
    assert "extract_xlsx_text" not in app_source[app_source.find("if ask_submitted"):app_source.find("# Phase 2H: Dán nhanh")]


def _build_request_through_packer(
    question: str,
    notebook_sources: list,
    temporary_sources: list,
    enabled_selections: list,
    privacy_mode: str = PRIVACY_MODE_CLOUD_ALLOWED,
    cloud_consent_confirmed: bool = True,
    consent_source_keys: tuple = ()
) -> WorkspaceAIAnswerRequest:
    q_text, packed_sources, warnings = pack_workspace_ai_context(
        question, notebook_sources, temporary_sources, enabled_selections
    )
    return WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question=q_text,
        context_sources=packed_sources,
        privacy_mode=privacy_mode,
        cloud_consent_confirmed=cloud_consent_confirmed,
        consent_source_keys=consent_source_keys
    )


def test_regression_blocked_source_after_cap():
    # 9.1 Blocked source after cap
    client = MockProviderClient()
    ns_sources = []
    selections = []
    # 20 allowed sources
    for i in range(20):
        ns_sources.append(MockNotebookSource(f"ns_{i}", "nb_1", f"Sổ {i}", "xlsx", "prev", "Text"))
        selections.append(MockSelection(f"ns_{i}", "notebook"))
    # 21st source is local_only (blocked)
    ns_sources.append(MockNotebookSource("ns_20", "nb_1", "Sổ 20", "xlsx", "prev", "Text", "local_only"))
    selections.append(MockSelection("ns_20", "notebook"))

    consent_keys = tuple(("notebook", f"ns_{i}") for i in range(21))
    req = _build_request_through_packer(
        question="Hỏi",
        notebook_sources=ns_sources,
        temporary_sources=[],
        enabled_selections=selections,
        consent_source_keys=consent_keys
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert client.call_count == 0
    assert res.externally_sent is False
    assert "chỉ được dùng trên máy" in res.error_message


def test_regression_unknown_blocked_after_cap():
    # 9.2 Unknown/blank blocked after cap
    client = MockProviderClient()
    ns_sources = []
    selections = []
    # 20 allowed sources
    for i in range(20):
        ns_sources.append(MockNotebookSource(f"ns_{i}", "nb_1", f"Sổ {i}", "xlsx", "prev", "Text"))
        selections.append(MockSelection(f"ns_{i}", "notebook"))
    # 21st source is unknown
    ns_sources.append(MockNotebookSource("ns_20", "nb_1", "Sổ 20", "xlsx", "prev", "Text", "unknown"))
    selections.append(MockSelection("ns_20", "notebook"))

    consent_keys = tuple(("notebook", f"ns_{i}") for i in range(21))
    req = _build_request_through_packer(
        question="Hỏi",
        notebook_sources=ns_sources,
        temporary_sources=[],
        enabled_selections=selections,
        consent_source_keys=consent_keys
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert client.call_count == 0
    assert res.externally_sent is False
    assert "chỉ được dùng trên máy" in res.error_message


def test_regression_invalid_privacy_mode():
    # 9.3 Invalid privacy mode
    client = MockProviderClient()
    ns_sources = [MockNotebookSource("ns_1", "nb_1", "Sổ 1", "xlsx", "prev", "Text")]
    selections = [MockSelection("ns_1", "notebook")]
    req = _build_request_through_packer(
        question="Hỏi",
        notebook_sources=ns_sources,
        temporary_sources=[],
        enabled_selections=selections,
        privacy_mode="unexpected_mode",
        consent_source_keys=(("notebook", "ns_1"),)
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert client.call_count == 0
    assert res.externally_sent is False
    assert "Chế độ trả lời chưa hợp lệ" in res.error_message


def test_regression_consent_snapshot_mismatch():
    # 9.4 Consent snapshot mismatch
    client = MockProviderClient()
    ns_sources = [MockNotebookSource("ns_1", "nb_1", "Sổ 1", "xlsx", "prev", "Text")]
    selections = [MockSelection("ns_1", "notebook")]
    req = _build_request_through_packer(
        question="Hỏi",
        notebook_sources=ns_sources,
        temporary_sources=[],
        enabled_selections=selections,
        consent_source_keys=(("notebook", "ns_different"),)
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert client.call_count == 0
    assert res.externally_sent is False
    assert "Tập nguồn đang bật đã thay đổi" in res.error_message


def test_regression_do_not_use_packed_keys_as_consent():
    # 9.5 Do not use packed keys as consent snapshot
    client = MockProviderClient()
    ns_sources = []
    selections = []
    # 21 allowed sources
    for i in range(21):
        ns_sources.append(MockNotebookSource(f"ns_{i}", "nb_1", f"Sổ {i}", "xlsx", "prev", "Text"))
        selections.append(MockSelection(f"ns_{i}", "notebook"))
    # Consent only for the first 20 sources (packed list)
    consent_keys = tuple(("notebook", f"ns_{i}") for i in range(20))
    req = _build_request_through_packer(
        question="Hỏi",
        notebook_sources=ns_sources,
        temporary_sources=[],
        enabled_selections=selections,
        consent_source_keys=consent_keys
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert client.call_count == 0
    assert res.externally_sent is False
    assert "Tập nguồn đang bật đã thay đổi" in res.error_message


def test_regression_warnings_propagate():
    # 9.6 Warnings propagate
    client = MockProviderClient("AI Response")
    # Trigger truncation warning by exceeding MAX_CONTEXT_CHARS_PER_SOURCE = 4_000
    ns_sources = [MockNotebookSource("ns_1", "nb_1", "Sổ 1", "xlsx", "prev", "A" * 5000)]
    selections = [MockSelection("ns_1", "notebook")]
    req = _build_request_through_packer(
        question="Hỏi",
        notebook_sources=ns_sources,
        temporary_sources=[],
        enabled_selections=selections,
        consent_source_keys=(("notebook", "ns_1"),)
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is True
    assert len(res.warnings) > 0
    assert any("rút gọn" in w for w in res.warnings)


def test_regression_empty_source_excluded():
    # 9.7 Empty source excluded from prompt
    client = MockProviderClient("AI Response")
    ns_sources = [MockNotebookSource("ns_1", "nb_1", "Sổ 1", "xlsx", "", "")]
    ts_sources = [MockTemporarySource("ts_1", "conv_1", "Tạm 1", "text", "prev", "Valid text")]
    selections = [
        MockSelection("ns_1", "notebook"),
        MockSelection("ts_1", "temporary")
    ]
    req = _build_request_through_packer(
        question="Hỏi",
        notebook_sources=ns_sources,
        temporary_sources=ts_sources,
        enabled_selections=selections,
        consent_source_keys=(("notebook", "ns_1"), ("temporary", "ts_1"))
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is True
    assert "Sổ 1" not in client.last_user_prompt
    assert "Tạm 1" in client.last_user_prompt
    assert any("không có nội dung" in w for w in res.warnings)

    # If all sources empty, must not call provider and externally_sent must be False
    ns_sources_empty = [MockNotebookSource("ns_1", "nb_1", "Sổ 1", "xlsx", "", "")]
    selections_empty = [MockSelection("ns_1", "notebook")]
    req_empty = _build_request_through_packer(
        question="Hỏi",
        notebook_sources=ns_sources_empty,
        temporary_sources=[],
        enabled_selections=selections_empty,
        consent_source_keys=(("notebook", "ns_1"),)
    )
    client_empty = MockProviderClient()
    res_empty = generate_workspace_ai_answer(req_empty, client_empty)
    assert res_empty.ok is False
    assert client_empty.call_count == 0
    assert res_empty.externally_sent is False
    assert "chưa có nội dung" in res_empty.error_message


def test_regression_provider_exception_sanitization():
    # 9.8 Provider exception sanitization
    ns_sources = [MockNotebookSource("ns_1", "nb_1", "Sổ 1", "xlsx", "prev", "Text")]
    selections = [MockSelection("ns_1", "notebook")]

    # 1. Unconfigured error
    class MockUnconfiguredClient:
        def generate(self, *, system_prompt: str, user_prompt: str) -> str:
            raise RuntimeError("chưa được cấu hình SECRET_TOKEN=abc")

    req = _build_request_through_packer(
        question="Hỏi",
        notebook_sources=ns_sources,
        temporary_sources=[],
        enabled_selections=selections,
        consent_source_keys=(("notebook", "ns_1"),)
    )
    res = generate_workspace_ai_answer(req, MockUnconfiguredClient())
    assert res.ok is False
    assert "SECRET_TOKEN" not in res.error_message
    assert "chưa được cấu hình" in res.error_message
    assert "Chưa gửi tới AI. AI chưa được cấu hình." == res.error_message

    # 2. Other error
    class MockOtherErrorClient:
        def generate(self, *, system_prompt: str, user_prompt: str) -> str:
            raise RuntimeError("some sensitive internal server error details")

    res2 = generate_workspace_ai_answer(req, MockOtherErrorClient())
    assert res2.ok is False
    assert "sensitive" not in res2.error_message
    assert "Dịch vụ AI chưa phản hồi. Nội dung nguồn vẫn được giữ trong Workspace Chat; vui lòng thử lại sau." == res2.error_message


def test_regression_blank_privacy_label_blocks_cloud():
    client = MockProviderClient()
    ns_sources = [MockNotebookSource("ns_1", "nb_1", "Sổ 1", "xlsx", "prev", "Text", "")]
    selections = [MockSelection("ns_1", "notebook")]
    req = _build_request_through_packer(
        question="Hỏi",
        notebook_sources=ns_sources,
        temporary_sources=[],
        enabled_selections=selections,
        consent_source_keys=(("notebook", "ns_1"),)
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert client.call_count == 0
    assert res.externally_sent is False
    assert "chỉ được dùng trên máy" in res.error_message


def test_regression_whitespace_privacy_label_blocks_cloud():
    client = MockProviderClient()
    ns_sources = [MockNotebookSource("ns_1", "nb_1", "Sổ 1", "xlsx", "prev", "Text", "   ")]
    selections = [MockSelection("ns_1", "notebook")]
    req = _build_request_through_packer(
        question="Hỏi",
        notebook_sources=ns_sources,
        temporary_sources=[],
        enabled_selections=selections,
        consent_source_keys=(("notebook", "ns_1"),)
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert client.call_count == 0
    assert res.externally_sent is False
    assert "chỉ được dùng trên máy" in res.error_message


def test_regression_unknown_privacy_label_blocks_cloud():
    client = MockProviderClient()
    ns_sources = [MockNotebookSource("ns_1", "nb_1", "Sổ 1", "xlsx", "prev", "Text", "public")]
    selections = [MockSelection("ns_1", "notebook")]
    req = _build_request_through_packer(
        question="Hỏi",
        notebook_sources=ns_sources,
        temporary_sources=[],
        enabled_selections=selections,
        consent_source_keys=(("notebook", "ns_1"),)
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert client.call_count == 0
    assert res.externally_sent is False
    assert "chỉ được dùng trên máy" in res.error_message


def test_regression_none_privacy_label_blocks_cloud():
    client = MockProviderClient()
    ns_sources = [MockNotebookSource("ns_1", "nb_1", "Sổ 1", "xlsx", "prev", "Text", None)]
    selections = [MockSelection("ns_1", "notebook")]
    req = _build_request_through_packer(
        question="Hỏi",
        notebook_sources=ns_sources,
        temporary_sources=[],
        enabled_selections=selections,
        consent_source_keys=(("notebook", "ns_1"),)
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert client.call_count == 0
    assert res.externally_sent is False
    assert "chỉ được dùng trên máy" in res.error_message


def test_regression_blank_source_after_cap_blocks_cloud():
    # 20 allowed sources + 21st source has blank label
    client = MockProviderClient()
    ns_sources = []
    selections = []
    for i in range(20):
        ns_sources.append(MockNotebookSource(f"ns_{i}", "nb_1", f"Sổ {i}", "xlsx", "prev", "Text"))
        selections.append(MockSelection(f"ns_{i}", "notebook"))
    ns_sources.append(MockNotebookSource("ns_20", "nb_1", "Sổ 20", "xlsx", "prev", "Text", ""))
    selections.append(MockSelection("ns_20", "notebook"))

    consent_keys = tuple(("notebook", f"ns_{i}") for i in range(21))
    req = _build_request_through_packer(
        question="Hỏi",
        notebook_sources=ns_sources,
        temporary_sources=[],
        enabled_selections=selections,
        consent_source_keys=consent_keys
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert client.call_count == 0
    assert res.externally_sent is False
    assert "chỉ được dùng trên máy" in res.error_message


def test_regression_whitespace_source_after_cap_blocks_cloud_through_real_packer():
    # 20 allowed sources + 21st source has whitespace label
    client = MockProviderClient()
    ns_sources = []
    selections = []
    for i in range(20):
        ns_sources.append(MockNotebookSource(f"ns_{i}", "nb_1", f"Sổ {i}", "xlsx", "prev", "Text"))
        selections.append(MockSelection(f"ns_{i}", "notebook"))
    ns_sources.append(MockNotebookSource("ns_20", "nb_1", "Sổ 20", "xlsx", "prev", "Text", "   "))
    selections.append(MockSelection("ns_20", "notebook"))

    consent_keys = tuple(("notebook", f"ns_{i}") for i in range(21))
    req = _build_request_through_packer(
        question="Hỏi",
        notebook_sources=ns_sources,
        temporary_sources=[],
        enabled_selections=selections,
        consent_source_keys=consent_keys
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert client.call_count == 0
    assert res.externally_sent is False
    assert "chỉ được dùng trên máy" in res.error_message


def test_regression_none_source_after_cap_blocks_cloud_through_real_packer():
    # 20 allowed sources + 21st source has None label
    client = MockProviderClient()
    ns_sources = []
    selections = []
    for i in range(20):
        ns_sources.append(MockNotebookSource(f"ns_{i}", "nb_1", f"Sổ {i}", "xlsx", "prev", "Text"))
        selections.append(MockSelection(f"ns_{i}", "notebook"))
    ns_sources.append(MockNotebookSource("ns_20", "nb_1", "Sổ 20", "xlsx", "prev", "Text", None))
    selections.append(MockSelection("ns_20", "notebook"))

    consent_keys = tuple(("notebook", f"ns_{i}") for i in range(21))
    req = _build_request_through_packer(
        question="Hỏi",
        notebook_sources=ns_sources,
        temporary_sources=[],
        enabled_selections=selections,
        consent_source_keys=consent_keys
    )
    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert client.call_count == 0
    assert res.externally_sent is False
    assert "chỉ được dùng trên máy" in res.error_message


def test_generate_workspace_ai_answer_with_retrieval():
    client = MockProviderClient()
    # 1. full enabled context sources (snapshot)
    src_full = WorkspaceAIContextSource(
        source_id="src_1",
        source_scope="temporary",
        source_type="txt",
        title="raw_doc.txt",
        privacy_label="cloud_allowed",
        text="Irrelevant raw content not retrieved",
        included_chars=36,
        truncated=False,
    )
    # 2. retrieved snippet sources (subset)
    src_retrieved = WorkspaceAIContextSource(
        source_id="src_1_chunk_1",
        source_scope="temporary",
        source_type="txt",
        title="raw_doc.txt",
        privacy_label="cloud_allowed",
        text="Hello retrieval snippet content!",
        included_chars=32,
        truncated=False,
    )

    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Hỏi",
        context_sources=(src_full,),
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        cloud_consent_confirmed=True,
        consent_source_keys=(("temporary", "src_1"),),
        retrieval_applied=True,
        retrieved_context_sources=(src_retrieved,),
    )

    res = generate_workspace_ai_answer(req, client)
    assert res.ok is True
    assert client.call_count == 1
    assert "Hello retrieval snippet content!" in client.last_user_prompt
    assert "Irrelevant raw content" not in client.last_user_prompt


def test_generate_workspace_ai_answer_with_retrieval_no_evidence():
    client = MockProviderClient()
    src_full = WorkspaceAIContextSource(
        source_id="src_1",
        source_scope="temporary",
        source_type="txt",
        title="doc.txt",
        privacy_label="cloud_allowed",
        text="Some context text",
        included_chars=17,
        truncated=False,
    )

    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Hỏi",
        context_sources=(src_full,),
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        cloud_consent_confirmed=True,
        consent_source_keys=(("temporary", "src_1"),),
        retrieval_applied=True,
        retrieved_context_sources=(),  # No evidence
    )

    res = generate_workspace_ai_answer(req, client)
    assert res.ok is False
    assert client.call_count == 0
    assert res.error_message == "Chưa tìm thấy đoạn phù hợp trong nguồn đang bật."


def test_generate_workspace_ai_answer_with_retrieval_privacy_and_consent_full_snapshot():
    client = MockProviderClient()
    # Retrieved snippet belongs to a cloud_allowed source
    src_retrieved = WorkspaceAIContextSource(
        source_id="src_allowed_chunk_1",
        source_scope="temporary",
        source_type="txt",
        title="allowed.txt",
        privacy_label="cloud_allowed",
        text="Allowed snippet text",
        included_chars=20,
        truncated=False,
    )
    # But one of the enabled sources in the full snapshot is local_only!
    src_allowed = WorkspaceAIContextSource(
        source_id="src_allowed",
        source_scope="temporary",
        source_type="txt",
        title="allowed.txt",
        privacy_label="cloud_allowed",
        text="Allowed raw content",
        included_chars=19,
        truncated=False,
    )
    src_local = WorkspaceAIContextSource(
        source_id="src_local",
        source_scope="temporary",
        source_type="txt",
        title="local.txt",
        privacy_label="local_only",  # local_only blocker!
        text="Secret local only text",
        included_chars=22,
        truncated=False,
    )

    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Hỏi",
        context_sources=(src_allowed, src_local),
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        cloud_consent_confirmed=True,
        consent_source_keys=(("temporary", "src_allowed"), ("temporary", "src_local")),
        retrieval_applied=True,
        retrieved_context_sources=(src_retrieved,),
    )

    res = generate_workspace_ai_answer(req, client)
    # Must be blocked by the local_only source in full snapshot
    assert res.ok is False
    assert client.call_count == 0
    assert "chỉ được dùng trên máy" in res.error_message


def test_workspace_chat_ai_answer_via_real_router_success(monkeypatch):
    called = []
    def mock_generate(payload):
        called.append(payload)
        return True, "Mocked Router Reply"
    monkeypatch.setattr("aios_habit.workspace_chat_router_adapter.generate_answer_via_router", mock_generate)

    src = WorkspaceAIContextSource(
        source_id="src_safe",
        source_scope="temporary",
        source_type="txt",
        title="safe.txt",
        privacy_label="cloud_safe",
        text="Public safe text",
        included_chars=16,
        truncated=False,
    )

    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Hỏi",
        context_sources=(src,),
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        cloud_consent_confirmed=True,
        consent_source_keys=(("temporary", "src_safe"),),
        real_router_enabled=True
    )

    client = MockProviderClient()
    res = generate_workspace_ai_answer(req, client)

    assert res.ok is True
    assert "Mocked Router Reply" in res.answer_text
    assert "Đây là câu trả lời do AI tạo, cần kiểm tra lại trước khi dùng." in res.answer_text
    assert res.included_source_titles == ("safe.txt",)
    assert len(called) == 1
    assert called[0].sanitized_question == "Hỏi"
    assert "safe.txt" in called[0].sanitized_sources[0].title
    assert client.call_count == 0

    import hashlib
    import json

    manifest = res.outbound_manifest
    sanitized_text = called[0].sanitized_sources[0].text
    assert manifest is not None
    assert manifest["schema_version"] == 1
    assert manifest["source_count"] == 1
    assert manifest["omitted_source_count"] == 0
    assert manifest["input_chars_total"] == len(src.text)
    assert manifest["outbound_chars_total"] == len(sanitized_text)
    assert manifest["sources"][0]["content_sha256"] == hashlib.sha256(
        sanitized_text.encode("utf-8")
    ).hexdigest()
    assert len(manifest["payload_sha256"]) == 64
    assert "Public safe text" not in json.dumps(manifest)


def test_workspace_chat_ai_answer_via_real_router_without_consent(monkeypatch):
    called = []
    def mock_generate(payload):
        called.append(payload)
        return True, "Mocked Router Reply"
    monkeypatch.setattr("aios_habit.workspace_chat_router_adapter.generate_answer_via_router", mock_generate)

    src = WorkspaceAIContextSource(
        source_id="src_machine",
        source_scope="temporary",
        source_type="txt",
        title="machine.txt",
        privacy_label="machine_only",
        text="Sensitive machine text",
        included_chars=22,
        truncated=False,
    )

    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Hỏi",
        context_sources=(src,),
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        cloud_consent_confirmed=False,
        consent_source_keys=(("temporary", "src_machine"),),
        real_router_enabled=True
    )

    client = MockProviderClient()
    res = generate_workspace_ai_answer(req, client)

    assert res.ok is False
    assert "xác nhận của Owner" in res.error_message
    assert len(called) == 0
    assert client.call_count == 0
    assert res.provider_success is False
    assert res.provider_completion_status == "not_requested"
    assert res.grounding_status == "not_assessed"
    assert res.outcome_status == "not_requested"


def test_workspace_chat_ai_answer_via_real_router_stale_fingerprint(monkeypatch):
    called = []
    def mock_generate(payload):
        called.append(payload)
        return True, "Mocked Router Reply"
    monkeypatch.setattr("aios_habit.workspace_chat_router_adapter.generate_answer_via_router", mock_generate)

    src = WorkspaceAIContextSource(
        source_id="src_safe",
        source_scope="temporary",
        source_type="txt",
        title="safe.txt",
        privacy_label="cloud_safe",
        text="Public text",
        included_chars=11,
        truncated=False,
    )

    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Hỏi",
        context_sources=(src,),
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        cloud_consent_confirmed=True,
        consent_source_keys=(("temporary", "other_source"),),
        real_router_enabled=True
    )

    client = MockProviderClient()
    res = generate_workspace_ai_answer(req, client)

    assert res.ok is False
    assert "Tập nguồn đang bật đã thay đổi" in res.error_message
    assert len(called) == 0
    assert client.call_count == 0


def test_workspace_chat_ai_answer_via_real_router_failure(monkeypatch):
    def mock_generate(payload):
        return False, "Dịch vụ AI chưa phản hồi. Vui lòng kiểm tra lại kết nối mạng hoặc cấu hình API key."
    monkeypatch.setattr("aios_habit.workspace_chat_router_adapter.generate_answer_via_router", mock_generate)

    src = WorkspaceAIContextSource(
        source_id="src_safe",
        source_scope="temporary",
        source_type="txt",
        title="safe.txt",
        privacy_label="cloud_safe",
        text="Public text",
        included_chars=11,
        truncated=False,
    )

    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Hỏi",
        context_sources=(src,),
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        cloud_consent_confirmed=True,
        consent_source_keys=(("temporary", "src_safe"),),
        real_router_enabled=True
    )

    res = generate_workspace_ai_answer(req, MockProviderClient())
    assert res.ok is False
    assert "Vui lòng kiểm tra lại kết nối mạng hoặc cấu hình API key." in res.error_message


def test_generate_answer_via_router_integration_mocked_outcome(monkeypatch):
    from aios_habit.workspace_chat_router_adapter import generate_answer_via_router
    from aios_habit.brain_gateway import SanitizedRouterPayload, SanitizedSourcePayload
    from nakazasen_ai_router import AIRouteOutcome, AIResult

    class FakeRouter:
        def __init__(self, outcome):
            self.outcome = outcome
            self.calls = []
        def route_outcome(self, request):
            self.calls.append(request)
            return self.outcome

    fake_outcome = AIRouteOutcome(
        status="success",
        result=AIResult(text="Success response", provider_name="fake_provider")
    )
    fake_router = FakeRouter(fake_outcome)

    monkeypatch.setattr("aios_habit.workspace_chat_router_adapter.create_router_from_env", lambda **k: fake_router)
    payload = SanitizedRouterPayload(
        sanitized_question="Q",
        sanitized_sources=(SanitizedSourcePayload("source_1", "public", "text", "Public", "User", "public"),),
        metadata={"source_set_hash": "hash"},
    )
    ok, text = generate_answer_via_router(payload)
    assert ok is True
    assert text == "Success response"
    assert len(fake_router.calls) == 1
    assert "Q" in fake_router.calls[0].prompt


def test_workspace_chat_router_adapter_class_instantiation(monkeypatch):
    from aios_habit.workspace_chat_router_adapter import WorkspaceChatRouterAdapter
    from aios_habit.brain_gateway import SanitizedRouterPayload
    called = []
    def mock_generate(payload):
        called.append(payload)
        return True, "class response"
    monkeypatch.setattr("aios_habit.workspace_chat_router_adapter.generate_answer_via_router", mock_generate)

    adapter = WorkspaceChatRouterAdapter()
    payload = SanitizedRouterPayload("Q", (), {"source_set_hash": "hash"})
    ok, text = adapter.generate_answer(payload)
    assert ok is True
    assert text == "class response"
    assert called == [payload]


def test_workspace_chat_router_creation_enables_network_and_v051_recovery(monkeypatch):
    from aios_habit.workspace_chat_router_adapter import generate_answer_via_router
    from aios_habit.brain_gateway import SanitizedRouterPayload
    from nakazasen_ai_router import AIRouteOutcome, AIResult

    kwargs_passed = {}

    def mock_create_router(**kwargs):
        kwargs_passed.update(kwargs)

        class DummyRouter:
            def route_outcome(self, request):
                return AIRouteOutcome(status="success", result=AIResult(text="OK", provider_name="p"))

        return DummyRouter()

    monkeypatch.setattr("aios_habit.workspace_chat_router_adapter.create_router_from_env", mock_create_router)
    payload = SanitizedRouterPayload("Q", (), {"source_set_hash": "hash"})
    ok, text = generate_answer_via_router(payload)

    assert ok is True
    assert kwargs_passed.get("enable_network") is True


def test_workspace_outcome_classifier_positive_negative_and_multilingual():
    for limited_answer in (
        "Chưa đủ thông tin trong các nguồn được cung cấp.",
        "Không tìm thấy đủ thông tin để so sánh hai quy trình.",
        "Thông tin trong các nguồn được cung cấp là không đầy đủ.",
        "Không có nguồn nào mô tả cụ thể các bước thực hiện.",
        "There is insufficient evidence in the provided documents.",
    ):
        assert classify_workspace_ai_outcome(
            limited_answer,
            provider_success=True,
            evidence_supplied=True,
        ) == ("answer_with_limits", "explicit_answer_limitation")
    assert classify_workspace_ai_outcome(
        "Thông tin không thiếu; hồ sơ mô tả đầy đủ quy trình.",
        provider_success=True,
        evidence_supplied=True,
    ) == ("success", "evidence_supplied_unverified")
    assert classify_workspace_ai_outcome(
        "The evidence is not insufficient; all steps are documented.",
        provider_success=True,
        evidence_supplied=True,
    ) == ("success", "evidence_supplied_unverified")
    assert classify_workspace_ai_outcome(
        "",
        provider_success=False,
        evidence_supplied=True,
    ) == ("provider_error", "not_assessed_provider_failure")
    assert classify_workspace_ai_outcome(
        "",
        provider_success=True,
        evidence_supplied=False,
    ) == ("insufficient_evidence", "insufficient_evidence")


def test_real_router_result_exposes_limited_outcome_and_canonical_manifest_hash(monkeypatch):
    monkeypatch.setattr(
        "aios_habit.workspace_chat_router_adapter.generate_answer_via_router",
        lambda _payload: (True, "Không tìm thấy thông tin trong nguồn được cung cấp."),
    )
    src = WorkspaceAIContextSource(
        source_id="src-safe",
        source_scope="temporary",
        source_type="txt",
        title="safe.txt",
        privacy_label="cloud_safe",
        text="Evidence text",
        included_chars=13,
        truncated=False,
    )
    request = WorkspaceAIAnswerRequest(
        conversation_id="contract-test",
        question="Hỏi",
        context_sources=(src,),
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        cloud_consent_confirmed=True,
        consent_source_keys=(("temporary", "src-safe"),),
        real_router_enabled=True,
    )

    result = generate_workspace_ai_answer(request, MockProviderClient())

    assert result.ok is True
    assert result.provider_success is True
    assert result.provider_completion_status == "completed"
    assert result.grounding_status == "explicit_answer_limitation"
    assert result.outcome_status == "answer_with_limits"
    manifest = dict(result.outbound_manifest or {})
    manifest_hash = manifest.pop("manifest_sha256")
    import hashlib
    import json
    canonical = json.dumps(
        manifest,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert manifest_hash == hashlib.sha256(canonical.encode("utf-8")).hexdigest()
