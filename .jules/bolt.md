## 2023-10-27 - Split script/style regex alternation for fast-path optimization
**Learning:** Combining multiple regular expressions into a single alternation pattern (like `<(script|style)`) forces the regex engine into parallel search mode if the individual patterns lack a common prefix. This disables fast-path literal string searching (like Boyer-Moore) which is highly effective on large documents.
**Action:** Iterate sequentially over independent, compiled regexes (e.g., one for `<script>` and one for `<style>`) to allow the engine to utilize fast-paths.
