"""Small YouTube Data API client wrapper used by service modules.

The rest of the codebase works with google-api-python-client request objects,
but sends them through ``YouTubeClient.call`` so logging and optional throttling
are centralized. The wrapper also exposes the API key so worker threads can
construct their own clients without sharing googleapiclient service instances.
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
    """Authenticated YouTube Data API v3 client.

    Args:
        api_key: Optional explicit key. When omitted, the key is loaded from
            ``YOUTUBE_API_KEY`` via ``core.config.load_api_key``.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else load_api_key()
        self._service = self._build_service(self._api_key)

    @property
    def service(self) -> Any:
        """Return the underlying google-api-python-client service object."""
        return self._service

    @property
    def api_key(self) -> str:
        """Return the key used to build this client.

        This is intentionally available for thread fan-out: each worker creates
        a fresh service object instead of sharing one across threads.
        """
        return self._api_key

    def _build_service(self, api_key: str) -> Any:
        """Build a YouTube Data API v3 service object without discovery caching."""
        return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=api_key, cache_discovery=False)

    def call(self, request: Any, delay_ms: int = 0) -> dict[str, Any]:
        """Execute a prepared API request, log timing, and optionally throttle.

        Any API exceptions are intentionally allowed to propagate so the service
        layer that understands the request context can decide whether to retry,
        mark a partial result, or surface an error.
        """
        logger.debug("Executing YouTube API request")
        start = time.perf_counter()
        result: dict[str, Any] = request.execute()
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.debug("API call completed in %.0fms (delay_ms=%s)", elapsed_ms, delay_ms)
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
        return result
