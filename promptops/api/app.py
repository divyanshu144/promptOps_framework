from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from promptops.core.adapter import OllamaAdapter
from promptops.core.prompt import Prompt
from promptops.core.runner import run_dataset, run_prompt_detailed
from promptops.opt.optimizer import optimize_prompt
from promptops.tests.dataset import demo_dataset
from promptops.tests.testcase import TestCase
from promptops.store.db import top_runs, recent_runs, init_db, get_run

app = FastAPI(title="PromptOps")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


class PromptPayload(BaseModel):
    name: str = "demo_prompt"
    system: str = "You are a helpful assistant."
    template: str = "{input}"
    model: str = "llama3.1"
    params: dict[str, Any] = Field(default_factory=lambda: {"temperature": 0.2, "max_tokens": 200})
    context_limit: int = 4096
    output_format: str | None = None
    output_schema: dict[str, Any] | None = None


class RunRequest(BaseModel):
    prompt: PromptPayload
    judge_model: str = "llama3.1"


class PreviewRequest(BaseModel):
    prompt: PromptPayload | None = None
    prompts: list[PromptPayload] | None = None
    judge_model: str = "llama3.1"
    inputs: list[str] | None = None
    rubric: dict[str, Any] | None = None


class OptimizeRequest(BaseModel):
    prompt: PromptPayload
    judge_model: str = "llama3.1"
    iterations: int = 2
    use_rewriter: bool = True
    rewriter_model: str | None = None


@app.get("/")
def root() -> dict[str, Any]:
    return {"status": "ok"}


@app.post("/run")
async def run(req: RunRequest) -> dict[str, Any]:
    adapter = OllamaAdapter()
    prompt = Prompt(**req.prompt.model_dump())
    results = await run_dataset(adapter, prompt, demo_dataset(), req.judge_model)
    return results


@app.post("/preview")
async def preview(req: PreviewRequest) -> dict[str, Any]:
    adapter = OllamaAdapter()
    prompt_payloads = req.prompts or ([req.prompt] if req.prompt else [])
    prompts = [Prompt(**p.model_dump()) for p in prompt_payloads]

    if req.inputs:
        testcases = [TestCase(input={"input": text}, rubric=req.rubric) for text in req.inputs]
    else:
        testcases = demo_dataset()

    all_results = []
    for prompt in prompts:
        prompt_results = []
        for tc in testcases:
            prompt_results.append(
                await run_prompt_detailed(adapter, prompt, tc, req.judge_model)
            )
        all_results.append({"prompt": prompt.model_dump(), "results": prompt_results})

    return {"results": all_results}


@app.post("/optimize")
async def optimize(req: OptimizeRequest) -> dict[str, Any]:
    adapter = OllamaAdapter()
    prompt = Prompt(**req.prompt.model_dump())
    results = await optimize_prompt(
        adapter=adapter,
        base_prompt=prompt,
        testcases=demo_dataset(),
        judge_model=req.judge_model,
        iterations=req.iterations,
        use_rewriter=req.use_rewriter,
        rewriter_model=req.rewriter_model,
    )
    return {
        "best_prompt": results["best_prompt"].model_dump(),
        "best_result": results["best_result"],
    }


@app.get("/leaderboard")
def leaderboard() -> dict[str, Any]:
    return {"runs": top_runs(10)}


@app.get("/runs")
def runs(limit: int = 200) -> dict[str, Any]:
    return {"runs": recent_runs(limit)}


@app.get("/runs/{run_id}")
def run_detail(run_id: int) -> dict[str, Any]:
    run = get_run(run_id)
    if not run:
        return {"error": "not_found"}
    return {"run": run}


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    runs = top_runs(10)
    recent = list(reversed(recent_runs(200)))

    mlflow_ui = __import__("os").getenv("MLFLOW_UI_URL", "http://localhost:5000")
    runs_json = __import__("json").dumps(recent)

    total_runs = len(recent)
    best_objective = max((r.get("objective") or 0.0) for r in recent) if recent else 0.0
    best_judge = max((r.get("judge_score") or 0.0) for r in recent) if recent else 0.0

    rows = []
    for r in runs:
        run_link = ""
        if r.get("run_id"):
            run_link = (
                f"<a href='{mlflow_ui}/#/experiments/0/runs/{r['run_id']}' "
                "target='_blank'>view</a>"
            )
        rows.append(
            f"<tr><td>{r['prompt_name']}</td><td>{r['model']}</td>"
            f"<td>{r['objective']:.4f}</td><td>{r['judge_score']:.4f}</td>"
            f"<td>{r['created_at']}</td><td>{run_link}</td></tr>"
        )
    table = "\n".join(rows) if rows else "<tr><td colspan='6'>No runs yet</td></tr>"

    html = f"""
    <!doctype html>
    <html>
      <head>
        <meta charset='utf-8'/>
        <title>PromptOps Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
          :root {{
            --bg: #0b0e14;
            --bg-2: #0f1a22;
            --card: rgba(255, 255, 255, 0.06);
            --border: rgba(255, 255, 255, 0.12);
            --text: #e8eef4;
            --muted: #a8b3c1;
            --accent: #4de3c2;
            --accent-2: #5aa7ff;
            --warning: #ffb454;
          }}
          * {{ box-sizing: border-box; }}
          body {{
            font-family: 'Space Grotesk', system-ui, sans-serif;
            color: var(--text);
            margin: 0;
            padding: 32px;
            background:
              radial-gradient(1200px 600px at 10% -10%, rgba(90,167,255,0.25), transparent 60%),
              radial-gradient(900px 600px at 110% 10%, rgba(77,227,194,0.18), transparent 60%),
              linear-gradient(180deg, var(--bg), var(--bg-2));
          }}
          .shell {{ max-width: 1200px; margin: 0 auto; }}
          h1 {{
            margin: 0 0 8px 0;
            font-size: 32px;
            letter-spacing: 0.2px;
          }}
          .sub {{
            color: var(--muted);
            margin-bottom: 24px;
          }}
          .grid {{ display: grid; grid-template-columns: 1.2fr 1fr; gap: 18px; }}
          .kpis {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 18px; }}
          .card {{
            border: 1px solid var(--border);
            background: var(--card);
            padding: 16px;
            border-radius: 14px;
            backdrop-filter: blur(8px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.25);
          }}
          .kpi-title {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }}
          .kpi-value {{ font-size: 24px; font-weight: 700; }}
          .filters {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }}
          label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px; }}
          select, input[type="checkbox"] {{
            margin-left: 6px;
            padding: 6px 10px;
            background: #0b1218;
            border: 1px solid var(--border);
            color: var(--text);
            border-radius: 8px;
          }}
          a {{ color: var(--accent); text-decoration: none; }}
          a:hover {{ color: var(--accent-2); }}
          table {{
            border-collapse: collapse;
            width: 100%;
            background: rgba(0,0,0,0.15);
            border-radius: 12px;
            overflow: hidden;
          }}
          th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.08); }}
          th {{ color: var(--muted); font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px; }}
          tr:hover td {{ background: rgba(255,255,255,0.04); }}
          canvas {{ width: 100%; height: 240px; }}
          .section-title {{ margin: 20px 0 10px; font-weight: 600; }}
          .mono {{ font-family: 'JetBrains Mono', ui-monospace, monospace; }}
          .badge {{
            display: inline-flex; align-items: center; gap: 6px;
            padding: 4px 8px; border-radius: 999px;
            background: rgba(77,227,194,0.12); color: var(--accent);
            font-size: 12px;
          }}
          .animate {{ animation: fadeUp 700ms ease-out both; }}
          .delay-1 {{ animation-delay: 80ms; }}
          .delay-2 {{ animation-delay: 160ms; }}
          .delay-3 {{ animation-delay: 240ms; }}
          @keyframes fadeUp {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
          }}
          @media (max-width: 900px) {{
            .grid {{ grid-template-columns: 1fr; }}
            .kpis {{ grid-template-columns: 1fr; }}
            body {{ padding: 20px; }}
          }}
        </style>
      </head>
      <body>
        <div class="shell">
        <h1 class="animate">PromptOps Dashboard</h1>
        <div class="sub animate delay-1">Prompt-as-code performance, optimization, and model quality insights</div>
        <div class="kpis">
          <div class="card animate delay-1">
            <div class="kpi-title">Total Runs</div>
            <div class="kpi-value mono">{total_runs}</div>
          </div>
          <div class="card animate delay-2">
            <div class="kpi-title">Best Objective</div>
            <div class="kpi-value mono">{best_objective:.4f}</div>
          </div>
          <div class="card animate delay-3">
            <div class="kpi-title">Best Judge Score</div>
            <div class="kpi-value mono">{best_judge:.4f}</div>
          </div>
        </div>
        <div class="grid">
          <div class="card animate delay-1">
            <div class="badge">Trend</div>
            <h3>Metric Trend</h3>
            <canvas id="trend"></canvas>
          </div>
          <div class="card animate delay-2">
            <div class="badge">Controls</div>
            <h3>Quick Links</h3>
            <p class="mono">MLflow UI: <a href="{mlflow_ui}" target="_blank">{mlflow_ui}</a></p>
            <div class="filters">
              <label>Prompt
                <select id="promptFilter"></select>
              </label>
              <label>Model
                <select id="modelFilter"></select>
              </label>
              <label>Metric
                <select id="metricFilter">
                  <option value="objective">Objective</option>
                  <option value="judge_score">Judge Score</option>
                </select>
              </label>
              <label>
                <input type="checkbox" id="compareToggle" />
                Compare Judge
              </label>
            </div>
          </div>
        </div>
        <div class="section-title">Top runs by objective score</div>
        <table>
          <thead>
            <tr>
              <th>Prompt</th>
              <th>Model</th>
              <th>Objective</th>
              <th>Judge Score</th>
              <th>Created At</th>
              <th>MLflow</th>
            </tr>
          </thead>
          <tbody>
            {table}
          </tbody>
        </table>
        <div class="section-title">Recent runs (filtered)</div>
        <table>
          <thead>
            <tr>
              <th>Prompt</th>
              <th>Model</th>
              <th>Objective</th>
              <th>Judge Score</th>
              <th>Created At</th>
            </tr>
          </thead>
          <tbody id="recentRows"></tbody>
        </table>
        <script>
          const runs = {runs_json};
          const promptFilter = document.getElementById('promptFilter');
          const modelFilter = document.getElementById('modelFilter');
          const metricFilter = document.getElementById('metricFilter');
          const compareToggle = document.getElementById('compareToggle');
          const recentRows = document.getElementById('recentRows');

          function unique(list, key) {{
            const set = new Set();
            list.forEach(r => {{ if (r[key]) set.add(r[key]); }});
            return Array.from(set).sort();
          }}

          function fillSelect(select, values) {{
            select.innerHTML = '';
            const optAll = document.createElement('option');
            optAll.value = '';
            optAll.textContent = 'All';
            select.appendChild(optAll);
            values.forEach(v => {{
              const opt = document.createElement('option');
              opt.value = v;
              opt.textContent = v;
              select.appendChild(opt);
            }});
          }}

          fillSelect(promptFilter, unique(runs, 'prompt_name'));
          fillSelect(modelFilter, unique(runs, 'model'));

          function filterRuns() {{
            const p = promptFilter.value;
            const m = modelFilter.value;
            return runs.filter(r =>
              (!p || r.prompt_name === p) && (!m || r.model === m)
            );
          }}

          function drawChart(primary, secondary) {{
            const canvas = document.getElementById('trend');
            const ctx = canvas.getContext('2d');
            const width = canvas.width = canvas.clientWidth;
            const height = canvas.height = 240;
            ctx.clearRect(0, 0, width, height);
            if (primary.length === 0) return;

            const all = secondary ? primary.concat(secondary) : primary;
            const xs = all.map(p => p.x);
            const ys = all.map(p => p.y);
            const minY = Math.min(...ys);
            const maxY = Math.max(...ys);
            const pad = 20;
            const scaleX = (x) => pad + (x - xs[0]) * (width - 2 * pad) / (xs[xs.length - 1] - xs[0] || 1);
            const scaleY = (y) => height - pad - ((y - minY) * (height - 2 * pad) / ((maxY - minY) || 1));

            function draw(points, color) {{
              ctx.strokeStyle = color;
              ctx.lineWidth = 2;
              ctx.beginPath();
              points.forEach((p, i) => {{
                const x = scaleX(p.x);
                const y = scaleY(p.y);
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
              }});
              ctx.stroke();
              ctx.fillStyle = color;
              points.forEach(p => {{
                const x = scaleX(p.x);
                const y = scaleY(p.y);
                ctx.beginPath();
                ctx.arc(x, y, 3, 0, Math.PI * 2);
                ctx.fill();
              }});
            }}

            draw(primary, '#4de3c2');
            if (secondary) draw(secondary, '#5aa7ff');
          }}

          function renderTable(list) {{
            if (list.length === 0) {{
              recentRows.innerHTML = "<tr><td colspan='5'>No runs</td></tr>";
              return;
            }}
            recentRows.innerHTML = list.map(r => {{
              const title = "run_id=" + (r.run_id || "") + " prompt_hash=" + (r.prompt_hash || "");
              return "<tr title=\"" + title + "\"><td>" + r.prompt_name + "</td><td>" + r.model + "</td>" +
                     "<td>" + Number(r.objective || 0).toFixed(4) + "</td>" +
                     "<td>" + Number(r.judge_score || 0).toFixed(4) + "</td>" +
                     "<td>" + r.created_at + "</td></tr>";
            }}).join('');
          }}

          function render() {{
            const metric = metricFilter.value;
            const filtered = filterRuns();
            const data = filtered.map((r, i) => ({{
              x: i + 1,
              y: Number(r[metric] || 0)
            }}));
            const compare = compareToggle.checked
              ? filtered.map((r, i) => ({{ x: i + 1, y: Number(r.judge_score || 0) }}))
              : null;
            drawChart(data, compare);
            renderTable(filtered.slice(-50));
          }}

          promptFilter.addEventListener('change', render);
          modelFilter.addEventListener('change', render);
          metricFilter.addEventListener('change', render);
          compareToggle.addEventListener('change', render);

          render();
        </script>
        </div>
      </body>
    </html>
    """
    return html
