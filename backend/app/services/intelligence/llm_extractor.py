import asyncio
import json
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

from app.core.config import settings


class LLMExtractorService:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self.model = model if model is not None else settings.OPENAI_MODEL
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        self.client = OpenAI(api_key=self.api_key)

    async def infer_relations(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Batched relationship inference using already-resolved entities.

        posts: [{"id": str, "text": str, "entities": [{"canonical": str, "label": str}]}]

        Returns:
        {
          "posts": {
             "<post_id>": {
                "relations": [{"source": str, "relation": str, "target": str, "confidence": float, "evidence": str}]
             }
          }
        }
        """

        system = (
            "You infer relationships from social posts given a list of already-resolved entities. "
            "Return ONLY valid JSON matching the requested schema. "
            "You MUST use provided canonical entities when referencing real-world entities. "
            "You MAY introduce CONCEPT nodes (lowercase phrases like agents, knowledge sharing) when useful. "
            "Do not invent new named entities beyond the provided list; every relation must have evidence."
        )

        user = {
            "task": "Infer relationships per post using provided entities",
            "schema": {
                "posts": {
                    "<post_id>": {
                        "relations": [
                            {
                                "source": "string (must be one of provided canonical entities OR a new CONCEPT)",
                                "relation": "string (verb/role)",
                                "target": "string (must be one of provided canonical entities OR a new CONCEPT)",
                                "confidence": "number 0..1",
                                "evidence": "string (quote/snippet from the post)"
                            }
                        ]
                    }
                }
            },
            "rules": [
                "Output must be strict JSON, no markdown.",
                "Do NOT create new named entities. If something looks like a named entity but is not in the provided list, skip it.",
                "CONCEPT nodes are allowed and should be lowercase and concise (1-4 words).",
                "Prefer relations between provided entities when possible.",
                "Relations must be forward direction (source -> target).",
                "Max 10 relations per post.",
                "If no relations, return an empty array for that post.",
            ],
            "posts": posts,
        }

        def _call_openai() -> str:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(user)},
                ],
                temperature=0.1,
            )
            return resp.choices[0].message.content or "{}"

        raw = await asyncio.to_thread(_call_openai)

        try:
            parsed = json.loads(raw)
        except Exception:
            # Best-effort salvage if model returned extra text
            start = raw.find("{")
            end = raw.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return {"posts": {}}
            try:
                parsed = json.loads(raw[start : end + 1])
            except Exception:
                return {"posts": {}}

        if not isinstance(parsed, dict):
            return {"posts": {}}

        if "posts" not in parsed or not isinstance(parsed.get("posts"), dict):
            return {"posts": {}}

        return parsed
