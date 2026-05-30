"""
Thin wrapper around google-api-python-client for YouTube Data API v3.

How a YouTube API call works (no lambdas needed)
-------------------------------------------------
The Google library uses two steps:

  1. **Build** a request object (no network yet):
         request = client.service.channels().list(part="id", forHandle="mrbeast")

  2. **Execute** it (HTTP happens here):
         data = client.call(request)

``YouTubeClient.call()`` only wraps step 2 so every request gets logging,
timing, and an optional delay after the response (rate limiting).

``client.service`` is the generated YouTube v3 API object from
``googleapiclient.discovery.build()``.
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
        # api_key is reserved for tests; production loads from src/credentials/.env.
        self._api_key = api_key if api_key is not None else load_api_key()
        self._service = self._build_service(self._api_key)

    @property
    def service(self) -> Any:
        """Low-level API object — use with .channels(), .videos(), .commentThreads(), etc."""
        return self._service

    def _build_service(self, api_key: str) -> Any:
        return build(YOUTUBE_API_SERVICE_NAME,YOUTUBE_API_VERSION,developerKey=api_key,cache_discovery=False)

    def call(self, request: Any, delay_ms: int = 0) -> dict[str, Any]:
        """
        Execute a prepared API request and return the parsed JSON dict.

        Args:
            request: Return value of e.g. ``service.channels().list(...)``.
                     Not executed until ``.execute()`` runs inside this method.
            delay_ms: Milliseconds to sleep *after* a successful response.
        """
        logger.debug("Executing YouTube API request")
        start = time.perf_counter()
        result: dict[str, Any] = request.execute()
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.debug("API call completed in %.0fms (delay_ms=%s)", elapsed_ms, delay_ms)
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
        return result
