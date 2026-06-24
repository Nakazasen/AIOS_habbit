from __future__ import annotations

from dataclasses import dataclass

from aios_habit.safety_modes import SAFETY_MODE_COMPANY, SAFETY_MODE_NORMAL

GROUP_LOCAL_INTERNAL = "Nguồn dùng trong máy / nội bộ"
GROUP_NORMAL_DOCS = "Nguồn AI cho tài liệu thường"
GROUP_CUSTOM = "Nguồn tự cấu hình"
STATUS_NOT_CONFIGURED = "not_configured"
STATUS_CONFIGURED = "configured"
STATUS_UNAVAILABLE = "unavailable"
STATUS_UNKNOWN = "unknown"
STATUS_LABELS_VI = {STATUS_NOT_CONFIGURED: "Chưa cấu hình", STATUS_CONFIGURED: "Đã cấu hình", STATUS_UNAVAILABLE: "Chưa sẵn sàng", STATUS_UNKNOWN: "Chưa kiểm tra"}
CAPABILITY_LABELS_VI = {"chat": "Hỏi đáp", "long_context": "Đọc tài liệu dài", "fast": "Phản hồi nhanh", "cheap_free": "Chi phí thấp / miễn phí", "coding": "Hỗ trợ kỹ thuật", "reasoning": "Lập luận tốt", "vision": "Hiểu hình ảnh"}

@dataclass(frozen=True)
class AIProviderProfile:
    provider_id: str
    display_name_vi: str
    short_description_vi: str
    provider_group: str
    endpoint_kind: str
    default_base_url: str = ""
    default_models: tuple[str, ...] = ()
    requires_api_key: bool = True
    supports_multiple_keys: bool = False
    supports_model_pool: bool = True
    supports_health_check: bool = False
    capabilities: tuple[str, ...] = ("chat",)
    safety_scope: str = "normal_docs_only"
    enabled_by_default: bool = False
    config_status: str = STATUS_NOT_CONFIGURED
    notes_vi: str = ""

    @property
    def status_label_vi(self) -> str:
        return STATUS_LABELS_VI.get(self.config_status, STATUS_LABELS_VI[STATUS_UNKNOWN])


def get_provider_catalog() -> tuple[AIProviderProfile, ...]:
    return (
        AIProviderProfile("openai_compatible_local", "AI trong máy tương thích OpenAI", "Dùng endpoint AI chạy trong máy hoặc mạng nội bộ.", GROUP_LOCAL_INTERNAL, "local_openai_compatible", "http://localhost:1234/v1", ("local-model",), False, False, True, True, ("chat", "coding", "reasoning"), "company_safe_possible", False, notes_vi="Phù hợp cho tài liệu công ty/mật nếu endpoint thật sự nằm trong máy hoặc mạng nội bộ."),
        AIProviderProfile("ollama", "Ollama", "AI chạy cục bộ qua Ollama.", GROUP_LOCAL_INTERNAL, "local_openai_compatible", "http://localhost:11434/v1", ("llama3.1", "qwen2.5"), False, False, True, True, ("chat", "coding", "reasoning"), "company_safe_possible", False, notes_vi="Không gửi ra ngoài nếu Ollama chạy trên máy/nội bộ."),
        AIProviderProfile("lm_studio", "LM Studio", "AI chạy trong máy qua LM Studio server.", GROUP_LOCAL_INTERNAL, "local_openai_compatible", "http://localhost:1234/v1", ("local-model",), False, False, True, True, ("chat", "coding", "reasoning"), "company_safe_possible", False, notes_vi="Phù hợp khi người dùng bật server nội bộ của LM Studio."),
        AIProviderProfile("nvidia_nim_local", "NVIDIA NIM nội bộ", "NIM tự triển khai trong mạng nội bộ.", GROUP_LOCAL_INTERNAL, "local_openai_compatible", "http://localhost:8000/v1", ("nvidia/local-model",), False, False, True, True, ("chat", "fast", "coding", "reasoning"), "company_safe_possible", False, notes_vi="Chỉ xem là an toàn cho tài liệu mật khi NIM nằm trong hạ tầng nội bộ."),
        AIProviderProfile("gemini", "Gemini", "Nguồn AI cloud mạnh cho tài liệu thường.", GROUP_NORMAL_DOCS, "native_api", default_models=("gemini-1.5-flash", "gemini-1.5-pro"), supports_multiple_keys=True, supports_health_check=True, capabilities=("chat", "long_context", "fast", "reasoning", "vision"), notes_vi="Không dùng cho tài liệu công ty/mật."),
        AIProviderProfile("openrouter", "OpenRouter", "Cổng tổng hợp nhiều mô hình AI, có lựa chọn miễn phí/quota miễn phí.", GROUP_NORMAL_DOCS, "cloud_openai_compatible", "https://openrouter.ai/api/v1", ("meta-llama/llama-3.3-70b-instruct:free", "meta-llama/llama-3.2-3b-instruct:free"), True, True, True, True, ("chat", "cheap_free", "reasoning", "coding"), notes_vi="Không dùng cho tài liệu công ty/mật."),
        AIProviderProfile("groq", "Groq", "AI cloud phản hồi nhanh, thường có quota miễn phí.", GROUP_NORMAL_DOCS, "cloud_openai_compatible", "https://api.groq.com/openai/v1", ("llama3-8b-8192", "gemma2-9b-it"), True, True, True, True, ("chat", "fast", "cheap_free"), notes_vi="Không dùng cho tài liệu công ty/mật."),
        AIProviderProfile("cerebras", "Cerebras", "AI cloud tốc độ cao cho tài liệu thường.", GROUP_NORMAL_DOCS, "cloud_openai_compatible", "https://api.cerebras.ai/v1", ("llama3.1-8b", "llama3.1-70b"), True, True, True, False, ("chat", "fast", "cheap_free"), notes_vi="Không dùng cho tài liệu công ty/mật."),
        AIProviderProfile("mistral", "Mistral AI", "AI cloud cho hỏi đáp và lập luận tài liệu thường.", GROUP_NORMAL_DOCS, "cloud_openai_compatible", "https://api.mistral.ai/v1", ("mistral-small-latest", "mistral-tiny"), True, True, True, False, ("chat", "reasoning", "coding"), notes_vi="Không dùng cho tài liệu công ty/mật."),
        AIProviderProfile("sambanova", "SambaNova", "AI cloud cho mô hình lớn/quota thử nghiệm.", GROUP_NORMAL_DOCS, "cloud_openai_compatible", "https://api.sambanova.ai/v1", ("DeepSeek-V3.1", "Llama-4-Maverick-17B-128E-Instruct"), True, True, True, False, ("chat", "reasoning", "coding"), notes_vi="Không dùng cho tài liệu công ty/mật."),
        AIProviderProfile("cloudflare_workers_ai", "Cloudflare Workers AI", "AI cloud qua tài khoản Cloudflare.", GROUP_NORMAL_DOCS, "native_api", "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run", ("@cf/meta/llama-3-8b-instruct",), True, False, True, False, ("chat", "cheap_free"), notes_vi="Không dùng cho tài liệu công ty/mật."),
        AIProviderProfile("huggingface", "Hugging Face", "Nguồn mô hình AI qua Hugging Face Inference.", GROUP_NORMAL_DOCS, "native_api", "https://api-inference.huggingface.co/models", ("meta-llama/Meta-Llama-3-8B-Instruct",), True, False, True, False, ("chat", "cheap_free"), notes_vi="Không dùng cho tài liệu công ty/mật."),
        AIProviderProfile("github_models", "GitHub Models", "AI cloud qua GitHub Models.", GROUP_NORMAL_DOCS, "cloud_openai_compatible", "https://models.inference.ai.azure.com", ("meta-llama-3-8b-instruct", "gpt-4o-mini"), True, False, True, False, ("chat", "coding", "cheap_free"), notes_vi="Không dùng cho tài liệu công ty/mật."),
        AIProviderProfile("ai21", "AI21 Studio", "AI cloud cho xử lý ngôn ngữ tài liệu thường.", GROUP_NORMAL_DOCS, "cloud_openai_compatible", "https://api.ai21.com/studio/v1", ("jamba-1.5-mini",), True, False, True, False, ("chat", "long_context", "reasoning"), notes_vi="Không dùng cho tài liệu công ty/mật."),
        AIProviderProfile("deepseek", "DeepSeek", "AI cloud mạnh về lập luận/kỹ thuật cho tài liệu thường.", GROUP_NORMAL_DOCS, "cloud_openai_compatible", "https://api.deepseek.com/v1", ("deepseek-chat", "deepseek-reasoner"), True, False, True, False, ("chat", "reasoning", "coding"), notes_vi="Không dùng cho tài liệu công ty/mật."),
        AIProviderProfile("chatanywhere", "ChatAnyWhere", "Nguồn OpenAI-compatible do người dùng tự đăng ký.", GROUP_NORMAL_DOCS, "cloud_openai_compatible", "https://api.chatanywhere.tech/v1", ("gpt-3.5-turbo",), True, True, True, False, ("chat", "cheap_free"), notes_vi="Không dùng cho tài liệu công ty/mật."),
        AIProviderProfile("custom_openai_compatible", "Nguồn OpenAI-compatible tự cấu hình", "Dành cho endpoint riêng của người dùng hoặc công ty.", GROUP_CUSTOM, "user_configured", requires_api_key=False, supports_multiple_keys=True, supports_health_check=True, capabilities=("chat", "coding", "reasoning", "long_context"), safety_scope="depends_on_endpoint", notes_vi="Chỉ dùng cho tài liệu công ty/mật khi endpoint được xác nhận là nội bộ/tin cậy."),
    )


def get_provider_profile(provider_id: str) -> AIProviderProfile | None:
    return next((p for p in get_provider_catalog() if p.provider_id == provider_id), None)


def list_provider_groups() -> tuple[str, ...]:
    groups = []
    for profile in get_provider_catalog():
        if profile.provider_group not in groups:
            groups.append(profile.provider_group)
    return tuple(groups)


def mask_secret(value: str | None) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    if len(token) <= 4:
        return "***"
    return f"****{token[-4:]}"


def summarize_provider_for_ui(profile: AIProviderProfile) -> dict[str, str]:
    if profile.safety_scope == "company_safe_possible":
        use_for = "Có thể dùng cho tài liệu công ty/mật nếu chạy trong máy hoặc nội bộ."
    elif profile.safety_scope == "depends_on_endpoint":
        use_for = "Phụ thuộc endpoint: chỉ dùng cho tài liệu mật khi đã xác nhận là nội bộ/tin cậy."
    else:
        use_for = "Được dùng khi tài liệu cho phép dùng nguồn AI bên ngoài."
    return {
        "name": profile.display_name_vi,
        "use_for": use_for,
        "api_key": "Cần khóa API" if profile.requires_api_key else "Không bắt buộc",
        "status": profile.status_label_vi,
        "notes": profile.notes_vi,
        "capabilities": ", ".join(CAPABILITY_LABELS_VI.get(item, item) for item in profile.capabilities),
    }


def is_provider_allowed_for_safety_mode(profile: AIProviderProfile, safety_mode: str, *, custom_endpoint_trusted: bool = False) -> bool:
    if safety_mode == SAFETY_MODE_COMPANY:
        return profile.safety_scope == "company_safe_possible" or (profile.provider_id == "custom_openai_compatible" and custom_endpoint_trusted)
    if safety_mode == SAFETY_MODE_NORMAL:
        return True
    return True


def provider_catalog_for_ui(safety_mode: str) -> tuple[dict[str, object], ...]:
    return tuple({"profile": p, "summary": summarize_provider_for_ui(p), "allowed": is_provider_allowed_for_safety_mode(p, safety_mode)} for p in get_provider_catalog())
