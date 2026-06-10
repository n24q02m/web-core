from __future__ import annotations

from pydantic import BaseModel, Field


class ScraperConfig(BaseModel):
    """Configuration for ScrapingAgent."""

    max_retries: int = Field(default=5, ge=0)
    min_content_length: int = Field(default=100, ge=0)
    enable_selector_inference: bool = True
    respect_robots: bool = True
