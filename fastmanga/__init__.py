"""FastManga package metadata and public exports."""

__version__ = "1.0.1"
__author__ = "Dave"
__license__ = "MIT"
__description__ = "Educational CLI manga reader and downloader prototype"

from .core.config import Config
from .core.database import Database
from .core.manga import Manga, Chapter, Page

__all__ = [
    "Config",
    "Database",
    "Manga",
    "Chapter",
    "Page",
    "__version__",
    "__description__",
]
