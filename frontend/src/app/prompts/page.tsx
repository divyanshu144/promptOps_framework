import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type PromptSummary = {
  prompt_name: string;
  run_count: number;
  best_objective: number | null;
  avg_objective: number | null;
  last_run_at: string | null;
};

async function fetchPrompts(): Promise<PromptSummary[]> {
  try {
    const res = await fetch(`${API_URL}/prompts`, { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    return data.prompts || [];
  } catch {
    return [];
  }
}

export default async function PromptsPage() {
  const prompts = await fetchPrompts();

  return (
    <main className="min-h-screen">
      <div className="mx-auto max-w-5xl px-6 py-8">
        <header className="animate-fadeUp">
          <h1 className="text-2xl font-semibold tracking-tight">Prompt History</h1>
          <p className="text-muted text-sm mt-1">
            All prompt names tracked across runs, with aggregate performance stats.
          </p>
        </header>

        <section className="mt-6">
          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-4 py-2.5 text-left text-[10px] font-mono uppercase tracking-widest text-muted/70">
                    Prompt Name
                  </th>
                  <th className="px-4 py-2.5 text-right text-[10px] font-mono uppercase tracking-widest text-muted/70">
                    Runs
                  </th>
                  <th className="px-4 py-2.5 text-right text-[10px] font-mono uppercase tracking-widest text-muted/70">
                    Best Objective
                  </th>
                  <th className="px-4 py-2.5 text-right text-[10px] font-mono uppercase tracking-widest text-muted/70">
                    Avg Objective
                  </th>
                  <th className="px-4 py-2.5 text-left text-[10px] font-mono uppercase tracking-widest text-muted/70 hidden md:table-cell">
                    Last Run
                  </th>
                  <th className="px-4 py-2.5 text-right text-[10px] font-mono uppercase tracking-widest text-muted/70"></th>
                </tr>
              </thead>
              <tbody>
                {prompts.length === 0 && (
                  <tr>
                    <td className="px-4 py-8 text-center text-muted" colSpan={6}>
                      No runs recorded yet.{" "}
                      <Link
                        href="/playground"
                        className="text-accent hover:text-accent/80 underline underline-offset-2"
                      >
                        Run a prompt →
                      </Link>
                    </td>
                  </tr>
                )}
                {prompts.map((p) => (
                  <tr
                    key={p.prompt_name}
                    className="border-t border-border/30 hover:bg-white/[0.025] transition-colors"
                  >
                    <td className="px-4 py-3 font-mono text-accent text-sm font-medium">
                      {p.prompt_name}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums text-muted text-sm">
                      {p.run_count}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums text-white text-sm">
                      {p.best_objective != null
                        ? Number(p.best_objective).toFixed(4)
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums text-muted text-sm">
                      {p.avg_objective != null
                        ? Number(p.avg_objective).toFixed(4)
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-muted font-mono text-xs hidden md:table-cell">
                      {p.last_run_at ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        href={`/prompts/${encodeURIComponent(p.prompt_name)}`}
                        className="text-[11px] font-mono text-muted/60 hover:text-accent transition-colors"
                      >
                        History →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}
