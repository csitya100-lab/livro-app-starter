import { Pause, Play, RotateCcw, RotateCw, Headphones } from "lucide-react";
import { useAudioPlayer } from "@/lib/audio-player";

const rates = [1, 1.25, 1.5] as const;

function formatTime(seconds: number) {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function AudioBar() {
  const { available, mode, playing, position, duration, rate, toggle, skip, seek, setRate } =
    useAudioPlayer();

  if (!available) return null;

  const total = duration > 0 ? duration : Math.max(position, 1);

  return (
    <div className="safe-bottom fixed inset-x-0 bottom-0 z-40 border-t border-border/70 bg-background/95 backdrop-blur-xl">
      <div className="mx-auto max-w-2xl px-4 py-2">
        <div className="flex items-center gap-2">
          <input
            type="range"
            min={0}
            max={total}
            step={1}
            value={Math.min(position, total)}
            onChange={(e) => seek(Number(e.target.value))}
            aria-label="Posição do áudio"
            className="h-1 flex-1 cursor-pointer appearance-none rounded-full bg-secondary accent-accent"
          />
          <span className="w-20 shrink-0 text-right font-sans text-[10px] tabular-nums text-muted-foreground">
            {formatTime(position)} / {formatTime(total)}
          </span>
        </div>

        <div className="mt-1 flex items-center justify-between">
          <span className="inline-flex items-center gap-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            <Headphones className="size-3.5" />
            {mode === "file" ? "Áudio" : "Voz do aparelho"}
          </span>

          <div className="flex items-center gap-1">
            <button
              type="button"
              aria-label="Voltar 15 segundos"
              onClick={() => skip(-15)}
              className="rounded-full p-2 text-foreground"
            >
              <RotateCcw className="size-5" />
            </button>
            <button
              type="button"
              aria-label={playing ? "Pausar leitura" : "Ouvir capítulo"}
              onClick={toggle}
              className="rounded-full bg-accent p-2.5 text-accent-foreground"
            >
              {playing ? <Pause className="size-5" /> : <Play className="size-5" />}
            </button>
            <button
              type="button"
              aria-label="Avançar 15 segundos"
              onClick={() => skip(15)}
              className="rounded-full p-2 text-foreground"
            >
              <RotateCw className="size-5" />
            </button>
          </div>

          <div className="flex items-center gap-1">
            {rates.map((r) => (
              <button
                key={r}
                type="button"
                aria-label={`Velocidade ${String(r).replace(".", ",")}x`}
                aria-pressed={rate === r}
                onClick={() => setRate(r)}
                className={`rounded-md px-1.5 py-1 font-sans text-[11px] font-semibold ${
                  rate === r ? "bg-secondary text-accent" : "text-muted-foreground"
                }`}
              >
                {String(r).replace(".", ",")}x
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
