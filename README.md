# Festa do Livro da USP: catálogo e listas

**Site: https://jvlcapi.github.io/festa-do-livro-usp/**

Gera o catálogo de preços da [Festa do Livro da USP](https://festadolivro.edusp.com.br) a partir das listas que cada editora publica no site, e publica um site aberto onde qualquer pessoa monta a própria lista de compras: busca em todas as editoras, total na feira, economia sobre o preço de capa, orçamento e compartilhamento por link. Projeto independente, não oficial da Edusp.

Nada da edição fica fixo no código. Quando sair a lista de um ano novo, o coletor descobre a edição sozinho (ou recebe o identificador), baixa os PDFs, lê, confere os preços, gera um catálogo novo e publica o site, tudo pelo GitHub Actions.

## Como funciona

```
site da Festa (API pública + PDFs das editoras)
        │  python -m festa_do_livro build   (local ou GitHub Actions)
        ▼
data/<edição>/catalogo.json   ← livros, preços, editoras
data/<edição>/edicao.json     ← nome e datas da edição
data/<edição>/relatorio.md    ← conferência dos preços contra os PDFs
        │  python -m festa_do_livro assemble-site → _site/
        ▼
GitHub Pages: site/index.html + catalogo.json + edicao.json
        │
        ▼
navegador de cada pessoa: busca, lista e totais (lista salva no próprio aparelho)
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

- **Atualizar catálogo** (`atualizar-catalogo.yml`): roda pelo botão *Run workflow* (com a edição opcional) e todo dia às 6h de Brasília de setembro a dezembro. Roda os testes, gera catálogo e relatório, mostra o relatório no resumo da execução e, se algo mudou, faz commit e publica o site.
- **Publicar site** (`publicar-site.yml`): monta `_site/` com a edição atual de `data/edicao-atual.json` e publica no GitHub Pages. Roda também quando `site/` ou os dados mudam por push.
- **Testes** (`testes.yml`): em todo push e pull request.

## O site

- Estático, sem servidor nem conta: `site/index.html` busca `edicao.json` e `catalogo.json` e faz tudo no navegador.
- **Lista**: salva no `localStorage` do navegador, separada por edição. Ao entrar uma edição nova, a lista recomeça e as antigas ficam para consulta. Quando o catálogo muda, os preços dos livros da lista são atualizados.
- **Compartilhar**: gera um link com a edição, um nome opcional e os identificadores dos livros no fragmento (`#lista=...`), que o navegador não envia ao servidor. Quem abre vê a lista com os preços atuais e pode copiar os livros para a dela.
- **Sem internet**: `site/sw.js` guarda o site e o catálogo no aparelho na primeira visita (rede primeiro, cache como reserva), para funcionar dentro da tenda da Festa.

Para ver localmente: `python -m festa_do_livro assemble-site` e depois `python -m http.server 8765 --bind 127.0.0.1 --directory _site`.

## Segredos

Nenhuma chave é necessária: o site da Festa e a API são públicos, o commit automático usa o `GITHUB_TOKEN` que o GitHub gera em cada execução e a publicação no Pages usa o token temporário do próprio GitHub (OIDC). O repositório tem *secret scanning* e *push protection* ligados. Se um dia for preciso uma chave (por exemplo, para notificações):

1. Cadastre em *Settings → Secrets and variables → Actions*.
2. Passe para o passo do workflow como `env: NOME: ${{ secrets.NOME }}` e leia com `os.environ` no código.
3. Para uso local, coloque num `.env` (já ignorado pelo Git) e nunca em `settings.json`.

O teste `tests/test_repository_hygiene.py` falha se algum arquivo versionado tiver padrão de token ou chave, e confere que `.env` e `cache/` estão ignorados. O catálogo também descarta links com parâmetros de credencial que vêm nas listas das editoras.

## Roteiro do dia em que a lista sair

1. Confirme a edição: `python -m festa_do_livro detect-edition` (ou veja a página de editoras no site da Festa).
2. Rode o workflow **Atualizar catálogo** (vazio = `auto`, ou informe a edição).
3. Abra o resumo da execução e leia o relatório: total de livros, listas não lidas e divergências por editora. Editora com formato novo aparece com 0 livros ou muitas divergências.
4. Se precisar de ajuste no leitor, corrija, adicione um teste com o PDF da editora em `tests/fixtures/price_lists/` e rode de novo.
5. Abra o site e confira que o nome e as datas da nova edição aparecem no topo.

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
  site_assembly.py            monta a pasta publicada no GitHub Pages
site/                         site público (página, cache offline, ícone, manifesto)
data/                         catálogos gerados (um diretório por edição)
```
