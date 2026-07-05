import time
import pytest
from aios_habit.brain_gateway import (
    BrainGateway, GatewaySource, BrainRequest, OwnerConsent, calculate_source_set_hash,
    PRIVACY_LOCAL_ONLY, PRIVACY_CONFIDENTIAL, PRIVACY_MACHINE_ONLY,
    PRIVACY_UNKNOWN, PRIVACY_CLOUD_SAFE, PRIVACY_PUBLIC,
    LOCAL_ONLY_HARD_DENY, CONFIDENTIAL_HARD_DENY, UNKNOWN_DEFAULT_DENY,
    MACHINE_ONLY_NEEDS_CONSENT, ROUTER_DISABLED, ROUTER_ALLOWED_PUBLIC,
    ROUTER_ALLOWED_CLOUD_SAFE, ROUTER_ALLOWED_OWNER_CONSENT
)

def test_local_only_hard_deny_even_with_consent():
    s = GatewaySource("1", "notebook", "text", "My Private Notes", PRIVACY_LOCAL_ONLY, "Secret text here D:\\data\\file.txt")
    shash = calculate_source_set_hash((s,))
    consent = OwnerConsent(shash, "mock_router", "workspace_chat_answer", time.time())
    
    req = BrainRequest("What is this?", (s,), consent, router_enabled=True)
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert not decision.allowed
    assert decision.reason_code == LOCAL_ONLY_HARD_DENY
    assert decision.next_action == "USE_LOCAL_ONLY"

def test_confidential_hard_deny_even_with_consent():
    s = GatewaySource("1", "notebook", "text", "Confidential doc", PRIVACY_CONFIDENTIAL, "Confidential text here")
    shash = calculate_source_set_hash((s,))
    consent = OwnerConsent(shash, "mock_router", "workspace_chat_answer", time.time())
    
    req = BrainRequest("What is this?", (s,), consent, router_enabled=True)
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert not decision.allowed
    assert decision.reason_code == CONFIDENTIAL_HARD_DENY
    assert decision.next_action == "USE_LOCAL_ONLY"

def test_unknown_deny_by_default():
    s = GatewaySource("1", "notebook", "text", "Unknown status doc", PRIVACY_UNKNOWN, "Some text")
    req = BrainRequest("What is this?", (s,), consent=None, router_enabled=True)
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert not decision.allowed
    assert decision.reason_code == UNKNOWN_DEFAULT_DENY
    assert decision.next_action == "REQUEST_CLASSIFICATION"

def test_machine_only_deny_without_consent():
    s = GatewaySource("1", "notebook", "text", "Machine doc", PRIVACY_MACHINE_ONLY, "Some text")
    req = BrainRequest("What is this?", (s,), consent=None, router_enabled=True)
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert not decision.allowed
    assert decision.reason_code == MACHINE_ONLY_NEEDS_CONSENT
    assert decision.next_action == "REQUEST_OWNER_CONSENT"

def test_machine_only_allow_with_consent_and_sanitized():
    s_text = "Secret Key " + "sk-12345678901234567890" + " in D:\\Sandbox\\secrets.txt"
    s = GatewaySource("source_id_raw", "notebook", "text", "Machine doc", PRIVACY_MACHINE_ONLY, s_text)
    shash = calculate_source_set_hash((s,))
    consent = OwnerConsent(shash, "mock_router", "workspace_chat_answer", time.time())
    
    q_text = "Tell me about path D:\\Sandbox and key " + "sk-12345678901234567890"
    req = BrainRequest(q_text, (s,), consent, router_enabled=True)
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert decision.allowed
    assert decision.reason_code == ROUTER_ALLOWED_OWNER_CONSENT
    
    payload = decision.sanitized_payload
    assert "[REDACTED_LOCAL_PATH]" in payload.sanitized_question
    assert "[REDACTED_API_KEY]" in payload.sanitized_question
    
    # Metadata Sanitization: raw source_id và title không được xuất hiện trong payload
    assert payload.sanitized_sources[0].source_id == "source_1"
    assert "source_id_raw" not in payload.sanitized_sources[0].source_id
    assert payload.sanitized_sources[0].title == "Nguồn đã làm sạch 1"
    assert "Machine doc" not in payload.sanitized_sources[0].title
    
    # Marker Redaction: Không chứa raw title của nguồn nhạy cảm
    assert payload.sanitized_sources[0].text == "[redacted machine_only source 1]"
    assert "Machine doc" not in payload.sanitized_sources[0].text

def test_mixed_local_only_and_cloud_safe_deny():
    s1 = GatewaySource("1", "notebook", "text", "Local doc", PRIVACY_LOCAL_ONLY, "Local text")
    s2 = GatewaySource("2", "notebook", "text", "Cloud doc", PRIVACY_CLOUD_SAFE, "Cloud text")
    
    req = BrainRequest("Combine these", (s1, s2), consent=None, router_enabled=True)
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert not decision.allowed
    assert decision.reason_code == LOCAL_ONLY_HARD_DENY

def test_cloud_safe_allow_when_enabled():
    s = GatewaySource("1", "notebook", "text", "Cloud doc", PRIVACY_CLOUD_SAFE, "Normal text D:\\paths")
    req = BrainRequest("Show cloud doc", (s,), consent=None, router_enabled=True)
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert decision.allowed
    assert decision.reason_code == ROUTER_ALLOWED_CLOUD_SAFE
    assert decision.sanitized_payload.sanitized_sources[0].text == "Normal text [REDACTED_LOCAL_PATH]"

def test_public_allow_when_enabled():
    s = GatewaySource("1", "notebook", "text", "Public doc", PRIVACY_PUBLIC, "Public text")
    req = BrainRequest("Show public doc", (s,), consent=None, router_enabled=True)
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert decision.allowed
    assert decision.reason_code == ROUTER_ALLOWED_PUBLIC

def test_router_disabled_no_external_call():
    s = GatewaySource("1", "notebook", "text", "Public doc", PRIVACY_PUBLIC, "Public text")
    req = BrainRequest("Show public doc", (s,), consent=None, router_enabled=False)
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert not decision.allowed
    assert decision.reason_code == ROUTER_DISABLED
    assert decision.next_action == "ENABLE_ROUTER_MOCK_FOR_TEST"

def test_mock_router_receives_no_raw_evidence_store():
    s = GatewaySource("1", "notebook", "text", "Machine doc", PRIVACY_MACHINE_ONLY, "Top secret")
    shash = calculate_source_set_hash((s,))
    consent = OwnerConsent(shash, "mock_router", "workspace_chat_answer", time.time())
    
    req = BrainRequest("Q", (s,), consent, router_enabled=True)
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert decision.allowed
    payload = decision.sanitized_payload
    assert payload.sanitized_sources[0].text == "[redacted machine_only source 1]"

def test_mock_router_receives_no_local_paths():
    s = GatewaySource("1", "notebook", "text", "Public doc", PRIVACY_PUBLIC, "User file in D:\\Sandbox\\dir")
    req = BrainRequest("User query for D:\\Sandbox", (s,), consent=None, router_enabled=True)
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert decision.allowed
    payload = decision.sanitized_payload
    assert "D:\\Sandbox" not in payload.sanitized_question
    assert "D:\\Sandbox" not in payload.sanitized_sources[0].text
    assert "[REDACTED_LOCAL_PATH]" in payload.sanitized_question
    assert "[REDACTED_LOCAL_PATH]" in payload.sanitized_sources[0].text

def test_sanitized_prompt_redacts_secret_like_text():
    token_val = "abcdefgh"
    q = "My key is " + "sk-abcdefghijklmnopqrts" + " and secret" + "_token: '" + token_val + "'"
    s = GatewaySource("1", "notebook", "text", "Public doc", PRIVACY_PUBLIC, "No secrets here")
    req = BrainRequest(q, (s,), consent=None, router_enabled=True)
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert decision.allowed
    q_sanitized = decision.sanitized_payload.sanitized_question
    assert "sk-abcdefghijklmnopqrts" not in q_sanitized
    assert token_val not in q_sanitized
    assert "[REDACTED_API_KEY]" in q_sanitized
    assert "secret_token=[REDACTED_SECRET]" in q_sanitized

def test_consent_tied_to_source_set_hash_and_invalidated():
    s1 = GatewaySource("1", "notebook", "text", "Machine doc", PRIVACY_MACHINE_ONLY, "Machine text")
    shash = calculate_source_set_hash((s1,))
    consent = OwnerConsent(shash, "mock_router", "workspace_chat_answer", time.time())
    
    s2 = GatewaySource("2", "notebook", "text", "Public doc", PRIVACY_PUBLIC, "Public text")
    
    req = BrainRequest("Query", (s1, s2), consent, router_enabled=True)
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert not decision.allowed
    assert decision.reason_code == MACHINE_ONLY_NEEDS_CONSENT

def test_unknown_with_consent_but_not_sanitized_reclassified_does_not_send_raw():
    s = GatewaySource("1", "notebook", "text", "Unknown doc", PRIVACY_UNKNOWN, "Raw content is here")
    shash = calculate_source_set_hash((s,))
    consent = OwnerConsent(shash, "mock_router", "workspace_chat_answer", time.time())
    
    req = BrainRequest("Query", (s,), consent, router_enabled=True)
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert decision.allowed
    assert decision.sanitized_payload.sanitized_sources[0].text == "[redacted unknown source 1]"

def test_machine_only_consent_wrong_hash_denied():
    s = GatewaySource("1", "notebook", "text", "Machine doc", PRIVACY_MACHINE_ONLY, "Text")
    consent = OwnerConsent("wrong_hash_here", "mock_router", "workspace_chat_answer", time.time())
    
    req = BrainRequest("Query", (s,), consent, router_enabled=True)
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert not decision.allowed
    assert decision.reason_code == MACHINE_ONLY_NEEDS_CONSENT

def test_consent_wrong_destination_denied():
    s = GatewaySource("1", "notebook", "text", "Machine doc", PRIVACY_MACHINE_ONLY, "Machine text")
    shash = calculate_source_set_hash((s,))
    consent = OwnerConsent(shash, "wrong_router", "workspace_chat_answer", time.time())
    
    req = BrainRequest("Query", (s,), consent, router_enabled=True, destination="mock_router")
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert not decision.allowed
    assert decision.reason_code == MACHINE_ONLY_NEEDS_CONSENT

def test_consent_wrong_purpose_denied():
    s = GatewaySource("1", "notebook", "text", "Machine doc", PRIVACY_MACHINE_ONLY, "Machine text")
    shash = calculate_source_set_hash((s,))
    consent = OwnerConsent(shash, "mock_router", "wrong_purpose", time.time())
    
    req = BrainRequest("Query", (s,), consent, router_enabled=True, purpose="workspace_chat_answer")
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert not decision.allowed
    assert decision.reason_code == MACHINE_ONLY_NEEDS_CONSENT

def test_consent_expired_denied():
    s = GatewaySource("1", "notebook", "text", "Machine doc", PRIVACY_MACHINE_ONLY, "Machine text")
    shash = calculate_source_set_hash((s,))
    now = time.time()
    consent = OwnerConsent(shash, "mock_router", "workspace_chat_answer", now - 20, expiry=now - 10)
    
    req = BrainRequest("Query", (s,), consent, router_enabled=True)
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert not decision.allowed
    assert decision.reason_code == MACHINE_ONLY_NEEDS_CONSENT

def test_empty_source_resolves_to_unknown_and_denied():
    req = BrainRequest("Query", (), consent=None, router_enabled=True)
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert not decision.allowed
    assert decision.reason_code == UNKNOWN_DEFAULT_DENY
    assert decision.next_action == "REQUEST_CLASSIFICATION"

def test_confidential_plus_public_mixed_strictly_denied():
    s1 = GatewaySource("1", "notebook", "text", "Confidential doc", PRIVACY_CONFIDENTIAL, "Confidential text")
    s2 = GatewaySource("2", "notebook", "text", "Public doc", PRIVACY_PUBLIC, "Public text")
    
    req = BrainRequest("Combine", (s1, s2), consent=None, router_enabled=True)
    gw = BrainGateway()
    decision = gw.preflight_check(req)
    
    assert not decision.allowed
    assert decision.reason_code == CONFIDENTIAL_HARD_DENY
