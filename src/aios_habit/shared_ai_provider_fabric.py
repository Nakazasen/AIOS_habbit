"""Versioned, secret-free AI provider registry shared by AIOS Agent surfaces."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parents[2] / 'config' / 'shared_ai_provider_fabric.json'


@dataclass(frozen=True)
class SharedProviderDescriptor:
    provider_id: str
    display_name: str
    endpoint_kind: str
    base_url_env: str
    default_base_url: str
    api_key_env: str
    model_env: str
    default_model: str
    capabilities: tuple[str, ...]
    safety_scope: str
    enabled_by_default: bool

    def public_dict(self) -> dict[str, Any]:
        return {
            'provider_id': self.provider_id, 'display_name': self.display_name,
            'endpoint_kind': self.endpoint_kind, 'base_url_env': self.base_url_env,
            'default_base_url': self.default_base_url, 'api_key_env': self.api_key_env,
            'model_env': self.model_env, 'default_model': self.default_model,
            'capabilities': self.capabilities, 'safety_scope': self.safety_scope,
            'enabled_by_default': self.enabled_by_default,
        }


def load_shared_provider_fabric(path: str | Path | None = None) -> tuple[SharedProviderDescriptor, ...]:
    registry_path = Path(path) if path is not None else DEFAULT_REGISTRY_PATH
    try:
        raw = json.loads(registry_path.read_text(encoding='utf-8-sig'))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError('Shared AI Provider Fabric không hợp lệ hoặc chưa sẵn sàng.') from error
    if raw.get('schema_version') != 1 or not isinstance(raw.get('providers'), list):
        raise ValueError('Shared AI Provider Fabric có schema không được hỗ trợ.')
    descriptors = []
    seen = set()
    required = {'provider_id', 'display_name', 'endpoint_kind', 'base_url_env', 'default_base_url', 'api_key_env', 'model_env', 'default_model', 'capabilities', 'safety_scope', 'enabled_by_default'}
    for item in raw['providers']:
        if not isinstance(item, dict) or set(item) & required != required:
            raise ValueError('Shared AI Provider Fabric thiếu trường bắt buộc.')
        provider_id = str(item['provider_id']).strip()
        if not provider_id or provider_id in seen or not isinstance(item['capabilities'], list):
            raise ValueError('Shared AI Provider Fabric chứa provider không hợp lệ.')
        seen.add(provider_id)
        descriptors.append(SharedProviderDescriptor(
            provider_id=provider_id, display_name=str(item['display_name']), endpoint_kind=str(item['endpoint_kind']),
            base_url_env=str(item['base_url_env']), default_base_url=str(item['default_base_url']),
            api_key_env=str(item['api_key_env']), model_env=str(item['model_env']), default_model=str(item['default_model']),
            capabilities=tuple(str(capability) for capability in item['capabilities']),
            safety_scope=str(item['safety_scope']), enabled_by_default=bool(item['enabled_by_default']),
        ))
    return tuple(descriptors)


def get_shared_provider(provider_id: str, *, path: str | Path | None = None) -> SharedProviderDescriptor | None:
    return next((provider for provider in load_shared_provider_fabric(path) if provider.provider_id == provider_id), None)


def providers_with_capability(capability: str, *, path: str | Path | None = None) -> tuple[SharedProviderDescriptor, ...]:
    return tuple(provider for provider in load_shared_provider_fabric(path) if capability in provider.capabilities)
