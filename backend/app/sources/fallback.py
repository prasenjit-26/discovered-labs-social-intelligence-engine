from typing import List, Optional
import logging

from app.sources.base import SocialSourcePlugin
from app.sources.reddit import RedditPlugin
from app.sources.reddit_json import RedditJsonPlugin
from app.sources.pushshift import PushshiftPlugin
from app.sources.reddit_html import RedditHtmlScrapePlugin
from app.sources.local_dataset import LocalDatasetPlugin
from app.core.config import settings
from app.models.unified import Community, UnifiedPost

logger = logging.getLogger(__name__)


class FallbackRedditSource(SocialSourcePlugin):
    """Try multiple Reddit data sources in order until one works."""

    def __init__(self, dataset_path: str):
        self.dataset = LocalDatasetPlugin(dataset_path)
        self.json_api = RedditJsonPlugin()
        self.pushshift = PushshiftPlugin()
        self.html = RedditHtmlScrapePlugin()

        self.official: Optional[RedditPlugin] = None
        if settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET:
            self.official = RedditPlugin()

    async def search_communities(self, query: str) -> List[Community]:
        print(f"FallbackRedditSource.search_communities query={query}")

        # 1) Official API
        if self.official:
            try:
                res = await self.official.search_communities(query)
                if res:
                    print(f"Official API found {len(res)} communities")
                    return res
                print("Official API returned empty")
            except Exception as e:
                print(f"Official API failed: {e}")
                pass

        # 2) Public JSON endpoints
        try:
            res = await self.json_api.search_communities(query)
            if res:
                print(f"JSON API found {len(res)} communities")
                return res
            print("JSON API returned empty")
        except Exception as e:
            print(f"JSON API failed: {e}")
            pass

        # 3) HTML scraping
        try:
            res = await self.html.search_communities(query)
            if res:
                print(f"HTML scraping found {len(res)} communities")
                return res
            print("HTML scraping returned empty")
        except Exception as e:
            print(f"HTML scraping failed: {e}")
            pass

        # 4) Local dataset
        res = await self.dataset.search_communities(query)
        print(f"Local dataset found {len(res)} communities")
        return res

    async def fetch_discussions(self, community_id: str, limit: int = 20) -> List[UnifiedPost]:
        print(f"FallbackRedditSource.fetch_discussions community_id={community_id} limit={limit}")

        # 1) Official API
        if self.official:
            try:
                res = await self.official.fetch_discussions(community_id, limit=limit)
                if res:
                    print(f"Official API returned {len(res)} posts")
                    return res
                print("Official API returned empty")
            except Exception as e:
                print(f"Official API failed: {e}")
                pass

        # 2) Public JSON endpoints
        try:
            res = await self.json_api.fetch_discussions(community_id, limit=limit)
            if res:
                print(f"JSON API returned {len(res)} posts")
                return res
            print("JSON API returned empty")
        except Exception as e:
            print(f"JSON API failed: {e}")
            pass

        # 3) Pushshift (best-effort)
        try:
            res = await self.pushshift.fetch_discussions(community_id, limit=limit)
            if res:
                print(f"Pushshift returned {len(res)} posts")
                return res
            print("Pushshift returned empty")
        except Exception as e:
            print(f"Pushshift failed: {e}")
            pass

        # 4) HTML scraping
        try:
            res = await self.html.fetch_discussions(community_id, limit=limit)
            if res:
                print(f"HTML scraping returned {len(res)} posts")
                return res
            print("HTML scraping returned empty")
        except Exception as e:
            print(f"HTML scraping failed: {e}")
            pass

        # 5) Local dataset
        res = await self.dataset.fetch_discussions(community_id, limit=limit)
        print(f"Local dataset returned {len(res)} posts")
        return res