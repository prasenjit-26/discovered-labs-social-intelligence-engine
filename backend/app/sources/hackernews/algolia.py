from typing import List
from datetime import datetime, timezone
import httpx

from app.models.unified import UnifiedPost, Platform, SocialActor
from app.sources.content_base import ContentSourcePlugin


class HackerNewsAlgoliaSource(ContentSourcePlugin):
    async def fetch_posts(self, query: str, limit: int = 50) -> List[UnifiedPost]:
        q = (query or "").strip()
        if not q:
            return []

        url = "https://hn.algolia.com/api/v1/search"
        params = {
            "query": q,
            "tags": "story",
            "hitsPerPage": min(max(int(limit), 1), 100),
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            payload = resp.json()

        out: List[UnifiedPost] = []
        for hit in payload.get("hits", []) or []:
            oid = hit.get("objectID")
            title = hit.get("title") or ""
            story_text = hit.get("story_text") or ""
            story_url = hit.get("url") or ""
            author = hit.get("author") or "unknown"
            created_at = hit.get("created_at")

            if not oid or not title:
                continue

            ts = datetime.now(timezone.utc)
            if created_at:
                try:
                    ts = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                except Exception:
                    ts = datetime.now(timezone.utc)

            points = hit.get("points") or 0
            comments = hit.get("num_comments") or 0
            engagement = float(points + 2 * comments)

            content = title
            if story_text:
                content = f"{title}\n\n{story_text}"
            elif story_url:
                content = f"{title}\n{story_url}"

            out.append(
                UnifiedPost(
                    id=f"hn_{oid}",
                    platform=Platform.HACKERNEWS,
                    content=content,
                    author=SocialActor(id=f"hn_{author}", username=author, platform=Platform.HACKERNEWS),
                    community_id=None,
                    timestamp=ts,
                    engagement_score=engagement,
                    url=story_url or f"https://news.ycombinator.com/item?id={oid}",
                )
            )

        return out
