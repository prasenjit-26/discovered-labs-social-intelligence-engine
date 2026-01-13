from abc import ABC, abstractmethod
from typing import List
from app.models.unified import UnifiedPost


class ContentSourcePlugin(ABC):
    @abstractmethod
    async def fetch_posts(self, query: str, limit: int = 50) -> List[UnifiedPost]:
        pass
