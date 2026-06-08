@lru_cache(maxsize=512)
def normalize_url(url: str) -> str:
    """Normalize a URL for deduplication.

    Transformations applied:
    - Lowercase scheme and netloc
    - Strip ``www.`` prefix from netloc
    - Strip trailing slashes from path (including `;params` section)
    - Remove tracking query parameters (UTM, click IDs, etc.)
    - Remove fragment (``#section`\*)

    Returns the original string unchanged if parsing fails.
    Returns empty string for empty input.
    """
    if not url:
        return ""

    try:
        # Performance Optimization: urlsplit is ~10x faster than urlparse
        split = urlsplit(url)
    except Exception:
        return url

    scheme = (split.scheme or "").lower()
    netloc = (split.netloc or "").lower()

    if netloc.startswith("www."):
        netloc = netloc[4:]

    # Strips trailing slashes from the entire path (including legacy ;params)
    path = split.path.rstrip("/") or ""

    if split.query:
        # Fast path check for tracking params (~17x faster if absent)
        if not _TRACKING_RE.search(split.query):
            query = split.query
        else:
            params = parse_qs(split.query, keep_blank_values=True)
            cleaned = {k: v for k, v in params.items() if k not in _TRACKING_PARAMS}
            query = urlencode(cleaned, doseq=True)
    else:
        query = ""

    # Fragment is always stripped (empty string)
    return urlunsplit((scheme, netloc, path, query, ""))
