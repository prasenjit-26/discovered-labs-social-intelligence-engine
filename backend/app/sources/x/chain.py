from typing import List, Dict, Any, Optional

from app.models.unified import UnifiedPost
from app.sources.content_base import ContentSourcePlugin
from app.sources.x.official import OfficialXSource
from app.sources.x.snscrape_source import SnscrapeXSource
from app.sources.x.fallback import FallbackXSource
from app.core.config import settings


class ChainXSource(ContentSourcePlugin):
    def __init__(self):
        self._official: Optional[OfficialXSource] = None
        if getattr(settings, "X_BEARER_TOKEN", ""):
            self._official = OfficialXSource()

        self._snscrape = SnscrapeXSource()
        self._nitter_fallback = FallbackXSource()
        self.last_errors: List[Dict[str, Any]] = []

    async def fetch_posts(self, query: str, limit: int = 50) -> List[UnifiedPost]:
        self.last_errors = []

        if self._official is not None:
            try:
                posts = await self._official.fetch_posts(query, limit=limit)
                if posts:
                    return posts
            except Exception as e:
                self.last_errors.append({"source": "official", "error": repr(e)})

        try:
            posts = await self._snscrape.fetch_posts(query, limit=limit)
            if posts:
                return posts
        except Exception as e:
            self.last_errors.append({"source": "snscrape", "error": repr(e)})

        # try:
        #     posts = await self._nitter_fallback.fetch_posts(query, limit=limit)
        #     for item in getattr(self._nitter_fallback, "last_errors", []) or []:
        #         self.last_errors.append({"source": "nitter", **item})
        #     return posts
        # except Exception as e:
            for item in getattr(self._nitter_fallback, "last_errors", []) or []:
                self.last_errors.append({"source": "nitter", **item})
            if not any(x.get("source") == "nitter" for x in self.last_errors):
                self.last_errors.append({"source": "nitter", "error": repr(e)})
            raise
