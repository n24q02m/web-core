# CHANGELOG

<!-- version list -->

## v1.3.3 (2026-04-22)

### Bug Fixes

- Relax pydantic lower bound to >=2.12.5 for cohere compatibility
  ([`4a04a45`](https://github.com/n24q02m/web-core/commit/4a04a45f13426f781287297a1d63740a053913b3))


## v1.3.2 (2026-04-22)

### Bug Fixes

- Restore SearchResult.to_dict (used by wet-mcp MCP tool responses)
  ([`d5fdb62`](https://github.com/n24q02m/web-core/commit/d5fdb621afe4ee01952610524c8741fc2cad96a3))

- **deps**: Update non-major dependencies ([#183](https://github.com/n24q02m/web-core/pull/183),
  [`570ee48`](https://github.com/n24q02m/web-core/commit/570ee4820cc4a1a4860bbf1c2155300da9f570d0))

### Chores

- **deps**: Lock file maintenance ([#185](https://github.com/n24q02m/web-core/pull/185),
  [`2e13da0`](https://github.com/n24q02m/web-core/commit/2e13da0adf3b38e781448d263afa197e70c57f8a))

- **deps**: Update astral-sh/setup-uv action to v8
  ([#184](https://github.com/n24q02m/web-core/pull/184),
  [`80744a5`](https://github.com/n24q02m/web-core/commit/80744a59f08da6ab6596ac06e9ea2a3677068252))

### Performance Improvements

- **http**: Fast-path URL query parameter tracking check
  ([#186](https://github.com/n24q02m/web-core/pull/186),
  [`58724e0`](https://github.com/n24q02m/web-core/commit/58724e03b44125096a26bcbc6fe70e597ce42876))


## v1.3.1 (2026-04-21)

### Bug Fixes

- Mount settings.yml in Docker SearXNG so JSON format works
  ([`103c831`](https://github.com/n24q02m/web-core/commit/103c831b195b0620c137fd5ea2ff96b8ba7f2ab2))

- Scope CD notify-downstream app token to n24q02m profile repo
  ([`0246407`](https://github.com/n24q02m/web-core/commit/0246407470df22483a775df3ca9bdda09631e713))


## v1.3.0 (2026-04-21)

### Bug Fixes

- [SECURITY] Unsafe domain name validation using regex with missing end anchor
  ([#158](https://github.com/n24q02m/web-core/pull/158),
  [`f8c02b9`](https://github.com/n24q02m/web-core/commit/f8c02b9c0e55ae5736eb1c8923b13c49b1bf0a26))

- Add diacritic preservation pre-commit hook ([#164](https://github.com/n24q02m/web-core/pull/164),
  [`df11645`](https://github.com/n24q02m/web-core/commit/df116459dea7c7efb2085b353c33423e7206fbda))

- Apply ruff format to selector_inference + test
  ([`2a638c5`](https://github.com/n24q02m/web-core/commit/2a638c58d117efd82bc7f1fc2d63b8ff5b73d214))

- Bump non-major Python deps (lock file maintenance)
  ([`200a6d0`](https://github.com/n24q02m/web-core/commit/200a6d0e13a3adbbfcc631f33bc57515413e91ff))

- Bump step-security/harden-runner digest to 8d3c67d
  ([`901583e`](https://github.com/n24q02m/web-core/commit/901583e920ce152cf925194ef839fbc85d0499ca))

- Ignore coverage.xml and htmlcov artifacts
  ([`b90c24e`](https://github.com/n24q02m/web-core/commit/b90c24e552eedd733138662c0ae8b8427b8b20d5))

- Move safe_httpx_client import to top of google_drive module
  ([#156](https://github.com/n24q02m/web-core/pull/156),
  [`98d84f2`](https://github.com/n24q02m/web-core/commit/98d84f28de5276575f12e937b3687a33a3f0c0b2))

- Optimize URL parsing and domain deduplication in search client
  ([`c074f6c`](https://github.com/n24q02m/web-core/commit/c074f6cc6cf0fa21c0e1cb7ad41c0f938c15d597))

- Pin pillow >=12.2.0 to resolve GHSA-whj4-6x5x-4v2j
  ([#156](https://github.com/n24q02m/web-core/pull/156),
  [`98d84f2`](https://github.com/n24q02m/web-core/commit/98d84f28de5276575f12e937b3687a33a3f0c0b2))

- Pin pillow >=12.2.0 to resolve GHSA-whj4-6x5x-4v2j
  ([`e55d984`](https://github.com/n24q02m/web-core/commit/e55d984b14e6cee1b7399677bb7842f9bd61c6a7))

- Pin pillow >=12.2.0 to resolve GHSA-whj4-6x5x-4v2j FITS GZIP bomb
  ([`8be31b5`](https://github.com/n24q02m/web-core/commit/8be31b5a3e227fb62925f888f960664c5e0dae12))

- Prevent sys.modules[httpx] pollution in selector_inference tests
  ([#172](https://github.com/n24q02m/web-core/pull/172),
  [`c0af4fe`](https://github.com/n24q02m/web-core/commit/c0af4fef8c4b292e5b9e66a8309003acc85d37bb))

- Remove hardcoded LLM model in selector_inference, add multi-provider auto-detect via env vars
  ([`70088e6`](https://github.com/n24q02m/web-core/commit/70088e6fd903979544e7bf45ff5cbf755c9511b2))

- Remove unused build_page_url helper from mangadex adapter
  ([`d028e89`](https://github.com/n24q02m/web-core/commit/d028e899c499f8c7f99d731faca55f8c876b7945))

- Resolve ruff lint errors in test_patchright.py
  ([`8be31b5`](https://github.com/n24q02m/web-core/commit/8be31b5a3e227fb62925f888f960664c5e0dae12))

- Scope CI concurrency group by event_name ([#164](https://github.com/n24q02m/web-core/pull/164),
  [`df11645`](https://github.com/n24q02m/web-core/commit/df116459dea7c7efb2085b353c33423e7206fbda))

- Silence ty unsupported-operator on subprocess.run(text=True) stdout
  ([#163](https://github.com/n24q02m/web-core/pull/163),
  [`4c26a90`](https://github.com/n24q02m/web-core/commit/4c26a90ccf7bfc9589dcbef983ea58cdc58a1710))

- Switch to safe_httpx_client in Google Drive adapter
  ([#150](https://github.com/n24q02m/web-core/pull/150),
  [`94c3d44`](https://github.com/n24q02m/web-core/commit/94c3d44a6cfa75e52be46fd1a070fedae994b210))

- Untrack .jules AI traces + gitignore AI-trace dirs
  ([`c97adbc`](https://github.com/n24q02m/web-core/commit/c97adbc0a51e1373f56bb468f2ad7e13aaae2d2a))

- Use secrets.token_hex(32) for SEARXNG_SECRET instead of hardcoded literal
  ([`c0474ee`](https://github.com/n24q02m/web-core/commit/c0474eec9c2a4045b453f557ca864bf4e4409d54))

- **deps**: Bump pytest to 9.0.3 [security] ([#142](https://github.com/n24q02m/web-core/pull/142),
  [`7f2c02e`](https://github.com/n24q02m/web-core/commit/7f2c02ea094bf47ef39ab52351c2f3f7663efbea))

- **deps**: Lock file maintenance ([#138](https://github.com/n24q02m/web-core/pull/138),
  [`5813715`](https://github.com/n24q02m/web-core/commit/5813715a941363ced25ed575665df619915e2782))

- **deps**: Lock file maintenance (filelock 3.28.0->3.29.0)
  ([`ad43150`](https://github.com/n24q02m/web-core/commit/ad43150c2139d0e60a655c6b4ad54e5483e4c36c))

- **scraper**: Remove hardcoded Syosetu age bypass cookie
  ([#160](https://github.com/n24q02m/web-core/pull/160),
  [`4c71b91`](https://github.com/n24q02m/web-core/commit/4c71b91cef66f58623614c05f8f784f2a5390dde))

- **scraper**: Secure domain wildcard matching regex
  ([#157](https://github.com/n24q02m/web-core/pull/157),
  [`e65a751`](https://github.com/n24q02m/web-core/commit/e65a751a4ec8fcb7a27b853a48aea5f9d667b287))

### Chores

- **deps**: Lock file maintenance ([#173](https://github.com/n24q02m/web-core/pull/173),
  [`d16bbfb`](https://github.com/n24q02m/web-core/commit/d16bbfbbb720e829e4f3f9baebd127d07b8c1a92))

- **deps**: Lock file maintenance ([#171](https://github.com/n24q02m/web-core/pull/171),
  [`abd6833`](https://github.com/n24q02m/web-core/commit/abd683330475cdef15d5891390c70e70999b0d69))

- **deps**: Lock file maintenance ([#168](https://github.com/n24q02m/web-core/pull/168),
  [`6d2e369`](https://github.com/n24q02m/web-core/commit/6d2e369db1db7ae5c5da8f244b6456eca8376caf))

- **deps**: Update actions/create-github-app-token digest to 1b10c78
  ([#137](https://github.com/n24q02m/web-core/pull/137),
  [`9757b3a`](https://github.com/n24q02m/web-core/commit/9757b3a63565363fe9435d91861762d796010ba6))

- **deps**: Update github/codeql-action digest to 95e58e9
  ([#166](https://github.com/n24q02m/web-core/pull/166),
  [`c6d0415`](https://github.com/n24q02m/web-core/commit/c6d04153823195ca15caee8fa98e1abb93d85bd5))

- **deps**: Update step-security/harden-runner digest to 6c3c2f2
  ([#167](https://github.com/n24q02m/web-core/pull/167),
  [`e07d3a7`](https://github.com/n24q02m/web-core/commit/e07d3a7c6c1a9ad7e4083f5f550b8c58fbac2b74))

### Features

- Auto-create downstream bump issues on stable release
  ([`c486017`](https://github.com/n24q02m/web-core/commit/c48601738670af2af7a0c2d501d376154aa2cf5c))

### Performance Improvements

- Lazy load gdown in google_drive adapter ([#156](https://github.com/n24q02m/web-core/pull/156),
  [`98d84f2`](https://github.com/n24q02m/web-core/commit/98d84f28de5276575f12e937b3687a33a3f0c0b2))

- Replace blocking sleep with asyncio.sleep in search runner
  ([#163](https://github.com/n24q02m/web-core/pull/163),
  [`4c26a90`](https://github.com/n24q02m/web-core/commit/4c26a90ccf7bfc9589dcbef983ea58cdc58a1710))

- Replace blocking sleep with asyncio.sleep in search runner (final fix)
  ([#163](https://github.com/n24q02m/web-core/pull/163),
  [`4c26a90`](https://github.com/n24q02m/web-core/commit/4c26a90ccf7bfc9589dcbef983ea58cdc58a1710))

- Replace blocking sleep with asyncio.sleep in search runner (fix CI)
  ([#163](https://github.com/n24q02m/web-core/pull/163),
  [`4c26a90`](https://github.com/n24q02m/web-core/commit/4c26a90ccf7bfc9589dcbef983ea58cdc58a1710))

- Replace blocking sleep with asyncio.sleep in search runner (fix lint)
  ([#163](https://github.com/n24q02m/web-core/pull/163),
  [`4c26a90`](https://github.com/n24q02m/web-core/commit/4c26a90ccf7bfc9589dcbef983ea58cdc58a1710))

- **scraper**: Optimize Turnstile sitekey extraction regex
  ([#170](https://github.com/n24q02m/web-core/pull/170),
  [`2a16a74`](https://github.com/n24q02m/web-core/commit/2a16a744c168d0c9d3f582e964657ac5b56e3079))

### Testing

- **scraper**: Add unit tests for merge_selectors utility
  ([#148](https://github.com/n24q02m/web-core/pull/148),
  [`9aa0c61`](https://github.com/n24q02m/web-core/commit/9aa0c61eede52131c26ec89ea602ee0301bed795))


## v1.2.0 (2026-04-17)

### Bug Fixes

- Bump gdown + langsmith + pytest for CVE-2026-40491, GHSA-rr7j-v2q5-chgv, CVE-2025-71176
  ([`eae7fc0`](https://github.com/n24q02m/web-core/commit/eae7fc05e835c053ec1e5977c423f25538151478))

- Bump pillow to 12.2.0 for FITS GZIP decompression bomb (CVE-2026-40192)
  ([`d4f787e`](https://github.com/n24q02m/web-core/commit/d4f787ea4d57f9b6270e130c0c6875cbcdcfa0f4))

- Correct README installation instructions to use PyPI package name
  ([`ff1ef31`](https://github.com/n24q02m/web-core/commit/ff1ef317dbc08c9115a04da72b3a6fdbf54ee0d9))

- Exempt SearXNG from SSRF check since it runs on localhost
  ([`d65d11f`](https://github.com/n24q02m/web-core/commit/d65d11ff377fcbdf7410028d054a1babf518187f))

- Lower coverage threshold to 85% to reflect untestable external dependencies
  ([`a83ca65`](https://github.com/n24q02m/web-core/commit/a83ca657277285c8e5cfe24ed9188bf79a5b744f))

- Mock patchright in captcha test to avoid browser dependency in CI
  ([`c080e7c`](https://github.com/n24q02m/web-core/commit/c080e7c4392958f4e1528c9b4a85838b253e7bce))

- Remove fuzzy kwarg for gdown 6.0 compat
  ([`ecb2a73`](https://github.com/n24q02m/web-core/commit/ecb2a73f7af17202377f494e1e2df48950807f44))

- Sync local changes from workspace
  ([`bcdb493`](https://github.com/n24q02m/web-core/commit/bcdb49398a1c2832e4a56b07f605ae185e40088f))

- **scraper**: Correct patchright wait_until test assertion to match source
  ([#135](https://github.com/n24q02m/web-core/pull/135),
  [`8d81f02`](https://github.com/n24q02m/web-core/commit/8d81f02bf40fd78d2a2533b092ffaf25f78dd4e6))

- **search**: Add explicit warning if Docker Daemon is down
  ([`28c6d23`](https://github.com/n24q02m/web-core/commit/28c6d23757eb7cf90d3cf0cbd219d302ef11a805))

- **search**: Fallback to Docker SearXNG on Windows/macOS to avoid env issues
  ([#753](https://github.com/n24q02m/web-core/pull/753),
  [`d87b916`](https://github.com/n24q02m/web-core/commit/d87b91668c95c24655ffc129739ece4eb9d64fc2))

### Chores

- **deps**: Bump the uv group across 1 directory with 2 updates
  ([#110](https://github.com/n24q02m/web-core/pull/110),
  [`b4d8dfe`](https://github.com/n24q02m/web-core/commit/b4d8dfe25532210a41f2bcfaa982f7e0350ed386))

### Features

- Add cross-OS CI matrix (ubuntu/windows/macos)
  ([`2ce1eed`](https://github.com/n24q02m/web-core/commit/2ce1eedb033660a7bd8aaeccad4394b73f870ecf))

- Migrate code review from Qodo to CodeRabbit ([#67](https://github.com/n24q02m/web-core/pull/67),
  [`f92129c`](https://github.com/n24q02m/web-core/commit/f92129cedfe4490bc9c68a19e6575b50f01fa8f4))

- **scraper**: Add structured domain usage logging for scraping analytics
  ([`4e98a70`](https://github.com/n24q02m/web-core/commit/4e98a7020cc570428699da9aa39afda83d2c21da))

### Performance Improvements

- **http**: Use list comprehension in _pinned_getaddrinfo
  ([#5](https://github.com/n24q02m/web-core/pull/5),
  [`06e8402`](https://github.com/n24q02m/web-core/commit/06e8402a9b1db2e2a38dc4466f6e8c3d2cf25bf9))

- **scraper**: Pre-compile wildcard regular expressions
  ([#108](https://github.com/n24q02m/web-core/pull/108),
  [`854d8d6`](https://github.com/n24q02m/web-core/commit/854d8d6bfaaec6fe1f307eb77d621d4cb57bdfef))

### Refactoring

- **search**: Use O(1) set operations for deduplication
  ([#107](https://github.com/n24q02m/web-core/pull/107),
  [`2636865`](https://github.com/n24q02m/web-core/commit/263686536036bf8a17b9416dacf44bf99fc607dc))


## v1.1.1-beta.7 (2026-04-06)

### Bug Fixes

- Use Python page.query_selector_all for Turnstile sitekey extraction
  ([`d330cf2`](https://github.com/n24q02m/web-core/commit/d330cf2553ae93a403939068da7485877cb584b1))


## v1.1.1-beta.6 (2026-04-06)

### Bug Fixes

- Extract Turnstile sitekey from CF iframe src (render=explicit)
  ([`f78ac59`](https://github.com/n24q02m/web-core/commit/f78ac59d51072074f56f85b1d08f15356d1c6cf3))


## v1.1.1-beta.5 (2026-04-06)

### Bug Fixes

- Apply ruff format to captcha and tls_spoof strategies
  ([`a46e0af`](https://github.com/n24q02m/web-core/commit/a46e0af7ea29d1b0e24c63eaba37e7bb9130df17))


## v1.1.1-beta.4 (2026-04-06)

### Bug Fixes

- CaptchaStrategy uses Patchright+CapSolver for CF Turnstile bypass
  ([`7aa79f0`](https://github.com/n24q02m/web-core/commit/7aa79f065945d21973823e95f663389848ab5fd5))


## v1.1.1-beta.3 (2026-04-06)

### Bug Fixes

- Restore gdown>=5.2.0 dependency lost during conflict resolution
  ([`d4c3240`](https://github.com/n24q02m/web-core/commit/d4c32402cb17dccaabaa39c66b0a5df1211f5dde))


## v1.1.1-beta.2 (2026-04-06)

### Bug Fixes

- Pass cookies from selectors to BasicHTTPStrategy and TLSSpoofStrategy
  ([`1286a10`](https://github.com/n24q02m/web-core/commit/1286a101d675fd7a47263ef26531eabe1f6da40d))


## v1.1.1-beta.1 (2026-04-06)

### Bug Fixes

- Add separate rate limit for at-home/server endpoint (0.5 RPS)
  ([`3e5ad06`](https://github.com/n24q02m/web-core/commit/3e5ad0637f427b53ad6e7e83a7e65f4512352f3b))


## v1.1.0 (2026-04-06)

### Bug Fixes

- Add brand section to SearXNG settings template
  ([`68c9881`](https://github.com/n24q02m/web-core/commit/68c98810e4dffd157f99959331b2f6d2c2bc0ed2))

- Apply ruff format to google_drive.py
  ([`9f4c16b`](https://github.com/n24q02m/web-core/commit/9f4c16bc41ccc4775bc9e74f08045ed7fe03bbec))

- Exclude google_drive adapter from coverage (requires real OAuth)
  ([`3d65ce4`](https://github.com/n24q02m/web-core/commit/3d65ce458acc507b0d2483f6b68056c347094afe))

- Resolve pre-existing ruff lint issues in patchright tests
  ([`66aa901`](https://github.com/n24q02m/web-core/commit/66aa9010df96f08ffe9b31b55b6bed35b4d4a196))

- Sync uv.lock after brand section fix
  ([`2229bb2`](https://github.com/n24q02m/web-core/commit/2229bb2387ff3e9927548435b7d970901d89370b))


## v1.1.0-beta.5 (2026-04-06)

### Bug Fixes

- Use gdown skip_download=True for efficient folder listing
  ([`e3d11a2`](https://github.com/n24q02m/web-core/commit/e3d11a29ceab488d6991c7422e15055406f7ec2c))


## v1.1.0-beta.4 (2026-04-06)

### Bug Fixes

- Clean up google_drive adapter ruff issues
  ([`058106e`](https://github.com/n24q02m/web-core/commit/058106e0ad223d3afc1e015decb5d7591c7690bc))


## v1.1.0-beta.3 (2026-04-06)

### Features

- Add Google Drive public folder adapter
  ([`069fe25`](https://github.com/n24q02m/web-core/commit/069fe2501f71efc5cfa91ad62fdc6ece6844e30d))


## v1.1.0-beta.2 (2026-04-06)

### Bug Fixes

- Add Newtoki-style CF managed challenge patterns and improve polling
  ([`630fd22`](https://github.com/n24q02m/web-core/commit/630fd22e7871826f16463917187f4b2faced11a0))

- Apply ruff format to test_headless.py
  ([`5564944`](https://github.com/n24q02m/web-core/commit/5564944427a30ceaec763ed593ca02bea8d96394))

### Features

- Cloudflare challenge detection, Turnstile solving, and improved escalation
  ([`4a2c1c8`](https://github.com/n24q02m/web-core/commit/4a2c1c8988ddb9a23f16ce250692547c8c4b0099))


## v1.1.0-beta.1 (2026-04-05)

### Features

- Add stealth scraping, PatchrightStrategy, and MangaDex API adapter
  ([`682e460`](https://github.com/n24q02m/web-core/commit/682e460b955291849c72814f3e5f34ebe1bd0655))

- Notify downstream repos on stable release ([#24](https://github.com/n24q02m/web-core/pull/24),
  [`69668c6`](https://github.com/n24q02m/web-core/commit/69668c6fa35f268aa4c99bc7bfdee574b1f8f2d6))


## v1.0.1 (2026-03-31)

### Bug Fixes

- Rename package to n24q02m-web-core for PyPI publishing
  ([`e6cd3f7`](https://github.com/n24q02m/web-core/commit/e6cd3f7a4c6916b88b6bbabdf124840eaae1f538))


## v1.0.0 (2026-03-31)

- Initial Release
