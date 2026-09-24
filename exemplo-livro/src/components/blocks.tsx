import { useState, type ReactNode } from "react";
import {
  Calculator,
  Check,
  ChevronLeft,
  ChevronRight,
  HelpCircle,
  Layers,
  RotateCcw,
  TrendingDown,
  X,
  type LucideIcon,
} from "lucide-react";
import type { Band, Block, Field, PoseidonGroup } from "@/content";

/** Cada tipo de bloco tem sua cor, vinda de theme.json (colors.<modo>.blocks). */
type Tone = "quiz" | "flashcard" | "calc" | "chart";
const toneVar = (tone: Tone) => `var(--block-${tone})`;

function BlockCard({
  tone,
  icon: Icon,
  label,
  right,
  children,
}: {
  tone: Tone;
  icon: LucideIcon;
  label: string;
  right?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section
      className="my-7 rounded-xl border border-t-[3px] border-border bg-card p-4"
      style={{ borderTopColor: toneVar(tone) }}
    >
      <div className="flex items-baseline justify-between gap-3">
        <p
          className="flex items-center gap-1.5 font-sans text-[12px] font-bold uppercase tracking-[0.1em]"
          style={{ color: toneVar(tone) }}
        >
          <Icon className="size-3.5 shrink-0" strokeWidth={2.4} />
          {label}
        </p>
        {right}
      </div>
      <div className="mt-3">{children}</div>
    </section>
  );
}

export function PullQuote({ block }: { block: Extract<Block, { type: "pullquote" }> }) {
  return (
    <figure className="my-8 border-l-[3px] border-accent pl-4">
      {block.label ? (
        <figcaption className="font-sans text-[11px] font-bold uppercase tracking-[0.14em] text-accent">
          {block.label}
        </figcaption>
      ) : null}
      <p className="mt-1.5 font-serif text-[1.22em] font-medium leading-[1.45] text-foreground">
        {block.text}
      </p>
    </figure>
  );
}

const TONE: Record<Band["tone"], string> = {
  alert: "border-destructive/40 bg-destructive/10 text-destructive",
  warn: "border-highlight bg-highlight/25 text-foreground",
  ok: "border-accent/40 bg-accent/10 text-accent",
  info: "border-border bg-surface text-muted-foreground",
};

/** Primeira faixa cujo teto ainda não foi ultrapassado; a última (max null) é o "acima de tudo". */
function bandFor(bands: Band[], value: number): Band | undefined {
  return bands.find((b) => b.max === null || value <= b.max) ?? bands[bands.length - 1];
}

function NumberField({
  field,
  value,
  onChange,
  showBand = true,
}: {
  field: Field;
  value: number;
  onChange: (v: number) => void;
  showBand?: boolean;
}) {
  const band = showBand ? bandFor(field.bands, value) : undefined;
  return (
    <div>
      <label className="flex items-baseline justify-between gap-3 font-sans text-[13px] font-medium">
        <span>{field.label}</span>
        <span className="flex items-center gap-1">
          <input
            type="number"
            inputMode="decimal"
            min={field.min}
            max={field.max}
            step={field.step}
            value={Number.isFinite(value) ? value : ""}
            onChange={(e) => onChange(Number(e.target.value))}
            className="w-20 rounded-lg border border-input bg-background px-2 py-1.5 text-right tabular-nums outline-none focus:border-accent"
          />
          {field.unit ? (
            <span className="w-14 text-[11px] text-muted-foreground">{field.unit}</span>
          ) : null}
        </span>
      </label>
      {band ? (
        <p className={`mt-1.5 rounded-lg border px-2.5 py-1.5 font-sans text-[12px] ${TONE[band.tone]}`}>
          {band.label}
        </p>
      ) : null}
    </div>
  );
}

function CalcShell({
  title,
  note,
  children,
}: {
  title: string;
  note: string | null;
  children: ReactNode;
}) {
  return (
    <BlockCard tone="calc" icon={Calculator} label={title}>
      <div className="space-y-4">{children}</div>
      {note ? (
        <p className="mt-4 border-t border-border/60 pt-3 font-sans text-[11px] leading-relaxed text-muted-foreground">
          {note}
        </p>
      ) : null}
    </BlockCard>
  );
}

export function BandsCalc({ block }: { block: Extract<Block, { type: "calc"; kind: "bands" }> }) {
  const [values, setValues] = useState<Record<string, number>>(() =>
    Object.fromEntries(block.fields.map((f) => [f.id, f.initial])),
  );
  return (
    <CalcShell title={block.title} note={block.note}>
      {block.fields.map((f) => (
        <NumberField
          key={f.id}
          field={f}
          value={values[f.id] ?? f.initial}
          onChange={(v) => setValues((p) => ({ ...p, [f.id]: v }))}
        />
      ))}
    </CalcShell>
  );
}

export function PoseidonCalc({
  block,
}: {
  block: Extract<Block, { type: "calc"; kind: "poseidon" }>;
}) {
  const [age, setAge] = useState(block.ageInitial);
  const [values, setValues] = useState<Record<string, number>>(() =>
    Object.fromEntries(block.fields.map((f) => [f.id, f.initial])),
  );

  // Reserva baixa se QUALQUER marcador ficar dentro da primeira faixa, cujo `max` é o teto
  // inclusivo do "abaixo do limiar" — a mesma semântica de bandFor.
  const low = block.fields.some((f) => {
    const top = f.bands[0]?.max;
    return top !== null && top !== undefined && (values[f.id] ?? f.initial) <= top;
  });
  const young = age < block.ageThreshold;
  const group: PoseidonGroup | undefined = block.groups[(low ? 2 : 0) + (young ? 0 : 1)];

  return (
    <CalcShell title={block.title} note={block.note}>
      <NumberField
        field={{
          id: "idade",
          label: block.ageLabel,
          unit: null,
          min: 18,
          max: 55,
          step: 1,
          initial: block.ageInitial,
          bands: [],
        }}
        value={age}
        onChange={setAge}
        showBand={false}
      />
      {block.fields.map((f) => (
        <NumberField
          key={f.id}
          field={f}
          value={values[f.id] ?? f.initial}
          onChange={(v) => setValues((p) => ({ ...p, [f.id]: v }))}
          showBand={false}
        />
      ))}
      {group ? (
        <div className="rounded-lg border border-accent/40 bg-accent/10 p-3">
          <p className="font-sans text-sm font-bold text-accent">{group.label}</p>
          <p className="mt-1 font-sans text-[12px] leading-relaxed text-foreground/80">
            {group.detail}
          </p>
          <dl className="mt-3 grid grid-cols-2 gap-2 font-sans text-[12px]">
            <div className="rounded-md bg-card px-2.5 py-2">
              <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">
                Por ciclo iniciado
              </dt>
              <dd className="text-base font-bold tabular-nums">{group.clbr}</dd>
            </div>
            <div className="rounded-md bg-card px-2.5 py-2">
              <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">
                Após 3 ciclos
              </dt>
              <dd className="text-base font-bold tabular-nums">{group.clbr3}</dd>
            </div>
          </dl>
        </div>
      ) : null}
    </CalcShell>
  );
}

export function Quiz({ block }: { block: Extract<Block, { type: "quiz" }> }) {
  const [chosen, setChosen] = useState<number | null>(null);
  const done = chosen !== null;

  return (
    <BlockCard tone="quiz" icon={HelpCircle} label="Teste rápido">
      <p className="font-sans text-[15px] font-medium leading-snug">{block.question}</p>
      <ul className="mt-3 space-y-2">
        {block.options.map((option, i) => {
          const right = i === block.answer;
          const state = !done
            ? "border-border bg-background"
            : right
              ? "border-accent bg-accent/10 text-accent"
              : i === chosen
                ? "border-destructive bg-destructive/10 text-destructive"
                : "border-border bg-background text-muted-foreground";
          return (
            <li key={i}>
              <button
                type="button"
                disabled={done}
                onClick={() => setChosen(i)}
                aria-label={option}
                className={`flex w-full items-start gap-2 rounded-lg border px-3 py-2.5 text-left font-sans text-[13px] leading-snug transition-colors ${state}`}
              >
                <span className="mt-0.5 shrink-0">
                  {done && right ? (
                    <Check className="size-4" />
                  ) : done && i === chosen ? (
                    <X className="size-4" />
                  ) : (
                    <span className="inline-block size-4 rounded-full border border-current opacity-40" />
                  )}
                </span>
                {option}
              </button>
            </li>
          );
        })}
      </ul>
      {done ? (
        <div className="mt-3 flex items-start justify-between gap-3">
          {block.explanation ? (
            <p className="font-sans text-[12px] leading-relaxed text-muted-foreground">
              {block.explanation}
            </p>
          ) : (
            <span />
          )}
          <button
            type="button"
            onClick={() => setChosen(null)}
            className="inline-flex shrink-0 items-center gap-1 rounded-md px-2 py-1 font-sans text-[11px] font-semibold text-accent"
          >
            <RotateCcw className="size-3.5" />
            Refazer
          </button>
        </div>
      ) : null}
    </BlockCard>
  );
}

export function Flashcards({ block }: { block: Extract<Block, { type: "flashcard" }> }) {
  const [index, setIndex] = useState(0);
  const [open, setOpen] = useState(false);
  const card = block.cards[index];
  if (!card) return null;

  const go = (delta: number) => {
    setIndex((i) => (i + delta + block.cards.length) % block.cards.length);
    setOpen(false);
  };

  return (
    <BlockCard
      tone="flashcard"
      icon={Layers}
      label={block.title ?? "Flashcards"}
      right={
        <p className="font-sans text-[11px] tabular-nums text-muted-foreground">
          {index + 1} / {block.cards.length}
        </p>
      }
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex min-h-32 w-full flex-col justify-center rounded-lg border border-border bg-surface px-4 py-5 text-left"
      >
        <span className="font-serif text-[15px] leading-snug">{card.front}</span>
        {open ? (
          <span className="mt-3 border-t border-border pt-3 font-sans text-[13px] leading-relaxed text-foreground/85">
            {card.back}
          </span>
        ) : (
          <span className="mt-3 font-sans text-[11px] uppercase tracking-wide text-muted-foreground">
            Tocar para ver a resposta
          </span>
        )}
      </button>

      <div className="mt-3 flex items-center justify-between">
        <button
          type="button"
          onClick={() => go(-1)}
          aria-label="Cartão anterior"
          className="inline-flex items-center gap-1 rounded-md px-2 py-1.5 font-sans text-[12px] font-semibold text-accent"
        >
          <ChevronLeft className="size-4" />
          Anterior
        </button>
        <button
          type="button"
          onClick={() => go(1)}
          aria-label="Próximo cartão"
          className="inline-flex items-center gap-1 rounded-md px-2 py-1.5 font-sans text-[12px] font-semibold text-accent"
        >
          Próximo
          <ChevronRight className="size-4" />
        </button>
      </div>
    </BlockCard>
  );
}

export function DeclineChart({ block }: { block: Extract<Block, { type: "chart" }> }) {
  const [index, setIndex] = useState(0);
  const points = block.points;
  const current = points[index];
  if (!current) return null;

  // Escala logarítmica: o estoque cai várias ordens de grandeza, então o log é o que deixa a curva legível.
  const logs = points.map((p) => Math.log10(Math.max(1, p.value)));
  const top = Math.max(...logs) + 0.2;
  const bottom = Math.min(...logs) - 0.2;
  const x = (i: number) => 16 + (i * 288) / Math.max(1, points.length - 1);
  const y = (v: number) => 116 - ((Math.log10(Math.max(1, v)) - bottom) / (top - bottom)) * 100;
  const path = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(" ");

  const cor = toneVar("chart");
  return (
    <BlockCard tone="chart" icon={TrendingDown} label={block.title}>
      <svg viewBox="0 0 320 132" role="img" aria-label={block.title} className="w-full">
        <path
          d={`${path} L${x(points.length - 1)},128 L${x(0)},128 Z`}
          fill={cor}
          fillOpacity="0.12"
        />
        <path d={path} fill="none" strokeWidth="2.5" strokeLinecap="round" stroke={cor} />
        {points.map((p, i) => (
          <circle
            key={p.stage}
            cx={x(i)}
            cy={y(p.value)}
            r={i === index ? 6 : 3.5}
            fill={cor}
            fillOpacity={i === index ? 1 : 0.45}
          />
        ))}
      </svg>

      <input
        type="range"
        min={0}
        max={points.length - 1}
        step={1}
        value={index}
        onChange={(e) => setIndex(Number(e.target.value))}
        aria-label="Etapa da vida"
        aria-valuetext={`${current.stage}: ${current.text}`}
        style={{ accentColor: cor }}
        className="mt-1 h-1 w-full cursor-pointer appearance-none rounded-full bg-secondary"
      />

      <div className="mt-3 rounded-lg border border-border bg-surface px-3 py-2.5">
        <p className="font-sans text-[11px] uppercase tracking-wide text-muted-foreground">
          {current.stage}
        </p>
        <p className="font-sans text-lg font-bold tabular-nums text-foreground">{current.text}</p>
      </div>

      {block.note ? (
        <p className="mt-3 font-sans text-[11px] leading-relaxed text-muted-foreground">
          {block.note}
        </p>
      ) : null}
    </BlockCard>
  );
}
