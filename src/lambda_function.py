"""AWS Lambda entrypoint for channel batch fetch (lightweight wrapper)."""

from __future__ import annotations

import os
from typing import Any

from lambda_runner import build_lambda_response, run_fetch_job
from utils.basic_utils import normalize_nonempty_str_list

# Optional direct in-code channel list. If empty, YOUTUBE_CHANNELS is used.
DEFAULT_CHANNELS: list[str] = []


def lambda_handler(event: dict[str, Any] | None, context: Any) -> dict[str, Any]:
    # event and context are intentionally unused in this version.
    if DEFAULT_CHANNELS:
        channels = normalize_nonempty_str_list(DEFAULT_CHANNELS)
    else:
        raw_env = os.getenv("YOUTUBE_CHANNELS", "")
        channels = normalize_nonempty_str_list(raw_env.split(",")) if raw_env.strip() else []

    if not channels:
        return build_lambda_response(
            400,
            {
                "ok": False,
                "error": "No channels configured. Set DEFAULT_CHANNELS in code or YOUTUBE_CHANNELS env var.",
            },
        )

    result = run_fetch_job(channels, quiet=True)
    return build_lambda_response(200, result)
