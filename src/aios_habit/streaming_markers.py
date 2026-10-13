"""Shared telemetry helpers for streaming chat markers with absolute timestamps.

Supports ticket DESKTOP-SPEED-PRESYNTH-MARKERS-HOME:
- Emits absolute timestamps matching the existing server log format:
  YYYY-MM-DD HH:MM:SS.mmm
- Shared formatter format_marker_timestamp() for adapter, app, and bridge.
- Provides emit_pre_synth_step_marker() for fine-grained segment attribution.
"""
from __future__ import annotations

from datetime import datetime
import logging
import sys
from typing import Optional

LOGGER = logging.getLogger("aios_habit.streaming_markers")


def _safe_print_streaming_marker(msg: str) -> None:
    """Print marker message to stdout safely across encoding environments."""
    try:
        if hasattr(sys.stdout, "buffer") and sys.stdout.buffer is not None:
            sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
            sys.stdout.buffer.flush()
        else:
            print(msg.encode("ascii", errors="backslashreplace").decode("ascii"), flush=True)
    except Exception:
        pass


def format_marker_timestamp(dt: Optional[datetime] = None) -> str:
    """Format an absolute timestamp matching the server logging format (YYYY-MM-DD HH:MM:SS.mmm)."""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def parse_marker_timestamp(ts_str: str) -> datetime:
    """Parse a marker timestamp string back into a datetime object."""
    cleaned = ts_str.strip()
    if "T" in cleaned:
        cleaned = cleaned.replace("T", " ")
    if "." in cleaned:
        return datetime.strptime(cleaned, "%Y-%m-%d %H:%M:%S.%f")
    return datetime.strptime(cleaned, "%Y-%m-%d %H:%M:%S")


def diff_marker_timestamps_s(ts_start: str, ts_end: str) -> float:
    """Calculate the direct elapsed seconds between two marker timestamps."""
    t0 = parse_marker_timestamp(ts_start)
    t1 = parse_marker_timestamp(ts_end)
    return max(0.0, (t1 - t0).total_seconds())


def emit_pre_synth_step_marker(
    conversation_id: str,
    step: str,
    timestamp: Optional[str] = None,
) -> str:
    """Emit a [PRE_SYNTH_STEP] marker with absolute timestamp.

    Format: [PRE_SYNTH_STEP] conv=<id> step=<name> timestamp=<YYYY-MM-DD HH:MM:SS.mmm>
    """
    ts = timestamp or format_marker_timestamp()
    marker_msg = f"[PRE_SYNTH_STEP] conv={conversation_id} step={step} timestamp={ts}"
    _safe_print_streaming_marker(marker_msg)
    try:
        LOGGER.info(
            "[PRE_SYNTH_STEP] conv=%s step=%s timestamp=%s",
            conversation_id,
            step,
            ts,
        )
    except Exception:
        pass
    return marker_msg
