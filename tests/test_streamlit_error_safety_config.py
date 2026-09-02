"""Regression checks for safe Streamlit error displays."""
from __future__ import annotations

import tomllib
from pathlib import Path


def test_streamlit_hides_error_details_and_links_from_end_users() -> None:
    config = tomllib.loads(Path(".streamlit/config.toml").read_text(encoding="utf-8"))

    assert config["client"]["showErrorDetails"] == "none"
    assert config["client"]["showErrorLinks"] is False
