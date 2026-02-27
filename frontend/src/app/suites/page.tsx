"use client";

import { useEffect, useState } from "react";

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

export default function SuitesPage() {
  const [suites, setSuites] = useState<Suite[]>([]);
  const [selectedSuite, setSelectedSuite] = useState<Suite | null>(null);
  const [cases, setCases] = useState<SuiteCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create form
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [creating, setCreating] = useState(false);

  // Add case form
  const [caseInput, setCaseInput] = useState('{"input": ""}');
  const [caseExpected, setCaseExpected] = useState("");
  const [caseRubric, setCaseRubric] = useState('{"quality": 1.0}');
  const [addingCase, setAddingCase] = useState(false);
  const [caseError, setCaseError] = useState<string | null>(null);

  async function loadSuites() {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/suites`);
      if (!res.ok) throw new Error("API error");
      const data = await res.json();
      setSuites(data.suites || []);
      setError(null);
    } catch {
      setError("Failed to load suites. Is the API running?");
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
        body: JSON.stringify({ name: newName.trim(), description: newDesc.trim() || null, cases: [] }),
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

  useEffect(() => {
    loadSuites();
  }, []);

  return (
    <main className="min-h-screen bg-hero">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <header>
          <h1 className="text-3xl font-semibold">Test Suites</h1>
          <p className="text-muted mt-2">Create and manage persistent test case collections.</p>
        </header>

        {error && (
          <div className="mt-4 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        <div className="mt-8 grid gap-6 md:grid-cols-3">
          {/* Sidebar: suite list + create */}
          <div className="space-y-4">
            <div className="rounded-2xl border border-border bg-card shadow-glow p-5">
              <div className="text-xs uppercase tracking-widest text-muted">Create Suite</div>
              <input
                className="mt-3 w-full rounded-lg border border-border bg-black/40 px-3 py-2 text-sm"
                placeholder="Suite name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
              <input
                className="mt-2 w-full rounded-lg border border-border bg-black/40 px-3 py-2 text-sm"
                placeholder="Description (optional)"
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
              />
              <button
                onClick={createSuite}
                disabled={creating || !newName.trim()}
                className="mt-3 w-full rounded-lg bg-accent px-4 py-2 text-black font-semibold text-sm hover:bg-accent2 disabled:opacity-50"
              >
                {creating ? "Creating…" : "Create"}
              </button>
            </div>

            <div className="rounded-2xl border border-border bg-card shadow-glow p-5">
              <div className="text-xs uppercase tracking-widest text-muted">
                Suites ({suites.length})
              </div>
              {loading && <div className="mt-3 text-muted text-sm">Loading…</div>}
              <div className="mt-3 space-y-2">
                {suites.map((s) => (
                  <div
                    key={s.id}
                    className={`flex items-center justify-between rounded-lg px-3 py-2 cursor-pointer text-sm transition-colors ${
                      selectedSuite?.id === s.id
                        ? "bg-accent/10 text-accent"
                        : "hover:bg-white/5 text-muted"
                    }`}
                    onClick={() => loadSuite(s.id)}
                  >
                    <div>
                      <div className="font-medium text-inherit">{s.name}</div>
                      <div className="text-xs">{s.case_count ?? 0} cases</div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteSuite(s.id);
                      }}
                      className="text-red-400 hover:text-red-300 text-xs px-2"
                    >
                      Delete
                    </button>
                  </div>
                ))}
                {!loading && suites.length === 0 && (
                  <div className="text-muted text-sm">No suites yet.</div>
                )}
              </div>
            </div>
          </div>

          {/* Main area: suite details + cases */}
          <div className="md:col-span-2 space-y-4">
            {!selectedSuite && (
              <div className="rounded-2xl border border-border bg-card shadow-glow p-8 text-center text-muted">
                Select a suite to view and edit its cases.
              </div>
            )}

            {selectedSuite && (
              <>
                <div className="rounded-2xl border border-border bg-card shadow-glow p-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-semibold">{selectedSuite.name}</div>
                      {selectedSuite.description && (
                        <div className="text-muted text-sm mt-1">{selectedSuite.description}</div>
                      )}
                    </div>
                    <div className="text-xs text-muted">{cases.length} cases</div>
                  </div>
                </div>

                {/* Add case form */}
                <div className="rounded-2xl border border-border bg-card shadow-glow p-5 space-y-3">
                  <div className="text-xs uppercase tracking-widest text-muted">Add Test Case</div>
                  <div>
                    <div className="text-xs text-muted mb-1">Input (JSON)</div>
                    <textarea
                      className="w-full h-20 rounded-lg border border-border bg-black/40 p-3 text-sm font-mono"
                      value={caseInput}
                      onChange={(e) => setCaseInput(e.target.value)}
                    />
                  </div>
                  <div>
                    <div className="text-xs text-muted mb-1">Expected Output (optional)</div>
                    <textarea
                      className="w-full h-16 rounded-lg border border-border bg-black/40 p-3 text-sm"
                      value={caseExpected}
                      onChange={(e) => setCaseExpected(e.target.value)}
                    />
                  </div>
                  <div>
                    <div className="text-xs text-muted mb-1">Rubric (JSON)</div>
                    <textarea
                      className="w-full h-16 rounded-lg border border-border bg-black/40 p-3 text-sm font-mono"
                      value={caseRubric}
                      onChange={(e) => setCaseRubric(e.target.value)}
                    />
                  </div>
                  {caseError && <div className="text-sm text-red-400">{caseError}</div>}
                  <button
                    onClick={addCase}
                    disabled={addingCase}
                    className="rounded-lg bg-accent px-4 py-2 text-black font-semibold text-sm hover:bg-accent2 disabled:opacity-50"
                  >
                    {addingCase ? "Adding…" : "Add Case"}
                  </button>
                </div>

                {/* Cases list */}
                <div className="space-y-3">
                  {cases.length === 0 && (
                    <div className="rounded-2xl border border-border bg-card shadow-glow p-5 text-center text-muted text-sm">
                      No cases yet.
                    </div>
                  )}
                  {cases.map((c, i) => (
                    <div key={c.id} className="rounded-2xl border border-border bg-card shadow-glow p-5">
                      <div className="flex items-start justify-between">
                        <div className="text-xs uppercase tracking-widest text-muted">Case #{i + 1}</div>
                        <button
                          onClick={() => removeCase(c.id)}
                          className="text-red-400 hover:text-red-300 text-xs"
                        >
                          Remove
                        </button>
                      </div>
                      <div className="mt-3 space-y-2 text-sm">
                        <div>
                          <span className="text-muted text-xs">Input: </span>
                          <span className="font-mono">{JSON.stringify(c.input)}</span>
                        </div>
                        {c.expected && (
                          <div>
                            <span className="text-muted text-xs">Expected: </span>
                            <span>{c.expected}</span>
                          </div>
                        )}
                        {c.rubric && (
                          <div>
                            <span className="text-muted text-xs">Rubric: </span>
                            <span className="font-mono">{JSON.stringify(c.rubric)}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
