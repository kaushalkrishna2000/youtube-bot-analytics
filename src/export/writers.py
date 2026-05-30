"""
Write ChannelReport instances to JSON and flat comment CSV files.

CSV rows duplicate target channel/video columns per comment for spreadsheet filters.
Batch mode always writes all_comments.csv (header only if no comments anywhere).
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Iterable

from models.records import ChannelReport, CommentRecord

logger = logging.getLogger(__name__)

CHANNEL_REPORT_FILENAME = "channel_report.json"
REPORTS_FILENAME = "reports.json"
COMMENTS_FILENAME = "comments.csv"
ALL_COMMENTS_FILENAME = "all_comments.csv"

COMMENT_CSV_FIELDS = [
    "target_channel_id",
    "target_channel_title",
    "video_id",
    "video_title",
    "comment_id",
    "comment_text",
    "comment_published_at",
    "author_display_name",
    "author_channel_id",
    "like_count",
    "author_channel_title",
    "author_channel_created_at",
    "author_channel_custom_url",
    "enrichment_status",
]


def write_channel_report_json(report: ChannelReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_reports_json(reports: Iterable[ChannelReport], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [r.to_dict() for r in reports]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _comment_row(report: ChannelReport, comment: CommentRecord) -> dict[str, str | int | None]:
    """Flatten one comment with target channel/video context for CSV export."""
    video = report.latest_video
    return {
        "target_channel_id": report.channel_id,
        "target_channel_title": report.title,
        "video_id": video.video_id if video else None,
        "video_title": video.title if video else None,
        "comment_id": comment.comment_id,
        "comment_text": comment.comment_text,
        "comment_published_at": comment.comment_published_at,
        "author_display_name": comment.author_display_name,
        "author_channel_id": comment.author_channel_id,
        "like_count": comment.like_count,
        "author_channel_title": comment.author_channel_title,
        "author_channel_created_at": comment.author_channel_created_at,
        "author_channel_custom_url": comment.author_channel_custom_url,
        "enrichment_status": comment.enrichment_status,
    }


def write_comments_csv(report: ChannelReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COMMENT_CSV_FIELDS)
        writer.writeheader()
        for comment in report.comments:
            writer.writerow(_comment_row(report, comment))


def write_all_comments_csv(reports: Iterable[ChannelReport], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COMMENT_CSV_FIELDS)
        writer.writeheader()
        for report in reports:
            for comment in report.comments:
                writer.writerow(_comment_row(report, comment))


def export_single(report: ChannelReport, output_dir: Path, *, write_json: bool = True, write_csv: bool = True) -> None:
    if write_json:
        path = output_dir / CHANNEL_REPORT_FILENAME
        write_channel_report_json(report, path)
        logger.info("Wrote %s", path)
    # Skip empty comments.csv in single mode when there are no rows.
    if write_csv and report.comments:
        path = output_dir / COMMENTS_FILENAME
        write_comments_csv(report, path)
        logger.info("Wrote %s", path)


def export_batch(reports: list[ChannelReport], output_dir: Path, *, write_json: bool = True, write_csv: bool = True) -> None:
    if write_json:
        path = output_dir / REPORTS_FILENAME
        write_reports_json(reports, path)
        logger.info("Wrote %s", path)
    if write_csv:
        path = output_dir / ALL_COMMENTS_FILENAME
        write_all_comments_csv(reports, path)
        logger.info("Wrote %s", path)
