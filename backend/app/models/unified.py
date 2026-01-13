from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class Platform(str, Enum):
    REDDIT = "reddit"
    TWITTER = "twitter"
    HACKERNEWS = "hackernews"

class SocialActor(BaseModel):
    id: str
    username: str
    platform: Platform
    reputation_score: Optional[float] = None

class EntityMatch(BaseModel):
    text: str          # The canonical entity name (e.g. "OpenAI")
    label: str         # ORG, PERSON, etc.
    confidence: float  # 0.0 to 1.0
    original_text: str # What was actually found in text (e.g. "Open AI")
    context: Optional[str] = None # Surrounding text/sentence

class UnifiedPost(BaseModel):
    id: str
    platform: Platform
    content: str
    author: SocialActor
    community_id: Optional[str] = None
    timestamp: datetime
    engagement_score: float = 0.0
    url: str
    
    # For Level 1 & 2
    sentiment: Optional[float] = None
    entities: List[EntityMatch] = [] # Extracted entities with scores

class Community(BaseModel):
    id: str
    name: str  # e.g., "r/openai" or "#openai"
    url: str
    platform: Platform
    subscribers: int = 0
    active_users: int = 0
    relevance_score: float = 0.0  # Calculated by us
    description: Optional[str] = None
    recent_posts: List[UnifiedPost] = []
