"""Unicode NFKC and mechanical normalization for document filenames and aliases.

This module replaces hardcoded document alias variations (QD-04) with an algorithmic
canonical key generator that normalizes:
- Unicode canonical equivalence (NFKC: halfwidth/fullwidth, composite characters)
- Mechanical middle dot variations ('・', '･', '·', '•' -> '_')
- Whitespace variations (' ' -> '_')
- File extension omissions/differences (.xlsx, .txt, .pptx, etc.)
- Case sensitivity (lowercased)
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Optional

_KNOWN_EXT_PATTERN = re.compile(
    r"\.(?:xlsx?|xlsm|csv|docx?|pptx?|txt|msg|pdf)$",
    re.IGNORECASE,
)
_MIDDLE_DOT_PATTERN = re.compile(r"[\u30FB\uFF65\u00B7\u2022\u2219]")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_MULTI_UNDERSCORE_PATTERN = re.compile(r"_+")


def normalize_document_key(name: str) -> str:
    """Compute the canonical key for a document filename, title, or alias.
    
    Applies Unicode NFKC normalization, removes standard document file extensions,
    converts middle dots and whitespace to single underscores, strips surrounding
    punctuation, and lowercases.
    """
    if not name:
        return ""
    # 1. Unicode NFKC normalization
    text = unicodedata.normalize("NFKC", str(name)).strip()
    
    # 2. Strip standard file extensions
    text = _KNOWN_EXT_PATTERN.sub("", text)
    
    # 3. Standardize middle dots to underscores
    text = _MIDDLE_DOT_PATTERN.sub("_", text)
    
    # 4. Standardize whitespace to underscores
    text = _WHITESPACE_PATTERN.sub("_", text)
    
    # 5. Collapse consecutive underscores and trim
    text = _MULTI_UNDERSCORE_PATTERN.sub("_", text)
    text = text.strip(" _\t\r\n")
    
    # 6. Case folding
    return text.lower()


def are_document_names_equivalent(name1: str, name2: str) -> bool:
    """Return True if two document names or aliases are mechanically equivalent."""
    k1 = normalize_document_key(name1)
    k2 = normalize_document_key(name2)
    return bool(k1 and k2 and k1 == k2)


def match_in_catalog(
    candidate: str,
    catalog_names: Iterable[str],
) -> Optional[str]:
    """Find a document in catalog_names that matches candidate by canonical key."""
    target_key = normalize_document_key(candidate)
    if not target_key:
        return None
    for name in catalog_names:
        if normalize_document_key(name) == target_key:
            return name
    return None
