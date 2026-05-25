#!/usr/bin/env python3
"""
CLI entry point for YouTube Bot Analytics.

Wires argparse, logging, and export. All YouTube logic lives in pipeline/services;
this module only parses flags, builds YouTubeClient, and dispatches single vs batch.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Imports use `api`, `pipeline`, etc. — add src/ to path when run as a script.
_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from api import YouTubeClient
from api.config import MAX_COMMENTS_CAP, get_request_delay_ms
from batch import load_channel_inputs, run_batch
from export import export_batch, export_single, resolve_output_dir
from logging_config import configure_logging
from pipeline import build_full_report

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Look up a YouTube channel, its latest video, and commenter channel metadata.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--channel", help="Channel URL, @handle, or UC... channel ID")
    group.add_argument("--batch", metavar="FILE", help="Path to .txt or .csv file with channel inputs")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write exports here (default: <project>/output/<YYYY-MM-DD_HHMMSS>/)",
    )
    parser.add_argument("--format", choices=("json", "csv", "both"), default="both", help="Output format (default: both)")
    parser.add_argument("--max-comments", type=int, default=100, help=f"Max top-level comments per video (default: 100, cap: {MAX_COMMENTS_CAP})")
    parser.add_argument("--no-comments", action="store_true", help="Skip comment fetching and enrichment")
    parser.add_argument("--delay-ms", type=int, default=None, help="Delay between API calls in milliseconds")
    parser.add_argument("--quiet", action="store_true", help="Suppress summary output and flow logs (errors only)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show flow logs at INFO level (default when not --quiet)")
    parser.add_argument("--debug", action="store_true", help="Show detailed logs including API call timing")
    return parser.parse_args()


def _resolve_log_level(args: argparse.Namespace) -> int:
    """--debug > default INFO (unless --quiet) > WARNING when --quiet."""
    if args.debug:
        return logging.DEBUG
    if args.verbose or not args.quiet:
        return logging.INFO
    return logging.WARNING


def _format_flags(args: argparse.Namespace) -> tuple[bool, bool]:
    write_json = args.format in ("json", "both")
    write_csv = args.format in ("csv", "both")
    return write_json, write_csv


def _print_report_summary(report, *, quiet: bool) -> None:
    if quiet:
        return
    print(f"\nChannel: {report.title or 'N/A'} ({report.channel_id or 'N/A'})")
    if report.latest_video:
        lv = report.latest_video
        print(f"Latest video: {lv.title} ({lv.video_id})")
        print(f"  Published: {lv.published_at}")
    if report.error:
        print(f"Error: {report.error}")
    print(f"Comments: {report.comments_fetched} ({report.comments_status})")


def _log_run_config(
    args: argparse.Namespace,
    *,
    delay_ms: int,
    include_comments: bool,
    max_comments: int,
    output_dir: Path,
) -> None:
    logger.info("Config: output_dir=%s format=%s max_comments=%s include_comments=%s delay_ms=%s", output_dir, args.format, max_comments, include_comments, delay_ms)


def main() -> int:
    args = _parse_args()
    configure_logging(level=_resolve_log_level(args), quiet=args.quiet)

    delay_ms = args.delay_ms if args.delay_ms is not None else get_request_delay_ms()
    include_comments = not args.no_comments
    # API returns at most 100 top-level threads per request; cap enforces that limit.
    max_comments = min(max(args.max_comments, 1), MAX_COMMENTS_CAP)
    write_json, write_csv = _format_flags(args)
    project_root = _SRC_DIR.parent
    output_dir = resolve_output_dir(args.output_dir, project_root=project_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    _log_run_config(args, delay_ms=delay_ms, include_comments=include_comments, max_comments=max_comments, output_dir=output_dir)

    try:
        logger.info("Initializing YouTube API client")
        client = YouTubeClient()
    except ValueError as exc:
        logger.error("Configuration error: %s", exc)
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    if args.channel:
        logger.info("Single-channel mode: %s", args.channel)
        report = build_full_report(client, args.channel, include_comments=include_comments, max_comments=max_comments, delay_ms=delay_ms)
        export_single(report, output_dir, write_json=write_json, write_csv=write_csv)
        _print_report_summary(report, quiet=args.quiet)
        if not args.quiet:
            print(f"\nWrote output to {output_dir}")
        # Partial data may still be written; non-zero exit signals resolution/metadata failure.
        exit_code = 1 if report.error else 0
        logger.info("Finished (exit code %s)", exit_code)
        return exit_code

    batch_path = Path(args.batch)
    logger.info("Batch mode: %s", batch_path)
    if not batch_path.is_file():
        logger.error("Batch file not found: %s", batch_path)
        print(f"Batch file not found: {batch_path}", file=sys.stderr)
        return 1

    try:
        inputs = load_channel_inputs(batch_path)
    except ValueError as exc:
        logger.error("%s", exc)
        print(str(exc), file=sys.stderr)
        return 1

    if not inputs:
        logger.error("No channel inputs found in batch file")
        print("No channel inputs found in batch file.", file=sys.stderr)
        return 1

    reports, failures = run_batch(client, inputs, include_comments=include_comments, max_comments=max_comments, delay_ms=delay_ms)
    export_batch(reports, output_dir, write_json=write_json, write_csv=write_csv)

    if not args.quiet:
        print(f"\nProcessed {len(reports)} channel(s).")
        for report in reports:
            _print_report_summary(report, quiet=False)
        if failures:
            print(f"\n{len(failures)} failure(s):")
            for inp, err in failures:
                print(f"  - {inp}: {err}")
        print(f"\nWrote output to {output_dir}")

    exit_code = 1 if failures else 0
    logger.info("Finished batch (exit code %s)", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
