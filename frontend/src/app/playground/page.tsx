"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type PromptPayload = {
  name: string;
  system: string;
  template: string;
  model: string;
  params: { temperature: number; max_tokens: number };
  context_limit: number;
  provider: string;
};

export default function Playground() {
  const [systemA, setSystemA] = useState("You are a helpful assistant.");
  const [templateA, setTemplateA] = useState("{input}");
  const [modelA, setModelA] = useState("llama3.1");
  const [providerA, setProviderA] = useState("ollama");

  const [enableB, setEnableB] = useState(false);
  const [systemB, setSystemB] = useState("You are a concise assistant.");
  const [templateB, setTemplateB] = useState("{input}");
  const [modelB, setModelB] = useState("llama3.1");

  const [judgeModel, setJudgeModel] = useState("llama3.1");
  const [input, setInput] = useState("Explain closures in one sentence.");
  const [rubric, setRubric] = useState("{\n  \"quality\": 1.0\n}");

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [results, setResults] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [showDiff, setShowDiff] = useState(false);
  const [advanced, setAdvanced] = useState(false);

  function diffTokens(a: string, b: string) {
    const at = a.split(/\s+/).filter(Boolean);
    const bt = b.split(/\s+/).filter(Boolean);
    const dp = Array(at.length + 1)
      .fill(0)
      .map(() => Array(bt.length + 1).fill(0));
    for (let i = 1; i <= at.length; i++) {
      for (let j = 1; j <= bt.length; j++) {
        dp[i][j] = at[i - 1] === bt[j - 1] ? dp[i - 1][j - 1] + 1 : Math.max(dp[i - 1][j], dp[i][j - 1]);
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
        provider: providerA,
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
    } catch (e: any) {
      setError(e.message || "Failed to reach API. Is the backend running?");
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
        `Run saved! ID: ${data.run_id} — avg score: ${Number(data.avg_judge_score || 0).toFixed(3)}`
      );
    } catch (e: any) {
      setError(e.message || "Failed to save run.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="min-h-screen bg-hero">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold">Prompt Playground</h1>
            <p className="text-muted mt-2">Test prompts without storing them.</p>
          </div>
        </header>

        <section className="grid gap-4 md:grid-cols-2 mt-6">
          <div className="rounded-2xl border border-border bg-card shadow-glow p-5">
            <div className="text-xs uppercase tracking-widest text-muted">Prompt</div>
            <textarea
              className="mt-2 w-full h-28 rounded-lg border border-border bg-black/40 p-3"
              value={systemA}
              onChange={(e) => setSystemA(e.target.value)}
              placeholder="System instructions"
            />
            <div className="text-xs uppercase tracking-widest text-muted mt-4">Template</div>
            <textarea
              className="mt-2 w-full h-20 rounded-lg border border-border bg-black/40 p-3"
              value={templateA}
              onChange={(e) => setTemplateA(e.target.value)}
              placeholder="Use {input}"
            />
            <div className="mt-3 flex gap-3">
              <label className="text-xs uppercase tracking-widest text-muted">
                Model
                <input
                  className="ml-2 rounded-lg border border-border bg-black/40 px-2 py-1 text-sm"
                  value={modelA}
                  onChange={(e) => setModelA(e.target.value)}
                />
              </label>
              <label className="text-xs uppercase tracking-widest text-muted">
                Provider
                <select
                  className="ml-2 rounded-lg border border-border bg-black/40 px-2 py-1 text-sm"
                  value={providerA}
                  onChange={(e) => setProviderA(e.target.value)}
                >
                  <option value="ollama">Ollama</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                </select>
              </label>
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-card shadow-glow p-5">
            <div className="text-xs uppercase tracking-widest text-muted">Input</div>
            <textarea
              className="mt-2 w-full h-44 rounded-lg border border-border bg-black/40 p-3"
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <div className="text-muted text-xs mt-2">
              Tip: add multiple lines to run multiple inputs (max 20).
            </div>
          </div>
        </section>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            onClick={runPreview}
            disabled={loading}
            className="inline-flex items-center justify-center rounded-lg bg-accent px-4 py-2 text-black font-semibold hover:bg-accent2 disabled:opacity-50"
          >
            {loading ? "Running..." : "Run Preview"}
          </button>
          <button
            onClick={saveRun}
            disabled={saving}
            className="inline-flex items-center justify-center rounded-lg border border-border bg-white/5 px-4 py-2 text-sm font-medium hover:bg-white/10 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Run"}
          </button>
          <label className="text-xs uppercase tracking-widest text-muted">
            <input
              className="mr-2"
              type="checkbox"
              checked={advanced}
              onChange={(e) => setAdvanced(e.target.checked)}
            />
            Advanced
          </label>
          {error && (
            <div className="flex items-center gap-2 text-sm text-red-400">
              {error}
              <button
                onClick={runPreview}
                className="underline text-red-300 hover:text-red-200"
              >
                Retry
              </button>
            </div>
          )}
          {saveMessage && <div className="text-sm text-emerald-400">{saveMessage}</div>}
        </div>

        {advanced && (
          <>
            <section className="grid gap-4 md:grid-cols-2 mt-4">
              <div className="rounded-2xl border border-border bg-card shadow-glow p-5">
                <div className="flex items-center justify-between">
                  <div className="text-xs uppercase tracking-widest text-muted">Prompt B (Optional)</div>
                  <label className="text-xs uppercase tracking-widest text-muted">
                    <input
                      className="mr-2"
                      type="checkbox"
                      checked={enableB}
                      onChange={(e) => setEnableB(e.target.checked)}
                    />
                    Enable
                  </label>
                </div>
                <textarea
                  className="mt-2 w-full h-28 rounded-lg border border-border bg-black/40 p-3"
                  value={systemB}
                  onChange={(e) => setSystemB(e.target.value)}
                  disabled={!enableB}
                />

                <div className="text-xs uppercase tracking-widest text-muted mt-4">Prompt B (Template)</div>
                <textarea
                  className="mt-2 w-full h-20 rounded-lg border border-border bg-black/40 p-3"
                  value={templateB}
                  onChange={(e) => setTemplateB(e.target.value)}
                  disabled={!enableB}
                />

                <label className="text-xs uppercase tracking-widest text-muted mt-4 block">
                  Prompt B Model
                  <input
                    className="mt-2 w-full rounded-lg border border-border bg-black/40 px-3 py-2"
                    value={modelB}
                    onChange={(e) => setModelB(e.target.value)}
                    disabled={!enableB}
                  />
                </label>
              </div>
              <div className="rounded-2xl border border-border bg-card shadow-glow p-5">
                <div className="text-xs uppercase tracking-widest text-muted">Judge + Rubric</div>
                <label className="text-xs uppercase tracking-widest text-muted mt-3 block">
                  Judge Model
                  <input
                    className="mt-2 w-full rounded-lg border border-border bg-black/40 px-3 py-2"
                    value={judgeModel}
                    onChange={(e) => setJudgeModel(e.target.value)}
                  />
                </label>
                <div className="text-xs uppercase tracking-widest text-muted mt-4">Rubric (JSON)</div>
                <textarea
                  className="mt-2 w-full h-32 rounded-lg border border-border bg-black/40 p-3 font-mono text-sm"
                  value={rubric}
                  onChange={(e) => setRubric(e.target.value)}
                />
              </div>
            </section>

            <div className="mt-4 flex items-center gap-3">
              <label className="text-xs uppercase tracking-widest text-muted">
                <input
                  className="mr-2"
                  type="checkbox"
                  checked={showDiff}
                  onChange={(e) => setShowDiff(e.target.checked)}
                />
                Show Diff
              </label>
            </div>
          </>
        )}

        <section className="mt-8">
          <div className="text-sm uppercase tracking-widest text-muted">Results</div>
          <div className="mt-3 grid gap-4">
            {results.length === 0 && (
              <div className="rounded-2xl border border-border bg-card shadow-glow p-5 text-muted">
                No results yet
              </div>
            )}

            {results.length > 0 && (() => {
              const promptNames = results.map((b: any, i: number) => b.prompt?.name || `Prompt ${i + 1}`);
              const maxInputs = Math.max(...results.map((b: any) => b.results.length));
              const canDiff = results.length === 2;

              return Array.from({ length: maxInputs }).map((_, inputIdx) => {
                const inputBlock = results[0]?.results?.[inputIdx];
                return (
                  <div key={inputIdx} className="rounded-2xl border border-border bg-card shadow-glow p-5">
                    <div className="text-xs uppercase tracking-widest text-muted">Input</div>
                    <pre className="mt-2 whitespace-pre-wrap text-sm">
                      {JSON.stringify(inputBlock?.input, null, 2)}
                    </pre>

                    <div className="mt-4 grid gap-4 md:grid-cols-2">
                      {results.map((block: any, pIdx: number) => {
                        const r = block.results?.[inputIdx];
                        return (
                          <div key={pIdx} className="rounded-xl border border-white/10 p-4">
                            <div className="text-xs uppercase tracking-widest text-muted">
                              {promptNames[pIdx]}
                            </div>
                            <div className="text-xs uppercase tracking-widest text-muted mt-3">Output</div>
                            <pre className="mt-2 whitespace-pre-wrap text-sm">{r?.output}</pre>
                            <div className="text-xs uppercase tracking-widest text-muted mt-4">Judge</div>
                            <div className="text-sm">
                              Score: {Number(r?.judge_score || 0).toFixed(4)}
                            </div>
                            {r?.judge_criteria && Object.keys(r.judge_criteria).length > 0 && (
                              <div className="mt-2 flex flex-wrap gap-1">
                                {Object.entries(r.judge_criteria).map(([k, v]: [string, any]) => (
                                  <span key={k} className="rounded-full bg-accent/10 px-2 py-0.5 text-xs text-accent">
                                    {k}: {Number(v).toFixed(2)}
                                  </span>
                                ))}
                              </div>
                            )}
                            <div className="text-muted text-sm mt-1">{r?.judge_reasoning}</div>
                          </div>
                        );
                      })}
                    </div>

                    {showDiff && canDiff && (
                      <div className="mt-4 rounded-xl border border-white/10 p-4">
                        <div className="text-xs uppercase tracking-widest text-muted">Diff (A → B)</div>
                        <div className="mt-2 text-sm leading-relaxed">
                          {diffTokens(
                            results[0]?.results?.[inputIdx]?.output || "",
                            results[1]?.results?.[inputIdx]?.output || ""
                          ).map((tok, tIdx) => {
                            if (tok.type === "add") {
                              return (
                                <span key={tIdx} className="bg-emerald-500/20 text-emerald-200 px-1 rounded">
                                  {tok.text}{" "}
                                </span>
                              );
                            }
                            if (tok.type === "del") {
                              return (
                                <span key={tIdx} className="bg-red-500/20 text-red-200 px-1 rounded line-through">
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
      </div>
    </main>
  );
}
