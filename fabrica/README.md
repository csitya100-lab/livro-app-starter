# fabrica/ — os scripts do pipeline

Quatro scripts, sem dependências fora da biblioteca padrão do Python (o PDF usa o Chrome instalado
na máquina). Todos recebem o slug do título, a partir da raiz do repositório.

| Script | O que faz |
| --- | --- |
| `md2book.py <slug>` | converte `<slug>/manuscrito/manuscrito.md` em `<slug>/content/book.json`: partes, capítulos, figuras, vídeos, quadros, destaques e blocos interativos. Usa `<slug>/content/theme.json` para título, subtítulo e autor, e insere as referências de `<slug>/refs/referencias.json`. |
| `validate.py <slug>` | valida `content/book.json` (mais `theme.json` e `content/images/`) contra o formato que a casca renderiza. Sai com erro e lista os problemas. `--selftest` confere o próprio validador. |
| `eutils.py` | busca no PubMed pelas E-utilities (sem chave de API) e formata a citação em Vancouver. Importado pelo script de resolução de referências de cada título. |
| `exportar.py <slug>` | gera `<slug>/exportacoes/<slug>.pdf` e `<slug>.epub` a partir de `content/`. `--selftest` monta um EPUB de teste com todos os tipos de bloco e confere a estrutura. |

## O que o validador cobra

- tipos de bloco `p｜h2｜h3｜image｜table｜pullquote｜video｜quiz｜flashcard｜calc｜chart`, com os campos
  obrigatórios de cada um;
- `id` de capítulo em formato de slug e único no livro;
- imagens e vídeos referenciados existindo em `content/images/` e `content/videos/`;
- capítulo numerado com seção "Referências", em parágrafos `1. …`, `2. …`, numerados em ordem e
  alfabéticos pelo primeiro autor;
- título e subtítulo de `book.json` iguais aos de `theme.json`, e a capa existindo.

## Referências por título

O script que resolve as chaves "Autor ano" no PubMed é **por livro**, porque os termos de busca mudam
com o assunto. Escreva-o em `<slug>/refs/resolver.py` usando `eutils.py`, guarde o resultado em
`<slug>/refs/mapa.json` (chave → PMID, confiança e citação) e grave a lista final em
`<slug>/refs/referencias.json`, que o `md2book.py` insere em cada capítulo.

Regra que não se negocia: referência não localizada vira pendência, nunca uma citação inventada.
