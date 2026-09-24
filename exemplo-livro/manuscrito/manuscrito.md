# Apresentação

Este é um título de demonstração. Ele existe para que você rode a fábrica uma vez, veja o resultado no navegador e depois apague a pasta inteira para colocar o seu livro no lugar.

São três capítulos curtos que usam, de propósito, todos os tipos de bloco que a casca sabe renderizar: figura, quadro, destaque, teste rápido, flashcards, calculadora e gráfico. Se algo aparecer errado na tela, o problema está no motor ou na instalação, não no seu manuscrito.

O texto abaixo descreve o próprio método. Leia como manual, não como livro.

# Parte I — O método

# Capítulo 1 — O que é um livro-app

Um livro-app é um web app de leitura, feito para o celular e instalável como aplicativo. Ele não tem servidor, não pede login e não coleta dados: todo o conteúdo viaja junto com a página, e o que o leitor marca fica guardado no próprio aparelho.

A diferença em relação a um PDF não está no texto, e sim no que o leitor pode fazer com ele. O sumário abre em um toque, a busca encontra a palavra no livro inteiro, o aparelho lê o capítulo em voz alta e um teste rápido devolve a resposta na hora.

## O que o leitor recebe

Na primeira visita, o navegador oferece instalar o livro na tela inicial. A partir daí ele abre sem barra de endereço e funciona sem internet, porque os arquivos ficam no cache do aparelho.

![Figura 1.1 — Um mesmo content/ alimenta as três saídas: app, PDF e EPUB.](images/figura-1-1.png)

O progresso de leitura, os favoritos e o tamanho da letra ficam no localStorage. Nada disso sai do aparelho do leitor.

> Um conteúdo, três formatos, e um autor responsável por ele.

## Três saídas, um conteúdo

O mesmo content/ gera as três entregas. Nenhuma delas é digitada duas vezes.

| Formato | Onde vive | Melhor para |
| --- | --- | --- |
| App (PWA) | link ou tela inicial do celular | leitura no dia a dia, busca, áudio, blocos interativos |
| PDF | arquivo, impressão | leitura linear, imprimir, anexar por e-mail |
| EPUB | Play Livros, Kobo, Thorium | leitores de e-book, tipografia ajustável |

```quiz
{
  "question": "O que acontece com o livro-app quando o leitor fica sem internet?",
  "options": [
    "Ele para de abrir até a conexão voltar",
    "Ele continua abrindo, porque os arquivos ficam no cache do aparelho",
    "Ele abre, mas perde o progresso de leitura"
  ],
  "answer": 1,
  "explanation": "O app é instalável como PWA e não depende de servidor. O progresso fica no localStorage do próprio aparelho."
}
```

## Referências

# Capítulo 2 — Como escrever o manuscrito

O manuscrito é um arquivo Markdown só seu. Você escreve como sempre escreveu; a fábrica cuida da conversão em blocos tipados, da validação e da montagem.

## Títulos e partes

Cada # de nível 1 abre um capítulo. "Capítulo 3 — Título" vira um capítulo numerado; um título sem número, como esta Apresentação, entra como abertura e fica fora da numeração. Uma linha "Parte II — Título" não cria capítulo: define a parte dos capítulos seguintes.

### Figuras

Figuras entram com a sintaxe normal do Markdown, apontando para images/. A legenda é o texto entre colchetes, e o arquivo precisa existir em content/images/ — se não existir, a validação acusa antes de o livro chegar ao navegador.

### Referências

Cada capítulo numerado termina com uma seção "Referências". Você cita no texto como preferir; a lista final é montada a partir do PubMed, com cada chave confirmada uma a uma. O que não for localizado vira pendência, nunca uma referência inventada.

> O que não for localizado vira pendência, nunca uma referência inventada.

```flashcard
{
  "title": "Convenções do manuscrito",
  "cards": [
    {"front": "Como abrir um capítulo numerado?", "back": "Uma linha começando com # e o texto \"Capítulo N — Título\"."},
    {"front": "Como definir a parte de um grupo de capítulos?", "back": "Uma linha # com \"Parte II — Título\", antes dos capítulos que pertencem a ela."},
    {"front": "Onde ficam as figuras?", "back": "Em content/images/, referenciadas pelo nome do arquivo na sintaxe de imagem do Markdown."},
    {"front": "E o destaque do capítulo?", "back": "Uma citação Markdown com > no início da linha. A frase precisa existir literalmente no texto do capítulo."}
  ]
}
```

## Referências

# Parte II — Recursos

# Capítulo 3 — Blocos interativos

Um capítulo só de texto corrido cansa no celular. Os blocos interativos quebram o ritmo e ajudam a fixar, e todos eles funcionam offline: as respostas, as faixas e os números vêm do content/, nunca de uma chamada a um modelo de linguagem.

## Teste rápido e flashcards

O teste rápido confere uma ideia logo depois de explicá-la, e devolve a explicação junto com a resposta. Os flashcards servem para fechar uma parte, reunindo o que o leitor precisa levar dali.

## Calculadora

Uma calculadora transforma uma tabela de faixas em resposta direta. As faixas ficam no conteúdo, com um rótulo e um tom para cada uma.

```calc
{
  "kind": "bands",
  "title": "Quanto vídeo cabe neste título?",
  "note": "Vídeo pesa cerca de 10 MB por minuto, e tudo isso entra no cache offline do leitor. Exemplo de calculadora: as faixas vêm do conteúdo, não de um modelo.",
  "fields": [
    {
      "id": "minutos",
      "label": "Minutos de vídeo no livro inteiro",
      "unit": "min",
      "min": 0,
      "max": 20,
      "step": 1,
      "initial": 3,
      "bands": [
        {"max": 2, "label": "Leve — cabe bem no cache do aparelho", "tone": "ok"},
        {"max": 6, "label": "Médio — use pôster e preload none em cada vídeo", "tone": "warn"},
        {"max": null, "label": "Pesado — considere hospedar o vídeo fora do app", "tone": "alert"}
      ]
    }
  ]
}
```

## Gráfico

O gráfico mostra uma queda em etapas. No exemplo abaixo, o peso de uma figura conforme ela é reduzida antes de entrar no livro.

```chart
{
  "kind": "decline",
  "title": "Peso de uma figura conforme a largura",
  "note": "Medida em uma imagem PNG de infográfico. Reduzir para 1.400 px no maior lado costuma manter a leitura no celular.",
  "points": [
    {"stage": "4.000 px", "value": 3300, "text": "3,3 MB — como sai do gerador"},
    {"stage": "2.000 px", "value": 1200, "text": "1,2 MB"},
    {"stage": "1.400 px", "value": 600, "text": "600 KB — largura recomendada"},
    {"stage": "1.000 px", "value": 320, "text": "320 KB — já perde detalhe em quadros"}
  ]
}
```

> Os blocos interativos funcionam offline porque os números vêm do conteúdo.

```quiz
{
  "question": "Por que a calculadora do livro não usa um modelo de linguagem para responder?",
  "options": [
    "Porque ficaria caro",
    "Porque quebraria o app offline e exigiria uma chave de API no código",
    "Porque o resultado seria mais lento"
  ],
  "answer": 1,
  "explanation": "Limiares, faixas e respostas vêm de content/. Uma chamada externa quebraria a leitura sem internet e a regra de não expor chaves."
}
```

## Referências
