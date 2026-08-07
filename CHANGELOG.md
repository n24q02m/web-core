# CHANGELOG

<!-- version list -->

## v2.4.0-beta.1 (2026-08-07)

### Bug Fixes

- Adopt better-semantic-release for built-in release guards
  ([`b4f65ea`](https://github.com/n24q02m/web-core/commit/b4f65ea92548678a94636ad22afcd7a3824d6315))

- Cache IP safety checks in SSRF validation
  ([`3214ccd`](https://github.com/n24q02m/web-core/commit/3214ccd4d76e409ab4b71ee85052a552ec4e6e5d))

- Convert SSRF allow_private iterable to frozenset
  ([`1e1d910`](https://github.com/n24q02m/web-core/commit/1e1d910f9f8a2f4e7733223240fdf8fe511eab78))

- Correct mention gate expression (balanced parens + precedence)
  ([#634](https://github.com/n24q02m/web-core/pull/634),
  [`a056719`](https://github.com/n24q02m/web-core/commit/a0567191e7712f202d700a4de973567d128eac19))

- Correct renovate commit message casing and semantic type
  ([#676](https://github.com/n24q02m/web-core/pull/676),
  [`43ca5d9`](https://github.com/n24q02m/web-core/commit/43ca5d99a723191d5640549a175fe510a09f379c))

- Drop rangeStrategy from update-type package rules
  ([#646](https://github.com/n24q02m/web-core/pull/646),
  [`a943e83`](https://github.com/n24q02m/web-core/commit/a943e83e05e076469f4524809523ad035555fc26))

- Escape CR/LF in log values from queries and subprocess output
  ([#670](https://github.com/n24q02m/web-core/pull/670),
  [`b1233f1`](https://github.com/n24q02m/web-core/commit/b1233f19a4807cdd4adf52a95b180716a4243e6b))

- Fail the release when the computed version already exists on the registry
  ([#624](https://github.com/n24q02m/web-core/pull/624),
  [`e061b02`](https://github.com/n24q02m/web-core/commit/e061b028b6c060a49618f4ac358d063b0800770a))

- Gate oc mention job on comment author write access
  ([#634](https://github.com/n24q02m/web-core/pull/634),
  [`a056719`](https://github.com/n24q02m/web-core/commit/a0567191e7712f202d700a4de973567d128eac19))

- Make renovate automerge effective (isolated groups, digest+lockfile automerge, 7-day cooldown)
  ([`449f6b0`](https://github.com/n24q02m/web-core/commit/449f6b01464e8cfd0846f0292ea98346d073c3e7))

- Move this repo to Apache-2.0 ([#659](https://github.com/n24q02m/web-core/pull/659),
  [`b712434`](https://github.com/n24q02m/web-core/commit/b7124348f6a61bd9e9f02c3e1eb66d12e2741f9d))

- Pin GitHub Action references to commit SHAs ([#644](https://github.com/n24q02m/web-core/pull/644),
  [`28df56e`](https://github.com/n24q02m/web-core/commit/28df56e29b1636fa0a83526c424e44ad03ffc26e))

- Pin rangeStrategy on delayed packageRules to fix renovate artifacts failure
  ([#641](https://github.com/n24q02m/web-core/pull/641),
  [`1b47d4f`](https://github.com/n24q02m/web-core/commit/1b47d4fb42432b68a58e356e4a1a18e1d28cdf88))

- Re-trigger pr-title check now that PR title is conventional again
  ([#643](https://github.com/n24q02m/web-core/pull/643),
  [`ca55f24`](https://github.com/n24q02m/web-core/commit/ca55f24f72706f82532492782fb96d4d2fe72c42))

- Run opencode bot on hosted runners ([#633](https://github.com/n24q02m/web-core/pull/633),
  [`87b9ae9`](https://github.com/n24q02m/web-core/commit/87b9ae97af983a7ee2af6c39638926c0e3c270ab))

- Trigger synchronize to verify pr-title reject path
  ([#643](https://github.com/n24q02m/web-core/pull/643),
  [`ca55f24`](https://github.com/n24q02m/web-core/commit/ca55f24f72706f82532492782fb96d4d2fe72c42))

- **deps**: Bump aiohttp from 3.14.1 to 3.14.3 in the uv group
  ([`f13abee`](https://github.com/n24q02m/web-core/commit/f13abeeca7a69dbfe630200e23fff930fbb67824))

- **deps**: Bump the uv group across 1 directory with 2 updates
  ([#669](https://github.com/n24q02m/web-core/pull/669),
  [`625ae31`](https://github.com/n24q02m/web-core/commit/625ae31038d2b2f422cb22344f99fef368469ff8))

- **deps**: Lock file maintenance ([#678](https://github.com/n24q02m/web-core/pull/678),
  [`628cbdd`](https://github.com/n24q02m/web-core/commit/628cbddbc07fdc398ff7af9254747b1173ceab67))

- **deps**: Lock file maintenance ([#677](https://github.com/n24q02m/web-core/pull/677),
  [`92e2050`](https://github.com/n24q02m/web-core/commit/92e205007896319f49f7b81435c48f769673b67a))

- **deps**: Lock file maintenance ([#675](https://github.com/n24q02m/web-core/pull/675),
  [`9c6b9e1`](https://github.com/n24q02m/web-core/commit/9c6b9e16da4599ed41088e9ac799618553618879))

- **deps**: Lock file maintenance ([#674](https://github.com/n24q02m/web-core/pull/674),
  [`941e631`](https://github.com/n24q02m/web-core/commit/941e6316f05aa352b7c74a70e843f4b5814d3f46))

- **deps**: Lock file maintenance ([#640](https://github.com/n24q02m/web-core/pull/640),
  [`e65c48c`](https://github.com/n24q02m/web-core/commit/e65c48c17384efabb4a7f15962c65692371da1ec))

- **deps**: Lock file maintenance ([#639](https://github.com/n24q02m/web-core/pull/639),
  [`b544eec`](https://github.com/n24q02m/web-core/commit/b544eec774b66c51d9caf56a8c9c7c5ea73a738e))

- **deps**: Lock file maintenance ([#637](https://github.com/n24q02m/web-core/pull/637),
  [`6571c03`](https://github.com/n24q02m/web-core/commit/6571c03cc6c02b1f4ed29e5bdcc69ebb17ed1936))

- **deps**: Lock file maintenance ([#632](https://github.com/n24q02m/web-core/pull/632),
  [`6ac9584`](https://github.com/n24q02m/web-core/commit/6ac9584aebc574d2b4fe2ea0783c99e4f6055743))

- **deps**: Lock file maintenance ([#630](https://github.com/n24q02m/web-core/pull/630),
  [`433018b`](https://github.com/n24q02m/web-core/commit/433018b2fd48f8fb0972623ff517d2cff55bc7ab))

- **deps**: Lock file maintenance ([#615](https://github.com/n24q02m/web-core/pull/615),
  [`1ab227d`](https://github.com/n24q02m/web-core/commit/1ab227d066af09e105568c07d041dd6330586088))

- **deps**: Update actions/checkout action to v7
  ([#628](https://github.com/n24q02m/web-core/pull/628),
  [`822af15`](https://github.com/n24q02m/web-core/commit/822af157ad7d8351bb290a1a9fb868d58f0a7810))

- **deps**: Update actions/setup-python action to v7
  ([#648](https://github.com/n24q02m/web-core/pull/648),
  [`b415b5e`](https://github.com/n24q02m/web-core/commit/b415b5e3f283cb2e69d48699c095d0d8060e5df8))

- **deps**: Update astral-sh/setup-uv action to v8.3.2
  ([#627](https://github.com/n24q02m/web-core/pull/627),
  [`e8f97d9`](https://github.com/n24q02m/web-core/commit/e8f97d98ea9495a2cb716ffb655397de76bcb0e6))

- **deps**: Update astral-sh/setup-uv action to v9
  ([#673](https://github.com/n24q02m/web-core/pull/673),
  [`de32930`](https://github.com/n24q02m/web-core/commit/de32930991285fb5b12e3b1f20bee7605c63bb67))

- **deps**: Update ghcr.io/astral-sh/uv:latest Docker digest to 069a513
  ([#638](https://github.com/n24q02m/web-core/pull/638),
  [`4e4774d`](https://github.com/n24q02m/web-core/commit/4e4774d89ff7d4d45280ad8432539863e33aea9f))

- **deps**: Update ghcr.io/astral-sh/uv:latest Docker digest to 0f36cb9
  ([#619](https://github.com/n24q02m/web-core/pull/619),
  [`07df8d1`](https://github.com/n24q02m/web-core/commit/07df8d188bb32e1b2eac0932eedce1dca9d98014))

- **deps**: Update ghcr.io/astral-sh/uv:latest Docker digest to 2d89062
  ([#672](https://github.com/n24q02m/web-core/pull/672),
  [`39de394`](https://github.com/n24q02m/web-core/commit/39de3940731882802cb90697ffaeecff9a7de5ff))

- **deps**: Update minor dependencies ([#647](https://github.com/n24q02m/web-core/pull/647),
  [`8c92aec`](https://github.com/n24q02m/web-core/commit/8c92aec40deb2fd00e76877de32ce9b9ae3909b8))

- **deps**: Update patch dependencies ([#636](https://github.com/n24q02m/web-core/pull/636),
  [`e9291b7`](https://github.com/n24q02m/web-core/commit/e9291b77c56260545de01930dacbf4aa3d7682a0))

- **deps**: Update patchright to >=1.61.2 ([#631](https://github.com/n24q02m/web-core/pull/631),
  [`117c3db`](https://github.com/n24q02m/web-core/commit/117c3db9e70ac4a4116b156a55677c3ebaa6672a))

- **deps**: Update python:3.13-slim-bookworm Docker digest to 67a1e1f
  ([#635](https://github.com/n24q02m/web-core/pull/635),
  [`ac89482`](https://github.com/n24q02m/web-core/commit/ac89482de9cde0b2d4970bd77356d9db01a41bf4))

### Features

- Add bot PR governance to this repo ([#671](https://github.com/n24q02m/web-core/pull/671),
  [`0902ac8`](https://github.com/n24q02m/web-core/commit/0902ac8229f917b4f3af7d2869a3a5fbcc1066e3))

- Add opencode github agent (responds to /oc)
  ([`1a64b4f`](https://github.com/n24q02m/web-core/commit/1a64b4fb77b6992bbd0274c352f035288132be8e))

- Add PR-title conventional-commit gate + no-bump release warning
  ([#643](https://github.com/n24q02m/web-core/pull/643),
  [`ca55f24`](https://github.com/n24q02m/web-core/commit/ca55f24f72706f82532492782fb96d4d2fe72c42))

- Add review-learnings store the automated reviewer must obey
  ([`4a084dd`](https://github.com/n24q02m/web-core/commit/4a084dda05245773800814db40b69a9b08c0f9b8))

- Auto-respond only to issues and PRs opened by outside people
  ([`29f4f40`](https://github.com/n24q02m/web-core/commit/29f4f40327348e0cd01c99b8b98ed50375bbf720))

- Reviewer must obey .github/review-learnings.md
  ([`ebc3632`](https://github.com/n24q02m/web-core/commit/ebc36322f5768e08deca365ad26807b07fd977c6))

- Sync cross-promo section ([#652](https://github.com/n24q02m/web-core/pull/652),
  [`c0a1862`](https://github.com/n24q02m/web-core/commit/c0a1862a7337a49915fc24ace81e3d6aa60c88f1))


## v2.3.1 (2026-07-05)


## v2.3.1-beta.1 (2026-07-05)

### Bug Fixes

- Log exception detail via structured extra in selector inference
  ([`1db5665`](https://github.com/n24q02m/web-core/commit/1db5665eb35cc20c483447848c449242970f79a9))

- Use urlsplit instead of urlparse for faster URL parsing
  ([`2d0cfc8`](https://github.com/n24q02m/web-core/commit/2d0cfc8687631c75d702c9f3b8ceb68ea0a4f1e6))

- **deps**: Lock file maintenance ([#609](https://github.com/n24q02m/web-core/pull/609),
  [`ca46dae`](https://github.com/n24q02m/web-core/commit/ca46daedb27e3ecf8fef50c5dac03df48d91378f))

- **deps**: Update github/codeql-action digest to 54f647b
  ([#607](https://github.com/n24q02m/web-core/pull/607),
  [`6db5075`](https://github.com/n24q02m/web-core/commit/6db507516a2168f79f04b4835fc7c4bab0c6d044))

- **deps**: Update non-major dependencies ([#608](https://github.com/n24q02m/web-core/pull/608),
  [`9c786ed`](https://github.com/n24q02m/web-core/commit/9c786ed79d385bcdaea0874af7ff09283fe14ce6))

- **deps**: Update python-semantic-release/publish-action digest to 4f3c5d7
  ([#611](https://github.com/n24q02m/web-core/pull/611),
  [`da5fbc8`](https://github.com/n24q02m/web-core/commit/da5fbc81ceacb8710cc5e34e872110011bbb3638))

- **deps**: Update python-semantic-release/python-semantic-release digest to 37a30a7
  ([#612](https://github.com/n24q02m/web-core/pull/612),
  [`273a548`](https://github.com/n24q02m/web-core/commit/273a548bb83d91e543ff9a6e84b8d9654ecfac2a))


## v2.3.0 (2026-07-01)

### Bug Fixes

- [PERF] Inefficient append in get_manga loop
  ([`bc20dbf`](https://github.com/n24q02m/web-core/commit/bc20dbf7877a42f3d21bf935db55fb7120b6a24c))

- Add edge case tests for get_domain_selectors
  ([`a86cbc6`](https://github.com/n24q02m/web-core/commit/a86cbc669e155d2f6e74588142edfea581cbc9c6))

- Bolt: Use urlsplit for ~2x faster URL normalization
  ([`8cc1cce`](https://github.com/n24q02m/web-core/commit/8cc1cce19ee8c4019906dbc5a5b74d5f5cb11cbc))

- Cover _list_folder_via_html HTTP error
  ([`b49c0e4`](https://github.com/n24q02m/web-core/commit/b49c0e4fe85c09b9c097e9c982426d0f08091975))

- Cover patchright SSRF-blocked + CF timeout
  ([`ea620f9`](https://github.com/n24q02m/web-core/commit/ea620f9caa20a32920b90be104a7a609ba3a5aea))

- Deeply nested code in _is_pid_alive
  ([`fe08ba3`](https://github.com/n24q02m/web-core/commit/fe08ba3eef6223e9a0475b9633f4f775bf124981))

- F-string in logger
  ([`867c5fd`](https://github.com/n24q02m/web-core/commit/867c5fdb66dec4bfd6d328a56dfcd3637927ca4c))

- Fast-path JS-render check before regex parse
  ([`7d2bd9a`](https://github.com/n24q02m/web-core/commit/7d2bd9a4d9ff355af9b3e7f4ce17efccc26948d1))

- Fixtures
  ([`3fe6f74`](https://github.com/n24q02m/web-core/commit/3fe6f740ba719b61b8c2827aed6912b2f0c673b1))

- Guard _get_safe_domains limit<=0 off-by-one
  ([`c108d54`](https://github.com/n24q02m/web-core/commit/c108d54bfbc156c8a34dff8e00bd8ff1b779a4bf))

- Guard non-dict in _extract_cookies + cover
  ([`7ae3eab`](https://github.com/n24q02m/web-core/commit/7ae3eab6a2672929a29cef5ee68703c47b57ac68))

- Harden script/style tag stripping against whitespace end tags (CodeQL py/bad-tag-filter)
  ([#537](https://github.com/n24q02m/web-core/pull/537),
  [`5793b06`](https://github.com/n24q02m/web-core/commit/5793b06cdb2f20925d9a0440d12d6f63637c94e4))

- Lock file maintenance
  ([`37d8db3`](https://github.com/n24q02m/web-core/commit/37d8db3a4c699af6424d40d7a4a400ffc57b8585))

- Log swallowed exception in agent selector inference
  ([`ed9773e`](https://github.com/n24q02m/web-core/commit/ed9773e38d561e20f32b83fc585edad30fca297d))

- Log swallowed exceptions in runner.py
  ([`0ac688b`](https://github.com/n24q02m/web-core/commit/0ac688bb09f5715a0f89fc836ddaa91fe5f365ef))

- Match script/style end tags with trailing junk in visible_text
  ([#537](https://github.com/n24q02m/web-core/pull/537),
  [`5793b06`](https://github.com/n24q02m/web-core/commit/5793b06cdb2f20925d9a0440d12d6f63637c94e4))

- Match script/style end tags with trailing whitespace in visible_text
  ([#537](https://github.com/n24q02m/web-core/pull/537),
  [`5793b06`](https://github.com/n24q02m/web-core/commit/5793b06cdb2f20925d9a0440d12d6f63637c94e4))

- Missing edge case tests for Google Drive HTML fallback list parsing
  ([`a4b5e6a`](https://github.com/n24q02m/web-core/commit/a4b5e6ad5a7c528a84ac22d1c7482c9aebaacf23))

- Postpone source normalization to capped results in search
  ([`b9e5358`](https://github.com/n24q02m/web-core/commit/b9e53580a7f3eba1e54f8da51f8f41df6d9eaa38))

- Read Turnstile sitekey from iframe src reliably
  ([`ed04b8c`](https://github.com/n24q02m/web-core/commit/ed04b8c293b0052972eb0e11178d46098ae8829e))

- Remove AI-trace plan.md from public repo and gitignore it
  ([#536](https://github.com/n24q02m/web-core/pull/536),
  [`16fcdd3`](https://github.com/n24q02m/web-core/commit/16fcdd30953e529d7b6b1f577966f0da1e2d4336))

- Scope SSRF allowlist to SearXNG host instead of global allow_private
  ([`783448d`](https://github.com/n24q02m/web-core/commit/783448d667ebcbd3e608441a1fae6502bedb4e39))

- Sync README with current code (architecture, config, capabilities)
  ([#538](https://github.com/n24q02m/web-core/pull/538),
  [`3d72d8a`](https://github.com/n24q02m/web-core/commit/3d72d8a8453f686cadd4dda95763cc8dde166697))

- Synchronous blocking sleep inside loop
  ([`5c1981a`](https://github.com/n24q02m/web-core/commit/5c1981afb3e5b68119d1c86f8086f255a7e56d61))

- Update dawidd6/action-send-mail action to v18
  ([`8b6b683`](https://github.com/n24q02m/web-core/commit/8b6b683a9ec80be4d036aab67465525d14f772f3))

- Update ghcr.io/astral-sh/uv:latest docker digest
  ([`8598b61`](https://github.com/n24q02m/web-core/commit/8598b6169b484352d384e2a1c7769c9274300fc7))

- Update non-major dependencies
  ([`4be00c2`](https://github.com/n24q02m/web-core/commit/4be00c26820c64188b604c15f92bad8ab19e2dbc))

- Use direct namedtuple field access for GoogleDriveFileToDownload
  ([`1844a44`](https://github.com/n24q02m/web-core/commit/1844a44f234234a2465c5458ab0c620be8a9a236))

- Use lazy %s logging in selector_inference
  ([`7152509`](https://github.com/n24q02m/web-core/commit/7152509590182e37a10a64b0f2148f91ca427498))

- **deps**: Lock file maintenance ([#605](https://github.com/n24q02m/web-core/pull/605),
  [`b0ec822`](https://github.com/n24q02m/web-core/commit/b0ec8222c6e166d4286af88a3a023debb1af40c3))

- **deps**: Lock file maintenance ([#541](https://github.com/n24q02m/web-core/pull/541),
  [`794be4d`](https://github.com/n24q02m/web-core/commit/794be4d8b9b613c892348fa631847923df52486a))

- **deps**: Lock file maintenance ([#540](https://github.com/n24q02m/web-core/pull/540),
  [`b48ca24`](https://github.com/n24q02m/web-core/commit/b48ca248637b1f19263bd4c8fc332385ce63118e))

- **deps**: Lock file maintenance ([#528](https://github.com/n24q02m/web-core/pull/528),
  [`d483ac7`](https://github.com/n24q02m/web-core/commit/d483ac7fbe0c6277ea2c4a7298876573be1b7a56))

- **deps**: Update actions/checkout action to v7
  ([#527](https://github.com/n24q02m/web-core/pull/527),
  [`ecec5cf`](https://github.com/n24q02m/web-core/commit/ecec5cff964f294db0509d9cbaf2450f90325603))

- **deps**: Update actions/setup-python digest to ece7cb0
  ([#577](https://github.com/n24q02m/web-core/pull/577),
  [`748fe55`](https://github.com/n24q02m/web-core/commit/748fe55a25c557f46d6f97231a284ee8d16d49b3))

- **deps**: Update ghcr.io/astral-sh/uv:latest Docker digest to 3d868e5
  ([#604](https://github.com/n24q02m/web-core/pull/604),
  [`dd842b5`](https://github.com/n24q02m/web-core/commit/dd842b5c271f316cb18656385d4bcbc59b103734))

- **deps**: Update ghcr.io/astral-sh/uv:latest Docker digest to d0a0a75
  ([#534](https://github.com/n24q02m/web-core/pull/534),
  [`dc3d747`](https://github.com/n24q02m/web-core/commit/dc3d747e37a2e7db95686b111c0940da3cd1df76))

- **deps**: Update non-major dependencies ([#573](https://github.com/n24q02m/web-core/pull/573),
  [`b803ad3`](https://github.com/n24q02m/web-core/commit/b803ad3f5037a1c83076b57166b72c313a217e78))

- **deps**: Update non-major dependencies ([#526](https://github.com/n24q02m/web-core/pull/526),
  [`f98a46d`](https://github.com/n24q02m/web-core/commit/f98a46d64e9919ad93ea077200704b703055c2cb))

- **deps**: Update non-major dependencies to >=0.9.0
  ([#539](https://github.com/n24q02m/web-core/pull/539),
  [`6985390`](https://github.com/n24q02m/web-core/commit/6985390b4498531c359dbc4353f804a0cc588de7))

- **deps**: Update python:3.13-slim-bookworm Docker digest to fcbd8df
  ([#578](https://github.com/n24q02m/web-core/pull/578),
  [`d3c0057`](https://github.com/n24q02m/web-core/commit/d3c00575d1aec52ec41301b27cae90196dc7938a))

### Performance Improvements

- Add fast path to cloudflare challenge detection
  ([#529](https://github.com/n24q02m/web-core/pull/529),
  [`b4f705e`](https://github.com/n24q02m/web-core/commit/b4f705e7bda69ff71bb89f122568cbe9ad9bf5a0))


## v2.3.0-beta.2 (2026-06-19)

### Features

- Optional HTTP basic-auth for the SearXNG search client
  ([`852170d`](https://github.com/n24q02m/web-core/commit/852170d1bef6642609433fe67fb380dee0fdb846))


## v2.3.0-beta.1 (2026-06-19)

### Bug Fixes

- Add extract_domain coverage and parametrize url validation tests
  ([`dabaec6`](https://github.com/n24q02m/web-core/commit/dabaec6c40117593eafbab9f8c4400d11552b5eb))

- Add unit tests for SearXNG _handle_restart_and_start and remove pragma no cover
  ([`983b6f5`](https://github.com/n24q02m/web-core/commit/983b6f530b636e6a578a2ef6859a715f77543af8))

- Cache normalize_url with lru_cache to avoid repeated URL parsing
  ([`9874c88`](https://github.com/n24q02m/web-core/commit/9874c8899e51e7e1771fec568b10fcc384ed03dd))

- Centralize and unify search test fixtures in conftest
  ([`2efeb52`](https://github.com/n24q02m/web-core/commit/2efeb525800dd71ed56db2788dd0107143c27f4d))

- Cover missing GOOGLE_CLOUD_PROJECT and selector-inference edge cases in tests
  ([`54551dc`](https://github.com/n24q02m/web-core/commit/54551dc4c4a8d789f98331ff3e8457acf9917453))

- Drop unused DriveChapter re-export from adapters package init
  ([`637598e`](https://github.com/n24q02m/web-core/commit/637598ec2782fd758642e071b4ecc7da58b4a55c))

- Re-validate cached DNS IPs against allow_private in is_safe_url to close SSRF bypass
  ([`281b8d4`](https://github.com/n24q02m/web-core/commit/281b8d4a63df5e389899e65fd632d1cc5776f5f6))

- Refresh lockfile (renovate maintenance)
  ([`85043d8`](https://github.com/n24q02m/web-core/commit/85043d8965d8fb2e8f22e963f1ab8b52c3909ab2))

- Remove orphaned Qodo pr-agent config and stale comment
  ([#483](https://github.com/n24q02m/web-core/pull/483),
  [`2ec09b5`](https://github.com/n24q02m/web-core/commit/2ec09b57acddbf7c94ed45c10175a998381fd486))

- Replace private knowledge-core reference with public wet-mcp consumer
  ([#484](https://github.com/n24q02m/web-core/pull/484),
  [`d6bee8d`](https://github.com/n24q02m/web-core/commit/d6bee8d09c2e1364cb021b4f9d0055fbffae6151))

- Reuse cached extract_domain util in selector_inference
  ([`b4753a6`](https://github.com/n24q02m/web-core/commit/b4753a60fe9a39af558418faf4fdd187d4dd5490))

- Reuse shared HTTP connection and raise feed batch size in MangaDexClient pagination
  ([`e9a5c6b`](https://github.com/n24q02m/web-core/commit/e9a5c6bfe5439541a82e9b4363ee344c574306df))

- Set explicit shell=False and add -- separator to subprocess calls in search runner
  ([`8ef2714`](https://github.com/n24q02m/web-core/commit/8ef2714490a16670368ebf270d9f731f0c723dd3))

- Sync cross-promo section and tagline to current descriptions
  ([#487](https://github.com/n24q02m/web-core/pull/487),
  [`b07599f`](https://github.com/n24q02m/web-core/commit/b07599fae8ced6b8d1fa4db94892359edaef41a5))

- Sync README tagline to current capability description
  ([#486](https://github.com/n24q02m/web-core/pull/486),
  [`fa602e6`](https://github.com/n24q02m/web-core/commit/fa602e6fa706be2f98cac3dd2e730bee9f4ec523))

- Update non-major dependencies
  ([`9addd55`](https://github.com/n24q02m/web-core/commit/9addd55db4e6f341bd85e9b78ba74dd6ebe7c99b))

- Use os.path for GoogleDriveFileToDownload name and extension parsing
  ([`1e6b12d`](https://github.com/n24q02m/web-core/commit/1e6b12dae1f6e80c61bce9cfc2cd55b0114822e7))

- Validate Google Drive file ID format to prevent path traversal in download_text_file
  ([`f9f17c3`](https://github.com/n24q02m/web-core/commit/f9f17c34dc74169bf34258d95521d74e8202a28e))

- **deps**: Lock file maintenance ([#481](https://github.com/n24q02m/web-core/pull/481),
  [`dbffd21`](https://github.com/n24q02m/web-core/commit/dbffd21cd5d2c4403c1c3200792d8a6380f0338a))

- **deps**: Update ghcr.io/astral-sh/uv:latest Docker digest to ff07b86
  ([#479](https://github.com/n24q02m/web-core/pull/479),
  [`cfce954`](https://github.com/n24q02m/web-core/commit/cfce954cc0ac42b6133f835e80d526426c7b2907))

- **deps**: Update non-major dependencies ([#480](https://github.com/n24q02m/web-core/pull/480),
  [`44c2cbb`](https://github.com/n24q02m/web-core/commit/44c2cbbbd6ada03e5313ef2a0e3db673cb5df963))

- **deps**: Update python:3.13-slim-bookworm Docker digest to 05b9539
  ([#488](https://github.com/n24q02m/web-core/pull/488),
  [`c9ca670`](https://github.com/n24q02m/web-core/commit/c9ca670f0e9f9e2b2f9ed14eef4435a62d60c900))

### Features

- Add get_manga/get_chapter methods and full page-URL properties to MangaDex adapter
  ([`9343e55`](https://github.com/n24q02m/web-core/commit/9343e55239abf75d9bb139b1d55af9f1ed32448b))

- Escalate past under-rendered JS shells + add remote render backends
  ([#530](https://github.com/n24q02m/web-core/pull/530),
  [`a66d054`](https://github.com/n24q02m/web-core/commit/a66d05477a0496767342c4591e43d406d969b83d))

- **http**: Centralize and memoize fast-path `extract_domain`
  ([#485](https://github.com/n24q02m/web-core/pull/485),
  [`caa8c0e`](https://github.com/n24q02m/web-core/commit/caa8c0e156ac960a18e73f3a56951ea5a21c7a78))

### Testing

- Add unit tests for _handle_restart_and_start
  ([`983b6f5`](https://github.com/n24q02m/web-core/commit/983b6f530b636e6a578a2ef6859a715f77543af8))

- Add unit tests for _handle_restart_and_start and fix formatting/lint
  ([`983b6f5`](https://github.com/n24q02m/web-core/commit/983b6f530b636e6a578a2ef6859a715f77543af8))

- Add unit tests for _handle_restart_and_start and fix lint
  ([`983b6f5`](https://github.com/n24q02m/web-core/commit/983b6f530b636e6a578a2ef6859a715f77543af8))


## v2.2.2-beta.3 (2026-06-10)

### Bug Fixes

- Flatten deeply nested conditionals in is_safe_url
  ([#446](https://github.com/n24q02m/web-core/pull/446),
  [`b1da44e`](https://github.com/n24q02m/web-core/commit/b1da44e9cb0a5956a9e5ab827d60db78e3edb9b6))

- Refactor _build_filtered_query to reduce nested conditionals
  ([#455](https://github.com/n24q02m/web-core/pull/455),
  [`98d68ec`](https://github.com/n24q02m/web-core/commit/98d68ec22fbc9f69b8145ec60fa698292600eefb))

- **scraper**: Implement SSRF protection for Patchright browser
  ([#476](https://github.com/n24q02m/web-core/pull/476),
  [`a64f07b`](https://github.com/n24q02m/web-core/commit/a64f07b21487c2ae790ee261ba5e668739757220))

- **scraper**: Refactor _load_domain_cookies to flatten nested conditionals
  ([#468](https://github.com/n24q02m/web-core/pull/468),
  [`85fa61d`](https://github.com/n24q02m/web-core/commit/85fa61d26e22b32423cdd4f6cd9d44a597758069))

### Testing

- Mock MangaDex API responses ([#470](https://github.com/n24q02m/web-core/pull/470),
  [`f81f75d`](https://github.com/n24q02m/web-core/commit/f81f75ddad7efa19c2133ff842ffdab157616ac6))

- Refactor fixtures in test_searxng_lock.py ([#466](https://github.com/n24q02m/web-core/pull/466),
  [`55e4a34`](https://github.com/n24q02m/web-core/commit/55e4a3422315815b6b4e4a5158e3a77146908555))

- **mangadex**: Improve test coverage to 100% ([#473](https://github.com/n24q02m/web-core/pull/473),
  [`55500e5`](https://github.com/n24q02m/web-core/commit/55500e5a27398b3f4e64e8928771c0f6125a7ce3))

- **search**: Add comprehensive test for missing url keys in domain capping
  ([#465](https://github.com/n24q02m/web-core/pull/465),
  [`c15dfe3`](https://github.com/n24q02m/web-core/commit/c15dfe369bc32014de64c58db1eed07bff1807ab))

- **search**: Add missing tests for _get_docker_lock and refactor config dir management
  ([#477](https://github.com/n24q02m/web-core/pull/477),
  [`0a51f7b`](https://github.com/n24q02m/web-core/commit/0a51f7be1230425d391d6cf47a24f33242edbf08))

- **search**: Add unit tests for _write_secure_text
  ([#448](https://github.com/n24q02m/web-core/pull/448),
  [`f9d9fe7`](https://github.com/n24q02m/web-core/commit/f9d9fe724968ebb510e5fe69340f9097547d6dfd))


## v2.2.2-beta.2 (2026-06-10)

### Bug Fixes

- Raise coverage gate to 95% policy and cover LLM provider calls
  ([#444](https://github.com/n24q02m/web-core/pull/444),
  [`5014e44`](https://github.com/n24q02m/web-core/commit/5014e445f18552dde4f8c258f21b96373511af4e))

- Remove leaked private identity from web-core public package
  ([#443](https://github.com/n24q02m/web-core/pull/443),
  [`c3b59e3`](https://github.com/n24q02m/web-core/commit/c3b59e32977b34593c82c19732ee110207aa0782))


## v2.2.2-beta.1 (2026-06-10)

### Bug Fixes

- **deps**: Lock file maintenance ([#441](https://github.com/n24q02m/web-core/pull/441),
  [`90a1864`](https://github.com/n24q02m/web-core/commit/90a1864575430843bd4d75333011ef03efc2b714))

- **deps**: Update non-major dependencies to >=0.0.46
  ([#440](https://github.com/n24q02m/web-core/pull/440),
  [`edb9fb7`](https://github.com/n24q02m/web-core/commit/edb9fb7f59e351c145890174d8c316c3bdc9d817))

- **deps**: Update step-security/harden-runner digest to 9af89fc
  ([#439](https://github.com/n24q02m/web-core/pull/439),
  [`5879cd3`](https://github.com/n24q02m/web-core/commit/5879cd3a24a38c420f6717583c80564f18e21cd4))


## v2.2.1 (2026-06-09)


## v2.2.1-beta.1 (2026-06-09)

### Bug Fixes

- Gitignore bot/merge junk artifacts (*.orig/*.rej/*.patch/*.diff/*.cover/*.bak)
  ([#396](https://github.com/n24q02m/web-core/pull/396),
  [`b921414`](https://github.com/n24q02m/web-core/commit/b9214140c737443644f80bb24d3aa2c6d7c812af))

- **deps**: Lock file maintenance ([#399](https://github.com/n24q02m/web-core/pull/399),
  [`45c3d10`](https://github.com/n24q02m/web-core/commit/45c3d10c0b9563c08fecae09aa61c7230066adb2))

- **deps**: Update codecov/codecov-action action to v7
  ([#398](https://github.com/n24q02m/web-core/pull/398),
  [`79fca4c`](https://github.com/n24q02m/web-core/commit/79fca4c254d2ea33902d751ff0723b4f0711ef9b))

- **deps**: Update non-major dependencies to >=0.0.45
  ([#437](https://github.com/n24q02m/web-core/pull/437),
  [`7e4087a`](https://github.com/n24q02m/web-core/commit/7e4087aca273ec5847313daa8951748a1daa2fcf))

- **scraper**: Add SSRF protection to browser strategies
  ([#426](https://github.com/n24q02m/web-core/pull/426),
  [`06242b0`](https://github.com/n24q02m/web-core/commit/06242b07d7a0d5e902618b49398da2e00d562140))

### Testing

- Add comprehensive tests for _build_filtered_query robustness
  ([#414](https://github.com/n24q02m/web-core/pull/414),
  [`6c14f0d`](https://github.com/n24q02m/web-core/commit/6c14f0d6ae8af5e4a42a617aa3e4126116d2ff9d))


## v2.2.0 (2026-06-07)


## v2.2.0-beta.1 (2026-06-07)

### Bug Fixes

- Add captcha coverage tests for safe client and sitekey extraction
  ([#308](https://github.com/n24q02m/web-core/pull/308),
  [`17f8bfc`](https://github.com/n24q02m/web-core/commit/17f8bfc2cdc01ef34f3505ed610a66aa33721fb3))

- Add cookie-passing tests for basic HTTP strategy
  ([#309](https://github.com/n24q02m/web-core/pull/309),
  [`d83c9b1`](https://github.com/n24q02m/web-core/commit/d83c9b1902a2d9803d1c2d915621477d63fb7724))

- Add cookies and max-redirects tests for TLS spoof strategy
  ([#302](https://github.com/n24q02m/web-core/pull/302),
  [`8845b8b`](https://github.com/n24q02m/web-core/commit/8845b8b29d295cd499de0505024d58a72bf038d9))

- Add invalid-json and protocol-less url tests for selector inference
  ([#292](https://github.com/n24q02m/web-core/pull/292),
  [`91aad9c`](https://github.com/n24q02m/web-core/commit/91aad9c5b43fbb5d0dedbea3a633e3e2e65b2356))

- Add is_safe_url dns cache tests ([#307](https://github.com/n24q02m/web-core/pull/307),
  [`b3134a0`](https://github.com/n24q02m/web-core/commit/b3134a070c1305ff71c6c137abedf3db60e8dd62))

- Add normalize_url edge case tests ([#291](https://github.com/n24q02m/web-core/pull/291),
  [`2932859`](https://github.com/n24q02m/web-core/commit/2932859fc685ec7bed254512a187693d01582562))

- Add shared client reuse and dedup branch tests for search
  ([#300](https://github.com/n24q02m/web-core/pull/300),
  [`15391af`](https://github.com/n24q02m/web-core/commit/15391af7414437b73538009d6319a3d36ee82f2f))

- Add SSRF block and DNS cache expiry tests for safe http client
  ([#301](https://github.com/n24q02m/web-core/pull/301),
  [`3f5cd79`](https://github.com/n24q02m/web-core/commit/3f5cd79c8e17ffcad13afd5d862d99093d5943aa))

- Add strip_tracking_params coverage tests ([#313](https://github.com/n24q02m/web-core/pull/313),
  [`00035ad`](https://github.com/n24q02m/web-core/commit/00035ad1a0653a385d0bcfe7389de22d3d14de15))

- Add turnstile sitekey extraction variation tests
  ([#287](https://github.com/n24q02m/web-core/pull/287),
  [`94c091c`](https://github.com/n24q02m/web-core/commit/94c091c80f8455b02f5d5ba91d97f8029d6fae5d))

- Add unix lsof/fuser fallback tests for stale port kill
  ([#295](https://github.com/n24q02m/web-core/pull/295),
  [`8afb3e6`](https://github.com/n24q02m/web-core/commit/8afb3e6f06b1a1cfed2f6d47e178dc834f8016be))

- Update ghcr.io/astral-sh/uv Docker digest to 03bdc89
  ([#321](https://github.com/n24q02m/web-core/pull/321),
  [`add3c69`](https://github.com/n24q02m/web-core/commit/add3c69865c995025ae8048c12c6a1a5323071cc))

- Update non-major dependencies ([#322](https://github.com/n24q02m/web-core/pull/322),
  [`f5b64c0`](https://github.com/n24q02m/web-core/commit/f5b64c099a22eca111168c108527c28ba88fbcd8))

- Uv lock file maintenance ([#323](https://github.com/n24q02m/web-core/pull/323),
  [`e7ae1b1`](https://github.com/n24q02m/web-core/commit/e7ae1b1a3838d92bf9bb49294deb46962bda91ee))

- **deps**: Bump aiohttp in the uv group across 1 directory
  ([#332](https://github.com/n24q02m/web-core/pull/332),
  [`b5d67a3`](https://github.com/n24q02m/web-core/commit/b5d67a34a99e2552078db951a0ef3a133f9ed6d2))

- **deps**: Update actions/checkout digest to df4cb1c
  ([`57df1a1`](https://github.com/n24q02m/web-core/commit/57df1a1c8c9d063fb10bcdcad8cd5fb63d7b7a34))

- **deps**: Update ghcr.io/astral-sh/uv Docker digest to b46b03d
  ([`8a5cd5a`](https://github.com/n24q02m/web-core/commit/8a5cd5a5da7fbba2919131d24cae34d3ae2d2ea4))

- **deps**: Update github/codeql-action digest to 8aad20d
  ([`aadde8a`](https://github.com/n24q02m/web-core/commit/aadde8a71c01f34d6cb07c8e2bc0eaf48e626209))

- **deps**: Update non-major dependencies
  ([`83f2348`](https://github.com/n24q02m/web-core/commit/83f234829029c1fb9e681b8e37ab27ad7aa84dd0))

- **search**: Fix SSRF vulnerability in service wait and search client
  ([`fa180c5`](https://github.com/n24q02m/web-core/commit/fa180c5054a23983994672de6d6c29441503eaf2))

### Features

- Add error-condition tests for _find_available_port
  ([`2494421`](https://github.com/n24q02m/web-core/commit/2494421e9a1080ad0e7cd50da05b46be11520a90))

- Add test for mangadex download_image failure
  ([`2c5930c`](https://github.com/n24q02m/web-core/commit/2c5930ccfb85dd13ed5fe868d5de6c8493bb3308))

- Add tests for _build_filtered_query error handling
  ([`57a3c7c`](https://github.com/n24q02m/web-core/commit/57a3c7cffef1206e1687ab6e70f603edee6ad562))

- Add tests for _get_docker_lock
  ([`6b70e75`](https://github.com/n24q02m/web-core/commit/6b70e753f6d3993ff7a4c063f4a5481880c640a8))

- Add tests for SearXNG Docker startup logic
  ([`c2deb20`](https://github.com/n24q02m/web-core/commit/c2deb20dea0baa8729c9d5942ec960fbbde8992f))


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
