"""Обход каталога: страницы со списком → карточки товаров."""

import asyncio
import logging
from collections.abc import Callable

import httpx

from parser.extract import Product, parse_listing, parse_product

log = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; CatalogParser/1.0; +https://github.com/mancheliroi)"


async def fetch(client: httpx.AsyncClient, url: str, *, retries: int = 3, backoff: float = 1.0) -> str:
    """GET с повторами при сетевых ошибках и ответах 429/5xx."""
    for attempt in range(1, retries + 1):
        try:
            resp = await client.get(url)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise httpx.HTTPStatusError(f"HTTP {resp.status_code}", request=resp.request, response=resp)
            resp.raise_for_status()
            return resp.text
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            client_error = status is not None and status < 500 and status != 429
            if client_error or attempt == retries:
                raise
            wait = backoff * 2 ** (attempt - 1)
            log.warning("Ошибка %s на %s, повтор через %.1f с", exc, url, wait)
            await asyncio.sleep(wait)
    raise RuntimeError("unreachable")


async def crawl(
    start_url: str,
    *,
    max_pages: int | None = None,
    concurrency: int = 5,
    delay: float = 0.2,
    client: httpx.AsyncClient | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> tuple[list[Product], list[str]]:
    """Возвращает (товары, ссылки, которые не удалось обработать)."""
    own_client = client is None
    client = client or httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT}, timeout=20, follow_redirects=True
    )
    sem = asyncio.Semaphore(concurrency)

    try:
        # 1. Собираем ссылки на товары, проходя пагинацию
        product_urls: list[str] = []
        url, pages = start_url, 0
        while url and (max_pages is None or pages < max_pages):
            html = await fetch(client, url)
            links, url = parse_listing(html, url)
            product_urls.extend(links)
            pages += 1
            log.info("Страница %d: %d товаров", pages, len(links))
            await asyncio.sleep(delay)

        product_urls = list(dict.fromkeys(product_urls))  # без дублей, порядок сохраняется

        # 2. Параллельно, но с ограничением, загружаем карточки
        done = 0
        failed: list[str] = []

        async def load(product_url: str) -> Product | None:
            nonlocal done
            async with sem:
                try:
                    product = parse_product(await fetch(client, product_url), product_url)
                except Exception as exc:  # одна битая карточка не должна ронять весь сбор
                    log.error("Не удалось обработать %s: %s", product_url, exc)
                    failed.append(product_url)
                    product = None
                await asyncio.sleep(delay)
            done += 1
            if on_progress:
                on_progress(done, len(product_urls))
            return product

        results = await asyncio.gather(*(load(u) for u in product_urls))
        return [p for p in results if p is not None], failed
    finally:
        if own_client:
            await client.aclose()
