import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { chapters, isTextBlock, theme } from "@/content";

export const Route = createFileRoute("/busca")({
  head: () => ({
    meta: [
      { title: `Busca no livro · ${theme.title}` },
      {
        name: "description",
        content: `Busque termos em todos os capítulos de ${theme.title} e veja trechos com destaque.`,
      },
      { property: "og:title", content: `Busca no livro · ${theme.title}` },
      {
        property: "og:description",
        content: "Encontre qualquer termo do livro em segundos.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: BuscaPage,
});

type Hit = { chapterId: string; chapterTitle: string; number: number | null; snippet: string };

function normalize(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

const index = chapters.map((c) => ({
  id: c.id,
  title: c.title,
  number: c.number,
  paragraphs: c.blocks
    .filter(isTextBlock)
    .map((b) => ({ text: b.text, norm: normalize(b.text) })),
}));

function BuscaPage() {
  const [query, setQuery] = useState("");

  const hits = useMemo<Hit[]>(() => {
    const q = normalize(query.trim());
    if (q.length < 3) return [];
    const results: Hit[] = [];
    for (const chapter of index) {
      for (const p of chapter.paragraphs) {
        const at = p.norm.indexOf(q);
        if (at === -1) continue;
        const start = Math.max(0, at - 60);
        results.push({
          chapterId: chapter.id,
          chapterTitle: chapter.title,
          number: chapter.number,
          snippet:
            (start > 0 ? "…" : "") + p.text.slice(start, at + q.length + 90).trim() + "…",
        });
        if (results.length > 120) return results;
      }
    }
    return results;
  }, [query]);

  return (
    <AppShell title="Busca">
      <div className="mx-auto max-w-2xl px-4 py-4">
        <div className="flex items-center gap-2 rounded-xl border border-border bg-card px-3">
          <Search className="size-4 text-muted-foreground" />
          <input
            type="search"
            aria-label="Buscar no livro inteiro"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar no livro inteiro…"
            className="w-full bg-transparent py-3 text-[15px] outline-none placeholder:text-muted-foreground"
            autoComplete="off"
            enterKeyHint="search"
          />
        </div>

        {query.trim().length > 0 && query.trim().length < 3 ? (
          <p className="mt-4 text-sm text-muted-foreground">Digite ao menos 3 letras.</p>
        ) : null}

        {hits.length > 0 ? (
          <p className="mt-4 text-xs uppercase tracking-wide text-muted-foreground">
            {hits.length} trecho{hits.length > 1 ? "s" : ""} encontrado
            {hits.length > 1 ? "s" : ""}
          </p>
        ) : null}

        <ul className="mt-2 space-y-2">
          {hits.map((hit, i) => (
            <li key={i}>
              <Link
                to="/capitulo/$chapterId"
                params={{ chapterId: hit.chapterId }}
                className="block rounded-xl border border-border bg-card px-4 py-3 active:bg-secondary"
              >
                <span className="text-[11px] font-semibold uppercase tracking-wide text-accent">
                  {hit.number ? `Capítulo ${hit.number} · ${hit.chapterTitle}` : hit.chapterTitle}
                </span>

                <p className="mt-1 font-serif text-sm leading-relaxed text-foreground/85">
                  <Highlighted text={hit.snippet} query={query.trim()} />
                </p>
              </Link>
            </li>
          ))}
        </ul>

        {query.trim().length >= 3 && hits.length === 0 ? (
          <p className="mt-8 text-center text-sm text-muted-foreground">
            Nenhum resultado para “{query.trim()}”.
          </p>
        ) : null}
      </div>
    </AppShell>
  );
}

function Highlighted({ text, query }: { text: string; query: string }) {
  const normText = normalize(text);
  const normQuery = normalize(query);
  const at = normText.indexOf(normQuery);
  if (at === -1 || !normQuery) return <>{text}</>;
  return (
    <>
      {text.slice(0, at)}
      <mark className="rounded bg-highlight/60 px-0.5 text-foreground">
        {text.slice(at, at + query.length)}
      </mark>
      {text.slice(at + query.length)}
    </>
  );
}
