import httpx
from bs4 import BeautifulSoup
from typing import List
from datetime import datetime

from app.sources.base import SocialSourcePlugin
from app.models.unified import Community, UnifiedPost, Platform, SocialActor


class RedditHtmlScrapePlugin(SocialSourcePlugin):
    """Best-effort HTML scraping using old.reddit.com.

    Important: This is a fallback and should be rate-limited.
    No bypassing of access controls (CAPTCHAs, login walls, etc.).
    """

    def __init__(self):
        self.base_headers = {
            "User-Agent": "social-intel-engine/1.0 (html-fallback)"
        }

    async def search_communities(self, query: str) -> List[Community]:
        url = "https://old.reddit.com/subreddits/search"
        params = {"q": query}

        async with httpx.AsyncClient(headers=self.base_headers, timeout=15) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()

        soup = BeautifulSoup(r.text, "lxml")

        communities: List[Community] = []
        # old.reddit search results: each result row is typically `.search-result` or table rows.
        for a in soup.select("a.search-subreddit-link"):
            href = a.get("href") or ""
            text = (a.text or "").strip()
            if not text.startswith("r/"):
                continue
            name = text.replace("r/", "")
            communities.append(
                Community(
                    id=f"reddit_{name.lower()}",
                    name=f"r/{name}",
                    url=href if href.startswith("http") else f"https://old.reddit.com/r/{name}",
                    platform=Platform.REDDIT,
                    subscribers=0,
                    active_users=0,
                    relevance_score=0.5,
                    description=None,
                )
            )

        return communities

    async def fetch_discussions(self, community_id: str, limit: int = 20) -> List[UnifiedPost]:
        subreddit_name = community_id.replace("reddit_", "")
        url = f"https://old.reddit.com/r/{subreddit_name}/hot/"

        async with httpx.AsyncClient(headers=self.base_headers, timeout=15) as client:
            r = await client.get(url)
            r.raise_for_status()

        soup = BeautifulSoup(r.text, "lxml")

        posts: List[UnifiedPost] = []
        for post in soup.select("div.thing"):
            if len(posts) >= limit:
                break

            post_id = post.get("data-fullname") or post.get("data-permalink") or ""
            title_el = post.select_one("a.title")
            title = (title_el.text or "").strip() if title_el else ""
            permalink = post.get("data-permalink") or (title_el.get("href") if title_el else "") or ""

            author_el = post.select_one("a.author")
            author_name = (author_el.text or "unknown").strip() if author_el else "unknown"

            # old.reddit doesn't expose timestamp reliably without more parsing; use now as fallback
            dt = datetime.now()

            posts.append(
                UnifiedPost(
                    id=f"html_post_{post_id}",
                    platform=Platform.REDDIT,
                    content=title,
                    author=SocialActor(
                        id=f"reddit_user_{author_name}",
                        username=author_name,
                        platform=Platform.REDDIT,
                    ),
                    community_id=community_id,
                    timestamp=dt,
                    engagement_score=0.0,
                    url=permalink if permalink.startswith("http") else f"https://old.reddit.com{permalink}",
                )
            )

        return posts
