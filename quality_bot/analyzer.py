import os
import json
import requests

SYSTEM_PROMPT = """Ты анализируешь корпоративные сообщения.
Верни СТРОГО JSON без пояснений:
{
  "sentiment": "positive|neutral|negative",
  "problem": "ok|aggressive_tone|toxic|impolite|unclear|off_topic"
}
Если явной проблемы нет — problem = "ok".
"""

def analyze_text(text: str) -> tuple[str, str]:
    iam = os.getenv("YANDEX_IAM_TOKEN", "").strip()
    base_url = os.getenv("YANDEX_OPENAI_BASE_URL", "https://llm.api.cloud.yandex.net/v1").strip()
    model = os.getenv("YANDEX_OPENAI_MODEL", "").strip()

    if not iam or not model:
        return "neutral", "ok"

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {iam}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "temperature": 0.0,
        "max_tokens": 200,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        if not r.ok:
            print("OPENAI HTTP:", r.status_code, r.text)
            return "neutral", "ok"

        data = r.json()
        print("OPENAI RESPONSE:", data)

        answer = data["choices"][0]["message"]["content"].strip()
        obj = json.loads(answer)
        return obj.get("sentiment", "neutral"), obj.get("problem", "ok")

    except Exception as e:
        print("OPENAI ERROR:", type(e).__name__, e)
        return "neutral", "ok"