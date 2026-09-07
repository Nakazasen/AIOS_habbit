"""Production prediction module for LSU Iris and shopfloor quality tracing.

Strictly adheres to data privacy guidelines: only aggregates, manifests, and
standardized metrics are shared with upper layers; raw factory proprietary files
are read locally only.
"""

from __future__ import annotations

__all__ = [
    "models",
    "lsu_iris",
]