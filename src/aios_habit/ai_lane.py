"""Tu dong chon lane AI (UX-CHAT-CORE #3): he thong tu chon, khong bat doi tay.

Thu tu uu tien: Gemini qua cau noi (khi bridge san sang) -> C-Agent (khi da
cau hinh endpoint) -> Nakazasen Router (khi co khoa cloud va khong bi
cooldown) -> cuc bo (luon kha dung, khong goi AI ngoai).

- Lua chon duoc ghi nho theo cuoc hoi thoai: con kha dung thi giu, khong
  nhay lane lien tuc giua cac lan render.
- Chi hoi user khi that su mo ho: tuc la khong co lane AI ngoai nao kha dung
  (roi ve cuc bo va noi ro trong cau tra loi).
- Ke hoach du phong van co: bien moi truong AIOS_AI_BACKEND ghim mot lane.

Tuong thich Python 3.11.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

BACKEND_GEMINI_WEB = "gemini_web"
BACKEND_CAGENT = "cagent_api"
BACKEND_ROUTER = "nakazasen_router"
BACKEND_LOCAL = "local"

BACKENDS = (
    BACKEND_GEMINI_WEB,
    BACKEND_CAGENT,
    BACKEND_ROUTER,
    BACKEND_LOCAL,
)

_LABELS_VI = {
    BACKEND_GEMINI_WEB: "Gemini qua cầu nối",
    BACKEND_CAGENT: "C-Agent",
    BACKEND_ROUTER: "Nakazasen Router",
    BACKEND_LOCAL: "Chạy cục bộ (không gọi AI ngoài)",
}

MANUAL_OVERRIDE_ENV = "AIOS_AI_BACKEND"


def backend_label_vi(backend: str) -> str:
    return _LABELS_VI.get(backend, str(backend))


@dataclass(frozen=True)
class LaneDecision:
    backend: str
    reason_vi: str
    automatic: bool = True


def _available(
    backend: str,
    *,
    bridge_available: bool,
    cagent_endpoint: str,
    router_keys_present: bool,
    router_cooling_down: bool,
) -> bool:
    if backend == BACKEND_GEMINI_WEB:
        return bool(bridge_available)
    if backend == BACKEND_CAGENT:
        return bool(cagent_endpoint.strip())
    if backend == BACKEND_ROUTER:
        return bool(router_keys_present) and not bool(router_cooling_down)
    return True  # local luon kha dung


def select_ai_backend(
    *,
    bridge_available: bool,
    cagent_endpoint: str = "",
    router_keys_present: bool = False,
    router_cooling_down: bool = False,
    manual_override: str = "",
) -> LaneDecision:
    """Chon lane theo do kha dung hien tai. Khong cham UI, de test duoc."""
    override = (manual_override or "").strip()
    if override in BACKENDS:
        return LaneDecision(
            backend=override,
            reason_vi="Giữ theo cấu hình tay " + MANUAL_OVERRIDE_ENV + ".",
            automatic=False,
        )
    if bridge_available:
        return LaneDecision(
            backend=BACKEND_GEMINI_WEB,
            reason_vi="Cầu nối Gemini đang sẵn sàng.",
        )
    if cagent_endpoint.strip():
        return LaneDecision(
            backend=BACKEND_CAGENT,
            reason_vi="Đã cấu hình endpoint C-Agent.",
        )
    if router_keys_present and not router_cooling_down:
        return LaneDecision(
            backend=BACKEND_ROUTER,
            reason_vi="Đã cấu hình khóa cloud cho Router.",
        )
    return LaneDecision(
        backend=BACKEND_LOCAL,
        reason_vi=(
            "Không có lane AI ngoài nào khả dụng; trả lời bằng tri thức cục bộ. "
            "Hãy kiểm tra cầu nối hoặc cấu hình C-Agent."
        ),
    )


def auto_backend_for_conversation(
    memory_key: str,
    session_state: Any,
    *,
    bridge_available: bool,
    cagent_endpoint: str = "",
    router_keys_present: bool = False,
    router_cooling_down: bool = False,
    manual_override: str = "",
) -> LaneDecision:
    """Chon lane va ghi nho theo cuoc hoi thoai.

    `session_state` la dict (Streamlit session_state dung duoc nhu dict).
    Lane da nho duoc giu lai neu van kha dung de khong nhay lane lien tuc.
    """
    decision = select_ai_backend(
        bridge_available=bridge_available,
        cagent_endpoint=cagent_endpoint,
        router_keys_present=router_keys_present,
        router_cooling_down=router_cooling_down,
        manual_override=manual_override,
    )
    get = getattr(session_state, "get", None)
    remembered = get(memory_key) if callable(get) else None
    if isinstance(remembered, str) and remembered in BACKENDS:
        signals = dict(
            bridge_available=bridge_available,
            cagent_endpoint=cagent_endpoint,
            router_keys_present=router_keys_present,
            router_cooling_down=router_cooling_down,
        )
        if _available(remembered, **signals):
            if remembered != decision.backend:
                return LaneDecision(
                    backend=remembered,
                    reason_vi="Giữ lane đã chọn trước đó (vẫn khả dụng).",
                    automatic=decision.automatic,
                )
            return decision
    try:
        session_state[memory_key] = decision.backend
    except (TypeError, AttributeError):
        pass
    return decision


def describe_decision_for_answer(decision: LaneDecision) -> str:
    """Dong trang thai nho hien trong cau tra loi (khong phoi toolbar)."""
    mode = "tự động chọn" if decision.automatic else "ghim tay"
    return "Đang dùng: " + backend_label_vi(decision.backend) + " (" + mode + "). " + decision.reason_vi
