# CLAUDE.md — Fábrica de livros-app (starter)

Repositório-modelo para transformar manuscritos em **livros-app**: web apps de leitura para celular,
instaláveis como PWA, sem servidor, sem login e sem coleta de dados. O motor de leitura é o mesmo para
todos os títulos e lê tudo de `content/`. Comunicar-se em português brasileiro, de forma curta e direta.
Presuma que o autor não edita código nem JSON: ele descreve o que quer e recebe o resultado pronto para
testar no navegador.

> Antes do primeiro título, preencha os dados do autor em `<slug>/content/theme.json`
> (`author.name` e `author.credentials`). Eles aparecem na capa, no PDF e no EPUB, e são a identificação
> profissional de quem assina a obra. Nunca publique um título com as credenciais de outra pessoa.

## Estrutura

```
livro-app-starter/
├── CLAUDE.md
├── .claude/skills/fabrica-livro-app/   # skill: manuscrito -> livro-app (pipeline passo a passo)
├── fabrica/                      # scripts do pipeline (Python)
│   ├── eutils.py                 # busca e formatação Vancouver via PubMed E-utilities
│   ├── md2book.py                # converte o manuscrito Markdown em content/book.json
│   ├── validate.py               # valida content/book.json de um título
│   └── exportar.py               # gera PDF e EPUB do título a partir de content/
└── <slug-do-titulo>/             # um diretório por livro (ex.: exemplo-livro)
    ├── content/
    │   ├── book.json             # FONTE DE VERDADE do conteúdo
    │   ├── theme.json            # identidade: título, autor, cores, fontes, ícones
    │   ├── images/               # capa + figuras + pôsteres, referenciados por nome de arquivo
    │   └── videos/               # vídeos dos capítulos (opcional), referenciados por nome de arquivo
    ├── manuscrito/               # manuscrito.md + figuras entregues pelo autor
    ├── refs/                     # referências validadas e relatório de pendências
    ├── src/                      # a casca (motor de leitura); NÃO contém texto do livro
    ├── public/                   # ícones e splash (o manifesto PWA é gerado de theme.json)
    ├── exportacoes/              # PDF e EPUB gerados por fabrica/exportar.py (fora do Git)
    └── package.json              # TanStack Start + Tailwind 4 + Capacitor iOS
```

O motor é o mesmo para todos os títulos. Um título novo = novo diretório com content/ preenchido + cópia
da casca do título mais recente. Melhorias na casca são feitas uma vez e propagadas aos demais títulos.

## Esquema de book.json

```json
{
  "title": "...", "subtitle": "...", "author": "...",
  "chapters": [
    {
      "id": "capitulo-4-slug", "number": 4, "part": "Parte II — ...",
      "title": "...", "subtitle": "...", "audioUrl": null,
      "blocks": [
        {"type": "p",     "text": "..."},
        {"type": "h2",    "text": "..."},
        {"type": "h3",    "text": "..."},
        {"type": "image", "key": "image7.png", "caption": "..."},
        {"type": "table", "rows": [["cabeçalho", "..."], ["linha", "..."]]},
        {"type": "pullquote", "text": "frase-chave literal do capítulo", "label": null},
        {"type": "video", "key": "x.mp4", "caption": "...", "poster": "poster-x.jpg"},
        {"type": "quiz", "question": "...", "options": ["..."], "answer": 0, "explanation": "..."},
        {"type": "flashcard", "title": "...", "cards": [{"front": "...", "back": "..."}]},
        {"type": "calc", "kind": "bands", "title": "...", "note": "...", "fields": ["..."]},
        {"type": "calc", "kind": "poseidon", "title": "...", "note": "...", "ageLabel": "...",
         "ageThreshold": 35, "ageInitial": 33, "fields": ["..."], "groups": ["..."]},
        {"type": "chart", "kind": "decline", "title": "...", "note": "...", "points": ["..."]}
      ]
    }
  ]
}
```

Tipos de bloco vigentes: p, h2, h3, image, table, pullquote, video, quiz, flashcard, calc, chart. Tipos planejados
(adicionar à casca antes de usar no conteúdo): audio, hotspot, compare, steps, image-quiz, model3d.
O último h2 de cada capítulo é "Referências", seguido de parágrafos "1. ...", "2. ..." em Vancouver;
blocos interativos vêm antes dessa seção.

Os campos de `calc` e `chart` estão em `src/content/types.ts` (`Field`, `Band`, `PoseidonGroup`). Em
qualquer faixa, `max` é teto inclusivo e a última faixa tem `"max": null`. No manuscrito, blocos
interativos entram como cerca com o tipo e um objeto JSON dentro (crases triplas seguidas de quiz,
flashcard, calc ou chart); vídeo usa a sintaxe de imagem apontando para `videos/x.mp4`, e o pôster é
encontrado por convenção em `images/poster-<nome>.jpg`. O destaque do capítulo entra como citação
Markdown (`> frase`) e a frase precisa existir literalmente no texto do capítulo.

`theme.json > colors.<modo>` traz, além de background, foreground, primary, primaryForeground, accent,
accentForeground e highlight, um objeto `blocks` com uma cor por tipo de bloco interativo (quiz,
flashcard, calc, chart). São elas que evitam que todos os blocos pareçam iguais.

## Pipeline de um título novo

1. Entrada: manuscrito (DOCX ou Markdown) + figuras + briefing (público, tom).
2. Converter em blocos tipados; um capítulo por heading de nível 1; figuras numeradas na ordem em que aparecem.
3. Limpeza editorial (ver regras abaixo). Nunca resumir, reescrever ou "melhorar" o texto do autor além dessas regras.
4. Referências: extrair todas as citações, validar cada uma no PubMed (fabrica/eutils.py), montar lista Vancouver por capítulo. O que não for localizado fica num relatório de pendências, nunca inventado.
5. Gerar content/book.json, content/theme.json, content/images/. Rodar `python fabrica/validate.py <slug>`.
6. Copiar a casca, rodar `npm run dev`, entregar URL local e roteiro de teste em 3 linhas.
7. Versões PDF e EPUB: `python fabrica/exportar.py <slug>`. Refazer sempre que o conteúdo mudar e conferir no PDF a capa, o sumário, uma abertura de capítulo e os blocos interativos.
8. Publicação (Vercel a partir do GitHub, ou equivalente) só com aprovação explícita do autor.

## Regras editoriais

- Remover frases de bastidor do roteiro de redação ("Para o livro, convém…", "A redação deve…", "Este capítulo deve…", "O texto deve…"), reescrevendo em voz de leitor. Manter frases legítimas de autor ("A tese deste capítulo é…").
- Referências sempre em Vancouver, com DOI quando houver, ordem alfabética por chave dentro de cada capítulo. Nunca fabricar referência; se não localizar, listar como pendente.
- Terminologia técnica conforme os consensos da área (em ultrassom e ginecologia: MUSA, IDEA, IETA). Siglas e números por extenso apenas em roteiros de narração.
- Conteúdo médico publicado deve respeitar a Resolução CFM 2.336/2023 (publicidade médica): sem promessa de resultado, sem sensacionalismo, com identificação profissional do autor (nome, CRM, RQE).

## Regras técnicas

- Nenhum texto do livro, cor, fonte ou nome de título hard-coded em src/. Tudo vem de content/.
- localStorage apenas para progresso, favoritos, marcadores e ajustes do leitor. Sem analytics, sem chamadas externas em runtime (exceto fontes do Google Fonts).
- Áudio: campo audioUrl por capítulo; se vazio, fallback para Web Speech API. Não gerar áudio sem pedido. Velocidade inicial padrão 1,5x (constante DEFAULT_RATE em src/lib/audio-player.tsx), com opções 1x, 1,25x e 1,5x; a escolha do leitor fica em localStorage e prevalece sobre o padrão.
- Calculadora ou quiz não usam LLM em runtime: todos os limiares, respostas e faixas vêm de content/. Chave de API quebraria o app offline e a regra de não fazer chamadas externas.
- Vídeo pesa cerca de 10 MB por minuto; use poucos por título, sempre com `poster` e `preload="none"`.
- Todo tipo de bloco novo precisa de uma versão estática em `fabrica/exportar.py`; sem ela a exportação para PDF e EPUB é interrompida de propósito.
- Build deve passar `npm run build && npx tsc --noEmit` antes de qualquer commit.
- Commits pequenos, mensagem em português no imperativo ("Adiciona bloco quiz à casca").
- Não instalar dependências novas nem mudar o design system sem avisar e justificar em uma frase.

## Como responder ao autor

- Confirmar o que foi feito em 2 a 4 frases; listas só quando houver mais de três itens de ação para ele.
- Sempre terminar com como testar (URL local + o que olhar) quando houver mudança visível.
- Em caso de dúvida sobre conteúdo médico ou referência, perguntar, não presumir.
