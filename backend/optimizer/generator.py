import asyncio
import os
from typing import Optional
import httpx
from dotenv import load_dotenv

load_dotenv()

VARIATION_STRATEGIES = [
    "direct and concise",
    "step by step instructions",
    "role-based (assign the AI a persona)",
    "few-shot with examples",
    "chain of thought reasoning",
    "structured output format",
    "constraint-based (add specific rules)",
    "audience-specific (explain for a beginner)",
    "expert-level technical",
    "question-based (reframe as questions)",
    "action-oriented with verbs",
    "context-rich with background",
    "negative framing (what NOT to do)",
    "comparative analysis style",
    "bullet point focused",
    "narrative storytelling style",
    "socratic method",
    "first principles breakdown",
    "eli5 (explain like im 5)",
    "professional formal tone",
]

async def generate_prompt_variations(user_goal: str, num_variations: int = 20, model: str = "gemini") -> list[dict]:
    strategies = VARIATION_STRATEGIES[:num_variations]
    variations = []
    async with httpx.AsyncClient() as client:
        tasks = [_generate_single_variation(client, user_goal, strategy, model) for strategy in strategies]
        results = await asyncio.gather(*tasks)
    for strategy, prompt in zip(strategies, results):
        if prompt:
            variations.append({"strategy": strategy, "prompt": prompt})
    return variations

async def _generate_single_variation(client, user_goal, strategy, model):
    meta_prompt = f"""You are an expert prompt engineer. Write a single optimized prompt for this goal: {user_goal}. Strategy: {strategy}. Write ONLY the prompt, nothing else, under 200 words."""
    try:
        if model == "gemini":
            return await _call_gemini(client, meta_prompt)
        return await _call_mistral(client, meta_prompt)
    except Exception as e:
        return None

async def _call_gemini(client, prompt):
    api_key = os.getenv("GOOGLE_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.8, "maxOutputTokens": 300}}
    resp = await client.post(url, json=body, timeout=30)
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

async def _call_mistral(client, prompt):
    headers = {"Authorization": f"Bearer {os.getenv('MISTRAL_API_KEY')}", "Content-Type": "application/json"}
    body = {"model": "mistral-small-latest", "messages": [{"role": "user", "content": prompt}], "temperature": 0.8, "max_tokens": 300}
    resp = await client.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=body, timeout=30)
    return resp.json()["choices"][0]["message"]["content"].strip()
