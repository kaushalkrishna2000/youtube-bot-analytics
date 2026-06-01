"""
Thin wrapper around google-api-python-client for YouTube Data API v3.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from googleapiclient.discovery import build

from core.config import load_api_key

logger = logging.getLogger(__name__)

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"


class YouTubeClient:
    """Authenticated YouTube Data API v3 client."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else load_api_key()
        self._service = self._build_service(self._api_key)

    @property
    def service(self) -> Any:
        return self._service

    def _build_service(self, api_key: str) -> Any:
        return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=api_key, cache_discovery=False)

    def call(self, request: Any, delay_ms: int = 0) -> dict[str, Any]:
        logger.debug("Executing YouTube API request")
        start = time.perf_counter()
        result: dict[str, Any] = request.execute()
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.debug("API call completed in %.0fms (delay_ms=%s)", elapsed_ms, delay_ms)
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
        return result
