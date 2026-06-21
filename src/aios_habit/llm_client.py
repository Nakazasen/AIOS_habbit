import os
import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional

class LLMConfigurationError(Exception):
    pass

@dataclass
class LLMConfig:
    provider: str
    base_url: str
    api_key: str
    model: str
    locality: str  # "local" or "cloud"
    timeout_seconds: int = 60
    max_prompt_chars: int = 12000

def load_llm_config() -> Optional[LLMConfig]:
    provider = os.getenv("AIOS_LLM_PROVIDER")
    if not provider:
        return None
        
    base_url = os.getenv("AIOS_LLM_BASE_URL", "http://localhost:11434/v1/chat/completions")
    api_key = os.getenv("AIOS_LLM_API_KEY", "")
    model = os.getenv("AIOS_LLM_MODEL", "local-model-name")
    locality = os.getenv("AIOS_LLM_LOCALITY", "local").lower()
    
    timeout_str = os.getenv("AIOS_LLM_TIMEOUT_SECONDS", "60")
    max_chars_str = os.getenv("AIOS_LLM_MAX_PROMPT_CHARS", "12000")
    
    try:
        timeout = int(timeout_str)
    except ValueError:
        timeout = 60
        
    try:
        max_prompt_chars = int(max_chars_str)
    except ValueError:
        max_prompt_chars = 12000
        
    return LLMConfig(
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        model=model,
        locality=locality,
        timeout_seconds=timeout,
        max_prompt_chars=max_prompt_chars
    )

def is_llm_configured() -> bool:
    return load_llm_config() is not None

def complete_chat(prompt: str, system_prompt: str = "", config: Optional[LLMConfig] = None) -> str:
    if config is None:
        config = load_llm_config()
        
    if config is None:
        raise LLMConfigurationError("AI provider chưa được cấu hình. Vui lòng thiết lập biến môi trường AIOS_LLM_PROVIDER.")
        
    # Check max prompt chars
    combined_len = len(prompt) + len(system_prompt)
    if combined_len > config.max_prompt_chars:
        allowed_len = config.max_prompt_chars - len(system_prompt) - 50
        if allowed_len > 0:
            prompt = prompt[:allowed_len] + "\n[ĐÃ BỊ CẮT BỚT VÌ VƯỢT QUÁ GIỚI HẠN KÝ TỰ]"
        else:
            raise ValueError("Prompt or System Prompt is too long and exceeds character limit.")
            
    payload = {
        "model": config.model,
        "messages": []
    }
    if system_prompt:
        payload["messages"].append({"role": "system", "content": system_prompt})
    payload["messages"].append({"role": "user", "content": prompt})
    
    headers = {
        "Content-Type": "application/json"
    }
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
        
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(config.base_url, data=data, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req, timeout=config.timeout_seconds) as response:
            res_data = response.read().decode("utf-8")
            res_json = json.loads(res_data)
            choices = res_json.get("choices", [])
            if not choices:
                raise RuntimeError(f"Phản hồi từ LLM không có 'choices': {res_data}")
            content = choices[0].get("message", {}).get("content", "")
            return content
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = ""
        raise RuntimeError(f"LLM API Error (HTTP {status}): {err_body}")
    except Exception as e:
        raise RuntimeError(f"Lỗi khi gọi LLM API: {e}")
