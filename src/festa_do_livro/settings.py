import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

EDITION_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class Settings:
    edition: str
    site_base_url: str


def load_settings(settings_path: Path, environment=None) -> Settings:
    environment = os.environ if environment is None else environment
    raw = json.loads(Path(settings_path).read_text())
    edition = (environment.get("FESTA_EDITION") or raw.get("edition") or "auto").strip()
    site_base_url = raw.get("site_base_url", "").rstrip("/")
    if edition != "auto" and not EDITION_PATTERN.match(edition):
        raise ValueError(
            f'edition inválida em {settings_path}: "{edition}". Use "auto" ou o identificador do site, '
            'por exemplo "28-festa-do-livro-da-usp".'
        )
    if not site_base_url.startswith("https://"):
        raise ValueError(f"site_base_url precisa começar com https:// em {settings_path}")
    return Settings(edition=edition, site_base_url=site_base_url)
