import re
from typing import Dict, Any, Optional
from aios_habit.brain_gateway import SanitizedRouterPayload

# Bộ lọc an toàn kiểm tra rò rỉ (Case-insensitive)
# Exception chỉ chứa thông báo an toàn, tuyệt đối không leak offending value thô.
def check_for_leaks(value: str) -> None:
    if not value:
        return
    
    # 1. Windows drive paths và local paths
    if re.search(r'(?i)[a-z]:[\\/]', value):
        raise ValueError("Security violation: local path detected")
    
    # 2. Local directories hoặc paths đặc thù
    if "Sandbox" in value or "aios_habit" in value:
        # source_ scope/id an toàn loại trừ
        if not (value.startswith("source_") or value in {"notebook", "temporary", "unknown", "workspace_chat_answer", "mock_router"}):
            raise ValueError("Security violation: local path keywords detected")
            
    # 3. Unix paths (/home/, /etc/...)
    if re.search(r'(?i)/(?:home|etc|var|usr|bin|tmp)/', value):
        raise ValueError("Security violation: local path detected")

    # 4. Secrets / Keys / Tokens (Case-insensitive)
    lower_val = value.lower()
    
    # Check sk-... và AIza...
    if "sk-" in lower_val or "aiza" in lower_val:
        raise ValueError("Security violation: API key pattern detected")

    # Check các token patterns (Bearer, Authorization, token, api_key, api-key, apikey, secret, password)
    forbidden_patterns = [
        r'authorization\s*:',
        r'bearer\s+',
        r'token\s*[:=]',
        r'api[_-]?key\s*[:=]',
        r'api-key\s*[:=]',
        r'apikey\s*[:=]',
        r'secret\s*[:=]',
        r'password\s*[:=]'
    ]
    for pattern in forbidden_patterns:
        if re.search(pattern, lower_val):
            raise ValueError("Security violation: sensitive pattern detected")
            
    # Case-insensitive substring checks
    for kw in ["authorization:", "bearer ", "token=", "api_key=", "api-key=", "apikey=", "secret=", "password="]:
        if kw in lower_val:
            raise ValueError("Security violation: sensitive pattern detected")
            
    # Local repository references
    if "aios_habit" in value and not value.startswith("source_"):
        raise ValueError("Security violation: local repo references detected")

# Duyệt đệ quy mọi metadata structure để kiểm tra rò rỉ
def check_value_recursive(val: Any) -> None:
    if isinstance(val, str):
        check_for_leaks(val)
    elif isinstance(val, (list, tuple, set, frozenset)):
        for item in val:
            check_value_recursive(item)
    elif isinstance(val, dict):
        for k, v in val.items():
            check_value_recursive(k)
            check_value_recursive(v)
    elif val is None or isinstance(val, (bool, int, float)):
        # Primitive an toàn
        pass
    else:
        # Nếu gặp object lạ không thuộc primitive an toàn
        raise ValueError("Security violation: unsafe object type in metadata")

class MockRouterAdapter:
    def __init__(self, enabled: bool = False):
        self.enabled = enabled

    def send_payload(self, payload: SanitizedRouterPayload) -> Dict[str, Any]:
        """
        Nhận SanitizedRouterPayload và mô phỏng cuộc gọi định tuyến.
        Không sử dụng bất kỳ thư viện mạng nào (offline hoàn toàn).
        """
        if not self.enabled:
            return {
                "ok": False,
                "error_message": "Router adapter is disabled.",
                "response_text": "",
                "mock_external_send": False,
                "would_send_externally": False,
                "mock_status": "mock only, no provider call"
            }

        # Kiểm tra toàn bộ các trường trong payload
        check_for_leaks(payload.sanitized_question)
        for s in payload.sanitized_sources:
            check_for_leaks(s.source_id)
            check_for_leaks(s.source_scope)
            check_for_leaks(s.source_type)
            check_for_leaks(s.title)
            check_for_leaks(s.text)
            check_for_leaks(s.privacy_label)
        
        # Duyệt đệ quy metadata
        if payload.metadata:
            check_value_recursive(payload.metadata)

        # Mô phỏng phản hồi từ Mock Router
        simulated_answer = (
            f"[MOCK ROUTER RESPONSE]\n"
            f"Tôi đã xử lý câu hỏi: '{payload.sanitized_question}'.\n"
            f"Dựa trên các nguồn an toàn đã được làm sạch:\n"
        )
        for s in payload.sanitized_sources:
            simulated_answer += f"- {s.title} ({s.privacy_label}): {s.text[:100]}\n"

        # Kiểm chứng an toàn cho chính phản hồi mock
        check_for_leaks(simulated_answer)

        return {
            "ok": True,
            "error_message": "",
            "response_text": simulated_answer.strip(),
            "mock_external_send": True,
            "would_send_externally": True,
            "mock_status": "mock only, no provider call"
        }
