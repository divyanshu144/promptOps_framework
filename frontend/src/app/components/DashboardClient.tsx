"use client";

import { useEffect, useMemo, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type Run = {
  id?: number;
  prompt_name?: string;
  model?: string;
  objective?: number;
  judge_score?: number;
  created_at?: string;
  run_id?: string;
  prompt_hash?: string;
  regression?: number;
};

function sparkline(points: number[], width = 640, height = 180) {
  if (points.length === 0) return "";
  const min = Math.min(...points);
  const max = Math.max(...points);
  const pad = 10;
  const scaleX = (i: number) =>
    pad + (i * (width - pad * 2)) / Math.max(points.length - 1, 1);
  const scaleY = (v: number) =>
    height - pad - ((v - min) * (height - pad * 2)) / Math.max(max - min, 1);
  return points
    .map((v, i) => `${scaleX(i).toFixed(2)},${scaleY(v).toFixed(2)}`)
    .join(" ");
}

export default function DashboardClient({
  runs: initialRuns,
  apiUrl,
}: {
  runs: Run[];
  apiUrl: string;
}) {
  const [runs, setRuns] = useState<Run[]>(initialRuns);
  const [promptFilter, setPromptFilter] = useState("");
  const [modelFilter, setModelFilter] = useState("");
  const [metric, setMetric] = useState<"objective" | "judge_score">("objective");
  const [compare, setCompare] = useState(false);
  const [apiError, setApiError] = useState(false);

  // KPI computed from live runs
  const totalRuns = runs.length;
  const bestObjective = Math.max(0, ...runs.map((r) => Number(r.objective || 0)));
  const bestJudge = Math.max(0, ...runs.map((r) => Number(r.judge_score || 0)));

  // Auto-refresh every 10 seconds
  useEffect(() => {
    const refresh = async () => {
      try {
        const res = await fetch(`${API_URL}/runs?limit=200`, { cache: "no-store" });
        if (!res.ok) throw new Error("non-ok");
        const data = await res.json();
        setRuns(data.runs || []);
        setApiError(false);
      } catch {
        setApiError(true);
      }
    };

    const id = setInterval(refresh, 10_000);
    return () => clearInterval(id);
  }, []);

  const prompts = useMemo(() => {
    return Array.from(new Set(runs.map((r) => r.prompt_name).filter(Boolean) as string[]));
  }, [runs]);

  const models = useMemo(() => {
    return Array.from(new Set(runs.map((r) => r.model).filter(Boolean) as string[]));
  }, [runs]);

  const filtered = useMemo(() => {
    return runs.filter((r) => {
      if (promptFilter && r.prompt_name !== promptFilter) return false;
      if (modelFilter && r.model !== modelFilter) return false;
      return true;
    });
  }, [runs, promptFilter, modelFilter]);

  const primary = filtered.map((r) => Number(r[metric] || 0));
  const secondary = filtered.map((r) => Number(r.judge_score || 0));

  return (
    <>
      {apiError && (
        <div className="mt-4 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          API unavailable — showing last known data. Check that the backend is running.
        </div>
      )}

      {/* Live KPIs */}
      <section className="grid gap-4 md:grid-cols-3 mt-6">
        <div className="rounded-2xl border border-border bg-card shadow-glow p-5">
          <div className="text-xs uppercase tracking-widest text-muted">Total Runs</div>
          <div className="text-2xl font-semibold mt-2 font-mono">{totalRuns}</div>
        </div>
        <div className="rounded-2xl border border-border bg-card shadow-glow p-5">
          <div className="text-xs uppercase tracking-widest text-muted">Best Objective</div>
          <div className="text-2xl font-semibold mt-2 font-mono">{bestObjective.toFixed(4)}</div>
        </div>
        <div className="rounded-2xl border border-border bg-card shadow-glow p-5">
          <div className="text-xs uppercase tracking-widest text-muted">Best Judge Score</div>
          <div className="text-2xl font-semibold mt-2 font-mono">{bestJudge.toFixed(4)}</div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3 mt-6">
        <div className="md:col-span-2 rounded-2xl border border-border bg-card shadow-glow p-5">
          <div className="text-xs uppercase tracking-widest text-muted">Trend</div>
          <div className="mt-3 h-56 w-full rounded-xl bg-black/30 border border-white/10">
            <svg viewBox="0 0 640 180" className="w-full h-full">
              <polyline
                fill="none"
                stroke="#4de3c2"
                strokeWidth="3"
                points={sparkline(primary)}
              />
              {compare && (
                <polyline
                  fill="none"
                  stroke="#5aa7ff"
                  strokeWidth="2"
                  opacity="0.6"
                  points={sparkline(secondary)}
                />
              )}
            </svg>
          </div>
        </div>
        <div className="rounded-2xl border border-border bg-card shadow-glow p-5">
          <div className="text-xs uppercase tracking-widest text-muted">Quick Links</div>
          <div className="mt-3 space-y-3 text-sm">
            <div className="text-muted">API: {apiUrl}</div>
            <div className="text-muted">Filters</div>
            <div className="flex flex-col gap-2">
              <label className="text-xs uppercase tracking-widest text-muted">
                Prompt
                <select
                  className="ml-2 rounded-lg border border-border bg-black/40 px-2 py-1"
                  value={promptFilter}
                  onChange={(e) => setPromptFilter(e.target.value)}
                >
                  <option value="">All</option>
                  {prompts.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs uppercase tracking-widest text-muted">
                Model
                <select
                  className="ml-2 rounded-lg border border-border bg-black/40 px-2 py-1"
                  value={modelFilter}
                  onChange={(e) => setModelFilter(e.target.value)}
                >
                  <option value="">All</option>
                  {models.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs uppercase tracking-widest text-muted">
                Metric
                <select
                  className="ml-2 rounded-lg border border-border bg-black/40 px-2 py-1"
                  value={metric}
                  onChange={(e) => setMetric(e.target.value as "objective" | "judge_score")}
                >
                  <option value="objective">Objective</option>
                  <option value="judge_score">Judge Score</option>
                </select>
              </label>
              <label className="text-xs uppercase tracking-widest text-muted">
                <input
                  className="mr-2"
                  type="checkbox"
                  checked={compare}
                  onChange={(e) => setCompare(e.target.checked)}
                />
                Compare Judge
              </label>
            </div>
          </div>
        </div>

        <div className="md:col-span-3">
          <div className="text-sm uppercase tracking-widest text-muted">Recent Runs</div>
          <div className="mt-3 overflow-hidden rounded-2xl border border-border bg-card shadow-glow">
            <table className="w-full text-sm">
              <thead className="text-muted">
                <tr className="text-left">
                  <th className="p-3">Prompt</th>
                  <th className="p-3">Model</th>
                  <th className="p-3">Objective</th>
                  <th className="p-3">Judge Score</th>
                  <th className="p-3">Created</th>
                  <th className="p-3">Run</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 && (
                  <tr>
                    <td className="p-4 text-muted" colSpan={6}>
                      No runs yet
                    </td>
                  </tr>
                )}
                {filtered.slice(-50).map((r, idx) => (
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
                    <td className="p-3">
                      {r.id ? (
                        <a className="text-accent hover:text-accent2" href={`/runs/${r.id}`}>
                          Details
                        </a>
                      ) : (
                        "-"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </>
  );
}
