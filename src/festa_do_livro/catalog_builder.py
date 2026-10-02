"""Turns the parsed price lists into the catalog file the web page reads."""
import collections
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .fair_site import EventDetails, Publisher
from .pdf_reading import extract_plain_text, extract_table_rows, extract_text_spans
from .position_parser import parse_by_position
from .table_parser import parse_table_rows

URL_IN_TEXT = re.compile(r"https?://\S+")
CREDENTIAL_QUERY_KEYS = {"token", "access_token", "accesstoken", "key", "apikey", "api_key", "signature", "sig", "auth", "password", "secret"}
IMAGE_HOSTS_AND_PATHS = ("bookinfometadados", "metabooks.com/api", "/cover/")
COMPANY_SUFFIX_WORDS = {"e", "livraria", "ltda", "me", "eireli", "distribuidora"}
MONEY_IN_TEXT = re.compile(r"(R\$\s*)?\d{1,3}(\.\d{3})*,\d{2}|\d+\.\d{2}\b")


@dataclass(frozen=True)
class ParsedPriceList:
    books: list[dict]
    method: str
    plain_text: str


def tidy(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip(" ;,-")


def tidy_subject(text: str) -> str:
    text = tidy(text)
    if text.isupper():
        text = text.capitalize()
    return text[:60]


def clean_parsed_book(book: dict) -> dict:
    book = dict(book)
    for field in ("title", "author", "imprint", "subject", "url"):
        book[field] = re.sub(r"\s+", " ", book.get(field) or "").strip()
    for field in ("subject", "title", "author"):
        match = URL_IN_TEXT.search(book[field])
        if match:
            if not book["url"]:
                book["url"] = match.group(0)
            book[field] = URL_IN_TEXT.sub("", book[field]).strip()
    if book["url"] and not book["url"].startswith("http"):
        book["url"] = "" if " " in book["url"] or "." not in book["url"] else "https://" + book["url"].lstrip("/")
    book["url"] = book["url"].replace(" ", "")
    book["title"] = re.sub(r"^(ean:?|isbn13:?)\s*\d+\s*", "", book["title"], flags=re.I).strip(" -")
    return book


def fill_missing_isbns_from_text(books: list[dict], plain_text: str) -> None:
    flat_text = re.sub(r"\s+", " ", plain_text)
    for book in books:
        if book["isbn"] or len(book["title"]) < 4:
            continue
        position = flat_text.find(book["title"][:40])
        if position < 0:
            continue
        match = re.search(r"(97[89][\d\-]{10,14})\s?$", flat_text[max(0, position - 22):position])
        if match:
            digits = re.sub(r"\D", "", match.group(1))
            if len(digits) == 13:
                book["isbn"] = digits


def parse_price_list(pdf_path: Path) -> ParsedPriceList:
    """Runs both readers and keeps the one that found more complete books."""
    try:
        from_tables = parse_table_rows(extract_table_rows(pdf_path))
    except Exception:
        from_tables = []
    try:
        from_positions = parse_by_position(extract_text_spans(pdf_path))
    except Exception:
        from_positions = []
    complete = lambda books: sum(1 for book in books if book["title"] and book["fair_price"])
    if complete(from_tables) >= 0.95 * complete(from_positions) and complete(from_tables) > 0:
        chosen, method = from_tables, "tabela"
    else:
        chosen, method = from_positions, "posição do texto"
    books = [clean_parsed_book(book) for book in chosen if book["title"] and book["fair_price"]]
    books = [book for book in books if book["title"]]
    plain_text = extract_plain_text(pdf_path)
    fill_missing_isbns_from_text(books, plain_text)
    return ParsedPriceList(books=books, method=method, plain_text=plain_text)


def safe_public_url(url: str) -> str:
    """Drops cover-image links and any query parameter that carries a credential."""
    if not url or len(url) < 12:
        return ""
    lowered = url.lower()
    if any(marker in lowered for marker in IMAGE_HOSTS_AND_PATHS) or lowered.split("?")[0].endswith((".jp", ".jpg", ".jpeg", ".png", ".webp")):
        return ""
    parts = urlsplit(url)
    kept_query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key.lower() not in CREDENTIAL_QUERY_KEYS]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept_query), parts.fragment))


def stable_book_id(isbn: str, exhibitor_name: str, title: str) -> str:
    return isbn or "x" + hashlib.md5((exhibitor_name + title).encode()).hexdigest()[:12]


def without_stray_letters(imprint: str) -> str:
    """Cells often swallow one letter of the neighbouring cell: "oAnita Garibaldi", "MATRIX N"."""
    imprint = re.sub(r"^[a-z]\s*(?=[A-ZÀ-Ý0-9])", "", (imprint or "").strip())
    return re.sub(r"\s+[A-Za-z]$", "", imprint).strip()


def imprint_repeats_exhibitor(imprint: str, exhibitor_name: str) -> bool:
    """True when the imprint adds nothing to the exhibitor name (equal, cut short, or followed only by noise)."""
    imprint_key = without_stray_letters(imprint).lower()
    exhibitor_key = exhibitor_name.lower()
    if not imprint_key:
        return True
    if exhibitor_key.startswith(imprint_key):
        return True
    if imprint_key.startswith(exhibitor_key):
        remainder = imprint_key[len(exhibitor_key):].strip()
        only_company_suffixes = all(word in COMPANY_SUFFIX_WORDS for word in re.findall(r"[a-zà-ý]+", remainder))
        return not re.search(r"[a-zà-ý]{2,}", remainder) or remainder == exhibitor_key or only_company_suffixes
    return False


def catalog_books(publishers: list[Publisher], parsed_by_index: dict[int, ParsedPriceList]) -> list[dict]:
    books = []
    seen = set()
    for publisher_index, parsed in sorted(parsed_by_index.items()):
        exhibitor_name = publishers[publisher_index].name
        for parsed_book in parsed.books:
            title = tidy(parsed_book["title"])
            if not title or re.fullmatch(r"[\d\s\-]+", title):
                continue
            book_id = stable_book_id(parsed_book["isbn"], exhibitor_name, title)
            if (book_id, publisher_index) in seen:
                continue
            seen.add((book_id, publisher_index))
            book = {
                "i": book_id, "t": title, "a": tidy(parsed_book["author"]), "s": tidy(parsed_book["imprint"]),
                "g": tidy_subject(parsed_book["subject"]), "c": parsed_book["cover_price"], "f": parsed_book["fair_price"], "x": publisher_index,
            }
            url = safe_public_url(parsed_book["url"])
            if url:
                book["u"] = url
            if not book["a"]:
                del book["a"]
            if not book["s"] or book["s"].lower() == exhibitor_name.lower() or re.fullmatch(r"\d+", book["s"]):
                book.pop("s", None)
            if not book["g"]:
                del book["g"]
            if book["c"] is None or book["c"] < book["f"]:
                book.pop("c")
            if book["f"] < 1:
                continue
            books.append(book)
    return books


def text_after_isbn_by_line(plain_text: str) -> dict[str, str]:
    lines = {}
    for line in plain_text.split("\n"):
        match = re.match(r"\s*(?:EAN:?\s*|ISBN13:\s*)?(97[89][\d\-]{10,16})\s*(.*)", line)
        if match:
            lines.setdefault(re.sub(r"\D", "", match.group(1))[:13], match.group(2))
    return lines


def repair_truncated_names(books: list[dict], publishers: list[Publisher], parsed_by_index: dict[int, ParsedPriceList]) -> int:
    """Table cells cut long author and imprint names; the raw text line still has them whole."""
    line_cache: dict[int, dict[str, str]] = {}
    repaired = 0
    for book in books:
        if not book["i"].isdigit() or "a" not in book or book["x"] not in parsed_by_index:
            continue
        if book["x"] not in line_cache:
            line_cache[book["x"]] = text_after_isbn_by_line(parsed_by_index[book["x"]].plain_text)
        line = line_cache[book["x"]].get(book["i"])
        if not line or not line.startswith(book["t"]):
            continue
        after_title = line[len(book["t"]):]
        money = MONEY_IN_TEXT.search(after_title)
        segment = (after_title[:money.start()] if money else after_title).strip()
        author = book["a"]
        if len(author) < 4 or not segment.startswith(author) or len(segment) <= len(author):
            continue

        exhibitor_name = publishers[book["x"]].name
        cut = None
        for name in filter(None, [without_stray_letters(book.get("s", "")), exhibitor_name]):
            position = segment.lower().find(name.lower()[:10], len(author) - 2)
            if position > 0:
                cut = position if cut is None else min(cut, position)
        subject_start = (book.get("g") or "").lower()[:8]
        if subject_start:
            position = segment.lower().find(subject_start, len(author) - 2)
            if position > 0:
                cut = position if cut is None else min(cut, position)

        full_author = segment[:cut] if cut is not None else segment
        full_author = re.sub(r"(\s+\d+)+\s*$", "", full_author)
        full_author = re.sub(r"\s+[A-Za-z]$", "", full_author.strip()).strip(" ,;")
        publisher_words = {word.lower() for word in re.findall(r"\w+", exhibitor_name + " " + (book.get("s") or "")) if len(word) >= 3}
        tokens = full_author.split()
        while len(tokens) > 1 and tokens[-1].lower().strip(".,;") in publisher_words and tokens[-1].lower() not in author.lower().split():
            tokens.pop()
        full_author = re.sub(r"(?<=[a-zà-ú])\d+$", "", " ".join(tokens))
        if len(author) < len(full_author) < len(author) + 40:
            book["a"] = full_author
            repaired += 1

        if cut is not None and book.get("s"):
            rest = re.sub(r"(\s+\d+(?:[.,]\d+)?)+\s*$", "", segment[cut:]).strip(" ,;")
            truncated = without_stray_letters(book["s"])
            cut_mid_word = len(rest) > len(truncated) and rest[len(truncated)].isalnum()
            if rest.lower().startswith(truncated.lower()) and cut_mid_word and len(rest) <= len(truncated) + 15:
                book["s"] = rest
    normalize_imprints(books, publishers)
    return repaired


def normalize_imprints(books: list[dict], publishers: list[Publisher]) -> None:
    for book in books:
        if book.get("s"):
            book["s"] = without_stray_letters(book["s"])

    frequent_imprints = collections.defaultdict(collections.Counter)
    for book in books:
        if book.get("s"):
            frequent_imprints[book["x"]][book["s"]] += 1

    for book in books:
        imprint = book.get("s")
        if not imprint:
            continue
        exhibitor_name = publishers[book["x"]].name
        # A common imprint cut short ("VALER EDITOR") or with a glued extra first letter ("SCOMPANHIA DAS LETRAS").
        own_count = frequent_imprints[book["x"]][imprint]
        for candidate, count in frequent_imprints[book["x"]].most_common():
            if count < 3 or count <= own_count or candidate == imprint:
                continue
            if candidate.lower().startswith(imprint.lower()) or (len(imprint) > 1 and candidate.lower().startswith(imprint[1:].lower())):
                imprint = candidate
                break
        if not re.search(r"[A-Za-zÀ-ÿ]{2,}", imprint) or imprint_repeats_exhibitor(imprint, exhibitor_name) or imprint_repeats_exhibitor(imprint[1:], exhibitor_name):
            book.pop("s")
        else:
            book["s"] = imprint


def build_catalog(event: EventDetails, publishers: list[Publisher], parsed_by_index: dict[int, ParsedPriceList], generated_at: str) -> dict:
    books = catalog_books(publishers, parsed_by_index)
    repair_truncated_names(books, publishers, parsed_by_index)
    return {
        "evento": {"edicao": event.edition, "nome": event.name, "periodo": event.period},
        "geradoEm": generated_at,
        "expositores": [{"nome": publisher.name, "site": publisher.site} for publisher in publishers],
        "livros": books,
    }


def same_content(first: dict, second: dict) -> bool:
    keys = ("evento", "expositores", "livros")
    return all(first.get(key) == second.get(key) for key in keys)
