from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any
from datetime import datetime, timedelta
import asyncio
from textblob import TextBlob
from app.services.analytics.exposure import ExposureService
from app.services.analytics.causation import CausationService
from app.models.unified import UnifiedPost, Platform, SocialActor
from app.core.database import supabase
from app.sources.x.factory import get_x_source
from app.sources.hackernews.factory import get_hackernews_source

router = APIRouter()
exposure_service = ExposureService()
causation_service = CausationService()

x_source = get_x_source()
hn_source = get_hackernews_source()


def _query_from_domain(domain: str) -> str:
    d = (domain or "").strip().lower()
    if not d:
        return ""
    return d.split(".")[0]

@router.post("/analytics/exposure")
async def get_competitive_exposure(
    target_company: str = Body(..., embed=True),
    competitors: List[str] = Body(..., embed=True),
    community_limit: int = Body(10, embed=True),
    days: int = Body(14, embed=True),
):
    """
    Level 2 Endpoint:
    Calculates Share of Voice and Sentiment.
    """
    if not target_company:
        raise HTTPException(status_code=400, detail="target_company is required")

    # 1) Resolve discovered communities for the company
    mapping_resp = await asyncio.to_thread(
        lambda: supabase.table("company_communities")
        .select("community_id,relevance_score")
        .eq("company_domain", target_company)
        .order("relevance_score", desc=True)
        .limit(community_limit)
        .execute()
    )
    mappings = mapping_resp.data or []
    community_ids = [m.get("community_id") for m in mappings if m.get("community_id")]
    if not community_ids:
        return {"share_of_voice": [], "sentiment": {}, "co_mentions": [], "anomalies": [], "total_posts": 0}

    comm_resp = await asyncio.to_thread(
        lambda: supabase.table("communities").select("id,name,url").in_("id", community_ids).execute()
    )
    comm_rows = comm_resp.data or []
    community_meta: Dict[str, Dict[str, Any]] = {c["id"]: c for c in comm_rows if c.get("id")}

    # 2) Fetch persisted posts for those communities in a time window
    now = datetime.utcnow()
    cutoff = now - timedelta(days=max(1, int(days or 14)))
    cutoff_iso = cutoff.isoformat()

    posts_resp = await asyncio.to_thread(
        lambda: supabase.table("posts")
        .select("*")
        .in_("community_id", community_ids)
        .gte("timestamp", cutoff_iso)
        .execute()
    )
    rows = posts_resp.data or []

    db_posts: List[UnifiedPost] = []
    for row in rows:
        try:
            ts = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
            post = UnifiedPost(
                id=row['id'],
                platform=Platform(row['platform']),
                content=row['content'],
                author=SocialActor(
                    id=row.get('author_id'),
                    username=row.get('author_username'),
                    platform=Platform(row['platform'])
                ) if row.get('author_id') else None,
                community_id=row['community_id'],
                timestamp=ts,
                engagement_score=row.get('engagement_score'),
                url=row.get('url'),
                sentiment=row.get('sentiment'),
            )
            db_posts.append(post)
        except Exception:
            continue

    results = exposure_service.calculate_metrics(db_posts, target_company, competitors, community_meta=community_meta)
    results["company"] = target_company
    results["competitors"] = competitors
    results["communities"] = [{"id": cid, **(community_meta.get(cid, {}))} for cid in community_ids]
    results["window"] = {"days": int(days or 14), "cutoff": cutoff_iso}
    return results

def persist_posts(posts: List[UnifiedPost], community_id: str):
    """Helper to persist posts synchronously (run in thread)"""
    for post in posts:
        # Calculate sentiment on the fly if not present
        if post.sentiment is None:
            blob = TextBlob(post.content)
            post.sentiment = blob.sentiment.polarity

        author_id = post.author.id if getattr(post, "author", None) is not None else None
        author_username = post.author.username if getattr(post, "author", None) is not None else None

        post_data = {
            "id": post.id,
            "platform": post.platform.value,
            "content": post.content,
            "author_id": author_id,
            "author_username": author_username,
            "community_id": community_id,
            "timestamp": post.timestamp.isoformat(),
            "engagement_score": post.engagement_score,
            "url": post.url,
            "sentiment": post.sentiment
        }
        supabase.table("posts").upsert(post_data).execute()


def persist_generic_posts(posts: List[UnifiedPost], company_domain: str = ""):
    """Persist non-community posts (X/HN) into posts table."""
    for post in posts:
        if post.sentiment is None:
            try:
                blob = TextBlob(post.content)
                post.sentiment = blob.sentiment.polarity
            except Exception:
                post.sentiment = None

        author_id = post.author.id if getattr(post, "author", None) is not None else None
        author_username = post.author.username if getattr(post, "author", None) is not None else None

        post_data = {
            "id": post.id,
            "company_domain": company_domain or None,
            "platform": post.platform.value,
            "content": post.content,
            "author_id": author_id,
            "author_username": author_username,
            "community_id": None,
            "timestamp": post.timestamp.isoformat(),
            "engagement_score": post.engagement_score,
            "url": post.url,
            "sentiment": post.sentiment,
        }
        try:
            supabase.table("posts").upsert(post_data).execute()
        except Exception:
            print("Failed to persist post:", post_data)


@router.post("/analytics/level3/ingest")
async def ingest_level3_posts(
    domain: str = Body(..., embed=True),
    limit_x: int = Body(25, embed=True),
    limit_hn: int = Body(25, embed=True),
):
    """Level 3: Fetch X (via Nitter/official) + HackerNews posts for a domain and persist into posts table."""
    if not domain:
        raise HTTPException(status_code=400, detail="domain is required")

    query = _query_from_domain(domain)
    if not query:
        raise HTTPException(status_code=400, detail="Invalid domain")

    x_errors = []
    try:
        x_posts: List[UnifiedPost] = await x_source.fetch_posts(query, limit=int(limit_x or 25))
    except Exception as e:
        print(f"X ingest warning: {e}")
        x_posts = []
        try:
            x_errors = getattr(x_source, "last_errors", []) or []
        except Exception:
            x_errors = []

    try:
        hn_posts: List[UnifiedPost] = await hn_source.fetch_posts(query, limit=int(limit_hn or 25))
    except Exception as e:
        print(f"HN ingest warning: {e}")
        hn_posts = []

    def _persist():
        persist_generic_posts(x_posts, company_domain=domain)
        persist_generic_posts(hn_posts, company_domain=domain)

    await asyncio.to_thread(_persist)
    return {
        "domain": domain,
        "query": query,
        "ingested": {
            "x": len(x_posts),
            "hackernews": len(hn_posts),
        },
        "errors": {
            "x": x_errors,
        },
    }

@router.post("/analytics/causation")
async def get_causation(
    target_company: str = Body(..., embed=True),
    days: int = Body(14, embed=True),
):
    """
    Level 3 Endpoint:
    Analyze cross-channel influence.
    """
    if not target_company:
        raise HTTPException(status_code=400, detail="target_company is required")

    query = _query_from_domain(target_company)
    now = datetime.utcnow()
    cutoff = now - timedelta(days=max(1, int(days or 14)))
    cutoff_iso = cutoff.isoformat()

    def _fetch_posts_company():
        return (
            supabase.table("posts")
            .select("*")
            # .gte("timestamp", cutoff_iso)
            .eq("company_domain", target_company)
            .execute()
        )

    try:
        posts_resp = await asyncio.to_thread(_fetch_posts_company)
        rows = posts_resp.data or []
    except Exception:
        rows = []

    db_posts: List[UnifiedPost] = []
    for row in rows:
        try:
            ts = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
            plat = Platform(row['platform'])

            post = UnifiedPost(
                id=row['id'],
                platform=plat,
                content=row.get('content') or "",
                author=SocialActor(
                    id=row.get('author_id'),
                    username=row.get('author_username'),
                    platform=plat,
                ) if row.get('author_id') else None,
                community_id=row.get('community_id'),
                timestamp=ts,
                engagement_score=row.get('engagement_score') or 0.0,
                url=row.get('url') or "",
                sentiment=row.get('sentiment'),
            )
            db_posts.append(post)
        except Exception:
            continue

    # Filter to posts that mention the company (simple alias matching)
    needle = query.lower() if query else target_company.lower()
    def _matches(p: UnifiedPost) -> bool:
        if not needle:
            return False
        content = (p.content or "").lower()
        url = (p.url or "").lower()
        return (needle in content) or (needle in url)

    platform_counts_all: Dict[str, int] = {}
    for p in db_posts:
        k = str(p.platform)
        platform_counts_all[k] = platform_counts_all.get(k, 0) + 1

    filtered = [p for p in db_posts if _matches(p)]

    platform_counts_filtered: Dict[str, int] = {}
    for p in filtered:
        k = str(p.platform)
        platform_counts_filtered[k] = platform_counts_filtered.get(k, 0) + 1

    result = causation_service.analyze_causation(filtered, query or target_company)
    result["window"] = {"days": int(days or 14), "cutoff": cutoff_iso}
    result["total_posts_scanned"] = len(db_posts)
    result["posts_used"] = len(filtered)
    result["needle"] = needle
    result["platform_counts_all"] = platform_counts_all
    result["platform_counts_filtered"] = platform_counts_filtered
    result["posts_preview"] = [
        {
            "id": p.id,
            "platform": p.platform.value,
            "timestamp": p.timestamp.isoformat() if getattr(p, "timestamp", None) else None,
            "content": (p.content or "")[:280],
            "url": p.url,
        }
        for p in filtered[:25]
    ]
    return result
