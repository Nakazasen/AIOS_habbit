import ast
import pytest
from aios_habit.workspace_chat_ai_answer import (
    WorkspaceAIAnswerRequest, WorkspaceAIContextSource,
    generate_workspace_ai_answer, WorkspaceAIAnswerResult
)
from aios_habit.brain_gateway import (
    PRIVACY_LOCAL_ONLY, PRIVACY_CLOUD_SAFE, PRIVACY_MACHINE_ONLY,
    calculate_source_set_hash, SanitizedRouterPayload, SanitizedSourcePayload
)
from aios_habit.router_adapter import MockRouterAdapter

def test_proof_no_network_imports_in_router_adapter():
    import os
    adapter_path = os.path.join("src", "aios_habit", "router_adapter.py")
    with open(adapter_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    forbidden = {"requests", "httpx", "openai", "socket", "urllib", "http"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                base_module = name.name.split(".")[0]
                assert base_module not in forbidden, f"Forbidden import detected: {name.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                base_module = node.module.split(".")[0]
                assert base_module not in forbidden, f"Forbidden import detected: from {node.module}"

def test_mock_router_payload_validation_fails_on_local_paths():
    payload = SanitizedRouterPayload(
        sanitized_question="Tell me about path D:\\Sandbox",
        sanitized_sources=(
            SanitizedSourcePayload("source_1", "notebook", "text", "Public doc", "Path is D:\\Sandbox", "public"),
        ),
        metadata={}
    )
    adapter = MockRouterAdapter(enabled=True)
    with pytest.raises(ValueError, match="Security violation"):
        adapter.send_payload(payload)

def test_workspace_chat_integration_local_only_denied():
    src = WorkspaceAIContextSource("1", "notebook", "text", "Private Notes", "local_only", "Secret content", 14, False)
    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Help me",
        context_sources=(src,),
        privacy_mode="cloud_allowed",
        cloud_consent_confirmed=True,
        router_enabled=True
    )
    
    class DummyClient:
        def __init__(self):
            self.call_count = 0
        def generate(self, *, system_prompt: str, user_prompt: str) -> str:
            self.call_count += 1
            return "Real answer"

    client = DummyClient()
    res = generate_workspace_ai_answer(req, client)
    
    assert not res.ok
    assert "Chỉ trả lời bằng dữ liệu local." in res.error_message
    assert "Hành động tiếp theo: USE_LOCAL_ONLY" in res.error_message
    assert res.reason_code == "LOCAL_ONLY_HARD_DENY"
    assert res.next_action == "USE_LOCAL_ONLY"
    assert client.call_count == 0

def test_workspace_chat_integration_machine_only_needs_consent():
    src = WorkspaceAIContextSource("1", "notebook", "text", "Machine Notes", "machine_only", "Some content", 12, False)
    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Help me",
        context_sources=(src,),
        privacy_mode="cloud_allowed",
        cloud_consent_confirmed=False,
        router_enabled=True
    )
    
    class DummyClient:
        def __init__(self):
            self.call_count = 0
        def generate(self, *, system_prompt: str, user_prompt: str) -> str:
            self.call_count += 1
            return "Real answer"

    client = DummyClient()
    res = generate_workspace_ai_answer(req, client)
    
    assert not res.ok
    assert "xác nhận của Owner" in res.error_message
    assert "Hành động tiếp theo: REQUEST_OWNER_CONSENT" in res.error_message
    assert res.reason_code == "MACHINE_ONLY_NEEDS_CONSENT"
    assert res.next_action == "REQUEST_OWNER_CONSENT"
    assert client.call_count == 0

def test_workspace_chat_integration_cloud_safe_allowed_mock_router():
    key_str = "sk-12345678901234567890"
    src = WorkspaceAIContextSource("1", "notebook", "text", "Cloud Notes", "cloud_safe", "Some content in D:\\Sandbox, key is " + key_str, 50, False)
    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Tell me key " + key_str + " in D:\\Sandbox",
        context_sources=(src,),
        privacy_mode="cloud_allowed",
        cloud_consent_confirmed=True,
        router_enabled=True
    )
    
    class DummyClient:
        def __init__(self):
            self.call_count = 0
        def generate(self, *, system_prompt: str, user_prompt: str) -> str:
            self.call_count += 1
            return "Real answer"

    client = DummyClient()
    res = generate_workspace_ai_answer(req, client)
    
    assert res.ok
    assert "[MOCK ROUTER RESPONSE]" in res.answer_text
    assert "[REDACTED_API_KEY]" in res.answer_text
    assert "[REDACTED_LOCAL_PATH]" in res.answer_text
    assert key_str not in res.answer_text
    assert "D:\\Sandbox" not in res.answer_text
    assert res.reason_code == "ROUTER_ALLOWED_CLOUD_SAFE"
    assert res.next_action == "CALL_MOCK_ROUTER"
    assert res.externally_sent is False
    assert res.mock_external_send is True
    assert res.would_send_externally is True
    assert client.call_count == 0

def test_metadata_leaks_prevented_in_sanitized_payload():
    key_str = "sk-12345678901234567890"
    title_path = "D:\\Sandbox\\AIOS_habbit\\secret.txt"
    src_id_key = "key_" + key_str
    scope_path = "D:\\Sandbox\\scope"
    
    from aios_habit.brain_gateway import BrainGateway, GatewaySource, BrainRequest, OwnerConsent
    gs = GatewaySource(src_id_key, scope_path, "text", title_path, "machine_only", "some text")
    shash = calculate_source_set_hash((gs,))
    consent = OwnerConsent(shash, "mock_router", "workspace_chat_answer", 2000000000.0)
    
    req = BrainRequest("query", (gs,), consent, router_enabled=True)
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert decision.allowed
    payload = decision.sanitized_payload
    
    assert payload.sanitized_sources[0].source_id == "source_1"
    assert payload.sanitized_sources[0].title == "Nguồn đã làm sạch 1"
    assert payload.sanitized_sources[0].source_scope == "unknown"
    
    for val in [title_path, src_id_key, scope_path]:
        assert val not in payload.sanitized_sources[0].source_id
        assert val not in payload.sanitized_sources[0].title
        assert val not in payload.sanitized_sources[0].source_scope

def test_workspace_chat_integration_wrong_consent_snapshot_denied():
    src1 = WorkspaceAIContextSource("1", "temporary", "text", "Machine Notes", "machine_only", "Content", 7, False)
    
    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Help",
        context_sources=(src1,),
        privacy_mode="cloud_allowed",
        cloud_consent_confirmed=True,
        consent_source_keys=(),
        router_enabled=True
    )
    
    class DummyClient:
        def generate(self, *, system_prompt: str, user_prompt: str) -> str:
            return "Answer"

    res = generate_workspace_ai_answer(req, DummyClient())
    
    assert not res.ok
    assert "không hợp lệ hoặc đã hết hạn" in res.error_message
    assert res.reason_code == "MACHINE_ONLY_NEEDS_CONSENT"

# REGRESSION TESTS BỔ SUNG VÒNG 2

def test_source_type_leak_prevention():
    from aios_habit.brain_gateway import BrainGateway, GatewaySource, BrainRequest
    gs = GatewaySource("1", "notebook", "D:\\Sandbox\\secret.txt token=abcdefgh", "Title", "public", "text content")
    req = BrainRequest("query", (gs,), consent=None, router_enabled=True)
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert decision.allowed
    payload = decision.sanitized_payload
    assert payload.sanitized_sources[0].source_type == "unknown"

def test_adapter_rejects_lowercase_authorization_and_bearer():
    payload = SanitizedRouterPayload(
        sanitized_question="Tell me about public doc",
        sanitized_sources=(
            SanitizedSourcePayload("source_1", "notebook", "text", "Title", "my authorization: abcdefgh", "public"),
        ),
        metadata={}
    )
    adapter = MockRouterAdapter(enabled=True)
    with pytest.raises(ValueError, match="Security violation"):
        adapter.send_payload(payload)

def test_adapter_rejects_generic_token_and_apikey():
    adapter = MockRouterAdapter(enabled=True)
    
    p1 = SanitizedRouterPayload(
        sanitized_question="token=abcdefgh",
        sanitized_sources=(
            SanitizedSourcePayload("source_1", "notebook", "text", "Title", "Content", "public"),
        ),
        metadata={}
    )
    with pytest.raises(ValueError, match="Security violation"):
        adapter.send_payload(p1)

    p2 = SanitizedRouterPayload(
        sanitized_question="Query",
        sanitized_sources=(
            SanitizedSourcePayload("source_1", "notebook", "text", "Title", "api_key=abcdefgh", "public"),
        ),
        metadata={}
    )
    with pytest.raises(ValueError, match="Security violation"):
        adapter.send_payload(p2)

def test_windows_path_with_spaces_fully_redacted():
    from aios_habit.brain_gateway import BrainGateway, GatewaySource, BrainRequest
    
    raw_text = "Check D:\\Sandbox Folder\\secret.txt and C:\\Users\\Admin\\My Documents\\a.txt"
    gs = GatewaySource("1", "notebook", "text", "Public", "public", raw_text)
    req = BrainRequest("query D:\\Sandbox Folder\\secret.txt", (gs,), consent=None, router_enabled=True)
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert decision.allowed
    payload = decision.sanitized_payload
    
    assert "Sandbox Folder" not in payload.sanitized_question
    assert "secret.txt" not in payload.sanitized_question
    assert "Sandbox Folder" not in payload.sanitized_sources[0].text
    assert "My Documents" not in payload.sanitized_sources[0].text
    assert "a.txt" not in payload.sanitized_sources[0].text

def test_adapter_checks_privacy_label():
    payload = SanitizedRouterPayload(
        sanitized_question="Query",
        sanitized_sources=(
            SanitizedSourcePayload("source_1", "notebook", "text", "Title", "Content", "D:\\Sandbox\\leak"),
        ),
        metadata={}
    )
    adapter = MockRouterAdapter(enabled=True)
    with pytest.raises(ValueError, match="Security violation"):
        adapter.send_payload(payload)

def test_end_to_end_gateway_mock_source_type_opaque():
    from aios_habit.brain_gateway import BrainGateway, GatewaySource, BrainRequest
    gs = GatewaySource("1", "notebook", "D:\\Sandbox\\leak_type", "Title", "public", "Safe text")
    req = BrainRequest("query", (gs,), consent=None, router_enabled=True)
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert decision.allowed
    payload = decision.sanitized_payload
    
    adapter = MockRouterAdapter(enabled=True)
    res = adapter.send_payload(payload)
    assert res["ok"] is True
    assert res["mock_external_send"] is True

# REGRESSION TESTS BỔ SUNG VÒNG 3 (ĐỆ QUY METADATA, SAFE SECURITY MESSAGES)

def test_nested_metadata_dict_rejected():
    # A. Metadata nested dict bị reject
    payload = SanitizedRouterPayload(
        sanitized_question="Query",
        sanitized_sources=(
            SanitizedSourcePayload("source_1", "notebook", "text", "Title", "Content", "public"),
        ),
        metadata={"nested": {"note": "C:\\Users\\Admin\\My Documents\\a.txt"}}
    )
    adapter = MockRouterAdapter(enabled=True)
    with pytest.raises(ValueError, match="Security violation"):
        adapter.send_payload(payload)

def test_nested_metadata_list_rejected():
    # B. Metadata list bị reject
    payload = SanitizedRouterPayload(
        sanitized_question="Query",
        sanitized_sources=(
            SanitizedSourcePayload("source_1", "notebook", "text", "Title", "Content", "public"),
        ),
        metadata={"notes": ["safe", "token=abcdefgh"]}
    )
    adapter = MockRouterAdapter(enabled=True)
    with pytest.raises(ValueError, match="Security violation"):
        adapter.send_payload(payload)

def test_nested_metadata_tuple_rejected():
    # C. Metadata tuple bị reject
    payload = SanitizedRouterPayload(
        sanitized_question="Query",
        sanitized_sources=(
            SanitizedSourcePayload("source_1", "notebook", "text", "Title", "Content", "public"),
        ),
        metadata={"notes": ("safe", "authorization: abcdefgh")}
    )
    adapter = MockRouterAdapter(enabled=True)
    with pytest.raises(ValueError, match="Security violation"):
        adapter.send_payload(payload)

def test_nested_metadata_set_rejected():
    # D. Metadata set bị reject
    payload = SanitizedRouterPayload(
        sanitized_question="Query",
        sanitized_sources=(
            SanitizedSourcePayload("source_1", "notebook", "text", "Title", "Content", "public"),
        ),
        metadata={"notes": {"safe", "api_key=abcdefgh"}}
    )
    adapter = MockRouterAdapter(enabled=True)
    with pytest.raises(ValueError, match="Security violation"):
        adapter.send_payload(payload)

def test_metadata_key_rejected():
    # E. Metadata key chứa secret cũng bị reject
    payload = SanitizedRouterPayload(
        sanitized_question="Query",
        sanitized_sources=(
            SanitizedSourcePayload("source_1", "notebook", "text", "Title", "Content", "public"),
        ),
        metadata={"token=abcdefgh": "safe"}
    )
    adapter = MockRouterAdapter(enabled=True)
    with pytest.raises(ValueError, match="Security violation"):
        adapter.send_payload(payload)

def test_security_error_message_does_not_leak_raw_secret():
    # F. Error message không leak raw secret
    payload = SanitizedRouterPayload(
        sanitized_question="bearer abcdefgh",
        sanitized_sources=(
            SanitizedSourcePayload("source_1", "notebook", "text", "Title", "Content", "public"),
        ),
        metadata={}
    )
    adapter = MockRouterAdapter(enabled=True)
    with pytest.raises(ValueError) as exc_info:
        adapter.send_payload(payload)
        
    err_msg = str(exc_info.value)
    # Lỗi không được chứa thông tin nhạy cảm thô
    assert "bearer abcdefgh" not in err_msg
    assert "abcdefgh" not in err_msg
    assert "Security violation" in err_msg

def test_workspace_chat_does_not_expose_raw_exception():
    # G. Workspace Chat không trả str(e) raw, thay bằng thông báo cố định an toàn
    src = WorkspaceAIContextSource("1", "notebook", "text", "Public Title", "public", "Safe content", 10, False)
    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_1",
        question="Query containing token=abcdefgh", # Kích hoạt leak check
        context_sources=(src,),
        privacy_mode="cloud_allowed",
        cloud_consent_confirmed=True,
        router_enabled=True
    )
    
    class DummyClient:
        def generate(self, *, system_prompt: str, user_prompt: str) -> str:
            return "Answer"

    res = generate_workspace_ai_answer(req, DummyClient())
    
    assert not res.ok
    # Assert lỗi thô không bị rò rỉ ra owner-facing response
    assert "token=abcdefgh" not in res.error_message
    assert "abcdefgh" not in res.error_message
    # Assert trả về thông báo an toàn tiếng Việt cố định
    assert "Yêu cầu đã bị chặn vì payload có dấu hiệu chứa thông tin nhạy cảm." in res.error_message
