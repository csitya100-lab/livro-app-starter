import { createFileRoute, Link, notFound, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef } from "react";
import { ChevronLeft, ChevronRight, Heart, ArrowLeft } from "lucide-react";
import { chapters, theme } from "@/content";
import { ChapterBody } from "@/components/ChapterBody";
import { AudioBar } from "@/components/AudioBar";
import { useAudioPlayer } from "@/lib/audio-player";
import { useLibrary } from "@/lib/reader-store";

export const Route = createFileRoute("/capitulo/$chapterId")({
  loader: ({ params }) => {
    const index = chapters.findIndex((c) => c.id === params.chapterId);
    if (index === -1) throw notFound();
    return { index };
  },
  head: ({ params }) => {
    const chapter = chapters.find((c) => c.id === params.chapterId);
    const title = chapter
      ? `${chapter.number ? `Capítulo ${chapter.number} — ` : ""}${chapter.title} · ${theme.title}`
      : `Capítulo · ${theme.title}`;
    const description =
      chapter?.subtitle ??
      chapter?.blocks.find((b) => b.type === "p")?.text.slice(0, 155) ??
      `Capítulo do livro ${theme.title}.`;
    return {
      meta: [
        { title },
        { name: "description", content: description },
        { property: "og:title", content: title },
        { property: "og:description", content: description },
        { property: "og:type", content: "article" },
        { name: "twitter:card", content: "summary_large_image" },
      ],
    };
  },
  component: ChapterPage,
});

function ChapterPage() {
  const { index } = Route.useLoaderData();
  const { chapterId } = Route.useParams();
  const navigate = useNavigate();
  const chapter = chapters[index]!;
  const prev = chapters[index - 1];
  const next = chapters[index + 1];
  const { library, toggleFavorite, setProgress, toggleBookmark } = useLibrary();
  const { loadChapter } = useAudioPlayer();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadChapter(chapter);
  }, [chapter, loadChapter]);

  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [chapterId]);

  useEffect(() => {
    const onScroll = () => {
      const el = containerRef.current;
      if (!el) return;
      const total = el.scrollHeight - window.innerHeight;
      const ratio = total > 0 ? window.scrollY / total : 1;
      setProgress(chapterId, ratio);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [chapterId, setProgress]);

  const favorite = library.favorites.includes(chapterId);
  const progress = Math.min(1, library.progress[chapterId] ?? 0);

  return (
    <div ref={containerRef} className="min-h-screen bg-background">
      <header className="safe-top sticky top-0 z-30 border-b border-border/70 bg-background/85 backdrop-blur-xl">
        <div className="mx-auto flex h-12 max-w-2xl items-center gap-2 px-3">
          <button
            type="button"
            onClick={() => navigate({ to: "/" })}
            className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-sm text-accent"
          >
            <ArrowLeft className="size-4" />
            Sumário
          </button>
          <span className="flex-1 truncate text-center text-xs text-muted-foreground">
            {chapter.number ? `Capítulo ${chapter.number}` : chapter.title}
          </span>
          <button
            type="button"
            aria-label={favorite ? "Remover dos salvos" : "Salvar capítulo"}
            onClick={() => toggleFavorite(chapterId)}
            className="rounded-lg p-2"
          >
            <Heart
              className={`size-5 ${favorite ? "fill-accent text-accent" : "text-muted-foreground"}`}
            />
          </button>
        </div>
        <div className="h-0.5 w-full bg-transparent">
          <div
            className="h-full bg-accent transition-[width]"
            style={{ width: `${Math.round(progress * 100)}%` }}
          />
        </div>
      </header>

      <article className="mx-auto max-w-2xl px-5 pb-[calc(8rem+env(safe-area-inset-bottom))] pt-6">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          {chapter.part}
        </p>
        <h1 className="mt-2 font-serif text-3xl font-bold leading-tight tracking-tight">
          {chapter.title}
        </h1>
        {chapter.subtitle ? (
          <p className="mt-2 font-serif text-base italic text-muted-foreground">
            {chapter.subtitle}
          </p>
        ) : null}

        <div className="mt-7">
          <ChapterBody
            blocks={chapter.blocks}
            bookmarked={(i) =>
              library.bookmarks.some((b) => b.chapterId === chapterId && b.blockIndex === i)
            }
            onToggleBookmark={(i, text) => toggleBookmark(chapterId, i, text)}
          />
        </div>

        <nav className="mt-12 flex gap-3">
          {prev ? (
            <Link
              to="/capitulo/$chapterId"
              params={{ chapterId: prev.id }}
              className="flex flex-1 items-center gap-2 rounded-xl border border-border bg-card px-4 py-3 text-left"
            >
              <ChevronLeft className="size-4 shrink-0 text-accent" />
              <span className="min-w-0">
                <span className="block text-[10px] uppercase tracking-wide text-muted-foreground">
                  Anterior
                </span>
                <span className="block truncate font-serif text-sm">{prev.title}</span>
              </span>
            </Link>
          ) : null}
          {next ? (
            <Link
              to="/capitulo/$chapterId"
              params={{ chapterId: next.id }}
              className="flex flex-1 items-center justify-end gap-2 rounded-xl border border-border bg-card px-4 py-3 text-right"
            >
              <span className="min-w-0">
                <span className="block text-[10px] uppercase tracking-wide text-muted-foreground">
                  Próximo
                </span>
                <span className="block truncate font-serif text-sm">{next.title}</span>
              </span>
              <ChevronRight className="size-4 shrink-0 text-accent" />
            </Link>
          ) : null}
        </nav>
      </article>

      <AudioBar />
    </div>
  );
}
