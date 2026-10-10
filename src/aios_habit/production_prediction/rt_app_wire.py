"""Realtime LSU alert pipeline wiring for Workspace Chat (DESKTOP-LSU-ALERT-WIRE-HOME).

Connects:
  HTTP StreamListener (18991) -> StreamBuffer (SQLite)
  -> RtConsumer (poll events) -> SMA(20) trend gate
  -> day_the_realtime_qua_cong_vao_chat -> Workspace Chat assistant messages.

Guarantees:
- Consumer runs in background daemon thread; does not block UI loop.
- SMA(20) gate behavior preserved: single isolated anomalies remain 'Cần biến',
  confirmed trends (>=3 consecutive or >=3/5 recent) surface as prominent alert cards.
- Python 3.11 compatible.
"""

from __future__ import annotations

import os
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aios_habit.production_prediction.jig_chat_wire import day_the_realtime_qua_cong_vao_chat
from aios_habit.production_prediction.rt_consumer import (
    RtConsumer,
    chuyen_lo_thanh_the_da_qua_cong,
    dinh_dang_text_chat_cho_the_realtime,
    tom_tat_can_bien_cho_chat,
)
from aios_habit.production_prediction.stream_api import (
    EVENTS_PATH,
    StreamBuffer,
    StreamListener,
)
from aios_habit.workspace_chat_models import ChatMessage
from aios_habit.workspace_chat_store import load_all_conversations, save_message

DEFAULT_STREAM_PORT: int = int(os.environ.get("AIOS_JIG_STREAM_PORT", "18991"))

_LISTENER: Optional[StreamListener] = None
_WORKER_THREAD: Optional[threading.Thread] = None
_STOP_EVENT = threading.Event()
_ACTIVE_CONV_ID: Optional[str] = None
_LOCK = threading.Lock()
_LAST_DISPATCH_TIME: float = 0.0
_DISPATCHED_ALERT_KEYS: set[Tuple[str, str]] = set()


def reset_rt_dispatched_alerts(conv_id: Optional[str] = None) -> None:
    """Reset tracked dispatched alert keys (useful in tests)."""
    global _DISPATCHED_ALERT_KEYS
    with _LOCK:
        if conv_id:
            _DISPATCHED_ALERT_KEYS = {k for k in _DISPATCHED_ALERT_KEYS if k[0] != conv_id}
        else:
            _DISPATCHED_ALERT_KEYS.clear()


def is_alert_already_dispatched(conv_id: str, alert_id: str) -> bool:
    """Check if an alert_id has already been dispatched to a conversation."""
    with _LOCK:
        if (conv_id, alert_id) in _DISPATCHED_ALERT_KEYS:
            return True
    try:
        from aios_habit.workspace_chat_store import load_messages
        msgs = load_messages(conv_id)
        for m in msgs:
            content = str(m.content or "")
            if alert_id and alert_id in content:
                with _LOCK:
                    _DISPATCHED_ALERT_KEYS.add((conv_id, alert_id))
                return True
    except Exception:
        pass
    return False


def record_dispatched_alert(conv_id: str, alert_id: str) -> None:
    """Record that an alert_id was dispatched to conv_id."""
    with _LOCK:
        _DISPATCHED_ALERT_KEYS.add((conv_id, alert_id))


ACTIVE_CONV_FILE = Path("local_cases") / "rt_active_conversation.txt"


def set_active_rt_conversation(conv_id: str) -> None:
    """Register current active conversation ID viewed by the user."""
    global _ACTIVE_CONV_ID
    cleaned = str(conv_id or "").strip()
    if not cleaned:
        return
    with _LOCK:
        _ACTIVE_CONV_ID = cleaned
    try:
        ACTIVE_CONV_FILE.parent.mkdir(parents=True, exist_ok=True)
        ACTIVE_CONV_FILE.write_text(cleaned, encoding="utf-8")
    except Exception:
        pass


def get_active_rt_conversation() -> Optional[str]:
    """Retrieve current active conversation ID, prioritizing disk synchronization."""
    global _ACTIVE_CONV_ID
    try:
        if ACTIVE_CONV_FILE.exists():
            val = ACTIVE_CONV_FILE.read_text(encoding="utf-8").strip()
            if val:
                with _LOCK:
                    _ACTIVE_CONV_ID = val
                return val
    except Exception:
        pass
    with _LOCK:
        if _ACTIVE_CONV_ID:
            return _ACTIVE_CONV_ID
    try:
        convs = load_all_conversations()
        if convs:
            return convs[0].id
    except Exception:
        pass
    return None


def get_last_dispatch_time() -> float:
    """Return timestamp of the most recent alert dispatch."""
    global _LAST_DISPATCH_TIME
    return _LAST_DISPATCH_TIME


def is_listener_healthy(port: int = DEFAULT_STREAM_PORT) -> bool:
    """Check if StreamListener events endpoint is accessible."""
    try:
        url = f"http://127.0.0.1:{port}{EVENTS_PATH}?since=0&limit=1"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return int(resp.status) == 200
    except Exception:
        return False


def ensure_listener_running(
    port: int = DEFAULT_STREAM_PORT,
    db_path: Optional[Path] = None,
) -> Optional[StreamListener]:
    """Start StreamListener on localhost port if not already listening."""
    global _LISTENER
    with _LOCK:
        if is_listener_healthy(port):
            return _LISTENER
        if db_path is None:
            db_path = Path("local_cases") / "jig_stream.sqlite"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        buffer = StreamBuffer(db_path)
        try:
            listener = StreamListener(host="127.0.0.1", port=port, buffer=buffer)
            listener.start()
            _LISTENER = listener
            return listener
        except OSError:
            return _LISTENER


def poll_and_dispatch_rt_alerts(
    conversation_id: Optional[str] = None,
    port: int = DEFAULT_STREAM_PORT,
    cursor_path: Optional[Path] = None,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Single polling step: fetch events, apply SMA(20) gate, push to chat.

    Returns summary dictionary with event counts and dispatch status.
    """
    global _LAST_DISPATCH_TIME
    if cursor_path is None:
        cursor_path = Path("local_cases") / "rt_consumer_cursor.txt"
    if db_path is None:
        db_path = Path("local_cases") / "jig_stream.sqlite"

    consumer = RtConsumer(
        base_url=f"http://127.0.0.1:{port}",
        duong_dan_cursor=cursor_path,
        timeout_giay=2.0,
        so_lan_thu_toi_da=1,
    )

    try:
        su_kien, cursor_moi = consumer.lay_su_kien_moi(gioi_han=100)
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "su_kien": 0,
            "cac_the": 0,
            "the_moi": 0,
            "cac_can_bien": 0,
            "dispatched": False,
        }

    if not su_kien:
        return {
            "ok": True,
            "su_kien": 0,
            "cac_the": 0,
            "the_moi": 0,
            "cac_can_bien": 0,
            "dispatched": False,
        }

    buffer = StreamBuffer(db_path)
    gom_keys: Dict[Tuple[str, str], bool] = {}
    for ev in su_kien:
        jig = str(ev.get("jig_id") or "—")
        met = str(ev.get("metric") or "—")
        gom_keys[(jig, met)] = True

    lich_su_theo_chi_so: Dict[Tuple[str, str], List[float]] = {}
    for (jig, met) in gom_keys:
        try:
            recent = buffer.recent_values(jig, met, 50)
            new_vals_count = sum(
                1
                for e in su_kien
                if str(e.get("jig_id")) == jig
                and str(e.get("metric")) == met
                and e.get("noi_dung", {}).get("gia_tri") is not None
            )
            if len(recent) > new_vals_count:
                lich_su_theo_chi_so[(jig, met)] = recent[:-new_vals_count]
            else:
                lich_su_theo_chi_so[(jig, met)] = recent
        except Exception:
            lich_su_theo_chi_so[(jig, met)] = []

    cac_the, cac_can_bien = chuyen_lo_thanh_the_da_qua_cong(
        su_kien, lich_su_theo_chi_so=lich_su_theo_chi_so
    )

    consumer.cursor = cursor_moi
    consumer._luu_cursor_xuong_dia()

    target_conv = conversation_id or get_active_rt_conversation()

    # Khử trùng ở khâu dispatch: một sự kiện xu hướng đã xác nhận chỉ sinh đúng một thẻ trong hội thoại
    the_moi = []
    if target_conv:
        for the in cac_the:
            alt_id = str(the.get("alert_id") or f"ALT-{the.get('ma_jig')}-{the.get('thong_so')}").replace(" ", "_")
            if not is_alert_already_dispatched(target_conv, alt_id):
                the_moi.append(the)
    else:
        the_moi = list(cac_the)

    chat_text = ""
    if the_moi or cac_can_bien:
        dong = []
        for the in the_moi:
            dong.append(dinh_dang_text_chat_cho_the_realtime(the))
        for muc in cac_can_bien:
            dong.append(tom_tat_can_bien_cho_chat(muc))
        if dong:
            chat_text = "\n".join(dong)

    dispatched_msg_id = ""
    if (
        (the_moi or (cac_can_bien and not cac_the))
        and target_conv
        and chat_text
        and chat_text != "Chưa có sự kiện realtime mới."
    ):
        dispatched_msg_id = f"MSG-A-{uuid.uuid4().hex[:8].upper()}"
        msg = ChatMessage(
            id=dispatched_msg_id,
            conversation_id=target_conv,
            role="assistant",
            content=chat_text,
        )
        save_message(msg)
        for the in the_moi:
            alt_id = str(the.get("alert_id") or f"ALT-{the.get('ma_jig')}-{the.get('thong_so')}").replace(" ", "_")
            record_dispatched_alert(target_conv, alt_id)
        _LAST_DISPATCH_TIME = time.time()

    return {
        "ok": True,
        "su_kien": len(su_kien),
        "cac_the": len(cac_the),
        "the_moi": len(the_moi),
        "cac_can_bien": len(cac_can_bien),
        "dispatched": bool(dispatched_msg_id),
        "chat_text": chat_text,
        "message_id": dispatched_msg_id,
        "conversation_id": target_conv,
    }


def start_rt_worker_thread(port: int = DEFAULT_STREAM_PORT) -> threading.Thread:
    """Start background daemon thread polling events continuously."""
    global _WORKER_THREAD, _STOP_EVENT
    with _LOCK:
        if _WORKER_THREAD is not None and _WORKER_THREAD.is_alive():
            return _WORKER_THREAD
        _STOP_EVENT.clear()

        def _worker_loop() -> None:
            while not _STOP_EVENT.is_set():
                try:
                    poll_and_dispatch_rt_alerts(port=port)
                except Exception:
                    pass
                _STOP_EVENT.wait(1.0)

        thread = threading.Thread(
            target=_worker_loop,
            daemon=True,
            name="aios-rt-alert-consumer",
        )
        thread.start()
        _WORKER_THREAD = thread
        return thread


def ensure_rt_alert_pipeline(port: int = DEFAULT_STREAM_PORT) -> None:
    """Start both background StreamListener and consumer worker thread."""
    try:
        ensure_listener_running(port=port)
    except Exception:
        pass
    try:
        start_rt_worker_thread(port=port)
    except Exception:
        pass


def stop_rt_alert_pipeline() -> None:
    """Stop background worker thread and HTTP listener gracefully."""
    global _LISTENER, _WORKER_THREAD
    with _LOCK:
        _STOP_EVENT.set()
        if _WORKER_THREAD is not None and _WORKER_THREAD.is_alive():
            _WORKER_THREAD.join(timeout=2.0)
            _WORKER_THREAD = None
        if _LISTENER is not None:
            try:
                _LISTENER.stop()
            except Exception:
                pass
            _LISTENER = None
