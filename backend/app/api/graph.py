from fastapi import APIRouter
from app.services.graph_service import GraphService
from app.services.relationship_extractor import RelationshipExtractor

router = APIRouter()
graph_service = GraphService()
extractor = RelationshipExtractor()

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

@router.post("/graph/analyze_text")
async def analyze_text_for_graph(text: str, domain: str = ""):
    """
    Extracts relationships from text and adds them to the graph.
    """
    relations = await extractor.extract_relations(text)
    for subj, rel, obj, confidence in relations:
        await graph_service.add_relationship(subj, rel, obj, confidence=confidence, company_domain=domain)
    
    return {"extracted": relations, "graph_size": len(graph_service.get_graph_data(domain).get("nodes", []))}
