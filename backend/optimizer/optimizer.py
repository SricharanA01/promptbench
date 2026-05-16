import asyncio
from generator import generate_prompt_variations
from evaluator import evaluate_all


async def optimize(
    user_goal: str,
    num_variations: int = 20,
    models: list[str] = None,
    top_k: int = 3,
) -> dict:
    """
    Full pipeline: goal → variations → evaluation → ranked results.
    Returns top_k best prompt+model combinations.
    """
    if models is None:
        models = ["gemini", "mistral"]

    print(f"\n{'='*60}")
    print(f"🚀 PromptBench Optimizer")
    print(f"   Goal: {user_goal}")
    print(f"   Variations: {num_variations} | Models: {models}")
    print(f"{'='*60}\n")

    # Step 1: generate variations
    variations = await generate_prompt_variations(
        user_goal=user_goal,
        num_variations=num_variations,
    )

    # Step 2: evaluate all variations across all models
    all_results = await evaluate_all(
        variations=variations,
        user_goal=user_goal,
        models=models,
    )

    # Step 3: get top results
    top_results = all_results[:top_k]
    successful = [r for r in all_results if not r["error"]]

    # Step 4: aggregate model-level stats
    model_stats = {}
    for model in models:
        model_results = [r for r in successful if r["model"] == model]
        if model_results:
            scores = [r["score"] for r in model_results]
            costs = [r["cost_usd"] for r in model_results]
            latencies = [r["latency_ms"] for r in model_results]
            model_stats[model] = {
                "avg_score": round(sum(scores) / len(scores), 1),
                "best_score": max(scores),
                "avg_cost_usd": round(sum(costs) / len(costs), 6),
                "avg_latency_ms": round(sum(latencies) / len(latencies)),
            }

    result = {
        "user_goal": user_goal,
        "total_combinations_tested": len(all_results),
        "top_results": top_results,
        "model_stats": model_stats,
        "all_results": all_results,
    }

    # Print summary
    print(f"\n{'='*60}")
    print(f"🏆 TOP {top_k} RESULTS")
    print(f"{'='*60}")
    for i, r in enumerate(top_results):
        print(f"\n#{i+1} Score: {r['score']}/10 | Model: {r['model']} | Strategy: {r['strategy']}")
        print(f"   Cost: ${r['cost_usd']:.5f} | Latency: {r['latency_ms']}ms")
        print(f"   Prompt preview: {r['prompt'][:100]}...")
        print(f"   Why: {r['score_reasoning']}")

    print(f"\n{'='*60}")
    print(f"📊 MODEL COMPARISON")
    for model, stats in model_stats.items():
        print(f"   {model}: avg {stats['avg_score']}/10 | best {stats['best_score']}/10 | avg cost ${stats['avg_cost_usd']:.5f}")

    return result


if __name__ == "__main__":
    import sys

    goal = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "summarize a legal contract and highlight the key risks"
    asyncio.run(optimize(user_goal=goal, num_variations=10, top_k=3))