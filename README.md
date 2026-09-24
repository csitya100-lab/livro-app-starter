# Fábrica de livros-app — starter

Transforme um manuscrito em um **livro-app**: um web app de leitura para celular, instalável como
aplicativo, que funciona sem internet, sem login e sem coletar dados. Do mesmo conteúdo saem também um
**PDF** e um **EPUB**.

Este repositório é o ponto de partida: traz o motor de leitura, os scripts do pipeline, as regras de
trabalho (`CLAUDE.md`), a skill que orienta o agente e um livro de exemplo pronto para rodar.

O conteúdo dos livros publicados com esta fábrica não faz parte do repositório — só o método.

## O que você precisa

| Ferramenta | Para quê |
| --- | --- |
| [Node.js](https://nodejs.org) 20 ou mais novo | rodar e compilar o app |
| Python 3.10 ou mais novo | os scripts de `fabrica/` |
| [Claude Code](https://docs.claude.com/claude-code) | conversar com o agente que monta o livro |
| Google Chrome | necessário só para exportar o PDF |

## Começando em cinco passos

```bash
git clone <url-deste-repositorio> livro-app
cd livro-app/exemplo-livro
npm install
npm run dev
```

Abra a URL que o Vite mostrar. Você verá o livro de exemplo com sumário, busca, leitura em voz alta,
teste rápido, flashcards, calculadora e gráfico — os tipos de bloco que a casca sabe renderizar.

O quinto passo é abrir o Claude Code na raiz do repositório e pedir o seu título:

```
crie um título novo a partir do manuscrito em meu-livro/manuscrito/
```

A skill `fabrica-livro-app` assume dali: inventaria o manuscrito, converte em blocos, valida as
referências no PubMed, monta o `content/`, roda a validação e entrega o app rodando.

## Como o repositório é organizado

```
CLAUDE.md                          regras de esquema, editoriais e técnicas (o agente lê antes de tudo)
.claude/skills/fabrica-livro-app/  o passo a passo do pipeline
fabrica/
  md2book.py                       manuscrito.md  ->  content/book.json
  validate.py                      confere o content/ contra o que a casca renderiza
  eutils.py                        busca e formata referências Vancouver via PubMed
  exportar.py                      gera o PDF e o EPUB a partir do content/
exemplo-livro/                     título de demonstração (apague quando tiver o seu)
  manuscrito/manuscrito.md         a entrada
  refs/referencias.json            a lista de referências por capítulo
  content/                         book.json, theme.json e images/ — a fonte de verdade
  src/                             a casca: o motor de leitura, igual para todos os títulos
```

A ideia central: **a casca não sabe o nome do seu livro**. Ela lê `content/book.json` e
`content/theme.json` em tempo de execução. Criar um título novo é preencher um `content/` e copiar a
casca — não é programar.

## Os comandos do pipeline

```bash
python fabrica/md2book.py <slug>     # manuscrito -> content/book.json
python fabrica/validate.py <slug>    # precisa terminar com zero erros
python fabrica/exportar.py <slug>    # gera exportacoes/<slug>.pdf e .epub
cd <slug> && npm run dev             # app em modo de desenvolvimento
cd <slug> && npm run build           # build de produção
```

## Antes de publicar o seu livro

1. **Preencha o autor.** Em `<slug>/content/theme.json`, os campos `author.name` e
   `author.credentials` aparecem na capa, no PDF e no EPUB. Se você é médica ou médico, são o seu nome,
   CRM e RQE — nunca os de outra pessoa. Publicar material médico com identificação de terceiros é erro
   perante a Resolução CFM 2.336/2023.
2. **Troque o `storagePrefix`.** Ele precisa ser único por título; dois livros com o mesmo prefixo
   compartilham progresso e favoritos no mesmo navegador.
3. **Revise as referências.** O pipeline nunca inventa uma referência: o que não for confirmado no
   PubMed fica em `pendencias.md` esperando a sua decisão.
4. **Rode a validação e o build.** `python fabrica/validate.py <slug>` e, dentro do título,
   `npm run build && npx tsc --noEmit`.

## Licença

Código e scripts sob licença MIT (veja `LICENSE`). O livro de exemplo serve de demonstração e pode ser
apagado. O conteúdo que você escrever é seu, e a licença dele é decisão sua.
