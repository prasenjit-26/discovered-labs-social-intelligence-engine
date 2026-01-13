from typing import List
from datetime import datetime, timezone
import httpx

from app.models.unified import UnifiedPost, Platform, SocialActor
from app.sources.content_base import ContentSourcePlugin
from app.core.config import settings


class OfficialXSource(ContentSourcePlugin):
    def __init__(self, bearer_token: str = ""):
        self.bearer_token = bearer_token or getattr(settings, "X_BEARER_TOKEN", "")

    async def fetch_posts(self, query: str, limit: int = 50) -> List[UnifiedPost]:
        if not self.bearer_token:
            raise RuntimeError("Missing X_BEARER_TOKEN")

        q = (query or "").strip()
        if not q:
            return []

        url = "https://api.x.com/2/tweets/search/recent"
        params = {
            "query": q,
            "max_results": min(max(int(limit), 10), 100),
            "tweet.fields": "created_at,public_metrics,author_id",
        }
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            payload = resp.json()

        out: List[UnifiedPost] = []
        for t in payload.get("data", []) or []:
            tid = t.get("id")
            text = t.get("text") or ""
            if not tid or not text:
                continue

            created_at = t.get("created_at")
            ts = datetime.now(timezone.utc)
            if created_at:
                try:
                    ts = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                except Exception:
                    ts = datetime.now(timezone.utc)

            metrics = t.get("public_metrics") or {}
            engagement = float(
                (metrics.get("like_count") or 0)
                + 2 * (metrics.get("retweet_count") or 0)
                + (metrics.get("reply_count") or 0)
            )

            author_id = t.get("author_id") or "unknown"
            out.append(
                UnifiedPost(
                    id=f"x_{tid}",
                    platform=Platform.TWITTER,
                    content=text,
                    author=SocialActor(id=f"x_{author_id}", username=str(author_id), platform=Platform.TWITTER),
                    community_id=None,
                    timestamp=ts,
                    engagement_score=engagement,
                    url=f"https://x.com/i/web/status/{tid}",
                )
            )

        return out
