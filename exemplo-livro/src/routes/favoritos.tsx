import { createFileRoute, Link } from "@tanstack/react-router";
import { Heart, Bookmark } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { chapters, theme } from "@/content";
import { useLibrary } from "@/lib/reader-store";

export const Route = createFileRoute("/favoritos")({
  head: () => ({
    meta: [
      { title: `Salvos · ${theme.title}` },
      {
        name: "description",
        content: `Seus capítulos favoritos e trechos marcados do livro ${theme.title}, guardados no aparelho.`,
      },
      { property: "og:title", content: `Salvos · ${theme.title}` },
      { property: "og:description", content: "Capítulos favoritos e trechos marcados." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: FavoritosPage,
});

function FavoritosPage() {
  const { library, hydrated } = useLibrary();
  const favorites = chapters.filter((c) => library.favorites.includes(c.id));
  const bookmarks = [...library.bookmarks].sort((a, b) => b.at - a.at);

  return (
    <AppShell title="Salvos">
      <div className="mx-auto max-w-2xl space-y-8 px-4 py-4">
        <section>
          <h2 className="flex items-center gap-2 px-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <Heart className="size-3.5" /> Capítulos favoritos
          </h2>
          {hydrated && favorites.length === 0 ? (
            <p className="mt-3 px-1 text-sm text-muted-foreground">
              Toque no coração dentro de um capítulo para salvá-lo aqui.
            </p>
          ) : (
            <ul className="mt-2 overflow-hidden rounded-xl border border-border bg-card">
              {favorites.map((c) => (
                <li key={c.id} className="border-b border-border/60 last:border-0">
                  <Link
                    to="/capitulo/$chapterId"
                    params={{ chapterId: c.id }}
                    className="block px-4 py-3 active:bg-secondary"
                  >
                    <span className="text-[11px] uppercase tracking-wide text-accent">
                      {c.number ? `Capítulo ${c.number}` : c.part}
                    </span>
                    <span className="block font-serif text-[15px]">{c.title}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h2 className="flex items-center gap-2 px-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <Bookmark className="size-3.5" /> Trechos marcados
          </h2>
          {hydrated && bookmarks.length === 0 ? (
            <p className="mt-3 px-1 text-sm text-muted-foreground">
              Toque no marcador ao lado de um parágrafo para guardá-lo.
            </p>
          ) : (
            <ul className="mt-2 space-y-2">
              {bookmarks.map((b) => {
                const chapter = chapters.find((c) => c.id === b.chapterId);
                return (
                  <li key={`${b.chapterId}-${b.blockIndex}`}>
                    <Link
                      to="/capitulo/$chapterId"
                      params={{ chapterId: b.chapterId }}
                      className="block rounded-xl border border-border bg-card px-4 py-3 active:bg-secondary"
                    >
                      <span className="text-[11px] uppercase tracking-wide text-accent">
                        {chapter?.number ? `Capítulo ${chapter.number}` : (chapter?.part ?? "")}
                      </span>
                      <p className="mt-1 font-serif text-sm leading-relaxed text-foreground/85">
                        {b.text}…
                      </p>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </div>
    </AppShell>
  );
}
