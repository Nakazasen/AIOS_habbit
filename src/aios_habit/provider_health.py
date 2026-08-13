from __future__ import annotations

import hashlib
import json
import math
import random
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from aios_habit.provider_catalog import get_provider_catalog

STATUS_HEALTHY = "healthy"
STATUS_COOLDOWN = "cooldown"
STATUS_DISABLED = "disabled"
STATUS_UNAVAILABLE = "unavailable"
STATUS_UNKNOWN = "unknown"

CIRCUIT_CLOSED = "closed"
CIRCUIT_DEGRADED = "degraded"
CIRCUIT_OPEN = "open"
CIRCUIT_HALF_OPEN = "half_open"

STATUS_LABELS_VI = {
    STATUS_HEALTHY: "Sẵn sàng",
    STATUS_COOLDOWN: "Đang tạm nghỉ",
    STATUS_DISABLED: "Bị tắt do lỗi xác thực",
    STATUS_UNAVAILABLE: "Chưa cấu hình",
    STATUS_UNKNOWN: "Chưa kiểm tra",
}

NO_KEY_ID = "khong-can-khoa"
_TRANSIENT_PROVIDER_ERRORS = frozenset({"timeout", "server_error", "network_error"})
_MODEL_ERRORS = frozenset({
    "model_not_found",
    "model_unsupported",
    "invalid_model",
    "invalid_output",
    "bad_response",
})


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
class ProviderCircuitState:
    provider_id: str
    status: str = CIRCUIT_CLOSED
    consecutive_failures: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_error_type: str = ""
    opened_until: float = 0.0
    half_open_in_flight: bool = False
    last_success_at: float = 0.0
    latency_ewma_ms: float = 0.0


@dataclass
class ModelHealthState:
    provider_id: str
    key_id_masked: str
    model_id: str
    status: str = STATUS_UNKNOWN
    failure_count: int = 0
    success_count: int = 0
    last_error_type: str = ""
    lockout_until: float = 0.0
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
    circuit_status: str = CIRCUIT_CLOSED
    circuit_open_until: float = 0.0
    model_lockout_count: int = 0
    latency_ewma_ms: float = 0.0


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
        "network_error": 120,
        "bad_response": 60,
        "model_not_found": 900,
        "model_unsupported": 900,
        "invalid_model": 900,
    }.get(str(error_type or ""), 0)


def classify_health_status(
    key_states: Iterable[ProviderKeyState],
    configured: bool,
    enabled: bool,
    now: float | None = None,
) -> str:
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
    if any(state.status == STATUS_COOLDOWN and state.cooldown_until > now for state in states):
        return STATUS_COOLDOWN
    return STATUS_UNKNOWN


def vietnamese_health_note(snapshot: ProviderHealthSnapshot) -> str:
    if not snapshot.configured:
        return "Chưa có nguồn AI ngoài nào được cấu hình. AIOS vẫn trả lời bằng dữ liệu cục bộ."
    if not snapshot.enabled:
        return "Nguồn AI chưa bật trong phiên này."
    if snapshot.circuit_status == CIRCUIT_OPEN:
        return "Nguồn AI đang tạm nghỉ sau lỗi hệ thống; AIOS sẽ thử nguồn khác hoặc dữ liệu cục bộ."
    if snapshot.circuit_status == CIRCUIT_HALF_OPEN:
        return "Nguồn AI đang được thử phục hồi có kiểm soát."
    if snapshot.status == STATUS_HEALTHY:
        return "Nguồn AI sẵn sàng cho tài liệu thường khi chính sách an toàn cho phép."
    if snapshot.status == STATUS_COOLDOWN:
        return "Nguồn AI đang tạm nghỉ sau lỗi gần nhất; AIOS sẽ thử nguồn khác hoặc dữ liệu cục bộ."
    if snapshot.status == STATUS_DISABLED:
        return "Nguồn AI bị tắt trong phiên này do lỗi xác thực khóa."
    return "Chưa kiểm tra nguồn AI trong phiên này."


@dataclass
class ProviderHealthStore:
    """Redacted health state for provider, key, and model failure isolation.

    State deliberately excludes prompts, source names, raw exceptions and raw keys.
    It can be persisted safely as JSON for a bounded process/run lifetime.
    """

    key_states: dict[str, dict[str, ProviderKeyState]] = field(default_factory=dict)
    circuit_states: dict[str, ProviderCircuitState] = field(default_factory=dict)
    model_states: dict[str, ModelHealthState] = field(default_factory=dict)
    circuit_failure_threshold: int = 3
    circuit_cooldown_seconds: float = 90.0
    max_backoff_seconds: float = 3600.0
    _clock: Callable[[], float] = field(default=time.time, repr=False, compare=False)

    @staticmethod
    def model_state_key(provider_id: str, key_id_masked: str, model_id: str) -> str:
        return f"{provider_id}|{key_id_masked}|{str(model_id or '').strip()}"

    def now(self) -> float:
        return float(self._clock())

    def get_provider_state(self, provider_id: str) -> dict[str, ProviderKeyState]:
        return self.key_states.setdefault(provider_id, {})

    def get_key_state(self, provider_id: str, key_id_masked: str) -> ProviderKeyState:
        provider_state = self.get_provider_state(provider_id)
        return provider_state.setdefault(key_id_masked, ProviderKeyState(key_id_masked))

    def get_circuit_state(self, provider_id: str) -> ProviderCircuitState:
        return self.circuit_states.setdefault(provider_id, ProviderCircuitState(provider_id))

    def get_model_state(
        self,
        provider_id: str,
        key_id_masked: str,
        model_id: str,
    ) -> ModelHealthState:
        identity = self.model_state_key(provider_id, key_id_masked, model_id)
        return self.model_states.setdefault(
            identity,
            ModelHealthState(provider_id, key_id_masked, str(model_id or "")),
        )

    def _backoff_seconds(
        self,
        error_type: str,
        failure_count: int,
        retry_after_seconds: float | None = None,
    ) -> float:
        if retry_after_seconds is not None:
            try:
                hinted = float(retry_after_seconds)
            except (TypeError, ValueError):
                hinted = 0.0
            if hinted > 0:
                return min(self.max_backoff_seconds, hinted)
        base = float(cooldown_seconds_for_error(error_type))
        if base <= 0:
            return 0.0
        exponent = max(0, min(int(failure_count) - 1, 6))
        return min(self.max_backoff_seconds, base * (2**exponent))

    def record_success(
        self,
        provider_id: str,
        key_id_masked: str,
        *,
        model_id: str = "",
        latency_ms: float | None = None,
    ) -> ProviderKeyState:
        now = self.now()
        state = self.get_key_state(provider_id, key_id_masked)
        state.status = STATUS_HEALTHY
        state.success_count += 1
        state.failure_count = max(0, state.failure_count - 1)
        state.last_error_type = ""
        state.cooldown_until = 0.0
        state.last_used_at = now
        circuit = self.get_circuit_state(provider_id)
        circuit.status = CIRCUIT_CLOSED
        circuit.consecutive_failures = 0
        circuit.success_count += 1
        circuit.last_error_type = ""
        circuit.opened_until = 0.0
        circuit.half_open_in_flight = False
        circuit.last_success_at = now
        if latency_ms is not None:
            sample = max(0.0, float(latency_ms))
            circuit.latency_ewma_ms = sample if not circuit.latency_ewma_ms else (
                (0.25 * sample) + (0.75 * circuit.latency_ewma_ms)
            )
        if model_id:
            model = self.get_model_state(provider_id, key_id_masked, model_id)
            model.status = STATUS_HEALTHY
            model.success_count += 1
            model.failure_count = max(0, model.failure_count - 1)
            model.last_error_type = ""
            model.lockout_until = 0.0
            model.last_used_at = now
        return state

    def record_failure(
        self,
        provider_id: str,
        key_id_masked: str,
        error_type: str,
        *,
        model_id: str = "",
        retry_after_seconds: float | None = None,
        provider_scoped: bool | None = None,
    ) -> ProviderKeyState:
        now = self.now()
        error_type = str(error_type or "unknown_error")
        state = self.get_key_state(provider_id, key_id_masked)
        state.failure_count += 1
        state.last_error_type = error_type
        state.last_used_at = now
        is_provider_failure = (
            provider_scoped
            if provider_scoped is not None
            else error_type in _TRANSIENT_PROVIDER_ERRORS
        )

        model_scoped = bool(model_id) and error_type in _MODEL_ERRORS | {"invalid_output"}
        if model_scoped:
            model = self.get_model_state(provider_id, key_id_masked, model_id)
            model.failure_count += 1
            model.last_error_type = error_type
            model.last_used_at = now
            lockout = self._backoff_seconds(error_type, model.failure_count, retry_after_seconds)
            model.status = STATUS_COOLDOWN if lockout else STATUS_UNKNOWN
            model.lockout_until = now + lockout if lockout else 0.0
            # The key can still serve another permitted model.
            state.status = STATUS_UNKNOWN
            state.cooldown_until = 0.0
        elif error_type == "auth_error":
            state.status = STATUS_DISABLED
            state.cooldown_until = 0.0
        elif error_type in {"rate_limited", "timeout"} or (
            error_type == "network_error" and not is_provider_failure
        ):
            # A transient response is attributable to the credential attempt: pause
            # this key briefly while the provider circuit independently tracks
            # provider-wide health. Auth failures remain permanently disabled.
            cooldown = self._backoff_seconds(error_type, state.failure_count, retry_after_seconds)
            state.status = STATUS_COOLDOWN if cooldown else STATUS_UNKNOWN
            state.cooldown_until = now + cooldown if cooldown else 0.0
        else:
            state.status = STATUS_UNKNOWN
            state.cooldown_until = 0.0

        if is_provider_failure:
            circuit = self.get_circuit_state(provider_id)
            circuit.failure_count += 1
            circuit.consecutive_failures += 1
            circuit.last_error_type = error_type
            circuit.half_open_in_flight = False
            if circuit.consecutive_failures >= max(1, self.circuit_failure_threshold):
                circuit.status = CIRCUIT_OPEN
                circuit.opened_until = now + self._backoff_seconds(
                    error_type,
                    circuit.consecutive_failures - self.circuit_failure_threshold + 1,
                    retry_after_seconds,
                )
            else:
                circuit.status = CIRCUIT_DEGRADED
        return state

    def is_provider_available(self, provider_id: str, keys: Iterable[str] | None = None) -> bool:
        if not self.begin_provider_attempt(provider_id):
            return False
        keys = list(keys or [""])
        return any(self.is_key_available(provider_id, mask_key_id(key)) for key in keys)

    def begin_provider_attempt(self, provider_id: str, now: float | None = None) -> bool:
        now = self.now() if now is None else now
        state = self.get_circuit_state(provider_id)
        if state.status != CIRCUIT_OPEN:
            return not (state.status == CIRCUIT_HALF_OPEN and state.half_open_in_flight)
        if state.opened_until > now:
            return False
        if state.half_open_in_flight:
            return False
        state.status = CIRCUIT_HALF_OPEN
        state.half_open_in_flight = True
        return True

    def is_key_available(self, provider_id: str, key_id_masked: str, now: float | None = None) -> bool:
        state = self.get_provider_state(provider_id).get(key_id_masked)
        if not state:
            return True
        now = self.now() if now is None else now
        if state.status == STATUS_DISABLED:
            return False
        if state.status == STATUS_COOLDOWN and state.cooldown_until > now:
            return False
        return True

    def is_model_available(
        self,
        provider_id: str,
        key_id_masked: str,
        model_id: str,
        now: float | None = None,
    ) -> bool:
        if not model_id:
            return True
        state = self.model_states.get(self.model_state_key(provider_id, key_id_masked, model_id))
        if not state:
            return True
        now = self.now() if now is None else now
        return not (state.status in {STATUS_DISABLED, STATUS_COOLDOWN} and state.lockout_until > now)

    def choose_next_key(self, provider_id: str, keys: Iterable[str], model_id: str = "") -> str | None:
        for key in keys:
            key_id = mask_key_id(key)
            if self.is_key_available(provider_id, key_id) and self.is_model_available(provider_id, key_id, model_id):
                return key
        return None

    def cleanup_expired(self, now: float | None = None) -> None:
        now = self.now() if now is None else now
        for provider in self.key_states.values():
            for state in provider.values():
                if state.status == STATUS_COOLDOWN and state.cooldown_until <= now:
                    state.status = STATUS_UNKNOWN
                    state.cooldown_until = 0.0
        for state in self.model_states.values():
            if state.status == STATUS_COOLDOWN and state.lockout_until <= now:
                state.status = STATUS_UNKNOWN
                state.lockout_until = 0.0
        for state in self.circuit_states.values():
            if state.status == CIRCUIT_OPEN and state.opened_until <= now:
                state.status = CIRCUIT_HALF_OPEN
                state.half_open_in_flight = False

    def export_state(self) -> dict[str, Any]:
        self.cleanup_expired()
        return {
            "schema_version": 1,
            "key_states": {
                provider: {key: asdict(state) for key, state in states.items()}
                for provider, states in self.key_states.items()
            },
            "circuit_states": {provider: asdict(state) for provider, state in self.circuit_states.items()},
            "model_states": {identity: asdict(state) for identity, state in self.model_states.items()},
        }

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(json.dumps(self.export_state(), ensure_ascii=False, sort_keys=True), encoding="utf-8")
        temporary.replace(destination)

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        clock: Callable[[], float] = time.time,
    ) -> "ProviderHealthStore":
        destination = Path(path)
        store = cls(_clock=clock)
        if not destination.exists():
            return store
        try:
            data = json.loads(destination.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return store
        if not isinstance(data, Mapping) or data.get("schema_version") != 1:
            return store
        for provider, states in dict(data.get("key_states") or {}).items():
            if isinstance(states, Mapping):
                store.key_states[str(provider)] = {
                    str(key): ProviderKeyState(**dict(value))
                    for key, value in states.items() if isinstance(value, Mapping)
                }
        for provider, value in dict(data.get("circuit_states") or {}).items():
            if isinstance(value, Mapping):
                store.circuit_states[str(provider)] = ProviderCircuitState(**dict(value))
        for identity, value in dict(data.get("model_states") or {}).items():
            if isinstance(value, Mapping):
                store.model_states[str(identity)] = ModelHealthState(**dict(value))
        store.cleanup_expired()
        return store

    def snapshot(self, provider_configs: Iterable[Any]) -> list[ProviderHealthSnapshot]:
        now = self.now()
        self.cleanup_expired(now)
        snapshots = []
        for cfg in provider_configs:
            keys = _keys_from_config(cfg)
            configured = bool(getattr(cfg, "endpoint_url", "") and getattr(cfg, "model_name", ""))
            enabled = bool(getattr(cfg, "enabled", False))
            key_ids = [mask_key_id(key) for key in keys]
            states = [self.get_provider_state(cfg.provider_id).get(key_id) for key_id in key_ids]
            states = [state for state in states if state]
            circuit = self.get_circuit_state(cfg.provider_id)
            status = classify_health_status(states, configured, enabled, now)
            if configured and enabled and circuit.status == CIRCUIT_OPEN and circuit.opened_until > now:
                status = STATUS_COOLDOWN
            active = ""
            next_key = self.choose_next_key(cfg.provider_id, keys, getattr(cfg, "model_name", ""))
            if next_key is not None and self.begin_provider_attempt(cfg.provider_id, now):
                active = mask_key_id(next_key)
                circuit.half_open_in_flight = False
            model_locks = [
                state for state in self.model_states.values()
                if state.provider_id == cfg.provider_id and state.status == STATUS_COOLDOWN and state.lockout_until > now
            ]
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
                last_error_type=next((state.last_error_type for state in states if state.last_error_type), circuit.last_error_type),
                cooldown_until=max([*(state.cooldown_until for state in states), circuit.opened_until], default=0.0),
                circuit_status=circuit.status,
                circuit_open_until=circuit.opened_until,
                model_lockout_count=len(model_locks),
                latency_ewma_ms=round(circuit.latency_ewma_ms, 2),
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
