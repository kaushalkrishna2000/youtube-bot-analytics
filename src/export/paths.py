"""Resolve JSON export paths for fetch modes."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

DEFAULT_OUTPUT_BASE = "fetch_export"
_TIMESTAMP_FORMAT = "%Y-%m-%d_%H%M%S"


def run_timestamp() -> str:
    return datetime.now().strftime(_TIMESTAMP_FORMAT)


def resolve_output_base(output_dir: Path | None, *, project_root: Path) -> Path:
    if output_dir is not None:
        return output_dir.resolve()
    return (project_root / DEFAULT_OUTPUT_BASE).resolve()


def sanitize_fs_name(value: str | None, *, fallback: str) -> str:
    text = (value or "").strip()
    if not text:
        return fallback
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("._-")
    return safe or fallback
