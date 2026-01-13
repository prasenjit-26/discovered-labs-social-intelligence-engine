import asyncpraw
from typing import List, Optional
from datetime import datetime
from app.sources.base import SocialSourcePlugin
from app.models.unified import Community, UnifiedPost, Platform, SocialActor
from app.core.config import settings

class RedditPlugin(SocialSourcePlugin):
    def __init__(self):
        # We initialize the Reddit client here.
        # Note: In a real app, you might want to handle missing credentials gracefully.
        self.reddit = asyncpraw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.REDDIT_USER_AGENT
        )

    async def search_communities(self, query: str) -> List[Community]:
        """
        Searches for subreddits matching the query.
        """
        communities = []
        # 'subreddits.search' returns a generator of Subreddit objects
        async for subreddit in self.reddit.subreddits.search(query, limit=20):
            # We need to await attributes that might be lazy-loaded in asyncpraw,
            # but usually basic attributes are available. 
            # Safely fetching data:
            try:
                # asyncpraw often requires explicit load for some attributes if not fetched
                await subreddit.load()
                
                # Calculate a simple business value score (Level 0 requirement)
                # This is a naive implementation; we will improve it in the DiscoveryService.
                subscribers = getattr(subreddit, "subscribers", 0) or 0
                active_users = getattr(subreddit, "accounts_active", 0) or 0
                
                relevance = 0.5 # Placeholder, will be refined by text matching later
                
                community = Community(
                    id=f"reddit_{subreddit.display_name.lower()}",
                    name=subreddit.display_name_prefixed, # e.g. r/openai
                    url=f"https://reddit.com{subreddit.url}",
                    platform=Platform.REDDIT,
                    subscribers=subscribers,
                    active_users=active_users,
                    relevance_score=relevance,
                    description=subreddit.public_description or ""
                )
                communities.append(community)
            except Exception as e:
                print(f"Error processing subreddit {subreddit}: {e}")
                continue
                
        return communities

    async def fetch_discussions(self, community_id: str, limit: int = 20) -> List[UnifiedPost]:
        """
        Fetches 'hot' posts from a specific subreddit.
        community_id expected format: "reddit_subname" -> we extract "subname"
        """
        subreddit_name = community_id.replace("reddit_", "")
        subreddit = await self.reddit.subreddit(subreddit_name)
        
        posts = []
        async for submission in subreddit.hot(limit=limit):
            # Convert timestamp
            dt = datetime.fromtimestamp(submission.created_utc)
            
            author_name = "unknown"
            if submission.author:
                author_name = submission.author.name
            
            post = UnifiedPost(
                id=f"reddit_post_{submission.id}",
                platform=Platform.REDDIT,
                content=f"{submission.title}\n{submission.selftext}",
                author=SocialActor(
                    id=f"reddit_user_{author_name}",
                    username=author_name,
                    platform=Platform.REDDIT
                ),
                community_id=community_id,
                timestamp=dt,
                engagement_score=float(submission.score + submission.num_comments),
                url=f"https://reddit.com{submission.permalink}"
            )
            posts.append(post)
            
        return posts

    async def close(self):
        await self.reddit.close()
