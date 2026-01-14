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
import hashlib

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


def _mock_x_posts(query: str, domain: str, limit: int = 25) -> List[UnifiedPost]:
    now = datetime.utcnow()
    base = (domain or query or "mock").strip().lower().encode("utf-8")
    seed_int = int(hashlib.sha256(base).hexdigest()[:8], 16)

    posts: List[UnifiedPost] = []
    n = max(1, int(limit or 25))

    # Deterministic pseudo-random helper (no global RNG)
    def _mix(x: int) -> int:
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= (x >> 17) & 0xFFFFFFFF
        x ^= (x << 5) & 0xFFFFFFFF
        return x & 0xFFFFFFFF

    # Create 2-4 burst windows within last ~36 hours.
    # Each burst generates 5-10 posts inside a 1-2 hour span.
    burst_count = 2 + (seed_int % 3)  # 2..4
    burst_centers = []
    s = seed_int & 0xFFFFFFFF
    for _ in range(burst_count):
        s = _mix(s)
        # 1..36 hours ago
        burst_centers.append(1 + (s % 36))

    burst_centers = sorted(list(dict.fromkeys(burst_centers)))

    i = 0
    for b_idx, center_hours_ago in enumerate(burst_centers):
        if i >= n:
            break

        s = _mix(s + b_idx + seed_int)
        burst_size = 5 + (s % 6)  # 5..10
        burst_span_hours = 1 + ((s >> 8) % 2)  # 1..2

        for j in range(burst_size):
            if i >= n:
                break

            # Spread within the burst window by minutes
            s = _mix(s + j + i)
            minute_offset = int(s % 60)
            hour_offset = int((s >> 16) % burst_span_hours)
            ts = now - timedelta(hours=int(center_hours_ago + hour_offset), minutes=minute_offset)

            uid = (seed_int + i) % 10_000_000
            content = (
                f"{query} BREAKING burst#{b_idx} #{uid}: "
                f"{query} spike in mentions, discussion accelerating."
            )

            posts.append(
                UnifiedPost(
                    id=f"mock_x_{seed_int}_{b_idx}_{i}",
                    platform=Platform.TWITTER,
                    content=content,
                    author=SocialActor(
                        id=f"mock_user_{(seed_int + i) % 9999}",
                        username=f"mock_user_{(seed_int + i) % 9999}",
                        platform=Platform.TWITTER,
                    ),
                    community_id=None,
                    timestamp=ts,
                    engagement_score=float(150 + (uid % 500)),
                    url=f"https://x.com/mock/status/{seed_int}{b_idx}{i}",
                    sentiment=None,
                )
            )
            i += 1

    # Fill remainder with sparse background noise across last 72 hours
    while i < n:
        s = _mix(s + i + seed_int)
        hours_ago = 1 + int(s % 72)
        minute_offset = int((s >> 8) % 60)
        ts = now - timedelta(hours=hours_ago, minutes=minute_offset)
        uid = (seed_int + i) % 10_000_000
        content = f"{query} update #{uid}: ongoing chatter and reactions."
        posts.append(
            UnifiedPost(
                id=f"mock_x_{seed_int}_noise_{i}",
                platform=Platform.TWITTER,
                content=content,
                author=SocialActor(
                    id=f"mock_user_{(seed_int + i) % 9999}",
                    username=f"mock_user_{(seed_int + i) % 9999}",
                    platform=Platform.TWITTER,
                ),
                community_id=None,
                timestamp=ts,
                engagement_score=float(30 + (uid % 120)),
                url=f"https://x.com/mock/status/{seed_int}n{i}",
                sentiment=None,
            )
        )
        i += 1

    # Sort newest -> oldest for nicer previews
    posts.sort(key=lambda p: p.timestamp, reverse=True)
    return posts


def _mock_hn_posts_from_x(
    x_posts: List[UnifiedPost],
    query: str,
    domain: str,
    lag_hours: int = 6,
    limit: int = 25,
) -> List[UnifiedPost]:
    """Generate HN posts that follow X by a fixed lag to create clear correlation."""
    base = (domain or query or "mock").strip().lower().encode("utf-8")
    seed_int = int(hashlib.sha256(base).hexdigest()[:8], 16)
    out: List[UnifiedPost] = []

    for i, xp in enumerate((x_posts or [])[: max(1, int(limit or 25))]):
        ts = xp.timestamp + timedelta(hours=int(lag_hours))
        out.append(
            UnifiedPost(
                id=f"mock_hn_{seed_int}_{i}",
                platform=Platform.HACKERNEWS,
                content=f"HN: {query} discussion follows X wave #{i}. {query} (mock)",
                author=SocialActor(
                    id=f"mock_hn_user_{(seed_int + i) % 9999}",
                    username=f"mock_hn_user_{(seed_int + i) % 9999}",
                    platform=Platform.HACKERNEWS,
                ),
                community_id=None,
                timestamp=ts,
                engagement_score=float(80 + ((seed_int + i) % 300)),
                url=f"https://news.ycombinator.com/item?id={seed_int}{i}",
                sentiment=None,
            )
        )

    out.sort(key=lambda p: p.timestamp, reverse=True)
    return out


def _mock_reddit_posts_from_x(
    x_posts: List[UnifiedPost],
    query: str,
    domain: str,
    lag_hours: int = 12,
    limit: int = 20,
) -> List[UnifiedPost]:
    """Generate Reddit posts that follow X by a fixed lag to create clear correlation."""
    base = (domain or query or "mock").strip().lower().encode("utf-8")
    seed_int = int(hashlib.sha256(base).hexdigest()[8:16], 16)
    out: List[UnifiedPost] = []

    for i, xp in enumerate((x_posts or [])[: max(1, int(limit or 20))]):
        ts = xp.timestamp + timedelta(hours=int(lag_hours))
        out.append(
            UnifiedPost(
                id=f"mock_reddit_{seed_int}_{i}",
                platform=Platform.REDDIT,
                content=f"Reddit: reacting to {query} trend from X wave #{i}. {query} (mock)",
                author=SocialActor(
                    id=f"mock_reddit_user_{(seed_int + i) % 9999}",
                    username=f"mock_reddit_user_{(seed_int + i) % 9999}",
                    platform=Platform.REDDIT,
                ),
                community_id=None,
                timestamp=ts,
                engagement_score=float(120 + ((seed_int + i) % 400)),
                url=f"https://reddit.com/r/mock/comments/{seed_int}{i}/{query}",
                sentiment=None,
            )
        )

    out.sort(key=lambda p: p.timestamp, reverse=True)
    return out


@router.post("/analytics/level3/ingest")
async def ingest_level3_posts(
    domain: str = Body(..., embed=True),
    limit_x: int = Body(25, embed=True),
    limit_hn: int = Body(25, embed=True),
    use_mock_x: bool = Body(False, embed=True),
):
    """Level 3: Fetch X (via Nitter/official) + HackerNews posts for a domain and persist into posts table."""
    if not domain:
        raise HTTPException(status_code=400, detail="domain is required")

    query = _query_from_domain(domain)
    if not query:
        raise HTTPException(status_code=400, detail="Invalid domain")

    x_errors = []
    if use_mock_x:
        x_posts = _mock_x_posts(query=query, domain=domain, limit=int(limit_x or 25))
        # Also generate aligned HN + Reddit signals within the same time window so causation
        # has cross-platform overlap when cutoff is applied.
        mock_hn_posts = _mock_hn_posts_from_x(
            x_posts=x_posts,
            query=query,
            domain=domain,
            lag_hours=6,
            limit=int(limit_hn or 25),
        )
        mock_reddit_posts = _mock_reddit_posts_from_x(
            x_posts=x_posts,
            query=query,
            domain=domain,
            lag_hours=12,
            limit=20,
        )
    else:
        try:
            x_posts = await x_source.fetch_posts(query, limit=int(limit_x or 25))
        except Exception as e:
            print(f"X ingest warning: {e}")
            x_posts = []
            try:
                x_errors = getattr(x_source, "last_errors", []) or []
            except Exception:
                x_errors = []

    if use_mock_x:
        hn_posts = mock_hn_posts
        reddit_posts = mock_reddit_posts
    else:
        reddit_posts = []
        try:
            hn_posts = await hn_source.fetch_posts(query, limit=int(limit_hn or 25))
        except Exception as e:
            print(f"HN ingest warning: {e}")
            hn_posts = []

    def _persist():
        persist_generic_posts(x_posts, company_domain=domain)
        persist_generic_posts(hn_posts, company_domain=domain)
        if reddit_posts:
            persist_generic_posts(reddit_posts, company_domain=domain)

    await asyncio.to_thread(_persist)

    # Diagnostics: confirm what's in DB for this company_domain
    def _platform_counts_company() -> Dict[str, int]:
        try:
            resp = (
                supabase.table("posts")
                .select("platform")
                .eq("company_domain", domain)
                .limit(1000)
                .execute()
            )
            rows = resp.data or []
            counts: Dict[str, int] = {}
            for r in rows:
                p = (r.get("platform") or "unknown")
                counts[p] = counts.get(p, 0) + 1
            return counts
        except Exception:
            return {}

    persisted_platform_counts = await asyncio.to_thread(_platform_counts_company)

    return {
        "domain": domain,
        "query": query,
        "use_mock_x": bool(use_mock_x),
        "ingested": {
            "x": len(x_posts),
            "hackernews": len(hn_posts),
            "reddit": len(reddit_posts),
        },
        "samples": {
            "x": [
                {
                    "id": p.id,
                    "platform": p.platform.value,
                    "timestamp": p.timestamp.isoformat() if getattr(p, "timestamp", None) else None,
                    "content": (p.content or "")[:140],
                }
                for p in x_posts[:3]
            ],
            "hackernews": [
                {
                    "id": p.id,
                    "platform": p.platform.value,
                    "timestamp": p.timestamp.isoformat() if getattr(p, "timestamp", None) else None,
                    "content": (p.content or "")[:140],
                }
                for p in hn_posts[:3]
            ],
            "reddit": [
                {
                    "id": p.id,
                    "platform": p.platform.value,
                    "timestamp": p.timestamp.isoformat() if getattr(p, "timestamp", None) else None,
                    "content": (p.content or "")[:140],
                }
                for p in reddit_posts[:3]
            ],
        },
        "persisted_platform_counts": persisted_platform_counts,
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
            .gte("timestamp", cutoff_iso)
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
        k = p.platform.value if getattr(p, "platform", None) is not None else "unknown"
        platform_counts_all[k] = platform_counts_all.get(k, 0) + 1

    filtered = [p for p in db_posts if _matches(p)]

    platform_counts_filtered: Dict[str, int] = {}
    for p in filtered:
        k = p.platform.value if getattr(p, "platform", None) is not None else "unknown"
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
