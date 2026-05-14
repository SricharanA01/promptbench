import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="LLM Benchmark API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory store (replace with Postgres in prod) ──────────────────────────
# Structure: list of run dicts, each with scored_results
RUNS: list[dict] = []
LATEST_RUN: Optional[dict] = None


def load_sample_data():
    """Load sample data so the frontend has something to show immediately."""
    global RUNS, LATEST_RUN
    sample_path = Path(__file__).parent / "sample_data.json"
    if sample_path.exists():
        with open(sample_path) as f:
            RUNS = json.load(f)
            LATEST_RUN = RUNS[-1] if RUNS else None


load_sample_data()


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_leaderboard_from_run(run: dict) -> list[dict]:
    results = run.get("scored_results", [])
    model_data = defaultdict(lambda: {
        "scores": [], "latencies": [], "costs": [],
        "categories": defaultdict(list), "failures": defaultdict(int)
    })
    for r in results:
        m = r["model"]
        model_data[m]["scores"].append(r.get("score", 0))
        model_data[m]["latencies"].append(r.get("latency_ms", 0))
        model_data[m]["costs"].append(r.get("cost_usd", 0))
        model_data[m]["categories"][r.get("task_category", "unknown")].append(r.get("score", 0))
        if r.get("failure_category"):
            model_data[m]["failures"][r["failure_category"]] += 1

    leaderboard = []
    for model, data in model_data.items():
        scores = data["scores"]
        latencies = [l for l in data["latencies"] if l > 0]
        costs = data["costs"]
        cat_scores = {
            cat: round(sum(s) / len(s), 1)
            for cat, s in data["categories"].items()
        }
        leaderboard.append({
            "model": model,
            "overall_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "category_scores": cat_scores,
            "median_latency_ms": sorted(latencies)[len(latencies) // 2] if latencies else 0,
            "avg_cost_per_task_usd": round(sum(costs) / len(costs), 6) if costs else 0,
            "total_cost_usd": round(sum(costs), 4),
            "failure_breakdown": dict(data["failures"]),
            "tasks_completed": len(scores),
        })

    return sorted(leaderboard, key=lambda x: x["overall_score"], reverse=True)


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "runs": len(RUNS)}


@app.get("/leaderboard")
def leaderboard(run_id: Optional[str] = None):
    """Current leaderboard — overall scores + per-category breakdown."""
    if not RUNS:
        return {"leaderboard": [], "run_id": None, "timestamp": None}

    run = LATEST_RUN
    if run_id:
        run = next((r for r in RUNS if r["run_id"] == run_id), None)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

    return {
        "leaderboard": get_leaderboard_from_run(run),
        "run_id": run["run_id"],
        "timestamp": run["timestamp"],
    }


@app.get("/models")
def list_models():
    """All models that have been benchmarked."""
    if not RUNS:
        return {"models": []}
    all_models = set()
    for run in RUNS:
        for r in run.get("scored_results", []):
            all_models.add(r["model"])
    return {"models": sorted(all_models)}


@app.get("/models/{model_id}/history")
def model_history(model_id: str):
    """Weekly score trend for a single model — used for the drift chart."""
    history = []
    for run in RUNS:
        results = [r for r in run.get("scored_results", []) if r["model"] == model_id]
        if not results:
            continue
        scores = [r.get("score", 0) for r in results]
        category_scores = defaultdict(list)
        for r in results:
            category_scores[r.get("task_category", "unknown")].append(r.get("score", 0))

        history.append({
            "run_id": run["run_id"],
            "timestamp": run["timestamp"],
            "overall_score": round(sum(scores) / len(scores), 1),
            "category_scores": {
                cat: round(sum(s) / len(s), 1)
                for cat, s in category_scores.items()
            },
            "median_latency_ms": sorted([r.get("latency_ms", 0) for r in results])[len(results) // 2],
        })

    return {"model": model_id, "history": history}


@app.get("/categories/{category}/scores")
def category_scores(category: str):
    """All model scores for a specific task category."""
    if not LATEST_RUN:
        return {"category": category, "scores": []}

    results = [
        r for r in LATEST_RUN.get("scored_results", [])
        if r.get("task_category") == category
    ]

    model_scores = defaultdict(list)
    for r in results:
        model_scores[r["model"]].append(r.get("score", 0))

    return {
        "category": category,
        "run_id": LATEST_RUN["run_id"],
        "scores": [
            {"model": m, "avg_score": round(sum(s) / len(s), 1), "task_count": len(s)}
            for m, s in model_scores.items()
        ]
    }


@app.get("/runs/latest/failures")
def latest_failures():
    """Failure breakdown from the most recent run — used for donut charts."""
    if not LATEST_RUN:
        return {"failures": {}}

    results = LATEST_RUN.get("scored_results", [])
    model_failures = defaultdict(lambda: defaultdict(int))
    for r in results:
        if r.get("failure_category"):
            model_failures[r["model"]][r["failure_category"]] += 1

    return {
        "run_id": LATEST_RUN["run_id"],
        "failures": {
            model: dict(cats)
            for model, cats in model_failures.items()
        }
    }


@app.get("/compare")
def compare_models(m1: str, m2: str):
    """Head-to-head: every task where m1 and m2 diverge significantly."""
    if not LATEST_RUN:
        return {"tasks": []}

    results = LATEST_RUN.get("scored_results", [])
    m1_results = {r["task_id"]: r for r in results if r["model"] == m1}
    m2_results = {r["task_id"]: r for r in results if r["model"] == m2}

    comparisons = []
    for task_id, r1 in m1_results.items():
        r2 = m2_results.get(task_id)
        if not r2:
            continue
        diff = abs(r1.get("score", 0) - r2.get("score", 0))
        comparisons.append({
            "task_id": task_id,
            "category": r1.get("task_category"),
            "difficulty": r1.get("task_difficulty"),
            f"{m1}_score": r1.get("score", 0),
            f"{m2}_score": r2.get("score", 0),
            f"{m1}_response": r1.get("response", ""),
            f"{m2}_response": r2.get("response", ""),
            "score_diff": diff,
            "winner": m1 if r1.get("score", 0) > r2.get("score", 0) else (m2 if r2.get("score", 0) > r1.get("score", 0) else "tie"),
        })

    comparisons.sort(key=lambda x: x["score_diff"], reverse=True)
    return {
        "m1": m1, "m2": m2,
        "run_id": LATEST_RUN["run_id"],
        "tasks": comparisons,
        "summary": {
            m1: sum(1 for c in comparisons if c["winner"] == m1),
            m2: sum(1 for c in comparisons if c["winner"] == m2),
            "ties": sum(1 for c in comparisons if c["winner"] == "tie"),
        }
    }


@app.get("/runs")
def list_runs():
    """All benchmark runs — used for the timeline."""
    return {
        "runs": [
            {
                "run_id": r["run_id"],
                "timestamp": r["timestamp"],
                "task_count": r.get("task_count", 0),
                "models": r.get("models", []),
            }
            for r in RUNS
        ]
    }


@app.get("/tasks")
def list_tasks():
    """All tasks in the benchmark."""
    tasks_path = Path(__file__).parent.parent / "tasks" / "tasks.json"
    if not tasks_path.exists():
        return {"tasks": []}
    with open(tasks_path) as f:
        tasks = json.load(f)
    return {
        "tasks": tasks,
        "categories": list({t["category"] for t in tasks}),
        "total": len(tasks),
    }


@app.get("/stats")
def global_stats():
    """High-level stats for the hero section of the dashboard."""
    total_api_calls = sum(
        len(r.get("scored_results", []))
        for r in RUNS
    )
    latest_ts = LATEST_RUN["timestamp"] if LATEST_RUN else None

    return {
        "total_runs": len(RUNS),
        "total_api_calls": total_api_calls,
        "models_tracked": 5,
        "tasks_per_run": LATEST_RUN.get("task_count", 50) if LATEST_RUN else 50,
        "latest_run_timestamp": latest_ts,
    }
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from pydantic import BaseModel

class OptimizeRequest(BaseModel):
    goal: str
    num_variations: int = 10
    models: list[str] = ["gemini", "mistral"]
    top_k: int = 3

@app.post("/optimize")
async def optimize_prompt(request: OptimizeRequest):
    """
    Takes a user goal, generates prompt variations,
    benchmarks them across models, returns the best ones.
    """
    from optimizer.optimizer import optimize
    result = await optimize(
        user_goal=request.goal,
        num_variations=request.num_variations,
        models=request.models,
        top_k=request.top_k,
    )
    return result

@app.get("/optimize/strategies")
def get_strategies():
    """Returns all available prompt strategies."""
    from optimizer.generator import VARIATION_STRATEGIES
    return {"strategies": VARIATION_STRATEGIES, "total": len(VARIATION_STRATEGIES)}