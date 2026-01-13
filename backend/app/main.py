from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings

from app.api import discovery, graph, analytics, entities
from app.services.graph_service import GraphService # Import to access the singleton if we used one, but here we depend on the router's service instance?
# Actually, the router instantiates its own service. This is a pattern issue.
# For simplicity in this codebase, we'll fix the GraphService instantiation pattern to be a singleton or shared.
# But looking at app/api/graph.py, it instantiates `graph_service = GraphService()`.
# We should probably expose that instance or create a dependency.

# Let's import the instance from api.graph for now to initialize it.
from app.api.graph import graph_service
from app.api.discovery import discovery_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load Graph
    print("Initializing Graph Data...")
    await graph_service.load_graph()
    
    print("Initializing Discovery Service...")
    await discovery_service.initialize()
    
    yield
    # Shutdown
    pass

app = FastAPI(
    title="Social Intelligence Engine",
    description="Discovered Labs Assignment API",
    version="1.0.0",
    lifespan=lifespan
)

# Allow Frontend to communicate with Backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, verify this is safe or specify exact domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(discovery.router, prefix="/api/v1", tags=["discovery"])
app.include_router(graph.router, prefix="/api/v1", tags=["graph"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
app.include_router(entities.router, prefix="/api/v1", tags=["entities"])

@app.get("/")
async def root():
    return {"message": "Social Intelligence Engine is running", "docs": "/docs"}

# We will add routes here later
