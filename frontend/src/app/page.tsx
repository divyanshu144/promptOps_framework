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
    <main className="min-h-screen bg-hero">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <header className="animate-fadeUp">
          <h1 className="text-3xl md:text-4xl font-semibold tracking-tight">
            PromptOps Dashboard
          </h1>
          <p className="text-muted mt-2">
            Prompt-as-code performance, optimization, and model quality insights
          </p>
        </header>

        {/* DashboardClient handles KPIs + trend + recent runs with auto-refresh */}
        <DashboardClient runs={recentRuns} apiUrl={API_URL} />

        <section className="mt-8">
          <div className="text-sm uppercase tracking-widest text-muted">Top Runs by Objective</div>
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
                    <td className="p-3">
                      {r.prompt_name}
                      {r.regression === 1 && (
                        <span className="ml-2 inline-flex items-center rounded-full bg-red-500/15 px-2 py-0.5 text-xs text-red-400 font-medium">
                          ↓ Regression
                        </span>
                      )}
                    </td>
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
