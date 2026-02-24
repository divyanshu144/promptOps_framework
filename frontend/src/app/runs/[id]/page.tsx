const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function fetchRun(id: string) {
  const res = await fetch(`${API_URL}/runs/${id}`, { cache: "no-store" });
  return res.json();
}

export default async function RunDetail({
  params,
}: {
  params: { id: string };
}) {
  const data = await fetchRun(params.id);
  const run = data.run;

  if (!run) {
    return (
      <main className="min-h-screen bg-hero">
        <div className="mx-auto max-w-4xl px-6 py-10">
          <h1 className="text-2xl font-semibold">Run not found</h1>
          <p className="text-muted mt-2">ID: {params.id}</p>
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
              href={`http://localhost:5000/#/experiments/0/runs/${run.run_id}`}
              target="_blank"
            >
              View in MLflow
            </a>
          </div>
        )}
      </div>
    </main>
  );
}
