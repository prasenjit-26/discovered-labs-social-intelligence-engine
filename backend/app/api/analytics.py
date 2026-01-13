from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any
from datetime import datetime
import asyncio
from textblob import TextBlob
from app.services.analytics.exposure import ExposureService
from app.services.analytics.causation import CausationService
from app.sources.factory import get_reddit_source
from app.models.unified import UnifiedPost, Platform, SocialActor
from app.core.database import supabase

router = APIRouter()
exposure_service = ExposureService()
causation_service = CausationService()
reddit_source = get_reddit_source()

@router.post("/analytics/exposure")
async def get_competitive_exposure(
    target_company: str = Body(..., embed=True),
    competitors: List[str] = Body(..., embed=True)
):
    """
    Level 2 Endpoint:
    Calculates Share of Voice and Sentiment.
    """
    # 1. Fetch data (Demo: Fetch real Reddit data for target)
    
    # We strip domain to get search query
    query = target_company.split('.')[0]
    
    live_posts = []
    try:
        # Fetch generic posts for the sector to get competitor mentions too
        relevant_communities = await reddit_source.search_communities(query)
        top_communities = relevant_communities[:3]
        
        for comm in top_communities:
            comm_posts = await reddit_source.fetch_discussions(comm.id, limit=10)
            live_posts.extend(comm_posts)
            
            # Persist fetched posts to Supabase for analysis usage
            try:
                await asyncio.to_thread(persist_posts, comm_posts, comm.id)
            except Exception as db_err:
                 print(f"Warning: Failed to persist posts for {comm.name}: {db_err}")
            
    except Exception as e:
        print(f"Error fetching data: {e}")
        # Continue with empty or partial data
        pass
    
    # 2. Retrieve ALL relevant data from Supabase for Analysis (Historical + Live)
    db_posts = []
    try:
        # Fetch posts from DB (Async wrapper)
        response = await asyncio.to_thread(
            lambda: supabase.table("posts").select("*").execute()
        )
        
        for row in response.data:
            # Reconstruct UnifiedPost objects
            # Handle timestamp parsing (some ISO strings might differ)
            ts = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
            
            post = UnifiedPost(
                id=row['id'],
                platform=Platform(row['platform']),
                content=row['content'],
                author=SocialActor(
                    id=row['author_id'], 
                    username=row['author_username'], 
                    platform=Platform(row['platform'])
                ),
                community_id=row['community_id'],
                timestamp=ts,
                engagement_score=row['engagement_score'],
                url=row['url']
            )
            db_posts.append(post)
            
        print(f"Loaded {len(db_posts)} posts from DB for analysis.")
        
    except Exception as e:
        print(f"Error reading from DB: {e}")
        # Fallback to just the live posts we fetched
        db_posts = live_posts

    # If DB was empty (first run), use live_posts
    if not db_posts:
        db_posts = live_posts
        
    results = exposure_service.calculate_metrics(db_posts, target_company, competitors)
    return results

def persist_posts(posts: List[UnifiedPost], community_id: str):
    """Helper to persist posts synchronously (run in thread)"""
    for post in posts:
        # Calculate sentiment on the fly if not present
        if post.sentiment is None:
            blob = TextBlob(post.content)
            post.sentiment = blob.sentiment.polarity

        post_data = {
            "id": post.id,
            "platform": post.platform.value,
            "content": post.content,
            "author_id": post.author.id,
            "author_username": post.author.username,
            "community_id": community_id,
            "timestamp": post.timestamp.isoformat(),
            "engagement_score": post.engagement_score,
            "url": post.url,
            "sentiment": post.sentiment
        }
        supabase.table("posts").upsert(post_data).execute()

@router.post("/analytics/causation")
async def get_causation(target_company: str = Body(..., embed=True)):
    """
    Level 3 Endpoint:
    Analyze cross-channel influence.
    """
    # For Level 3 demo, we need multi-platform data.
    # Since we only have Reddit connected really, we will generate some 
    # MOCK data for Twitter to demonstrate the algorithm working.
    
    from datetime import datetime, timedelta
    import random
    
    # Real Reddit posts (or mocks if empty)
    posts = []
    base_time = datetime.now()
    
    # Generate Synthetic Data Pattern: Twitter leads Reddit by 4 hours
    # 1. Create Twitter Spike at T-10h
    for i in range(20):
        posts.append(UnifiedPost(
            id=f"tw_{i}", platform=Platform.TWITTER, content=f"Huge news about {target_company}!",
            author=None, timestamp=base_time - timedelta(hours=10) + timedelta(minutes=random.randint(0, 60)),
            url="", engagement_score=10
        ))
        
    # 2. Create Reddit Spike at T-6h (4 hours later)
    for i in range(30):
        posts.append(UnifiedPost(
            id=f"rd_{i}", platform=Platform.REDDIT, content=f"Did you see the news about {target_company}?",
            author=None, timestamp=base_time - timedelta(hours=6) + timedelta(minutes=random.randint(0, 60)),
            url="", engagement_score=10
        ))
        
    # Run analysis
    result = causation_service.analyze_causation(posts, target_company)
    return result
