#!/usr/bin/env python3
"""Valida content/book.json de um livro-app contra o formato que a casca (src/) sabe renderizar.

Uso:
    python fabrica/validate.py <pasta-do-livro>        # ex.: python fabrica/validate.py exemplo-livro
    python fabrica/validate.py --selftest              # confere que o validador pega erros conhecidos

Sai com código 1 e lista todos os problemas encontrados; código 0 quando tudo está no padrão.
O formato espelha src/content/types.ts: se mudar lá, mude aqui.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

# Tipos de bloco e campos obrigatórios (nome -> tipo aceito). Espelho de src/content/types.ts.
NONE = type(None)
BLOCK_FIELDS = {
    "p": {"text": str},
    "h2": {"text": str},
    "h3": {"text": str},
    "image": {"key": str, "caption": (str, NONE)},
    "table": {"rows": list},
    "pullquote": {"text": str, "label": (str, NONE)},
    "video": {"key": str, "caption": (str, NONE), "poster": (str, NONE)},
    "quiz": {"question": str, "options": list, "answer": int, "explanation": (str, NONE)},
    "flashcard": {"title": (str, NONE), "cards": list},
    "chart": {"kind": str, "title": str, "note": (str, NONE), "points": list},
}
# calc tem campos diferentes por kind; validado à parte em _check_calc.
CALC_FIELDS = {
    "bands": {"kind": str, "title": str, "note": (str, NONE), "fields": list},
    "poseidon": {"kind": str, "title": str, "note": (str, NONE), "ageLabel": str,
                 "ageThreshold": int, "ageInitial": int, "fields": list, "groups": list},
}
BAND_FIELDS = {"max": (int, float, NONE), "label": str, "tone": str}
FIELD_FIELDS = {"id": str, "label": str, "unit": (str, NONE), "min": (int, float),
                "max": (int, float), "step": (int, float), "initial": (int, float), "bands": list}
TONES = {"alert", "warn", "ok", "info"}
CHAPTER_FIELDS = {
    "id": str,
    "number": (int, type(None)),
    "title": str,
    "subtitle": (str, type(None)),
    "part": str,
    "blocks": list,
}
OPTIONAL_CHAPTER_FIELDS = {"audioUrl": (str, type(None))}
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
REF_RE = re.compile(r"^(\d+)\.\s+\S")
REFERENCES_TITLE = "referências"


def _ref_key(text):
    """Chave de ordenação de uma referência Vancouver: primeiro autor, sem acentos e sem caixa."""
    first = re.sub(r"^\d+\.\s+", "", text).split(",")[0]
    return unicodedata.normalize("NFKD", first).encode("ascii", "ignore").decode().casefold().strip()


def _check_fields(obj, required, optional, where, errors):
    for name, kind in required.items():
        if name not in obj:
            errors.append(f"{where}: falta o campo '{name}'")
        elif not isinstance(obj[name], kind):
            errors.append(f"{where}: campo '{name}' com tipo errado ({type(obj[name]).__name__})")
        elif kind is str and not obj[name].strip():
            errors.append(f"{where}: campo '{name}' está vazio")
    for name, kind in optional.items():
        if name in obj and not isinstance(obj[name], kind):
            errors.append(f"{where}: campo '{name}' com tipo errado ({type(obj[name]).__name__})")
    for name in obj:
        if name not in required and name not in optional:
            errors.append(f"{where}: campo desconhecido '{name}'")


def _check_list(items, required, where, errors, what):
    """Cada item da lista precisa ser um objeto com exatamente os campos de `required`."""
    if not items:
        errors.append(f"{where}: '{what}' está vazio")
        return
    for k, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"{where}.{what}[{k}]: precisa ser um objeto")
            continue
        _check_fields(item, required, {}, f"{where}.{what}[{k}]", errors)


def _check_calc(bl, where, errors):
    kind = bl.get("kind")
    if kind not in CALC_FIELDS:
        errors.append(f"{where}: calc com kind inválido '{kind}' (aceitos: {', '.join(CALC_FIELDS)})")
        return
    _check_fields(bl, {"type": str, **CALC_FIELDS[kind]}, {}, where, errors)
    for k, field in enumerate(bl.get("fields") or []):
        if not isinstance(field, dict):
            errors.append(f"{where}.fields[{k}]: precisa ser um objeto")
            continue
        _check_fields(field, FIELD_FIELDS, {}, f"{where}.fields[{k}]", errors)
        bands = field.get("bands")
        if isinstance(bands, list):
            _check_list(bands, BAND_FIELDS, f"{where}.fields[{k}]", errors, "bands")
            for b in bands:
                if isinstance(b, dict) and b.get("tone") not in TONES:
                    errors.append(f"{where}.fields[{k}]: tone inválido '{b.get('tone')}' (aceitos: {', '.join(sorted(TONES))})")
            tops = [b.get("max") for b in bands if isinstance(b, dict)]
            finite = [t for t in tops if isinstance(t, (int, float))]
            if finite != sorted(finite):
                errors.append(f"{where}.fields[{k}]: faixas fora de ordem crescente de 'max'")
            if tops and tops[-1] is not None:
                errors.append(f"{where}.fields[{k}]: a última faixa precisa ter 'max': null (valores acima de tudo)")
    if kind == "poseidon":
        groups = bl.get("groups")
        if isinstance(groups, list):
            _check_list(groups, {"label": str, "detail": str, "clbr": str, "clbr3": str}, where, errors, "groups")
            if len(groups) != 4:
                errors.append(f"{where}: POSEIDON precisa de 4 grupos na ordem 1 a 4, veio {len(groups)}")


def _check_block_extra(btype, bl, where, image_files, video_files, errors):
    if btype == "image" and isinstance(bl.get("key"), str):
        if bl["key"] not in image_files:
            errors.append(f"{where}: imagem '{bl['key']}' não existe em content/images/")
    elif btype == "video":
        if isinstance(bl.get("key"), str) and bl["key"] not in video_files:
            errors.append(f"{where}: vídeo '{bl['key']}' não existe em content/videos/")
        if isinstance(bl.get("poster"), str) and bl["poster"] not in image_files:
            errors.append(f"{where}: pôster '{bl['poster']}' não existe em content/images/")
    elif btype == "table" and isinstance(bl.get("rows"), list):
        rows = bl["rows"]
        if not rows or not all(isinstance(r, list) and all(isinstance(c, str) for c in r) for r in rows):
            errors.append(f"{where}: 'rows' deve ser lista não vazia de listas de strings")
        elif len({len(r) for r in rows}) != 1:
            errors.append(f"{where}: linhas da tabela com número de colunas diferente")
    elif btype == "quiz":
        options = bl.get("options")
        if not isinstance(options, list) or len(options) < 2 or not all(isinstance(o, str) and o.strip() for o in options):
            errors.append(f"{where}: 'options' deve ter ao menos duas alternativas de texto")
        elif not isinstance(bl.get("answer"), int) or not 0 <= bl["answer"] < len(options):
            errors.append(f"{where}: 'answer' deve ser o índice de uma alternativa (0 a {len(options) - 1})")
    elif btype == "flashcard" and isinstance(bl.get("cards"), list):
        _check_list(bl["cards"], {"front": str, "back": str}, where, errors, "cards")
    elif btype == "chart":
        if bl.get("kind") != "decline":
            errors.append(f"{where}: chart com kind inválido '{bl.get('kind')}' (aceito: decline)")
        if isinstance(bl.get("points"), list):
            _check_list(bl["points"], {"stage": str, "value": (int, float), "text": str}, where, errors, "points")


def validate(book, image_files, theme=None, video_files=frozenset()):
    """Retorna (erros, avisos). `image_files`/`video_files` são os nomes em content/images/ e content/videos/."""
    errors, warnings = [], []

    if not isinstance(book, dict):
        return ["book.json: o topo precisa ser um objeto"], warnings
    chapters = book.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        return ["book.json: 'chapters' precisa ser uma lista não vazia"], warnings

    if theme:
        for field in ("title", "subtitle"):
            if field in book and book[field] != theme.get(field):
                errors.append(f"book.json '{field}' difere de theme.json ('{book[field]}' vs '{theme.get(field)}')")
        cover = theme.get("cover", "")
        if cover.rsplit("/", 1)[-1] not in image_files:
            errors.append(f"theme.json: capa '{cover}' não existe em content/images/")

    seen_ids = {}
    used_images = set()
    for ci, ch in enumerate(chapters):
        where = f"chapters[{ci}]"
        if not isinstance(ch, dict):
            errors.append(f"{where}: capítulo precisa ser um objeto")
            continue
        _check_fields(ch, CHAPTER_FIELDS, OPTIONAL_CHAPTER_FIELDS, where, errors)
        cid = ch.get("id")
        if isinstance(cid, str):
            where = f"chapters[{ci}] ({cid})"
            if not ID_RE.match(cid):
                errors.append(f"{where}: id deve ser slug (letras minúsculas, números e hífens)")
            if cid in seen_ids:
                errors.append(f"{where}: id duplicado (já usado em chapters[{seen_ids[cid]}])")
            seen_ids.setdefault(cid, ci)

        blocks = ch.get("blocks")
        if not isinstance(blocks, list):
            continue
        if not blocks:
            errors.append(f"{where}: 'blocks' está vazio")

        ref_start = None
        for bi, bl in enumerate(blocks):
            bwhere = f"{where}.blocks[{bi}]"
            if not isinstance(bl, dict):
                errors.append(f"{bwhere}: bloco precisa ser um objeto")
                continue
            btype = bl.get("type")
            if btype == "calc":
                _check_calc(bl, bwhere, errors)
                continue
            if btype not in BLOCK_FIELDS:
                allowed = ", ".join(list(BLOCK_FIELDS) + ["calc"])
                errors.append(f"{bwhere}: tipo de bloco não permitido '{btype}' (aceitos: {allowed})")
                continue
            _check_fields(bl, {"type": str, **BLOCK_FIELDS[btype]}, {}, bwhere, errors)

            if isinstance(bl.get("key"), str) and btype == "image":
                used_images.add(bl["key"])
            if isinstance(bl.get("poster"), str):
                used_images.add(bl["poster"])
            _check_block_extra(btype, bl, bwhere, image_files, video_files, errors)

            if btype == "h2" and isinstance(bl.get("text"), str) and bl["text"].strip().lower() == REFERENCES_TITLE:
                if ref_start is not None:
                    errors.append(f"{bwhere}: segunda seção 'Referências' no mesmo capítulo")
                ref_start = bi

        # Seção "Referências": obrigatória em capítulos numerados; quando existe, só parágrafos "N. ..." em ordem 1..n.
        if ref_start is None:
            if ch.get("number") is not None:
                errors.append(f"{where}: capítulo numerado sem seção 'Referências'")
        else:
            refs = blocks[ref_start + 1 :]
            if not refs:
                errors.append(f"{where}: seção 'Referências' vazia")
            keys = []
            for k, bl in enumerate(refs, start=1):
                bwhere = f"{where}.blocks[{ref_start + k}]"
                if not isinstance(bl, dict) or bl.get("type") != "p":
                    errors.append(f"{bwhere}: dentro de 'Referências' só são permitidos parágrafos")
                    continue
                m = REF_RE.match(bl.get("text", "") if isinstance(bl.get("text"), str) else "")
                if not m:
                    errors.append(f"{bwhere}: referência sem numeração 'N. ' -> {str(bl.get('text'))[:60]!r}")
                elif int(m.group(1)) != k:
                    errors.append(f"{bwhere}: referência numerada {m.group(1)}, esperado {k}")
                else:
                    keys.append((k, _ref_key(bl["text"])))
            # Regra editorial: referências em ordem alfabética pelo primeiro autor dentro do capítulo.
            for (k1, a), (k2, b) in zip(keys, keys[1:]):
                if a > b:
                    errors.append(f"{where}: referências fora de ordem alfabética entre {k1} ('{a}') e {k2} ('{b}')")
                    break

    cover = theme.get("cover", "").rsplit("/", 1)[-1] if theme else ""
    for f in sorted(image_files - used_images - {cover}):
        warnings.append(f"content/images/{f} não é referenciada por nenhum bloco")

    return errors, warnings


def main(argv):
    if argv[1:] == ["--selftest"]:
        return selftest()
    if len(argv) != 2:
        print(__doc__)
        return 2
    root = Path(argv[1])
    book_path, theme_path, images_dir = root / "content/book.json", root / "content/theme.json", root / "content/images"
    videos_dir = root / "content/videos"
    try:
        book = json.loads(book_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"ERRO: não foi possível ler {book_path}: {e}")
        return 1
    theme = json.loads(theme_path.read_text(encoding="utf-8")) if theme_path.exists() else None
    image_files = {p.name for p in images_dir.iterdir()} if images_dir.is_dir() else set()
    video_files = {p.name for p in videos_dir.iterdir()} if videos_dir.is_dir() else set()

    errors, warnings = validate(book, image_files, theme, video_files)
    for w in warnings:
        print(f"AVISO: {w}")
    if errors:
        print(f"\n{len(errors)} problema(s) em {book_path}:")
        for e in errors:
            print(f"  - {e}")
        return 1
    n_blocks = sum(len(c["blocks"]) for c in book["chapters"])
    n_images = sum(1 for c in book["chapters"] for b in c["blocks"] if b["type"] == "image")
    print(f"OK: {len(book['chapters'])} capítulos, {n_blocks} blocos, {n_images} imagens, nenhum problema.")
    return 0


def selftest():
    """Menor livro válido + um erro de cada categoria; falha se o validador deixar passar."""
    good = {
        "title": "T", "subtitle": "S",
        "chapters": [
            {"id": "abertura", "number": None, "title": "A", "subtitle": None, "part": "P",
             "blocks": [{"type": "p", "text": "x"}]},
            {"id": "capitulo-1", "number": 1, "title": "C", "subtitle": None, "part": "P", "audioUrl": None,
             "blocks": [{"type": "image", "key": "a.png", "caption": None},
                        {"type": "table", "rows": [["a", "b"], ["c", "d"]]},
                        {"type": "video", "key": "v.mp4", "caption": None, "poster": "a.png"},
                        {"type": "quiz", "question": "Q?", "options": ["A", "B"], "answer": 1, "explanation": None},
                        {"type": "flashcard", "title": None, "cards": [{"front": "F", "back": "B"}]},
                        {"type": "chart", "kind": "decline", "title": "C", "note": None,
                         "points": [{"stage": "s", "value": 10, "text": "dez"}]},
                        {"type": "calc", "kind": "bands", "title": "C", "note": None,
                         "fields": [{"id": "amh", "label": "AMH", "unit": "ng/mL", "min": 0, "max": 10,
                                     "step": 0.1, "initial": 1.5,
                                     "bands": [{"max": 1, "label": "baixa", "tone": "alert"},
                                               {"max": None, "label": "ok", "tone": "ok"}]}]},
                        {"type": "h2", "text": "Referências"},
                        {"type": "p", "text": "1. Alfa A. X."},
                        {"type": "p", "text": "2. Beta B. Y."},
                        {"type": "p", "text": "3. Gama C. Z."}]},
        ],
    }
    theme = {"title": "T", "subtitle": "S", "cover": "images/a.png"}
    assert validate(good, {"a.png"}, theme, {"v.mp4"}) == ([], []), validate(good, {"a.png"}, theme, {"v.mp4"})

    bad = json.loads(json.dumps(good))
    blocks = bad["chapters"][1]["blocks"]
    bad["chapters"][0]["id"] = "capitulo-1"                         # id duplicado
    blocks[0]["key"] = "nao-existe.png"                             # imagem ausente
    blocks[1] = {"type": "mapa", "q": "?"}                          # tipo não permitido
    blocks[2]["key"] = "sumiu.mp4"                                  # vídeo ausente
    blocks[3]["answer"] = 7                                         # alternativa inexistente
    blocks[6]["fields"][0]["bands"][0]["tone"] = "roxo"             # tone inválido
    blocks[-3]["text"] = "Ref sem número"                           # referência não numerada
    blocks[-2]["text"] = "2. Gama C. Z."                            # fora de ordem alfabética
    blocks[-1]["text"] = "3. Beta B. Y."
    errors, _ = validate(bad, {"a.png"}, None, {"v.mp4"})
    for needle in ("id duplicado", "não existe em content/images", "tipo de bloco não permitido",
                   "não existe em content/videos", "índice de uma alternativa", "tone inválido",
                   "sem numeração", "fora de ordem alfabética"):
        assert any(needle in e for e in errors), f"validador não detectou: {needle}\n{errors}"
    print(f"selftest OK ({len(errors)} erros detectados no livro inválido)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
