"""Windows OS Identity Provider for AIOS Habit.

Implements T010 of 010-expert-knowledge-acquisition.
Resolves authenticated caller principal directly from the Windows OS session.
Strictly zero-password storage and fail-closed design.
"""

from __future__ import annotations

import getpass
import os
import platform
from dataclasses import dataclass
from typing import Optional

from aios_habit.expert_identity import (
    IdentityProvider,
    IdentityProviderError,
    VerifiedPrincipal,
)
from aios_habit.feature_flags import (
    FEATURE_EXPERT_MULTI_USER,
    is_feature_enabled,
)


@dataclass(frozen=True)
class RecordedPersonSuggestion:
    """Editable responsibility metadata; it never represents authentication or authority."""

    suggested_name: str
    machine_ref: str
    is_verified: bool = False


def suggest_recorded_person() -> RecordedPersonSuggestion:
    """Suggest local OS metadata without turning it into an identity or grant."""
    try:
        name = getpass.getuser().strip()
    except Exception:
        name = ""
    return RecordedPersonSuggestion(
        suggested_name=name or "người dùng",
        machine_ref=platform.node().strip() or "máy hiện tại",
    )


class WindowsOSIdentityProvider:
    """Identity provider extracting principal credentials from current OS context.

    Operates in fail-closed mode. Does not persist or require any passwords.
    """

    def __init__(self, provider_name: str = "windows_os") -> None:
        self._provider_name = provider_name

    def get_provider_name(self) -> str:
        """Return provider name."""
        return self._provider_name

    def resolve_current_principal(self) -> Optional[VerifiedPrincipal]:
        """Resolve current authenticated Windows OS principal.

        Returns VerifiedPrincipal if valid identity is found, otherwise None.
        Raises IdentityProviderError on critical runtime ambiguity.
        """
        try:
            username = getpass.getuser()
        except Exception as exc:
            raise IdentityProviderError(
                f"Không thể xác định tài khoản người dùng hệ điều hành: {exc}"
            ) from exc

        if not username or not username.strip():
            return None

        username = username.strip()
        domain = os.environ.get("USERDOMAIN", "").strip()

        # Construct canonical OS subject string (e.g. DOMAIN\user or user)
        if domain and domain.upper() != platform.node().upper():
            subject = f"{domain}\\{username}"
        else:
            subject = username

        display_name = os.environ.get("USERDISPLAYNAME") or username

        return VerifiedPrincipal(
            subject=subject,
            provider_name=self._provider_name,
            display_name=display_name,
            metadata={
                "system": platform.system(),
                "node": platform.node(),
                "domain": domain,
            },
        )
