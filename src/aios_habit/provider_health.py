from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Iterable

from aios_habit.provider_catalog import get_provider_catalog

STATUS_HEALTHY = "healthy"
STATUS_COOLDOWN = "cooldown"
STATUS_DISABLED = "disabled"
STATUS_UNAVAILABLE = "unavailable"
STATUS_UNKNOWN = "unknown"

STATUS_LABELS_VI = {
    STATUS_HEALTHY: "Sẵn sàng",
    STATUS_COOLDOWN: "Đang tạm nghỉ",
    STATUS_DISABLED: "Bị tắt do lỗi xác thực",
    STATUS_UNAVAILABLE: "Chưa cấu hình",
    STATUS_UNKNOWN: "Chưa kiểm tra",
}

NO_KEY_ID = "khong-can-khoa"


@dataclass
class ProviderKeyState:
    key_id_masked: str
    status: str = STATUS_UNKNOWN
    failure_count: int = 0
    success_count: int = 0
    last_error_type: str = ""
    cooldown_until: float = 0.0
    last_used_at: float = 0.0


@dataclass
class ProviderHealthSnapshot:
    provider_id: str
    provider_name: str
    status: str = STATUS_UNKNOWN
    configured: bool = False
    enabled: bool = False
    active_key_id_masked: str = ""
    key_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_error_type: str = ""
    cooldown_until: float = 0.0
    note_vi: str = ""


def mask_key_id(secret: str | None) -> str:
    token = str(secret or "").strip()
    if not token:
        return NO_KEY_ID
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:8]
    suffix = token[-4:] if len(token) >= 4 else "***"
    return f"key-{digest}-****{suffix}"


def cooldown_seconds_for_error(error_type: str) -> int:
    return {
        "rate_limited": 600,
        "timeout": 120,
        "server_error": 120,
        "bad_response": 60,
    }.get(str(error_type or ""), 0)


def classify_health_status(key_states: Iterable[ProviderKeyState], configured: bool, enabled: bool, now: float | None = None) -> str:
    if not configured or not enabled:
        return STATUS_UNAVAILABLE
    now = time.time() if now is None else now
    states = list(key_states)
    if not states:
        return STATUS_UNKNOWN
    if any(state.status == STATUS_HEALTHY for state in states):
        return STATUS_HEALTHY
    if all(state.status == STATUS_DISABLED for state in states):
        return STATUS_DISABLED
    if all(state.status == STATUS_COOLDOWN and state.cooldown_until > now for state in states):
        return STATUS_COOLDOWN
    if any(state.status == STATUS_COOLDOWN and state.cooldown_until > now for state in states):
        return STATUS_COOLDOWN
    return STATUS_UNKNOWN


def vietnamese_health_note(snapshot: ProviderHealthSnapshot) -> str:
    if not snapshot.configured:
        return "Chưa có nguồn AI ngoài nào được cấu hình. AIOS vẫn trả lời bằng dữ liệu cục bộ."
    if not snapshot.enabled:
        return "Nguồn AI chưa bật trong phiên này."
    if snapshot.status == STATUS_HEALTHY:
        return "Nguồn AI sẵn sàng cho tài liệu thường khi chính sách an toàn cho phép."
    if snapshot.status == STATUS_COOLDOWN:
        return "Nguồn AI đang tạm nghỉ sau lỗi gần nhất; AIOS sẽ thử nguồn khác hoặc dữ liệu cục bộ."
    if snapshot.status == STATUS_DISABLED:
        return "Nguồn AI bị tắt trong phiên này do lỗi xác thực khóa."
    return "Chưa kiểm tra nguồn AI trong phiên này."


@dataclass
class ProviderHealthStore:
    key_states: dict[str, dict[str, ProviderKeyState]] = field(default_factory=dict)

    def get_provider_state(self, provider_id: str) -> dict[str, ProviderKeyState]:
        return self.key_states.setdefault(provider_id, {})

    def get_key_state(self, provider_id: str, key_id_masked: str) -> ProviderKeyState:
        provider_state = self.get_provider_state(provider_id)
        return provider_state.setdefault(key_id_masked, ProviderKeyState(key_id_masked))

    def record_success(self, provider_id: str, key_id_masked: str) -> ProviderKeyState:
        state = self.get_key_state(provider_id, key_id_masked)
        state.status = STATUS_HEALTHY
        state.success_count += 1
        state.failure_count = max(0, state.failure_count - 1)
        state.last_error_type = ""
        state.cooldown_until = 0.0
        state.last_used_at = time.time()
        return state

    def record_failure(self, provider_id: str, key_id_masked: str, error_type: str) -> ProviderKeyState:
        state = self.get_key_state(provider_id, key_id_masked)
        state.failure_count += 1
        state.last_error_type = error_type
        state.last_used_at = time.time()
        if error_type == "auth_error":
            state.status = STATUS_DISABLED
            state.cooldown_until = 0.0
        else:
            cooldown = cooldown_seconds_for_error(error_type)
            if cooldown:
                state.status = STATUS_COOLDOWN
                state.cooldown_until = time.time() + cooldown
            else:
                state.status = STATUS_UNKNOWN
        return state

    def is_key_available(self, provider_id: str, key_id_masked: str, now: float | None = None) -> bool:
        state = self.get_provider_state(provider_id).get(key_id_masked)
        if not state:
            return True
        now = time.time() if now is None else now
        if state.status == STATUS_DISABLED:
            return False
        if state.status == STATUS_COOLDOWN and state.cooldown_until > now:
            return False
        return True

    def is_provider_available(self, provider_id: str, keys: Iterable[str] | None = None) -> bool:
        keys = list(keys or [""])
        return any(self.is_key_available(provider_id, mask_key_id(key)) for key in keys)

    def choose_next_key(self, provider_id: str, keys: Iterable[str]) -> str | None:
        for key in keys:
            if self.is_key_available(provider_id, mask_key_id(key)):
                return key
        return None

    def snapshot(self, provider_configs: Iterable[Any]) -> list[ProviderHealthSnapshot]:
        snapshots = []
        for cfg in provider_configs:
            keys = _keys_from_config(cfg)
            configured = bool(getattr(cfg, "endpoint_url", "") and getattr(cfg, "model_name", ""))
            enabled = bool(getattr(cfg, "enabled", False))
            key_ids = [mask_key_id(key) for key in keys]
            states = [self.get_provider_state(cfg.provider_id).get(key_id) for key_id in key_ids]
            states = [state for state in states if state]
            status = classify_health_status(states, configured, enabled)
            active = ""
            next_key = self.choose_next_key(cfg.provider_id, keys)
            if next_key is not None:
                active = mask_key_id(next_key)
            snapshot = ProviderHealthSnapshot(
                provider_id=cfg.provider_id,
                provider_name=getattr(cfg, "display_name_vi", cfg.provider_id),
                status=status,
                configured=configured,
                enabled=enabled,
                active_key_id_masked=active,
                key_count=len(keys),
                success_count=sum(state.success_count for state in states),
                failure_count=sum(state.failure_count for state in states),
                last_error_type=next((state.last_error_type for state in states if state.last_error_type), ""),
                cooldown_until=max((state.cooldown_until for state in states), default=0.0),
            )
            snapshot.note_vi = vietnamese_health_note(snapshot)
            snapshots.append(snapshot)
        return snapshots


def _keys_from_config(config: Any) -> list[str]:
    keys = [str(key) for key in getattr(config, "api_keys", []) or [] if str(key).strip()]
    if keys:
        return keys
    api_key = str(getattr(config, "api_key", "") or "")
    return [api_key] if api_key else [""]


def provider_health_table_for_ui(
    provider_configs: Iterable[Any],
    health_store: ProviderHealthStore | None = None,
) -> list[dict[str, Any]]:
    health_store = health_store or ProviderHealthStore()
    snapshots_by_id = {snapshot.provider_id: snapshot for snapshot in health_store.snapshot(provider_configs)}
    rows: list[dict[str, Any]] = []
    for profile in get_provider_catalog():
        snapshot = snapshots_by_id.get(profile.provider_id)
        if snapshot is None:
            snapshot = ProviderHealthSnapshot(
                provider_id=profile.provider_id,
                provider_name=profile.display_name_vi,
                status=STATUS_UNAVAILABLE,
                configured=False,
                enabled=False,
                note_vi="Chưa cấu hình nguồn AI này.",
            )
        rows.append({
            "Nguồn AI": snapshot.provider_name,
            "Trạng thái": STATUS_LABELS_VI.get(snapshot.status, STATUS_LABELS_VI[STATUS_UNKNOWN]),
            "Đã cấu hình": "Có" if snapshot.configured and snapshot.enabled else "Không",
            "Khóa đang dùng": snapshot.active_key_id_masked or "Không",
            "Lần lỗi gần nhất": snapshot.last_error_type or "Không",
            "Ghi chú": snapshot.note_vi,
        })
    return rows
