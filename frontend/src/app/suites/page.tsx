"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type Suite = {
  id: number;
  name: string;
  description?: string;
  case_count?: number;
  created_at?: string;
};

type SuiteCase = {
  id: number;
  suite_id: number;
  input: Record<string, any>;
  expected?: string;
  rubric?: Record<string, any>;
  order_idx?: number;
};

type RunResult = {
  run_id: number;
  avg_judge_score: number;
  avg_objective: number;
  regression: boolean;
};

const inputCls =
  "w-full rounded-lg border border-border bg-fog/60 px-3 py-2 text-sm text-white placeholder-muted focus:border-accent/40 outline-none transition-colors";
const textareaCls =
  "w-full rounded-lg border border-border bg-fog/60 px-3 py-2 text-sm text-white placeholder-muted focus:border-accent/40 outline-none transition-colors resize-none";
const labelCls = "block text-[10px] font-mono uppercase tracking-widest text-muted mb-1.5";

export default function SuitesPage() {
  const [suites, setSuites] = useState<Suite[]>([]);
  const [selectedSuite, setSelectedSuite] = useState<Suite | null>(null);
  const [cases, setCases] = useState<SuiteCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [creating, setCreating] = useState(false);

  const [caseInput, setCaseInput] = useState('{"input": ""}');
  const [caseExpected, setCaseExpected] = useState("");
  const [caseRubric, setCaseRubric] = useState('{"quality": 1.0}');
  const [addingCase, setAddingCase] = useState(false);
  const [caseError, setCaseError] = useState<string | null>(null);

  const [showRunPanel, setShowRunPanel] = useState(false);
  const [runSystem, setRunSystem] = useState("You are a helpful assistant.");
  const [runModel, setRunModel] = useState("llama3.1");
  const [runProvider, setRunProvider] = useState("ollama");
  const [runJudge, setRunJudge] = useState("llama3.1");
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<RunResult | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  async function loadSuites() {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/suites`);
      if (!res.ok) throw new Error("API error");
      const data = await res.json();
      setSuites(data.suites || []);
      setError(null);
    } catch {
      setError(`Failed to load suites. Make sure the API is running at ${API_URL}.`);
    } finally {
      setLoading(false);
    }
  }

  async function loadSuite(id: number) {
    try {
      const res = await fetch(`${API_URL}/suites/${id}`);
      if (!res.ok) throw new Error("not found");
      const data = await res.json();
      setSelectedSuite(data.suite);
      setCases(data.cases || []);
      setShowRunPanel(false);
      setRunResult(null);
      setRunError(null);
    } catch {
      setError("Failed to load suite.");
    }
  }

  async function createSuite() {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const res = await fetch(`${API_URL}/suites`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newName.trim(),
          description: newDesc.trim() || null,
          cases: [],
        }),
      });
      if (!res.ok) throw new Error("create failed");
      setNewName("");
      setNewDesc("");
      await loadSuites();
    } catch {
      setError("Failed to create suite.");
    } finally {
      setCreating(false);
    }
  }

  async function deleteSuite(id: number) {
    try {
      await fetch(`${API_URL}/suites/${id}`, { method: "DELETE" });
      if (selectedSuite?.id === id) {
        setSelectedSuite(null);
        setCases([]);
        setShowRunPanel(false);
        setRunResult(null);
      }
      await loadSuites();
    } catch {
      setError("Failed to delete suite.");
    }
  }

  async function addCase() {
    if (!selectedSuite) return;
    setCaseError(null);
    let inputObj: any;
    let rubricObj: any = null;
    try {
      inputObj = JSON.parse(caseInput);
    } catch {
      setCaseError("Input must be valid JSON");
      return;
    }
    try {
      if (caseRubric.trim()) rubricObj = JSON.parse(caseRubric);
    } catch {
      setCaseError("Rubric must be valid JSON");
      return;
    }
    setAddingCase(true);
    try {
      const res = await fetch(`${API_URL}/suites/${selectedSuite.id}/cases`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          input: inputObj,
          expected: caseExpected.trim() || null,
          rubric: rubricObj,
          order_idx: cases.length,
        }),
      });
      if (!res.ok) throw new Error("add failed");
      setCaseInput('{"input": ""}');
      setCaseExpected("");
      await loadSuite(selectedSuite.id);
      await loadSuites();
    } catch {
      setCaseError("Failed to add case.");
    } finally {
      setAddingCase(false);
    }
  }

  async function removeCase(caseId: number) {
    if (!selectedSuite) return;
    try {
      await fetch(`${API_URL}/suites/${selectedSuite.id}/cases/${caseId}`, {
        method: "DELETE",
      });
      await loadSuite(selectedSuite.id);
      await loadSuites();
    } catch {
      setError("Failed to remove case.");
    }
  }

  async function runSuite() {
    if (!selectedSuite) return;
    setRunning(true);
    setRunError(null);
    setRunResult(null);
    try {
      const res = await fetch(`${API_URL}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: {
            name: `suite_${selectedSuite.id}_run`,
            system: runSystem,
            template: "{input}",
            model: runModel,
            params: { temperature: 0.2, max_tokens: 200 },
            context_limit: 4096,
            provider: runProvider,
          },
          judge_model: runJudge,
          suite_id: selectedSuite.id,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setRunResult(data);
    } catch (e: any) {
      const msg: string = e?.message || "";
      if (msg.includes("Failed to fetch") || msg.includes("ERR_CONNECTION_REFUSED")) {
        setRunError(`Cannot reach the API at ${API_URL}. Is the backend running?`);
      } else {
        setRunError(msg || "Run failed.");
      }
    } finally {
      setRunning(false);
    }
  }

  useEffect(() => {
    loadSuites();
  }, []);

  return (
    <main className="min-h-screen">
      <div className="mx-auto max-w-6xl px-6 py-8">
        <header className="animate-fadeUp">
          <h1 className="text-2xl font-semibold tracking-tight">Test Suites</h1>
          <p className="text-muted text-sm mt-1">
            Persistent collections of test cases with expected outputs and rubrics.
          </p>
        </header>

        {error && (
          <div className="mt-4 flex items-center gap-3 rounded-lg border border-danger/25 bg-danger/5 px-4 py-2.5 text-sm text-danger">
            <span className="w-1.5 h-1.5 rounded-full bg-danger shrink-0" />
            {error}
          </div>
        )}

        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {/* Sidebar */}
          <div className="space-y-3">
            <div className="rounded-xl border border-border bg-card overflow-hidden">
              <div className="border-b border-border px-4 py-2.5">
                <span className="text-[10px] font-mono uppercase tracking-widest text-muted">
                  New Suite
                </span>
              </div>
              <div className="p-4 space-y-2">
                <input
                  className={inputCls}
                  placeholder="Suite name"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && createSuite()}
                />
                <input
                  className={inputCls}
                  placeholder="Description (optional)"
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                />
                <button
                  onClick={createSuite}
                  disabled={creating || !newName.trim()}
                  className="w-full rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-black hover:bg-accent/90 disabled:opacity-50 transition-colors"
                >
                  {creating ? "Creating…" : "Create Suite"}
                </button>
              </div>
            </div>

            <div className="rounded-xl border border-border bg-card overflow-hidden">
              <div className="border-b border-border px-4 py-2.5 flex items-center justify-between">
                <span className="text-[10px] font-mono uppercase tracking-widest text-muted">
                  Suites
                </span>
                <span className="text-[10px] font-mono text-muted/50">{suites.length}</span>
              </div>
              <div className="p-2">
                {loading && (
                  <div className="px-2 py-3 text-muted text-xs font-mono">Loading…</div>
                )}
                {!loading && suites.length === 0 && (
                  <div className="px-2 py-3 text-muted text-xs">
                    No suites yet. Create one above.
                  </div>
                )}
                {suites.map((s) => (
                  <div
                    key={s.id}
                    onClick={() => loadSuite(s.id)}
                    className={`flex items-center justify-between rounded-lg px-3 py-2.5 cursor-pointer text-sm transition-colors ${
                      selectedSuite?.id === s.id
                        ? "bg-accent/10 text-accent"
                        : "hover:bg-white/[0.04] text-white"
                    }`}
                  >
                    <div className="min-w-0">
                      <div className="font-medium text-inherit truncate">{s.name}</div>
                      <div className="text-[11px] font-mono text-muted/70 mt-0.5">
                        {s.case_count ?? 0} cases
                      </div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteSuite(s.id);
                      }}
                      className="ml-2 shrink-0 text-muted/50 hover:text-danger text-xs transition-colors px-1"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Main panel */}
          <div className="md:col-span-2 space-y-3">
            {!selectedSuite && (
              <div className="rounded-xl border border-border bg-card px-6 py-12 text-center">
                <div className="text-muted text-sm">Select a suite to view its cases.</div>
                {suites.length === 0 && (
                  <div className="text-muted/60 text-xs mt-1.5">
                    Create a suite first, then add test cases.
                  </div>
                )}
              </div>
            )}

            {selectedSuite && (
              <>
                {/* Suite header */}
                <div className="rounded-xl border border-border bg-card overflow-hidden">
                  <div className="flex items-center justify-between px-5 py-3.5">
                    <div className="min-w-0">
                      <div className="font-semibold text-white">{selectedSuite.name}</div>
                      {selectedSuite.description && (
                        <div className="text-muted text-xs mt-0.5">{selectedSuite.description}</div>
                      )}
                    </div>
                    <div className="flex items-center gap-3 shrink-0 ml-3">
                      <span className="text-[11px] font-mono text-muted/60">
                        {cases.length} {cases.length === 1 ? "case" : "cases"}
                      </span>
                      {cases.length > 0 && (
                        <button
                          onClick={() => {
                            setShowRunPanel((v) => !v);
                            setRunResult(null);
                            setRunError(null);
                          }}
                          className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors ${
                            showRunPanel
                              ? "bg-white/8 text-white border border-border"
                              : "bg-accent text-black hover:bg-accent/90"
                          }`}
                        >
                          {showRunPanel ? "Hide" : "Run Suite"}
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                {/* Run suite panel */}
                {showRunPanel && (
                  <div className="rounded-xl border border-accent/20 bg-card overflow-hidden animate-fadeIn">
                    <div className="border-b border-accent/15 px-4 py-2.5">
                      <span className="text-[10px] font-mono uppercase tracking-widest text-accent/70">
                        Run Against Prompt
                      </span>
                    </div>
                    <div className="p-4 space-y-3">
                      <div>
                        <label className={labelCls}>System Prompt</label>
                        <textarea
                          className={`${textareaCls} h-20`}
                          value={runSystem}
                          onChange={(e) => setRunSystem(e.target.value)}
                        />
                      </div>
                      <div className="grid grid-cols-3 gap-3">
                        <div>
                          <label className={labelCls}>Model</label>
                          <input className={inputCls} value={runModel} onChange={(e) => setRunModel(e.target.value)} />
                        </div>
                        <div>
                          <label className={labelCls}>Provider</label>
                          <select className={inputCls} value={runProvider} onChange={(e) => setRunProvider(e.target.value)}>
                            <option value="ollama">Ollama</option>
                            <option value="openai">OpenAI</option>
                            <option value="anthropic">Anthropic</option>
                          </select>
                        </div>
                        <div>
                          <label className={labelCls}>Judge Model</label>
                          <input className={inputCls} value={runJudge} onChange={(e) => setRunJudge(e.target.value)} />
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <button
                          onClick={runSuite}
                          disabled={running}
                          className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-black hover:bg-accent/90 disabled:opacity-50 transition-colors"
                        >
                          {running ? "Running…" : "Run Now"}
                        </button>
                        {runError && (
                          <span className="text-danger text-sm">{runError}</span>
                        )}
                      </div>
                      {runResult && (
                        <div className="rounded-lg border border-signal/25 bg-signal/5 p-4 space-y-1.5 text-sm">
                          <div className="text-signal font-semibold">Run complete</div>
                          <div className="font-mono text-xs text-muted">
                            Avg objective:{" "}
                            <span className="text-accent">
                              {Number(runResult.avg_objective || 0).toFixed(4)}
                            </span>
                            {" · "}
                            Avg judge:{" "}
                            <span className="text-white">
                              {Number(runResult.avg_judge_score || 0).toFixed(4)}
                            </span>
                          </div>
                          {runResult.regression && (
                            <div className="text-danger text-xs font-mono">↓ Regression detected</div>
                          )}
                          <Link
                            href={`/runs/${runResult.run_id}`}
                            className="text-accent hover:text-accent/80 text-xs underline underline-offset-2"
                          >
                            View run details →
                          </Link>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Add case form */}
                <div className="rounded-xl border border-border bg-card overflow-hidden">
                  <div className="border-b border-border px-4 py-2.5">
                    <span className="text-[10px] font-mono uppercase tracking-widest text-muted">
                      Add Test Case
                    </span>
                  </div>
                  <div className="p-4 space-y-3">
                    <div>
                      <label className={labelCls}>Input (JSON)</label>
                      <textarea
                        className={`${textareaCls} h-16 font-mono`}
                        value={caseInput}
                        onChange={(e) => setCaseInput(e.target.value)}
                      />
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <div>
                        <label className={labelCls}>Expected Output (optional)</label>
                        <textarea
                          className={`${textareaCls} h-16`}
                          value={caseExpected}
                          onChange={(e) => setCaseExpected(e.target.value)}
                        />
                      </div>
                      <div>
                        <label className={labelCls}>Rubric (JSON)</label>
                        <textarea
                          className={`${textareaCls} h-16 font-mono`}
                          value={caseRubric}
                          onChange={(e) => setCaseRubric(e.target.value)}
                        />
                      </div>
                    </div>
                    {caseError && (
                      <div className="text-danger text-sm">{caseError}</div>
                    )}
                    <button
                      onClick={addCase}
                      disabled={addingCase}
                      className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-black hover:bg-accent/90 disabled:opacity-50 transition-colors"
                    >
                      {addingCase ? "Adding…" : "Add Case"}
                    </button>
                  </div>
                </div>

                {/* Cases list */}
                {cases.length === 0 ? (
                  <div className="rounded-xl border border-border bg-card px-5 py-8 text-center text-muted text-sm">
                    No cases yet. Add your first test case above.
                  </div>
                ) : (
                  <div className="rounded-xl border border-border bg-card overflow-hidden">
                    <div className="border-b border-border px-4 py-2.5">
                      <span className="text-[10px] font-mono uppercase tracking-widest text-muted">
                        Cases ({cases.length})
                      </span>
                    </div>
                    <div className="divide-y divide-border/40">
                      {cases.map((c, i) => (
                        <div key={c.id} className="px-4 py-3 hover:bg-white/[0.02] transition-colors">
                          <div className="flex items-start justify-between gap-3">
                            <span className="text-[10px] font-mono text-muted/50 tabular-nums shrink-0 mt-0.5">
                              {String(i + 1).padStart(2, "0")}
                            </span>
                            <div className="flex-1 min-w-0 space-y-1.5 text-sm">
                              <div className="font-mono text-xs text-white/80 truncate">
                                {JSON.stringify(c.input)}
                              </div>
                              {c.expected && (
                                <div className="text-muted text-xs truncate">
                                  <span className="text-muted/50">expected: </span>
                                  {c.expected}
                                </div>
                              )}
                              {c.rubric && (
                                <div className="font-mono text-[11px] text-muted/60">
                                  {JSON.stringify(c.rubric)}
                                </div>
                              )}
                            </div>
                            <button
                              onClick={() => removeCase(c.id)}
                              className="shrink-0 text-muted/40 hover:text-danger text-xs transition-colors px-1"
                            >
                              ✕
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
