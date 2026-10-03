import json
from pathlib import Path

from festa_do_livro.site_assembly import assemble_site

ROOT = Path(__file__).resolve().parents[1]


def write_edition(data_directory: Path, edition: str):
    edition_directory = data_directory / edition
    edition_directory.mkdir(parents=True)
    (edition_directory / "catalogo.json").write_text(json.dumps({"livros": [], "expositores": []}))
    (edition_directory / "edicao.json").write_text(json.dumps({"edicao": edition, "nome": "28 Festa do Livro da USP", "periodo": ""}))
    (data_directory / "edicao-atual.json").write_text(json.dumps({
        "edicao": edition, "catalogo": f"{edition}/catalogo.json", "edicaoInfo": f"{edition}/edicao.json", "relatorio": f"{edition}/relatorio.md",
    }))


def test_site_gets_the_current_edition_files(tmp_path):
    write_edition(tmp_path / "data", "28-festa-do-livro-da-usp")

    assemble_site(ROOT / "site", tmp_path / "data", tmp_path / "_site")

    published = json.loads((tmp_path / "_site" / "edicao.json").read_text())
    assert published["edicao"] == "28-festa-do-livro-da-usp"


def test_site_contains_page_offline_worker_and_catalog(tmp_path):
    write_edition(tmp_path / "data", "28-festa-do-livro-da-usp")

    assemble_site(ROOT / "site", tmp_path / "data", tmp_path / "_site")

    names = sorted(path.name for path in (tmp_path / "_site").iterdir())
    assert names == [".nojekyll", "catalogo.json", "edicao.json", "icon.svg", "index.html", "manifest.webmanifest", "sw.js"]


def test_site_page_has_no_claude_artifact_dependency():
    page = (ROOT / "site" / "index.html").read_text()
    assert "claude.use" not in page and "claude?.use" not in page
