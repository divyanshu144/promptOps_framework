"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Dashboard", exact: true },
  { href: "/playground", label: "Playground", exact: false },
  { href: "/optimize", label: "Optimize", exact: false },
  { href: "/suites", label: "Suites", exact: false },
  { href: "/prompts", label: "Prompts", exact: false },
];

export default function NavBar() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-50 border-b border-border bg-ink/75 backdrop-blur-xl">
      <div className="mx-auto max-w-6xl px-6 h-11 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2 group shrink-0">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-50" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-accent" />
            </span>
            <span className="text-sm font-semibold tracking-tight text-white group-hover:text-accent transition-colors duration-150">
              PromptOps
            </span>
          </Link>

          <div className="flex items-center gap-0.5">
            {links.map(({ href, label, exact }) => {
              const isActive = exact ? pathname === href : pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={`px-3 py-1.5 rounded-md text-[13px] font-medium transition-all duration-150 ${
                    isActive
                      ? "bg-accent/12 text-accent"
                      : "text-muted hover:text-white hover:bg-white/[0.05]"
                  }`}
                >
                  {label}
                </Link>
              );
            })}
          </div>
        </div>

        <span className="hidden md:block text-[11px] font-mono text-muted/40 tracking-wider">
          prompt-as-code
        </span>
      </div>
    </nav>
  );
}
