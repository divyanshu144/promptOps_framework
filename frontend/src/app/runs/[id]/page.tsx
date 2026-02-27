"use client";

import { useEffect, useState } from "react";
import { use } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const MLFLOW_URL = process.env.NEXT_PUBLIC_MLFLOW_URL || "http://localhost:5000";

type RunResult = {
  id: number;
  test_idx: number;
  input: Record<string, any>;
  expected?: string;
  output: string;
  judge_score?: number;
  judge_criteria?: Record<string, number>;
  judge_reasoning?: string;
  metrics?: Record<string, any>;
};

export default function RunDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [run, setRun] = useState<any>(null);
  const [results, setResults] = useState<RunResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  useEffect(() => {
    fetch(`${API_URL}/runs/${id}`, { cache: "no-store" })
      .then((res) => {
        if (!res.ok) throw new Error("not found");
        return res.json();
      })
      .then((data) => {
        setRun(data.run);
        setResults(data.results || []);
      })
      .catch(() => setError("Run not found or API unavailable."))
      .finally(() => setLoading(false));
  }, [id]);

  const toggleExpand = (idx: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  if (loading) {
    return (
      <main className="min-h-screen bg-hero">
        <div className="mx-auto max-w-4xl px-6 py-10 text-muted">Loading…</div>
      </main>
    );
  }

  if (error || !run) {
    return (
      <main className="min-h-screen bg-hero">
        <div className="mx-auto max-w-4xl px-6 py-10">
          <div className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {error || "Run not found"}
          </div>
          <a className="text-accent hover:text-accent2 mt-4 inline-block" href="/">
            Back
          </a>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-hero">
      <div className="mx-auto max-w-4xl px-6 py-10">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold">Run Details</h1>
            <p className="text-muted mt-2 font-mono">ID: {run.id}</p>
          </div>
          <a className="text-accent hover:text-accent2" href="/">
            Back
          </a>
        </div>

        {run.regression === 1 && (
          <div className="mt-4 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            ↓ Regression detected — this run scored lower than the previous best.
          </div>
        )}

        <div className="mt-6 rounded-2xl border border-border bg-card shadow-glow p-5">
          <div className="grid gap-4 md:grid-cols-2 text-sm">
            <div>
              <div className="text-muted text-xs uppercase tracking-widest">Prompt</div>
              <div className="mt-1">{run.prompt_name}</div>
            </div>
            <div>
              <div className="text-muted text-xs uppercase tracking-widest">Model</div>
              <div className="mt-1">{run.model}</div>
            </div>
            <div>
              <div className="text-muted text-xs uppercase tracking-widest">Objective</div>
              <div className="mt-1 font-mono">{Number(run.objective || 0).toFixed(4)}</div>
            </div>
            <div>
              <div className="text-muted text-xs uppercase tracking-widest">Judge Score</div>
              <div className="mt-1 font-mono">{Number(run.judge_score || 0).toFixed(4)}</div>
            </div>
            <div>
              <div className="text-muted text-xs uppercase tracking-widest">Created At</div>
              <div className="mt-1">{run.created_at}</div>
            </div>
            <div>
              <div className="text-muted text-xs uppercase tracking-widest">Prompt Hash</div>
              <div className="mt-1 font-mono break-all">{run.prompt_hash}</div>
            </div>
          </div>
        </div>

        {run.run_id && (
          <div className="mt-4">
            <a
              className="text-accent hover:text-accent2"
              href={`${MLFLOW_URL}/#/experiments/0/runs/${run.run_id}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              View in MLflow →
            </a>
          </div>
        )}

        {results.length > 0 && (
          <section className="mt-8">
            <div className="text-sm uppercase tracking-widest text-muted">
              Per-Test-Case Breakdown ({results.length} cases)
            </div>
            <div className="mt-3 space-y-3">
              {results.map((r) => (
                <div
                  key={r.id}
                  className="rounded-2xl border border-border bg-card shadow-glow overflow-hidden"
                >
                  <button
                    className="w-full flex items-center justify-between p-4 text-left hover:bg-white/5"
                    onClick={() => toggleExpand(r.test_idx)}
                  >
                    <span className="text-sm font-medium">
                      Case #{r.test_idx + 1} — Judge:{" "}
                      <span className="font-mono">{Number(r.judge_score || 0).toFixed(3)}</span>
                    </span>
                    <span className="text-muted text-xs">
                      {expanded.has(r.test_idx) ? "▲ collapse" : "▼ expand"}
                    </span>
                  </button>

                  {expanded.has(r.test_idx) && (
                    <div className="border-t border-border p-4 space-y-4 text-sm">
                      <div>
                        <div className="text-xs uppercase tracking-widest text-muted">Input</div>
                        <pre className="mt-1 whitespace-pre-wrap text-xs bg-black/30 rounded-lg p-3">
                          {JSON.stringify(r.input, null, 2)}
                        </pre>
                      </div>
                      {r.expected && (
                        <div>
                          <div className="text-xs uppercase tracking-widest text-muted">Expected</div>
                          <pre className="mt-1 whitespace-pre-wrap text-xs bg-black/30 rounded-lg p-3">
                            {r.expected}
                          </pre>
                        </div>
                      )}
                      <div>
                        <div className="text-xs uppercase tracking-widest text-muted">Output</div>
                        <pre className="mt-1 whitespace-pre-wrap text-xs bg-black/30 rounded-lg p-3">
                          {r.output}
                        </pre>
                      </div>
                      {r.judge_criteria && Object.keys(r.judge_criteria).length > 0 && (
                        <div>
                          <div className="text-xs uppercase tracking-widest text-muted">Criteria Scores</div>
                          <div className="mt-1 flex flex-wrap gap-2">
                            {Object.entries(r.judge_criteria).map(([k, v]) => (
                              <span
                                key={k}
                                className="rounded-full bg-accent/10 px-3 py-1 text-xs text-accent"
                              >
                                {k}: {Number(v).toFixed(2)}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {r.judge_reasoning && (
                        <div>
                          <div className="text-xs uppercase tracking-widest text-muted">Reasoning</div>
                          <p className="mt-1 text-muted text-xs">{r.judge_reasoning}</p>
                        </div>
                      )}
                      {r.metrics && (
                        <div>
                          <div className="text-xs uppercase tracking-widest text-muted">Metrics</div>
                          <div className="mt-1 flex flex-wrap gap-2">
                            {Object.entries(r.metrics)
                              .filter(([, v]) => v !== null && v !== undefined)
                              .map(([k, v]) => (
                                <span
                                  key={k}
                                  className="rounded-full bg-white/5 px-3 py-1 text-xs text-muted"
                                >
                                  {k}: {typeof v === "number" ? Number(v).toFixed(4) : String(v)}
                                </span>
                              ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
