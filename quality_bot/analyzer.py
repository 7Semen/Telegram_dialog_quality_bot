import os
import json
from typing import Tuple
import httpx

SYSTEM_PROMPT = """Ты анализируешь корпоративные сообщения.
Верни СТРОГО JSON без пояснений в формате:
{
  "sentiment": "positive|neutral|negative",
  "problem": "ok|aggressive_tone|toxic|impolite|unclear|off_topic"
}
Если явной проблемы нет — problem="ok".
"""

SENTIMENT_MAP = {
    "позитивная": "positive",
    "нейтральная": "neutral",
    "негативная": "negative",
}

PROBLEM_MAP = {
    "ок": "ok",
    "aggressive_tone": "aggressive_tone",
    "агрессивный тон": "aggressive_tone",
    "toxic": "toxic",
    "токсичность": "toxic",
    "impolite": "impolite",
    "невежливость": "impolite",
    "unclear": "unclear",
    "непонятно": "unclear",
    "off_topic": "off_topic",
    "не по теме": "off_topic",
}

ALLOWED_SENTIMENT = {"positive", "neutral", "negative"}
ALLOWED_PROBLEM = {"ok", "aggressive_tone", "toxic", "impolite", "unclear", "off_topic"}


def _extract_json(content: str) -> str:
    content = (content or "").strip()

    # code-fence ```json ... ```
    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    # если вокруг JSON есть мусор — вырежем первый объект
    if not content.startswith("{"):
        l = content.find("{")
        r = content.rfind("}")
        if l != -1 and r != -1 and r > l:
            content = content[l:r + 1]

    return content


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
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)

        if resp.status_code >= 400:
            # можно залогировать resp.text, но аккуратно (без ключей)
            return "neutral", "ok"

        data = resp.json()
        content = (data.get("choices", [{}])[0].get("message", {}) or {}).get("content", "")
        content = _extract_json(content)

        obj = json.loads(content)

        sentiment = SENTIMENT_MAP.get(obj.get("sentiment", "neutral"), obj.get("sentiment", "neutral"))
        problem = obj.get("problem", "ok")
        problem = PROBLEM_MAP.get(problem, problem)

        if sentiment not in ALLOWED_SENTIMENT:
            sentiment = "neutral"
        if problem not in ALLOWED_PROBLEM:
            problem = "ok"

        return sentiment, problem

    except Exception:
        return "neutral", "ok"
