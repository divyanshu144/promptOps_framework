import DashboardClient from "./components/DashboardClient";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function fetchRuns() {
  const res = await fetch(`${API_URL}/leaderboard`, { cache: "no-store" });
  const data = await res.json();
  return data.runs || [];
}

async function fetchRecent() {
  const res = await fetch(`${API_URL}/runs?limit=200`, { cache: "no-store" });
  const data = await res.json();
  return data.runs || [];
}

export default async function Page() {
  const topRuns = await fetchRuns();
  const recentRuns = await fetchRecent();

  return (
    <main className="min-h-screen bg-hero">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <header className="animate-fadeUp">
          <h1 className="text-3xl md:text-4xl font-semibold tracking-tight">
            PromptOps Dashboard
          </h1>
          <p className="text-muted mt-2">
            Prompt-as-code performance, optimization, and model quality insights
          </p>
          <div className="mt-4">
            <a className="text-accent hover:text-accent2" href="/playground">
              Open Prompt Playground →
            </a>
          </div>
        </header>

        <section className="grid gap-4 md:grid-cols-3 mt-8">
          <div className="rounded-2xl border border-border bg-card shadow-glow p-5 animate-fadeUp">
            <div className="text-xs uppercase tracking-widest text-muted">Total Runs</div>
            <div className="text-2xl font-semibold mt-2 font-mono">
              {recentRuns.length}
            </div>
          </div>
          <div className="rounded-2xl border border-border bg-card shadow-glow p-5 animate-fadeUp">
            <div className="text-xs uppercase tracking-widest text-muted">Best Objective</div>
            <div className="text-2xl font-semibold mt-2 font-mono">
              {Math.max(0, ...recentRuns.map((r: any) => Number(r.objective || 0))).toFixed(4)}
            </div>
          </div>
          <div className="rounded-2xl border border-border bg-card shadow-glow p-5 animate-fadeUp">
            <div className="text-xs uppercase tracking-widest text-muted">Best Judge Score</div>
            <div className="text-2xl font-semibold mt-2 font-mono">
              {Math.max(0, ...recentRuns.map((r: any) => Number(r.judge_score || 0))).toFixed(4)}
            </div>
          </div>
        </section>

        <DashboardClient runs={recentRuns} apiUrl={API_URL} />

        <section className="mt-8">
          <div className="text-sm uppercase tracking-widest text-muted">Top Runs</div>
          <div className="mt-3 overflow-hidden rounded-2xl border border-border bg-card shadow-glow">
            <table className="w-full text-sm">
              <thead className="text-muted">
                <tr className="text-left">
                  <th className="p-3">Prompt</th>
                  <th className="p-3">Model</th>
                  <th className="p-3">Objective</th>
                  <th className="p-3">Judge Score</th>
                  <th className="p-3">Created</th>
                </tr>
              </thead>
              <tbody>
                {topRuns.length === 0 && (
                  <tr>
                    <td className="p-4 text-muted" colSpan={5}>
                      No runs yet
                    </td>
                  </tr>
                )}
                {topRuns.map((r: any, idx: number) => (
                  <tr key={idx} className="border-t border-white/5 hover:bg-white/5">
                    <td className="p-3">{r.prompt_name}</td>
                    <td className="p-3">{r.model}</td>
                    <td className="p-3 font-mono">{Number(r.objective || 0).toFixed(4)}</td>
                    <td className="p-3 font-mono">{Number(r.judge_score || 0).toFixed(4)}</td>
                    <td className="p-3 text-muted">{r.created_at}</td>
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
