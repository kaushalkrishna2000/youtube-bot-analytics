"""Load channel inputs and run channel-mode reports in batch."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from api.client import YouTubeClient
from logic.report import build_channel_report
from models.records import ChannelReport

logger = logging.getLogger(__name__)
CHANNEL_COLUMN_NAMES = ("channel", "url", "handle", "channel_url", "channel_id")


def load_channel_inputs(path: Path) -> list[str]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        inputs = _load_from_csv(path)
    else:
        inputs = _load_from_txt(path)
    logger.info("Loaded %s channel input(s) from %s", len(inputs), path)
    return inputs


def _load_from_txt(path: Path) -> list[str]:
    inputs: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        inputs.append(stripped)
    return inputs


def _load_from_csv(path: Path) -> list[str]:
    inputs: list[str] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return inputs
        column = _detect_column(reader.fieldnames)
        if column is None:
            raise ValueError(f"No channel column found in {path}. Expected one of: {', '.join(CHANNEL_COLUMN_NAMES)}")

        for row in reader:
            value = (row.get(column) or "").strip()
            if value and not value.startswith("#"):
                inputs.append(value)
    return inputs


def _detect_column(fieldnames: list[str]) -> str | None:
    lower_map = {name.lower(): name for name in fieldnames}
    for candidate in CHANNEL_COLUMN_NAMES:
        if candidate in lower_map:
            return lower_map[candidate]
    return None


def run_batch(client: YouTubeClient, channel_inputs: list[str], *, include_comments: bool = True, max_videos: int = 10, max_comments: int = 1000, delay_ms: int = 0) -> tuple[list[ChannelReport], list[tuple[str, str]]]:
    reports: list[ChannelReport] = []
    failures: list[tuple[str, str]] = []
    total = len(channel_inputs)
    logger.info("Starting batch run for %s channel(s)", total)

    for index, channel_input in enumerate(channel_inputs, start=1):
        logger.info("Processing [%s/%s]: %s", index, total, channel_input)
        try:
            report = build_channel_report(
                client,
                channel_input,
                include_comments=include_comments,
                max_videos=max_videos,
                max_comments=max_comments,
                delay_ms=delay_ms,
            )
            if report.error:
                failures.append((channel_input, report.error))
            reports.append(report)
        except Exception as exc:
            logger.exception("Unexpected error for %s", channel_input)
            failures.append((channel_input, str(exc)))
            reports.append(ChannelReport(input_raw=channel_input, error=str(exc)))

    logger.info("Batch run complete: %s success, %s failure", total - len(failures), len(failures))
    return reports, failures
