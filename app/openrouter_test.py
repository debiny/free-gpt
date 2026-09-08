from pathlib import Path

import httpx
from pydotenv import Environment

env = Environment(str(Path(__file__).parent / ".env"))
API_KEY = env.get("OPENROUTER_API_KEY")
MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"  # troque pelo modelo desejado

resp = httpx.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={"model": MODEL, "messages": [{"role": "user", "content": "Diga oi em uma frase curta."}]},
    timeout=30,
)
resp.raise_for_status()
print(resp.json()["choices"][0]["message"]["content"])
