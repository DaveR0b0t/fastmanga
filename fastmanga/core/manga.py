"""Core data models for manga, chapters, and pages."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MangaStatus(Enum):
    """Manga publication status."""

    ONGOING = "ongoing"
    COMPLETED = "completed"
    HIATUS = "hiatus"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class ReadingStatus(Enum):
    """User's reading status."""

    READING = "reading"
    COMPLETED = "completed"
    PLAN_TO_READ = "plan_to_read"
    DROPPED = "dropped"
    ON_HOLD = "on_hold"


@dataclass
class Page:
    """Represents a single manga page."""

    number: int
    url: str
    image_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None

    def __post_init__(self) -> None:
        """Initialize image_url if not provided."""
        if self.image_url is None:
            self.image_url = self.url


@dataclass
class Chapter:
    """Represents a manga chapter."""

    id: str
    manga_id: str
    number: float
    title: Optional[str] = None
    volume: Optional[str] = None
    language: str = "en"
    pages_count: int = 0
    scanlation_group: Optional[str] = None
    publish_date: Optional[datetime] = None
    pages: List[Page] = field(default_factory=list)
    is_downloaded: bool = False
    download_path: Optional[str] = None
    provider: str = "unknown"

    def __str__(self) -> str:
        """String representation of chapter."""
        title = f" - {self.title}" if self.title else ""
        volume = f"Vol. {self.volume} " if self.volume else ""
        return f"{volume}Ch. {self.number}{title}"

    @property
    def safe_filename(self) -> str:
        """Generate a safe filename for this chapter."""
        volume = f"Vol{self.volume}_" if self.volume else ""
        chapter = f"Ch{self.number:g}"
        title = f"_{self._sanitize(self.title)}" if self.title else ""
        return f"{volume}{chapter}{title}"

    @staticmethod
    def _sanitize(text: Optional[str]) -> str:
        """Sanitize text for use in filenames."""
        if not text:
            return ""

        sanitized = text
        for char in '<>:"/\\|?*':
            sanitized = sanitized.replace(char, '_')
        return sanitized[:100]


@dataclass
class Manga:
    """Represents a manga series."""

    id: str
    title: str
    alt_titles: List[str] = field(default_factory=list)
    description: Optional[str] = None
    cover_url: Optional[str] = None
    author: Optional[str] = None
    artist: Optional[str] = None
    genres: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    status: MangaStatus = MangaStatus.UNKNOWN
    year: Optional[int] = None
    chapters: List[Chapter] = field(default_factory=list)
    provider: str = "unknown"
    provider_url: Optional[str] = None

    reading_status: Optional[ReadingStatus] = None
    chapters_read: int = 0
    rating: Optional[float] = None
    last_read: Optional[datetime] = None
    last_chapter_read: Optional[float] = None
    is_favorite: bool = False

    mal_id: Optional[int] = None
    anilist_id: Optional[int] = None

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        """String representation of manga."""
        return self.title

    @property
    def safe_title(self) -> str:
        """Generate a safe title for use in filenames/directories."""
        return Chapter._sanitize(self.title)

    @property
    def total_chapters(self) -> int:
        """Get total number of chapters."""
        return len(self.chapters)

    @property
    def progress_percentage(self) -> float:
        """Calculate reading progress as percentage."""
        if not self.total_chapters:
            return 0.0
        return (self.chapters_read / self.total_chapters) * 100

    def get_chapter(self, number: float) -> Optional[Chapter]:
        """Get a specific chapter by number."""
        return next((chapter for chapter in self.chapters if chapter.number == number), None)

    def get_next_chapter(self, current: float) -> Optional[Chapter]:
        """Get the next chapter after the given chapter number."""
        return next(
            (chapter for chapter in sorted(self.chapters, key=lambda item: item.number) if chapter.number > current),
            None,
        )

    def get_previous_chapter(self, current: float) -> Optional[Chapter]:
        """Get the previous chapter before the given chapter number."""
        return next(
            (
                chapter
                for chapter in sorted(self.chapters, key=lambda item: item.number, reverse=True)
                if chapter.number < current
            ),
            None,
        )

    def mark_chapter_read(self, chapter_number: float) -> None:
        """Mark a chapter as read and update progress."""
        chapter = self.get_chapter(chapter_number)
        if chapter is None:
            return

        now = datetime.now()
        self.last_chapter_read = chapter_number
        self.last_read = now
        self.chapters_read = sum(1 for item in self.chapters if item.number <= chapter_number)
        self.updated_at = now

    def to_dict(self) -> Dict[str, Any]:
        """Convert manga to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "alt_titles": self.alt_titles,
            "description": self.description,
            "cover_url": self.cover_url,
            "author": self.author,
            "artist": self.artist,
            "genres": self.genres,
            "tags": self.tags,
            "status": self.status.value,
            "year": self.year,
            "provider": self.provider,
            "provider_url": self.provider_url,
            "reading_status": self.reading_status.value if self.reading_status else None,
            "chapters_read": self.chapters_read,
            "rating": self.rating,
            "last_read": self.last_read.isoformat() if self.last_read else None,
            "last_chapter_read": self.last_chapter_read,
            "is_favorite": self.is_favorite,
            "mal_id": self.mal_id,
            "anilist_id": self.anilist_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Manga":
        """Create manga from dictionary."""
        normalized = dict(data)

        if normalized.get("last_read"):
            normalized["last_read"] = datetime.fromisoformat(normalized["last_read"])
        if normalized.get("created_at"):
            normalized["created_at"] = datetime.fromisoformat(normalized["created_at"])
        if normalized.get("updated_at"):
            normalized["updated_at"] = datetime.fromisoformat(normalized["updated_at"])

        if normalized.get("status"):
            normalized["status"] = MangaStatus(normalized["status"])
        if normalized.get("reading_status"):
            normalized["reading_status"] = ReadingStatus(normalized["reading_status"])

        normalized.pop("chapters", None)
        return cls(**normalized)
