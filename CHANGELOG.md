# CHANGELOG

<!-- version list -->

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
