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

        # Store the API key for service building
        self._api_key = api_key

        # Build the internal YouTube service client
        self._service = self._build_service(api_key)

    @property
    def service(self) -> Any:

        # Expose the internal service client
        return self._service

    @property
    def api_key(self) -> str:

        # Expose the API key used for this client
        return self._api_key

    def _build_service(self, api_key: str) -> Any:

        # Create the Google API service without discovery caching
        return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=api_key, cache_discovery=False)

    def call(self, request: Any, delay_ms: int = 0) -> dict[str, Any]:

        # Log the intent to execute an API request
        logger.debug("Executing YouTube API request")

        # Track the start time for performance measurement
        start = time.perf_counter()

        # Execute the request and capture the response
        result: dict[str, Any] = request.execute()

        # Log completion details and execution time
        logger.debug("API call completed in %.0fms (delay_ms=%s)", (time.perf_counter() - start) * 1000, delay_ms)

        # Apply a delay if throttling is requested
        if delay_ms > 0:

            # Sleep for the specified duration in milliseconds
            time.sleep(delay_ms / 1000.0)

        # Return the resulting response dictionary
        return result
