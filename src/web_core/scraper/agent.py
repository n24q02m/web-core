"""ScrapingAgent: LangGraph autonomous web scraper."""

from __future__ import annotations

import asyncio
from typing import Any

from langgraph.graph import END, START, StateGraph

from web_core.scraper.cache import StrategyCache
from web_core.scraper.state import ScrapingError, ScrapingState


class ScrapingAgent:
    """Orchestrates multiple scraping strategies via a LangGraph state machine.

    The agent tries strategies in cache-recommended order, validates content,
    escalates on failure, and records outcomes to the strategy cache.
    """

    def __init__(
        self,
        strategies: dict[str, Any] | None = None,
        strategy_cache: StrategyCache | None = None,
        max_retries: int = 5,
        min_content_length: int = 100,
    ):
        self.strategies = strategies or {}
        self.strategy_cache = strategy_cache or StrategyCache()
        self.max_retries = max_retries
        self.min_content_length = min_content_length
        self._graph = self._build_graph()

    def _build_graph(self):
        """Construct the LangGraph state machine."""
        graph = StateGraph(ScrapingState)

        graph.add_node("check_cache", self._check_cache_node)
        graph.add_node("select_strategy", self._select_strategy_node)
        graph.add_node("execute", self._execute_node)
        graph.add_node("validate", self._validate_node)
        graph.add_node("extract", self._extract_node)
        graph.add_node("escalate", self._escalate_node)
        graph.add_node("update_cache", self._update_cache_node)

        graph.add_edge(START, "check_cache")
        graph.add_edge("check_cache", "select_strategy")
        graph.add_edge("select_strategy", "execute")
        graph.add_edge("execute", "validate")
        graph.add_conditional_edges(
            "validate",
            self._route_after_validate,
            {"extract": "extract", "escalate": "escalate"},
        )
        graph.add_edge("extract", "update_cache")
        graph.add_conditional_edges(
            "escalate",
            self._route_after_escalate,
            {"select_strategy": "select_strategy", "update_cache": "update_cache"},
        )
        graph.add_edge("update_cache", END)

        return graph.compile()

    # ------------------------------------------------------------------
    # Node implementations
    # ------------------------------------------------------------------

    async def _check_cache_node(self, state: ScrapingState) -> ScrapingState:
        """Query strategy cache for recommended order."""
        url = state.get("url", "")
        order = await self.strategy_cache.recommend(url)

        # Preserve cache-recommended order but only include available strategies
        available_dict: dict[str, None] = {s: None for s in order if s in self.strategies}
        # Append any strategies not in the cache recommendation
        available_dict.update({s: None for s in self.strategies})
        available = list(available_dict)

        return {
            **state,
            "strategy_order": available,
            "current_strategy_idx": 0,
            "strategies_tried": [],
            "errors": list(state.get("errors", [])),
        }

    async def _select_strategy_node(self, state: ScrapingState) -> ScrapingState:
        """Select strategy (pass-through; index is managed by check_cache/escalate)."""
        return state

    async def _execute_node(self, state: ScrapingState) -> ScrapingState:
        """Execute the current strategy."""
        order = state.get("strategy_order", [])
        idx = state.get("current_strategy_idx", 0)
        errors = list(state.get("errors", []))
        tried = list(state.get("strategies_tried", []))
        url = state.get("url", "")
        selectors = state.get("selectors")

        if idx >= len(order):
            return {
                **state,
                "success": False,
                "content": "",
                "status_code": 0,
                "errors": errors,
                "strategies_tried": tried,
            }

        strategy_name = order[idx]
        strategy = self.strategies.get(strategy_name)
        tried.append(strategy_name)

        if strategy is None:
            errors.append(f"Strategy '{strategy_name}' not found")
            return {
                **state,
                "success": False,
                "content": "",
                "status_code": 0,
                "errors": errors,
                "strategies_tried": tried,
            }

        try:
            result = await strategy.fetch(url, selectors)
            return {
                **state,
                "content": result.content,
                "status_code": result.status_code,
                "strategies_tried": tried,
                "errors": errors,
                "metadata": {**state.get("metadata", {}), "last_strategy": strategy_name},
            }
        except Exception as e:
            errors.append(f"{strategy_name}: {e!s}")
            return {
                **state,
                "success": False,
                "content": "",
                "status_code": 0,
                "errors": errors,
                "strategies_tried": tried,
            }

    async def _validate_node(self, state: ScrapingState) -> ScrapingState:
        """Validate that the response is usable."""
        content = state.get("content", "")
        status_code = state.get("status_code", 0)
        valid = 200 <= status_code < 400 and len(content) >= self.min_content_length
        return {**state, "success": valid}

    def _route_after_validate(self, state: ScrapingState) -> str:
        """Route to extract on success, escalate on failure."""
        return "extract" if state.get("success", False) else "escalate"

    async def _extract_node(self, state: ScrapingState) -> ScrapingState:
        """Extract step (pass-through; content already in state)."""
        return state

    async def _escalate_node(self, state: ScrapingState) -> ScrapingState:
        """Advance to the next strategy in the order."""
        idx = state.get("current_strategy_idx", 0)
        return {**state, "current_strategy_idx": idx + 1}

    def _route_after_escalate(self, state: ScrapingState) -> str:
        """Decide whether to retry with the next strategy or give up."""
        idx = state.get("current_strategy_idx", 0)
        order = state.get("strategy_order", [])
        tried_count = len(state.get("strategies_tried", []))
        if idx < len(order) and tried_count < self.max_retries:
            return "select_strategy"
        return "update_cache"

    async def _update_cache_node(self, state: ScrapingState) -> ScrapingState:
        """Record outcomes for all tried strategies in the cache."""
        url = state.get("url", "")
        success = state.get("success", False)
        tried = state.get("strategies_tried", [])

        if not tried:
            return state

        last_strategy = tried[-1]
        tasks = [
            self.strategy_cache.record(
                url=url,
                strategy_name=strategy_name,
                success=(success and strategy_name == last_strategy),
            )
            for strategy_name in tried
        ]
        await asyncio.gather(*tasks)
        return state

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def scrape(self, url: str, selectors: dict[str, str] | None = None) -> str:
        """Scrape *url*, returning content on success or raising ScrapingError."""
        initial_state: ScrapingState = {
            "url": url,
            "selectors": selectors or {},
            "strategy_order": [],
            "current_strategy_idx": 0,
            "content": "",
            "status_code": 0,
            "success": False,
            "strategies_tried": [],
            "errors": [],
            "metadata": {},
        }
        result = await self._graph.ainvoke(initial_state)
        if not result.get("success", False):
            raise ScrapingError(
                url=url,
                strategies_tried=result.get("strategies_tried", []),
                final_error=(result["errors"][-1] if result.get("errors") else "No strategies available"),
            )
        return result.get("content", "")
