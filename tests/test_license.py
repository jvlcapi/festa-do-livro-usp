"""The credit required by the license must travel with the code and with every copy of the site."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_NOTICE = "Required Notice: Copyright 2026 João Vitor Lopes Capi (https://github.com/jvlcapi)"
LICENSE_URL = "https://polyformproject.org/licenses/noncommercial/1.0.0"


def test_license_file_starts_with_the_required_notice():
    assert (ROOT / "LICENSE.md").read_text().splitlines()[0] == REQUIRED_NOTICE


def test_license_file_keeps_the_official_terms():
    text = (ROOT / "LICENSE.md").read_text()
    assert "# PolyForm Noncommercial License 1.0.0" in text and LICENSE_URL in text


def test_published_page_carries_the_notice_and_the_license():
    page = (ROOT / "site" / "index.html").read_text()
    assert REQUIRED_NOTICE in page and LICENSE_URL in page
