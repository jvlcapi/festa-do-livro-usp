import re
import unicodedata


def without_accents_lowercase(text: str) -> str:
    return unicodedata.normalize("NFD", text or "").encode("ascii", "ignore").decode().lower()


def collapse_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()
