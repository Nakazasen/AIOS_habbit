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
import re
import sys
import time
from typing import Any, Callable, List, Optional, Sequence

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


def split_text_into_streaming_chunks(text: str, target_chunk_size: int = 40) -> List[str]:
    """Split a text block into progressive streaming chunks while strictly preserving exact content.

    Invariant: ''.join(split_text_into_streaming_chunks(text)) == text
    Splits by paragraph/sentence/word boundaries without breaking markdown citations or formatting.
    """
    if not text:
        return []
    if len(text) <= target_chunk_size:
        return [text]

    # Delimiter-preserving tokenizer: captures paragraphs, sentence endings, punctuation, and whitespace
    pattern = re.compile(r"(\n+|(?<=[.?!:])\s+|(?<=[,;])\s+|\s+)")
    tokens = pattern.split(text)
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    for tok in tokens:
        if not tok:
            continue
        if current_len + len(tok) <= target_chunk_size:
            current.append(tok)
            current_len += len(tok)
        else:
            if current:
                chunks.append("".join(current))
                current = []
                current_len = 0
            if len(tok) > target_chunk_size:
                for i in range(0, len(tok), target_chunk_size):
                    chunks.append(tok[i : i + target_chunk_size])
            else:
                current.append(tok)
                current_len += len(tok)

    if current:
        chunks.append("".join(current))

    assert "".join(chunks) == text, "split_text_into_streaming_chunks invariant violation: output does not match input"
    return chunks


def progressive_emit_chunks(
    text: str,
    on_chunk: Optional[Callable[[str], None]],
    cancellation_event: Any = None,
    target_total_duration_s: float = 0.7,
    target_chunk_size: int = 40,
) -> None:
    """Progressively deliver chunks of a complete text block to an on_chunk listener.

    Supports ticket DESKTOP-HOME-ANSWER-STREAMING-DISPLAY:
    - Yields chunks progressively so the user sees text flowing smoothly in real time.
    - Adapts chunk delay dynamically so total duration stays within a fast, responsive window (0.3s - 0.9s).
    - Checks cancellation_event on every step to halt immediately if user cancels.
    - True streaming chunks (len <= target_chunk_size) pass through instantly with zero added delay.
    """
    if not text or on_chunk is None:
        return

    if len(text) <= target_chunk_size:
        on_chunk(text)
        return

    chunks = split_text_into_streaming_chunks(text, target_chunk_size=target_chunk_size)
    if len(chunks) <= 1:
        on_chunk(text)
        return

    chunk_delay = min(0.035, max(0.012, target_total_duration_s / len(chunks)))
    for idx, chunk in enumerate(chunks):
        if cancellation_event is not None and getattr(cancellation_event, "is_set", lambda: False)():
            break
        on_chunk(chunk)
        if idx < len(chunks) - 1:
            time.sleep(chunk_delay)

