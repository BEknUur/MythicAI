import asyncio
import httpx, logging, mimetypes
from pathlib import Path
from typing import List, Dict

log = logging.getLogger("downloader")


# ─────────────────── сбор ссылок ────────────────────────────────────────────
def _collect_urls(items: List[Dict]) -> List[str]:
    """Ищем displayUrl и images во всех latestPosts и childPosts."""
    urls: list[str] = []

    def walk(post: Dict):
        if post.get("displayUrl"):
            urls.append(post["displayUrl"])
        urls.extend(post.get("images", []))
        for child in post.get("childPosts", []):
            walk(child)

    for root in items:
        for p in root.get("latestPosts", []):
            walk(p)

    # удаляем дубликаты, сохраняя порядок
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            out.append(u)
            seen.add(u)
    return out


# ─────────────────── скачивание ─────────────────────────────────────────────
async def _save(url: str, folder: Path, client: httpx.AsyncClient, idx: int):
    r = await client.get(url, follow_redirects=True, timeout=30)
    r.raise_for_status()
    # получаем расширение по Content-Type, fallback = .jpg
    ext = mimetypes.guess_extension(r.headers.get("content-type", "")) or ".jpg"
    fname = folder / f"{idx:03d}{ext}"
    fname.write_bytes(r.content)
    log.debug("saved %s", fname.name)


def download_photos(items: List[Dict], folder: Path):
    """Синхронная обёртка для Starlette BackgroundTask."""
    urls = _collect_urls(items)
    if not urls:
        log.warning("no image urls found — nothing to download")
        return

    folder.mkdir(parents=True, exist_ok=True)
    log.info("downloading %s images → %s", len(urls), folder)

    async def main():
        async with httpx.AsyncClient() as client:
            tasks = [_save(u, folder, client, i) for i, u in enumerate(urls, 1)]
            await asyncio.gather(*tasks)

    asyncio.run(main())
    log.info("done   (%s files)", len(urls))
