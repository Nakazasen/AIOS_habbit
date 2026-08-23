"""Gemini Web proxy engine for AIOS WorkLens.

Zero-cost, anonymous web proxy leveraging Google Gemini's public web StreamGenerate endpoint.
Exposes standard completion methods for local sidecar daemon.
"""
from __future__ import annotations

import json
import logging
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Mapping

LOGGER = logging.getLogger(__name__)

# Default Fallback BL
DEFAULT_GEMINI_BL = "boq_assistant-bard-web-server_20260821.03_p0"
CURRENT_GEMINI_BL = DEFAULT_GEMINI_BL

# Supported Models & Modes
# Mode mapping: 1=FAST, 2=THINKING, 3=PRO, 4=AUTO, 5=FAST_DYNAMIC_THINKING, 6=FLASH_LITE
MODELS_MAP: dict[str, dict[str, Any]] = {
    "gemini-3.7-flash": {"mode": 1, "think": 4, "desc": "Gemini 3.7 Flash"},
    "gemini-3.6-flash": {"mode": 1, "think": 4, "desc": "Gemini 3.6 Flash"},
    "gemini-3.5-flash": {"mode": 1, "think": 4, "desc": "Gemini 3.5 Flash"},
    "gemini-3.5-flash-thinking": {"mode": 2, "think": 0, "desc": "Gemini 3.5 Flash Thinking"},
    "gemini-flash-lite": {"mode": 6, "think": 4, "desc": "Gemini Flash Lite"},
}


def fetch_latest_bl() -> str | None:
    """Fetch the latest gemini_bl from gemini.google.com page."""
    try:
        req = urllib.request.Request(
            "https://gemini.google.com/app",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        m = re.search(r"(boq_assistant-bard-web-server_\d+\.\d+_p\d+)", html)
        if m:
            return m.group(1)
    except Exception as e:
        LOGGER.warning("Gemini BL auto-update fetch failed: %s", e)
    return None


def ensure_latest_bl() -> str:
    """Returns current BL or fetches latest if possible."""
    global CURRENT_GEMINI_BL
    new_bl = fetch_latest_bl()
    if new_bl:
        CURRENT_GEMINI_BL = new_bl
    return CURRENT_GEMINI_BL


def clean_gemini_text(text: str, strip: bool = True) -> str:
    """Remove internal code execution artifacts."""
    text = re.sub(
        r"```(?:python|javascript|text)\?code_(?:reference|stdout)&code_event_index=\d+\n.*?```\n?",
        "",
        text,
        flags=re.DOTALL,
    )
    return text.strip() if strip else text


def extract_response_text(raw: str) -> str:
    """Parse StreamGenerate response to extract final text."""
    bard_err = re.search(r"BardErrorInfo\s*\[(\d+)\]", raw)
    if bard_err:
        raise RuntimeError(f"Gemini upstream rejected request: BardErrorInfo [{bard_err.group(1)}]")
    texts: list[str] = []
    for line in raw.split("\n"):
        if '"wrb.fr"' not in line:
            continue
        try:
            arr = json.loads(line)
            if not isinstance(arr, list) or len(arr) == 0 or len(arr[0]) < 3:
                continue
            inner_str = arr[0][2]
            if not inner_str:
                continue
            inner = json.loads(inner_str)
            if isinstance(inner, list) and len(inner) > 4 and inner[4]:
                for part in inner[4]:
                    if isinstance(part, list) and len(part) > 1 and part[1] and isinstance(part[1], list):
                        for t in part[1]:
                            if isinstance(t, str) and len(t) > 0:
                                texts.append(t)
        except (json.JSONDecodeError, IndexError, TypeError):
            pass
    if texts:
        return clean_gemini_text(texts[-1])
    return ""


def gemini_stream_generate(
    prompt: str,
    model_id: int = 1,
    think_mode: int = 4,
    timeout_seconds: float = 60.0,
    retry_attempts: int = 2,
) -> str:
    """Send prompt to Gemini StreamGenerate endpoint with automatic BL refresh."""
    global CURRENT_GEMINI_BL

    inner: list[Any] = [None] * 80
    inner[0] = [prompt, 0, None, None, None, None, 0]
    inner[1] = ["en"]
    inner[2] = ["", "", "", None, None, None, None, None, None, ""]
    inner[6] = [0]
    inner[7] = 1
    inner[10] = 1
    inner[11] = 0
    inner[17] = [[think_mode]]
    inner[18] = 0
    inner[27] = 1
    inner[30] = [4]
    inner[41] = [2]
    inner[53] = 0
    inner[59] = str(uuid.uuid4())
    inner[61] = []
    inner[68] = 1
    inner[79] = model_id

    outer = [None, json.dumps(inner)]
    params = {"f.req": json.dumps(outer)}
    body = urllib.parse.urlencode(params).encode("utf-8")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://gemini.google.com",
        "Referer": "https://gemini.google.com/app",
        "X-Same-Domain": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    ctx = ssl.create_default_context()
    last_err: Exception | None = None

    for attempt in range(retry_attempts):
        reqid = int(time.time()) % 1000000
        url = (
            "https://gemini.google.com/_/BardChatUi/data/"
            "assistant.lamda.BardFrontendService/StreamGenerate"
            f"?bl={CURRENT_GEMINI_BL}&hl=en&_reqid={reqid}&rt=c"
        )
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, context=ctx, timeout=timeout_seconds) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (404, 405):
                LOGGER.info("Received HTTP %d, refreshing Gemini BL...", e.code)
                new_bl = fetch_latest_bl()
                if new_bl and new_bl != CURRENT_GEMINI_BL:
                    CURRENT_GEMINI_BL = new_bl
                    continue
        except Exception as e:
            last_err = e
            if attempt < retry_attempts - 1:
                time.sleep(1.0)

    if last_err:
        raise last_err
    raise RuntimeError("Gemini Web stream generation failed after retries.")


def generate_gemini_web_reply(
    prompt: str,
    model_name: str = "gemini-3.6-flash",
    timeout_seconds: float = 60.0,
) -> dict[str, Any]:
    """Top-level generation helper returning structured response dict."""
    model_cfg = MODELS_MAP.get(model_name, MODELS_MAP["gemini-3.6-flash"])
    model_id = model_cfg["mode"]
    think_mode = model_cfg["think"]

    start_t = time.perf_counter()
    try:
        raw = gemini_stream_generate(
            prompt=prompt,
            model_id=model_id,
            think_mode=think_mode,
            timeout_seconds=timeout_seconds,
        )
        answer = extract_response_text(raw)
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        if not answer:
            return {
                "ok": False,
                "answer_text": "",
                "model": "",
                "latency_ms": elapsed_ms,
                "error": "Gemini Web trả về kết quả rỗng.",
            }
        return {
            "ok": True,
            "answer_text": answer,
            "model": "",
            "latency_ms": elapsed_ms,
            "error": "",
        }
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        LOGGER.warning("Gemini Web generation failed: %s", e)
        return {
            "ok": False,
            "answer_text": "",
            "model": "",
            "latency_ms": elapsed_ms,
            "error": f"Gemini Web generation failed: {e}",
        }
