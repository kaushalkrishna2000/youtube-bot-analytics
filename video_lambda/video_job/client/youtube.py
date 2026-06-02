"""Small YouTube Data API client wrapper for video_lambda."""

from __future__ import annotations

import logging
import time
from typing import Any

from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"


class YouTubeClient:
    """Small wrapper around the YouTube Data API service client."""

    def __init__(self, api_key: str) -> None:
        """Create a YouTube API service for the provided key.

        Args:
            api_key: YouTube Data API key.
        """
        self._api_key = api_key
        self._service = self._build_service(api_key)

    @property
    def service(self) -> Any:
        """Return the underlying Google API service object."""
        return self._service

    @property
    def api_key(self) -> str:
        """Return the API key used to build the service."""
        return self._api_key

    def _build_service(self, api_key: str) -> Any:
        """Build the YouTube Data API service without discovery caching."""
        return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=api_key, cache_discovery=False)

    def call(self, request: Any, delay_ms: int = 0) -> dict[str, Any]:
        """Execute a YouTube API request and apply optional throttling.

        Args:
            request: Google API request object with an ``execute`` method.
            delay_ms: Delay to sleep after the request completes.

        Returns:
            Response dictionary from the YouTube API.
        """
        logger.debug("Executing YouTube API request")
        start = time.perf_counter()
        result: dict[str, Any] = request.execute()
        logger.debug("API call completed in %.0fms (delay_ms=%s)", (time.perf_counter() - start) * 1000, delay_ms)
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
        return result
