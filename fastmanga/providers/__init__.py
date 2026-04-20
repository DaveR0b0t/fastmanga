"""Manga providers."""

from .base import BaseProvider
from .mangadex import MangaDexProvider

__all__ = [
    "BaseProvider",
    "MangaDexProvider",
]
