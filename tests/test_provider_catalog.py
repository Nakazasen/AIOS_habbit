from aios_habit.provider_catalog import (
    GROUP_CUSTOM,
    GROUP_LOCAL_INTERNAL,
    GROUP_NORMAL_DOCS,
    get_provider_catalog,
    get_provider_profile,
    is_provider_allowed_for_safety_mode,
    list_provider_groups,
    mask_secret,
    provider_catalog_for_ui,
)
from aios_habit.safety_modes import SAFETY_MODE_AUTO, SAFETY_MODE_COMPANY, SAFETY_MODE_NORMAL

EXPECTED_PROVIDERS = {
    "openai_compatible_local", "ollama", "lm_studio", "nvidia_nim_local",
    "gemini", "openrouter", "groq", "cerebras", "mistral", "sambanova",
    "cloudflare_workers_ai", "huggingface", "github_models", "ai21", "deepseek", "chatanywhere",
    "custom_openai_compatible",
}


def test_provider_catalog_contains_expected_providers():
    ids = {p.provider_id for p in get_provider_catalog()}
    assert EXPECTED_PROVIDERS <= ids
    assert len(ids) == len(get_provider_catalog())


def test_provider_groups_are_vietnamese_and_complete():
    groups = set(list_provider_groups())
    assert GROUP_LOCAL_INTERNAL in groups
    assert GROUP_NORMAL_DOCS in groups
    assert GROUP_CUSTOM in groups


def test_display_names_are_non_empty_and_not_raw_ids():
    for profile in get_provider_catalog():
        assert profile.display_name_vi.strip()
        assert profile.display_name_vi != profile.provider_id
        assert "cloud_allowed" not in profile.display_name_vi
        assert "local_only" not in profile.display_name_vi


def test_mask_secret():
    assert mask_secret("") == ""
    assert mask_secret(None) == ""
    assert mask_secret("abc") == "***"
    assert mask_secret("sk-secret-1234") == "****1234"


def test_company_mode_allows_only_internal_sources_by_default():
    allowed = {row["profile"].provider_id for row in provider_catalog_for_ui(SAFETY_MODE_COMPANY) if row["allowed"]}
    assert {"openai_compatible_local", "ollama", "lm_studio", "nvidia_nim_local"} <= allowed
    assert "gemini" not in allowed
    assert "openrouter" not in allowed
    assert "groq" not in allowed
    assert "custom_openai_compatible" not in allowed


def test_normal_docs_mode_allows_cloud_sources():
    for provider_id in ["gemini", "openrouter", "groq", "deepseek"]:
        profile = get_provider_profile(provider_id)
        assert profile is not None
        assert is_provider_allowed_for_safety_mode(profile, SAFETY_MODE_NORMAL)


def test_auto_mode_displays_all_sources_with_markers():
    rows = provider_catalog_for_ui(SAFETY_MODE_AUTO)
    ids = {row["profile"].provider_id for row in rows}
    assert EXPECTED_PROVIDERS <= ids
    assert any("tài liệu công ty/mật" in row["summary"]["use_for"] for row in rows)
    assert any("nguồn AI bên ngoài" in row["summary"]["use_for"] for row in rows)
