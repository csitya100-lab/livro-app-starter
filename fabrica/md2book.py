#!/usr/bin/env python3
"""Converte <slug>/manuscrito/manuscrito.md em <slug>/content/book.json (etapa 1 da skill fabrica-livro-app).

Convenções do Markdown (ver CLAUDE.md):
- "# Capítulo N — Título" abre um capítulo numerado; "# Título" sem número abre uma seção de abertura (part "Abertura").
- "# Parte X — Título" não é capítulo: define o campo `part` dos capítulos seguintes.
- "## " -> h2, "### " -> h3, parágrafo -> p, "![Legenda](images/arquivo.png)" -> image, tabela Markdown -> table.
- Marcas de citação inline "[3]" ou "[3, 12]" são removidas do texto (as referências ficam na seção do capítulo).
- A seção "## Referências" de cada capítulo é substituída pela lista de <slug>/refs/referencias.json
  ({"<número ou id>": ["1. …", "2. …"]}); capítulo sem lista fica sem a seção.

Uso: python fabrica/md2book.py <slug>
"""
import json, re, sys, unicodedata
from pathlib import Path

CITE_RE = re.compile(r"\s*\[\d+(?:\s*,\s*\d+)*\]")
IMG_RE = re.compile(r"^!\[(.*?)\]\((.*?)\)\s*$")
FENCE_RE = re.compile(r"^```(\w+)\s*$")
CHAPTER_RE = re.compile(r"^Capítulo\s+(\d+)\s*[—–-]\s*(.+)$")
PART_RE = re.compile(r"^Parte\s+\S+\s*[—–-]\s*.+$")
VIDEO_EXT = {".mp4", ".webm"}
# Blocos interativos entram como cerca ```<tipo> com um objeto JSON dentro (ver CLAUDE.md).
INTERACTIVE = {"quiz", "flashcard", "calc", "chart"}


def slug(text):
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", t)).strip("-")


def clean(text):
    return re.sub(r"\s{2,}", " ", CITE_RE.sub("", text)).strip()


def parse_blocks(lines, images_dir=None):
    blocks, para, table = [], [], []
    fence_type, fence_body = None, []

    def flush_para():
        nonlocal para
        if para:
            blocks.append({"type": "p", "text": clean(" ".join(para))})
            para = []

    def flush_table():
        nonlocal table
        if table:
            rows = []
            for row in table:
                cells = [clean(c) for c in row.strip().strip("|").split("|")]
                if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    continue  # linha separadora do cabeçalho
                rows.append(cells)
            blocks.append({"type": "table", "rows": rows})
            table = []

    for raw in lines:
        line = raw.rstrip()
        if fence_type is not None:
            if line.strip() == "```":
                try:
                    payload = json.loads("\n".join(fence_body))
                except json.JSONDecodeError as exc:
                    raise SystemExit(f"bloco ```{fence_type} com JSON inválido: {exc}")
                blocks.append({"type": fence_type, **payload})
                fence_type, fence_body = None, []
            else:
                fence_body.append(raw)
            continue
        fence = FENCE_RE.match(line)
        if fence and fence.group(1) in INTERACTIVE:
            flush_para(); flush_table()
            fence_type, fence_body = fence.group(1), []
            continue
        if line.startswith("> "):
            # citação Markdown vira o destaque do capítulo (frase-chave do próprio texto)
            flush_para(); flush_table()
            blocks.append({"type": "pullquote", "text": clean(line[2:]), "label": None})
            continue
        if line.startswith("|"):
            flush_para(); table.append(line); continue
        flush_table()
        if not line.strip():
            flush_para(); continue
        if line.startswith("### "):
            flush_para(); blocks.append({"type": "h3", "text": clean(line[4:])}); continue
        if line.startswith("## "):
            flush_para(); blocks.append({"type": "h2", "text": clean(line[3:])}); continue
        m = IMG_RE.match(line)
        if m:
            flush_para()
            caption = clean(m.group(1)) or None
            target = Path(m.group(2))
            if target.suffix.lower() in VIDEO_EXT:
                # pôster por convenção: content/images/poster-<nome-do-vídeo>.jpg, quando existir
                poster = f"poster-{target.stem}.jpg"
                if images_dir is None or not (images_dir / poster).exists():
                    poster = None
                blocks.append({"type": "video", "key": target.name, "caption": caption, "poster": poster})
            else:
                blocks.append({"type": "image", "key": target.name, "caption": caption})
            continue
        para.append(line.strip())
    flush_para(); flush_table()
    return blocks


def apply_references(blocks, refs):
    """Troca tudo após o último h2 'Referências' pela lista numerada; sem lista, remove a seção."""
    idx = [i for i, b in enumerate(blocks) if b["type"] == "h2" and b["text"].strip().lower() == "referências"]
    if not idx:
        return blocks + ([{"type": "h2", "text": "Referências"}] + [{"type": "p", "text": r} for r in refs] if refs else [])
    head = blocks[: idx[-1]]
    if not refs:
        return head
    return head + [{"type": "h2", "text": "Referências"}] + [{"type": "p", "text": r} for r in refs]


def convert(root: Path):
    md = (root / "manuscrito/manuscrito.md").read_text(encoding="utf-8")
    theme = json.loads((root / "content/theme.json").read_text(encoding="utf-8"))
    refs_path = root / "refs/referencias.json"
    refs = json.loads(refs_path.read_text(encoding="utf-8")) if refs_path.exists() else {}

    chapters, part = [], "Abertura"
    for chunk in re.split(r"^# ", md, flags=re.M)[1:]:
        title_line, _, body = chunk.partition("\n")
        title_line = title_line.strip()
        if PART_RE.match(title_line):
            part = title_line
            continue
        m = CHAPTER_RE.match(title_line)
        if m:
            number, title = int(m.group(1)), m.group(2).strip()
            cid, cpart = f"capitulo-{number}-{slug(title)}", part
        else:
            number, title = None, title_line
            cid, cpart = slug(title), "Abertura"
        blocks = parse_blocks(body.splitlines(), root / "content/images")
        blocks = apply_references(blocks, refs.get(str(number) if number is not None else cid, []))
        chapters.append({"id": cid, "number": number, "title": title, "subtitle": None, "part": cpart,
                         "audioUrl": None, "blocks": blocks})

    book = {"title": theme["title"], "subtitle": theme["subtitle"], "author": theme["author"]["name"], "chapters": chapters}
    out = root / "content/book.json"
    out.write_text(json.dumps(book, ensure_ascii=False, indent=2), encoding="utf-8")
    n_blocks = sum(len(c["blocks"]) for c in chapters)
    print(f"{out}: {len(chapters)} capítulos, {n_blocks} blocos, "
          f"{sum(1 for c in chapters for b in c['blocks'] if b['type']=='image')} imagens, "
          f"{sum(1 for c in chapters for b in c['blocks'] if b['type']=='table')} tabelas")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__); sys.exit(2)
    convert(Path(sys.argv[1]))
