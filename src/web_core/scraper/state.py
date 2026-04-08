"""Scraping state and error types."""

from __future__ import annotations

from typing import Any, TypedDict


class ScrapingError(Exception):
    """Raised when all scraping strategies are exhausted."""

    def __init__(self, url: str, strategies_tried: list[str], final_error: str):
        self.url = url
        self.strategies_tried = strategies_tried
        self.final_error = final_error
        super().__init__(f"All strategies failed for {url}: tried {strategies_tried}, last error: {final_error}")


class ScrapingState(TypedDict, total=False):
    """State passed through the scraping LangGraph workflow."""

    url: str
    selectors: dict[str, str]
    strategy_order: list[str]
    current_strategy_idx: int
    content: str
    status_code: int
    success: bool
    strategies_tried: list[str]
    errors: list[str]
    metadata: dict[str, Any]
    # LLM selector inference
    inferred_selectors: dict[str, str]
    selector_inference_attempted: bool
