import { useState } from "react";
import { Bookmark, BookmarkCheck, X } from "lucide-react";
import { images, videos, type Block } from "@/content";
import { BandsCalc, DeclineChart, Flashcards, PoseidonCalc, PullQuote, Quiz } from "./blocks";

export function ChapterBody({
  blocks,
  bookmarked,
  onToggleBookmark,
}: {
  blocks: Block[];
  bookmarked: (index: number) => boolean;
  onToggleBookmark: (index: number, text: string) => void;
}) {
  const [zoom, setZoom] = useState<{ src: string; caption: string | null } | null>(null);

  let inReferences = false;
  // O primeiro parágrafo abre o capítulo: corpo maior e capitular (ver .lead em styles.css).
  const leadIndex = blocks.findIndex((b) => b.type === "p");

  return (
    <div className="reading-body space-y-5">
      {blocks.map((block, i) => {
        if (block.type === "h2") {
          inReferences = block.text.trim().toLowerCase() === "referências";
          return (
            <h2
              key={i}
              className="pt-6 font-sans text-[19px] font-bold leading-tight tracking-tight text-accent before:mb-3 before:block before:h-0.5 before:w-9 before:rounded-full before:bg-accent"
            >
              {block.text}
            </h2>
          );
        }
        if (block.type === "h3") {
          inReferences = false;
          return (
            <h3
              key={i}
              className="pt-3 font-sans text-[12px] font-bold uppercase tracking-[0.14em] text-muted-foreground"
            >
              {block.text}
            </h3>
          );
        }
        if (block.type === "image") {
          const src = images[block.key];
          if (!src) return null;
          return (
            <figure key={i} className="my-6">
              <button
                type="button"
                onClick={() => setZoom({ src, caption: block.caption })}
                className="block w-full overflow-hidden rounded-xl border border-border bg-card"
              >
                <img
                  src={src}
                  alt={block.caption ?? "Figura do capítulo"}
                  loading="lazy"
                  className="w-full"
                />
              </button>
              {block.caption ? (
                <figcaption className="mt-2 font-sans text-xs leading-relaxed text-muted-foreground">
                  {block.caption}
                </figcaption>
              ) : null}
            </figure>
          );
        }
        if (block.type === "table") {
          const [head, ...rows] = block.rows;
          return (
            <div
              key={i}
              className="-mx-4 my-6 overflow-x-auto px-4"
            >
              <table className="w-full min-w-[520px] border-collapse font-sans text-[13px]">
                <thead>
                  <tr>
                    {head?.map((cell, j) => (
                      <th
                        key={j}
                        className="border-b border-border bg-surface px-3 py-2 text-left font-semibold"
                      >
                        {cell}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, r) => (
                    <tr key={r} className="align-top">
                      {row.map((cell, c) => (
                        <td key={c} className="border-b border-border/60 px-3 py-2 leading-relaxed">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
        if (block.type === "video") {
          const src = videos[block.key];
          if (!src) return null;
          const poster = block.poster ? images[block.poster] : undefined;
          return (
            <figure key={i} className="my-6">
              <video
                src={src}
                poster={poster}
                controls
                playsInline
                preload="none"
                className="mx-auto max-h-[70vh] w-full rounded-xl border border-border bg-black"
              />
              {block.caption ? (
                <figcaption className="mt-2 font-sans text-xs leading-relaxed text-muted-foreground">
                  {block.caption}
                </figcaption>
              ) : null}
            </figure>
          );
        }
        if (block.type === "pullquote") return <PullQuote key={i} block={block} />;
        if (block.type === "quiz") return <Quiz key={i} block={block} />;
        if (block.type === "flashcard") return <Flashcards key={i} block={block} />;
        if (block.type === "calc") {
          return block.kind === "poseidon" ? (
            <PoseidonCalc key={i} block={block} />
          ) : (
            <BandsCalc key={i} block={block} />
          );
        }
        if (block.type === "chart") return <DeclineChart key={i} block={block} />;

        const saved = bookmarked(i);
        return (
          <p
            key={i}
            className={`group relative text-foreground/90 ${
              inReferences
                ? "pl-6 -indent-6 text-left text-[0.85em] leading-relaxed"
                : i === leadIndex
                  ? "lead"
                  : ""
            }`}
          >
            {block.text}
            <button
              type="button"
              aria-label={saved ? "Remover marcador" : "Salvar trecho"}
              onClick={() => onToggleBookmark(i, block.text)}
              className={`ml-1 inline-flex translate-y-[3px] rounded-md p-0.5 transition-opacity ${
                saved ? "text-accent" : "text-muted-foreground/40"
              }`}
            >
              {saved ? (
                <BookmarkCheck className="size-4" />
              ) : (
                <Bookmark className="size-4" />
              )}
            </button>
          </p>
        );
      })}

      {zoom ? (
        <div
          className="fixed inset-0 z-50 flex flex-col bg-background/97 backdrop-blur-sm"
          onClick={() => setZoom(null)}
        >
          <div className="safe-top flex justify-end p-3">
            <button
              type="button"
              className="rounded-full bg-secondary p-2 text-secondary-foreground"
              aria-label="Fechar"
            >
              <X className="size-5" />
            </button>
          </div>
          <div className="flex-1 overflow-auto px-3 pb-8">
            <img src={zoom.src} alt={zoom.caption ?? "Figura ampliada"} className="w-full" />
            {zoom.caption ? (
              <p className="mt-3 font-sans text-xs text-muted-foreground">{zoom.caption}</p>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
