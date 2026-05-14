import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from optimizer.generator import generate_prompt_variations
from optimizer.evaluator import evaluate_all

async def optimize(user_goal, num_variations=10, models=None, top_k=3):
    if models is None:
        models = ["gemini", "mistral"]
    variations = await generate_prompt_variations(user_goal=user_goal, num_variations=num_variations)
    all_results = await evaluate_all(variations=variations, user_goal=user_goal, models=models)
    top_results = all_results[:top_k]
    from collections import defaultdict
    model_stats = {}
    for model in models:
        model_results = [r for r in all_results if r["model"] == model and not r.get("error")]
        if model_results:
            scores = [r["score"] for r in model_results]
            costs = [r["cost_usd"] for r in model_results]
            latencies = [r["latency_ms"] for r in model_results]
            model_stats[model] = {
                "avg_score": round(sum(scores)/len(scores), 1),
                "best_score": max(scores),
                "avg_cost_usd": round(sum(costs)/len(costs), 6),
                "avg_latency_ms": round(sum(latencies)/len(latencies)),
            }
    return {
        "user_goal": user_goal,
        "total_combinations_tested": len(all_results),
        "top_results": top_results,
        "model_stats": model_stats,
        "all_results": all_results,
    }
