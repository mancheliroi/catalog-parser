"""HTML-образцы в разметке books.toscrape.com."""

import pytest


def listing_page(slugs: list[str], next_href: str | None) -> str:
    items = "".join(
        f'<article class="product_pod"><h3><a href="{s}/index.html" title="{s}">{s}</a></h3></article>'
        for s in slugs
    )
    nxt = f'<li class="next"><a href="{next_href}">next</a></li>' if next_href else ""
    return f"<html><body><section><ol class='row'>{items}</ol><ul class='pager'>{nxt}</ul></section></body></html>"


def product_page(title: str, price: str = "£51.77", stock: str = "In stock (22 available)", rating: str = "Three") -> str:
    return f"""
    <html><body>
      <ul class="breadcrumb">
        <li><a href="../index.html">Home</a></li>
        <li><a href="../category/books_1/index.html">Books</a></li>
        <li><a href="../category/books/poetry_23/index.html">Poetry</a></li>
        <li class="active">{title}</li>
      </ul>
      <div class="product_main">
        <h1>{title}</h1>
        <p class="price_color">{price}</p>
        <p class="instock availability"><i class="icon-ok"></i> {stock} </p>
        <p class="star-rating {rating}"></p>
      </div>
      <div id="product_description" class="sub-header"><h2>Product Description</h2></div>
      <p>Описание книги «{title}».</p>
      <table class="table table-striped">
        <tr><th>UPC</th><td>a897fe39b1053632</td></tr>
        <tr><th>Product Type</th><td>Books</td></tr>
      </table>
    </body></html>"""


@pytest.fixture
def site():
    """Маленький «сайт» из двух страниц каталога и трёх карточек (одна битая)."""
    base = "https://books.toscrape.com/catalogue/"
    return {
        base + "page-1.html": listing_page(["book-a", "book-b"], "page-2.html"),
        base + "page-2.html": listing_page(["book-c", "book-a"], None),  # book-a дублируется
        base + "book-a/index.html": product_page("Книга А"),
        base + "book-b/index.html": product_page("Книга Б", price="£10.00", stock="Out of stock", rating="Five"),
        base + "book-c/index.html": "<html><body>404-подобная страница без карточки</body></html>",
    }
