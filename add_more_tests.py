import sys

path = 'tests/test_search/test_runner.py'
with open(path, 'r') as f:
    lines = f.readlines()

extra_tests = [
    "    async def test_restart_on_crash_with_stderr(self, tmp_discovery, monkeypatch):\n",
    "        \"\"\"Cover line 858: successful stderr reading during crash.\"\"\"\n",
    "        import web_core.search.runner as mod\n",
    "        monkeypatch.delenv(\"SEARXNG_URL\", raising=False)\n",
    "        mock_proc = MagicMock()\n",
    "        mock_proc.poll.return_value = 1\n",
    "        mock_proc.pid = 12345\n",
    "        mock_proc.stderr = MagicMock()\n",
    "        mock_proc.stderr.read.return_value = b\"some error output\"\n",
    "        mod._searxng_process = mock_proc\n",
    "        mod._searxng_port = 18888\n",
    "        with (\n",
    "            patch(\"web_core.search.runner._try_reuse_existing\", new_callable=AsyncMock, return_value=None),\n",
    "            patch(\"web_core.search.runner._is_searxng_installed\", return_value=True),\n",
    "            patch(\"web_core.search.runner._start_searxng_subprocess\", new_callable=AsyncMock, return_value=\"http://127.0.0.1:18889\"),\n",
    "        ):\n",
    "            await ensure_searxng()\n",
    "\n",
    "    async def test_restart_with_cooldown(self, tmp_discovery, monkeypatch):\n",
    "        \"\"\"Cover lines 881-883: cooldown logic.\"\"\"\n",
    "        import web_core.search.runner as mod\n",
    "        monkeypatch.delenv(\"SEARXNG_URL\", raising=False)\n",
    "        mod._restart_count = 1\n",
    "        mod._last_restart_time = time.time()\n",
    "        with (\n",
    "            patch(\"web_core.search.runner._try_reuse_existing\", new_callable=AsyncMock, return_value=None),\n",
    "            patch(\"web_core.search.runner._is_searxng_installed\", return_value=True),\n",
    "            patch(\"web_core.search.runner._start_searxng_subprocess\", new_callable=AsyncMock, return_value=\"http://127.0.0.1:18889\"),\n",
    "            patch(\"asyncio.sleep\", new_callable=AsyncMock) as mock_sleep,\n",
    "        ):\n",
    "            await ensure_searxng()\n",
    "            mock_sleep.assert_called_once()\n",
    "\n",
    "    async def test_restart_alive_but_unhealthy(self, tmp_discovery, monkeypatch):\n",
    "        \"\"\"Cover lines 819-826: process alive but unhealthy.\"\"\"\n",
    "        import web_core.search.runner as mod\n",
    "        monkeypatch.delenv(\"SEARXNG_URL\", raising=False)\n",
    "        mock_proc = MagicMock()\n",
    "        mock_proc.pid = 12345\n",
    "        mod._searxng_process = mock_proc\n",
    "        mod._searxng_port = 18888\n",
    "        with (\n",
    "            patch(\"web_core.search.runner._is_process_alive\", return_value=True),\n",
    "            patch(\"web_core.search.runner._quick_health_check\", new_callable=AsyncMock, return_value=False),\n",
    "            patch(\"web_core.search.runner._try_reuse_existing\", new_callable=AsyncMock, return_value=None),\n",
    "            patch(\"web_core.search.runner._is_searxng_installed\", return_value=True),\n",
    "            patch(\"web_core.search.runner._start_searxng_subprocess\", new_callable=AsyncMock, return_value=\"http://127.0.0.1:18889\"),\n",
    "            patch(\"web_core.search.runner._force_kill_process\") as mock_kill,\n",
    "        ):\n",
    "            await ensure_searxng()\n",
    "            mock_kill.assert_called_once_with(mock_proc)\n",
    "            assert mod._searxng_port is None or mod._searxng_port != 18888 # It should have been cleared then maybe set again by start\n",
    "\n"
]

insertion_point = -1
for i, line in enumerate(lines):
    if 'async def test_installs_and_starts' in line:
        insertion_point = i
        break

if insertion_point != -1:
    lines[insertion_point:insertion_point] = extra_tests
    with open(path, 'w') as f:
        f.writelines(lines)
    print("Successfully inserted extra tests.")
else:
    print("Could not find insertion point.")
