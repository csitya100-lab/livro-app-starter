#!/usr/bin/env python3
"""Exporta um título para PDF e EPUB a partir de content/, os mesmos arquivos que o app lê.

Uso (na raiz do repositório):
    python fabrica/exportar.py <slug>             # gera <slug>/exportacoes/<slug>.pdf e <slug>.epub
    python fabrica/exportar.py <slug> --sem-pdf   # só o EPUB
    python fabrica/exportar.py --selftest

Blocos interativos viram versões estáticas: quiz com gabarito no fim do livro, flashcards como lista
de revisão, calculadoras como quadros de faixas, gráfico como desenho vetorial com tabela e vídeo como
pôster com legenda. Um tipo de bloco sem exportação definida interrompe o script, em vez de sumir.

O PDF sai do Chrome em modo headless; o EPUB 3 é montado com a biblioteca padrão e conferido
estruturalmente ao final (arquivos do manifest, XHTML bem formado, imagens, links e âncoras).
"""
import base64
import glob
import html
import io
import json
import math
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from string import Template

from PIL import Image, ImageOps

PAGINA_MM = (170, 240)          # 17 x 24 cm, formato mais comum de livro técnico no Brasil
CAPA_PX = (1700, 2400)          # mesma proporção da página
IMAGEM_MAX = 1400
XHTML_NS = "http://www.w3.org/1999/xhtml"
SVG_NS = "http://www.w3.org/2000/svg"
OPF_NS = "http://www.idpf.org/2007/opf"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
SUBCONJUNTOS_FONTE = ("latin", "latin-ext", "greek")
CAPA_ARQUIVO = "capa-livro.jpg"


# ---------------------------------------------------------------- utilidades

def esc(texto):
    return html.escape(str(texto), quote=True)


def num(valor):
    return f"{valor:g}".replace(".", ",")


def faixas(field):
    """Faixas de uma calculadora em texto, com a semântica do app: `max` é teto inclusivo."""
    linhas, anterior = [], None
    for banda in field["bands"]:
        teto = banda["max"]
        if teto is None:
            faixa = f"acima de {num(anterior)}" if anterior is not None else "qualquer valor"
        elif anterior is None:
            faixa = f"até {num(teto)}"
        else:
            faixa = f"acima de {num(anterior)} até {num(teto)}"
        linhas.append((faixa, banda["label"]))
        if teto is not None:
            anterior = teto
    return linhas


def rgb(imagem):
    """Converte para RGB compondo a transparência sobre branco (PNG com canal alfa)."""
    if imagem.mode in ("RGBA", "LA") or (imagem.mode == "P" and "transparency" in imagem.info):
        imagem = imagem.convert("RGBA")
        fundo = Image.new("RGB", imagem.size, "white")
        fundo.paste(imagem, mask=imagem.getchannel("A"))
        return fundo
    return imagem.convert("RGB")


def jpeg(imagem, qualidade=85):
    buffer = io.BytesIO()
    rgb(imagem).save(buffer, "JPEG", quality=qualidade, optimize=True)
    return buffer.getvalue()


def rotulo_capitulo(cap):
    return f"Capítulo {cap['number']}" if cap["number"] is not None else cap["title"]


def dividir_parte(parte):
    rotulo, _, titulo = parte.partition(" — ")
    return rotulo, titulo


def agrupar(capitulos):
    """[(parte, [(índice, capítulo), ...]), ...] na ordem do livro."""
    grupos = []
    for idx, cap in enumerate(capitulos, 1):
        if not grupos or grupos[-1][0] != cap["part"]:
            grupos.append((cap["part"], []))
        grupos[-1][1].append((idx, cap))
    return grupos


def svg_declinio(pontos, cor, titulo):
    """Mesmo desenho do gráfico do app: escala logarítmica, linha, área e marcadores."""
    logs = [math.log10(max(1, p["value"])) for p in pontos]
    topo, base = max(logs) + 0.2, min(logs) - 0.2
    n = len(pontos)
    x = lambda i: 16 + i * 288 / max(1, n - 1)
    y = lambda v: 116 - (math.log10(max(1, v)) - base) / (topo - base) * 100
    linha = " ".join(f"{'L' if i else 'M'}{x(i):.1f},{y(p['value']):.1f}" for i, p in enumerate(pontos))
    area = f"{linha} L{x(n - 1):.1f},128 L{x(0):.1f},128 Z"
    marcas = "".join(f'<circle cx="{x(i):.1f}" cy="{y(p["value"]):.1f}" r="4" fill="{cor}"/>'
                     for i, p in enumerate(pontos))
    return (f'<svg xmlns="{SVG_NS}" viewBox="0 0 320 132" role="img" aria-label="{esc(titulo)}">'
            f"<title>{esc(titulo)}</title>"
            f'<path d="{area}" fill="{cor}" fill-opacity="0.12"/>'
            f'<path d="{linha}" fill="none" stroke="{cor}" stroke-width="2.5" stroke-linecap="round"/>'
            f"{marcas}</svg>")


def rosto_html(theme, agora):
    autor = theme["author"]
    credenciais = f"<br/>{esc(autor['credentials'])}" if autor.get("credentials") else ""
    tagline = f'<p class="rosto-tagline">{esc(theme["tagline"])}</p>' if theme.get("tagline") else ""
    local = agora.astimezone()
    return (f'<section class="rosto">{tagline}<h1 class="rosto-titulo">{esc(theme["title"])}</h1>'
            f'<p class="rosto-sub">{esc(theme["subtitle"])}</p>'
            f'<p class="rosto-autor">{esc(autor["name"])}{credenciais}</p>'
            f'<div class="rosto-direitos"><p>© {local.year} {esc(autor["name"])}. Todos os direitos reservados.</p>'
            f"<p>Versão gerada em {local:%d/%m/%Y} a partir do livro-app.</p></div></section>")


# ---------------------------------------------------------------- blocos

class Render:
    """Converte blocos do book.json em XHTML. `modo` muda só caminhos, links e o jeito de aplicar cor."""

    def __init__(self, theme, modo, nome_img):
        self.modo = modo
        self.nome_img = nome_img
        self.cores = theme["colors"]["light"]
        self.testes = []            # (número, capítulo, arquivo, bloco), para o gabarito
        self.com_svg = set()        # arquivos EPUB que precisam de properties="svg"

    def cor(self, tipo):
        cor = self.cores.get("blocks", {}).get(tipo) or self.cores["accent"]
        # leitores de EPUB antigos não entendem oklch(); o PDF (Chrome) entende
        return cor if self.modo == "pdf" or cor.startswith("#") else "#777777"

    def estilo(self, tipo):
        propriedade = "--cor" if self.modo == "pdf" else "border-top-color"
        return f' style="{propriedade}: {self.cor(tipo)}"'

    def img(self, chave):
        return ("../images/" if self.modo == "epub" else "images/") + self.nome_img[chave]

    def cabecalho(self, cap):
        partes = []
        if cap["number"] is not None:
            partes.append(f'<p class="cap-numero">Capítulo {cap["number"]}</p>')
        partes.append(f'<h1 class="cap-titulo">{esc(cap["title"])}</h1>')
        if cap.get("subtitle"):
            partes.append(f'<p class="cap-subtitulo">{esc(cap["subtitle"])}</p>')
        return f'<header class="cap-cabecalho">{"".join(partes)}</header>'

    def corpo(self, cap, arquivo):
        saida, em_referencias = [], False
        lead = next((i for i, b in enumerate(cap["blocks"]) if b["type"] == "p"), -1)
        for i, b in enumerate(cap["blocks"]):
            tipo = b["type"]
            if tipo == "h2":
                em_referencias = b["text"].strip().lower() == "referências"
                saida.append(f"<h2>{esc(b['text'])}</h2>")
            elif tipo == "h3":
                em_referencias = False
                saida.append(f"<h3>{esc(b['text'])}</h3>")
            elif tipo == "p":
                classe = "ref" if em_referencias else ("lead" if i == lead else "")
                abre = f'<p class="{classe}">' if classe else "<p>"
                saida.append(f"{abre}{esc(b['text'])}</p>")
            elif tipo == "image":
                legenda = b.get("caption")
                figcaption = f"<figcaption>{esc(legenda)}</figcaption>" if legenda else ""
                saida.append(f'<figure class="figura"><img src="{self.img(b["key"])}" '
                             f'alt="{esc(legenda or "Figura")}"/>{figcaption}</figure>')
            elif tipo == "table":
                cabeca, *linhas = b["rows"]
                th = "".join(f"<th>{esc(c)}</th>" for c in cabeca)
                corpo = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in linha) + "</tr>" for linha in linhas)
                saida.append(f"<table><thead><tr>{th}</tr></thead><tbody>{corpo}</tbody></table>")
            elif tipo == "pullquote":
                saida.append(f'<blockquote class="destaque"><p>{esc(b["text"])}</p></blockquote>')
            elif tipo == "video":
                legenda = esc(b.get("caption") or "Vídeo")
                aviso = '<span class="nota-app"> O vídeo está disponível na versão app do livro.</span>'
                if b.get("poster") in self.nome_img:
                    saida.append(f'<figure class="figura"><img src="{self.img(b["poster"])}" alt="{legenda}"/>'
                                 f"<figcaption>{legenda}{aviso}</figcaption></figure>")
                else:
                    saida.append(f'<p class="nota">{legenda}{aviso}</p>')
            elif tipo == "quiz":
                n = len(self.testes) + 1
                self.testes.append((n, cap, arquivo, b))
                alternativas = "".join(f"<li>{esc(o)}</li>" for o in b["options"])
                alvo = f"gabarito.xhtml#resposta-{n}" if self.modo == "epub" else f"#resposta-{n}"
                saida.append(f'<div class="bloco" id="teste-{n}"{self.estilo("quiz")}>'
                             f'<p class="bloco-rotulo">Teste rápido {n}</p>'
                             f'<p class="bloco-pergunta">{esc(b["question"])}</p>'
                             f'<ol class="alternativas" type="a">{alternativas}</ol>'
                             f'<p class="nota"><a href="{alvo}">Ver a resposta</a></p></div>')
            elif tipo == "flashcard":
                cartoes = "".join(f"<dt>{esc(c['front'])}</dt><dd>{esc(c['back'])}</dd>" for c in b["cards"])
                saida.append(f'<div class="bloco"{self.estilo("flashcard")}>'
                             f'<p class="bloco-rotulo">{esc(b.get("title") or "Revisão rápida")}</p>'
                             f'<dl class="cartoes">{cartoes}</dl></div>')
            elif tipo == "calc":
                partes = [f'<p class="bloco-rotulo">{esc(b["title"])}</p>']
                if b["kind"] == "poseidon":
                    linhas = "".join(f"<tr><td>{esc(g['label'])}</td><td>{esc(g['detail'])}</td>"
                                     f"<td>{esc(g['clbr'])}</td><td>{esc(g['clbr3'])}</td></tr>" for g in b["groups"])
                    partes.append("<table><caption>Taxa acumulada de nascidos vivos</caption><thead><tr>"
                                  "<th>Grupo</th><th>Perfil</th><th>Por ciclo iniciado</th><th>Após 3 ciclos</th>"
                                  f"</tr></thead><tbody>{linhas}</tbody></table>")
                else:
                    for campo in b["fields"]:
                        unidade = f" ({esc(campo['unit'])})" if campo.get("unit") else ""
                        linhas = "".join(f"<tr><td>{esc(fx)}</td><td>{esc(rot)}</td></tr>" for fx, rot in faixas(campo))
                        partes.append(f"<table><caption>{esc(campo['label'])}</caption><thead><tr>"
                                      f"<th>Valor{unidade}</th><th>Interpretação</th></tr></thead>"
                                      f"<tbody>{linhas}</tbody></table>")
                if b.get("note"):
                    partes.append(f'<p class="nota">{esc(b["note"])}</p>')
                saida.append(f'<div class="bloco"{self.estilo("calc")}>{"".join(partes)}</div>')
            elif tipo == "chart":
                self.com_svg.add(arquivo)
                linhas = "".join(f"<tr><td>{esc(p['stage'])}</td><td>{esc(p['text'])}</td></tr>" for p in b["points"])
                nota = f'<p class="nota">{esc(b["note"])}</p>' if b.get("note") else ""
                saida.append(f'<div class="bloco"{self.estilo("chart")}>'
                             f'<p class="bloco-rotulo">{esc(b["title"])}</p>'
                             f'{svg_declinio(b["points"], self.cor("chart"), b["title"])}'
                             f"<table><thead><tr><th>Etapa</th><th>Valor</th></tr></thead>"
                             f"<tbody>{linhas}</tbody></table>{nota}</div>")
            else:
                raise SystemExit(f"ERRO: bloco '{tipo}' ({cap['id']}) não tem exportação para PDF/EPUB; "
                                 "defina-a em fabrica/exportar.py")
        return "".join(saida)

    def gabarito(self):
        itens = []
        for n, cap, arquivo, b in self.testes:
            letra = chr(97 + b["answer"])
            volta = f"{arquivo}#teste-{n}" if self.modo == "epub" else f"#teste-{n}"
            explicacao = f'<p class="nota">{esc(b["explanation"])}</p>' if b.get("explanation") else ""
            itens.append(f'<div class="resposta" id="resposta-{n}">'
                         f'<p class="resposta-cab">Teste rápido {n} · {esc(rotulo_capitulo(cap))}</p>'
                         f"<p>{esc(b['question'])}</p>"
                         f"<p><strong>Resposta: {letra})</strong> {esc(b['options'][b['answer']])}</p>"
                         f'{explicacao}<p class="nota"><a href="{volta}">Voltar ao teste</a></p></div>')
        return ('<header class="cap-cabecalho"><h1 class="cap-titulo">Respostas dos testes rápidos</h1></header>'
                + "".join(itens))


# ---------------------------------------------------------------- EPUB

CSS_EPUB = Template("""
body { margin: 0 3%; line-height: 1.5; }
.capa { margin: 0; padding: 0; text-align: center; }
.capa img { max-width: 100%; height: auto; }
.rosto { text-align: center; margin-top: 15%; }
.rosto-tagline, .cap-numero, .parte-rotulo, .bloco-rotulo, .resposta-cab {
  font-family: sans-serif; font-size: 0.72em; font-weight: bold; letter-spacing: 0.12em; text-transform: uppercase; }
.rosto-titulo { font-size: 2em; line-height: 1.15; margin: 0.4em 0; }
.rosto-sub { font-size: 1.1em; margin: 0 0 2em; }
.rosto-autor { font-family: sans-serif; font-size: 0.9em; }
.rosto-direitos { margin-top: 4em; font-size: 0.75em; }
.parte-cabecalho { margin: 0.5em 0 2em; padding-bottom: 1em; border-bottom: 1px solid #999999; }
.parte-titulo { font-size: 1.3em; margin: 0.2em 0 0; }
.cap-cabecalho { margin: 0 0 1.6em; }
.cap-numero { margin: 1.2em 0 0.3em; }
h1.cap-titulo { font-size: 1.7em; line-height: 1.15; margin: 0 0 0.3em; }
.cap-subtitulo { font-style: italic; margin: 0; }
h2 { font-family: sans-serif; font-size: 1.15em; line-height: 1.25; margin: 1.6em 0 0.5em; page-break-after: avoid; }
h3 { font-family: sans-serif; font-size: 0.8em; letter-spacing: 0.1em; text-transform: uppercase; margin: 1.2em 0 0.4em; page-break-after: avoid; }
p { margin: 0 0 0.75em; }
p.lead { font-size: 1.1em; }
p.lead::first-letter { float: left; font-size: 3em; line-height: 0.85; margin: 0.04em 0.08em 0 0; font-weight: bold; }
p.ref { font-size: 0.85em; margin-bottom: 0.4em; padding-left: 1.6em; text-indent: -1.6em; }
figure { margin: 1.3em 0; page-break-inside: avoid; }
figure img { display: block; max-width: 100%; height: auto; margin: 0 auto; }
figcaption, .nota { font-family: sans-serif; font-size: 0.78em; line-height: 1.4; }
figcaption { margin-top: 0.4em; }
.nota-app { font-style: italic; }
table { width: 100%; border-collapse: collapse; margin: 0.8em 0; font-size: 0.8em; }
caption { font-weight: bold; text-align: left; margin-bottom: 0.3em; }
th, td { border: 1px solid #999999; padding: 0.3em 0.4em; text-align: left; vertical-align: top; }
blockquote.destaque { margin: 1.5em 0; padding: 0 0 0 0.9em; border-left: 3px solid $accent; font-size: 1.15em; font-weight: bold; }
.bloco { margin: 1.5em 0; padding: 0.7em 0.9em; border: 1px solid #999999; border-top-width: 4px; page-break-inside: avoid; }
.bloco-pergunta { font-weight: bold; }
ol.alternativas { margin: 0.4em 0 0.6em 1.4em; padding: 0; }
dl.cartoes { margin: 0; }
dl.cartoes dt { font-weight: bold; margin-top: 0.7em; }
dl.cartoes dd { margin: 0.2em 0 0; }
.bloco svg { width: 100%; height: auto; }
.resposta { margin: 0 0 1.3em; padding-bottom: 1em; border-bottom: 1px solid #cccccc; }
nav ol { list-style: none; padding-left: 0; }
nav ol ol { padding-left: 1.2em; }
nav li { margin: 0.35em 0; }
nav span { font-weight: bold; }
""")

CONTAINER = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
             '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
             "</rootfiles></container>")


def pagina_xhtml(titulo, corpo, css, lang):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE html>\n'
            f'<html xmlns="{XHTML_NS}" xmlns:epub="http://www.idpf.org/2007/ops" lang="{lang}" xml:lang="{lang}">'
            f'<head><meta charset="UTF-8"/><title>{esc(titulo)}</title>'
            f'<link rel="stylesheet" type="text/css" href="{css}"/></head><body>{corpo}</body></html>')


def montar_epub(book, theme, imagens, nome_img, capa, destino, agora=None):
    agora = agora or datetime.now(timezone.utc)
    lang = theme.get("lang", "pt-BR")
    titulo, autor = theme["title"], theme["author"]["name"]
    uid = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, 'livro-app:' + theme['id'])}"
    capitulos = book["chapters"]
    render = Render(theme, "epub", nome_img)

    docs = [("capa", "text/capa.xhtml", pagina_xhtml(
                titulo, f'<section epub:type="cover" class="capa"><img src="../images/{CAPA_ARQUIVO}" '
                        f'alt="Capa: {esc(titulo)}"/></section>', "../css/livro.css", lang), ""),
            ("rosto", "text/rosto.xhtml", pagina_xhtml(titulo, rosto_html(theme, agora), "../css/livro.css", lang), "")]
    anterior = None
    for idx, cap in enumerate(capitulos, 1):
        arquivo = f"cap-{idx:02d}.xhtml"
        parte = ""
        if cap["part"] != "Abertura" and cap["part"] != anterior:
            rotulo, subtitulo = dividir_parte(cap["part"])
            parte = (f'<div class="parte-cabecalho"><p class="parte-rotulo">{esc(rotulo)}</p>'
                     + (f'<p class="parte-titulo">{esc(subtitulo)}</p>' if subtitulo else "") + "</div>")
        anterior = cap["part"]
        corpo = parte + render.cabecalho(cap) + render.corpo(cap, arquivo)
        docs.append((f"cap-{idx:02d}", f"text/{arquivo}", pagina_xhtml(cap["title"], corpo, "../css/livro.css", lang),
                     "svg" if arquivo in render.com_svg else ""))
    if render.testes:
        docs.append(("gabarito", "text/gabarito.xhtml",
                     pagina_xhtml("Respostas dos testes rápidos", render.gabarito(), "../css/livro.css", lang), ""))

    # sumário (nav) e toc.ncx para leitores antigos
    def item_nav(idx, cap):
        rotulo = f"{rotulo_capitulo(cap)} — {cap['title']}" if cap["number"] is not None else cap["title"]
        return f'<li><a href="text/cap-{idx:02d}.xhtml">{esc(rotulo)}</a></li>'

    itens = []
    for parte, caps in agrupar(capitulos):
        if parte == "Abertura":
            itens.extend(item_nav(i, c) for i, c in caps)
        else:
            itens.append(f"<li><span>{esc(parte)}</span><ol>{''.join(item_nav(i, c) for i, c in caps)}</ol></li>")
    if render.testes:
        itens.append('<li><a href="text/gabarito.xhtml">Respostas dos testes rápidos</a></li>')
    inicio = next((i for i, c in enumerate(capitulos, 1) if c["number"] is not None), 1)
    nav = pagina_xhtml("Sumário",
                       f'<nav epub:type="toc" id="toc"><h1>Sumário</h1><ol>{"".join(itens)}</ol></nav>'
                       '<nav epub:type="landmarks" hidden=""><ol>'
                       '<li><a epub:type="cover" href="text/capa.xhtml">Capa</a></li>'
                       '<li><a epub:type="toc" href="nav.xhtml#toc">Sumário</a></li>'
                       f'<li><a epub:type="bodymatter" href="text/cap-{inicio:02d}.xhtml">Início da leitura</a></li>'
                       "</ol></nav>", "css/livro.css", lang)

    pontos = []
    for ordem, (idx, cap) in enumerate(enumerate(capitulos, 1), 1):
        rotulo = f"{rotulo_capitulo(cap)} — {cap['title']}" if cap["number"] is not None else cap["title"]
        pontos.append(f'<navPoint id="np-{ordem}" playOrder="{ordem}"><navLabel><text>{esc(rotulo)}</text>'
                      f'</navLabel><content src="text/cap-{idx:02d}.xhtml"/></navPoint>')
    ncx = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="{lang}">'
           f'<head><meta name="dtb:uid" content="{uid}"/><meta name="dtb:depth" content="1"/>'
           '<meta name="dtb:totalPageCount" content="0"/><meta name="dtb:maxPageNumber" content="0"/></head>'
           f"<docTitle><text>{esc(titulo)}</text></docTitle><navMap>{''.join(pontos)}</navMap></ncx>")

    manifest = ['<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
                '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
                '<item id="css" href="css/livro.css" media-type="text/css"/>',
                f'<item id="capa-imagem" href="images/{CAPA_ARQUIVO}" media-type="image/jpeg" properties="cover-image"/>']
    for id_, href, _, props in docs:
        extra = f' properties="{props}"' if props else ""
        manifest.append(f'<item id="{id_}" href="{href}" media-type="application/xhtml+xml"{extra}/>')
    for n, nome in enumerate(sorted(imagens), 1):
        manifest.append(f'<item id="img-{n:03d}" href="images/{esc(nome)}" media-type="image/jpeg"/>')
    spine = ['<itemref idref="capa"/>', '<itemref idref="rosto"/>', '<itemref idref="nav"/>']
    spine += [f'<itemref idref="{id_}"/>' for id_, *_ in docs[2:]]
    direitos = f"© {agora.astimezone().year} {autor}. Todos os direitos reservados."
    opf = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<package xmlns="{OPF_NS}" version="3.0" unique-identifier="bookid" xml:lang="{lang}">'
           '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
           f'<dc:identifier id="bookid">{uid}</dc:identifier><dc:title>{esc(titulo)}</dc:title>'
           f"<dc:creator>{esc(autor)}</dc:creator><dc:language>{lang}</dc:language>"
           f"<dc:description>{esc(theme.get('description', ''))}</dc:description>"
           f"<dc:rights>{esc(direitos)}</dc:rights><dc:date>{agora:%Y-%m-%d}</dc:date>"
           f'<meta property="dcterms:modified">{agora:%Y-%m-%dT%H:%M:%SZ}</meta>'
           '<meta name="cover" content="capa-imagem"/></metadata>'
           f"<manifest>{''.join(manifest)}</manifest><spine toc=\"ncx\">{''.join(spine)}</spine></package>")

    accent = theme["colors"]["light"]["accent"]
    with zipfile.ZipFile(destino, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        escrever = lambda nome, dados: z.writestr(nome, dados, compress_type=zipfile.ZIP_DEFLATED)
        escrever("META-INF/container.xml", CONTAINER)
        escrever("OEBPS/content.opf", opf)
        escrever("OEBPS/nav.xhtml", nav)
        escrever("OEBPS/toc.ncx", ncx)
        escrever("OEBPS/css/livro.css", CSS_EPUB.substitute(accent=accent if accent.startswith("#") else "#777777"))
        for _, href, conteudo, _ in docs:
            escrever(f"OEBPS/{href}", conteudo)
        escrever(f"OEBPS/images/{CAPA_ARQUIVO}", capa)
        for nome, dados in imagens.items():
            escrever(f"OEBPS/images/{nome}", dados)
    return render


def conferir_epub(arquivo_epub):
    """Checagem estrutural do EPUB, no espírito do epubcheck. Retorna a lista de problemas."""
    erros = []
    ns = {"o": OPF_NS}
    with zipfile.ZipFile(arquivo_epub) as z:
        primeiro = z.infolist()[0]
        if (primeiro.filename != "mimetype" or primeiro.compress_type != zipfile.ZIP_STORED
                or z.read("mimetype") != b"application/epub+zip"):
            erros.append("mimetype precisa ser o primeiro arquivo, sem compressão")
        nomes = set(z.namelist())
        try:
            container = ET.fromstring(z.read("META-INF/container.xml"))
            opf_path = container.find(".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile").get("full-path")
            opf = ET.fromstring(z.read(opf_path))
        except Exception as exc:  # noqa: BLE001 — qualquer falha aqui invalida o arquivo inteiro
            return erros + [f"container.xml ou OPF ilegível: {exc}"]
        base = posixpath.dirname(opf_path)
        itens = {}
        for item in opf.findall("o:manifest/o:item", ns):
            caminho = posixpath.normpath(posixpath.join(base, item.get("href")))
            itens[caminho] = item
            if caminho not in nomes:
                erros.append(f"manifest aponta para arquivo inexistente: {caminho}")
        for sobra in sorted(nomes - set(itens) - {"mimetype", "META-INF/container.xml", opf_path}):
            erros.append(f"arquivo fora do manifest: {sobra}")
        ids = {item.get("id") for item in itens.values()}
        for ref in opf.findall("o:spine/o:itemref", ns):
            if ref.get("idref") not in ids:
                erros.append(f"spine referencia id inexistente: {ref.get('idref')}")
        propriedades = {c: (i.get("properties") or "").split() for c, i in itens.items()}
        if sum("nav" in p for p in propriedades.values()) != 1:
            erros.append("é preciso exatamente um documento com properties=nav")
        if sum("cover-image" in p for p in propriedades.values()) != 1:
            erros.append("é preciso exatamente uma imagem com properties=cover-image")

        docs = {}
        for caminho, item in itens.items():
            if item.get("media-type") == "application/xhtml+xml" and caminho in nomes:
                try:
                    docs[caminho] = ET.fromstring(z.read(caminho))
                except ET.ParseError as exc:
                    erros.append(f"{caminho}: XHTML mal formado ({exc})")
        ancoras = {c: {e.get("id") for e in raiz.iter() if e.get("id")} for c, raiz in docs.items()}
        for caminho, raiz in docs.items():
            tem_svg = raiz.find(f".//{{{SVG_NS}}}svg") is not None
            if tem_svg != ("svg" in propriedades[caminho]):
                erros.append(f"{caminho}: properties=svg não corresponde à presença de SVG")
            pasta = posixpath.dirname(caminho)
            for img in raiz.iter(f"{{{XHTML_NS}}}img"):
                alvo = posixpath.normpath(posixpath.join(pasta, img.get("src", "")))
                if alvo not in itens:
                    erros.append(f"{caminho}: imagem fora do manifest: {img.get('src')}")
            for link in raiz.iter(f"{{{XHTML_NS}}}a"):
                href = link.get("href", "")
                if not href or re.match(r"^[a-z][a-z0-9+.-]*:", href):
                    continue
                parte_arquivo, _, fragmento = href.partition("#")
                alvo = posixpath.normpath(posixpath.join(pasta, parte_arquivo)) if parte_arquivo else caminho
                if alvo not in docs:
                    erros.append(f"{caminho}: link para documento inexistente: {href}")
                elif fragmento and fragmento not in ancoras[alvo]:
                    erros.append(f"{caminho}: âncora inexistente: {href}")
        for caminho, item in itens.items():
            if item.get("media-type") == "application/x-dtbncx+xml" and caminho in nomes:
                ncx = ET.fromstring(z.read(caminho))
                for conteudo in ncx.iter("{http://www.daisy.org/z3986/2005/ncx/}content"):
                    alvo = posixpath.normpath(posixpath.join(posixpath.dirname(caminho), conteudo.get("src", "")))
                    if alvo.partition("#")[0] not in docs:
                        erros.append(f"toc.ncx aponta para documento inexistente: {conteudo.get('src')}")
    return erros


# ---------------------------------------------------------------- PDF

CSS_PDF = Template("""
@page { size: ${largura}mm ${altura}mm; margin: 21mm 18mm 23mm;
  @top-center { content: "$titulo_css"; font-family: "$sans", sans-serif; font-size: 7pt; font-weight: 700;
    letter-spacing: 0.14em; text-transform: uppercase; color: $muted; }
  @bottom-center { content: counter(page); font-family: "$serif", Georgia, serif; font-size: 8.5pt; color: $muted; } }
@page capa { margin: 0; @top-center { content: none; } @bottom-center { content: none; } }
@page divisor { margin: 0; @top-center { content: none; } @bottom-center { content: none; } }
@page semcabecalho { @top-center { content: none; } }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; font-family: "$serif", Georgia, serif; font-size: 10.4pt; line-height: 1.56; color: $fg; }
a { color: $accent; }
/* sem isto o Chrome cola as palavras da quebra de linha nos marcadores laterais do PDF */
h1, h2, h3 { white-space: break-spaces; }
.capa-pdf { page: capa; break-after: page; width: ${largura}mm; height: ${altura}mm; overflow: hidden; background: $primary; }
.capa-pdf img { display: block; width: ${largura}mm; height: ${altura}mm; object-fit: contain; }
.rosto { page: semcabecalho; break-after: page; text-align: center; padding-top: 36mm; }
.rosto-tagline { font: 700 7.5pt "$sans", sans-serif; letter-spacing: 0.18em; text-transform: uppercase; color: $accent; margin: 0 0 6mm; }
.rosto-titulo { font-size: 28pt; line-height: 1.1; margin: 0; }
.rosto-sub { font-size: 12pt; margin: 4mm 10mm 22mm; color: $muted; }
.rosto-autor { font: 600 10pt/1.5 "$sans", sans-serif; }
.rosto-direitos { margin-top: 58mm; font: 7.5pt/1.5 "$sans", sans-serif; color: $muted; }
.rosto-direitos p { margin: 0; }
.sumario { page: semcabecalho; break-after: page; }
.sumario h1 { font-size: 20pt; margin: 6mm 0 5mm; }
.toc-parte { font: 700 7pt "$sans", sans-serif; letter-spacing: 0.16em; text-transform: uppercase; color: $accent; margin: 5mm 0 1mm; }
.toc-parte span { display: block; font: 600 10.5pt "$serif", Georgia, serif; letter-spacing: 0; text-transform: none; color: $fg; margin-top: 0.8mm; }
.sumario a { display: flex; gap: 3mm; padding: 1.3mm 0; border-bottom: 0.2mm solid $border; color: $fg; text-decoration: none; font-size: 10pt; }
.sumario .num { flex: 0 0 7mm; font: 700 8.5pt "$sans", sans-serif; color: $accent; padding-top: 0.5mm; }
.parte { page: divisor; break-before: page; break-after: page; box-sizing: border-box; width: ${largura}mm; height: ${altura}mm;
  padding: 0 22mm; background: $primary; color: $primary_fg; display: flex; flex-direction: column; justify-content: center; }
.parte-rotulo { font: 700 9pt "$sans", sans-serif; letter-spacing: 0.2em; text-transform: uppercase; color: $ouro; margin: 0 0 5mm; }
.parte-titulo { font-size: 24pt; line-height: 1.15; font-weight: 700; margin: 0; }
.capitulo { break-before: page; }
.cap-cabecalho { margin: 8mm 0 8mm; }
.cap-numero { font: 700 7.5pt "$sans", sans-serif; letter-spacing: 0.18em; text-transform: uppercase; color: $accent; margin: 0 0 2.5mm; }
.cap-titulo { font-size: 22pt; line-height: 1.12; margin: 0; }
.cap-subtitulo { font-style: italic; color: $muted; margin: 2mm 0 0; }
h2 { font: 700 12.5pt/1.25 "$sans", sans-serif; color: $accent; margin: 7mm 0 2.5mm; break-after: avoid; }
h2::before { content: ""; display: block; width: 9mm; height: 0.7mm; border-radius: 0.5mm; background: $accent; margin-bottom: 2.4mm; }
h3 { font: 700 8pt "$sans", sans-serif; letter-spacing: 0.12em; text-transform: uppercase; color: $muted; margin: 5mm 0 2mm; break-after: avoid; }
p { margin: 0 0 2.5mm; orphans: 3; widows: 3; }
p.lead { font-size: 11.6pt; line-height: 1.5; }
p.lead::first-letter { float: left; font-size: 3.35em; line-height: 0.8; font-weight: 700; color: $accent; margin: 0.05em 0.07em 0 0; }
p.ref { font-size: 8.3pt; line-height: 1.4; padding-left: 5mm; text-indent: -5mm; margin-bottom: 1.2mm; break-inside: avoid; }
figure { margin: 5mm 0; break-inside: avoid; }
figure img { display: block; max-width: 100%; max-height: 168mm; margin: 0 auto; }
figcaption, .nota { font: 7.8pt/1.45 "$sans", sans-serif; color: $muted; }
figcaption { margin-top: 2mm; }
.nota { margin: 2mm 0 0; }
.nota-app { font-style: italic; }
table { width: 100%; border-collapse: collapse; font: 7.6pt/1.35 "$sans", sans-serif; margin: 4mm 0; }
caption { text-align: left; font-weight: 700; margin-bottom: 1.2mm; }
thead { display: table-header-group; }
th { background: $surface; font-weight: 700; text-align: left; }
th, td { border-bottom: 0.25mm solid $border; padding: 1.3mm 1.6mm; vertical-align: top; }
tr { break-inside: avoid; }
blockquote.destaque { margin: 6mm 0; padding: 0.5mm 0 0.5mm 4.5mm; border-left: 0.9mm solid $accent; font-size: 13pt; line-height: 1.38; font-weight: 600; break-inside: avoid; }
blockquote.destaque p { margin: 0; }
.bloco { margin: 5mm 0; padding: 3.2mm 4mm 3.6mm; border: 0.25mm solid $border; border-top: 1.1mm solid var(--cor); border-radius: 1.8mm; break-inside: avoid; }
.bloco-rotulo { font: 700 7.2pt "$sans", sans-serif; letter-spacing: 0.12em; text-transform: uppercase; color: var(--cor); margin: 0 0 2mm; }
.bloco-pergunta { font-weight: 600; margin-bottom: 1.5mm; }
ol.alternativas { margin: 0 0 1.5mm 5.5mm; padding: 0; }
ol.alternativas li { margin: 0.8mm 0; }
dl.cartoes { margin: 0; }
dl.cartoes dt { font-weight: 700; margin-top: 2.4mm; }
dl.cartoes dt:first-child { margin-top: 0; }
dl.cartoes dd { margin: 0.6mm 0 0; }
.bloco svg { display: block; width: 100%; height: auto; margin: 1mm 0 2mm; }
.bloco table { margin: 2mm 0; }
/* a coluna de faixas não pode quebrar "acima de 2 até 4" no meio do número */
.bloco th:first-child, .bloco td:first-child { white-space: nowrap; width: 1%; }
/* rótulo e título da parte seguem junto com o primeiro capítulo: nunca ficam sozinhos no pé da página */
.toc-bloco { break-inside: avoid; }
.resposta { break-inside: avoid; padding: 0 0 3mm; margin: 0 0 3.5mm; border-bottom: 0.25mm solid $border; }
.resposta-cab { font: 700 7.5pt "$sans", sans-serif; letter-spacing: 0.1em; text-transform: uppercase; color: $accent; margin-bottom: 1mm; }
""")


def html_pdf(book, theme, nome_img, fontes, agora):
    capitulos = book["chapters"]
    render = Render(theme, "pdf", nome_img)
    corpo, anterior = [], None
    for idx, cap in enumerate(capitulos, 1):
        if cap["part"] != "Abertura" and cap["part"] != anterior:
            rotulo, subtitulo = dividir_parte(cap["part"])
            corpo.append(f'<section class="parte"><p class="parte-rotulo">{esc(rotulo)}</p>'
                         + (f'<p class="parte-titulo">{esc(subtitulo)}</p>' if subtitulo else "") + "</section>")
        anterior = cap["part"]
        corpo.append(f'<section class="capitulo" id="cap-{idx}">{render.cabecalho(cap)}{render.corpo(cap, "")}</section>')
    if render.testes:
        corpo.append(f'<section class="capitulo" id="gabarito">{render.gabarito()}</section>')

    sumario = ['<section class="sumario"><h1>Sumário</h1>']
    for parte, caps in agrupar(capitulos):
        links = []
        for idx, cap in caps:
            numero = cap["number"] if cap["number"] is not None else ""
            links.append(f'<a href="#cap-{idx}"><span class="num">{numero}</span><span>{esc(cap["title"])}</span></a>')
        if parte != "Abertura":
            rotulo, subtitulo = dividir_parte(parte)
            cabeca = f'<p class="toc-parte">{esc(rotulo)}' + (f"<span>{esc(subtitulo)}</span>" if subtitulo else "") + "</p>"
            links[0] = f'<div class="toc-bloco">{cabeca}{links[0]}</div>'
        sumario.extend(links)
    if render.testes:
        sumario.append('<a href="#gabarito"><span class="num"></span><span>Respostas dos testes rápidos</span></a>')
    sumario.append("</section>")

    claro, escuro = theme["colors"]["light"], theme["colors"]["dark"]
    fg = claro["foreground"]
    css = CSS_PDF.substitute(
        largura=PAGINA_MM[0], altura=PAGINA_MM[1],
        titulo_css=theme["title"].replace("\\", "\\\\").replace('"', '\\"'),
        sans=theme["fonts"]["sans"], serif=theme["fonts"]["serif"], fg=fg, accent=claro["accent"],
        primary=claro["primary"], primary_fg=claro["primaryForeground"], ouro=escuro["accent"],
        surface=claro["background"],
        muted=f"color-mix(in oklab, {fg} 58%, white)", border=f"color-mix(in oklab, {fg} 16%, white)")
    lang = theme.get("lang", "pt-BR")
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"/><title>{esc(theme["title"])}</title>'
            f'<meta name="author" content="{esc(theme["author"]["name"])}"/><style>{fontes}{css}</style></head><body>'
            f'<section class="capa-pdf"><img src="images/{CAPA_ARQUIVO}" alt="Capa"/></section>'
            f'{rosto_html(theme, agora)}{"".join(sumario)}{"".join(corpo)}</body></html>')


# ---------------------------------------------------------------- Chrome, fontes, imagens, capa

def achar_chrome():
    candidatos = [os.environ.get("CHROME"),
                  r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                  r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                  shutil.which("chrome"), shutil.which("google-chrome"), shutil.which("chromium")]
    candidatos += sorted(glob.glob(os.path.expanduser(r"~\AppData\Local\ms-playwright\chromium-*\chrome-win64\chrome.exe")),
                         reverse=True)
    return next((c for c in candidatos if c and Path(c).exists()), None)


def chrome(executavel, *argumentos):
    # perfil temporário: não interfere no Chrome aberto do usuário
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as perfil:
        return subprocess.run([executavel, "--headless", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                               "--hide-scrollbars", f"--user-data-dir={perfil}", *argumentos],
                              capture_output=True, text=True, timeout=600)


def baixar(url):
    pedido = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(pedido, timeout=30) as resposta:
        return resposta.read()


def fontes_css(theme):
    """@font-face das fontes do tema embutidas em base64 (sem depender de rede na hora de imprimir)."""
    fontes = theme["fonts"]
    url = ("https://fonts.googleapis.com/css2?family=" + urllib.parse.quote_plus(fontes["sans"])
           + ":wght@400;500;600;700;800&family=" + urllib.parse.quote_plus(fontes["serif"])
           + ":ital,wght@0,400;0,600;0,700;1,400&display=swap")
    try:
        css = baixar(url).decode("utf-8")
        cache, saida = {}, []
        for subconjunto, bloco in re.findall(r"/\* ([a-z-]+) \*/\s*(@font-face\s*\{.*?\})", css, re.S):
            if subconjunto not in SUBCONJUNTOS_FONTE:
                continue

            def embutir(m):
                if m.group(1) not in cache:
                    cache[m.group(1)] = base64.b64encode(baixar(m.group(1))).decode("ascii")
                return f"url(data:font/woff2;base64,{cache[m.group(1)]})"

            saida.append(re.sub(r"url\((https://[^)]+)\)", embutir, bloco))
        return "\n".join(saida)
    except Exception as exc:  # noqa: BLE001 — sem rede, o PDF sai com fontes do sistema
        print(f"AVISO: fontes do tema não baixadas ({exc}); o PDF usará fontes do sistema.")
        return ""


def preparar_imagens(root, book):
    chaves = []
    for cap in book["chapters"]:
        for b in cap["blocks"]:
            if b["type"] == "image":
                chaves.append(b["key"])
            elif b["type"] == "video" and b.get("poster"):
                chaves.append(b["poster"])
    imagens, nome_img = {}, {}
    for chave in dict.fromkeys(chaves):
        nome = re.sub(r"[^A-Za-z0-9_-]+", "-", Path(chave).stem) + ".jpg"
        if nome in imagens or nome == CAPA_ARQUIVO:
            raise SystemExit(f"ERRO: duas imagens viram o mesmo arquivo '{nome}' ao converter para JPEG ({chave})")
        imagem = rgb(Image.open(root / "content" / "images" / chave))
        imagem.thumbnail((IMAGEM_MAX, IMAGEM_MAX), Image.LANCZOS)
        imagens[nome], nome_img[chave] = jpeg(imagem), nome
    return imagens, nome_img


CAPA_HTML = Template("""<!doctype html><html><head><meta charset="utf-8"><style>$fontes
html, body { margin: 0; width: ${w}px; height: ${h}px; overflow: hidden; background: $prim; }
.arte { position: absolute; left: 0; top: ${arte_topo}px; width: ${w}px; height: ${arte_h}px;
  background: url(data:image/jpeg;base64,$arte) center / cover no-repeat; }
.arte::before, .arte::after { content: ""; position: absolute; left: 0; right: 0; height: 280px; }
.arte::before { top: 0; background: linear-gradient($prim, transparent); }
.arte::after { bottom: 0; background: linear-gradient(transparent, $prim); }
.topo { position: absolute; left: 150px; right: 150px; top: 250px; color: $fg; }
.tagline { font: 700 42px "$sans", sans-serif; letter-spacing: 0.2em; text-transform: uppercase; color: $ouro; margin: 0 0 48px; }
h1 { font: 700 188px/1.02 "$serif", Georgia, serif; margin: 0; }
.sub { font: 500 60px/1.3 "$sans", sans-serif; margin: 52px 0 0; opacity: 0.9; }
.autor { position: absolute; left: 150px; right: 150px; bottom: 190px; color: $fg; font: 600 52px/1.35 "$sans", sans-serif; }
.autor span { display: block; font-weight: 400; font-size: 40px; opacity: 0.78; }
</style></head><body><div class="arte"></div>
<div class="topo"><p class="tagline">$tagline</p><h1>$titulo</h1><p class="sub">$subtitulo</p></div>
<div class="autor">$autor<span>$credenciais</span></div></body></html>""")


def preparar_capa(root, theme, fontes, executavel, pasta):
    """Capa em pé: usa a arte como está. Arte deitada: compõe uma capa em pé com título e autor."""
    arte = rgb(Image.open(root / "content" / theme["cover"]))
    if arte.height >= arte.width:
        arte.thumbnail(CAPA_PX, Image.LANCZOS)
        return jpeg(arte, 90), "arte original em pé"
    if executavel:
        w, h = CAPA_PX
        arte_h = round(arte.height * w / arte.width)
        faixa = base64.b64encode(jpeg(arte.resize((w, arte_h), Image.LANCZOS), 90)).decode("ascii")
        claro, escuro = theme["colors"]["light"], theme["colors"]["dark"]
        pagina = CAPA_HTML.substitute(
            fontes=fontes, w=w, h=h, arte=faixa, arte_h=arte_h, arte_topo=min(1040, h - arte_h - 330),
            prim=claro["primary"], fg=claro["primaryForeground"], ouro=escuro["accent"],
            sans=theme["fonts"]["sans"], serif=theme["fonts"]["serif"],
            tagline=esc(theme.get("tagline", "")), titulo=esc(theme["title"]), subtitulo=esc(theme["subtitle"]),
            autor=esc(theme["author"]["name"]), credenciais=esc(theme["author"].get("credentials", "")))
        origem, png = pasta / "capa.html", pasta / "capa.png"
        origem.write_text(pagina, encoding="utf-8")
        chrome(executavel, f"--window-size={w},{h}", "--force-device-scale-factor=1", f"--screenshot={png}",
               origem.resolve().as_uri())
        if png.exists():
            composta = Image.open(png)
            if composta.size != CAPA_PX:
                composta = composta.resize(CAPA_PX, Image.LANCZOS)
            return jpeg(composta, 90), "composta a partir da arte deitada"
    print("AVISO: sem Chrome para compor a capa; usando um recorte da arte deitada.")
    return jpeg(ImageOps.fit(arte, CAPA_PX), 90), "recorte da arte deitada"


# ---------------------------------------------------------------- orquestração

def exportar(root, com_pdf=True):
    root = root.resolve()
    slug = root.name
    book = json.loads((root / "content/book.json").read_text(encoding="utf-8"))
    theme = json.loads((root / "content/theme.json").read_text(encoding="utf-8"))
    saida = root / "exportacoes"
    saida.mkdir(exist_ok=True)
    agora = datetime.now(timezone.utc)
    executavel = achar_chrome()
    imagens, nome_img = preparar_imagens(root, book)
    fontes = fontes_css(theme) if executavel else ""

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp = Path(tmp)
        capa, origem_capa = preparar_capa(root, theme, fontes, executavel, tmp)

        epub = saida / f"{slug}.epub"
        render = montar_epub(book, theme, imagens, nome_img, capa, epub, agora)
        erros = conferir_epub(epub)
        if erros:
            print(f"ERRO: EPUB com {len(erros)} problema(s):")
            for erro in erros:
                print(f"  - {erro}")
            return 1
        print(f"EPUB  {epub.relative_to(root.parent)}  {epub.stat().st_size / 1e6:.1f} MB | "
              f"{len(book['chapters'])} seções, {len(imagens)} imagens, {len(render.testes)} testes | estrutura conferida")

        if com_pdf:
            if not executavel:
                print("ERRO: Chrome não encontrado; defina a variável CHROME para gerar o PDF.")
                return 1
            (tmp / "images").mkdir()
            (tmp / "images" / CAPA_ARQUIVO).write_bytes(capa)
            for nome, dados in imagens.items():
                (tmp / "images" / nome).write_bytes(dados)
            documento = tmp / "livro.html"
            documento.write_text(html_pdf(book, theme, nome_img, fontes, agora), encoding="utf-8")
            pdf = saida / f"{slug}.pdf"
            pdf.unlink(missing_ok=True)
            resultado = chrome(executavel, "--no-pdf-header-footer", "--generate-pdf-document-outline",
                               f"--print-to-pdf={pdf}", documento.resolve().as_uri())
            if not pdf.exists():
                print("ERRO: o Chrome não gerou o PDF.\n" + resultado.stderr[-1500:])
                return 1
            paginas = len(re.findall(rb"/Type\s*/Page[^s]", pdf.read_bytes()))
            print(f"PDF   {pdf.relative_to(root.parent)}  {pdf.stat().st_size / 1e6:.1f} MB | {paginas} páginas "
                  f"{PAGINA_MM[0] // 10}x{PAGINA_MM[1] // 10} cm | fontes {'do tema' if fontes else 'do sistema'}")
    print(f"capa: {origem_capa}")
    return 0


def selftest():
    fx = [f for f, _ in faixas({"bands": [{"max": 1, "label": "a", "tone": "ok"},
                                          {"max": 2, "label": "b", "tone": "ok"},
                                          {"max": None, "label": "c", "tone": "ok"}]})]
    assert fx == ["até 1", "acima de 1 até 2", "acima de 2"], fx
    assert num(0.5) == "0,5" and num(15) == "15"

    imagem = jpeg(Image.new("RGBA", (20, 30), (200, 30, 30, 120)))
    theme = {"id": "teste", "title": "Livro & teste", "subtitle": "Sub", "lang": "pt-BR", "description": "D",
             "tagline": "T", "author": {"name": "Autor", "credentials": "CRM 1"},
             "colors": {"light": {"accent": "#5C1A22", "blocks": {"quiz": "#7B3FA0"}}}}
    faixa = {"id": "x", "label": "AMH", "unit": "ng/mL", "min": 0, "max": 9, "step": 0.1, "initial": 1,
             "bands": [{"max": 1, "label": "baixa", "tone": "alert"}, {"max": None, "label": "ok", "tone": "ok"}]}
    blocos = [
        {"type": "p", "text": "Primeiro <parágrafo>."}, {"type": "h2", "text": "Seção"}, {"type": "h3", "text": "Sub"},
        {"type": "image", "key": "a.png", "caption": "Figura 1"}, {"type": "table", "rows": [["A", "B"], ["1", "2"]]},
        {"type": "pullquote", "text": "Frase", "label": None},
        {"type": "video", "key": "v.mp4", "caption": "Vídeo", "poster": "a.png"},
        {"type": "quiz", "question": "Q?", "options": ["x", "y"], "answer": 1, "explanation": "Porque sim."},
        {"type": "flashcard", "title": None, "cards": [{"front": "F", "back": "V"}]},
        {"type": "calc", "kind": "bands", "title": "C", "note": "N", "fields": [faixa]},
        {"type": "calc", "kind": "poseidon", "title": "P", "note": None, "ageLabel": "Idade", "ageThreshold": 35,
         "ageInitial": 30, "fields": [faixa],
         "groups": [{"label": f"G{i}", "detail": "d", "clbr": "1%", "clbr3": "2%"} for i in range(1, 5)]},
        {"type": "chart", "kind": "decline", "title": "Gráfico", "note": None,
         "points": [{"stage": "a", "value": 1000, "text": "mil"}, {"stage": "b", "value": 10, "text": "dez"}]},
        {"type": "h2", "text": "Referências"}, {"type": "p", "text": "1. Ref."}]
    book = {"chapters": [
        {"id": "apresentacao", "number": None, "title": "Apresentação", "subtitle": None, "part": "Abertura",
         "blocks": [{"type": "p", "text": "Olá."}]},
        {"id": "capitulo-1-x", "number": 1, "title": "Um", "subtitle": "S", "part": "Parte I — Teste", "blocks": blocos}]}

    with tempfile.TemporaryDirectory() as t:
        destino = Path(t) / "t.epub"
        render = montar_epub(book, theme, {"a.jpg": imagem}, {"a.png": "a.jpg"}, imagem, destino)
        erros = conferir_epub(destino)
        assert not erros, erros
        assert len(render.testes) == 1 and render.com_svg == {"cap-02.xhtml"}

        # o conferidor precisa pegar um link quebrado
        quebrado = Path(t) / "q.epub"
        with zipfile.ZipFile(destino) as origem, zipfile.ZipFile(quebrado, "w") as copia:
            for info in origem.infolist():
                dados = origem.read(info.filename)
                if info.filename.endswith("cap-02.xhtml"):
                    dados = dados.replace(b"#resposta-1", b"#resposta-99")
                copia.writestr(info, dados, compress_type=info.compress_type)
        assert any("âncora inexistente" in e for e in conferir_epub(quebrado))

    try:
        Render(theme, "epub", {}).corpo({"id": "c", "blocks": [{"type": "mapa"}]}, "c.xhtml")
    except SystemExit as exc:
        assert "não tem exportação" in str(exc)
    else:
        raise AssertionError("bloco desconhecido deveria interromper a exportação")
    print("selftest OK")
    return 0


def main(argv):
    if argv[1:] == ["--selftest"]:
        return selftest()
    alvos = [a for a in argv[1:] if not a.startswith("--")]
    if len(alvos) != 1:
        print(__doc__)
        return 2
    return exportar(Path(alvos[0]), com_pdf="--sem-pdf" not in argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
