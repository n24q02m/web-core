# CHANGELOG

<!-- version list -->

## v2.1.1 (2026-05-28)

### Bug Fixes

- **deps**: Lock file maintenance ([#284](https://github.com/n24q02m/web-core/pull/284),
  [`ce38db3`](https://github.com/n24q02m/web-core/commit/ce38db34c4b3907fc7ef0507a663c05b96346981))

- **deps**: Update non-major dependencies ([#283](https://github.com/n24q02m/web-core/pull/283),
  [`ccdb094`](https://github.com/n24q02m/web-core/commit/ccdb0947e2ff1d3dd573916926fdd3fdbef154b2))

### Performance Improvements

- Use connection pooling for robots.txt fetching
  ([#285](https://github.com/n24q02m/web-core/pull/285),
  [`5060c5f`](https://github.com/n24q02m/web-core/commit/5060c5f406dee1c5be5b2c1f83ea8c92721d2dfa))


## v2.1.0 (2026-05-26)


## v2.1.0-beta.3 (2026-05-26)

### Bug Fixes

- **deps**: Lock file maintenance ([#281](https://github.com/n24q02m/web-core/pull/281),
  [`f501856`](https://github.com/n24q02m/web-core/commit/f501856ea416e770af02e19bca77b98c409b5954))


## v2.1.0-beta.2 (2026-05-24)

### Bug Fixes

- **deps**: Lock file maintenance ([#280](https://github.com/n24q02m/web-core/pull/280),
  [`59366d9`](https://github.com/n24q02m/web-core/commit/59366d9dbda92a8738a3a32e9f69d97abe06b719))

- **deps**: Update step-security/harden-runner digest to ab7a940
  ([#279](https://github.com/n24q02m/web-core/pull/279),
  [`389b03d`](https://github.com/n24q02m/web-core/commit/389b03d6ef3110d21680d51253f8fdeaf9d0fde3))


## v2.1.0-beta.1 (2026-05-24)

### Bug Fixes

- **deps**: Bump idna from 3.13 to 3.15 ([#271](https://github.com/n24q02m/web-core/pull/271),
  [`bccf938`](https://github.com/n24q02m/web-core/commit/bccf938529962cbba70c79d4c1a9586a4682f9a2))

- **deps**: Lock file maintenance ([#278](https://github.com/n24q02m/web-core/pull/278),
  [`b3f000d`](https://github.com/n24q02m/web-core/commit/b3f000dce05653e8b8f6eaf4936ad17bb054d485))

- **deps**: Refresh uv lock file maintenance ([#251](https://github.com/n24q02m/web-core/pull/251),
  [`c62998f`](https://github.com/n24q02m/web-core/commit/c62998f680755be475f9ef003d583aefbe62b42f))

- **deps**: Update actions/create-github-app-token digest to bcd2ba4
  ([#259](https://github.com/n24q02m/web-core/pull/259),
  [`1bbe4c9`](https://github.com/n24q02m/web-core/commit/1bbe4c93a8c4880f83a34e7a840ce7a90a358c80))

- **deps**: Update codecov/codecov-action digest to e79a696
  ([#274](https://github.com/n24q02m/web-core/pull/274),
  [`a571034`](https://github.com/n24q02m/web-core/commit/a571034500457dde3b3cc1706d467e780c1a54ba))

- **deps**: Update ghcr.io/astral-sh/uv:latest Docker digest to 440fd64
  ([#275](https://github.com/n24q02m/web-core/pull/275),
  [`d6cfd37`](https://github.com/n24q02m/web-core/commit/d6cfd379b37cca8d17d5e71dad70730445d6f233))

- **deps**: Update ghcr.io/astral-sh/uv:latest Docker digest to e590846
  ([#255](https://github.com/n24q02m/web-core/pull/255),
  [`8c187de`](https://github.com/n24q02m/web-core/commit/8c187debc1c80b7932c00751b6bbbe0eda5d0ea0))

- **deps**: Update github/codeql-action digest to 7211b7c
  ([#276](https://github.com/n24q02m/web-core/pull/276),
  [`adaeb21`](https://github.com/n24q02m/web-core/commit/adaeb21688507ee2f8bb22f5319d86a34ec1d29c))

- **deps**: Update non-major dependencies ([#277](https://github.com/n24q02m/web-core/pull/277),
  [`52f48cd`](https://github.com/n24q02m/web-core/commit/52f48cd7b5b8356d68ee9f6dc91e4a8491934666))

- **deps**: Update non-major dependencies ([#253](https://github.com/n24q02m/web-core/pull/253),
  [`50d19cc`](https://github.com/n24q02m/web-core/commit/50d19cc36aac1c3cd9800f92e3ac8ee080a88859))

- **deps**: Update python:3.13-slim-bookworm Docker digest
  ([#250](https://github.com/n24q02m/web-core/pull/250),
  [`d357a3e`](https://github.com/n24q02m/web-core/commit/d357a3e40d88978eee09b56cf0a75e5b6965515e))

- **security**: Block SSRF via curl_cffi redirects in TLSSpoofStrategy
  ([#273](https://github.com/n24q02m/web-core/pull/273),
  [`9fae899`](https://github.com/n24q02m/web-core/commit/9fae899282e7a6955b8f2618901b1b115ba64f8e))

- **security**: Prevent SSRF bypass in curl-cffi by disabling auto-redirects
  ([#273](https://github.com/n24q02m/web-core/pull/273),
  [`9fae899`](https://github.com/n24q02m/web-core/commit/9fae899282e7a6955b8f2618901b1b115ba64f8e))

- **tests**: Resolve ruff SIM117 linting error in test_tls_spoof.py
  ([#273](https://github.com/n24q02m/web-core/pull/273),
  [`9fae899`](https://github.com/n24q02m/web-core/commit/9fae899282e7a6955b8f2618901b1b115ba64f8e))

### Code Style

- Run ruff format on tests/test_scraper/test_strategies/test_tls_spoof.py
  ([#273](https://github.com/n24q02m/web-core/pull/273),
  [`9fae899`](https://github.com/n24q02m/web-core/commit/9fae899282e7a6955b8f2618901b1b115ba64f8e))

### Features

- **mangadex**: Reuse HTTP connections via async context manager
  ([#267](https://github.com/n24q02m/web-core/pull/267),
  [`0d61bb2`](https://github.com/n24q02m/web-core/commit/0d61bb2610c32972cf92f0fc5bcd6fb9a47109d3))


## v2.0.1 (2026-05-09)


## v2.0.1-beta.1 (2026-05-09)

### Bug Fixes

- **deps**: Drop pydantic <2.13 cap; move cap to wet-mcp where cohere lives
  ([`aa51e70`](https://github.com/n24q02m/web-core/commit/aa51e70e1c3b75d4c3512371deacb9b4a6eabb51))


## v2.0.0 (2026-05-09)


## v2.0.0-beta.1 (2026-05-09)

### Bug Fixes

- Combine nested with statements in test_client.py for SIM117 ruff check
  ([`72d39e7`](https://github.com/n24q02m/web-core/commit/72d39e7fe550c4c6fef55d774abaca20a600d2c8))

- Dedupe domains via set+early break in _build_filtered_query
  ([`1a5e260`](https://github.com/n24q02m/web-core/commit/1a5e260b55b8c640755da3271808c2a6c40baa23))

- Parallelize async chapter fetching in google_drive adapter
  ([`23f60c5`](https://github.com/n24q02m/web-core/commit/23f60c5027ccc04070fc0310e49cf3f9f17b644c))

- Parallelize sequential pagination I/O in mangadex adapter
  ([`b1e8d9c`](https://github.com/n24q02m/web-core/commit/b1e8d9c78ddf9a54856613fb915113c4371a4dd8))

- Remove bot rewrite artifact ([#243](https://github.com/n24q02m/web-core/pull/243),
  [`fc976fd`](https://github.com/n24q02m/web-core/commit/fc976fdd3b30f7d0cb8acd9f275a81f362b48178))

- Remove site-specific selectors (Plan A Task 2)
  ([`67d9cd1`](https://github.com/n24q02m/web-core/commit/67d9cd1af1a11d05d9dd5eb2f8504079c71aa9e8))

- Remove tracked bot memory files (per .gitignore policy)
  ([`b92fe12`](https://github.com/n24q02m/web-core/commit/b92fe12b50d15b0dbd939376b6e9e5a64153d771))

- Replace bare except Exception with TimeoutError + debug log in patchright
  ([`51fe2e7`](https://github.com/n24q02m/web-core/commit/51fe2e71a0f04025e7c6ad52b15e8af6abe8e8c9))

- Sanitize exception logging via type(exc).__name__ to prevent info leak
  ([`f4b3dab`](https://github.com/n24q02m/web-core/commit/f4b3dab25fafcce728e4b44975732216b68549ba))

- Validate _read_discovery file perms + types in runner
  ([`da831a2`](https://github.com/n24q02m/web-core/commit/da831a2b67bbadc11457bdf49a822477c4d5823c))

- **deps**: Bump non-major dependencies
  ([`ba0adc8`](https://github.com/n24q02m/web-core/commit/ba0adc8d72a5c2339c545b969a0375c4c2c85001))

- **deps**: Lock file maintenance ([#247](https://github.com/n24q02m/web-core/pull/247),
  [`7cb9fe9`](https://github.com/n24q02m/web-core/commit/7cb9fe9be346c41baaca8b688f12c49c43109f86))

- **deps**: Refresh uv.lock maintenance
  ([`5650332`](https://github.com/n24q02m/web-core/commit/5650332980fdf1e527883a5e49a5a66d444f72cc))

- **deps**: Update actions/dependency-review-action action to v5
  ([#248](https://github.com/n24q02m/web-core/pull/248),
  [`668fa2b`](https://github.com/n24q02m/web-core/commit/668fa2b9786c250067c9a5da689c7433128fd21c))

- **deps**: Update ghcr.io/astral-sh/uv:latest Docker digest to 3a59a3c
  ([#245](https://github.com/n24q02m/web-core/pull/245),
  [`3406b1d`](https://github.com/n24q02m/web-core/commit/3406b1df606cdeb034925e1721f9d0179aa5f547))

- **deps**: Update github/codeql-action digest to 68bde55
  ([#246](https://github.com/n24q02m/web-core/pull/246),
  [`834d0a1`](https://github.com/n24q02m/web-core/commit/834d0a133b055c62f6af5f3dc764cefb1b836b73))

- **search**: Address lint and secret detection CI failures
  ([`da831a2`](https://github.com/n24q02m/web-core/commit/da831a2b67bbadc11457bdf49a822477c4d5823c))

- **search**: Ensure windows compatibility for secure subprocess runner
  ([`da831a2`](https://github.com/n24q02m/web-core/commit/da831a2b67bbadc11457bdf49a822477c4d5823c))

- **search**: Harden subprocess execution and discovery file security
  ([`da831a2`](https://github.com/n24q02m/web-core/commit/da831a2b67bbadc11457bdf49a822477c4d5823c))

- **search**: Harden subprocess runner and fix windows ci failures
  ([`da831a2`](https://github.com/n24q02m/web-core/commit/da831a2b67bbadc11457bdf49a822477c4d5823c))

- **search**: Sanitize placeholders and split hashes to bypass secret detection
  ([`da831a2`](https://github.com/n24q02m/web-core/commit/da831a2b67bbadc11457bdf49a822477c4d5823c))

- **search**: Sanitize placeholders to satisfy secret detection
  ([`da831a2`](https://github.com/n24q02m/web-core/commit/da831a2b67bbadc11457bdf49a822477c4d5823c))

### Features

- Add edge case tests for _apply_domain_cap
  ([`78072a4`](https://github.com/n24q02m/web-core/commit/78072a4c473362870aa67ca1d84e04b652358e37))

- Add edge case tests for Google Drive folder ID extraction
  ([`04667f3`](https://github.com/n24q02m/web-core/commit/04667f3ba6980e8c56fc5f7c880ef1f3ff62a31a))

- Add error path test for _pinned_getaddrinfo
  ([`526c33a`](https://github.com/n24q02m/web-core/commit/526c33abe3a995d309887655918304423baabcaa))

- Add Table of contents heading + auto-generated link list (Spec E Wave 2)
  ([`c3d4231`](https://github.com/n24q02m/web-core/commit/c3d42313830b591d14b8507cb51dc2374ae27924))

- Add tests for Cloudflare resolution wait in patchright strategy
  ([`c8ee31c`](https://github.com/n24q02m/web-core/commit/c8ee31c8b5ba8b09ac6d19f81f39f6826676f939))

- Retrofit Tier 1 governance files via repo-bootstrap apply (Spec E Wave 4)
  ([`0979c94`](https://github.com/n24q02m/web-core/commit/0979c9408c9b47c9b9b3dd49b486a9e7d9cf2ad9))

- Scope refinement — remove site-specific selectors
  ([`82b8f40`](https://github.com/n24q02m/web-core/commit/82b8f402a8f683356bb8b3529ee99aca8b7d1ee8))

- Sync cross-promo section ([#242](https://github.com/n24q02m/web-core/pull/242),
  [`ee65e92`](https://github.com/n24q02m/web-core/commit/ee65e92f95f80e15c8460cdf02e2907ab652b8e8))

### Performance Improvements

- **google-drive**: Parallelize chapter downloads with TaskGroup
  ([`23f60c5`](https://github.com/n24q02m/web-core/commit/23f60c5027ccc04070fc0310e49cf3f9f17b644c))

- **scraper**: Batch Turnstile sitekey extraction to reduce IPC latency
  ([#249](https://github.com/n24q02m/web-core/pull/249),
  [`9b0106d`](https://github.com/n24q02m/web-core/commit/9b0106d033563783e4744f73b009b326ffc197d4))

### Refactoring

- Optimize domain extraction in selector inference
  ([#243](https://github.com/n24q02m/web-core/pull/243),
  [`fc976fd`](https://github.com/n24q02m/web-core/commit/fc976fdd3b30f7d0cb8acd9f275a81f362b48178))

### Breaking Changes

- Site-specific domain selectors (Newtoki, Syosetu R-18) and their wildcard configs are removed from
  web-core's built-in DOMAIN_CONFIGS. These were experimental scope creep — site-specific behaviors
  (which authority owns the content, what cookies to send, age-gate flows) belong in the consuming
  application, not in shared infrastructure.


## v1.3.12 (2026-05-06)


## v1.3.12-beta.1 (2026-05-06)

### Chores

- **deps**: Lock file maintenance ([#214](https://github.com/n24q02m/web-core/pull/214),
  [`fe6400d`](https://github.com/n24q02m/web-core/commit/fe6400d18ed732fcbef12803f5c7e43142b2cd84))

- **deps**: Update step-security/harden-runner digest to a5ad31d
  ([#212](https://github.com/n24q02m/web-core/pull/212),
  [`ef14310`](https://github.com/n24q02m/web-core/commit/ef143109ff2d92bdb252b8dc0e4cc49c5bdb34b4))

### Performance Improvements

- Parallelize google drive chapter downloads ([#222](https://github.com/n24q02m/web-core/pull/222),
  [`cb467da`](https://github.com/n24q02m/web-core/commit/cb467da9f2e2b766df6de0ccd806366bf4d3e66f))


## v1.3.11 (2026-05-05)

### Bug Fixes

- Add use_default_settings to subprocess SearXNG template
  ([#221](https://github.com/n24q02m/web-core/pull/221),
  [`2812387`](https://github.com/n24q02m/web-core/commit/28123872d5fdd4f2ec4c8cc858264ac2088d5828))

- Disable SearXNG limiter + enable JSON in subprocess template
  ([#221](https://github.com/n24q02m/web-core/pull/221),
  [`2812387`](https://github.com/n24q02m/web-core/commit/28123872d5fdd4f2ec4c8cc858264ac2088d5828))


## v1.3.10 (2026-05-05)


## v1.3.10-beta.2 (2026-05-05)

### Bug Fixes

- Add use_default_settings to subprocess SearXNG template
  ([#220](https://github.com/n24q02m/web-core/pull/220),
  [`f65d58b`](https://github.com/n24q02m/web-core/commit/f65d58b7c8289e907655a4b5749cf953e25f754b))

### Chores

- **deps**: Lock file maintenance ([#205](https://github.com/n24q02m/web-core/pull/205),
  [`4e1dc0f`](https://github.com/n24q02m/web-core/commit/4e1dc0fc88d33f3ceb2a898fe49bed49fbc7dda7))

- **deps**: Update github/codeql-action digest to e46ed2c
  ([#210](https://github.com/n24q02m/web-core/pull/210),
  [`910a833`](https://github.com/n24q02m/web-core/commit/910a8335a015c1dc888ad44b99bca13d0ef2646d))

### Performance Improvements

- **scraper**: Avoid string allocation in captcha sitekey extraction
  ([#207](https://github.com/n24q02m/web-core/pull/207),
  [`fd27ab7`](https://github.com/n24q02m/web-core/commit/fd27ab790a6a7c033af68a1320e281bd4e53da40))


## v1.3.10-beta.1 (2026-04-30)

### Bug Fixes

- Patch shutil.which in searxng lock tests for CI without Docker
  ([#208](https://github.com/n24q02m/web-core/pull/208),
  [`f6b2b4a`](https://github.com/n24q02m/web-core/commit/f6b2b4a135eb9f96d18138d4d1fdd466dd9f5988))

- **search**: Pin searxng port + filelock to prevent container leak
  ([#208](https://github.com/n24q02m/web-core/pull/208),
  [`f6b2b4a`](https://github.com/n24q02m/web-core/commit/f6b2b4a135eb9f96d18138d4d1fdd466dd9f5988))


## v1.3.9 (2026-04-29)

### Bug Fixes

- Pin Python to ==3.13.* for pin parity (D13) ([#203](https://github.com/n24q02m/web-core/pull/203),
  [`2b5903f`](https://github.com/n24q02m/web-core/commit/2b5903fb51c6c928b673cc1c690206be10973e07))

- **deps**: Lock file maintenance ([#202](https://github.com/n24q02m/web-core/pull/202),
  [`494338f`](https://github.com/n24q02m/web-core/commit/494338f6534e4589ec1fa2fa46cbc51054d78ee5))

- **deps**: Update dawidd6/action-send-mail action to v17
  ([#201](https://github.com/n24q02m/web-core/pull/201),
  [`c19832f`](https://github.com/n24q02m/web-core/commit/c19832f8571d0b87bcc12e4572f116e0be32d768))

- **deps**: Update non-major dependencies ([#200](https://github.com/n24q02m/web-core/pull/200),
  [`6df620c`](https://github.com/n24q02m/web-core/commit/6df620ca58efe3a84123ddd383ebede18a17843a))


## v1.3.8 (2026-04-28)

### Bug Fixes

- Pin pydantic <2.13 for cohere consumer compatibility
  ([#199](https://github.com/n24q02m/web-core/pull/199),
  [`8429e11`](https://github.com/n24q02m/web-core/commit/8429e11e1e2522b29aff9b0f6ddee52080c5a26a))

- **deps**: Update dependency langgraph to >=1.1.10
  ([#195](https://github.com/n24q02m/web-core/pull/195),
  [`55e64ad`](https://github.com/n24q02m/web-core/commit/55e64adecdd414c9b766281c7bb63037f1c0c618))

### Chores

- **deps**: Lock file maintenance ([#196](https://github.com/n24q02m/web-core/pull/196),
  [`87d2d57`](https://github.com/n24q02m/web-core/commit/87d2d57ef3697ba856c2806b7bfbe284e76ee9f3))

### Performance Improvements

- **scraper**: Optimize Turnstile sitekey extraction fast-path
  ([#197](https://github.com/n24q02m/web-core/pull/197),
  [`b9dcb2d`](https://github.com/n24q02m/web-core/commit/b9dcb2dac9641a577e1130a17d6a8feea00a1263))


## v1.3.7 (2026-04-27)

### Bug Fixes

- Collapse nested if statements in SearXNG runner (SIM102)
  ([`554934c`](https://github.com/n24q02m/web-core/commit/554934c2bb5927e2e4439662d4307d9de863f739))

- Sweep doppler/infisical refs to skret SSM
  ([`249ec29`](https://github.com/n24q02m/web-core/commit/249ec29a0b558283c2a08f0885465263975ddab4))

- **deps**: Update non-major dependencies ([#193](https://github.com/n24q02m/web-core/pull/193),
  [`fc428f7`](https://github.com/n24q02m/web-core/commit/fc428f77fa74eed6f2219e82a30f39ccebb452af))

### Chores

- **deps**: Lock file maintenance ([#194](https://github.com/n24q02m/web-core/pull/194),
  [`0c77c91`](https://github.com/n24q02m/web-core/commit/0c77c916e866af1198d7b413351dfdf3a9f09139))

- **deps**: Lock file maintenance ([#191](https://github.com/n24q02m/web-core/pull/191),
  [`d6b65be`](https://github.com/n24q02m/web-core/commit/d6b65be7c4433e091d1e58ed8555e8a7fca22986))


## v1.3.6 (2026-04-24)

### Bug Fixes

- Block CGNAT (100.64.0.0/10) + unspecified (0.0.0.0) IPs in SSRF guard
  ([`1b25781`](https://github.com/n24q02m/web-core/commit/1b25781d7469209dd5335f70c5a20fd7bca59473))

- Loosen pydantic pin to accommodate cohere consumers
  ([`a39cd17`](https://github.com/n24q02m/web-core/commit/a39cd177423ed7594e15c9f0a03885c2efa73226))

- **deps**: Update non-major dependencies ([#188](https://github.com/n24q02m/web-core/pull/188),
  [`4ad88a0`](https://github.com/n24q02m/web-core/commit/4ad88a0c2907e238b356119e4586f988ac56f716))

### Chores

- **deps**: Lock file maintenance ([#189](https://github.com/n24q02m/web-core/pull/189),
  [`1af9150`](https://github.com/n24q02m/web-core/commit/1af9150f6ef74b9eb1b6cd70f376261371ef6255))


## v1.3.5 (2026-04-22)

### Bug Fixes

- Stdin=DEVNULL + fast-path for docker inspect in SearXNG runner
  ([`9181358`](https://github.com/n24q02m/web-core/commit/91813582a16d02619a322dbacb6eae54102486d6))


## v1.3.4 (2026-04-22)

### Bug Fixes

- Pass stdin=DEVNULL to docker subprocess calls
  ([`d4347d9`](https://github.com/n24q02m/web-core/commit/d4347d9aab142adf39e71565e000bb9ca0c08750))


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

- Add Site Redacted-style CF managed challenge patterns and improve polling
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
