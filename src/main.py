#!/usr/bin/env python3
"""CLI entry point for YouTube Bot Analytics fetch workflows."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from api.client import YouTubeClient
from cli.parser import parse_args
from core.config import get_request_delay_ms
from core.logging import configure_logging
from export.paths import resolve_output_base, run_timestamp
from export.writers import export_channel_batch, export_channel_single, export_video_mode
from logic.batch import load_channel_inputs, run_batch
from logic.report import build_channel_report, build_video_report

logger = logging.getLogger(__name__)


def _resolve_log_level(args) -> int:
    if args.debug:
        return logging.DEBUG
    if args.verbose or not args.quiet:
        return logging.INFO
    return logging.WARNING


def main() -> int:
    args = parse_args()
    # Logging precedence: --debug > default INFO > --quiet.
    quiet_mode = args.quiet and not args.debug
    configure_logging(level=_resolve_log_level(args), quiet=quiet_mode)

    delay_ms = args.delay_ms if args.delay_ms is not None else get_request_delay_ms()
    include_comments = not args.no_comments
    project_root = _SRC_DIR.parent
    output_base = resolve_output_base(args.output_dir, project_root=project_root)
    timestamp = run_timestamp()
    logger.info(
        "Config: mode=%s include_comments=%s delay_ms=%s output_base=%s",
        f"{args.command}:{getattr(args, 'fetch_mode', '-')}",
        include_comments,
        delay_ms,
        output_base,
    )

    try:
        client = YouTubeClient()
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    if args.command == "fetch" and args.fetch_mode == "channel" and args.channel_mode == "single":
        logger.info(
            "Starting channel single fetch: input=%s max_videos=%s max_comments=%s",
            args.channel,
            args.max_videos,
            args.max_comments,
        )
        report = build_channel_report(
            client,
            args.channel,
            include_comments=include_comments,
            max_videos=max(args.max_videos, 1),
            max_comments=max(args.max_comments, 1),
            delay_ms=delay_ms,
        )
        path = export_channel_single(report, output_base, timestamp)
        logger.info("Exported channel single report to %s", path)
        if not args.quiet:
            print(f"Wrote output to {path}")
        return 1 if report.error else 0

    if args.command == "fetch" and args.fetch_mode == "channel" and args.channel_mode == "batch":
        logger.info(
            "Starting channel batch fetch: batch_file=%s max_videos=%s max_comments=%s",
            args.batch,
            args.max_videos,
            args.max_comments,
        )
        batch_path = Path(args.batch)
        if not batch_path.is_file():
            print(f"Batch file not found: {batch_path}", file=sys.stderr)
            return 1

        try:
            inputs = load_channel_inputs(batch_path)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1

        if not inputs:
            print("No channel inputs found in batch file.", file=sys.stderr)
            return 1

        reports, failures = run_batch(
            client,
            inputs,
            include_comments=include_comments,
            max_videos=max(args.max_videos, 1),
            max_comments=max(args.max_comments, 1),
            delay_ms=delay_ms,
        )
        paths = export_channel_batch(reports, output_base, timestamp)
        logger.info("Exported %s channel report file(s)", len(paths))
        if not args.quiet:
            print(f"Wrote {len(paths)} files under {(output_base / 'batch_mode' / timestamp)}")
        return 1 if failures else 0

    if args.command == "fetch" and args.fetch_mode == "video":
        logger.info("Starting video fetch: video_id=%s max_comments=%s", args.video_id, args.max_comments)
        report = build_video_report(
            client,
            args.video_id,
            max_comments=max(args.max_comments, 1),
            delay_ms=delay_ms,
        )
        path = export_video_mode(report, output_base, timestamp)
        logger.info("Exported video report to %s", path)
        if not args.quiet:
            print(f"Wrote output to {path}")
        return 1 if report.error else 0

    print("Unsupported command", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
