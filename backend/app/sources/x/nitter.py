from typing import List
from datetime import datetime, timezone
import asyncio
from urllib.parse import urlparse

from app.models.unified import UnifiedPost, Platform, SocialActor
from app.sources.content_base import ContentSourcePlugin
from app.core.config import settings
from ntscraper import Nitter


class NitterXSource(ContentSourcePlugin):
    def __init__(self, base_url: str = ""):
        self.base_url = (base_url or getattr(settings, "NITTER_BASE_URL", "") or "https://nitter.net").rstrip("/")

    def _instance(self) -> str:
        """ntscraper expects a hostname like 'nitter.net' (not a full https URL)."""
        try:
            p = urlparse(self.base_url)
            return (p.netloc or p.path or "").strip().lstrip("/")
        except Exception:
            return (
                self.base_url.replace("https://", "")
                .replace("http://", "")
                .split("/")[0]
                .strip()
            )

    async def fetch_posts(self, query: str, limit: int = 50) -> List[UnifiedPost]:
        q = (query or "").strip()
        if not q:
            return []

        def _scrape(instance: str = None) -> dict:
            scraper = Nitter()
            return scraper.get_tweets(
                q,
                mode="term",
                number=int(limit or 50),
                instance=instance,
                max_retries=2,
            )

        instance = self._instance()
        try:
            data = await asyncio.to_thread(_scrape, instance)
        except IndexError:
            # ntscraper sometimes throws IndexError depending on instance state.
            # Retry without forcing instance (random instance selection).
            data = await asyncio.to_thread(_scrape, None)
        tweets = (data or {}).get("tweets", []) or []

        items: List[UnifiedPost] = []
        for t in tweets:
            if len(items) >= limit:
                break

            tid = t.get("tweetId") or t.get("id") or t.get("tweet_id")
            link = t.get("link") or t.get("url")
            text = t.get("text") or t.get("content") or ""
            user = t.get("user") or {}
            username = (
                user.get("username")
                or user.get("name")
                or t.get("username")
                or "unknown"
            )
            if isinstance(username, str):
                username = username.lstrip("@").strip() or "unknown"

            if not tid and link:
                # Try to extract id from URL if present
                parts = str(link).split("/")
                if "status" in parts:
                    try:
                        tid = parts[parts.index("status") + 1]
                    except Exception:
                        tid = None

            if not tid or not text:
                continue

            ts = datetime.now(timezone.utc)
            dt = t.get("date") or t.get("created_at")
            if isinstance(dt, datetime):
                ts = dt
            elif isinstance(dt, str) and dt:
                try:
                    ts = datetime.fromisoformat(dt.replace("Z", "+00:00"))
                except Exception:
                    ts = datetime.now(timezone.utc)

            stats = t.get("stats") or t.get("public_metrics") or {}

            def _num(x):
                try:
                    return int(str(x).replace(",", ""))
                except Exception:
                    return 0

            engagement = float(
                _num(stats.get("likes"))
                + 2 * _num(stats.get("retweets"))
                + _num(stats.get("replies"))
                + _num(stats.get("quotes"))
            )

            items.append(
                UnifiedPost(
                    id=f"x_{tid}",
                    platform=Platform.TWITTER,
                    content=text,
                    author=SocialActor(
                        id=f"x_{username}", username=username, platform=Platform.TWITTER
                    ),
                    community_id=None,
                    timestamp=ts,
                    engagement_score=engagement,
                    url=link or "",
                )
            )

        return items
