import sys
path = "src/web_core/adapters/mangadex.py"
with open(path, "r") as f:
    lines = f.readlines()

start = -1
end = -1
for i, line in enumerate(lines):
    if "def _parse_batch(items: list[dict]) -> list[ChapterInfo]:" in line:
        start = i
    if start != -1 and "return batch_chapters" in line and line.strip() == "return batch_chapters":
        end = i
        break

if start == -1 or end == -1:
    print(f"Failed to find block: start={start}, end={end}")
    sys.exit(1)

new_block = [
    "        def _parse_batch(items: list[dict]) -> list[ChapterInfo]:\n",
    "            return [\n",
    "                ChapterInfo(\n",
    "                    id=item[\"id\"],\n",
    "                    chapter=(attrs := item.get(\"attributes\", {})).get(\"chapter\"),\n",
    "                    title=attrs.get(\"title\"),\n",
    "                    volume=attrs.get(\"volume\"),\n",
    "                    language=attrs.get(\"translatedLanguage\", \"\"),\n",
    "                    pages=attrs.get(\"pages\", 0),\n",
    "                )\n",
    "                for item in items\n",
    "            ]\n"
]

lines[start:end+1] = new_block
with open(path, "w") as f:
    f.writelines(lines)
print("Success")
