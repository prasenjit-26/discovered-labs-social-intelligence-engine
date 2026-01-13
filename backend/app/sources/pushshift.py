import httpx
from typing import List
from datetime import datetime

from app.sources.base import SocialSourcePlugin
from app.models.unified import Community, UnifiedPost, Platform, SocialActor


class PushshiftPlugin(SocialSourcePlugin):
    """Best-effort Pushshift integration.

    Note: Pushshift availability has historically changed. This plugin is designed
    to fail gracefully and allow fallbacks.
    """

    def __init__(self):
        self.base_headers = {
            "User-Agent": "social-intel-engine/1.0 (pushshift)"
        }

    async def search_communities(self, query: str) -> List[Community]:
        # Pushshift doesn't reliably provide subreddit search. We'll return empty here.
        return []

    async def fetch_discussions(self, community_id: str, limit: int = 20) -> List[UnifiedPost]:
        subreddit_name = community_id.replace("reddit_", "")

        # Historical endpoint format (best-effort)
        url = "https://api.pushshift.io/reddit/search/submission/"
        params = {"subreddit": subreddit_name, "size": min(limit, 100), "sort": "desc", "sort_type": "created_utc"}

        async with httpx.AsyncClient(headers=self.base_headers, timeout=15) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            payload = r.json()

        items = payload.get("data", [])
        posts: List[UnifiedPost] = []

        for item in items:
            post_id = item.get("id") or item.get("full_link")
            if not post_id:
                continue

            created_utc = item.get("created_utc") or 0
            dt = datetime.fromtimestamp(created_utc)

            author_name = item.get("author") or "unknown"
            title = item.get("title") or ""
            selftext = item.get("selftext") or ""
            score = int(item.get("score") or 0)
            num_comments = int(item.get("num_comments") or 0)
            url_link = item.get("full_link") or item.get("url") or ""

            posts.append(
                UnifiedPost(
                    id=f"pushshift_post_{post_id}",
                    platform=Platform.REDDIT,
                    content=f"{title}\n{selftext}",
                    author=SocialActor(
                        id=f"reddit_user_{author_name}",
                        username=author_name,
                        platform=Platform.REDDIT,
                    ),
                    community_id=community_id,
                    timestamp=dt,
                    engagement_score=float(score + num_comments),
                    url=url_link,
                )
            )

        return posts
