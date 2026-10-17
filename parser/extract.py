"""Разбор HTML-страниц каталога. Только чистые функции — без сети, легко тестировать.

Селекторы рассчитаны на учебный магазин books.toscrape.com.
Для другого сайта достаточно поменять функции в этом файле.
"""

import re
from dataclasses import dataclass
from urllib.parse import urljoin

from selectolax.lexbor import LexborHTMLParser as HTMLParser

RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


@dataclass
class Product:
    title: str
    price: float
    currency: str
    in_stock: bool
    rating: int
    url: str
    category: str = ""
    stock_count: int | None = None
    upc: str = ""
    description: str = ""


def parse_price(text: str) -> tuple[float, str]:
    """«£51.77» → (51.77, '£'). Понимает и «1 299,90 ₽»."""
    text = text.strip()
    match = re.search(r"\d[\d\s ]*(?:[.,]\d+)?", text)
    if not match:
        raise ValueError(f"Не удалось распознать цену: {text!r}")
    number = match.group().replace(" ", "").replace(" ", "").replace(",", ".")
    currency = (text[: match.start()] + text[match.end() :]).strip()
    return float(number), currency


def parse_listing(html: str, page_url: str) -> tuple[list[str], str | None]:
    """Страница каталога → (ссылки на товары, ссылка на следующую страницу)."""
    tree = HTMLParser(html)
    links = [
        urljoin(page_url, a.attributes["href"])
        for a in tree.css("article.product_pod h3 a")
        if a.attributes.get("href")
    ]
    nxt = tree.css_first("li.next a")
    next_url = urljoin(page_url, nxt.attributes["href"]) if nxt and nxt.attributes.get("href") else None
    return links, next_url


def parse_product(html: str, url: str) -> Product:
    """Карточка товара → Product."""
    tree = HTMLParser(html)
    main = tree.css_first("div.product_main")
    if main is None:
        raise ValueError(f"На странице нет карточки товара: {url}")

    title = main.css_first("h1").text(strip=True)
    price, currency = parse_price(main.css_first("p.price_color").text())

    availability = main.css_first("p.availability").text(strip=True)
    count = re.search(r"\((\d+) available\)", availability)

    rating_node = main.css_first("p.star-rating")
    rating_classes = (rating_node.attributes.get("class") or "").split() if rating_node else []
    rating = next((RATINGS[c] for c in rating_classes if c in RATINGS), 0)

    crumbs = tree.css("ul.breadcrumb li a")
    category = crumbs[-1].text(strip=True) if len(crumbs) >= 3 else ""

    desc_node = tree.css_first("#product_description + p")
    table = {
        row.css_first("th").text(strip=True): row.css_first("td").text(strip=True)
        for row in tree.css("table.table tr")
        if row.css_first("th") and row.css_first("td")
    }

    return Product(
        title=title,
        price=price,
        currency=currency,
        in_stock="In stock" in availability,
        rating=rating,
        url=url,
        category=category,
        stock_count=int(count.group(1)) if count else None,
        upc=table.get("UPC", ""),
        description=desc_node.text(strip=True) if desc_node else "",
    )
