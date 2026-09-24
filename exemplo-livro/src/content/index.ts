// Ponto único de leitura do conteúdo. A fonte de verdade é content/ (book.json, theme.json, images/, videos/).
import bookJson from "../../content/book.json";
import themeJson from "../../content/theme.json";
import type { Chapter } from "./types";

export type { Band, Block, Chapter, Field, PoseidonGroup, TextBlock } from "./types";
export { isTextBlock } from "./types";

export const theme = themeJson;

export const chapters = bookJson.chapters as unknown as Chapter[];

/** Nome do arquivo em content/<pasta>/ -> URL servida pelo Vite. */
function byFilename(files: Record<string, string>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(files).map(([path, url]) => [path.slice(path.lastIndexOf("/") + 1), url]),
  );
}

export const images = byFilename(
  import.meta.glob("../../content/images/*.{png,jpg,jpeg,webp,svg}", {
    eager: true,
    import: "default",
    query: "?url",
  }) as Record<string, string>,
);

export const videos = byFilename(
  import.meta.glob("../../content/videos/*.{mp4,webm}", {
    eager: true,
    import: "default",
    query: "?url",
  }) as Record<string, string>,
);

export const coverUrl = images[theme.cover.slice(theme.cover.lastIndexOf("/") + 1)] ?? "";
