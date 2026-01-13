from typing import List, Optional, Dict, Any

from app.models.unified import UnifiedPost
from app.sources.content_base import ContentSourcePlugin
from app.sources.x.nitter import NitterXSource
from app.core.config import settings


class FallbackXSource(ContentSourcePlugin):
    def __init__(self, base_urls: Optional[List[str]] = None):
        if base_urls is None:
            raw = getattr(settings, "NITTER_FALLBACK_URLS", "") or ""
            base_urls = [x.strip() for x in raw.split(",") if x.strip()]

        primary = getattr(settings, "NITTER_BASE_URL", "https://nitter.net")

        # If env var is empty/invalid, fall back to a built-in list of public instances.
        if not base_urls:
            base_urls = [
                primary,
                "https://nitter.net",
                "https://nitter.poast.org",
                "https://nitter.privacydev.net",
            ]
        else:
            # Always try primary first (if set) even when fallbacks are provided.
            if primary and primary not in base_urls:
                base_urls = [primary] + base_urls

        self.base_urls = [u.rstrip("/") for u in base_urls if u]

    async def fetch_posts(self, query: str, limit: int = 50) -> List[UnifiedPost]:
        last_err: Optional[Exception] = None
        self.last_errors: List[Dict[str, Any]] = []
        for base in self.base_urls:
            try:
                src = NitterXSource(base_url=base)
                posts = await src.fetch_posts(query, limit=limit)
                if posts:
                    return posts
            except Exception as e:
                last_err = e
                self.last_errors.append({"base_url": base, "error": repr(e)})
                continue
        if last_err is not None:
            raise last_err
        return []
