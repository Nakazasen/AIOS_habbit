import json
import pytest
from aios_habit.shared_ai_provider_fabric import get_shared_provider, load_shared_provider_fabric, providers_with_capability


def test_fabric_returns_public_secret_free_descriptors():
    gemini = get_shared_provider('gemini')
    assert gemini is not None
    assert gemini.api_key_env == 'GEMINI_API_KEY'
    assert 'agent_tool_calling' in gemini.capabilities
    public = gemini.public_dict()
    assert public['api_key_env'] == 'GEMINI_API_KEY'
    assert 'api_key' not in public


def test_fabric_rejects_invalid_schema(tmp_path):
    bad = tmp_path / 'bad.json'
    bad.write_text(json.dumps({'schema_version': 999, 'providers': []}), encoding='utf-8')
    with pytest.raises(ValueError): load_shared_provider_fabric(bad)


def test_fabric_filters_by_capability():
    providers = providers_with_capability('agent_tool_calling')
    assert {'gemini', 'nvidia', 'openai'}.issubset({provider.provider_id for provider in providers})
