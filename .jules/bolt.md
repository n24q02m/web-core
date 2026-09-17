## 2023-10-27 - Split script/style regex alternation for fast-path optimization
**Learning:** Combining multiple regular expressions into a single alternation pattern (like `<(script|style)`) forces the regex engine into parallel search mode if the individual patterns lack a common prefix. This disables fast-path literal string searching (like Boyer-Moore) which is highly effective on large documents.
**Action:** Iterate sequentially over independent, compiled regexes (e.g., one for `<script>` and one for `<style>`) to allow the engine to utilize fast-paths.

## 2024-09-16 - Whitespace collapsing optimization
**Learning:** Using `" ".join(string.split())` is approximately 5x faster for collapsing arbitrary whitespace in strings compared to using a compiled regular expression (`re.compile(r"\s+").sub(" ", string).strip()`). The `split()` method without arguments utilizes highly optimized C-level string methods.
**Action:** Replace `re.sub` whitespace collapsing with `" ".join(string.split())` where appropriate for performance-critical text processing.
