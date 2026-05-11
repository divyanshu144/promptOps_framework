"use client";

import { useEffect, useRef, useState } from "react";

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
  if (msg.toLowerCase().includes("cors") || msg.toLowerCase().includes("blocked")) {
    return `Request blocked by CORS policy. Check the CORS_ORIGINS env var on the backend.`;
  }
  if (msg.startsWith("HTTP 5")) return `Server error (${msg}). Check the backend logs.`;
  return msg;
}

type PromptPayload = {
  name: string;
  system: string;
  template: string;
  model: string;
  params: { temperature: number; max_tokens: number };
  context_limit: number;
  provider: string;
};

const inputCls =
  "w-full rounded-lg border border-border bg-fog/60 px-3 py-2 text-sm text-white placeholder-muted focus:border-accent/40 outline-none transition-colors";
const textareaCls =
  "w-full rounded-lg border border-border bg-fog/60 px-3 py-2 text-sm text-white placeholder-muted focus:border-accent/40 outline-none transition-colors resize-none";
const labelCls = "block text-[10px] font-mono uppercase tracking-widest text-muted mb-1.5";
const sectionTitle = "text-[10px] font-mono uppercase tracking-widest text-muted";

export default function Playground() {
  const [systemA, setSystemA] = useState("You are a helpful assistant.");
  const [templateA, setTemplateA] = useState("{input}");
  const [modelA, setModelA] = useState("llama3.1");
  const [providerA, setProviderA] = useState("ollama");

  const [enableB, setEnableB] = useState(false);
  const [systemB, setSystemB] = useState("You are a concise assistant.");
  const [templateB, setTemplateB] = useState("{input}");
  const [modelB, setModelB] = useState("llama3.1");
  const [providerB, setProviderB] = useState("ollama");

  const [judgeModel, setJudgeModel] = useState("llama3.1");
  const [input, setInput] = useState("Explain closures in one sentence.");
  const [rubric, setRubric] = useState('{\n  "quality": 1.0\n}');

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [results, setResults] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [showDiff, setShowDiff] = useState(false);
  const [advanced, setAdvanced] = useState(false);

  const runPreviewRef = useRef<() => void>(() => {});
  useEffect(() => {
    runPreviewRef.current = () => {
      if (!loading) runPreview();
    };
  });
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        runPreviewRef.current();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  function diffTokens(a: string, b: string) {
    const at = a.split(/\s+/).filter(Boolean);
    const bt = b.split(/\s+/).filter(Boolean);
    const dp = Array(at.length + 1)
      .fill(0)
      .map(() => Array(bt.length + 1).fill(0));
    for (let i = 1; i <= at.length; i++) {
      for (let j = 1; j <= bt.length; j++) {
        dp[i][j] =
          at[i - 1] === bt[j - 1]
            ? dp[i - 1][j - 1] + 1
            : Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
    const out: { text: string; type: "same" | "add" | "del" }[] = [];
    let i = at.length;
    let j = bt.length;
    while (i > 0 || j > 0) {
      if (i > 0 && j > 0 && at[i - 1] === bt[j - 1]) {
        out.push({ text: at[i - 1], type: "same" });
        i--;
        j--;
      } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
        out.push({ text: bt[j - 1], type: "add" });
        j--;
      } else if (i > 0) {
        out.push({ text: at[i - 1], type: "del" });
        i--;
      }
    }
    return out.reverse();
  }

  async function runPreview() {
    setLoading(true);
    setError(null);
    setResults([]);
    setSaveMessage(null);

    let rubricObj: any = null;
    try {
      rubricObj = rubric.trim() ? JSON.parse(rubric) : null;
    } catch {
      setError("Rubric must be valid JSON");
      setLoading(false);
      return;
    }

    const prompts: PromptPayload[] = [
      {
        name: "prompt_A",
        system: systemA,
        template: templateA,
        model: modelA,
        params: { temperature: 0.2, max_tokens: 200 },
        context_limit: 4096,
        provider: providerA,
      },
    ];

    if (enableB) {
      prompts.push({
        name: "prompt_B",
        system: systemB,
        template: templateB,
        model: modelB,
        params: { temperature: 0.2, max_tokens: 200 },
        context_limit: 4096,
        provider: providerB,
      });
    }

    const body = {
      prompts,
      judge_model: judgeModel,
      inputs: input
        .split("\n")
        .map((x) => x.trim())
        .filter(Boolean),
      rubric: rubricObj,
    };

    try {
      const res = await fetch(`${API_URL}/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setResults(data.results || []);
    } catch (e) {
      setError(apiError(e, API_URL));
    } finally {
      setLoading(false);
    }
  }

  async function saveRun() {
    setSaving(true);
    setSaveMessage(null);
    setError(null);

    const body = {
      prompt: {
        name: "playground_run",
        system: systemA,
        template: templateA,
        model: modelA,
        params: { temperature: 0.2, max_tokens: 200 },
        context_limit: 4096,
        provider: providerA,
      },
      judge_model: judgeModel,
    };

    try {
      const res = await fetch(`${API_URL}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setSaveMessage(
        `Saved — run #${data.run_id}, avg score: ${Number(data.avg_judge_score || 0).toFixed(3)}`
      );
    } catch (e) {
      setError(apiError(e, API_URL));
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="min-h-screen">
      <div className="mx-auto max-w-6xl px-6 py-8">
        <header className="animate-fadeUp flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Playground</h1>
            <p className="text-muted text-sm mt-1">
              Test prompts without storing them.{" "}
              <kbd className="rounded bg-white/8 border border-white/10 px-1.5 py-0.5 text-[11px] font-mono text-muted">
                ⌘ Enter
              </kbd>{" "}
              to run.
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <label className="flex items-center gap-2 cursor-pointer text-xs text-muted select-none">
              <input
                type="checkbox"
                className="rounded border-border"
                checked={advanced}
                onChange={(e) => setAdvanced(e.target.checked)}
              />
              Advanced
            </label>
          </div>
        </header>

        {/* Main prompt editor */}
        <div className="mt-6 grid gap-3 md:grid-cols-2">
          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="border-b border-border px-4 py-2.5 flex items-center justify-between">
              <span className={sectionTitle}>Prompt A</span>
              <div className="flex items-center gap-3 text-xs">
                <select
                  className="rounded-md border border-border bg-fog/60 px-2 py-1 text-xs text-white outline-none focus:border-accent/40"
                  value={providerA}
                  onChange={(e) => setProviderA(e.target.value)}
                >
                  <option value="ollama">Ollama</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                </select>
                <input
                  className="w-32 rounded-md border border-border bg-fog/60 px-2 py-1 text-xs text-white outline-none focus:border-accent/40"
                  value={modelA}
                  onChange={(e) => setModelA(e.target.value)}
                  placeholder="model"
                />
              </div>
            </div>
            <div className="p-4 space-y-3">
              <div>
                <label className={labelCls}>System</label>
                <textarea
                  className={`${textareaCls} h-28`}
                  value={systemA}
                  onChange={(e) => setSystemA(e.target.value)}
                  placeholder="System instructions"
                />
              </div>
              <div>
                <label className={labelCls}>Template</label>
                <textarea
                  className={`${textareaCls} h-16 font-mono`}
                  value={templateA}
                  onChange={(e) => setTemplateA(e.target.value)}
                  placeholder="{input}"
                />
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="border-b border-border px-4 py-2.5">
              <span className={sectionTitle}>Input</span>
            </div>
            <div className="p-4">
              <textarea
                className={`${textareaCls} h-48`}
                value={input}
                onChange={(e) => setInput(e.target.value)}
              />
              <p className="mt-2 text-[11px] text-muted font-mono">
                One input per line · max 20
              </p>
            </div>
          </div>
        </div>

        {/* Action bar */}
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <button
            onClick={runPreview}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-black hover:bg-accent/90 disabled:opacity-50 transition-colors"
          >
            {loading ? (
              <>
                <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Running…
              </>
            ) : (
              "Run Preview"
            )}
          </button>
          <button
            onClick={saveRun}
            disabled={saving}
            className="inline-flex items-center rounded-lg border border-border bg-white/[0.04] px-4 py-2 text-sm font-medium text-white hover:bg-white/[0.07] disabled:opacity-50 transition-colors"
          >
            {saving ? "Saving…" : "Save Run"}
          </button>
          {error && (
            <div className="flex items-center gap-2 text-sm text-danger">
              <span>{error}</span>
              <button onClick={runPreview} className="underline text-danger/70 hover:text-danger text-xs">
                Retry
              </button>
            </div>
          )}
          {saveMessage && (
            <span className="text-sm text-signal font-mono">{saveMessage}</span>
          )}
        </div>

        {/* Advanced section */}
        {advanced && (
          <div className="mt-3 grid gap-3 md:grid-cols-2 animate-fadeIn">
            <div className="rounded-xl border border-border bg-card overflow-hidden">
              <div className="border-b border-border px-4 py-2.5 flex items-center justify-between">
                <span className={sectionTitle}>Prompt B</span>
                <label className="flex items-center gap-2 text-xs text-muted cursor-pointer select-none">
                  <input
                    type="checkbox"
                    className="rounded border-border"
                    checked={enableB}
                    onChange={(e) => setEnableB(e.target.checked)}
                  />
                  Enable
                </label>
              </div>
              <div className="p-4 space-y-3">
                <div className="flex items-center gap-2 mb-1">
                  <select
                    className="rounded-md border border-border bg-fog/60 px-2 py-1 text-xs text-white outline-none focus:border-accent/40 disabled:opacity-40"
                    value={providerB}
                    onChange={(e) => setProviderB(e.target.value)}
                    disabled={!enableB}
                  >
                    <option value="ollama">Ollama</option>
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic</option>
                  </select>
                  <input
                    className="w-32 rounded-md border border-border bg-fog/60 px-2 py-1 text-xs text-white outline-none focus:border-accent/40 disabled:opacity-40"
                    value={modelB}
                    onChange={(e) => setModelB(e.target.value)}
                    disabled={!enableB}
                    placeholder="model"
                  />
                </div>
                <div>
                  <label className={labelCls}>System</label>
                  <textarea
                    className={`${textareaCls} h-28 disabled:opacity-40`}
                    value={systemB}
                    onChange={(e) => setSystemB(e.target.value)}
                    disabled={!enableB}
                  />
                </div>
                <div>
                  <label className={labelCls}>Template</label>
                  <textarea
                    className={`${textareaCls} h-16 font-mono disabled:opacity-40`}
                    value={templateB}
                    onChange={(e) => setTemplateB(e.target.value)}
                    disabled={!enableB}
                  />
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-border bg-card overflow-hidden">
              <div className="border-b border-border px-4 py-2.5">
                <span className={sectionTitle}>Judge &amp; Rubric</span>
              </div>
              <div className="p-4 space-y-3">
                <div>
                  <label className={labelCls}>Judge Model</label>
                  <input className={inputCls} value={judgeModel} onChange={(e) => setJudgeModel(e.target.value)} />
                </div>
                <div>
                  <label className={labelCls}>Rubric (JSON)</label>
                  <textarea
                    className={`${textareaCls} h-32 font-mono`}
                    value={rubric}
                    onChange={(e) => setRubric(e.target.value)}
                  />
                </div>
                <label className="flex items-center gap-2 cursor-pointer text-xs text-muted select-none">
                  <input
                    type="checkbox"
                    className="rounded border-border"
                    checked={showDiff}
                    onChange={(e) => setShowDiff(e.target.checked)}
                  />
                  Show word-level diff (A → B)
                </label>
              </div>
            </div>
          </div>
        )}

        {/* Results */}
        {results.length > 0 && (
          <section className="mt-5 animate-fadeUp">
            <div className="text-[10px] font-mono uppercase tracking-widest text-muted mb-2">Results</div>
            <div className="space-y-3">
              {(() => {
                const promptNames = results.map(
                  (b: any, i: number) => b.prompt?.name || `Prompt ${i + 1}`
                );
                const maxInputs = Math.max(...results.map((b: any) => b.results.length));
                const canDiff = results.length === 2;

                return Array.from({ length: maxInputs }).map((_, inputIdx) => {
                  const inputBlock = results[0]?.results?.[inputIdx];
                  return (
                    <div
                      key={inputIdx}
                      className="rounded-xl border border-border bg-card overflow-hidden"
                    >
                      <div className="border-b border-border px-4 py-2.5 bg-fog/30">
                        <span className="text-[10px] font-mono uppercase tracking-widest text-muted mr-3">
                          Input {maxInputs > 1 ? `${inputIdx + 1}` : ""}
                        </span>
                        <span className="font-mono text-xs text-white/70">
                          {JSON.stringify(inputBlock?.input)}
                        </span>
                      </div>

                      <div className="p-4 grid gap-3 md:grid-cols-2">
                        {results.map((block: any, pIdx: number) => {
                          const r = block.results?.[inputIdx];
                          return (
                            <div
                              key={pIdx}
                              className="rounded-lg border border-border/60 bg-fog/30 overflow-hidden"
                            >
                              <div className="border-b border-border/40 px-3 py-2 flex items-center justify-between">
                                <span className="text-[10px] font-mono uppercase tracking-widest text-muted">
                                  {promptNames[pIdx]}
                                </span>
                                <span className="font-mono text-xs text-accent">
                                  {Number(r?.judge_score || 0).toFixed(4)}
                                </span>
                              </div>
                              <div className="p-3 space-y-2">
                                <pre className="whitespace-pre-wrap text-sm leading-relaxed text-white/90 font-display">
                                  {r?.output}
                                </pre>
                                {r?.judge_criteria &&
                                  Object.keys(r.judge_criteria).length > 0 && (
                                    <div className="flex flex-wrap gap-1.5 pt-1">
                                      {Object.entries(r.judge_criteria).map(
                                        ([k, v]: [string, any]) => (
                                          <span
                                            key={k}
                                            className="rounded bg-accent/8 border border-accent/15 px-2 py-0.5 text-[10px] font-mono text-accent"
                                          >
                                            {k}: {Number(v).toFixed(2)}
                                          </span>
                                        )
                                      )}
                                    </div>
                                  )}
                                {r?.judge_reasoning && (
                                  <p className="text-muted text-xs leading-relaxed">
                                    {r.judge_reasoning}
                                  </p>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      {showDiff && canDiff && (
                        <div className="border-t border-border px-4 py-3">
                          <div className="text-[10px] font-mono uppercase tracking-widest text-muted mb-2">
                            Diff (A → B)
                          </div>
                          <div className="text-sm leading-relaxed">
                            {diffTokens(
                              results[0]?.results?.[inputIdx]?.output || "",
                              results[1]?.results?.[inputIdx]?.output || ""
                            ).map((tok, tIdx) => {
                              if (tok.type === "add") {
                                return (
                                  <span
                                    key={tIdx}
                                    className="bg-signal/15 text-signal px-0.5 rounded-sm"
                                  >
                                    {tok.text}{" "}
                                  </span>
                                );
                              }
                              if (tok.type === "del") {
                                return (
                                  <span
                                    key={tIdx}
                                    className="bg-danger/15 text-danger px-0.5 rounded-sm line-through"
                                  >
                                    {tok.text}{" "}
                                  </span>
                                );
                              }
                              return <span key={tIdx}>{tok.text} </span>;
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                });
              })()}
            </div>
          </section>
        )}

        {results.length === 0 && !loading && (
          <div className="mt-5 rounded-xl border border-border bg-card px-6 py-10 text-center text-muted text-sm">
            Run a prompt above to see results here.
          </div>
        )}
      </div>
    </main>
  );
}
