"""Resolve where run artifacts are written."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

DEFAULT_OUTPUT_BASE = "output"
_TIMESTAMP_FORMAT = "%Y-%m-%d_%H%M%S"


def run_timestamp() -> str:
    return datetime.now().strftime(_TIMESTAMP_FORMAT)


def resolve_output_dir(
    output_dir: Path | None,
    *,
    project_root: Path,
    timestamp: str | None = None,
) -> Path:
    """
    Choose the directory for JSON/CSV exports.

    - No --output-dir: ``{project_root}/output/{timestamp}/``
    - With --output-dir: use that path as-is (created if missing)
    """
    if output_dir is not None:
        return output_dir.resolve()

    stamp = timestamp or run_timestamp()
    return (project_root / DEFAULT_OUTPUT_BASE / stamp).resolve()
