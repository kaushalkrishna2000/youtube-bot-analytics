"""Runtime dependency model for channel_lambda."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from channel_job.model.settings import Settings


class Runtime(BaseModel):
    """Per-invocation dependency bundle for the channel staging runner."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    settings: Settings
    job_id: str
    youtube_client: Any
    s3_client: Any
    mongo_writer: Any
