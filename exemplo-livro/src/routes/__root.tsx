import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  HeadContent,
  Scripts,
} from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";

import appCss from "../styles.css?url";
import { reportLovableError } from "../lib/lovable-error-reporting";
import { useSettings } from "../lib/reader-store";
import { AudioPlayerProvider } from "../lib/audio-player";
import { theme } from "@/content";

const fontsHref =
  "https://fonts.googleapis.com/css2?family=" +
  encodeURIComponent(theme.fonts.sans).replace(/%20/g, "+") +
  ":wght@400;500;600;700;800&family=" +
  encodeURIComponent(theme.fonts.serif).replace(/%20/g, "+") +
  ":ital,wght@0,400;0,600;0,700;1,400&display=swap";

// Variáveis de identidade lidas de theme.json; styles.css consome estas variáveis.
const vars = (c: typeof theme.colors.light) =>
  `--background:${c.background};--foreground:${c.foreground};` +
  `--primary:${c.primary};--primary-foreground:${c.primaryForeground};` +
  `--accent:${c.accent};--accent-foreground:${c.accentForeground};` +
  `--highlight:${c.highlight};` +
  Object.entries(c.blocks)
    .map(([nome, cor]) => `--block-${nome}:${cor};`)
    .join("");
const themeCss =
  `:root{--theme-font-sans:"${theme.fonts.sans}";--theme-font-serif:"${theme.fonts.serif}";${vars(theme.colors.light)}}` +
  `.dark{${vars(theme.colors.dark)}}`;


function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-7xl font-bold text-foreground">404</h1>
        <h2 className="mt-4 text-xl font-semibold text-foreground">Page not found</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="mt-6">
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Go home
          </Link>
        </div>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  console.error(error);
  const router = useRouter();
  useEffect(() => {
    reportLovableError(error, { boundary: "tanstack_root_error_component" });
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-semibold tracking-tight text-foreground">
          This page didn't load
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Something went wrong on our end. You can try refreshing or head back home.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <button
            onClick={() => {
              router.invalidate();
              reset();
            }}
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Try again
          </button>
          <a
            href="/"
            className="inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
          >
            Go home
          </a>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      {
        name: "viewport",
        content: "width=device-width, initial-scale=1, viewport-fit=cover, maximum-scale=1",
      },
      { title: theme.title },
      { name: "description", content: theme.description },
      { name: "theme-color", content: theme.colors.themeColor },
      { name: "apple-mobile-web-app-capable", content: "yes" },
      { name: "apple-mobile-web-app-status-bar-style", content: "black-translucent" },
      { name: "apple-mobile-web-app-title", content: theme.shortName },
      { property: "og:title", content: theme.title },
      { property: "og:description", content: theme.description },
      { property: "og:type", content: "book" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
    links: [
      {
        rel: "stylesheet",
        href: appCss,
      },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "anonymous" },
      { rel: "stylesheet", href: fontsHref },
      { rel: "manifest", href: "/manifest.webmanifest" },
      { rel: "icon", type: "image/png", href: "/favicon.png" },
      { rel: "apple-touch-icon", href: `/${theme.icons["180"]}` },
    ],
  }),

  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang={theme.lang}>
      <head>
        <HeadContent />
        <style dangerouslySetInnerHTML={{ __html: themeCss }} />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  useSettings();

  return (
    <QueryClientProvider client={queryClient}>
      <AudioPlayerProvider>
        {/* Required: nested routes render here. Removing <Outlet /> breaks all child routes. */}
        <Outlet />
      </AudioPlayerProvider>
    </QueryClientProvider>
  );

}
