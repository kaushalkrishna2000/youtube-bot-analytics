"""Write JSON exports for channel/video fetch modes."""

from __future__ import annotations

import json
from pathlib import Path

from export.paths import sanitize_fs_name
from models.records import ChannelReport, VideoFetchReport


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def export_channel_single(report: ChannelReport, output_base: Path, timestamp: str) -> Path:
    channel_name = sanitize_fs_name(report.title or report.channel_id or report.input_raw, fallback="unknown_channel")
    path = output_base / channel_name / f"{timestamp}.json"
    _write_json(path, report.to_dict())
    return path


def export_channel_batch(reports: list[ChannelReport], output_base: Path, timestamp: str) -> list[Path]:
    base = output_base / "batch_mode" / timestamp
    paths: list[Path] = []
    for report in reports:
        channel_name = sanitize_fs_name(report.title or report.channel_id or report.input_raw, fallback="unknown_channel")
        path = base / f"{channel_name}.json"
        _write_json(path, report.to_dict())
        paths.append(path)
    return paths


def export_video_mode(report: VideoFetchReport, output_base: Path, timestamp: str) -> Path:
    video_name = sanitize_fs_name(report.video.video_id if report.video else report.input_video_id, fallback="unknown_video")
    path = output_base / "video_mode" / video_name / f"{timestamp}.json"
    _write_json(path, report.to_dict())
    return path
