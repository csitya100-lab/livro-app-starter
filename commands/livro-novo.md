---
description: Cria um livro-app novo a partir de um manuscrito
argument-hint: [pasta-ou-arquivo-do-manuscrito]
---

O autor quer transformar um manuscrito em livro-app. Siga a skill `fabrica-livro-app`, que descreve
o pipeline inteiro, e não pule a Etapa 0.

O manuscrito está em: $ARGUMENTS

Se nada foi informado, procure por um arquivo `.md` ou `.docx` na pasta atual e pergunte ao autor
qual é o manuscrito antes de tocar em qualquer coisa.

Comece pelo **inventário** (Etapa 0 da skill): leia o manuscrito inteiro e responda em uma lista
curta quantos capítulos há, se existe divisão em partes, quais figuras faltam e em que estado estão
as referências. Só depois de o autor confirmar é que a conversão começa.

Lembretes que valem para todo título novo:

- os dados do autor em `theme.json` (`author.name`, `author.credentials`) são de quem assina a obra —
  pergunte, não repita os do exemplo;
- `storagePrefix` precisa ser único por título;
- referência não confirmada no PubMed vira pendência, nunca citação inventada;
- publicar (Vercel, GitHub Pages ou equivalente) só com aprovação explícita do autor.
