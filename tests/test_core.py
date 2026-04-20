"""Test suite for FastManga core functionality."""

from pathlib import Path
import tempfile

import pytest

from fastmanga.core.config import Config
from fastmanga.core.database import Database
from fastmanga.core.manga import Chapter, Manga, MangaStatus, Page, ReadingStatus
from fastmanga.providers.mangadex import MangaDexProvider


@pytest.fixture
def temp_config():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Config(config_path=Path(tmpdir) / "config.yaml")
        config.data_dir = Path(tmpdir) / "data"
        config.cache_dir = Path(tmpdir) / "cache"
        config.downloads.download_dir = str(Path(tmpdir) / "downloads")
        yield config


@pytest.fixture
def temp_db(temp_config):
    db_path = temp_config.data_dir / "test.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    yield Database(db_path)


@pytest.fixture
def sample_manga():
    return Manga(
        id="test-manga-1",
        title="Test Manga",
        alt_titles=["Alternative Title"],
        description="A test manga for unit testing",
        author="Test Author",
        artist="Test Artist",
        genres=["Action", "Adventure"],
        tags=["Fantasy", "Magic"],
        status=MangaStatus.ONGOING,
        year=2024,
        provider="test",
    )


@pytest.fixture
def sample_chapter(sample_manga):
    return Chapter(
        id="test-chapter-1",
        manga_id=sample_manga.id,
        number=1.0,
        title="Test Chapter",
        volume="1",
        language="en",
        pages_count=20,
        scanlation_group="Test Group",
        provider="test",
    )


class TestManga:
    def test_manga_creation(self, sample_manga):
        assert sample_manga.id == "test-manga-1"
        assert sample_manga.title == "Test Manga"
        assert len(sample_manga.genres) == 2
        assert sample_manga.status == MangaStatus.ONGOING

    def test_safe_title(self):
        manga = Manga(id="1", title="Test: Manga / With <Invalid> Characters", provider="test")
        safe = manga.safe_title
        assert "<" not in safe
        assert ">" not in safe
        assert "/" not in safe

    def test_progress_calculation(self, sample_manga):
        sample_manga.chapters = [Chapter(id=f"ch{i}", manga_id=sample_manga.id, number=float(i), provider="test") for i in range(1, 11)]
        sample_manga.chapters_read = 5
        assert sample_manga.total_chapters == 10
        assert sample_manga.progress_percentage == 50.0

    def test_mark_chapter_read(self, sample_manga):
        sample_manga.chapters = [Chapter(id=f"ch{i}", manga_id=sample_manga.id, number=float(i), provider="test") for i in range(1, 6)]
        sample_manga.mark_chapter_read(3.0)
        assert sample_manga.last_chapter_read == 3.0
        assert sample_manga.chapters_read == 3
        assert sample_manga.last_read is not None


class TestChapter:
    def test_chapter_creation(self, sample_chapter):
        assert sample_chapter.number == 1.0
        assert sample_chapter.title == "Test Chapter"
        assert sample_chapter.pages_count == 20

    def test_chapter_string_representation(self, sample_chapter):
        chapter_str = str(sample_chapter)
        assert "Ch. 1" in chapter_str
        assert "Vol. 1" in chapter_str

    def test_safe_filename_generation(self, sample_chapter):
        filename = sample_chapter.safe_filename
        assert "Vol1_Ch1" in filename
        assert "/" not in filename
        assert "\\" not in filename


class TestDatabase:
    def test_database_creation(self, temp_db):
        assert temp_db.db_path.exists()

    def test_add_manga(self, temp_db, sample_manga):
        temp_db.add_manga(sample_manga)
        retrieved = temp_db.get_manga(sample_manga.id)
        assert retrieved is not None
        assert retrieved.title == sample_manga.title

    def test_add_chapter(self, temp_db, sample_manga, sample_chapter):
        temp_db.add_manga(sample_manga)
        temp_db.add_chapter(sample_chapter)
        chapters = temp_db.get_chapters(sample_manga.id)
        assert len(chapters) == 1
        assert chapters[0].number == 1.0

    def test_search_manga(self, temp_db, sample_manga):
        temp_db.add_manga(sample_manga)
        results = temp_db.search_manga("Test")
        assert len(results) == 1
        assert results[0].title == "Test Manga"

    def test_bookmarks_and_history(self, temp_db, sample_manga, sample_chapter):
        temp_db.add_manga(sample_manga)
        temp_db.add_chapter(sample_chapter)
        temp_db.add_to_history(sample_manga.id, sample_chapter.id, sample_chapter.number, page_number=5)
        temp_db.add_bookmark(sample_manga.id, sample_chapter.id, page_number=10, note="Interesting page")
        history = temp_db.get_reading_history(limit=10)
        bookmarks = temp_db.get_bookmarks(sample_manga.id)
        assert len(history) == 1
        assert history[0]["page_number"] == 5
        assert len(bookmarks) == 1
        assert bookmarks[0]["note"] == "Interesting page"

    def test_statistics(self, temp_db, sample_manga):
        sample_manga.reading_status = ReadingStatus.READING
        sample_manga.chapters_read = 10
        sample_manga.is_favorite = True
        temp_db.add_manga(sample_manga)
        stats = temp_db.get_statistics()
        assert stats["total_manga"] == 1
        assert stats["total_chapters_read"] == 10
        assert stats["favorites"] == 1
        assert ReadingStatus.READING.value in stats["by_status"]


class TestConfig:
    def test_config_creation(self, temp_config):
        assert temp_config.config_path.exists()

    def test_config_defaults(self, temp_config):
        assert temp_config.general.default_provider == "mangadex"
        assert temp_config.downloads.format == "cbz"
        assert temp_config.downloads.concurrent_downloads == 3

    def test_config_save_load(self, temp_config):
        temp_config.downloads.quality = "original"
        temp_config.save()
        new_config = Config(temp_config.config_path)
        assert new_config.downloads.quality == "original"

    def test_config_get_set(self, temp_config):
        assert temp_config.get("downloads.quality") == "high"
        temp_config.set("downloads.quality", "low")
        assert temp_config.downloads.quality == "low"


@pytest.mark.integration
@pytest.mark.asyncio
class TestMangaDexProvider:
    async def test_provider_search(self):
        provider = MangaDexProvider()
        try:
            results = await provider.search("One Piece", limit=5)
            assert len(results) > 0
            assert all(isinstance(m, Manga) for m in results)
            assert all(m.title for m in results)
        finally:
            await provider.close()

    async def test_provider_get_chapters(self):
        provider = MangaDexProvider()
        try:
            results = await provider.search("Naruto", limit=1)
            if results:
                chapters = await provider.get_chapters(results[0].id)
                assert len(chapters) > 0
                assert all(isinstance(c, Chapter) for c in chapters)
        finally:
            await provider.close()


class TestHelpers:
    def test_page_creation(self):
        page = Page(number=1, url="https://example.com/page1.jpg")
        assert page.number == 1
        assert page.image_url == page.url

    def test_status_enums(self):
        assert MangaStatus.ONGOING.value == "ongoing"
        assert ReadingStatus.READING.value == "reading"
