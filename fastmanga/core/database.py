"""Database management for local manga library."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from .manga import Chapter, Manga, ReadingStatus


class Database:
    """SQLite database manager for manga library."""

    def __init__(self, db_path: Path):
        """Initialize database connection."""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def get_connection(self) -> Iterator[sqlite3.Connection]:
        """Get database connection with automatic commit and rollback."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS manga (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    alt_titles TEXT,
                    description TEXT,
                    cover_url TEXT,
                    author TEXT,
                    artist TEXT,
                    genres TEXT,
                    tags TEXT,
                    status TEXT,
                    year INTEGER,
                    provider TEXT,
                    provider_url TEXT,
                    reading_status TEXT,
                    chapters_read INTEGER DEFAULT 0,
                    rating REAL,
                    last_read TEXT,
                    last_chapter_read REAL,
                    is_favorite INTEGER DEFAULT 0,
                    mal_id INTEGER,
                    anilist_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chapters (
                    id TEXT PRIMARY KEY,
                    manga_id TEXT NOT NULL,
                    number REAL NOT NULL,
                    title TEXT,
                    volume TEXT,
                    language TEXT DEFAULT 'en',
                    pages_count INTEGER DEFAULT 0,
                    scanlation_group TEXT,
                    publish_date TEXT,
                    is_downloaded INTEGER DEFAULT 0,
                    download_path TEXT,
                    provider TEXT,
                    FOREIGN KEY (manga_id) REFERENCES manga(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reading_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    manga_id TEXT NOT NULL,
                    chapter_id TEXT NOT NULL,
                    chapter_number REAL NOT NULL,
                    page_number INTEGER DEFAULT 1,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (manga_id) REFERENCES manga(id) ON DELETE CASCADE,
                    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bookmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    manga_id TEXT NOT NULL,
                    chapter_id TEXT NOT NULL,
                    page_number INTEGER NOT NULL,
                    note TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (manga_id) REFERENCES manga(id) ON DELETE CASCADE,
                    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_manga_title ON manga(title)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_manga_status ON manga(reading_status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chapters_manga ON chapters(manga_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_manga ON reading_history(manga_id)")

    @staticmethod
    def _decode_json_list(value: Optional[str]) -> List[str]:
        return json.loads(value) if value else []

    def _deserialize_manga_row(self, row: sqlite3.Row) -> Manga:
        data: Dict[str, Any] = dict(row)
        data["alt_titles"] = self._decode_json_list(data.get("alt_titles"))
        data["genres"] = self._decode_json_list(data.get("genres"))
        data["tags"] = self._decode_json_list(data.get("tags"))
        data["is_favorite"] = bool(data["is_favorite"])

        manga = Manga.from_dict(data)
        manga.chapters = self.get_chapters(manga.id)
        return manga

    def add_manga(self, manga: Manga) -> None:
        """Add or update a manga in the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            data = manga.to_dict()
            data["alt_titles"] = json.dumps(data["alt_titles"])
            data["genres"] = json.dumps(data["genres"])
            data["tags"] = json.dumps(data["tags"])
            data["is_favorite"] = int(data["is_favorite"])

            cursor.execute("""
                INSERT OR REPLACE INTO manga (
                    id, title, alt_titles, description, cover_url, author, artist,
                    genres, tags, status, year, provider, provider_url,
                    reading_status, chapters_read, rating, last_read,
                    last_chapter_read, is_favorite, mal_id, anilist_id,
                    created_at, updated_at
                ) VALUES (
                    :id, :title, :alt_titles, :description, :cover_url, :author, :artist,
                    :genres, :tags, :status, :year, :provider, :provider_url,
                    :reading_status, :chapters_read, :rating, :last_read,
                    :last_chapter_read, :is_favorite, :mal_id, :anilist_id,
                    :created_at, :updated_at
                )
            """, data)

    def get_manga(self, manga_id: str) -> Optional[Manga]:
        """Get a manga by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM manga WHERE id = ?", (manga_id,))
            row = cursor.fetchone()
            return self._deserialize_manga_row(row) if row else None

    def get_all_manga(self, status: Optional[ReadingStatus] = None) -> List[Manga]:
        """Get all manga, optionally filtered by reading status."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute(
                    "SELECT * FROM manga WHERE reading_status = ? ORDER BY title",
                    (status.value,),
                )
            else:
                cursor.execute("SELECT * FROM manga ORDER BY title")
            return [self._deserialize_manga_row(row) for row in cursor.fetchall()]

    def search_manga(self, query: str) -> List[Manga]:
        """Search manga by title."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM manga WHERE title LIKE ? ORDER BY title",
                (f"%{query}%",),
            )
            return [self._deserialize_manga_row(row) for row in cursor.fetchall()]

    def delete_manga(self, manga_id: str) -> None:
        """Delete a manga from the database."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM manga WHERE id = ?", (manga_id,))

    def add_chapter(self, chapter: Chapter) -> None:
        """Add or update a chapter."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO chapters (
                    id, manga_id, number, title, volume, language,
                    pages_count, scanlation_group, publish_date,
                    is_downloaded, download_path, provider
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chapter.id,
                chapter.manga_id,
                chapter.number,
                chapter.title,
                chapter.volume,
                chapter.language,
                chapter.pages_count,
                chapter.scanlation_group,
                chapter.publish_date.isoformat() if chapter.publish_date else None,
                int(chapter.is_downloaded),
                chapter.download_path,
                chapter.provider,
            ))

    def get_chapters(self, manga_id: str) -> List[Chapter]:
        """Get all chapters for a manga."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM chapters WHERE manga_id = ? ORDER BY number",
                (manga_id,),
            )

            chapters = []
            for row in cursor.fetchall():
                data = dict(row)
                if data.get("publish_date"):
                    data["publish_date"] = datetime.fromisoformat(data["publish_date"])
                data["is_downloaded"] = bool(data["is_downloaded"])
                chapters.append(Chapter(**data))
            return chapters

    def add_to_history(
        self,
        manga_id: str,
        chapter_id: str,
        chapter_number: float,
        page_number: int = 1,
    ) -> None:
        """Add a reading session to history."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO reading_history (
                    manga_id, chapter_id, chapter_number, page_number, timestamp
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (manga_id, chapter_id, chapter_number, page_number, datetime.now().isoformat()),
            )

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get reading history."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT h.*, m.title as manga_title, c.title as chapter_title
                FROM reading_history h
                JOIN manga m ON h.manga_id = m.id
                JOIN chapters c ON h.chapter_id = c.id
                ORDER BY h.timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def add_bookmark(
        self,
        manga_id: str,
        chapter_id: str,
        page_number: int,
        note: Optional[str] = None,
    ) -> None:
        """Add a bookmark."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO bookmarks (manga_id, chapter_id, page_number, note, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (manga_id, chapter_id, page_number, note, datetime.now().isoformat()),
            )

    def get_bookmarks(self, manga_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get bookmarks, optionally filtered by manga."""
        query = """
            SELECT b.*, m.title as manga_title, c.number as chapter_number, c.title as chapter_title
            FROM bookmarks b
            JOIN manga m ON b.manga_id = m.id
            JOIN chapters c ON b.chapter_id = c.id
        """
        params: tuple[Any, ...] = ()

        if manga_id:
            query += " WHERE b.manga_id = ?"
            params = (manga_id,)

        query += " ORDER BY b.created_at DESC"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict[str, Any]:
        """Get library statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            stats: Dict[str, Any] = {}

            cursor.execute("SELECT COUNT(*) FROM manga")
            stats["total_manga"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM chapters")
            stats["total_chapters"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM manga WHERE reading_status = ?", (ReadingStatus.READING.value,))
            stats["currently_reading"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM manga WHERE reading_status = ?", (ReadingStatus.COMPLETED.value,))
            stats["completed"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM reading_history")
            stats["reading_sessions"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM bookmarks")
            stats["bookmarks"] = cursor.fetchone()[0]

            return stats