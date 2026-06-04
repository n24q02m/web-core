with open('src/web_core/adapters/mangadex.py', 'r') as f:
    lines = f.readlines()

new_feed = """    async def get_chapter_feed(
        self,
        manga_id: str,
        language: str = "en",
        limit: int = 100,
    ) -> list[ChapterInfo]:
        \"\"\"Get chapters for a manga, handling pagination automatically.

        Parameters
        ----------
        manga_id:
            UUID of the manga.
        language:
            Translated language filter (ISO 639-1).
        limit:
            Maximum number of chapters to return.
        \"\"\"
        # Fetch first page to get total
        first_batch_limit = min(limit, 100)
        data = await self._get(
            f"/manga/{manga_id}/feed",
            params={
                "translatedLanguage[]": language,
                "order[chapter]": "asc",
                "limit": first_batch_limit,
                "offset": 0,
            },
        )

        total = data.get("total", 0)
        first_batch = data.get("data", [])
        chapters = self._parse_chapter_batch(first_batch)

        # Calculate remaining pages
        effective_limit = min(limit, total)
        if len(chapters) >= effective_limit or not first_batch:
            return chapters[:limit]

        # Prepare offsets for remaining pages
        offsets = []
        curr_offset = len(chapters)
        pages_to_fetch = 1  # We already fetched one page
        while curr_offset < effective_limit and pages_to_fetch < _MAX_FEED_PAGES:
            next_batch_limit = min(limit - curr_offset, 100)
            offsets.append((curr_offset, next_batch_limit))
            curr_offset += next_batch_limit
            pages_to_fetch += 1

        if not offsets:
            return chapters[:limit]

        results = await asyncio.gather(
            *(self._fetch_chapter_batch(manga_id, language, o, l) for o, l in offsets)
        )
        for batch_chapters in results:
            chapters.extend(batch_chapters)

        return chapters[:limit]
"""

# Replace lines 229 to 314 (index 228 to 313)
# Need to be careful about the exact range.
# Line 315 is '    async def get_chapter_images(' which is index 314.
# So we replace up to index 313.

lines[228:314] = [new_feed + "\n"]

with open('src/web_core/adapters/mangadex.py', 'w') as f:
    f.writelines(lines)
