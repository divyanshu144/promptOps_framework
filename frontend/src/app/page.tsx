import Link from "next/link";
import DashboardClient from "./components/DashboardClient";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function fetchRuns() {
  try {
    const res = await fetch(`${API_URL}/leaderboard`, { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    return data.runs || [];
  } catch {
    return [];
  }
}

async function fetchRecent() {
  try {
    const res = await fetch(`${API_URL}/runs?limit=200`, { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    return data.runs || [];
  } catch {
    return [];
  }
}

export default async function Page() {
  const topRuns = await fetchRuns();
  const recentRuns = await fetchRecent();

  return (
    <main className="min-h-screen">
      <div className="mx-auto max-w-6xl px-6 py-8">
        <header className="animate-fadeUp flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2.5">
              <span className="text-[10px] font-mono uppercase tracking-widest text-accent bg-accent/8 border border-accent/18 rounded px-2 py-0.5">
                prompt-as-code
              </span>
            </div>
            <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
            <p className="text-muted text-sm mt-1">
              Performance metrics, optimization history, and regression tracking.
            </p>
          </div>
          <Link
            href="/playground"
            className="shrink-0 inline-flex items-center gap-1.5 rounded-lg bg-accent px-3.5 py-2 text-sm font-semibold text-black hover:bg-accent/90 transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            New run
          </Link>
        </header>

        <DashboardClient runs={recentRuns} apiUrl={API_URL} />

        {topRuns.length > 0 && (
          <section className="mt-5">
            <div className="text-[10px] font-mono uppercase tracking-widest text-muted mb-2">
              Leaderboard — Top 10 by Objective
            </div>
            <div className="rounded-xl border border-border bg-card overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-4 py-2.5 text-left text-[10px] font-mono uppercase tracking-widest text-muted/70 w-10">#</th>
                    <th className="px-4 py-2.5 text-left text-[10px] font-mono uppercase tracking-widest text-muted/70">Prompt</th>
                    <th className="px-4 py-2.5 text-left text-[10px] font-mono uppercase tracking-widest text-muted/70">Model</th>
                    <th className="px-4 py-2.5 text-right text-[10px] font-mono uppercase tracking-widest text-muted/70">Objective</th>
                    <th className="px-4 py-2.5 text-right text-[10px] font-mono uppercase tracking-widest text-muted/70">Judge</th>
                    <th className="px-4 py-2.5 text-right text-[10px] font-mono uppercase tracking-widest text-muted/70"></th>
                  </tr>
                </thead>
                <tbody>
                  {topRuns.map((r: any, idx: number) => (
                    <tr
                      key={idx}
                      className="border-t border-border/30 hover:bg-white/[0.025] transition-colors"
                    >
                      <td className="px-4 py-3 font-mono text-[11px] text-muted/40">
                        {String(idx + 1).padStart(2, "0")}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Link
                            href={`/prompts/${encodeURIComponent(r.prompt_name)}`}
                            className="text-white hover:text-accent transition-colors font-medium"
                          >
                            {r.prompt_name}
                          </Link>
                          {r.regression === 1 && (
                            <span className="inline-flex items-center gap-1 rounded bg-danger/10 border border-danger/20 px-1.5 py-0.5 text-[10px] text-danger font-mono">
                              ↓ regression
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-muted font-mono text-xs">{r.model}</td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-accent">
                        {Number(r.objective || 0).toFixed(4)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-muted">
                        {Number(r.judge_score || 0).toFixed(4)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          href={`/runs/${r.id}`}
                          className="text-[11px] font-mono text-muted/60 hover:text-accent transition-colors"
                        >
                          #{r.id}
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
