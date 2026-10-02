from festa_do_livro.fair_site import HttpResponse, Publisher
from festa_do_livro.price_list_download import download_price_lists

PDF_BYTES = b"%PDF-1.7\n%conteudo de teste\n"


def publisher(name, url):
    return Publisher(name=name, slug=name.lower(), price_list_url=url, site="")


def test_downloads_each_price_list_once_into_the_cache(tmp_path):
    requested = []

    def fetch(url):
        requested.append(url)
        return HttpResponse(200, "application/pdf", PDF_BYTES)

    publishers = [publisher("NewPOP", "https://example.com/a.pdf"), publisher("L&PM", "https://example.com/b.pdf")]

    first = download_price_lists(publishers, tmp_path, fetch)
    second = download_price_lists(publishers, tmp_path, fetch)

    assert [result.path.read_bytes() for result in first] == [PDF_BYTES, PDF_BYTES]
    assert len(requested) == 2
    assert [result.path for result in second] == [result.path for result in first]


def test_publisher_without_list_is_reported_not_downloaded(tmp_path):
    results = download_price_lists([publisher("Pontes", "")], tmp_path, lambda url: None)

    assert results[0].path is None
    assert results[0].problem == "sem lista de preços"


def test_non_pdf_response_is_reported_without_stopping_the_others(tmp_path):
    def fetch(url):
        if "quebrado" in url:
            return HttpResponse(404, "text/html", b"<html>nao encontrado</html>")
        return HttpResponse(200, "application/pdf", PDF_BYTES)

    results = download_price_lists(
        [publisher("Quebrada", "https://example.com/quebrado.pdf"), publisher("Boa", "https://example.com/ok.pdf")],
        tmp_path,
        fetch,
    )

    assert results[0].path is None and "404" in results[0].problem
    assert results[1].path is not None
