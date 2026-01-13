import httpx
from typing import List
from datetime import datetime

from app.sources.base import SocialSourcePlugin
from app.models.unified import Community, UnifiedPost, Platform, SocialActor


class RedditJsonPlugin(SocialSourcePlugin):
    """Public Reddit JSON endpoints (no API key)."""

    def __init__(self):
        self.base_headers = {
            "User-Agent": "social-intel-engine/1.0 (json-endpoints)"
        }

    async def search_communities(self, query: str) -> List[Community]:
        url = "https://www.reddit.com/subreddits/search.json"
        params = {"q": query, "limit": 20}

        async with httpx.AsyncClient(headers=self.base_headers, timeout=15) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            payload = r.json()

        children = payload.get("data", {}).get("children", [])
        communities: List[Community] = []

        for item in children:
            data = item.get("data", {})
            name = data.get("display_name", "")
            if not name:
                continue

            subscribers = int(data.get("subscribers") or 0)
            active_users = int(data.get("accounts_active") or 0)
            public_description = data.get("public_description") or ""

            communities.append(
                Community(
                    id=f"reddit_{name.lower()}",
                    name=f"r/{name}",
                    url=f"https://reddit.com/r/{name}",
                    platform=Platform.REDDIT,
                    subscribers=subscribers,
                    active_users=active_users,
                    relevance_score=0.5,
                    description=public_description,
                )
            )

        return communities

    async def fetch_discussions(self, community_id: str, limit: int = 20) -> List[UnifiedPost]:
        subreddit_name = community_id.replace("reddit_", "")
        url = f"https://www.reddit.com/r/{subreddit_name}/hot.json"
        params = {"limit": limit}

        async with httpx.AsyncClient(headers=self.base_headers, timeout=15) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            payload = r.json()

        children = payload.get("data", {}).get("children", [])
        posts: List[UnifiedPost] = []

        for item in children:
            data = item.get("data", {})
            post_id = data.get("id")
            if not post_id:
                continue

            created_utc = data.get("created_utc") or 0
            dt = datetime.fromtimestamp(created_utc)

            author_name = data.get("author") or "unknown"
            title = data.get("title") or ""
            selftext = data.get("selftext") or ""
            score = int(data.get("score") or 0)
            num_comments = int(data.get("num_comments") or 0)
            permalink = data.get("permalink") or ""

            posts.append(
                UnifiedPost(
                    id=f"reddit_post_{post_id}",
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
                    url=f"https://reddit.com{permalink}",
                )
            )

        return posts
