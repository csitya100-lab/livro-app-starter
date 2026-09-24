import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { isTextBlock, theme, type Block, type Chapter } from "@/content";

const STORE_KEY = `${theme.storagePrefix}.audio.v1`;
const LANG = theme.lang.toLowerCase();
const CHARS_PER_SECOND = 15; // estimativa de fala em 1x
const DEFAULT_RATE = 1.5;

type Persisted = { rate: number; positions: Record<string, number> };

const defaultPersisted: Persisted = { rate: DEFAULT_RATE, positions: {} };

function readStore(): Persisted {
  if (typeof window === "undefined") return defaultPersisted;
  try {
    const raw = window.localStorage.getItem(STORE_KEY);
    if (!raw) return defaultPersisted;
    return { ...defaultPersisted, ...(JSON.parse(raw) as Persisted) };
  } catch {
    return defaultPersisted;
  }
}

function writeStore(value: Persisted) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORE_KEY, JSON.stringify(value));
  } catch {
    /* armazenamento indisponível */
  }
}

/** Texto legível do capítulo: ignora imagens, quadros e a seção "Referências". */
export function speakableSegments(blocks: Block[]): string[] {
  const out: string[] = [];
  let stop = false;
  for (const block of blocks) {
    if (stop) break;
    if (!isTextBlock(block)) continue; // imagens, vídeos, quadros e blocos interativos não são falados
    if (block.type === "h2" && block.text.trim().toLowerCase() === "referências") {
      stop = true;
      break;
    }
    const text = block.text.trim();
    if (!text) continue;
    // quebra em frases para permitir busca e retomada mais finas
    const parts = text.match(/[^.!?]+[.!?]*\s*/g) ?? [text];
    for (const part of parts) {
      const t = part.trim();
      if (t) out.push(t);
    }
  }
  return out;
}

type AudioState = {
  available: boolean;
  chapterId: string | null;
  chapterTitle: string | null;
  mode: "file" | "speech" | null;
  playing: boolean;
  position: number;
  duration: number;
  rate: number;
};

type AudioApi = AudioState & {
  toggle: () => void;
  seek: (seconds: number) => void;
  skip: (delta: number) => void;
  setRate: (rate: number) => void;
  loadChapter: (chapter: Chapter) => void;
};

const AudioCtx = createContext<AudioApi | null>(null);

export function useAudioPlayer() {
  const ctx = useContext(AudioCtx);
  if (!ctx) throw new Error("useAudioPlayer precisa do AudioPlayerProvider");
  return ctx;
}

export function AudioPlayerProvider({ children }: { children: ReactNode }) {
  const [speechSupported, setSpeechSupported] = useState(false);
  const [chapter, setChapter] = useState<Chapter | null>(null);
  const [playing, setPlaying] = useState(false);
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(0);
  const [rate, setRateState] = useState(DEFAULT_RATE);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const segmentsRef = useRef<string[]>([]);
  const offsetsRef = useRef<number[]>([]); // chars acumulados por segmento
  const totalCharsRef = useRef(0);
  const segIndexRef = useRef(0);
  const segStartedAtRef = useRef(0);
  const rateRef = useRef(DEFAULT_RATE);
  const playingRef = useRef(false);
  const chapterIdRef = useRef<string | null>(null);
  const manualStopRef = useRef(false);

  const mode: "file" | "speech" | null = chapter
    ? chapter.audioUrl
      ? "file"
      : speechSupported
        ? "speech"
        : null
    : null;

  /* ---------- persistência ---------- */
  useEffect(() => {
    setSpeechSupported(typeof window !== "undefined" && "speechSynthesis" in window);
    const stored = readStore();
    setRateState(stored.rate);
    rateRef.current = stored.rate;
  }, []);

  const persistPosition = useCallback((id: string, seconds: number) => {
    const store = readStore();
    writeStore({ ...store, positions: { ...store.positions, [id]: seconds } });
  }, []);

  /* ---------- fala ---------- */
  const cancelSpeech = useCallback(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    manualStopRef.current = true;
    window.speechSynthesis.cancel();
  }, []);

  const pickVoice = useCallback(() => {
    const voices = window.speechSynthesis.getVoices();
    return (
      voices.find((v) => v.lang?.toLowerCase() === LANG) ??
      voices.find((v) => v.lang?.toLowerCase().startsWith(LANG.slice(0, 2))) ??
      null
    );
  }, []);

  const speakFrom = useCallback(
    (index: number) => {
      if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
      const segments = segmentsRef.current;
      if (index >= segments.length) {
        playingRef.current = false;
        setPlaying(false);
        setPosition(0);
        segIndexRef.current = 0;
        return;
      }
      manualStopRef.current = true;
      window.speechSynthesis.cancel();
      manualStopRef.current = false;

      segIndexRef.current = index;
      segStartedAtRef.current = Date.now();

      const utter = new SpeechSynthesisUtterance(segments[index]);
      utter.lang = theme.lang;
      const voice = pickVoice();
      if (voice) utter.voice = voice;
      utter.rate = rateRef.current;
      utter.onend = () => {
        if (manualStopRef.current || !playingRef.current) return;
        speakFrom(index + 1);
      };
      utter.onerror = () => {
        if (manualStopRef.current || !playingRef.current) return;
        speakFrom(index + 1);
      };
      window.speechSynthesis.speak(utter);
    },
    [pickVoice],
  );

  // relógio virtual da fala
  useEffect(() => {
    if (mode !== "speech" || !playing) return;
    const tick = () => {
      const idx = segIndexRef.current;
      const base = offsetsRef.current[idx] ?? 0;
      const elapsed = (Date.now() - segStartedAtRef.current) / 1000;
      const segChars = (segmentsRef.current[idx] ?? "").length;
      const spoken = Math.min(segChars, elapsed * CHARS_PER_SECOND * rateRef.current);
      const chars = base + spoken;
      const seconds = chars / CHARS_PER_SECOND;
      setPosition(seconds);
      if (chapterIdRef.current) persistPosition(chapterIdRef.current, seconds);
    };
    const id = window.setInterval(tick, 500);
    return () => window.clearInterval(id);
  }, [mode, playing, persistPosition]);

  const seekSpeech = useCallback(
    (seconds: number) => {
      const total = totalCharsRef.current / CHARS_PER_SECOND;
      const target = Math.min(Math.max(0, seconds), Math.max(0, total - 0.5));
      const targetChars = target * CHARS_PER_SECOND;
      const offsets = offsetsRef.current;
      let index = 0;
      for (let i = 0; i < offsets.length; i++) {
        if ((offsets[i] ?? 0) <= targetChars) index = i;
        else break;
      }
      setPosition((offsets[index] ?? 0) / CHARS_PER_SECOND);
      if (playingRef.current) speakFrom(index);
      else segIndexRef.current = index;
    },
    [speakFrom],
  );

  /* ---------- carregar capítulo ---------- */
  const loadChapter = useCallback(
    (next: Chapter) => {
      if (chapterIdRef.current === next.id) return;
      const wasPlaying = playingRef.current;

      // encerra o que estava tocando
      cancelSpeech();
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.removeAttribute("src");
        audioRef.current.load();
      }

      chapterIdRef.current = next.id;
      setChapter(next);

      const segments = speakableSegments(next.blocks);
      segmentsRef.current = segments;
      const offsets: number[] = [];
      let acc = 0;
      for (const s of segments) {
        offsets.push(acc);
        acc += s.length + 1;
      }
      offsetsRef.current = offsets;
      totalCharsRef.current = acc;
      segIndexRef.current = 0;

      const saved = readStore().positions[next.id] ?? 0;

      if (next.audioUrl) {
        setDuration(0);
        setPosition(saved);
        const el = audioRef.current;
        if (el) {
          el.src = next.audioUrl;
          el.playbackRate = rateRef.current;
          el.currentTime = saved;
          if (wasPlaying) void el.play().catch(() => undefined);
        }
        playingRef.current = wasPlaying;
        setPlaying(wasPlaying);
      } else {
        setDuration(acc / CHARS_PER_SECOND);
        setPosition(saved);
        const targetChars = saved * CHARS_PER_SECOND;
        let index = 0;
        for (let i = 0; i < offsets.length; i++) {
          if ((offsets[i] ?? 0) <= targetChars) index = i;
          else break;
        }
        segIndexRef.current = index;
        playingRef.current = wasPlaying;
        setPlaying(wasPlaying);
        if (wasPlaying) speakFrom(index);
      }
    },
    [cancelSpeech, speakFrom],
  );

  /* ---------- controles ---------- */
  const toggle = useCallback(() => {
    if (!chapter) return;
    if (playingRef.current) {
      playingRef.current = false;
      setPlaying(false);
      if (mode === "file") audioRef.current?.pause();
      else cancelSpeech();
      if (chapterIdRef.current) persistPosition(chapterIdRef.current, position);
      return;
    }
    playingRef.current = true;
    setPlaying(true);
    if (mode === "file") {
      const el = audioRef.current;
      if (el) void el.play().catch(() => undefined);
    } else {
      speakFrom(segIndexRef.current);
    }
  }, [chapter, mode, cancelSpeech, persistPosition, position, speakFrom]);

  const seek = useCallback(
    (seconds: number) => {
      if (!chapter) return;
      if (mode === "file") {
        const el = audioRef.current;
        if (el) el.currentTime = Math.max(0, Math.min(seconds, el.duration || seconds));
        setPosition(seconds);
      } else {
        seekSpeech(seconds);
      }
      if (chapterIdRef.current) persistPosition(chapterIdRef.current, Math.max(0, seconds));
    },
    [chapter, mode, seekSpeech, persistPosition],
  );

  const skip = useCallback((delta: number) => seek(position + delta), [seek, position]);

  const setRate = useCallback(
    (value: number) => {
      rateRef.current = value;
      setRateState(value);
      const store = readStore();
      writeStore({ ...store, rate: value });
      if (mode === "file") {
        if (audioRef.current) audioRef.current.playbackRate = value;
      } else if (playingRef.current) {
        speakFrom(segIndexRef.current);
      }
    },
    [mode, speakFrom],
  );

  /* ---------- elemento <audio> ---------- */
  useEffect(() => {
    if (typeof window === "undefined") return;
    const el = new Audio();
    el.preload = "metadata";
    audioRef.current = el;
    const onTime = () => {
      setPosition(el.currentTime);
      if (chapterIdRef.current) persistPosition(chapterIdRef.current, el.currentTime);
    };
    const onMeta = () => setDuration(el.duration || 0);
    const onEnd = () => {
      playingRef.current = false;
      setPlaying(false);
    };
    el.addEventListener("timeupdate", onTime);
    el.addEventListener("loadedmetadata", onMeta);
    el.addEventListener("ended", onEnd);
    return () => {
      el.removeEventListener("timeupdate", onTime);
      el.removeEventListener("loadedmetadata", onMeta);
      el.removeEventListener("ended", onEnd);
      el.pause();
      audioRef.current = null;
    };
  }, [persistPosition]);

  // encerra a fala ao sair da página
  useEffect(() => () => cancelSpeech(), [cancelSpeech]);

  const value = useMemo<AudioApi>(
    () => ({
      available: mode !== null,
      chapterId: chapter?.id ?? null,
      chapterTitle: chapter?.title ?? null,
      mode,
      playing,
      position,
      duration,
      rate,
      toggle,
      seek,
      skip,
      setRate,
      loadChapter,
    }),
    [mode, chapter, playing, position, duration, rate, toggle, seek, skip, setRate, loadChapter],
  );

  return <AudioCtx.Provider value={value}>{children}</AudioCtx.Provider>;
}
