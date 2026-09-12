"""Feature flags configuration for AIOS Habit.

Provides fail-closed feature toggles for experimental and gradual rollouts,
consolidated into a single flag for Goal 010 (Expert Knowledge Acquisition).
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, Iterator


# Single canonical feature flag for Goal 010 Expert Knowledge Acquisition
FEATURE_EXPERT_KNOWLEDGE_ACQUISITION = "expert_knowledge_acquisition"

# Compatibility aliases pointing to the consolidated flag
FEATURE_EXPERT_COVERAGE = FEATURE_EXPERT_KNOWLEDGE_ACQUISITION
FEATURE_EXPERT_INTERVIEW = FEATURE_EXPERT_KNOWLEDGE_ACQUISITION
FEATURE_EXPERT_AUDIO = FEATURE_EXPERT_KNOWLEDGE_ACQUISITION
FEATURE_EXPERT_PUBLICATION = FEATURE_EXPERT_KNOWLEDGE_ACQUISITION

# Independent legacy multi-user flag (kept separate to avoid turning on legacy RBAC when Goal 010 is active)
FEATURE_EXPERT_MULTI_USER = "expert_multi_user"

# Goal 011 adaptive Workspace Chat memory loop (fail-closed; default off)
FEATURE_ADAPTIVE_WORK_MEMORY = "adaptive_work_memory"

# Consolidated Goal 010 feature set (single flag)
ALL_010_FEATURES = (
    FEATURE_EXPERT_KNOWLEDGE_ACQUISITION,
)


@dataclass(frozen=True)
class FeatureFlagState:
    """Immutable state snapshot of feature flags."""

    expert_knowledge_acquisition: bool = False
    expert_multi_user: bool = False
    adaptive_work_memory: bool = False

    @property
    def expert_knowledge_coverage(self) -> bool:
        return self.expert_knowledge_acquisition

    @property
    def expert_interview(self) -> bool:
        return self.expert_knowledge_acquisition

    @property
    def expert_interview_audio(self) -> bool:
        return self.expert_knowledge_acquisition

    @property
    def expert_knowledge_publication(self) -> bool:
        return self.expert_knowledge_acquisition

    def to_dict(self) -> Dict[str, bool]:
        """Convert flags to dictionary representation."""
        return {
            FEATURE_EXPERT_KNOWLEDGE_ACQUISITION: self.expert_knowledge_acquisition,
            FEATURE_EXPERT_MULTI_USER: self.expert_multi_user,
            FEATURE_ADAPTIVE_WORK_MEMORY: self.adaptive_work_memory,
        }

    def is_enabled(self, flag_name: str) -> bool:
        """Check if a specific flag is enabled."""
        if flag_name in (
            FEATURE_EXPERT_KNOWLEDGE_ACQUISITION,
            "expert_knowledge_coverage",
            "expert_interview",
            "expert_interview_audio",
            "expert_knowledge_publication",
        ):
            return self.expert_knowledge_acquisition
        if flag_name in (FEATURE_EXPERT_MULTI_USER, "expert_multi_user"):
            return self.expert_multi_user
        if flag_name in (FEATURE_ADAPTIVE_WORK_MEMORY, "adaptive_work_memory"):
            return self.adaptive_work_memory
        return False


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

    def _canonical_name(self, flag_name: str) -> str:
        if flag_name in (
            FEATURE_EXPERT_KNOWLEDGE_ACQUISITION,
            "expert_knowledge_coverage",
            "expert_interview",
            "expert_interview_audio",
            "expert_knowledge_publication",
        ):
            return FEATURE_EXPERT_KNOWLEDGE_ACQUISITION
        if flag_name in (FEATURE_EXPERT_MULTI_USER, "expert_multi_user"):
            return FEATURE_EXPERT_MULTI_USER
        if flag_name in (FEATURE_ADAPTIVE_WORK_MEMORY, "adaptive_work_memory"):
            return FEATURE_ADAPTIVE_WORK_MEMORY
        return flag_name

    def get_flag(self, flag_name: str) -> bool:
        """Get current state of a flag, respecting overrides and environment."""
        canonical = self._canonical_name(flag_name)
        if canonical in self._overrides:
            return self._overrides[canonical]
        if flag_name in self._overrides:
            return self._overrides[flag_name]

        # Environment variable convention: AIOS_FEATURE_<FLAG_NAME_UPPER>
        env_key = f"AIOS_FEATURE_{canonical.upper()}"
        return self._env_bool(env_key, default=False)

    def set_override(self, flag_name: str, enabled: bool) -> None:
        """Set an in-memory override for a flag."""
        canonical = self._canonical_name(flag_name)
        self._overrides[canonical] = bool(enabled)
        self._overrides[flag_name] = bool(enabled)

    def clear_override(self, flag_name: str) -> None:
        """Clear an override for a flag."""
        canonical = self._canonical_name(flag_name)
        self._overrides.pop(canonical, None)
        self._overrides.pop(flag_name, None)

    def reset_all_overrides(self) -> None:
        """Reset all in-memory overrides."""
        self._overrides.clear()

    def snapshot(self) -> FeatureFlagState:
        """Produce an immutable snapshot of all current flags."""
        return FeatureFlagState(
            expert_knowledge_acquisition=self.get_flag(FEATURE_EXPERT_KNOWLEDGE_ACQUISITION),
            expert_multi_user=self.get_flag(FEATURE_EXPERT_MULTI_USER),
            adaptive_work_memory=self.get_flag(FEATURE_ADAPTIVE_WORK_MEMORY),
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
        with override_feature_flags(expert_knowledge_acquisition=True):
            assert is_feature_enabled(FEATURE_EXPERT_KNOWLEDGE_ACQUISITION) is True
    """
    old_overrides = dict(_GLOBAL_REGISTRY._overrides)
    try:
        for k, v in kwargs.items():
            _GLOBAL_REGISTRY.set_override(k, v)
        yield _GLOBAL_REGISTRY.snapshot()
    finally:
        _GLOBAL_REGISTRY._overrides = old_overrides
