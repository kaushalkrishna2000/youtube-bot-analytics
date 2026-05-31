"""Argument parsing for fetch subcommands."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YouTube bot analytics fetcher")
    parser.add_argument("--output-dir", type=Path, default=None, metavar="PATH", help="Optional output base directory override")
    parser.add_argument("--delay-ms", type=int, default=None, help="Delay between API calls in milliseconds")
    parser.add_argument("--no-comments", action="store_true", help="Skip comment fetching and enrichment")
    parser.add_argument("--quiet", action="store_true", help="Suppress summary output and flow logs (errors only)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Explicit INFO logs (default behavior)")
    parser.add_argument("--debug", action="store_true", help="Show detailed logs")

    subparsers = parser.add_subparsers(dest="command", required=True)
    fetch_parser = subparsers.add_parser("fetch", help="Run fetch workflows")
    fetch_subparsers = fetch_parser.add_subparsers(dest="fetch_mode", required=True)

    channel_parser = fetch_subparsers.add_parser("channel", help="Channel-based fetch mode")
    channel_subparsers = channel_parser.add_subparsers(dest="channel_mode", required=True)

    channel_single = channel_subparsers.add_parser("single", help="Fetch one channel")
    channel_single.add_argument("--channel", required=True, help="Channel URL, @handle, or UC... channel ID")
    channel_single.add_argument("--max-videos", type=int, default=10, help="Latest videos to fetch (default: 10)")
    channel_single.add_argument("--max-comments", type=int, default=1000, help="Top comments per video (default: 1000)")

    channel_batch = channel_subparsers.add_parser("batch", help="Fetch channels from file")
    channel_batch.add_argument("--batch", required=True, metavar="FILE", help="Path to .txt or .csv file with channel inputs")
    channel_batch.add_argument("--max-videos", type=int, default=10, help="Latest videos per channel (default: 10)")
    channel_batch.add_argument("--max-comments", type=int, default=1000, help="Top comments per video (default: 1000)")

    video_parser = fetch_subparsers.add_parser("video", help="Video-based fetch mode")
    video_parser.add_argument("--video-id", required=True, help="YouTube video ID")
    video_parser.add_argument("--max-comments", type=int, default=1000, help="Top comments (default: 1000)")

    return parser.parse_args()
