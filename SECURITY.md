# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please **DO NOT** create a public issue.

Instead, please email: **quangminh2402.dev@gmail.com**

Include:

1. Detailed description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if any)

You will receive acknowledgment within 48 hours.

## Security Measures

- Regular dependency updates via Renovate
- Pre-commit hooks with gitleaks for secret detection
- GitHub Actions SHA-pinned for supply chain security
- Branch protection via repository rulesets
- SSRF protection on all outbound HTTP: DNS pinning + IP validation, redirect
  no-follow with per-hop re-validation, and per-connection re-resolve-and-vet
  to close redirect-bypass and DNS-rebinding (TOCTOU) gaps — enforced across
  HTTP strategies and stealth browsers
- Published as a public PyPI package; releases via OIDC Trusted Publishing
