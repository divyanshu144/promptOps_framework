"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function OptimizePage() {
  const [system, setSystem] = useState("You are a helpful assistant.");
  const [template, setTemplate] = useState("{input}");
  const [model, setModel] = useState("llama3.1");
  const [judgeModel, setJudgeModel] = useState("llama3.1");
  const [iterations, setIterations] = useState(2);
  const [useRewriter, setUseRewriter] = useState(true);
  const [provider, setProvider] = useState("ollama");

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  async function runOptimize() {
    setLoading(true);
    setError(null);
    setResult(null);

    const body = {
      prompt: {
        name: "optimize_prompt",
        system,
        template,
        model,
        params: { temperature: 0.2, max_tokens: 200 },
        context_limit: 4096,
        provider,
      },
      judge_model: judgeModel,
      iterations: Math.max(1, Math.min(5, iterations)),
      use_rewriter: useRewriter,
    };

    try {
      const res = await fetch(`${API_URL}/optimize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setResult(data);
    } catch (e: any) {
      setError(e.message || "Failed to reach API.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-hero">
      <div className="mx-auto max-w-4xl px-6 py-10">
        <header>
          <h1 className="text-3xl font-semibold">Prompt Optimizer</h1>
          <p className="text-muted mt-2">
            Automatically find the best prompt variant using iterative evaluation.
          </p>
        </header>

        <section className="mt-8 space-y-4">
          <div className="rounded-2xl border border-border bg-card shadow-glow p-5 space-y-4">
            <div>
              <div className="text-xs uppercase tracking-widest text-muted">System Prompt</div>
              <textarea
                className="mt-2 w-full h-24 rounded-lg border border-border bg-black/40 p-3 text-sm"
                value={system}
                onChange={(e) => setSystem(e.target.value)}
              />
            </div>
            <div>
              <div className="text-xs uppercase tracking-widest text-muted">Template</div>
              <textarea
                className="mt-2 w-full h-16 rounded-lg border border-border bg-black/40 p-3 text-sm font-mono"
                value={template}
                onChange={(e) => setTemplate(e.target.value)}
              />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="text-xs uppercase tracking-widest text-muted block">
                Model
                <input
                  className="mt-2 w-full rounded-lg border border-border bg-black/40 px-3 py-2 text-sm"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                />
              </label>
              <label className="text-xs uppercase tracking-widest text-muted block">
                Judge Model
                <input
                  className="mt-2 w-full rounded-lg border border-border bg-black/40 px-3 py-2 text-sm"
                  value={judgeModel}
                  onChange={(e) => setJudgeModel(e.target.value)}
                />
              </label>
              <label className="text-xs uppercase tracking-widest text-muted block">
                Iterations (1–5)
                <input
                  type="number"
                  min={1}
                  max={5}
                  className="mt-2 w-full rounded-lg border border-border bg-black/40 px-3 py-2 text-sm"
                  value={iterations}
                  onChange={(e) => setIterations(Number(e.target.value))}
                />
              </label>
              <label className="text-xs uppercase tracking-widest text-muted block">
                Provider
                <select
                  className="mt-2 w-full rounded-lg border border-border bg-black/40 px-3 py-2 text-sm"
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                >
                  <option value="ollama">Ollama</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                </select>
              </label>
            </div>
            <label className="flex items-center gap-2 text-xs uppercase tracking-widest text-muted">
              <input
                type="checkbox"
                checked={useRewriter}
                onChange={(e) => setUseRewriter(e.target.checked)}
              />
              Use LLM Rewriter
            </label>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={runOptimize}
              disabled={loading}
              className="inline-flex items-center justify-center rounded-lg bg-accent px-5 py-2.5 text-black font-semibold hover:bg-accent2 disabled:opacity-50"
            >
              {loading ? "Optimizing… (this may take a while)" : "Run Optimizer"}
            </button>
            {error && (
              <div className="text-sm text-red-400">
                {error}{" "}
                <button onClick={runOptimize} className="underline text-red-300 hover:text-red-200">
                  Retry
                </button>
              </div>
            )}
          </div>
        </section>

        {result && (
          <section className="mt-8 space-y-4">
            <div className="text-sm uppercase tracking-widest text-muted">Best Result</div>

            <div className="rounded-2xl border border-border bg-card shadow-glow p-5 space-y-3">
              <div className="flex items-center gap-3">
                <span className="text-xs uppercase tracking-widest text-muted">Avg Objective</span>
                <span className="font-mono text-accent">
                  {Number(result.best_result?.avg_objective || 0).toFixed(4)}
                </span>
                <span className="text-xs uppercase tracking-widest text-muted ml-4">Avg Judge Score</span>
                <span className="font-mono">
                  {Number(result.best_result?.avg_judge_score || 0).toFixed(4)}
                </span>
              </div>

              <div>
                <div className="text-xs uppercase tracking-widest text-muted">Best Prompt Name</div>
                <div className="mt-1 font-mono text-sm">{result.best_prompt?.name}</div>
              </div>

              <div>
                <div className="text-xs uppercase tracking-widest text-muted">System</div>
                <pre className="mt-1 whitespace-pre-wrap text-sm bg-black/30 rounded-lg p-3">
                  {result.best_prompt?.system}
                </pre>
              </div>

              <div>
                <div className="text-xs uppercase tracking-widest text-muted">Template</div>
                <pre className="mt-1 whitespace-pre-wrap text-sm bg-black/30 rounded-lg p-3 font-mono">
                  {result.best_prompt?.template}
                </pre>
              </div>

              {result.best_result?.regression && (
                <div className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                  ↓ {result.best_result.regression_warning}
                </div>
              )}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
