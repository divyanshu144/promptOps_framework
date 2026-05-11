"use client";

import { useEffect, useState } from "react";
import { use } from "react";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type Run = {
  id: number;
  prompt_name: string;
  model: string;
  objective: number | null;
  judge_score: number | null;
  prompt_hash: string;
  regression: number;
  created_at: string;
  run_id: string | null;
};

function Sparkline({ points, width = 600, height = 140 }: { points: number[]; width?: number; height?: number }) {
  if (points.length < 2) return null;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const pad = 10;
  const scaleX = (i: number) => pad + (i * (width - pad * 2)) / Math.max(points.length - 1, 1);
  const scaleY = (v: number) =>
    height - pad - ((v - min) * (height - pad * 2)) / Math.max(max - min, 0.001);
  const pts = points.map((v, i) => `${scaleX(i).toFixed(2)},${scaleY(v).toFixed(2)}`).join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full">
      <polyline fill="none" stroke="#4de3c2" strokeWidth="2.5" points={pts} />
      {points.map((v, i) => (
        <circle
          key={i}
          cx={scaleX(i)}
          cy={scaleY(v)}
          r="3"
          fill="#4de3c2"
          opacity="0.8"
        />
      ))}
    </svg>
  );
}

export default function PromptHistoryPage({ params }: { params: Promise<{ name: string }> }) {
  const { name } = use(params);
  const decodedName = decodeURIComponent(name);

  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/prompts/${encodeURIComponent(decodedName)}/history`, { cache: "no-store" })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load history");
        return res.json();
      })
      .then((data) => setRuns(data.runs || []))
      .catch(() => setError("Could not load prompt history. Is the backend running?"))
      .finally(() => setLoading(false));
  }, [decodedName]);

  const objectives = runs.map((r) => Number(r.objective ?? 0));
  const bestObjective = objectives.length ? Math.max(...objectives) : null;
  const avgObjective = objectives.length
    ? objectives.reduce((a, b) => a + b, 0) / objectives.length
    : null;

  if (loading) {
    return (
      <main className="min-h-screen bg-hero">
        <div className="mx-auto max-w-5xl px-6 py-10 text-muted">Loading…</div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-hero">
      <div className="mx-auto max-w-5xl px-6 py-10">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-semibold">
              Prompt: <span className="font-mono text-accent">{decodedName}</span>
            </h1>
            <p className="text-muted mt-1">{runs.length} runs recorded</p>
          </div>
          <Link href="/prompts" className="text-accent hover:text-accent2 text-sm">
            ← All prompts
          </Link>
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        {/* KPIs */}
        <section className="grid gap-4 md:grid-cols-3 mt-6">
          <div className="rounded-2xl border border-border bg-card shadow-glow p-5">
            <div className="text-xs uppercase tracking-widest text-muted">Total Runs</div>
            <div className="text-2xl font-semibold mt-2 font-mono">{runs.length}</div>
          </div>
          <div className="rounded-2xl border border-border bg-card shadow-glow p-5">
            <div className="text-xs uppercase tracking-widest text-muted">Best Objective</div>
            <div className="text-2xl font-semibold mt-2 font-mono">
              {bestObjective != null ? bestObjective.toFixed(4) : "—"}
            </div>
          </div>
          <div className="rounded-2xl border border-border bg-card shadow-glow p-5">
            <div className="text-xs uppercase tracking-widest text-muted">Avg Objective</div>
            <div className="text-2xl font-semibold mt-2 font-mono">
              {avgObjective != null ? avgObjective.toFixed(4) : "—"}
            </div>
          </div>
        </section>

        {/* Trend chart */}
        {objectives.length >= 2 && (
          <section className="mt-6 rounded-2xl border border-border bg-card shadow-glow p-5">
            <div className="text-xs uppercase tracking-widest text-muted">Objective Over Time</div>
            <div className="mt-3 h-40 w-full rounded-xl bg-black/30 border border-white/10">
              <Sparkline points={objectives} />
            </div>
          </section>
        )}

        {/* Runs table */}
        <section className="mt-6">
          <div className="text-sm uppercase tracking-widest text-muted">All Runs</div>
          <div className="mt-3 overflow-hidden rounded-2xl border border-border bg-card shadow-glow">
            <table className="w-full text-sm">
              <thead className="text-muted">
                <tr className="text-left">
                  <th className="p-3">ID</th>
                  <th className="p-3">Model</th>
                  <th className="p-3">Objective</th>
                  <th className="p-3">Judge Score</th>
                  <th className="p-3">Hash</th>
                  <th className="p-3">Created</th>
                  <th className="p-3"></th>
                </tr>
              </thead>
              <tbody>
                {runs.length === 0 && (
                  <tr>
                    <td className="p-4 text-muted" colSpan={7}>No runs yet.</td>
                  </tr>
                )}
                {runs.map((r) => (
                  <tr key={r.id} className="border-t border-white/5 hover:bg-white/5">
                    <td className="p-3 font-mono text-muted">{r.id}</td>
                    <td className="p-3">{r.model}</td>
                    <td className="p-3 font-mono">
                      {Number(r.objective ?? 0).toFixed(4)}
                      {r.regression === 1 && (
                        <span className="ml-2 inline-flex items-center rounded-full bg-red-500/15 px-2 py-0.5 text-xs text-red-400 font-medium">
                          ↓
                        </span>
                      )}
                    </td>
                    <td className="p-3 font-mono">{Number(r.judge_score ?? 0).toFixed(4)}</td>
                    <td className="p-3 font-mono text-muted text-xs truncate max-w-[100px]">
                      {r.prompt_hash?.slice(0, 8)}…
                    </td>
                    <td className="p-3 text-muted">{r.created_at}</td>
                    <td className="p-3">
                      <Link href={`/runs/${r.id}`} className="text-accent hover:text-accent2">
                        Details
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
