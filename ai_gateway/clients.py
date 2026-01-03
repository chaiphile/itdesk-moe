import os
import requests
from typing import List
import hashlib
import json
from json import JSONDecodeError


class OpenRouterClient:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model
        # follow platform default base URL
        self.base = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    def summarize(self, text: str) -> dict:
        # Simple wrapper. In tests this method should be monkeypatched to avoid network.
        if not self.api_key:
            # fallback deterministic local summarization for dev without key
            return {
                "summary": (text[:250] + "...") if len(text) > 250 else text,
                "action_items": [],
                "timeline": [],
                "confidence": 0.6,
                "warnings": [],
            }
        url = f"{self.base}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        # Build a user message that requests STRICT JSON output
        system = {
            "role": "system",
            "content": "You are a strict JSON generator. Return ONLY a single valid JSON object matching the provided schema. Do not include any explanatory text."
        }
        user = {"role": "user", "content": text}
        payload = {"model": self.model, "messages": [system, user], "max_tokens": 1500}
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        # Simplified extraction — real integration may parse choices
        content = ""
        if isinstance(data, dict):
            # attempt common shapes
            choices = data.get("choices") or []
            if choices:
                message = choices[0].get("message") or choices[0]
                content = message.get("content") if isinstance(message, dict) else str(message)

        # Attempt to parse JSON only from the content
        try:
            parsed = json.loads(content)
            return parsed if isinstance(parsed, dict) else {"raw": content}
        except JSONDecodeError:
            # Return an indicator that parsing failed; caller should audit
            return {"__raw": content}


class EmbeddingClient:
    def __init__(self, model: str = "intfloat/multilingual-e5-large", dim: int = 1536):
        self.model = model
        self.dim = dim

    def embed(self, text: str) -> List[float]:
        # Deterministic pseudo-embedding: use repeated hashing to create float values in [-1,1]
        out = []
        i = 0
        while len(out) < self.dim:
            h = hashlib.sha256((text + str(i)).encode("utf-8")).digest()
            # take bytes in chunks of 8 to form a float-like value
            for j in range(0, len(h), 4):
                if len(out) >= self.dim:
                    break
                chunk = h[j : j + 4]
                val = int.from_bytes(chunk, "big", signed=False)
                # normalize to -1..1
                out.append(((val / 0xFFFFFFFF) * 2.0) - 1.0)
            i += 1
        return out[: self.dim]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]
