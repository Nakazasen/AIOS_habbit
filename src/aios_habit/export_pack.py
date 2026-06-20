import re

from .models import RAW_PATTERNS, SECRET_PATTERNS, scan_text_for_patterns


def redacted(text: str) -> str:
    output = text
    for pattern in SECRET_PATTERNS:
        output = re.sub(pattern, "[REDACTED]", output)
    return output


def validate_export_text(text: str) -> list[str]:
    if scan_text_for_patterns(text, RAW_PATTERNS):
        return ["source conversation archive marker detected"]
    return []
