"""Manga downloader with support for multiple formats."""

import asyncio
from io import BytesIO
from pathlib import Path
from typing import Optional, Sequence
from zipfile import ZIP_DEFLATED, ZipFile

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    import urllib.error
    import urllib.request

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from rich.console import Console
from rich.progress import BarColumn, DownloadColumn, Progress, SpinnerColumn, TextColumn

from ..core.config import Config
from ..core.manga import Chapter, Manga
from ..providers.base import BaseProvider

console = Console()


class Downloader:
    """Handles manga chapter downloads."""

    def __init__(self, config: Config):
        self.config = config
        self.client = httpx.AsyncClient(timeout=60.0) if HTTPX_AVAILABLE else None
        self.download_dir = config.download_dir

    async def download_chapter(
        self,
        provider: BaseProvider,
        manga: Manga,
        chapter: Chapter,
        format: Optional[str] = None,
    ) -> Optional[Path]:
        output_format = format or self.config.downloads.format
        manga_dir = self.download_dir / manga.safe_title
        manga_dir.mkdir(parents=True, exist_ok=True)

        with console.status(f"[bold blue]Fetching pages for {chapter}..."):
            pages = await provider.get_chapter_pages(chapter.id)

        if not pages:
            console.print(f"[red]No pages found for {chapter}[/red]")
            return None

        chapter.pages = pages
        chapter.pages_count = len(pages)

        downloaded_pages: list[tuple[int, bytes]] = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            DownloadColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"Downloading {chapter}", total=len(pages))
            for page in pages:
                image_data = await self._download_image(page.url)
                if image_data is None:
                    console.print(f"[yellow]Warning: Failed to download page {page.number}[/yellow]")
                    continue
                downloaded_pages.append((page.number, image_data))
                progress.update(task, advance=1)

        if not downloaded_pages:
            console.print(f"[red]Failed to download any pages for {chapter}[/red]")
            return None

        if output_format == "cbz":
            output_path = await self._save_as_cbz(manga_dir, chapter, downloaded_pages)
        elif output_format == "pdf":
            output_path = await self._save_as_pdf(manga_dir, chapter, downloaded_pages)
        else:
            output_path = await self._save_as_folder(manga_dir, chapter, downloaded_pages)

        chapter.is_downloaded = True
        chapter.download_path = str(output_path)
        console.print(f"[green]Downloaded {chapter} to {output_path}[/green]")
        return output_path

    async def _download_image(self, url: str) -> Optional[bytes]:
        try:
            if self.client is not None:
                response = await self.client.get(url)
                response.raise_for_status()
                return response.content

            loop = asyncio.get_running_loop()

            def _download() -> Optional[bytes]:
                try:
                    with urllib.request.urlopen(url, timeout=30) as response:
                        return response.read()
                except urllib.error.URLError as exc:
                    console.print(f"[yellow]URL error: {exc}[/yellow]")
                    return None

            return await loop.run_in_executor(None, _download)
        except Exception as exc:
            console.print(f"[yellow]Error downloading image: {exc}[/yellow]")
            return None

    @staticmethod
    def _detect_image_extension(image_data: bytes) -> str:
        if PIL_AVAILABLE:
            image = Image.open(BytesIO(image_data))
            return image.format.lower() if image.format else "jpg"
        if image_data.startswith(bytes([137, 80, 78, 71])):
            return "png"
        if image_data.startswith(bytes([255, 216])):
            return "jpg"
        return "jpg"

    async def _save_as_cbz(self, manga_dir: Path, chapter: Chapter, pages: Sequence[tuple[int, bytes]]) -> Path:
        output_path = manga_dir / f"{chapter.safe_filename}.cbz"
        with ZipFile(output_path, "w", ZIP_DEFLATED) as cbz:
            for page_num, image_data in sorted(pages):
                extension = self._detect_image_extension(image_data)
                cbz.writestr(f"{page_num:04d}.{extension}", image_data)
        return output_path

    async def _save_as_pdf(self, manga_dir: Path, chapter: Chapter, pages: Sequence[tuple[int, bytes]]) -> Path:
        output_path = manga_dir / f"{chapter.safe_filename}.pdf"
        if not PIL_AVAILABLE:
            console.print("[yellow]PIL not available, saving as folder instead[/yellow]")
            return await self._save_as_folder(manga_dir, chapter, pages)

        images = []
        for _, image_data in sorted(pages):
            image = Image.open(BytesIO(image_data))
            if image.mode != "RGB":
                image = image.convert("RGB")
            images.append(image)

        if images:
            images[0].save(output_path, save_all=True, append_images=images[1:], format="PDF")
        return output_path

    async def _save_as_folder(self, manga_dir: Path, chapter: Chapter, pages: Sequence[tuple[int, bytes]]) -> Path:
        chapter_dir = manga_dir / chapter.safe_filename
        chapter_dir.mkdir(parents=True, exist_ok=True)
        for page_num, image_data in sorted(pages):
            extension = self._detect_image_extension(image_data)
            (chapter_dir / f"{page_num:04d}.{extension}").write_bytes(image_data)
        return chapter_dir

    async def close(self) -> None:
        if self.client is not None:
            await self.client.aclose()
