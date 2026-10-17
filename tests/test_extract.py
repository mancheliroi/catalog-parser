import pytest

from parser.extract import parse_listing, parse_price, parse_product
from tests.conftest import listing_page, product_page

BASE = "https://books.toscrape.com/catalogue/"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("£51.77", (51.77, "£")),
        ("  $5 ", (5.0, "$")),
        ("1 299,90 ₽", (1299.90, "₽")),
        ("1 299 ₽", (1299.0, "₽")),
    ],
)
def test_parse_price(text, expected):
    assert parse_price(text) == expected


def test_parse_price_rejects_garbage():
    with pytest.raises(ValueError):
        parse_price("нет в наличии")


def test_listing_links_and_next_page_are_absolute():
    links, nxt = parse_listing(listing_page(["x", "y"], "page-2.html"), BASE + "page-1.html")
    assert links == [BASE + "x/index.html", BASE + "y/index.html"]
    assert nxt == BASE + "page-2.html"


def test_last_listing_page_has_no_next():
    _, nxt = parse_listing(listing_page(["x"], None), BASE + "page-50.html")
    assert nxt is None


def test_product_fields():
    p = parse_product(product_page("Книга А"), BASE + "book-a/index.html")
    assert (p.title, p.price, p.currency) == ("Книга А", 51.77, "£")
    assert p.in_stock and p.stock_count == 22
    assert p.rating == 3
    assert p.category == "Poetry"
    assert p.upc == "a897fe39b1053632"
    assert p.description == "Описание книги «Книга А»."


def test_out_of_stock_product():
    p = parse_product(product_page("Б", stock="Out of stock", rating="Five"), BASE + "b/index.html")
    assert not p.in_stock and p.stock_count is None and p.rating == 5


def test_page_without_product_raises():
    with pytest.raises(ValueError):
        parse_product("<html></html>", BASE + "x")
