## 2023-10-27 - Split script/style regex alternation for fast-path optimization
**Learning:** Combining multiple regular expressions into a single alternation pattern (like `<(script|style)`) forces the regex engine into parallel search mode if the individual patterns lack a common prefix. This disables fast-path literal string searching (like Boyer-Moore) which is highly effective on large documents.
**Action:** Iterate sequentially over independent, compiled regexes (e.g., one for `<script>` and one for `<style>`) to allow the engine to utilize fast-paths.

## 2024-09-16 - Whitespace collapsing optimization
**Learning:** Using `" ".join(string.split())` is approximately 5x faster for collapsing arbitrary whitespace in strings compared to using a compiled regular expression (`re.compile(r"\s+").sub(" ", string).strip()`). The `split()` method without arguments utilizes highly optimized C-level string methods.
**Action:** Replace `re.sub` whitespace collapsing with `" ".join(string.split())` where appropriate for performance-critical text processing.

## 2024-09-20 - Pre-compile regex in hot paths to avoid parsing overhead
**Learning:** Calling `re.sub(pattern, ...)` with a string pattern directly on hot paths forces the regex engine to parse the pattern and maintain an internal cache. Pre-compiling the regex at the module level using `re.compile(pattern)` and calling `.sub(...)` on the compiled object avoids this overhead, making execution significantly faster (e.g., ~33% faster for user-agent substitution).
**Action:** Extract inline regex patterns into module-level pre-compiled `re.Pattern` objects for frequently called functions.

## 2024-10-05 - Rejected Micro-Optimization: Pre-compiling Regex in Loops
**Learning:** Pre-compiling a simple regex (like `r"v?(\d+)"`) that is executed within a nested loop was rejected by the maintainers as a duplicate/micro-optimization. While technically faster, the maintainers considered the impact too small to warrant the change, categorizing it alongside similar past rejections (e.g., #842).
**Action:** Avoid proposing micro-optimizations that only save a fraction of a microsecond per call (like pre-compiling simple, infrequently executed regexes) unless there is clear evidence it is a bottleneck in a critical hot-path. Focus on larger algorithmic or architectural performance gains.
