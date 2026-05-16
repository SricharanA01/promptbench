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


async def generate_prompt_variations(
    user_goal: str,
    num_variations: int = 20,
    model: str = "gemini",
) -> list[dict]:
    """
    Takes a user goal and generates N prompt variations using different strategies.
    Returns list of {strategy, prompt} dicts.
    """
    print(f"\n🧠 Generating {num_variations} prompt variations for: '{user_goal}'")

    strategies = VARIATION_STRATEGIES[:num_variations]
    variations = []

    async with httpx.AsyncClient() as client:
        tasks = [
            _generate_single_variation(client, user_goal, strategy, model)
            for strategy in strategies
        ]
        results = await asyncio.gather(*tasks)

    for strategy, prompt in zip(strategies, results):
        if prompt:
            variations.append({
                "strategy": strategy,
                "prompt": prompt,
            })
            print(f"  ✓ {strategy[:40]}")

    print(f"\n✅ Generated {len(variations)} variations\n")
    return variations


async def _generate_single_variation(
    client: httpx.AsyncClient,
    user_goal: str,
    strategy: str,
    model: str,
) -> Optional[str]:
    """Generate one prompt variation using a specific strategy."""

    meta_prompt = f"""You are an expert prompt engineer. Your job is to write a single, optimized prompt that achieves the following goal:

GOAL: {user_goal}

STRATEGY TO USE: {strategy}

Rules:
- Write ONLY the prompt itself, nothing else
- Do not include explanations, labels, or meta-commentary
- The prompt should be ready to paste directly into an AI system
- Make it specific, clear, and optimized for the strategy
- Keep it under 200 words

Write the prompt now:"""

    try:
        if model == "gemini":
            return await _call_gemini(client, meta_prompt)
        elif model == "mistral":
            return await _call_mistral(client, meta_prompt)
        else:
            return await _call_gemini(client, meta_prompt)
    except Exception as e:
        print(f"  ✗ Failed for strategy '{strategy}': {e}")
        return None


async def _call_gemini(client: httpx.AsyncClient, prompt: str) -> str:
    api_key = os.getenv("GOOGLE_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 300}
    }
    resp = await client.post(url, json=body, timeout=30)
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


async def _call_mistral(client: httpx.AsyncClient, prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {os.getenv('MISTRAL_API_KEY')}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "mistral-small-latest",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 300,
    }
    resp = await client.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers=headers, json=body, timeout=30
    )
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()