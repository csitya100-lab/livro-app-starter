import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { X } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { chapters, images, theme } from "@/content";

export const Route = createFileRoute("/figuras")({
  head: () => ({
    meta: [
      { title: `Figuras e quadros · ${theme.title}` },
      {
        name: "description",
        content: `Galeria com todas as figuras e quadros do livro ${theme.title}, com link para o capítulo de origem.`,
      },
      { property: "og:title", content: `Figuras e quadros · ${theme.title}` },
      {
        property: "og:description",
        content: "Índice visual das ilustrações e quadros clínicos do livro.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: FigurasPage,
});

type Item = {
  key: string;
  src: string;
  caption: string;
  chapterId: string;
  chapterTitle: string;
  number: number | null;
};

const items: Item[] = chapters.flatMap((chapter) =>
  chapter.blocks
    .filter((b) => b.type === "image")
    .map((b) => {
      const block = b as Extract<typeof b, { type: "image" }>;
      return {
        key: `${chapter.id}-${block.key}`,
        src: images[block.key] ?? "",
        caption:
          block.caption ??
          (chapter.number ? `Ilustração do capítulo ${chapter.number}` : "Ilustração de abertura"),
        chapterId: chapter.id,
        chapterTitle: chapter.title,
        number: chapter.number,
      };
    })
    .filter((item) => item.src && !item.src.includes("capa")),
);

function FigurasPage() {
  const [zoom, setZoom] = useState<Item | null>(null);

  return (
    <AppShell title="Figuras e quadros">
      <div className="mx-auto max-w-2xl px-4 py-4">
        <ul className="grid grid-cols-2 gap-3">
          {items.map((item) => (
            <li key={item.key} className="overflow-hidden rounded-xl border border-border bg-card">
              <button type="button" onClick={() => setZoom(item)} className="block w-full">
                <img
                  src={item.src}
                  alt={item.caption}
                  loading="lazy"
                  className="aspect-4/3 w-full bg-surface object-contain"
                />
              </button>
              <div className="px-3 py-2">
                <p className="line-clamp-2 font-serif text-xs leading-snug">{item.caption}</p>
                <Link
                  to="/capitulo/$chapterId"
                  params={{ chapterId: item.chapterId }}
                  className="mt-1 block text-[10px] font-semibold uppercase tracking-wide text-accent"
                >
                  {item.number ? `Cap. ${item.number}` : "Abertura"}
                </Link>
              </div>
            </li>
          ))}
        </ul>
      </div>

      {zoom ? (
        <div
          className="fixed inset-0 z-50 flex flex-col bg-background/97 backdrop-blur-sm"
          onClick={() => setZoom(null)}
        >
          <div className="safe-top flex justify-end p-3">
            <button
              type="button"
              aria-label="Fechar figura"
              onClick={() => setZoom(null)}
              className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-full bg-secondary p-2 text-secondary-foreground"
            >
              <X className="size-5" />
            </button>
          </div>
          <div className="flex-1 overflow-auto px-3 pb-10">
            <img src={zoom.src} alt={zoom.caption} className="w-full" />
            <p className="mt-3 text-xs text-muted-foreground">{zoom.caption}</p>
          </div>
        </div>
      ) : null}
    </AppShell>
  );
}
