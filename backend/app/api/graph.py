from fastapi import APIRouter
from app.services.graph_service import GraphService

router = APIRouter()
graph_service = GraphService()

@router.get("/graph")
async def get_knowledge_graph(domain: str = ""):
    """
    Level 1 Endpoint:
    Returns the node-link data structure for visualization.
    """
    if domain:
        await graph_service.load_graph(domain)
    return graph_service.get_graph_data(domain)

@router.get("/graph/{entity}")
async def get_entity_graph(entity: str, domain: str = ""):
    """
    Returns the subgraph for a specific entity (neighbors).
    """
    if domain:
        await graph_service.load_graph(domain)
    return graph_service.get_entity_subgraph(entity, domain)

