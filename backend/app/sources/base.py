from abc import ABC, abstractmethod
from typing import List
from app.models.unified import Community, UnifiedPost

class SocialSourcePlugin(ABC):
    """
    Abstract Base Class that all social media plugins must implement.
    This ensures our system doesn't care if data comes from Reddit or X.
    """
    
    @abstractmethod
    async def search_communities(self, query: str) -> List[Community]:
        """Find relevant communities based on a keyword."""
        pass

    @abstractmethod
    async def fetch_discussions(self, community_id: str, limit: int = 100) -> List[UnifiedPost]:
        """Fetch recent posts/discussions from a specific community."""
        pass
