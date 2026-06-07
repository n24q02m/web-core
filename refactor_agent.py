import sys

file_path = "src/web_core/scraper/agent.py"
with open(file_path, "r") as f:
    lines = f.readlines()

# Find the start of _execute_node
start_line = -1
for i, line in enumerate(lines):
    if "async def _execute_node" in line:
        start_line = i
        break

if start_line == -1:
    print("Could not find _execute_node")
    sys.exit(1)

# Find the end of _execute_node (it ends before _validate_node)
end_line = -1
for i, line in enumerate(lines[start_line:], start_line):
    if "async def _validate_node" in line:
        end_line = i
        break

if end_line == -1:
    print("Could not find _validate_node")
    sys.exit(1)

# Helpers to be added
helpers = [
    "    def _handle_exhausted_strategies(self, state: ScrapingState, errors: list[str], tried: list[str]) -> ScrapingState:\n",
    "        \"\"\"Handle terminal state when strategy order is exhausted.\"\"\"\n",
    "        return {\n",
    "            **state,\n",
    "            \"success\": False,\n",
    "            \"content\": \"\",\n",
    "            \"status_code\": 0,\n",
    "            \"errors\": errors,\n",
    "            \"strategies_tried\": tried,\n",
    "        }\n",
    "\n",
    "    def _record_strategy_failure(\n",
    "        self, state: ScrapingState, strategy_name: str, error_msg: str, tried: list[str], errors: list[str]\n",
    "    ) -> ScrapingState:\n",
    "        \"\"\"Record strategy failure and return failure state.\"\"\"\n",
    "        formatted_error = error_msg if \"not found\" in error_msg else f\"{strategy_name}: {error_msg}\"\n",
    "        errors.append(formatted_error)\n",
    "        return {\n",
    "            **state,\n",
    "            \"success\": False,\n",
    "            \"content\": \"\",\n",
    "            \"status_code\": 0,\n",
    "            \"errors\": errors,\n",
    "            \"strategies_tried\": tried,\n",
    "        }\n",
    "\n",
    "    async def _perform_strategy_fetch(\n",
    "        self,\n",
    "        strategy: Any,\n",
    "        strategy_name: str,\n",
    "        url: str,\n",
    "        selectors: Any,\n",
    "        state: ScrapingState,\n",
    "        tried: list[str],\n",
    "        errors: list[str],\n",
    "    ) -> ScrapingState:\n",
    "        \"\"\"Execute strategy fetch and return success state.\"\"\"\n",
    "        t0 = time.monotonic()\n",
    "        result = await strategy.fetch(url, selectors)\n",
    "        elapsed_ms = (time.monotonic() - t0) * 1000\n",
    "\n",
    "        metadata = {\n",
    "            **state.get(\"metadata\", {}),\n",
    "            \"last_strategy\": strategy_name,\n",
    "            \"last_elapsed_ms\": elapsed_ms,\n",
    "        }\n",
    "        return {\n",
    "            **state,\n",
    "            \"content\": result.content,\n",
    "            \"status_code\": result.status_code,\n",
    "            \"strategies_tried\": tried,\n",
    "            \"errors\": errors,\n",
    "            \"metadata\": metadata,\n",
    "        }\n",
    "\n"
]

# New _execute_node
new_execute_node = [
    "    async def _execute_node(self, state: ScrapingState) -> ScrapingState:\n",
    "        \"\"\"Execute the current strategy with time tracking.\"\"\"\n",
    "        order = state.get(\"strategy_order\", [])\n",
    "        idx = state.get(\"current_strategy_idx\", 0)\n",
    "        errors = list(state.get(\"errors\", []))\n",
    "        tried = list(state.get(\"strategies_tried\", []))\n",
    "        url = state.get(\"url\", \"\")\n",
    "        selectors = state.get(\"selectors\")\n",
    "\n",
    "        if idx >= len(order):\n",
    "            return self._handle_exhausted_strategies(state, errors, tried)\n",
    "\n",
    "        strategy_name = order[idx]\n",
    "        strategy = self.strategies.get(strategy_name)\n",
    "\n",
    "        # Only add to tried list if not already there (avoids duplicates on retry)\n",
    "        if not tried or tried[-1] != strategy_name:\n",
    "            tried.append(strategy_name)\n",
    "\n",
    "        if strategy is None:\n",
    "            return self._record_strategy_failure(\n",
    "                state, strategy_name, f\"Strategy '{strategy_name}' not found\", tried, errors\n",
    "            )\n",
    "\n",
    "        try:\n",
    "            return await self._perform_strategy_fetch(\n",
    "                strategy, strategy_name, url, selectors, state, tried, errors\n",
    "            )\n",
    "        except Exception as e:\n",
    "            return self._record_strategy_failure(state, strategy_name, str(e), tried, errors)\n",
    "\n"
]

new_lines = lines[:start_line] + helpers + new_execute_node + lines[end_line:]

with open(file_path, "w") as f:
    f.writelines(new_lines)
