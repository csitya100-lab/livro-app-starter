---
name: fabrica-livro-app
description: Transforma um manuscrito (Markdown ou DOCX) em um livro-app pronto para testar no navegador, dentro do repositório da fábrica de livros-app. Use SEMPRE que o autor pedir para criar um novo título ou livro-app, converter ou "montar o app" de um manuscrito, verificar ou inventariar uma pasta de título nova, gerar ou validar content/book.json e theme.json, validar referências de capítulos no PubMed, montar a lista Vancouver, copiar a casca para um título novo, ou propagar uma melhoria da casca aos demais títulos. Acione mesmo que ele diga apenas "verifique o conteúdo", "vê o que falta nesse livro" ou "segue com o título X" quando houver uma pasta de título no repositório. Não usar para slides, posts ou análise crítica de artigos.
---

# Fábrica de livro-app

Um livro-app é um web app de leitura para celular, instalável como PWA, sem servidor e sem
coleta de dados. O motor de leitura (a casca em `src/`) é o mesmo para todos os títulos e lê
tudo de `content/`. Portanto, fazer um título novo é produzir três coisas bem-formadas:
`content/book.json`, `content/theme.json` e `content/images/`. O resto é cópia.

As regras de esquema, editoriais e técnicas estão no `CLAUDE.md` da raiz. Esta skill não as
repete: descreve a ordem de trabalho, o que checar em cada etapa e o que entregar ao autor.
Presuma que o autor não edita código nem JSON. Ele descreve o que quer e recebe algo para testar
no navegador.

## Onde estão os scripts e a casca

Duas situações, e a diferença é só o caminho dos arquivos.

**Repositório clonado** — tudo está na raiz: `fabrica/`, o `CLAUDE.md` com as regras e o título de
exemplo em `exemplo-livro/`. Trabalhe ali mesmo.

**Skill vinda do plugin** — o autor está numa pasta qualquer, sem a fábrica. Os arquivos ficam em
`${CLAUDE_PLUGIN_ROOT}`, que é somente leitura:

- scripts: `${CLAUDE_PLUGIN_ROOT}/fabrica/md2book.py`, `validate.py`, `eutils.py`, `exportar.py`;
- casca, `public/` e modelo de `theme.json`: `${CLAUDE_PLUGIN_ROOT}/exemplo-livro/`;
- regras de esquema e editoriais: `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md`.

No primeiro título feito por essa via, copie `CLAUDE.md` para a pasta de trabalho do autor e crie
`<slug>/` ali com a casca do exemplo. Nunca escreva dentro de `${CLAUDE_PLUGIN_ROOT}`.

## Entradas e saídas

Entra: uma pasta `<slug>/manuscrito/` com um ou mais `.md` (ou `.docx`), figuras e, se houver,
um briefing (público, tom, cores). Sai: `<slug>/content/` validado, a casca copiada, o app
rodando em `npm run dev` e um `<slug>/pendencias.md` com tudo o que não foi possível resolver.

## Etapa 0 — Inventário do manuscrito

Antes de converter, leia o manuscrito inteiro e responda ao autor em uma lista curta:

- Quantos headings de nível 1 há e se cada um é um capítulo numerado ("# Capítulo 3 — ...")
  ou uma abertura sem número (Apresentação, Prefácio). Isso define a estrutura do sumário.
- Se existe divisão em partes. O campo `part` é obrigatório em cada capítulo. Se o manuscrito
  não traz "Parte I", "Parte II", pergunte ao autor como agrupar; não invente.
- Figuras referenciadas versus figuras entregues. Liste as que faltam pelo nome.
- Estado das referências: já em Vancouver, apenas "Autor ano", ou placeholders.
- Frases de bastidor e termos banidos pelo `CLAUDE.md`.
- Se o texto anuncia partes ou capítulos que ainda não estão na pasta.

Esse inventário é o que permite ao autor decidir se segue agora ou espera material. Nunca
altere o manuscrito nesta etapa.

## Etapa 1 — Conversão em blocos tipados

`python fabrica/md2book.py <slug>` faz a conversão. As regras de mapeamento, todas espelhadas
em `src/content/types.ts` e em `fabrica/validate.py`:

- Cada `# ` vira um capítulo. "Capítulo N — Título" dá `number: N` e `title`; um `# ` sem
  número (Apresentação, Prefácio) dá `number: null` e `part: "Abertura"`.
- `id` é o slug `capitulo-N-titulo-sem-acentos`; para abertura, o slug do título (`prefacio`).
- `## ` vira bloco `h2`, `### ` vira `h3`, parágrafo vira `p`. Não junte nem quebre parágrafos.
- `![Figura 2.1 — Legenda](images/figura-2-1.png)` vira `{"type":"image","key":"figura-2-1.png",
  "caption":"Figura 2.1 — Legenda"}`. A chave é só o nome do arquivo, que deve existir em
  `content/images/`. Figuras são numeradas na ordem em que aparecem.
- Tabelas Markdown viram `{"type":"table","rows":[[...],[...]]}`, primeira linha como cabeçalho.
- `![Legenda](videos/x.mp4)` vira `{"type":"video",...}`; o pôster sai de `images/poster-x.jpg` quando
  esse arquivo existe. Gere o pôster com `ffmpeg -ss 2 -i <vídeo> -frames:v 1 -vf scale=540:-1 <jpg>`.
- Blocos interativos entram no manuscrito como cerca com o tipo e um JSON dentro (crases triplas
  seguidas de quiz, flashcard, calc ou chart) e devem ficar antes do `## Referências` do capítulo.
  O conteúdo vem do texto já aprovado do livro, nunca de fonte externa, e vai para `pendencias.md`
  para revisão do autor.
- `> frase` vira o destaque do capítulo. A frase precisa aparecer literalmente no texto (compare
  ignorando as marcas de citação `[n]`); um destaque por capítulo, colocado no meio, quebra o texto corrido.

## Ritmo da leitura

Texto corrido demais deixa o livro monótono. Metas por título, medidas no `book.json`: ao menos 12% dos
blocos visuais ou interativos, e nenhum capítulo com mais de cinco parágrafos seguidos sem figura,
quadro, destaque ou bloco interativo. Quando faltar figura, gere infográficos com a ferramenta de sua
preferência (o NotebookLM faz isso a partir das fontes do caderno) e reduza para 1.400 px no maior lado.
A casca já traz capitular no primeiro parágrafo, filete nos títulos de seção e cor própria por tipo de
bloco; não recrie isso no conteúdo.
- `audioUrl` fica `null`. Só se gera áudio com pedido explícito.
- Subtítulo de capítulo só quando o manuscrito traz um; caso contrário `null`.

Tipos de bloco além dos previstos no `CLAUDE.md` exigem mudar a casca primeiro. Se o manuscrito
pede algo assim, registre em `pendencias.md` e siga sem o bloco.

## Etapa 2 — Limpeza editorial

Aplique só o que `CLAUDE.md` autoriza: remover frases de bastidor reescrevendo em voz de
leitor e trocar os termos banidos. Nada de resumir, "melhorar" ou reordenar o texto do autor.
Cada substituição feita vai numa lista para o autor conferir, porque é o texto dele que está
sendo tocado.

## Etapa 3 — Referências validadas no PubMed

É a etapa mais longa e a única em que inventar é grave. O fluxo, com `fabrica/eutils.py`
(sem chave de API):

1. Extraia de cada capítulo as chaves "Autor ano" citadas na seção "Referências" e no corpo.
2. Para cada chave, busque com `esearch(f"{autor}[au] AND {ano}[dp] AND ({termos do tema})")`
   e leia os candidatos com `efetch`. Os termos do tema vêm do assunto do livro (para reserva
   ovariana, algo como `ovarian OR follicle OR AMH OR oocyte`). Sem esse filtro o nome de um
   autor comum devolve dezenas de artigos errados.
3. Confirme cada PMID lendo título e periódico. Guarde um mapa `chave -> {pmid, confiança,
   nota}` em `<slug>/refs/mapa.json`. Confiança "média" quando há dois artigos plausíveis do
   mesmo autor no mesmo ano; anote os dois e pergunte ao autor qual ele citou.
4. Formate com `vancouver(efetch([pmid])[pmid])`, removendo o sufixo ` PMID: ...`. Diretrizes
   sem PMID (ACOG, ACR, WHO) entram escritas à mão, com URL.
5. Ordene em ordem alfabética pela chave do primeiro autor dentro de cada capítulo e grave em
   `<slug>/refs/referencias.json` no formato `{"<número do capítulo>": ["1. …", "2. …"]}`.
   O `md2book.py` insere essa lista na seção "Referências" de cada capítulo.
6. O que não foi localizado vai para `pendencias.md` com a chave e o que foi tentado. Nunca
   entra na lista uma referência sem PMID confirmado ou sem fonte oficial.

O script de resolução é por título, porque os termos de busca mudam com o assunto: escreva-o em
`<slug>/refs/resolver.py` usando `fabrica/eutils.py`, e não reaproveite o de outro livro sem
trocar os termos.

## Etapa 4 — theme.json, capa e ícones

Copie `exemplo-livro/content/theme.json` como modelo e troque todos os campos de identidade:
`id`, `title`, `subtitle`, `shortName`, `tagline`, `description`, `cover`, `storagePrefix`.
O `storagePrefix` precisa ser único por título, senão dois apps no mesmo `localhost`
compartilham progresso e favoritos.

`author.name` e `author.credentials` são a identificação profissional de quem assina a obra:
preencha com os dados do próprio autor (nome, CRM e RQE quando for médico). Publicar um título
com as credenciais de outra pessoa é erro de identificação profissional — a Resolução CFM
2.336/2023 exige que a peça identifique corretamente quem a assina.

Cores e fontes são decisão do autor. Se o briefing não traz, proponha duas paletas em uma
frase cada e espere. Os ícones em `public/` (192, 512, 180, 1024, favicon, splash) são
gerados a partir da capa; sem capa, use um placeholder e registre em `pendencias.md`.

## Etapa 5 — Validação

```bash
python fabrica/validate.py <slug>
```

Zero erros é pré-requisito para a etapa seguinte. O validador confere tipos de bloco, ids
únicos, imagens existentes, seção "Referências" numerada e ordenada, e coerência entre
`book.json` e `theme.json`.

## Etapa 6 — Casca e teste local

Copie do título mais recente apenas o motor: `src/`, `public/`, `package.json`,
`package-lock.json`, `tsconfig.json`, `vite.config.ts`, `.gitignore`. Não copie
`node_modules`, `.output`, `.tanstack`, `.wrangler` nem `content/`. Depois:

```bash
cd <slug> && npm install && npm run dev
```

Entregue a URL local e um roteiro de teste em três linhas: abrir o sumário, ler um capítulo
com figura e tabela, tocar o áudio e conferir que começa em 1,5x.

## Etapa 6b — Versões PDF e EPUB

```bash
python fabrica/exportar.py <slug>
```

Gera `<slug>/exportacoes/<slug>.pdf` (17 × 24 cm, Chrome em modo headless, fontes do tema embutidas) e
`<slug>.epub` (EPUB 3 montado com a biblioteca padrão e conferido ao final: manifest, XHTML bem formado,
imagens, links e âncoras). Capa em pé é usada como está; arte deitada vira uma capa em pé composta com
título, subtítulo e autor. Blocos interativos viram versões estáticas, e o gabarito dos testes vai para
o fim do livro. Os arquivos ficam fora do Git: gere de novo a cada mudança de conteúdo.

O leitor de PDF do Claude Code não renderiza páginas. Para conferir, use PyMuPDF num ambiente
descartável, sem instalar nada no projeto: `uv run --no-project --with pymupdf python -`, renderizando
capa, sumário, uma abertura de capítulo, um bloco interativo e o gabarito. Confira também que os
marcadores laterais (`doc.get_toc()`) têm os títulos com espaços.

## Etapa 7 — Commit e publicação

Antes de qualquer commit: `npm run build && npx tsc --noEmit` dentro do título. Commits
pequenos, em português, no imperativo. Publicar (Vercel a partir do GitHub, ou equivalente) só
com aprovação explícita do autor.

## Manutenção da casca

Uma melhoria na casca é feita uma vez, no título mais recente, e propagada aos outros
copiando `src/`, `vite.config.ts` e `package.json`. `public/` e `content/` nunca são
propagados: são por título. Exemplos de ajustes que vivem na casca: velocidade inicial do
áudio (`DEFAULT_RATE` em `src/lib/audio-player.tsx`), opções de velocidade, tipos de bloco.

## Como reportar ao autor

Duas a quatro frases dizendo o que foi feito, depois "como testar" com a URL, depois as
pendências em lista se houver mais de três. Dúvida de conteúdo médico ou de referência é
pergunta, não suposição.
