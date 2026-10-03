# Plano de implementação

Objetivo: gerar o catálogo da Festa do Livro da USP a partir de qualquer edição (sem link fixo no código), publicar esse catálogo numa página com listas pessoais e privadas, e deixar tudo pronto para o dia em que a lista da próxima edição sair.

## Etapa 1: Coletor configurável por edição
**Goal**: código que descobre a edição (automática pela página inicial do site, ou fixada em `settings.json`), lista as editoras pela API e baixa os PDFs de preço.
**Success Criteria**: `python -m festa_do_livro download` com `"edition": "auto"` encontra `27-festa-do-livro-da-usp` hoje; trocar para outra edição é mudar uma linha.
**Tests**: detecção da edição a partir de HTML salvo; leitura de `settings.json` (auto e fixa); paginação da API de editoras com respostas salvas; edição inexistente gera erro claro.
**Status**: Complete

## Etapa 2: Leitura dos PDFs, conferência e catálogo
**Goal**: portar o leitor validado (tabelas + posição do texto), a conferência de preços e a montagem do `catalogo.json` com os dados do evento (nome, datas).
**Success Criteria**: rodar sobre os PDFs da 27ª edição reproduz o catálogo já validado (34.771 livros) e o relatório aponta só as divergências conhecidas.
**Tests**: regressões reais com PDFs de amostra (HarperCollins "Mesa" lida como preço, Atma, Contraponto só com %, Ars et Vita com capa inteira); URLs com token removidas; preço abaixo de R$ 1 descartado.
**Status**: Complete

## Etapa 3: GitHub Action e segredos
**Goal**: workflow que roda sob demanda e diariamente, gera catálogo + relatório e faz commit só quando algo mudou.
**Success Criteria**: execução manual no GitHub termina verde e gera `data/<edição>/catalogo.json`; nenhuma chave no repositório (só `GITHUB_TOKEN` automático; futuras chaves via Actions secrets).
**Tests**: execução manual do workflow; checagem de que `.env` e caches estão no `.gitignore`.
**Status**: Complete

## Etapa 4: Site público com listas no aparelho
**Goal**: site estático no GitHub Pages, aberto a qualquer pessoa sem conta nem convite, que lê nome/datas da edição e o catálogo publicados junto, guarda a lista no navegador por edição, compartilha a lista por link e funciona sem internet depois da primeira visita. (Substitui a página no Claude Artifact, que exigia conta no claude.ai e convite de Colaborador.)
**Success Criteria**: o workflow publica o site com o catálogo da 27ª edição; no site publicado dá para buscar, adicionar, remover, definir orçamento, gerar o link e abrir o link em outro navegador com os mesmos livros.
**Tests**: montagem do site com a edição atual (`tests/test_site_assembly.py`); checagem de sintaxe do script; teste manual no endereço publicado.
**Status**: Complete (falta só um teste num celular de verdade, issue #16)

## Etapa 5: Roteiro do dia do lançamento
**Goal**: README com o passo a passo para quando a nova edição sair (detectar, rodar, conferir relatório, publicar) e liberação do repositório como público.
**Success Criteria**: dá para seguir o roteiro sem consultar o histórico da conversa.
**Tests**: ensaio do roteiro com a 27ª edição fixada em `settings.json`.
**Status**: In Progress (README pronto; falta o dia do lançamento)
