import logging
from pathlib import Path

import pymupdf
from pypdf import PdfReader

logging.getLogger("pypdf").setLevel(logging.ERROR)


def extract_table_rows(pdf_path: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    with pymupdf.open(pdf_path) as document:
        for page in document:
            for table in page.find_tables().tables:
                for row in table.extract():
                    rows.append([(cell or "").replace("\n", " ").strip() for cell in row])
    return rows


def extract_plain_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def extract_text_spans(pdf_path: Path) -> list[list[dict]]:
    """Every text span of every page, with horizontal bounds and vertical center."""
    pages: list[list[dict]] = []
    with pymupdf.open(pdf_path) as document:
        for page in document:
            spans = []
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if not text:
                            continue
                        left, top, right, bottom = span["bbox"]
                        spans.append({"left": left, "right": right, "middle": (top + bottom) / 2, "text": text})
            pages.append(merge_adjacent_spans(spans))
    return pages


def merge_adjacent_spans(spans: list[dict]) -> list[dict]:
    spans = sorted(spans, key=lambda span: (round(span["middle"]), span["left"]))
    merged: list[dict] = []
    for span in spans:
        previous = merged[-1] if merged else None
        gap = span["left"] - previous["right"] if previous else None
        if previous and abs(previous["middle"] - span["middle"]) < 1.5 and 0 <= gap < 2.5:
            previous["text"] += ("" if gap < 0.8 else " ") + span["text"]
            previous["right"] = span["right"]
        else:
            merged.append(dict(span))
    return merged
