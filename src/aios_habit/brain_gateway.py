import re
import hashlib
from dataclasses import dataclass, field
from typing import Tuple, Optional, List, Dict, Any

# Trạng thái Privacy Levels
PRIVACY_LOCAL_ONLY = "local_only"
PRIVACY_CONFIDENTIAL = "confidential"
PRIVACY_MACHINE_ONLY = "machine_only"
PRIVACY_UNKNOWN = "unknown"
PRIVACY_CLOUD_SAFE = "cloud_safe"
PRIVACY_PUBLIC = "public"

# Mức độ nghiêm ngặt giảm dần
PRIVACY_STRICTNESS_ORDER = [
    PRIVACY_LOCAL_ONLY,
    PRIVACY_CONFIDENTIAL,
    PRIVACY_MACHINE_ONLY,
    PRIVACY_UNKNOWN,
    PRIVACY_CLOUD_SAFE,
    PRIVACY_PUBLIC
]

# Allow-lists cho metadata
SAFE_SOURCE_TYPES = {"document", "text", "spreadsheet", "image", "unknown"}
SAFE_SCOPES = {"notebook", "temporary", "unknown"}

# Reason codes
LOCAL_ONLY_HARD_DENY = "LOCAL_ONLY_HARD_DENY"
CONFIDENTIAL_HARD_DENY = "CONFIDENTIAL_HARD_DENY"
UNKNOWN_DEFAULT_DENY = "UNKNOWN_DEFAULT_DENY"
MACHINE_ONLY_NEEDS_CONSENT = "MACHINE_ONLY_NEEDS_CONSENT"
MIXED_STRICTEST_PRIVACY = "MIXED_STRICTEST_PRIVACY"
ROUTER_DISABLED = "ROUTER_DISABLED"
ROUTER_ALLOWED_CLOUD_SAFE = "ROUTER_ALLOWED_CLOUD_SAFE"
ROUTER_ALLOWED_PUBLIC = "ROUTER_ALLOWED_PUBLIC"
ROUTER_ALLOWED_OWNER_CONSENT = "ROUTER_ALLOWED_OWNER_CONSENT"
SANITIZATION_FAILED = "SANITIZATION_FAILED"

# Next Actions tương ứng với Reason Codes
NEXT_ACTIONS = {
    LOCAL_ONLY_HARD_DENY: "USE_LOCAL_ONLY",
    CONFIDENTIAL_HARD_DENY: "USE_LOCAL_ONLY",
    UNKNOWN_DEFAULT_DENY: "REQUEST_CLASSIFICATION",
    MACHINE_ONLY_NEEDS_CONSENT: "REQUEST_OWNER_CONSENT",
    MIXED_STRICTEST_PRIVACY: "USE_LOCAL_ONLY",
    ROUTER_DISABLED: "ENABLE_ROUTER_MOCK_FOR_TEST",
    SANITIZATION_FAILED: "USE_LOCAL_ONLY",
    ROUTER_ALLOWED_CLOUD_SAFE: "CALL_MOCK_ROUTER",
    ROUTER_ALLOWED_PUBLIC: "CALL_MOCK_ROUTER",
    ROUTER_ALLOWED_OWNER_CONSENT: "CALL_MOCK_ROUTER"
}

@dataclass(frozen=True)
class GatewaySource:
    source_id: str
    source_scope: str
    source_type: str
    title: str
    privacy_label: str
    text: str

@dataclass(frozen=True)
class OwnerConsent:
    source_set_hash: str
    destination: str
    purpose: str
    timestamp: float
    one_shot: bool = True
    expiry: Optional[float] = None

    def is_valid_for(self, source_set_hash: str, destination: str, purpose: str, now: Optional[float] = None) -> bool:
        if now is None:
            import time
            now = time.time()
        if self.source_set_hash != source_set_hash:
            return False
        if self.destination != destination:
            return False
        if self.purpose != purpose:
            return False
        if self.expiry is not None and now > self.expiry:
            return False
        return True

@dataclass(frozen=True)
class BrainRequest:
    question: str
    sources: Tuple[GatewaySource, ...]
    consent: Optional[OwnerConsent] = None
    router_enabled: bool = False
    purpose: str = "workspace_chat_answer"
    destination: str = "mock_router"

@dataclass(frozen=True)
class SanitizedSourcePayload:
    source_id: str
    source_scope: str
    source_type: str
    title: str
    text: str  # sanitized or redacted text
    privacy_label: str

@dataclass(frozen=True)
class SanitizedRouterPayload:
    sanitized_question: str
    sanitized_sources: Tuple[SanitizedSourcePayload, ...]
    metadata: Dict[str, Any]

@dataclass(frozen=True)
class BrainDecision:
    allowed: bool
    reason_code: str
    next_action: str
    message: str
    sanitized_payload: Optional[SanitizedRouterPayload] = None

def _normalize_privacy_label(label: Optional[str]) -> str:
    if not label:
        return PRIVACY_UNKNOWN
    cleaned = label.strip().lower()
    if cleaned in PRIVACY_STRICTNESS_ORDER:
        return cleaned
    return PRIVACY_UNKNOWN

def get_strictest_privacy(sources: Tuple[GatewaySource, ...]) -> str:
    # Empty source = unknown (default deny)
    if not sources:
        return PRIVACY_UNKNOWN
    strictest_idx = len(PRIVACY_STRICTNESS_ORDER) - 1
    for s in sources:
        normalized = _normalize_privacy_label(s.privacy_label)
        try:
            idx = PRIVACY_STRICTNESS_ORDER.index(normalized)
            if idx < strictest_idx:
                strictest_idx = idx
        except ValueError:
            idx = PRIVACY_STRICTNESS_ORDER.index(PRIVACY_UNKNOWN)
            if idx < strictest_idx:
                strictest_idx = idx
    return PRIVACY_STRICTNESS_ORDER[strictest_idx]

def calculate_source_set_hash(sources: Tuple[GatewaySource, ...]) -> str:
    parts = []
    sorted_sources = sorted(sources, key=lambda x: (x.source_scope or "", x.source_id or ""))
    for s in sorted_sources:
        normalized_label = _normalize_privacy_label(s.privacy_label)
        parts.append(f"{s.source_scope}:{s.source_id}:{normalized_label}")
    content = "|".join(parts)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def sanitize_text(text: str) -> str:
    if not text:
        return ""
    # Redact Windows paths (bao gồm cả dấu gạch chéo xuôi/ngược và khoảng trắng)
    # Ví dụ: D:\Sandbox Folder\secret.txt, C:\Users\Admin\My Documents\a.txt
    text = re.sub(r'(?i)[a-z]:\\(?:[^\\:\"\'<>\|\?\*]+(?:\\|/))*[^\\:\"\'<>\|\?\*\s]+(?:\.[a-zA-Z0-9]{2,4})?', '[REDACTED_LOCAL_PATH]', text)
    text = re.sub(r'(?i)[a-z]:/(?:[^\\:\"\'<>\|\?\*]+(?:\\|/))*[^\\:\"\'<>\|\?\*\s]+(?:\.[a-zA-Z0-9]{2,4})?', '[REDACTED_LOCAL_PATH]', text)
    # Tiếp tục quét các Windows path dạng C:\path\to\file nếu còn sót
    text = re.sub(r'[a-zA-Z]:\\[^\s\)\(\"\']+', '[REDACTED_LOCAL_PATH]', text)
    text = re.sub(r'[a-zA-Z]:/[^\s\)\(\"\']+', '[REDACTED_LOCAL_PATH]', text)
    
    # Redact Unix paths
    text = re.sub(r'/(?:[a-zA-Z0-9_\.\-]+/)+[^\s\)\(\"\']+', '[REDACTED_LOCAL_PATH]', text)
    
    # Redact API Keys / secrets (e.g. sk-..., AIza...)
    text = re.sub(r'(sk-[a-zA-Z0-9]{8,})', '[REDACTED_API_KEY]', text)
    text = re.sub(r'(AIza[a-zA-Z0-9_\-]{8,})', '[REDACTED_API_KEY]', text)
    
    # Redact secret-like patterns (case-insensitive)
    text = re.sub(r'(?i)(secret|token|api_key|password|private_key|api-key|apikey)\s*[:=]\s*["\']?[a-zA-Z0-9_\-\.\+@]{8,}["\']?', r'\1=[REDACTED_SECRET]', text)
    return text

class BrainGateway:
    def preflight_check(self, request: BrainRequest) -> BrainDecision:
        if not request.router_enabled:
            return BrainDecision(
                allowed=False,
                reason_code=ROUTER_DISABLED,
                next_action=NEXT_ACTIONS[ROUTER_DISABLED],
                message="AI Router đang bị tắt. Vui lòng kích hoạt trong cấu hình."
            )

        # Empty sources logic: UNKNOWN_DEFAULT_DENY
        if not request.sources:
            return BrainDecision(
                allowed=False,
                reason_code=UNKNOWN_DEFAULT_DENY,
                next_action=NEXT_ACTIONS[UNKNOWN_DEFAULT_DENY],
                message="Nguồn dữ liệu đang bật rỗng. Cần phân loại nguồn trước khi gửi AI cloud."
            )

        strictest = get_strictest_privacy(request.sources)

        # 1. Hard deny: local_only và confidential
        if strictest in {PRIVACY_LOCAL_ONLY, PRIVACY_CONFIDENTIAL}:
            rc = LOCAL_ONLY_HARD_DENY if strictest == PRIVACY_LOCAL_ONLY else CONFIDENTIAL_HARD_DENY
            return BrainDecision(
                allowed=False,
                reason_code=rc,
                next_action=NEXT_ACTIONS[rc],
                message=f"Chỉ trả lời bằng dữ liệu local. Nguồn dữ liệu có tính bảo mật cao ({strictest}) không được phép gửi ra ngoài."
            )

        current_hash = calculate_source_set_hash(request.sources)

        # 2. Default deny for unknown
        if strictest == PRIVACY_UNKNOWN:
            if not request.consent:
                return BrainDecision(
                    allowed=False,
                    reason_code=UNKNOWN_DEFAULT_DENY,
                    next_action=NEXT_ACTIONS[UNKNOWN_DEFAULT_DENY],
                    message="Nguồn dữ liệu chưa được phân loại bảo mật. Hãy phân loại nguồn trước khi gửi AI cloud."
                )
            if not request.consent.is_valid_for(current_hash, request.destination, request.purpose):
                return BrainDecision(
                    allowed=False,
                    reason_code=UNKNOWN_DEFAULT_DENY,
                    next_action=NEXT_ACTIONS[UNKNOWN_DEFAULT_DENY],
                    message="Xác nhận đồng ý không hợp lệ hoặc đã hết hạn."
                )

        # 3. Soft deny for machine_only
        if strictest == PRIVACY_MACHINE_ONLY:
            if not request.consent:
                return BrainDecision(
                    allowed=False,
                    reason_code=MACHINE_ONLY_NEEDS_CONSENT,
                    next_action=NEXT_ACTIONS[MACHINE_ONLY_NEEDS_CONSENT],
                    message="Nguồn dữ liệu yêu cầu sự xác nhận của Owner trước khi gửi lên AI cloud."
                )
            if not request.consent.is_valid_for(current_hash, request.destination, request.purpose):
                return BrainDecision(
                    allowed=False,
                    reason_code=MACHINE_ONLY_NEEDS_CONSENT,
                    next_action=NEXT_ACTIONS[MACHINE_ONLY_NEEDS_CONSENT],
                    message="Xác nhận đồng ý của Owner không hợp lệ hoặc đã hết hạn."
                )

        # Tiến hành làm sạch payload
        sanitized_question = sanitize_text(request.question)
        sanitized_sources: List[SanitizedSourcePayload] = []

        # Kiểm tra xem có bất kỳ nguồn nào là machine_only hoặc unknown không
        has_sensitive_source = any(_normalize_privacy_label(s.privacy_label) in {PRIVACY_MACHINE_ONLY, PRIVACY_UNKNOWN} for s in request.sources)

        for idx, s in enumerate(request.sources, 1):
            norm_label = _normalize_privacy_label(s.privacy_label)
            
            # Map scope bằng allow-list
            scope = s.source_scope.strip().lower() if s.source_scope else "unknown"
            if scope not in SAFE_SCOPES:
                scope = "unknown"

            # Map source_type bằng allow-list (Ngăn rò rỉ source_type thô)
            stype = s.source_type.strip().lower() if s.source_type else "unknown"
            if stype not in SAFE_SOURCE_TYPES:
                stype = "unknown"

            # Opaque ID
            opaque_id = f"source_{idx}"

            # Opaque/Sanitized Title
            if norm_label in {PRIVACY_LOCAL_ONLY, PRIVACY_CONFIDENTIAL, PRIVACY_MACHINE_ONLY, PRIVACY_UNKNOWN}:
                opaque_title = f"Nguồn đã làm sạch {idx}"
            else:
                opaque_title = sanitize_text(s.title)

            # Redacted marker an toàn
            if has_sensitive_source or norm_label in {PRIVACY_LOCAL_ONLY, PRIVACY_CONFIDENTIAL, PRIVACY_MACHINE_ONLY, PRIVACY_UNKNOWN}:
                if norm_label == PRIVACY_MACHINE_ONLY:
                    redacted_text = f"[redacted machine_only source {idx}]"
                elif norm_label == PRIVACY_UNKNOWN:
                    redacted_text = f"[redacted unknown source {idx}]"
                elif norm_label == PRIVACY_CONFIDENTIAL:
                    redacted_text = f"[redacted confidential source {idx}]"
                elif norm_label == PRIVACY_LOCAL_ONLY:
                    redacted_text = f"[redacted local_only source {idx}]"
                else:
                    redacted_text = f"[redacted source {idx}]"
            else:
                redacted_text = sanitize_text(s.text)

            sanitized_sources.append(SanitizedSourcePayload(
                source_id=opaque_id,
                source_scope=scope,
                source_type=stype,
                title=opaque_title,
                text=redacted_text,
                privacy_label=norm_label
            ))

        # Đóng gói SanitizedRouterPayload an toàn
        payload = SanitizedRouterPayload(
            sanitized_question=sanitized_question,
            sanitized_sources=tuple(sanitized_sources),
            metadata={
                "strictest_privacy": strictest,
                "source_set_hash": current_hash,
                "strictly_sanitized": True,
                "purpose": sanitize_text(request.purpose),
                "destination": sanitize_text(request.destination)
            }
        )

        # Xác định reason code thành công
        if strictest == PRIVACY_PUBLIC:
            rc = ROUTER_ALLOWED_PUBLIC
        elif strictest == PRIVACY_CLOUD_SAFE:
            rc = ROUTER_ALLOWED_CLOUD_SAFE
        else:
            rc = ROUTER_ALLOWED_OWNER_CONSENT

        return BrainDecision(
            allowed=True,
            reason_code=rc,
            next_action=NEXT_ACTIONS[rc],
            message="Yêu cầu được chấp nhận gửi tới AI Router.",
            sanitized_payload=payload
        )
