# CHANGELOG

<!-- version list -->

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
