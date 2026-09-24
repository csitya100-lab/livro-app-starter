import { Link, useRouterState } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { BookOpen, Search, Images, Bookmark, Settings } from "lucide-react";

const tabs = [
  { to: "/", label: "Início", icon: BookOpen },
  { to: "/busca", label: "Busca", icon: Search },
  { to: "/figuras", label: "Figuras", icon: Images },
  { to: "/favoritos", label: "Salvos", icon: Bookmark },
  { to: "/ajustes", label: "Ajustes", icon: Settings },
] as const;

export function AppShell({
  children,
  title,
  hideTabBar = false,
}: {
  children: ReactNode;
  title?: string;
  hideTabBar?: boolean;
}) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <div className="min-h-screen bg-background">
      {title ? (
        <header className="safe-top sticky top-0 z-30 border-b border-border/70 bg-background/85 backdrop-blur-xl">
          <div className="mx-auto flex h-12 max-w-2xl items-center px-4">
            <h1 className="text-[15px] font-semibold tracking-tight">{title}</h1>
          </div>
        </header>
      ) : null}

      <main className={hideTabBar ? "" : "pb-[calc(4.5rem+env(safe-area-inset-bottom))]"}>
        {children}
      </main>

      {hideTabBar ? null : (
        <nav className="safe-bottom fixed inset-x-0 bottom-0 z-40 border-t border-border/70 bg-background/90 backdrop-blur-xl">
          <ul className="mx-auto flex max-w-2xl">
            {tabs.map(({ to, label, icon: Icon }) => {
              const active = to === "/" ? pathname === "/" : pathname.startsWith(to);
              return (
                <li key={to} className="flex-1">
                  <Link
                    to={to}
                    className={`flex flex-col items-center gap-1 py-2 text-[10px] font-medium transition-colors ${
                      active ? "text-accent" : "text-muted-foreground"
                    }`}
                  >
                    <Icon className="size-[22px]" strokeWidth={active ? 2.4 : 1.8} />
                    {label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      )}
    </div>
  );
}
