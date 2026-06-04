import sys

with open('src/web_core/adapters/mangadex.py', 'r') as f:
    lines = f.readlines()

new_methods = """
    def _parse_chapter_batch(self, items: list[dict]) -> list[ChapterInfo]:
        \"\"\"Parse a list of chapter items from the API.\"\"\"
        batch_chapters: list[ChapterInfo] = []
        for item in items:
            attrs = item.get("attributes", {})
            batch_chapters.append(
                ChapterInfo(
                    id=item["id"],
                    chapter=attrs.get("chapter"),
                    title=attrs.get("title"),
                    volume=attrs.get("volume"),
                    language=attrs.get("translatedLanguage", ""),
                    pages=attrs.get("pages", 0),
                )
            )
        return batch_chapters

    async def _fetch_chapter_batch(
        self,
        manga_id: str,
        language: str,
        offset: int,
        limit: int,
    ) -> list[ChapterInfo]:
        \"\"\"Fetch and parse a single page of the manga feed.\"\"\"
        data = await self._get(
            f"/manga/{manga_id}/feed",
            params={
                "translatedLanguage[]": language,
                "order[chapter]": "asc",
                "limit": limit,
                "offset": offset,
            },
        )
        return self._parse_chapter_batch(data.get("data", []))
"""

# Insert after _get method which ends at line 152 (index 151)
lines.insert(153, new_methods)

with open('src/web_core/adapters/mangadex.py', 'w') as f:
    f.writelines(lines)
