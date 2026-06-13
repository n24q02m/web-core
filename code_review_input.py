# Source: src/web_core/adapters/google_drive.py

async def _list_folder_recursive(folder_id: str, semaphore: asyncio.Semaphore) -> list[DriveFile]:
    """Recursively list files in a Google Drive folder using the embedded view."""
    url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    async with semaphore:
        async with safe_httpx_client(follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return []
            html = resp.text

    soup = bs4.BeautifulSoup(html, "html.parser")
    files: list[DriveFile] = []
    subfolder_ids: list[str] = []

    for a_tag in soup.find_all("a"):
        href = a_tag.get("href", "")
        if not isinstance(href, str) or not href:
            continue

        # File links
        file_match = re.search(r"drive\.google\.com/file/d/([-\w]{25,})", href)
        if file_match:
            file_id = file_match.group(1)
            name = a_tag.get_text(strip=True)
            ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if ext in _SUPPORTED_EXTS:
                files.append(DriveFile(file_id=file_id, name=name))
            continue

        # Doc links (Google native)
        docs_match = re.search(r"docs\.google\.com/\w+/d/([-\w]{25,})", href)
        if docs_match:
            file_id = docs_match.group(1)
            name = a_tag.get_text(strip=True)
            files.append(DriveFile(file_id=file_id, name=name))
            continue

        # Subfolder links
        folder_match = re.search(r"drive\.google\.com/drive/folders/([-\w]{25,})", href)
        if folder_match:
            subfolder_ids.append(folder_match.group(1))

    if subfolder_ids:
        # Deduplicate subfolder IDs to avoid infinite loops or redundant work
        subfolder_ids = list(dict.fromkeys(subfolder_ids))
        tasks = [_list_folder_recursive(fid, semaphore) for fid in subfolder_ids]
        subfolder_results = await asyncio.gather(*tasks)
        for res in subfolder_results:
            files.extend(res)

    return files
