"use client";

import { useRef, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

function apiError(e: unknown, url: string): string {
  const msg = e instanceof Error ? e.message : String(e);
  if (
    msg.includes("Failed to fetch") ||
    msg.includes("NetworkError") ||
    msg.includes("ERR_CONNECTION_REFUSED")
  ) {
    return `Cannot reach the API at ${url}. Make sure the backend server is running.`;
  }
  return msg;
}

const inputCls =
  "w-full rounded-lg border border-border bg-fog/60 px-3 py-2 text-sm text-white placeholder-muted focus:border-accent/40 outline-none transition-colors";
const textareaCls =
  "w-full rounded-lg border border-border bg-fog/60 px-3 py-2 text-sm text-white placeholder-muted focus:border-accent/40 outline-none transition-colors resize-none";
const labelCls = "block text-[10px] font-mono uppercase tracking-widest text-muted mb-1.5";

export default function OptimizePage() {
  const [system, setSystem] = useState("You are a helpful assistant.");
  const [template, setTemplate] = useState("{input}");
  const [model, setModel] = useState("llama3.1");
  const [judgeModel, setJudgeModel] = useState("llama3.1");
  const [iterations, setIterations] = useState(2);
  const [useRewriter, setUseRewriter] = useState(true);
  const [provider, setProvider] = useState("ollama");

  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<string[]>([]);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const progressEndRef = useRef<HTMLDivElement>(null);

  function scrollProgress() {
    progressEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }

  async function runOptimize() {
    setLoading(true);
    setError(null);
    setResult(null);
    setProgress([]);
    setCopied(false);

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
      const res = await fetch(`${API_URL}/optimize/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok || !res.body) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop()!;
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const event = JSON.parse(line.slice(6));
          if (event.type === "progress") {
            setProgress((prev) => [...prev, event.message]);
            scrollProgress();
          } else if (event.type === "done") {
            setResult({
              baseline_result: event.baseline_result,
              best_prompt: event.best_prompt,
              best_result: event.best_result,
              comparison: event.comparison,
            });
            setLoading(false);
          } else if (event.type === "error") {
            setError(event.message);
            setLoading(false);
          }
        }
      }
    } catch (e) {
      setError(apiError(e, API_URL));
      setLoading(false);
    }
  }

  function copySystem() {
    if (!result?.best_prompt?.system) return;
    navigator.clipboard.writeText(result.best_prompt.system).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <main className="min-h-screen">
      <div className="mx-auto max-w-4xl px-6 py-8">
        <header className="animate-fadeUp">
          <h1 className="text-2xl font-semibold tracking-tight">Prompt Optimizer</h1>
          <p className="text-muted text-sm mt-1">
            Generate 7–8 mutations, evaluate in parallel, pick the best.{" "}
            <kbd className="rounded bg-white/8 border border-white/10 px-1.5 py-0.5 text-[11px] font-mono text-muted">
              Run
            </kbd>{" "}
            to start streaming progress.
          </p>
        </header>

        <div className="mt-6 rounded-xl border border-border bg-card overflow-hidden">
          <div className="border-b border-border px-5 py-3">
            <span className="text-[10px] font-mono uppercase tracking-widest text-muted">Configuration</span>
          </div>
          <div className="p-5 space-y-5">
            <div>
              <label className={labelCls}>System Prompt</label>
              <textarea
                className={`${textareaCls} h-24`}
                value={system}
                onChange={(e) => setSystem(e.target.value)}
                placeholder="You are a helpful assistant."
              />
            </div>
            <div>
              <label className={labelCls}>Template</label>
              <textarea
                className={`${textareaCls} h-14 font-mono`}
                value={template}
                onChange={(e) => setTemplate(e.target.value)}
                placeholder="{input}"
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className={labelCls}>Model</label>
                <input className={inputCls} value={model} onChange={(e) => setModel(e.target.value)} />
              </div>
              <div>
                <label className={labelCls}>Judge Model</label>
                <input className={inputCls} value={judgeModel} onChange={(e) => setJudgeModel(e.target.value)} />
              </div>
              <div>
                <label className={labelCls}>Iterations (1–5)</label>
                <input
                  type="number"
                  min={1}
                  max={5}
                  className={inputCls}
                  value={iterations}
                  onChange={(e) => setIterations(Number(e.target.value))}
                />
              </div>
              <div>
                <label className={labelCls}>Provider</label>
                <select className={inputCls} value={provider} onChange={(e) => setProvider(e.target.value)}>
                  <option value="ollama">Ollama</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                </select>
              </div>
            </div>
            <label className="flex items-center gap-2.5 cursor-pointer text-sm text-muted select-none">
              <input
                type="checkbox"
                checked={useRewriter}
                onChange={(e) => setUseRewriter(e.target.checked)}
                className="rounded border-border"
              />
              Use LLM rewriter (adds one LLM-generated variant per iteration)
            </label>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={runOptimize}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-accent px-5 py-2.5 text-sm font-semibold text-black hover:bg-accent/90 disabled:opacity-50 transition-colors"
          >
            {loading ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Optimizing…
              </>
            ) : (
              "Run Optimizer"
            )}
          </button>
          {error && (
            <div className="flex items-center gap-2 text-sm text-danger">
              <span>{error}</span>
              <button onClick={runOptimize} className="underline text-danger/70 hover:text-danger text-xs">
                Retry
              </button>
            </div>
          )}
        </div>

        {/* Progress log */}
        {progress.length > 0 && (
          <div className="mt-5 rounded-xl border border-border bg-fog/40 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-border">
              <span className="text-[10px] font-mono uppercase tracking-widest text-muted">Progress log</span>
              {loading && (
                <span className="flex items-center gap-1.5 text-[10px] font-mono text-accent">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent animate-ping" />
                  running
                </span>
              )}
            </div>
            <div className="p-4 font-mono text-xs space-y-1.5 max-h-52 overflow-y-auto">
              {progress.map((msg, i) => (
                <div key={i} className="flex gap-3">
                  <span className="text-muted/40 select-none tabular-nums w-5 text-right shrink-0">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="text-muted">{msg}</span>
                </div>
              ))}
              {loading && (
                <div className="flex gap-3 text-muted/40 animate-pulse">
                  <span className="w-5 text-right">  </span>
                  <span>▊</span>
                </div>
              )}
              <div ref={progressEndRef} />
            </div>
          </div>
        )}

        {/* Best result */}
        {result && (
          <div className="mt-5 space-y-3 animate-fadeUp">
            <div className="text-[10px] font-mono uppercase tracking-widest text-muted">Best Result</div>

            <div className="rounded-xl border border-signal/25 bg-signal/5 overflow-hidden">
              <div className="px-5 py-3 border-b border-signal/15 flex items-center gap-4 flex-wrap">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono uppercase tracking-widest text-muted">Avg Objective</span>
                  <span className="font-mono text-accent font-semibold">
                    {Number(result.best_result?.avg_objective || 0).toFixed(4)}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono uppercase tracking-widest text-muted">Avg Judge Score</span>
                  <span className="font-mono text-white">
                    {Number(result.best_result?.avg_judge_score || 0).toFixed(4)}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono uppercase tracking-widest text-muted">Pass Rate</span>
                  <span className="font-mono text-white">
                    {result.best_result?.pass_rate != null
                      ? `${(Number(result.best_result.pass_rate) * 100).toFixed(0)}%`
                      : "—"}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono uppercase tracking-widest text-muted">Baseline</span>
                  <span className="font-mono text-white">
                    {result.baseline_result?.pass_rate != null
                      ? `${(Number(result.baseline_result.pass_rate) * 100).toFixed(0)}%`
                      : "—"}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono uppercase tracking-widest text-muted">Delta</span>
                  <span className="font-mono text-accent">
                    {result.comparison?.pass_rate_delta != null
                      ? `${Number(result.comparison.pass_rate_delta) >= 0 ? "+" : ""}${(
                          Number(result.comparison.pass_rate_delta) * 100
                        ).toFixed(0)}pp`
                      : "—"}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono uppercase tracking-widest text-muted">Variant</span>
                  <span className="font-mono text-accent text-xs">{result.best_prompt?.name}</span>
                </div>
              </div>

              <div className="p-5 space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className={labelCls}>System Prompt</span>
                    <button
                      onClick={copySystem}
                      className="flex items-center gap-1.5 text-[11px] font-mono text-muted hover:text-accent transition-colors"
                    >
                      {copied ? (
                        <>
                          <svg className="w-3.5 h-3.5 text-signal" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          <span className="text-signal">Copied</span>
                        </>
                      ) : (
                        <>
                          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                          Copy
                        </>
                      )}
                    </button>
                  </div>
                  <pre className="whitespace-pre-wrap text-sm bg-fog/60 rounded-lg p-4 leading-relaxed border border-border">
                    {result.best_prompt?.system}
                  </pre>
                </div>

                <div>
                  <span className={labelCls}>Template</span>
                  <pre className="whitespace-pre-wrap text-sm bg-fog/60 rounded-lg p-4 font-mono border border-border">
                    {result.best_prompt?.template}
                  </pre>
                </div>

                {result.best_result?.regression && (
                  <div className="flex items-center gap-2 rounded-lg border border-danger/30 bg-danger/5 px-4 py-3 text-sm text-danger">
                    <span>↓</span>
                    <span>{result.best_result.regression_warning}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
