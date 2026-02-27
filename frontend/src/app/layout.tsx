import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "PromptOps Dashboard",
  description: "Prompt-as-code optimization and evaluation dashboard.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <nav className="sticky top-0 z-50 border-b border-border bg-black/60 backdrop-blur-md">
          <div className="mx-auto max-w-6xl px-6 py-3 flex items-center gap-6 text-sm">
            <span className="font-semibold text-accent tracking-tight">PromptOps</span>
            <Link href="/" className="text-muted hover:text-accent transition-colors">
              Dashboard
            </Link>
            <Link href="/playground" className="text-muted hover:text-accent transition-colors">
              Playground
            </Link>
            <Link href="/optimize" className="text-muted hover:text-accent transition-colors">
              Optimize
            </Link>
            <Link href="/suites" className="text-muted hover:text-accent transition-colors">
              Suites
            </Link>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
