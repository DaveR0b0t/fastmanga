"""
Base provider interface for manga sources.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ..core.manga import Manga, Chapter, Page


class BaseProvider(ABC):
    """Abstract base class for manga providers."""
    
    name: str = "base"
    base_url: str = ""
    supports_search: bool = True
    supports_popular: bool = True
    supports_latest: bool = True
    
    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 20,
        **filters: Any
    ) -> List[Manga]:
        """
        Search for manga.
        
        Args:
            query: Search query
            limit: Maximum number of results
            **filters: Additional filters (genre, year, status, etc.)
        
        Returns:
            List of manga results
        """
        pass
    
    @abstractmethod
    async def get_manga(self, manga_id: str) -> Optional[Manga]:
        """
        Get detailed manga information.
        
        Args:
            manga_id: Provider-specific manga ID
        
        Returns:
            Manga object with details
        """
        pass
    
    @abstractmethod
    async def get_chapters(self, manga_id: str) -> List[Chapter]:
        """
        Get chapters for a manga.
        
        Args:
            manga_id: Provider-specific manga ID
        
        Returns:
            List of chapters
        """
        pass
    
    @abstractmethod
    async def get_chapter_pages(self, chapter_id: str) -> List[Page]:
        """
        Get pages for a chapter.
        
        Args:
            chapter_id: Provider-specific chapter ID
        
        Returns:
            List of pages
        """
        pass
    
    async def get_popular(self, limit: int = 20) -> List[Manga]:
        """
        Get popular manga.
        
        Args:
            limit: Maximum number of results
        
        Returns:
            List of popular manga
        """
        if not self.supports_popular:
            raise NotImplementedError(f"{self.name} does not support popular manga")
        return []
    
    async def get_latest(self, limit: int = 20) -> List[Manga]:
        """
        Get latest manga updates.
        
        Args:
            limit: Maximum number of results
        
        Returns:
            List of latest manga
        """
        if not self.supports_latest:
            raise NotImplementedError(f"{self.name} does not support latest manga")
        return []
    
    def _sanitize_id(self, id_str: str) -> str:
        """Sanitize provider ID for use in filenames."""
        return id_str.replace("/", "_").replace("\\", "_")
