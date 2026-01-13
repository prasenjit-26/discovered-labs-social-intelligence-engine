from typing import List
from datetime import datetime, timezone
import asyncio
import os

from app.models.unified import UnifiedPost, Platform, SocialActor
from app.sources.content_base import ContentSourcePlugin
import ssl
import certifi

class SnscrapeXSource(ContentSourcePlugin):
    async def fetch_posts(self, query: str, limit: int = 50) -> List[UnifiedPost]:
        q = (query or "").strip()
        if not q:
            return []
        import snscrape.modules.twitter as sntwitter
        def _scrape_sync() -> List[UnifiedPost]:
            # macOS Python installs sometimes lack a valid CA bundle, causing snscrape/requests
            # to fail with SSL_CERTIFICATE_VERIFY_FAILED. Point requests at certifi's CA bundle.
            try:
                import certifi

                ca = certifi.where()
                os.environ.setdefault("SSL_CERT_FILE", ca)
                os.environ.setdefault("REQUESTS_CA_BUNDLE", ca)
            except Exception:
                pass

            import snscrape.modules.twitter as sntwitter

            items: List[UnifiedPost] = []
            scraper = sntwitter.TwitterSearchScraper(q)
            for tweet in scraper("chatgpt").get_items():
                print(tweet.date, tweet.user.username, tweet.content)
                break
            for i, tweet in enumerate(scraper.get_items()):
                if limit and i >= int(limit):
                    break

                tid = getattr(tweet, "id", None)
                content = getattr(tweet, "rawContent", None) or getattr(tweet, "content", None) or ""
                date = getattr(tweet, "date", None)
                user = getattr(tweet, "user", None)

                if not tid or not content:
                    continue

                ts = date
                if ts is None:
                    ts = datetime.now(timezone.utc)
                elif isinstance(ts, datetime) and ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)

                username = None
                author_id = None
                if user is not None:
                    username = getattr(user, "username", None) or getattr(user, "displayname", None)
                    author_id = getattr(user, "id", None)

                url = getattr(tweet, "url", None) or ""

                like_count = getattr(tweet, "likeCount", 0) or 0
                retweet_count = getattr(tweet, "retweetCount", 0) or 0
                reply_count = getattr(tweet, "replyCount", 0) or 0
                quote_count = getattr(tweet, "quoteCount", 0) or 0

                engagement = float(int(like_count) + 2 * int(retweet_count) + int(reply_count) + int(quote_count))

                items.append(
                    UnifiedPost(
                        id=f"x_{tid}",
                        platform=Platform.TWITTER,
                        content=content,
                        author=SocialActor(
                            id=f"x_{author_id or (username or 'unknown')}",
                            username=(username or "unknown"),
                            platform=Platform.TWITTER,
                        ),
                        community_id=None,
                        timestamp=ts,
                        engagement_score=engagement,
                        url=url,
                    )
                )

            return items

        return await asyncio.to_thread(_scrape_sync)
