from fastapi import APIRouter, HTTPException
from app.core.database import supabase
from typing import List, Dict, Any

router = APIRouter()

@router.get("/entities")
async def get_entities():
    """
    Level 0: Browse extracted entities.
    Returns list of canonical entities with their labels.
    """
    try:
        response = supabase.table("entities").select("*").order("name").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/entities/{entity_name}")
async def get_entity_details(entity_name: str):
    """
    Level 0: Get details for a specific entity.
    Returns:
    - Variations found (e.g., "Open AI", "openai")
    - Mentions with context and confidence scores
    """
    try:
        # 1. Get Variations
        var_res = supabase.table("entity_variations").select("variation").eq("canonical_name", entity_name).execute()
        variations = [row['variation'] for row in var_res.data]
        
        # 2. Get Mentions (Join with posts could be done here or just return mention context)
        # We limit to 50 recent mentions for performance
        mentions_res = supabase.table("entity_mentions")\
            .select("*")\
            .eq("entity_name", entity_name)\
            .order("created_at", desc=True)\
            .limit(50)\
            .execute()
            
        return {
            "name": entity_name,
            "variations": variations,
            "mentions": mentions_res.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
