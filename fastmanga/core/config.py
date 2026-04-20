"""
Configuration management for FastManga.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict
from platformdirs import user_config_dir, user_data_dir, user_cache_dir


@dataclass
class GeneralConfig:
    """General application settings."""
    default_provider: str = "mangadex"
    image_renderer: str = "chafa"  # chafa, icat, sixel, none
    use_fzf: bool = True
    auto_sync: bool = True
    log_level: str = "INFO"


@dataclass
class ReadingConfig:
    """Reading interface settings."""
    page_fit: str = "width"  # width, height, best
    background_color: str = "black"
    zoom_level: int = 100
    reading_direction: str = "ltr"  # ltr, rtl, ttb
    double_page_mode: bool = False
    show_page_numbers: bool = True


@dataclass
class DownloadConfig:
    """Download settings."""
    download_dir: str = "~/Manga"
    quality: str = "high"  # low, medium, high, original
    format: str = "cbz"  # cbz, pdf, folder
    concurrent_downloads: int = 3
    merge_chapters: bool = False
    keep_archive: bool = True
    create_metadata: bool = True


@dataclass
class ProviderConfig:
    """Provider-specific settings."""
    mangadex_language: str = "en"
    mangadex_data_saver: bool = False
    mangasee_enabled: bool = True
    use_fallback: bool = True


@dataclass
class MALConfig:
    """MyAnimeList integration settings."""
    auto_update: bool = True
    auto_sync_interval: int = 3600
    client_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


@dataclass
class WorkerConfig:
    """Background worker settings."""
    enabled: bool = True
    check_interval: int = 300
    max_retries: int = 3
    retry_delay: int = 60


@dataclass
class CacheConfig:
    """Cache settings."""
    enabled: bool = True
    max_size: int = 1024  # MB
    ttl: int = 86400  # seconds


class Config:
    """Main configuration manager."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration."""
        self.config_dir = Path(user_config_dir("fastmanga", "fastmanga"))
        self.data_dir = Path(user_data_dir("fastmanga", "fastmanga"))
        self.cache_dir = Path(user_cache_dir("fastmanga", "fastmanga"))
        
        # Create directories
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_path = config_path or self.config_dir / "config.yaml"
        
        # Initialize config sections
        self.general = GeneralConfig()
        self.reading = ReadingConfig()
        self.downloads = DownloadConfig()
        self.providers = ProviderConfig()
        self.mal = MALConfig()
        self.worker = WorkerConfig()
        self.cache = CacheConfig()
        
        # Load existing config
        self.load()
    
    @property
    def download_dir(self) -> Path:
        """Get the download directory as a Path object."""
        path = Path(self.downloads.download_dir).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def database_path(self) -> Path:
        """Get the database file path."""
        return self.data_dir / "library.db"
    
    @property
    def queue_path(self) -> Path:
        """Get the download queue file path."""
        return self.data_dir / "queue.json"
    
    @property
    def history_path(self) -> Path:
        """Get the reading history file path."""
        return self.data_dir / "history.json"
    
    def load(self) -> None:
        """Load configuration from file."""
        if not self.config_path.exists():
            self.save()  # Create default config
            return
        
        try:
            with open(self.config_path, 'r') as f:
                data = yaml.safe_load(f) or {}
            
            # Update config sections
            if "general" in data:
                self._update_dataclass(self.general, data["general"])
            if "reading" in data:
                self._update_dataclass(self.reading, data["reading"])
            if "downloads" in data:
                self._update_dataclass(self.downloads, data["downloads"])
            if "providers" in data:
                self._update_dataclass(self.providers, data["providers"])
            if "mal" in data:
                self._update_dataclass(self.mal, data["mal"])
            if "worker" in data:
                self._update_dataclass(self.worker, data["worker"])
            if "cache" in data:
                self._update_dataclass(self.cache, data["cache"])
                
        except Exception as e:
            print(f"Error loading config: {e}")
            print("Using default configuration")
    
    def save(self) -> None:
        """Save configuration to file."""
        data = {
            "general": asdict(self.general),
            "reading": asdict(self.reading),
            "downloads": asdict(self.downloads),
            "providers": asdict(self.providers),
            "mal": asdict(self.mal),
            "worker": asdict(self.worker),
            "cache": asdict(self.cache),
        }
        
        with open(self.config_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def reset(self) -> None:
        """Reset configuration to defaults."""
        self.general = GeneralConfig()
        self.reading = ReadingConfig()
        self.downloads = DownloadConfig()
        self.providers = ProviderConfig()
        self.mal = MALConfig()
        self.worker = WorkerConfig()
        self.cache = CacheConfig()
        self.save()
    
    @staticmethod
    def _update_dataclass(obj: Any, data: Dict[str, Any]) -> None:
        """Update a dataclass object with dictionary data."""
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dot-notation key."""
        parts = key.split(".")
        obj = self
        
        for part in parts:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                return default
        
        return obj
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value by dot-notation key."""
        parts = key.split(".")
        obj = self
        
        for part in parts[:-1]:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                return
        
        if hasattr(obj, parts[-1]):
            setattr(obj, parts[-1], value)
            self.save()
