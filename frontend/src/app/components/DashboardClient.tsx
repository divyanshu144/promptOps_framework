"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

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

function AreaChart({
  points,
  color = "#f59e0b",
  secondaryPoints,
  secondaryColor = "#38bdf8",
}: {
  points: number[];
  color?: string;
  secondaryPoints?: number[];
  secondaryColor?: string;
}) {
  const W = 640;
  const H = 140;
  const pad = { x: 6, y: 10 };

  function buildPath(pts: number[]) {
    if (pts.length < 2) return { line: "", area: "" };
    const min = Math.min(...pts);
    const max = Math.max(...pts);
    const range = Math.max(max - min, 0.0001);
    const sx = (i: number) =>
      pad.x + (i * (W - pad.x * 2)) / Math.max(pts.length - 1, 1);
    const sy = (v: number) =>
      H - pad.y - ((v - min) * (H - pad.y * 2)) / range;
    const coords = pts.map((v, i) => `${sx(i).toFixed(1)},${sy(v).toFixed(1)}`);
    const line = coords.join(" ");
    const area = `M ${sx(0).toFixed(1)},${H} L ${coords.join(" L ")} L ${sx(
      pts.length - 1
    ).toFixed(1)},${H} Z`;
    return { line, area };
  }

  const primary = buildPath(points);
  const secondary = secondaryPoints ? buildPath(secondaryPoints) : null;

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="w-full h-full"
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id="grad-p" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.28" />
          <stop offset="100%" stopColor={color} stopOpacity="0.01" />
        </linearGradient>
        {secondary && (
          <linearGradient id="grad-s" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={secondaryColor} stopOpacity="0.16" />
            <stop offset="100%" stopColor={secondaryColor} stopOpacity="0" />
          </linearGradient>
        )}
      </defs>
      {primary.area && <path d={primary.area} fill="url(#grad-p)" />}
      {primary.line && (
        <polyline
          fill="none"
          stroke={color}
          strokeWidth="1.5"
          strokeLinejoin="round"
          strokeLinecap="round"
          points={primary.line}
        />
      )}
      {secondary?.area && (
        <path d={secondary.area} fill="url(#grad-s)" opacity="0.8" />
      )}
      {secondary?.line && (
        <polyline
          fill="none"
          stroke={secondaryColor}
          strokeWidth="1.5"
          strokeLinejoin="round"
          strokeLinecap="round"
          strokeDasharray="5 3"
          points={secondary.line}
          opacity="0.7"
        />
      )}
    </svg>
  );
}

function KpiCard({
  label,
  value,
  sub,
  highlight,
}: {
  label: string;
  value: string;
  sub?: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border bg-card relative overflow-hidden transition-colors duration-300 ${
        highlight ? "border-accent/20 hover:border-accent/35" : "border-border hover:border-white/12"
      }`}
    >
      <div
        className={`absolute inset-x-0 top-0 h-px ${
          highlight
            ? "bg-gradient-to-r from-transparent via-accent/60 to-transparent"
            : "bg-gradient-to-r from-transparent via-white/10 to-transparent"
        }`}
      />
      <div className="px-5 py-4">
        <div className="text-[10px] font-mono uppercase tracking-widest text-muted">{label}</div>
        <div
          className={`mt-2 text-3xl font-semibold font-mono tabular-nums tracking-tight ${
            highlight ? "text-accent" : "text-white"
          }`}
        >
          {value}
        </div>
        {sub && <div className="mt-0.5 text-[11px] font-mono text-muted/60">{sub}</div>}
      </div>
    </div>
  );
}

const selectCls =
  "w-full rounded-lg border border-border bg-fog/60 px-3 py-1.5 text-sm text-white placeholder-muted focus:border-accent/40 outline-none transition-colors font-display";

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

  const totalRuns = runs.length;
  const bestObjective = Math.max(0, ...runs.map((r) => Number(r.objective || 0)));
  const bestJudge = Math.max(0, ...runs.map((r) => Number(r.judge_score || 0)));
  const regressions = runs.filter((r) => r.regression === 1).length;

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

  const prompts = useMemo(
    () =>
      Array.from(
        new Set(runs.map((r) => r.prompt_name).filter(Boolean) as string[])
      ),
    [runs]
  );
  const models = useMemo(
    () =>
      Array.from(
        new Set(runs.map((r) => r.model).filter(Boolean) as string[])
      ),
    [runs]
  );

  const filtered = useMemo(
    () =>
      runs.filter((r) => {
        if (promptFilter && r.prompt_name !== promptFilter) return false;
        if (modelFilter && r.model !== modelFilter) return false;
        return true;
      }),
    [runs, promptFilter, modelFilter]
  );

  const primary = filtered.map((r) => Number(r[metric] || 0));
  const secondary = filtered.map((r) => Number(r.judge_score || 0));

  return (
    <>
      {apiError && (
        <div className="mt-4 flex items-center gap-3 rounded-lg border border-danger/25 bg-danger/5 px-4 py-2.5 text-sm text-danger">
          <span className="w-1.5 h-1.5 rounded-full bg-danger shrink-0" />
          API unavailable — showing cached data.{" "}
          <span className="font-mono text-xs text-danger/60">{apiUrl}</span>
        </div>
      )}

      {/* KPIs */}
      <section className="grid gap-2.5 grid-cols-2 md:grid-cols-4 mt-5">
        <KpiCard label="Total Runs" value={String(totalRuns)} />
        <KpiCard
          label="Best Objective"
          value={bestObjective > 0 ? bestObjective.toFixed(4) : "—"}
          sub="multi-metric"
          highlight
        />
        <KpiCard
          label="Best Judge Score"
          value={bestJudge > 0 ? bestJudge.toFixed(4) : "—"}
          sub="averaged 3×"
        />
        <KpiCard
          label="Regressions"
          value={String(regressions)}
          sub={regressions === 0 ? "all clear" : "needs review"}
        />
      </section>

      {/* Chart + Filters */}
      <section className="grid gap-2.5 md:grid-cols-3 mt-2.5">
        <div className="md:col-span-2 rounded-xl border border-border bg-card p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[10px] font-mono uppercase tracking-widest text-muted">
              {metric === "objective" ? "Objective" : "Judge Score"} trend
              {filtered.length > 0 && (
                <span className="ml-2 text-muted/50">{filtered.length} runs</span>
              )}
            </span>
            {compare && (
              <div className="flex items-center gap-4 text-[10px] font-mono text-muted">
                <span className="flex items-center gap-1.5">
                  <span className="inline-block w-4 h-0.5 bg-accent rounded-full" />
                  objective
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="inline-block w-4 border-t border-dashed border-accent2" />
                  judge
                </span>
              </div>
            )}
          </div>
          <div className="h-36 w-full">
            {primary.length >= 2 ? (
              <AreaChart
                points={primary}
                secondaryPoints={compare ? secondary : undefined}
              />
            ) : (
              <div className="h-full flex items-center justify-center text-muted text-xs font-mono">
                {primary.length === 1 ? "need ≥2 runs to draw trend" : "no data yet"}
              </div>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-4 space-y-3">
          <div className="text-[10px] font-mono uppercase tracking-widest text-muted">Filters</div>

          <div>
            <label className="block text-[11px] text-muted mb-1">Prompt</label>
            <select className={selectCls} value={promptFilter} onChange={(e) => setPromptFilter(e.target.value)}>
              <option value="">All prompts</option>
              {prompts.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-[11px] text-muted mb-1">Model</label>
            <select className={selectCls} value={modelFilter} onChange={(e) => setModelFilter(e.target.value)}>
              <option value="">All models</option>
              {models.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-[11px] text-muted mb-1">Chart metric</label>
            <select
              className={selectCls}
              value={metric}
              onChange={(e) => setMetric(e.target.value as "objective" | "judge_score")}
            >
              <option value="objective">Objective</option>
              <option value="judge_score">Judge Score</option>
            </select>
          </div>

          <label className="flex items-center gap-2 cursor-pointer text-[11px] text-muted select-none">
            <input
              type="checkbox"
              className="rounded border-border"
              checked={compare}
              onChange={(e) => setCompare(e.target.checked)}
            />
            Overlay judge score
          </label>

          <div className="pt-1 text-[10px] font-mono text-muted/40 truncate">{apiUrl}</div>
        </div>
      </section>

      {/* Recent Runs Table */}
      <section className="mt-2.5">
        <div className="text-[10px] font-mono uppercase tracking-widest text-muted mb-2">
          Recent Runs
          {filtered.length > 0 && (
            <span className="ml-2 text-muted/40">{Math.min(filtered.length, 50)} shown</span>
          )}
        </div>
        <div className="rounded-xl border border-border bg-card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                {["Prompt", "Model", "Objective", "Judge", "Created", ""].map((h, i) => (
                  <th
                    key={i}
                    className={`px-4 py-2.5 text-[10px] font-mono uppercase tracking-widest text-muted/70 ${
                      i >= 2 && i <= 3 ? "text-right" : i === 5 ? "text-right" : "text-left"
                    } ${i === 4 ? "hidden md:table-cell" : ""}`}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr>
                  <td className="px-4 py-8 text-center text-muted text-sm" colSpan={6}>
                    No runs yet.{" "}
                    <Link
                      href="/playground"
                      className="text-accent hover:text-accent/80 underline underline-offset-2"
                    >
                      Run your first prompt →
                    </Link>
                  </td>
                </tr>
              )}
              {[...filtered].reverse().slice(0, 50).map((r, idx) => (
                <tr
                  key={idx}
                  className="border-t border-border/30 hover:bg-white/[0.025] transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      {r.prompt_name ? (
                        <Link
                          href={`/prompts/${encodeURIComponent(r.prompt_name)}`}
                          className="text-white hover:text-accent transition-colors font-medium text-sm"
                        >
                          {r.prompt_name}
                        </Link>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                      {r.regression === 1 && (
                        <span className="inline-flex items-center gap-1 rounded bg-danger/10 border border-danger/20 px-1.5 py-0.5 text-[10px] text-danger font-mono">
                          ↓ regression
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-muted font-mono text-xs">{r.model ?? "—"}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums text-accent text-sm">
                    {Number(r.objective || 0).toFixed(4)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums text-muted text-sm">
                    {Number(r.judge_score || 0).toFixed(4)}
                  </td>
                  <td className="px-4 py-3 text-muted font-mono text-[11px] hidden md:table-cell">
                    {r.created_at ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {r.id ? (
                      <Link
                        className="text-[11px] font-mono text-muted/60 hover:text-accent transition-colors"
                        href={`/runs/${r.id}`}
                      >
                        #{r.id}
                      </Link>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
