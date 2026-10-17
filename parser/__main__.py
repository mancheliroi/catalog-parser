"""CLI: python -m parser --out data/books.xlsx --pages 3"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

import httpx

from parser.crawler import crawl
from parser.export import save

DEFAULT_URL = "https://books.toscrape.com/catalogue/page-1.html"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Парсер каталога товаров с выгрузкой в Excel/CSV")
    ap.add_argument("--url", default=DEFAULT_URL, help="первая страница каталога")
    ap.add_argument("--out", type=Path, default=Path("data/products.xlsx"), help="файл результата (.xlsx или .csv)")
    ap.add_argument("--pages", type=int, default=None, help="сколько страниц каталога обойти (по умолчанию все)")
    ap.add_argument("--concurrency", type=int, default=5, help="одновременных запросов")
    ap.add_argument("--delay", type=float, default=0.2, help="пауза после запроса, сек")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(message)s")

    def progress(done: int, total: int) -> None:
        print(f"\rКарточки: {done}/{total}", end="", file=sys.stderr, flush=True)

    started = time.monotonic()
    try:
        products, failed = asyncio.run(
            crawl(args.url, max_pages=args.pages, concurrency=args.concurrency, delay=args.delay, on_progress=progress)
        )
    except httpx.HTTPError as exc:
        print(f"Не удалось загрузить каталог: {exc}", file=sys.stderr)
        return 2
    print(file=sys.stderr)
    save(products, args.out)

    print(f"Готово: {len(products)} товаров → {args.out} за {time.monotonic() - started:.1f} с")
    if failed:
        print(f"Не удалось обработать {len(failed)} ссылок (см. лог с -v)")
    return 0 if products else 1


if __name__ == "__main__":
    raise SystemExit(main())
