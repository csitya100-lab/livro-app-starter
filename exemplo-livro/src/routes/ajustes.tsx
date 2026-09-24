import { createFileRoute } from "@tanstack/react-router";
import { Moon, Sun, SunMoon, Type, RotateCcw } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { useLibrary, useSettings, type ThemeMode } from "@/lib/reader-store";
import { chapters, theme } from "@/content";

const numbered = chapters.filter((c) => c.number !== null).length;
const opening = chapters.length - numbered;
// Trecho de amostra para o leitor calibrar fonte e espaçamento: primeira frase do livro.
const sample =
  chapters[0]?.blocks.find((b) => b.type === "p")?.text.match(/^[^.!?]+[.!?]/)?.[0] ?? "";

export const Route = createFileRoute("/ajustes")({
  head: () => ({
    meta: [
      { title: `Ajustes de leitura · ${theme.title}` },
      {
        name: "description",
        content: `Escolha tema claro ou escuro, tamanho da fonte e espaçamento de linha para ler ${theme.title} com conforto.`,
      },
      { property: "og:title", content: `Ajustes de leitura · ${theme.title}` },
      { property: "og:description", content: "Tema, tamanho da fonte e espaçamento de linha." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: AjustesPage,
});

const themes: { value: ThemeMode; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "Claro", icon: Sun },
  { value: "dark", label: "Escuro", icon: Moon },
  { value: "auto", label: "Automático", icon: SunMoon },
];

function AjustesPage() {
  const { settings, updateSettings } = useSettings();
  const { reset } = useLibrary();

  return (
    <AppShell title="Ajustes">
      <div className="mx-auto max-w-2xl space-y-8 px-4 py-4">
        <section>
          <h2 className="px-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Aparência
          </h2>
          <div className="mt-2 grid grid-cols-3 gap-2">
            {themes.map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                type="button"
                onClick={() => updateSettings({ theme: value })}
                className={`flex flex-col items-center gap-1.5 rounded-xl border px-3 py-4 text-xs font-medium transition-colors ${
                  settings.theme === value
                    ? "border-accent bg-accent/10 text-accent"
                    : "border-border bg-card text-muted-foreground"
                }`}
              >
                <Icon className="size-5" />
                {label}
              </button>
            ))}
          </div>
        </section>

        <section>
          <h2 className="flex items-center gap-2 px-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <Type className="size-3.5" /> Texto
          </h2>
          <div className="mt-2 space-y-5 rounded-xl border border-border bg-card p-4">
            <label className="block">
              <span className="flex justify-between text-sm">
                Tamanho da fonte
                <span className="text-muted-foreground">
                  {Math.round(settings.fontScale * 100)}%
                </span>
              </span>
              <input
                type="range"
                min={0.85}
                max={1.5}
                step={0.05}
                value={settings.fontScale}
                onChange={(e) => updateSettings({ fontScale: Number(e.target.value) })}
                className="mt-3 w-full accent-[var(--accent)]"
              />
            </label>
            <label className="block">
              <span className="flex justify-between text-sm">
                Espaçamento de linha
                <span className="text-muted-foreground">{settings.lineHeight.toFixed(2)}</span>
              </span>
              <input
                type="range"
                min={1.5}
                max={2.1}
                step={0.05}
                value={settings.lineHeight}
                onChange={(e) => updateSettings({ lineHeight: Number(e.target.value) })}
                className="mt-3 w-full accent-[var(--accent)]"
              />
            </label>
            <p className="reading-body rounded-lg bg-surface p-3 text-foreground/85">{sample}</p>
          </div>
        </section>

        <section>
          <h2 className="px-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Sobre
          </h2>
          <div className="mt-2 space-y-2 rounded-xl border border-border bg-card p-4 text-sm text-muted-foreground">
            <p className="font-serif text-base text-foreground">{theme.title}</p>
            <p>
              {theme.author.name}
              {theme.author.credentials ? ` · ${theme.author.credentials}` : ""}
            </p>
            <p>
              {numbered} capítulos{opening > 0 ? ` e ${opening} seção(ões) de abertura` : ""}, com
              figuras e quadros. Todo o conteúdo fica no aparelho e funciona sem internet.
            </p>
          </div>
        </section>

        <button
          type="button"
          onClick={() => {
            if (window.confirm("Apagar progresso, favoritos e marcadores?")) reset();
          }}
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-border px-4 py-3 text-sm font-medium text-destructive"
        >
          <RotateCcw className="size-4" />
          Apagar dados de leitura
        </button>
      </div>
    </AppShell>
  );
}
