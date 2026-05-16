import asyncio
import os
import time
from typing import Optional
import httpx
from dotenv import load_dotenv

load_dotenv()


async def evaluate_prompt(
    client: httpx.AsyncClient,
    prompt: str,
    user_goal: str,
    model: str,
) -> dict:
    """
    Runs a single prompt against a single model.
    Returns score, latency, cost, and the actual response.
    """
    try:
        if model == "gemini":
            result = await _run_gemini(client, prompt)
        elif model == "mistral":
            result = await _run_mistral(client, prompt)
        else:
            return _error_result(model, "unknown model")

        score = await _score_response(client, result["response"], user_goal)

        return {
            "model": model,
            "prompt": prompt,
            "response": result["response"],
            "latency_ms": result["latency_ms"],
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
            "cost_usd": result["cost_usd"],
            "score": score["score"],
            "score_reasoning": score["reasoning"],
            "error": None,
        }

    except Exception as e:
        return _error_result(model, str(e))


async def evaluate_all(
    variations: list[dict],
    user_goal: str,
    models: list[str] = None,
) -> list[dict]:
    """
    Runs every prompt variation against every model.
    Returns all results sorted by score descending.
    """
    if models is None:
        models = ["gemini", "mistral"]

    print(f"📊 Evaluating {len(variations)} prompts × {len(models)} models = {len(variations) * len(models)} total runs\n")

    all_results = []

    async with httpx.AsyncClient() as client:
        for i, variation in enumerate(variations):
            print(f"[{i+1}/{len(variations)}] Strategy: {variation['strategy'][:45]}")

            tasks = [
                evaluate_prompt(client, variation["prompt"], user_goal, model)
                for model in models
            ]
            results = await asyncio.gather(*tasks)

            for r in results:
                r["strategy"] = variation["strategy"]
                status = f"score:{r['score']}/10" if not r["error"] else f"error:{r['error'][:30]}"
                print(f"     {r['model']:15s} {status}")
                all_results.append(r)

            await asyncio.sleep(0.3)

    all_results.sort(key=lambda x: x["score"], reverse=True)
    print(f"\n✅ Evaluation complete — best score: {all_results[0]['score']}/10\n")
    return all_results


async def _score_response(
    client: httpx.AsyncClient,
    response: str,
    user_goal: str,
) -> dict:
    """Use Gemini to score how well a response achieves the user goal."""
    if not response:
        return {"score": 0, "reasoning": "no response"}

    judge_prompt = f"""You are evaluating whether an AI response successfully achieves a user's goal.

USER GOAL: {user_goal}

AI RESPONSE TO EVALUATE:
{response[:800]}

Score this response from 0-10:
- 10: Perfectly achieves the goal, clear, specific, actionable
- 7-9: Mostly achieves the goal with minor gaps
- 4-6: Partially achieves the goal
- 1-3: Barely relevant to the goal
- 0: Completely misses the goal or refused

Respond with ONLY this JSON:
{{"score": <0-10>, "reasoning": "<one sentence>"}}"""

    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        body = {
            "contents": [{"role": "user", "parts": [{"text": judge_prompt}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 100}
        }
        resp = await client.post(url, json=body, timeout=20)
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()

        import json, re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            result = json.loads(match.group())
            return {
                "score": max(0, min(10, int(result.get("score", 5)))),
                "reasoning": result.get("reasoning", ""),
            }
    except Exception:
        pass

    return {"score": 5, "reasoning": "scoring unavailable"}


async def _run_gemini(client: httpx.AsyncClient, prompt: str) -> dict:
    api_key = os.getenv("GOOGLE_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 512}
    }
    start = time.perf_counter()
    resp = await client.post(url, json=body, timeout=30)
    latency_ms = int((time.perf_counter() - start) * 1000)
    data = resp.json()
    input_tokens = data.get("usageMetadata", {}).get("promptTokenCount", 0)
    output_tokens = data.get("usageMetadata", {}).get("candidatesTokenCount", 0)
    return {
        "response": data["candidates"][0]["content"]["parts"][0]["text"].strip(),
        "latency_ms": latency_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(input_tokens / 1000 * 0.000125 + output_tokens / 1000 * 0.000375, 6),
    }


async def _run_mistral(client: httpx.AsyncClient, prompt: str) -> dict:
    headers = {
        "Authorization": f"Bearer {os.getenv('MISTRAL_API_KEY')}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "mistral-small-latest",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 512,
    }
    start = time.perf_counter()
    resp = await client.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers=headers, json=body, timeout=30
    )
    latency_ms = int((time.perf_counter() - start) * 1000)
    data = resp.json()
    input_tokens = data["usage"]["prompt_tokens"]
    output_tokens = data["usage"]["completion_tokens"]
    return {
        "response": data["choices"][0]["message"]["content"].strip(),
        "latency_ms": latency_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(input_tokens / 1000 * 0.0002 + output_tokens / 1000 * 0.0006, 6),
    }


def _error_result(model: str, error: str) -> dict:
    return {
        "model": model,
        "prompt": "",
        "response": None,
        "latency_ms": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0,
        "score": 0,
        "score_reasoning": f"error: {error}",
        "error": error,
        "strategy": "",
    }