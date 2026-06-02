"""Runtime dependency model for video_lambda."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from video_job.model.settings import Settings


class Runtime(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    settings: Settings
    event: dict[str, Any] | None
    youtube_client: Any
    s3_client: Any
    mongo_writer: Any
