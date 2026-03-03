import os
import json
import httpx
from typing import Tuple

SYSTEM_PROMPT = """Ты анализируешь корпоративные сообщения.
Верни СТРОГО JSON без пояснений в формате:
{
  "sentiment": "positive|neutral|negative",
  "problem": "ok|aggressive_tone|toxic|impolite|unclear|off_topic"
}
Если явной проблемы нет — problem="ok".
"""

SENTIMENT_MAP = {"позитивная":"positive","нейтральная":"neutral","негативная":"negative"}
PROBLEM_MAP = {
    "ок":"ok",
    "агрессивный тон":"aggressive_tone",
    "токсичность":"toxic",
    "невежливость":"impolite",
    "непонятно":"unclear",
    "не по теме":"off_topic",
}

async def analyze_text(text: str) -> Tuple[str, str]:
    text = (text or "").strip()
    if not text:
        return "neutral", "ok"

    api_key = os.getenv("YANDEX_API_KEY", "").strip()
    folder_id = os.getenv("YANDEX_FOLDER_ID", "").strip()
    model = os.getenv("YANDEX_MODEL", "").strip()

    if not api_key or not folder_id or not model:
        return "neutral", "ok"

    url = "https://llm.api.cloud.yandex.net/v1/chat/completions"
    headers = {
        "Authorization": f"Api-Key {api_key}",
        "Content-Type": "application/json; charset=utf-8",
        "x-folder-id": folder_id,
    }
    payload = {
        "model": model,
        "temperature": 0.0,
        "max_tokens": 120,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "response_format": {"type": "json_object"},
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, headers=headers, json=payload)

        if r.status_code >= 400:
            print("AI HTTP:", r.status_code, r.text)
            return "neutral", "ok"

        data = r.json()
        content = (data.get("choices", [{}])[0].get("message", {}) or {}).get("content", "")
        content = (content or "").strip()

        if content.startswith("```"):
            content = content.strip().strip("`").replace("json\n", "", 1).strip()

        obj = json.loads(content)

        sentiment = obj.get("sentiment", "neutral")
        problem = obj.get("problem", "ok")

        sentiment = SENTIMENT_MAP.get(sentiment, sentiment)
        problem = PROBLEM_MAP.get(problem, problem)

        if sentiment not in ("positive", "neutral", "negative"):
            sentiment = "neutral"
        if problem not in ("ok", "aggressive_tone", "toxic", "impolite", "unclear", "off_topic"):
            problem = "ok"

        return sentiment, problem

    except Exception as e:
        import traceback
        traceback.print_exc()
        print("AI ANALYZE ERROR:", type(e).__name__, e)
        return "neutral", "ok"
