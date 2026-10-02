from pathlib import Path

import pytest

from festa_do_livro.catalog_builder import (
    ParsedPriceList,
    build_catalog,
    imprint_repeats_exhibitor,
    parse_price_list,
    safe_public_url,
    same_content,
)
from festa_do_livro.fair_site import EventDetails, Publisher
from festa_do_livro.price_verification import verify_prices

PRICE_LISTS = Path(__file__).parent / "fixtures" / "price_lists"
EVENT = EventDetails(edition="27-festa-do-livro-da-usp", name="27 Festa do Livro da USP", period="26 e 30 de novembro")


def catalog_for(fixture_name: str, exhibitor_name: str) -> tuple[dict, ParsedPriceList]:
    parsed = parse_price_list(PRICE_LISTS / fixture_name)
    publishers = [Publisher(name=exhibitor_name, slug="", price_list_url="https://example.com/x.pdf", site="")]
    return build_catalog(EVENT, publishers, {0: parsed}, "2026-10-02T00:00:00+00:00"), parsed


def book_titled(catalog: dict, title_start: str) -> dict:
    matches = [book for book in catalog["livros"] if book["t"].startswith(title_start)]
    assert matches, f"livro começando com {title_start!r} não encontrado"
    return matches[0]


@pytest.fixture(scope="module")
def newpop():
    return catalog_for("newpop.pdf", "NewPOP Editora")


@pytest.fixture(scope="module")
def harpercollins():
    return catalog_for("harpercollins.pdf", "HarperCollins Brasil")


@pytest.fixture(scope="module")
def atma():
    return catalog_for("atma.pdf", "Atma Editora")


def test_reads_every_book_of_a_standard_list(newpop):
    catalog, _ = newpop
    assert len(catalog["livros"]) == 338


def test_standard_list_prices(newpop):
    book = book_titled(newpop[0], "Street Fighter: Alpha - Volume 01")
    assert (book["i"], book["c"], book["f"]) == ("9788583620143", 19.9, 9.95)


def test_table_number_column_is_not_read_as_price(harpercollins):
    book = book_titled(harpercollins[0], "A esperança da Primavera")
    assert (book["c"], book["f"]) == (89.9, 44.95)


def test_stray_number_in_imprint_column_is_not_read_as_price(atma):
    book = book_titled(atma[0], "Baya, Kamu e Yaí")
    assert (book["c"], book["f"]) == (96.0, 48.0)


def test_author_cut_by_the_table_cell_is_completed_from_the_text(atma):
    book = book_titled(atma[0], "O corvo")
    assert book["a"] == "Edgar Allan Poe"


def test_distributor_keeps_the_real_imprint(atma):
    book = book_titled(atma[0], "O corvo")
    assert book["s"] == "VALER EDITORA"


def test_row_numbers_are_not_read_as_prices():
    catalog, _ = catalog_for("autentica.pdf", "Autêntica Editora")
    book = book_titled(catalog, "1461 dias na trincheira")
    assert (book["c"], book["f"]) == (79.8, 39.9)


def test_list_with_only_cover_price_and_percentage():
    catalog, _ = catalog_for("contraponto.pdf", "Contraponto")
    book = book_titled(catalog, "Alexandre o Grande")
    assert (book["c"], book["f"]) == (116.0, 58.0)


def test_whole_number_cover_price_next_to_decimal_fair_price():
    catalog, _ = catalog_for("ars_et_vita.pdf", "Ars et Vita")
    book = book_titled(catalog, "A bússola adúltera")
    assert (book["c"], book["f"]) == (58.0, 23.2)


def test_every_newpop_price_matches_the_pdf_text(newpop):
    catalog, parsed = newpop
    report = verify_prices(catalog, {0: parsed.plain_text})
    assert report.mismatch_count == 0


def test_verification_flags_a_wrong_price(newpop):
    catalog, parsed = newpop
    tampered = {**catalog, "livros": [dict(book_titled(catalog, "Street Fighter: Alpha - Volume 01"), f=1.23)]}
    report = verify_prices(tampered, {0: parsed.plain_text})
    assert report.mismatch_count == 1


def test_catalog_carries_event_name_and_period(newpop):
    assert newpop[0]["evento"] == {"edicao": "27-festa-do-livro-da-usp", "nome": "27 Festa do Livro da USP", "periodo": "26 e 30 de novembro"}


def test_url_with_access_token_is_never_published():
    assert safe_public_url("https://api.metabooks.com/api/v1/cover/9788562564932/m?access_token=abc") == ""


def test_credential_query_parameters_are_removed_from_shop_links():
    assert safe_public_url("https://loja.example.com/livro?id=7&token=segredo") == "https://loja.example.com/livro?id=7"


def test_cover_image_links_are_dropped():
    assert safe_public_url("https://fl-storage.bookinfometadados.com.br/uploads/book/first_cover/9788525431561.jpg") == ""


@pytest.mark.parametrize("imprint, repeats", [
    ("COMPANHIA DAS LETRA", True),
    ("Atma Editora L", True),
    ("NOVA FRONTEIRA / TRAMA", False),
    ("VALER EDITORA", False),
    ("EDITORA AUTORES ASSOCIADOS LTDA", True),
])
def test_imprint_redundancy(imprint, repeats):
    exhibitor = {"COMPANHIA DAS LETRA": "Companhia das Letras", "Atma Editora L": "Atma Editora", "NOVA FRONTEIRA / TRAMA": "Nova Fronteira",
                 "VALER EDITORA": "Atma Editora", "EDITORA AUTORES ASSOCIADOS LTDA": "Editora Autores Associados"}[imprint]
    assert imprint_repeats_exhibitor(imprint, exhibitor) is repeats


def test_prices_below_one_real_are_discarded():
    parsed = ParsedPriceList(
        books=[
            {"isbn": "9788539102211", "title": "Livro de verdade", "author": "", "imprint": "", "subject": "", "url": "", "cover_price": 72.0, "fair_price": 36.0},
            {"isbn": "9788539100001", "title": "Erro da planilha", "author": "", "imprint": "", "subject": "", "url": "", "cover_price": 0.1, "fair_price": 0.05},
        ],
        method="tabela",
        plain_text="",
    )
    publishers = [Publisher(name="Annablume", slug="", price_list_url="x", site="")]
    catalog = build_catalog(EVENT, publishers, {0: parsed}, "2026-10-02T00:00:00+00:00")
    assert [book["t"] for book in catalog["livros"]] == ["Livro de verdade"]


def test_same_content_ignores_generation_time(newpop):
    catalog, _ = newpop
    assert same_content(catalog, {**catalog, "geradoEm": "outro horário"})
