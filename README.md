# Festa do Livro da USP: catálogo e listas

Gera o catálogo de preços da [Festa do Livro da USP](https://festadolivro.edusp.com.br) a partir das listas que cada editora publica no site, e alimenta uma página onde cada pessoa monta a própria lista de compras.

Nada da edição fica fixo no código. Quando sair a lista de um ano novo, o coletor descobre a edição sozinho (ou recebe o identificador), baixa os PDFs, lê, confere os preços e gera um catálogo novo; a página só precisa receber esse arquivo.

## Como funciona

```
site da Festa (API pública + PDFs das editoras)
        │  python -m festa_do_livro build   (local ou GitHub Actions)
        ▼
data/<edição>/catalogo.json   ← livros, preços, editoras
data/<edição>/edicao.json     ← nome e datas da edição
data/<edição>/relatorio.md    ← conferência dos preços contra os PDFs
        │  publicado junto com web/index.html
        ▼
página (Claude Artifact) → listas privadas por pessoa e por edição
```

- **Edição**: `settings.json` tem `"edition": "auto"`, que usa a edição declarada na página inicial do site. Para fixar uma edição, troque por exemplo para `"28-festa-do-livro-da-usp"` ou passe `FESTA_EDITION`.
- **Leitura dos PDFs**: cada lista é lida de dois jeitos (células da tabela e posição do texto) e fica o resultado mais completo. Nomes cortados pela célula são completados pelo texto do PDF.
- **Conferência**: cada preço de capa e de feira precisa aparecer na linha do mesmo ISBN no PDF. O que não bate vai para o relatório.

## Rodar localmente

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/pytest -q
.venv/bin/python -m festa_do_livro detect-edition
.venv/bin/python -m festa_do_livro build
```

O `build` baixa os PDFs para `cache/<edição>/` (fora do Git) e escreve em `data/`. Para outra edição: `--edition 28-festa-do-livro-da-usp`.

## GitHub Actions

- **Atualizar catálogo** (`.github/workflows/atualizar-catalogo.yml`): roda pelo botão *Run workflow* (com a edição opcional) e todo dia às 6h de Brasília de setembro a dezembro. Roda os testes, gera catálogo e relatório, mostra o relatório no resumo da execução e faz commit só quando algo mudou.
- **Testes** (`testes.yml`): em todo push e pull request.

## Publicar na página

A página é um Claude Artifact e não consegue acessar outros sites; por isso o catálogo é publicado junto com ela. Peça ao Claude: *"atualiza o catálogo da Festa do Livro"*. Ele publica:

| Arquivo publicado | Origem |
|---|---|
| página | `web/index.html` |
| `catalogo.json` | `data/<edição atual>/catalogo.json` |
| `edicao.json` | `data/<edição atual>/edicao.json` |

com as regras de acesso de `web/capabilities.json`. A edição atual está em `data/edicao-atual.json`. O link da página fica fora deste repositório.

## Dados e privacidade

| Caminho no banco da página | Quem lê | Quem escreve |
|---|---|---|
| `data/users/<pessoa>/<edição>` (lista) | só a própria pessoa | só a própria pessoa |
| `compartilhadas/<pessoa>` (cópia compartilhada) | todos com o link | só a própria pessoa |

Compartilhar vale para todos que têm o link: as regras do banco são por nível de acesso, então não existe compartilhamento seguro com uma pessoa específica. Para montar uma lista, a pessoa precisa de acesso de Colaborador.

## Segredos

Hoje nenhuma chave é necessária: o site e a API são públicos e o commit automático usa o `GITHUB_TOKEN` que o GitHub gera em cada execução. Se um dia for preciso uma chave (por exemplo, para notificações):

1. Cadastre em *Settings → Secrets and variables → Actions*.
2. Passe para o passo do workflow como `env: NOME: ${{ secrets.NOME }}` e leia com `os.environ` no código.
3. Para uso local, coloque num `.env` (já ignorado pelo Git) e nunca em `settings.json`.

O teste `tests/test_repository_hygiene.py` falha se algum arquivo versionado tiver padrão de token ou chave, e confere que `.env` e `cache/` estão ignorados. O catálogo também descarta links com parâmetros de credencial que vêm nas listas das editoras.

## Roteiro do dia em que a lista sair

1. Confirme a edição: `python -m festa_do_livro detect-edition` (ou veja a página de editoras no site).
2. Rode o workflow **Atualizar catálogo** (vazio = `auto`, ou informe a edição).
3. Abra o resumo da execução e leia o relatório: total de livros, listas não lidas e divergências por editora. Editora com formato novo aparece com 0 livros ou muitas divergências.
4. Se precisar de ajuste no leitor, corrija, adicione um teste com o PDF da editora em `tests/fixtures/price_lists/` e rode de novo.
5. Peça ao Claude para publicar o catálogo novo na página e confira que o nome e as datas da edição aparecem.
6. Com tudo funcionando, siga a issue *Tornar o repositório público*.

## Estrutura

```
settings.json                 edição ("auto" ou identificador) e endereço do site
src/festa_do_livro/
  fair_site.py                página inicial, API do evento e das editoras
  price_list_download.py      download dos PDFs com cache
  pdf_reading.py              extração de tabelas, texto e posições
  table_parser.py             leitor por células da tabela
  position_parser.py          leitor por posição do texto
  catalog_builder.py          limpeza, nomes completos, links seguros, catalogo.json
  price_verification.py       conferência de preços e relatório
web/index.html                página das listas
web/capabilities.json         regras de acesso do banco da página
data/                         catálogos gerados (um diretório por edição)
```
