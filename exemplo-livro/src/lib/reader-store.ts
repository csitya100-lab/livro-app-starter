import { useCallback, useEffect, useState } from "react";
import { theme } from "@/content";

export type ThemeMode = "light" | "dark" | "auto";

export type ReaderSettings = {
  theme: ThemeMode;
  fontScale: number; // 0.85 - 1.4
  lineHeight: number; // 1.5 - 2.0
};

export const defaultSettings: ReaderSettings = {
  theme: "auto",
  fontScale: 1,
  lineHeight: 1.75,
};

type Library = {
  favorites: string[];
  progress: Record<string, number>; // chapterId -> 0..1
  lastChapterId: string | null;
  bookmarks: { chapterId: string; blockIndex: number; text: string; at: number }[];
};

const defaultLibrary: Library = {
  favorites: [],
  progress: {},
  lastChapterId: null,
  bookmarks: [],
};

const SETTINGS_KEY = `${theme.storagePrefix}.settings.v1`;
const LIBRARY_KEY = `${theme.storagePrefix}.library.v1`;

function read<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return fallback;
    return { ...fallback, ...(JSON.parse(raw) as T) };
  } catch {
    return fallback;
  }
}

function write(key: string, value: unknown) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* armazenamento indisponível */
  }
}

const listeners = new Set<() => void>();
function broadcast() {
  listeners.forEach((l) => l());
}

function useStored<T>(key: string, fallback: T) {
  const [value, setValue] = useState<T>(fallback);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setValue(read(key, fallback));
    setHydrated(true);
    const listener = () => setValue(read(key, fallback));
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const update = useCallback(
    (patch: Partial<T> | ((prev: T) => T)) => {
      const current = read(key, fallback);
      const next =
        typeof patch === "function"
          ? (patch as (prev: T) => T)(current)
          : { ...current, ...patch };
      write(key, next);
      setValue(next);
      broadcast();
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [key],
  );

  return { value, update, hydrated };
}

export function useSettings() {
  const { value, update, hydrated } = useStored<ReaderSettings>(SETTINGS_KEY, defaultSettings);

  useEffect(() => {
    if (!hydrated) return;
    const root = document.documentElement;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const dark = value.theme === "dark" || (value.theme === "auto" && media.matches);
      root.classList.toggle("dark", dark);
    };
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [value.theme, hydrated]);

  useEffect(() => {
    if (!hydrated) return;
    const root = document.documentElement;
    root.style.setProperty("--reader-font-size", `${1.0625 * value.fontScale}rem`);
    root.style.setProperty("--reader-line-height", String(value.lineHeight));
  }, [value.fontScale, value.lineHeight, hydrated]);

  return { settings: value, updateSettings: update, hydrated };
}

export function useLibrary() {
  const { value, update, hydrated } = useStored<Library>(LIBRARY_KEY, defaultLibrary);

  const toggleFavorite = useCallback(
    (chapterId: string) =>
      update((prev) => ({
        ...prev,
        favorites: prev.favorites.includes(chapterId)
          ? prev.favorites.filter((id) => id !== chapterId)
          : [...prev.favorites, chapterId],
      })),
    [update],
  );

  const setProgress = useCallback(
    (chapterId: string, ratio: number) =>
      update((prev) => {
        const rounded = Math.min(1, Math.max(0, Math.round(ratio * 20) / 20));
        if (prev.progress[chapterId] === rounded && prev.lastChapterId === chapterId) return prev;
        return {
          ...prev,
          lastChapterId: chapterId,
          progress: {
            ...prev.progress,
            [chapterId]: Math.max(prev.progress[chapterId] ?? 0, rounded),
          },
        };
      }),
    [update],
  );

  const toggleBookmark = useCallback(
    (chapterId: string, blockIndex: number, text: string) =>
      update((prev) => {
        const exists = prev.bookmarks.some(
          (b) => b.chapterId === chapterId && b.blockIndex === blockIndex,
        );
        return {
          ...prev,
          bookmarks: exists
            ? prev.bookmarks.filter(
                (b) => !(b.chapterId === chapterId && b.blockIndex === blockIndex),
              )
            : [
                ...prev.bookmarks,
                { chapterId, blockIndex, text: text.slice(0, 200), at: Date.now() },
              ],
        };
      }),
    [update],
  );

  const reset = useCallback(() => update(() => defaultLibrary), [update]);

  return { library: value, hydrated, toggleFavorite, setProgress, toggleBookmark, reset };
}
