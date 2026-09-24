import { createFileRoute, Link } from "@tanstack/react-router";
import { ChevronRight, Play } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { chapters, coverUrl, theme } from "@/content";
import { useLibrary } from "@/lib/reader-store";

const numbered = chapters.filter((c) => c.number !== null).length;

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: `${theme.title} — ${theme.subtitle}` },
      {
        name: "description",
        content: `Leia ${theme.title} no celular: ${theme.description} ${numbered} capítulos com figuras e quadros.`,
      },
      { property: "og:title", content: `${theme.title} — livro digital` },
      { property: "og:description", content: theme.description },
      { property: "og:type", content: "book" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Home,
});

const parts = Array.from(new Set(chapters.map((c) => c.part)));

function Home() {
  const { library, hydrated } = useLibrary();
  const last = (hydrated
    ? chapters.find((c) => c.id === library.lastChapterId) ?? chapters[0]
    : chapters[0])!;


  return (
    <AppShell>
      <div className="safe-top relative overflow-hidden bg-primary text-primary-foreground">
        <img
          src={coverUrl}
          alt=""
          aria-hidden
          className="absolute inset-0 size-full object-cover opacity-40"
        />
        <div className="relative mx-auto max-w-2xl px-5 pb-8 pt-10">
          {/* A faixa do herói é escura em qualquer paleta, então o texto sai do primary-foreground:
              usar text-accent aqui quebra quando o accent do título é escuro. */}
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary-foreground/75">
            {theme.tagline}
          </p>
          <h1 className="mt-3 font-serif text-4xl font-bold leading-[1.05] tracking-tight">
            {theme.title}
          </h1>
          <p className="mt-3 max-w-sm text-sm leading-relaxed text-primary-foreground/80">
            {theme.subtitle}
          </p>
          <p className="mt-2 text-xs text-primary-foreground/70">
            {theme.author.name}
            {theme.author.credentials ? ` · ${theme.author.credentials}` : ""}
          </p>

          <Link
            to="/capitulo/$chapterId"
            params={{ chapterId: last.id }}
            className="mt-6 inline-flex items-center gap-2 rounded-full bg-accent px-5 py-3 text-sm font-semibold text-accent-foreground ring-1 ring-primary-foreground/25"
          >
            <Play className="size-4 fill-current" />
            {library.lastChapterId ? "Continuar lendo" : "Começar a ler"}
          </Link>
        </div>
      </div>

      <div className="mx-auto max-w-2xl px-4 py-6">
        <h2 className="px-1 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Sumário
        </h2>

        {parts.map((part) => {
          // "Parte I — O desenvolvimento ovariano" vira rótulo em caixa alta + título serifado
          const [rotulo, ...resto] = part.split(" — ");
          const titulo = resto.join(" — ");
          return (
          <section key={part} className="mt-7">
            <h3 className="px-1">
              <span className="block font-sans text-[11px] font-bold uppercase tracking-[0.16em] text-accent">
                {rotulo}
              </span>
              {titulo ? (
                <span className="mt-1 block font-serif text-[17px] font-semibold leading-snug">
                  {titulo}
                </span>
              ) : null}
              <span className="mt-2.5 block h-px w-full bg-border" />
            </h3>
            <ul className="mt-2 overflow-hidden rounded-xl border border-border bg-card">
              {chapters
                .filter((c) => c.part === part)
                .map((c) => {
                  const progress = library.progress[c.id] ?? 0;
                  return (
                    <li key={c.id} className="border-b border-border/60 last:border-0">
                      <Link
                        to="/capitulo/$chapterId"
                        params={{ chapterId: c.id }}
                        className="flex items-center gap-3 px-4 py-3.5 active:bg-secondary"
                      >
                        <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-surface font-sans text-[12px] font-bold tabular-nums text-accent">
                          {c.number ?? "—"}
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate font-serif text-[15px] font-medium">
                            {c.title}
                          </span>
                          {progress > 0 ? (
                            <span className="mt-1 block h-1 w-full overflow-hidden rounded-full bg-secondary">
                              <span
                                className="block h-full rounded-full bg-accent"
                                style={{ width: `${Math.round(progress * 100)}%` }}
                              />
                            </span>
                          ) : null}
                        </span>
                        <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
                      </Link>
                    </li>
                  );
                })}
            </ul>
          </section>
          );
        })}
      </div>
    </AppShell>
  );
}
