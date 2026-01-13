import json
from pathlib import Path
from typing import List
from datetime import datetime

from app.sources.base import SocialSourcePlugin
from app.models.unified import Community, UnifiedPost, Platform, SocialActor


class LocalDatasetPlugin(SocialSourcePlugin):
    """Always-available fallback backed by a local JSON dataset."""

    def __init__(self, dataset_path: str):
        self.dataset_path = Path(dataset_path)
        self._data = None

    def _load(self):
        if self._data is not None:
            return
        with self.dataset_path.open("r", encoding="utf-8") as f:
            self._data = json.load(f)

    async def search_communities(self, query: str) -> List[Community]:
        self._load()
        q = query.lower()
        communities: List[Community] = []
        for c in self._data.get("communities", []):
            name = c.get("name", "")
            desc = (c.get("description") or "").lower()
            if q in name.lower() or q in desc:
                communities.append(
                    Community(
                        id=c["id"],
                        name=c["name"],
                        url=c.get("url", ""),
                        platform=Platform.REDDIT,
                        subscribers=int(c.get("subscribers") or 0),
                        active_users=int(c.get("active_users") or 0),
                        relevance_score=float(c.get("relevance_score") or 0.5),
                        description=c.get("description"),
                    )
                )
        return communities[:20]

    async def fetch_discussions(self, community_id: str, limit: int = 20) -> List[UnifiedPost]:
        self._load()
        posts: List[UnifiedPost] = []
        for p in self._data.get("posts", []):
            if p.get("community_id") != community_id:
                continue
            dt = datetime.fromisoformat(p["timestamp"])
            posts.append(
                UnifiedPost(
                    id=p["id"],
                    platform=Platform.REDDIT,
                    content=p.get("content", ""),
                    author=SocialActor(
                        id=p.get("author_id", "reddit_user_unknown"),
                        username=p.get("author", "unknown"),
                        platform=Platform.REDDIT,
                    ),
                    community_id=community_id,
                    timestamp=dt,
                    engagement_score=float(p.get("engagement_score") or 0.0),
                    url=p.get("url", ""),
                )
            )
            if len(posts) >= limit:
                break
        return posts
