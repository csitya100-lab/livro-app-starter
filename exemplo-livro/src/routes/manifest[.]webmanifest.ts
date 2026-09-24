import { createFileRoute } from "@tanstack/react-router";
import { theme } from "@/content";

// Manifesto PWA gerado a partir de content/theme.json (substitui public/manifest.webmanifest).
const manifest = {
  name: theme.title,
  short_name: theme.shortName,
  description: theme.description,
  start_url: "/",
  scope: "/",
  display: "standalone",
  orientation: "portrait",
  background_color: theme.colors.themeColor,
  theme_color: theme.colors.themeColor,
  lang: theme.lang,
  icons: [
    { src: `/${theme.icons["192"]}`, sizes: "192x192", type: "image/png", purpose: "any" },
    { src: `/${theme.icons["512"]}`, sizes: "512x512", type: "image/png", purpose: "any" },
    { src: `/${theme.icons["512"]}`, sizes: "512x512", type: "image/png", purpose: "maskable" },
  ],
};

export const Route = createFileRoute("/manifest.webmanifest")({
  server: {
    handlers: {
      GET: () =>
        new Response(JSON.stringify(manifest), {
          headers: { "content-type": "application/manifest+json; charset=utf-8" },
        }),
    },
  },
});
