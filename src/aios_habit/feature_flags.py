"""Feature flags configuration for AIOS Habit.

Provides fail-closed feature toggles for experimental and gradual rollouts,
specifically for feature 010 (Expert Knowledge Acquisition).
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, Iterator


# Feature flag key constants for 010-expert-knowledge-acquisition
FEATURE_EXPERT_COVERAGE = "expert_knowledge_coverage"
FEATURE_EXPERT_INTERVIEW = "expert_interview"
FEATURE_EXPERT_AUDIO = "expert_interview_audio"
FEATURE_EXPERT_PUBLICATION = "expert_knowledge_publication"
FEATURE_EXPERT_MULTI_USER = "expert_multi_user"

# All flags of 010 feature set
ALL_010_FEATURES = (
    FEATURE_EXPERT_COVERAGE,
    FEATURE_EXPERT_INTERVIEW,
    FEATURE_EXPERT_AUDIO,
    FEATURE_EXPERT_PUBLICATION,
    FEATURE_EXPERT_MULTI_USER,
)


@dataclass(frozen=True)
class FeatureFlagState:
    """Immutable state snapshot of feature flags."""

    expert_knowledge_coverage: bool = False
    expert_interview: bool = False
    expert_interview_audio: bool = False
    expert_knowledge_publication: bool = False
    expert_multi_user: bool = False

    def to_dict(self) -> Dict[str, bool]:
        """Convert flags to dictionary representation."""
        return {
            FEATURE_EXPERT_COVERAGE: self.expert_knowledge_coverage,
            FEATURE_EXPERT_INTERVIEW: self.expert_interview,
            FEATURE_EXPERT_AUDIO: self.expert_interview_audio,
            FEATURE_EXPERT_PUBLICATION: self.expert_knowledge_publication,
            FEATURE_EXPERT_MULTI_USER: self.expert_multi_user,
        }

    def is_enabled(self, flag_name: str) -> bool:
        """Check if a specific flag is enabled."""
        mapping = self.to_dict()
        return mapping.get(flag_name, False)


class FeatureFlagRegistry:
    """Thread-safe and test-friendly registry for feature flags."""

    def __init__(self) -> None:
        self._overrides: Dict[str, bool] = {}

    def _env_bool(self, env_var: str, default: bool = False) -> bool:
        """Read boolean from environment variable."""
        val = os.environ.get(env_var, "").strip().lower()
        if not val:
            return default
        return val in ("1", "true", "yes", "on")

    def get_flag(self, flag_name: str) -> bool:
        """Get current state of a flag, respecting overrides and environment."""
        if flag_name in self._overrides:
            return self._overrides[flag_name]

        # Environment variable convention: AIOS_FEATURE_<FLAG_NAME_UPPER>
        env_key = f"AIOS_FEATURE_{flag_name.upper()}"
        return self._env_bool(env_key, default=False)

    def set_override(self, flag_name: str, enabled: bool) -> None:
        """Set an in-memory override for a flag."""
        self._overrides[flag_name] = bool(enabled)

    def clear_override(self, flag_name: str) -> None:
        """Clear an override for a flag."""
        self._overrides.pop(flag_name, None)

    def reset_all_overrides(self) -> None:
        """Reset all in-memory overrides."""
        self._overrides.clear()

    def snapshot(self) -> FeatureFlagState:
        """Produce an immutable snapshot of all current flags."""
        return FeatureFlagState(
            expert_knowledge_coverage=self.get_flag(FEATURE_EXPERT_COVERAGE),
            expert_interview=self.get_flag(FEATURE_EXPERT_INTERVIEW),
            expert_interview_audio=self.get_flag(FEATURE_EXPERT_AUDIO),
            expert_knowledge_publication=self.get_flag(FEATURE_EXPERT_PUBLICATION),
            expert_multi_user=self.get_flag(FEATURE_EXPERT_MULTI_USER),
        )


# Global singleton registry
_GLOBAL_REGISTRY = FeatureFlagRegistry()


def is_feature_enabled(flag_name: str) -> bool:
    """Global helper to check if a feature flag is enabled (default False)."""
    return _GLOBAL_REGISTRY.get_flag(flag_name)


def set_feature_flag(flag_name: str, enabled: bool) -> None:
    """Global helper to set an override for a feature flag."""
    _GLOBAL_REGISTRY.set_override(flag_name, enabled)


def reset_feature_flags() -> None:
    """Global helper to reset all overrides."""
    _GLOBAL_REGISTRY.reset_all_overrides()


def get_feature_snapshot() -> FeatureFlagState:
    """Get current snapshot of all feature flags."""
    return _GLOBAL_REGISTRY.snapshot()


@contextmanager
def override_feature_flags(**kwargs: bool) -> Iterator[FeatureFlagState]:
    """Context manager to temporarily override feature flags during testing.

    Example:
        with override_feature_flags(expert_interview=True):
            assert is_feature_enabled("expert_interview") is True
    """
    old_overrides = dict(_GLOBAL_REGISTRY._overrides)
    try:
        for k, v in kwargs.items():
            _GLOBAL_REGISTRY.set_override(k, v)
        yield _GLOBAL_REGISTRY.snapshot()
    finally:
        _GLOBAL_REGISTRY._overrides = old_overrides
