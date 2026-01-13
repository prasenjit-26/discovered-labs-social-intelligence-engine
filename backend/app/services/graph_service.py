import networkx as nx
from typing import List, Dict, Any
import asyncio
from app.core.database import supabase, get_supabase_client

class GraphService:
    def __init__(self):
        # In-memory graphs keyed by company_domain for fast traversal/analysis
        self.graphs: Dict[str, nx.DiGraph] = {}
        # We don't load from DB here anymore to avoid blocking startup
        # Call load_graph() explicitly during app startup

    def _get_graph(self, company_domain: str) -> nx.DiGraph:
        key = company_domain or "__all__"
        if key not in self.graphs:
            self.graphs[key] = nx.DiGraph()
        return self.graphs[key]

    async def load_graph(self, company_domain: str = ""):
        """Load relationships for a company_domain (or all if blank) from Supabase into memory asynchronously"""
        try:
            # Run blocking DB call in a thread
            def _fetch():
                q = supabase.table("relationships").select("*")
                if company_domain:
                    q = q.eq("company_domain", company_domain)
                return q.execute()

            response = await asyncio.to_thread(_fetch)

            g = self._get_graph(company_domain)
            g.clear()

            for row in response.data:
                g.add_node(row['source'])
                g.add_node(row['target'])
                g.add_edge(row['source'], row['target'], relation=row['relation'])
            print(f"Loaded {len(g.edges())} relationships from DB.")
        except Exception as e:
            print(f"Warning: Could not load graph from DB: {e}")

    async def add_relationship(self, source: str, relation: str, target: str, confidence: float = 1.0, company_domain: str = ""):
        """
        Adds an edge to the graph and persists to DB asynchronously.
        """
        # Update Memory (CPU bound, fast enough to keep in main thread usually, but let's be safe)
        g = self._get_graph(company_domain)
        g.add_node(source)
        g.add_node(target)
        g.add_edge(source, target, relation=relation)

        # Update DB in background thread
        await asyncio.to_thread(self._persist_relationship, company_domain, source, relation, target, confidence)

    def _persist_relationship(self, company_domain, source, relation, target, confidence):
        try:
            client = get_supabase_client()
            # Upsert Entities first
            entities_data = [
                {"name": source, "label": "UNKNOWN"}, 
                {"name": target, "label": "UNKNOWN"}
            ]
            client.table("entities").upsert(entities_data, ignore_duplicates=True).execute()

            # Upsert Relationship
            edge_data = {
                "company_domain": company_domain or "",
                "source": source,
                "target": target,
                "relation": relation,
                "confidence": confidence
            }
            client.table("relationships").upsert(edge_data, on_conflict="company_domain,source,target,relation").execute()
            
        except Exception as e:
            print(f"Error persisting relationship {source}-{relation}->{target}: {e}")

    def get_graph_data(self, company_domain: str = "") -> Dict[str, Any]:
        """
        Returns JSON formatted for a frontend library like react-force-graph.
        Format: { "nodes": [{"id": "OpenAI"}], "links": [{"source": "Elon", "target": "OpenAI"}] }
        """
        g = self._get_graph(company_domain)
        nodes = [{"id": n, "val": g.degree(n)} for n in g.nodes()]
        links = [{"source": u, "target": v, "name": d['relation']} for u, v, d in g.edges(data=True)]
        
        return {"nodes": nodes, "links": links}

    def get_entity_subgraph(self, entity: str, company_domain: str = "") -> Dict[str, Any]:
        """Returns the immediate neighborhood of an entity."""
        g = self._get_graph(company_domain)
        if entity not in g:
            return {"nodes": [], "links": []}
            
        # Get neighbors (successors and predecessors)
        successors = list(g.successors(entity))
        predecessors = list(g.predecessors(entity))
        
        nodes_list = list(set([entity] + successors + predecessors))
        subgraph = g.subgraph(nodes_list)
        
        nodes = [{"id": n, "val": g.degree(n)} for n in subgraph.nodes()]
        links = [{"source": u, "target": v, "name": d['relation']} for u, v, d in subgraph.edges(data=True)]
        
        return {"nodes": nodes, "links": links}
