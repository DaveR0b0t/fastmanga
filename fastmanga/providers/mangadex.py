"""MangaDex provider implementation with offline-friendly mock fallback."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import copy

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None

from .base import BaseProvider
from ..core.manga import Chapter, Manga, MangaStatus, Page


class MangaDexProvider(BaseProvider):
    """MangaDex API provider with predictable fallback data for local use."""

    name = "mangadex"
    base_url = "https://api.mangadex.org"

    def __init__(self, language: str = "en", data_saver: bool = False):
        self.language = language
        self.data_saver = data_saver
        self.client = httpx.AsyncClient(timeout=30.0) if HTTPX_AVAILABLE else None
        self._init_mock_data()

    def _init_mock_data(self) -> None:
        self.mock_manga = {
            "one-piece": Manga(
                id="one-piece",
                title="One Piece",
                alt_titles=["OP"],
                description="A story about pirates and the quest for the One Piece treasure.",
                author="Oda Eiichiro",
                artist="Oda Eiichiro",
                genres=["Action", "Adventure", "Comedy"],
                tags=["Pirates", "Shounen"],
                status=MangaStatus.ONGOING,
                year=1997,
                provider=self.name,
                cover_url="https://example.com/onepiece.jpg",
            ),
            "naruto": Manga(
                id="naruto",
                title="Naruto",
                alt_titles=["NARUTO"],
                description="A young ninja's quest to become Hokage.",
                author="Kishimoto Masashi",
                artist="Kishimoto Masashi",
                genres=["Action", "Adventure"],
                tags=["Ninja", "Shounen"],
                status=MangaStatus.COMPLETED,
                year=1999,
                provider=self.name,
                cover_url="https://example.com/naruto.jpg",
            ),
            "berserk": Manga(
                id="berserk",
                title="Berserk",
                alt_titles=["ベルセルク"],
                description="Dark fantasy story following Guts, the Black Swordsman.",
                author="Miura Kentarou",
                artist="Miura Kentarou",
                genres=["Action", "Adventure", "Fantasy", "Horror"],
                tags=["Dark Fantasy", "Seinen"],
                status=MangaStatus.HIATUS,
                year=1989,
                provider=self.name,
                cover_url="https://example.com/berserk.jpg",
            ),
        }

        self.mock_chapters: Dict[str, List[Chapter]] = {}
        for manga_id in self.mock_manga:
            chapters: List[Chapter] = []
            count = 100 if manga_id == "naruto" else 50
            for i in range(1, count + 1):
                chapters.append(
                    Chapter(
                        id=f"{manga_id}-ch-{i}",
                        manga_id=manga_id,
                        number=float(i),
                        title=f"Chapter {i}",
                        volume=str((i - 1) // 10 + 1),
                        language=self.language,
                        pages_count=20,
                        scanlation_group="Mock Scanlations",
                        publish_date=datetime(2020, 1, 1),
                        provider=self.name,
                    )
                )
            self.mock_chapters[manga_id] = chapters

    def _clone_mock_manga(self, manga: Manga) -> Manga:
        return copy.deepcopy(manga)

    def _clone_mock_chapters(self, manga_id: str) -> List[Chapter]:
        return copy.deepcopy(self.mock_chapters.get(manga_id, []))

    def _search_mock_data(self, query: str, limit: int) -> List[Manga]:
        q = query.lower().strip()
        results: List[Manga] = []
        for manga in self.mock_manga.values():
            fields = [manga.title, *(manga.alt_titles or []), manga.author or ""]
            if any(q in field.lower() for field in fields if field):
                results.append(self._clone_mock_manga(manga))
        return results[:limit]

    async def search(self, query: str, limit: int = 20, **filters: Any) -> List[Manga]:
        if not HTTPX_AVAILABLE or self.client is None:
            return self._search_mock_data(query, limit)
        try:
            params = {
                "title": query,
                "limit": limit,
                "includes[]": ["cover_art", "author", "artist"],
                "contentRating[]": ["safe", "suggestive", "erotica"],
            }
            response = await self.client.get(f"{self.base_url}/manga", params=params)
            response.raise_for_status()
            data = response.json()
            results = []
            for item in data.get("data", []):
                manga = self._parse_manga(item)
                if manga is not None:
                    results.append(manga)
            return results
        except Exception:
            return self._search_mock_data(query, limit)

    async def get_manga(self, manga_id: str) -> Optional[Manga]:
        if not HTTPX_AVAILABLE or self.client is None:
            manga = self.mock_manga.get(manga_id)
            return self._clone_mock_manga(manga) if manga else None
        try:
            response = await self.client.get(
                f"{self.base_url}/manga/{manga_id}",
                params={"includes[]": ["cover_art", "author", "artist"]},
            )
            response.raise_for_status()
            data = response.json()
            return self._parse_manga(data["data"])
        except Exception:
            manga = self.mock_manga.get(manga_id)
            return self._clone_mock_manga(manga) if manga else None

    async def get_chapters(self, manga_id: str) -> List[Chapter]:
        if not HTTPX_AVAILABLE or self.client is None:
            return self._clone_mock_chapters(manga_id)
        chapters: List[Chapter] = []
        offset = 0
        limit = 100
        try:
            while True:
                params = {
                    "manga": manga_id,
                    "translatedLanguage[]": [self.language],
                    "limit": limit,
                    "offset": offset,
                    "order[chapter]": "asc",
                    "includes[]": ["scanlation_group"],
                }
                response = await self.client.get(f"{self.base_url}/chapter", params=params)
                response.raise_for_status()
                data = response.json()
                for item in data.get("data", []):
                    chapter = self._parse_chapter(item, manga_id)
                    if chapter is not None:
                        chapters.append(chapter)
                total = data.get("total", 0)
                offset += limit
                if offset >= total:
                    break
            return chapters
        except Exception:
            return self._clone_mock_chapters(manga_id)

    async def get_chapter_pages(self, chapter_id: str) -> List[Page]:
        if not HTTPX_AVAILABLE or self.client is None:
            return [Page(number=i, url=f"https://via.placeholder.com/800x1200.png?text=Page+{i}") for i in range(1, 21)]
        try:
            response = await self.client.get(f"{self.base_url}/at-home/server/{chapter_id}")
            response.raise_for_status()
            data = response.json()
            base_url = data["baseUrl"]
            chapter_hash = data["chapter"]["hash"]
            files = data["chapter"]["dataSaver" if self.data_saver else "data"]
            pages = []
            quality = "data-saver" if self.data_saver else "data"
            for i, filename in enumerate(files, 1):
                pages.append(Page(number=i, url=f"{base_url}/{quality}/{chapter_hash}/{filename}"))
            return pages
        except Exception:
            return [Page(number=i, url=f"https://via.placeholder.com/800x1200.png?text=Page+{i}") for i in range(1, 21)]

    async def get_popular(self, limit: int = 20) -> List[Manga]:
        if not HTTPX_AVAILABLE or self.client is None:
            return [self._clone_mock_manga(manga) for manga in list(self.mock_manga.values())[:limit]]
        try:
            params = {
                "limit": limit,
                "includes[]": ["cover_art", "author", "artist"],
                "order[followedCount]": "desc",
                "contentRating[]": ["safe", "suggestive", "erotica"],
            }
            response = await self.client.get(f"{self.base_url}/manga", params=params)
            response.raise_for_status()
            data = response.json()
            results = []
            for item in data.get("data", []):
                manga = self._parse_manga(item)
                if manga is not None:
                    results.append(manga)
            return results
        except Exception:
            return [self._clone_mock_manga(manga) for manga in list(self.mock_manga.values())[:limit]]

    async def get_latest(self, limit: int = 20) -> List[Manga]:
        return await self.get_popular(limit=limit)

    async def get_trending(self, limit: int = 20) -> List[Manga]:
        return await self.get_popular(limit=limit)

    def _parse_manga(self, data: Dict[str, Any]) -> Optional[Manga]:
        try:
            attrs = data["attributes"]
            title = attrs["title"].get("en") or list(attrs["title"].values())[0]
            alt_titles = []
            for alt in attrs.get("altTitles", []):
                alt_titles.extend(alt.values())
            description = attrs.get("description", {}).get("en")
            cover_url = None
            author = None
            artist = None
            for rel in data.get("relationships", []):
                rel_type = rel.get("type")
                rel_attrs = rel.get("attributes", {})
                if rel_type == "cover_art":
                    filename = rel_attrs.get("fileName")
                    if filename:
                        cover_url = f"https://uploads.mangadex.org/covers/{data['id']}/{filename}"
                elif rel_type == "author":
                    author = rel_attrs.get("name")
                elif rel_type == "artist":
                    artist = rel_attrs.get("name")
            genres = []
            tags = []
            for tag in attrs.get("tags", []):
                tag_attrs = tag.get("attributes", {})
                tag_name = tag_attrs.get("name", {}).get("en", "")
                if tag_attrs.get("group") == "genre":
                    genres.append(tag_name)
                else:
                    tags.append(tag_name)
            status_map = {
                "ongoing": MangaStatus.ONGOING,
                "completed": MangaStatus.COMPLETED,
                "hiatus": MangaStatus.HIATUS,
                "cancelled": MangaStatus.CANCELLED,
            }
            status = status_map.get(attrs.get("status"), MangaStatus.UNKNOWN)
            return Manga(
                id=data["id"],
                title=title,
                alt_titles=alt_titles,
                description=description,
                cover_url=cover_url,
                author=author,
                artist=artist,
                genres=genres,
                tags=tags,
                status=status,
                year=attrs.get("year"),
                provider=self.name,
                provider_url=f"https://mangadex.org/title/{data['id']}",
            )
        except Exception:
            return None

    def _parse_chapter(self, data: Dict[str, Any], manga_id: str) -> Optional[Chapter]:
        try:
            attrs = data["attributes"]
            raw_num = attrs.get("chapter")
            if not raw_num:
                return None
            chapter_num = float(raw_num)
            scanlation_group = None
            for rel in data.get("relationships", []):
                if rel.get("type") == "scanlation_group":
                    scanlation_group = rel.get("attributes", {}).get("name")
                    break
            publish_date = None
            if attrs.get("publishAt"):
                try:
                    publish_date = datetime.fromisoformat(attrs["publishAt"].replace("Z", "+00:00"))
                except Exception:
                    publish_date = None
            return Chapter(
                id=data["id"],
                manga_id=manga_id,
                number=chapter_num,
                title=attrs.get("title"),
                volume=attrs.get("volume"),
                language=attrs.get("translatedLanguage", self.language),
                pages_count=attrs.get("pages", 0),
                scanlation_group=scanlation_group,
                publish_date=publish_date,
                provider=self.name,
            )
        except Exception:
            return None

    async def close(self) -> None:
        if self.client is not None and HTTPX_AVAILABLE:
            await self.client.aclose()
