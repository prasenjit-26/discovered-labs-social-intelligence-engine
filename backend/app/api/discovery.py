from fastapi import APIRouter, HTTPException
from typing import List, Any, Dict, Optional
import asyncio
from app.models.unified import Community
from app.services.discovery import DiscoveryService
from app.api.graph import graph_service as shared_graph_service
from app.core.database import supabase, get_supabase_client
import time

router = APIRouter()
discovery_service = DiscoveryService(graph_service=shared_graph_service)


async def _get_db_discovery(domain: str) -> Optional[List[Community]]:
    """Load last discovery result for a domain from company_communities mapping."""
    try:
        mapping_resp = await asyncio.to_thread(
            lambda: supabase.table("company_communities")
            .select("community_id,relevance_score")
            .eq("company_domain", domain)
            .order("relevance_score", desc=True)
            .execute()
        )
        mappings = mapping_resp.data or []
        if len(mappings) == 0:
            return None

        ids = [m["community_id"] for m in mappings if m.get("community_id")]
        score_by_id = {m["community_id"]: m.get("relevance_score", 0.0) for m in mappings if m.get("community_id")}

        comm_resp = await asyncio.to_thread(
            lambda: supabase.table("communities").select("*").in_("id", ids).execute()
        )
        comm_rows = comm_resp.data or []
        comm_by_id = {r["id"]: r for r in comm_rows if r.get("id")}

        communities: List[Community] = []
        for cid in ids:
            row = comm_by_id.get(cid)
            if not row:
                continue
            try:
                comm = Community(**row)
                comm.relevance_score = float(score_by_id.get(cid, comm.relevance_score or 0.0))
                communities.append(comm)
            except Exception:
                continue

        return communities if len(communities) > 0 else None
    except Exception:
        return None


async def _upsert_company_communities(domain: str, communities: List[Community]) -> None:
    rows: List[Dict[str, Any]] = []
    for c in communities:
        rows.append(
            {
                "company_domain": domain,
                "community_id": c.id,
                "relevance_score": c.relevance_score,
            }
        )

    if len(rows) == 0:
        return

    def _persist():
        last_err = None
        for attempt in range(3):
            try:
                client = get_supabase_client()

                # Ensure referenced communities exist before writing mapping (FK constraint)
                comm_rows: List[Dict[str, Any]] = []
                for c in communities:
                    comm_rows.append(
                        {
                            "id": c.id,
                            "name": c.name,
                            "url": c.url,
                            "platform": c.platform.value,
                            "subscribers": c.subscribers,
                            "active_users": c.active_users,
                            "description": c.description,
                            "relevance_score": c.relevance_score,
                        }
                    )

                if len(comm_rows) > 0:
                    client.table("communities").upsert(comm_rows).execute()

                client.table("company_communities").upsert(
                    rows,
                    on_conflict="company_domain,community_id",
                ).execute()
                return
            except Exception as e:
                last_err = e
                time.sleep(0.2 * (attempt + 1))
        raise last_err

    await asyncio.to_thread(_persist)

@router.get("/discover", response_model=List[Community])
async def discover_communities(domain: str, refetch: bool = False):
    """
    Level 0 Endpoint:
    Given a domain (e.g. 'openai.com'), discover and rank relevant communities.
    """
    if not domain:
        raise HTTPException(status_code=400, detail="Domain is required")

    try:
        if not refetch:
            cached = await _get_db_discovery(domain)
            if cached is not None and len(cached) > 0:
                return cached

        results = await discovery_service.discover_communities(domain)
        await _upsert_company_communities(domain, results)
        return results
    except Exception as e:
        # In production, log the error properly
        print(f"Discovery error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discover/history")
async def discovery_history():
    """List companies that have already been fetched (cached)."""
    try:
        resp = await asyncio.to_thread(
            lambda: supabase.table("company_communities")
            .select("company_domain,updated_at")
            .order("updated_at", desc=True)
            .execute()
        )
        rows = resp.data or []
        seen = set()
        items = []
        for r in rows:
            d = r.get("company_domain")
            if not d or d in seen:
                continue
            seen.add(d)
            items.append({"company_domain": d, "updated_at": r.get("updated_at")})
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discover/posts")
async def get_company_posts(domain: str, community_limit: int = 5, post_limit: int = 5):
    """Return persisted posts for the company’s top communities (for UI browsing)."""
    if not domain:
        raise HTTPException(status_code=400, detail="Domain is required")

    try:
        mapping_resp = await asyncio.to_thread(
            lambda: supabase.table("company_communities")
            .select("community_id,relevance_score")
            .eq("company_domain", domain)
            .order("relevance_score", desc=True)
            .limit(community_limit)
            .execute()
        )
        mappings = mapping_resp.data or []
        community_ids = [m.get("community_id") for m in mappings if m.get("community_id")]
        if not community_ids:
            return {"items": []}

        comm_resp = await asyncio.to_thread(
            lambda: supabase.table("communities").select("id,name,url").in_("id", community_ids).execute()
        )
        comm_rows = comm_resp.data or []
        comm_by_id = {c["id"]: c for c in comm_rows if c.get("id")}

        posts_resp = await asyncio.to_thread(
            lambda: supabase.table("posts")
            .select("id,community_id,content,url,engagement_score,timestamp")
            .in_("community_id", community_ids)
            .order("engagement_score", desc=True)
            .limit(community_limit * post_limit)
            .execute()
        )
        post_rows = posts_resp.data or []

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for p in post_rows:
            cid = p.get("community_id")
            if not cid:
                continue
            grouped.setdefault(cid, [])
            if len(grouped[cid]) < post_limit:
                grouped[cid].append(p)

        items = []
        for cid in community_ids:
            comm = comm_by_id.get(cid, {"id": cid, "name": cid, "url": None})
            items.append({
                "community": comm,
                "posts": grouped.get(cid, []),
            })

        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discover/cached", response_model=List[Community])
async def get_cached_discovery(domain: str):
    if not domain:
        raise HTTPException(status_code=400, detail="Domain is required")
    cached = await _get_db_discovery(domain)
    if cached is None:
        raise HTTPException(status_code=404, detail="No cached discovery for this domain")
    return cached


@router.post("/discover/refetch", response_model=List[Community])
async def refetch_discovery(domain: str):
    if not domain:
        raise HTTPException(status_code=400, detail="Domain is required")
    try:
        results = await discovery_service.discover_communities(domain)
        await _upsert_company_communities(domain, results)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
