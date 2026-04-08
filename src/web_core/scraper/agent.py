"""ScrapingAgent: LangGraph autonomous web scraper.

Enhanced with:
- Domain-specific selector configuration for known sites
- LLM-based CSS selector inference when default selectors fail
- Time tracking per strategy execution for cache optimization
- Configurable content extraction with inferred selectors
"""

from __future__ import annotations

import time
from typing import Any

from langgraph.graph import END, START, StateGraph

from web_core.scraper.cache import StrategyCache
from web_core.scraper.selector_inference import (
    get_domain_selectors,
    infer_selectors_with_llm,
    merge_selectors,
)
from web_core.scraper.state import ScrapingError, ScrapingState
from web_core.scraper.utils import is_cloudflare_challenge


class ScrapingAgent:
    """Orchestrates multiple scraping strategies via a LangGraph state machine.

    The agent tries strategies in cache-recommended order, validates content,
    escalates on failure, and records outcomes to the strategy cache.

    Enhanced with LLM-based selector inference: when a strategy returns valid
    HTML but content extraction yields nothing useful, the agent can use an
    LLM to infer CSS selectors from the page structure and retry extraction.
    """

    def __init__(
        self,
        strategies: dict[str, Any] | None = None,
        strategy_cache: StrategyCache | None = None,
        max_retries: int = 5,
        min_content_length: int = 100,
        enable_selector_inference: bool = True,
    ):
        self.strategies = strategies or {}
        self.strategy_cache = strategy_cache or StrategyCache()
        self.max_retries = max_retries
        self.min_content_length = min_content_length
        self.enable_selector_inference = enable_selector_inference
        self._graph = self._build_graph()

    def _build_graph(self):
        """Construct the LangGraph state machine.

        Flow:
        START → check_cache → select_strategy → execute → validate
          ├─ (success) → extract → update_cache → END
          └─ (fail) → infer_selectors (optional) → escalate
              ├─ (more strategies) → select_strategy (loop)
              └─ (exhausted) → update_cache → END
        """
        graph = StateGraph(ScrapingState)

        graph.add_node("check_cache", self._check_cache_node)
        graph.add_node("select_strategy", self._select_strategy_node)
        graph.add_node("execute", self._execute_node)
        graph.add_node("validate", self._validate_node)
        graph.add_node("extract", self._extract_node)
        graph.add_node("infer_selectors", self._infer_selectors_node)
        graph.add_node("escalate", self._escalate_node)
        graph.add_node("update_cache", self._update_cache_node)

        graph.add_edge(START, "check_cache")
        graph.add_edge("check_cache", "select_strategy")
        graph.add_edge("select_strategy", "execute")
        graph.add_edge("execute", "validate")
        graph.add_conditional_edges(
            "validate",
            self._route_after_validate,
            {"extract": "extract", "infer_selectors": "infer_selectors", "escalate": "escalate"},
        )
        graph.add_edge("extract", "update_cache")
        graph.add_conditional_edges(
            "infer_selectors",
            self._route_after_infer,
            {"execute": "execute", "escalate": "escalate"},
        )
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
        """Query strategy cache for recommended order and domain config."""
        url = state.get("url", "")
        order = await self.strategy_cache.recommend(url)

        # Preserve cache-recommended order but only include available strategies
        available_dict: dict[str, None] = {s: None for s in order if s in self.strategies}
        # Append any strategies not in the cache recommendation
        available_dict.update({s: None for s in self.strategies})
        available = list(available_dict)

        # Apply domain-specific selectors if no selectors provided
        selectors = dict(state.get("selectors", {}))
        if not selectors:
            domain_selectors = get_domain_selectors(url)
            if domain_selectors:
                selectors = domain_selectors

        return {
            **state,
            "selectors": selectors,
            "strategy_order": available,
            "current_strategy_idx": 0,
            "strategies_tried": [],
            "errors": list(state.get("errors", [])),
            "selector_inference_attempted": False,
            "inferred_selectors": {},
        }

    async def _select_strategy_node(self, state: ScrapingState) -> ScrapingState:
        """Select strategy (pass-through; index is managed by check_cache/escalate)."""
        return state

    async def _execute_node(self, state: ScrapingState) -> ScrapingState:
        """Execute the current strategy with time tracking."""
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

        # Only add to tried list if not already there (avoids duplicates on retry)
        if not tried or tried[-1] != strategy_name:
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
            t0 = time.monotonic()
            result = await strategy.fetch(url, selectors)
            elapsed_ms = (time.monotonic() - t0) * 1000

            metadata = {
                **state.get("metadata", {}),
                "last_strategy": strategy_name,
                "last_elapsed_ms": elapsed_ms,
            }
            return {
                **state,
                "content": result.content,
                "status_code": result.status_code,
                "strategies_tried": tried,
                "errors": errors,
                "metadata": metadata,
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
        """Validate that the response is usable.

        Rejects responses that:
        - Have non-2xx/3xx status codes
        - Are shorter than min_content_length
        - Contain Cloudflare challenge HTML (JS challenge, Turnstile, managed)
        """
        content = state.get("content", "")
        status_code = state.get("status_code", 0)
        errors = list(state.get("errors", []))

        status_ok = 200 <= status_code < 400
        length_ok = len(content) >= self.min_content_length
        cf_challenge = is_cloudflare_challenge(content) if content else False

        if cf_challenge:
            strategy = state.get("metadata", {}).get("last_strategy", "unknown")
            errors.append(f"{strategy}: Cloudflare challenge detected in response")

        valid = status_ok and length_ok and not cf_challenge
        return {**state, "success": valid, "errors": errors}

    def _route_after_validate(self, state: ScrapingState) -> str:
        """Route to extract on success, try LLM inference if enabled, else escalate."""
        if state.get("success", False):
            return "extract"
        # If we have HTML content but it was too short / didn't pass validation,
        # and we haven't tried LLM inference yet, try it
        content = state.get("content", "")
        if (
            self.enable_selector_inference
            and content
            and len(content) > 50
            and not state.get("selector_inference_attempted", False)
        ):
            return "infer_selectors"
        return "escalate"

    async def _extract_node(self, state: ScrapingState) -> ScrapingState:
        """Extract step (pass-through; content already in state)."""
        return state

    async def _infer_selectors_node(self, state: ScrapingState) -> ScrapingState:
        """Use LLM to infer CSS selectors from the HTML content.

        Only runs once per scrape — if it fails, we fall through to escalate.
        """
        url = state.get("url", "")
        content = state.get("content", "")
        existing_selectors = state.get("selectors", {})

        # First try domain config (no LLM call needed)
        domain_selectors = get_domain_selectors(url)
        if domain_selectors and not existing_selectors:
            return {
                **state,
                "selectors": domain_selectors,
                "inferred_selectors": domain_selectors,
                "selector_inference_attempted": True,
            }

        # LLM inference
        try:
            inferred = await infer_selectors_with_llm(url, content)
            if inferred:
                merged = merge_selectors(existing_selectors, inferred)
                return {
                    **state,
                    "selectors": merged,
                    "inferred_selectors": inferred,
                    "selector_inference_attempted": True,
                }
        except Exception:
            pass

        return {**state, "selector_inference_attempted": True}

    def _route_after_infer(self, state: ScrapingState) -> str:
        """After selector inference, retry current strategy if new selectors found."""
        inferred = state.get("inferred_selectors", {})
        if inferred:
            return "execute"  # Retry with new selectors
        return "escalate"

    async def _escalate_node(self, state: ScrapingState) -> ScrapingState:
        """Advance to the next strategy in the order."""
        idx = state.get("current_strategy_idx", 0)
        return {
            **state,
            "current_strategy_idx": idx + 1,
            "selector_inference_attempted": False,  # Reset for next strategy
        }

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
        elapsed_ms = state.get("metadata", {}).get("last_elapsed_ms", 0.0)

        for strategy_name in tried:
            is_success = success and strategy_name == tried[-1]
            await self.strategy_cache.record(
                url=url,
                strategy_name=strategy_name,
                success=is_success,
                time_ms=elapsed_ms if is_success else 0.0,
            )
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
            "inferred_selectors": {},
            "selector_inference_attempted": False,
        }
        result = await self._graph.ainvoke(initial_state)
        if not result.get("success", False):
            raise ScrapingError(
                url=url,
                strategies_tried=result.get("strategies_tried", []),
                final_error=(result["errors"][-1] if result.get("errors") else "No strategies available"),
            )
        return result.get("content", "")
