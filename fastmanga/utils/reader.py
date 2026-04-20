"""Terminal-based manga reader with image rendering."""

import subprocess
import tempfile
from pathlib import Path
from typing import Sequence

from rich.console import Console
from rich.panel import Panel

from ..core.config import Config
from ..core.manga import Chapter, Manga
from ..providers.base import BaseProvider
from .downloader import Downloader

console = Console()


class MangaReader:
    """Terminal-based manga reader."""

    def __init__(self, config: Config):
        self.config = config
        self.image_renderer = config.general.image_renderer
        self.downloader = Downloader(config)
        self.output_dir = config.download_dir

    async def read_chapter(self, provider: BaseProvider, manga: Manga, chapter: Chapter) -> None:
        console.print(
            Panel(
                f"[bold cyan]{manga.title}[/bold cyan]\n[yellow]{chapter}[/yellow]",
                title="Reading",
                border_style="blue",
            )
        )

        if not chapter.pages:
            with console.status("[bold blue]Loading pages..."):
                chapter.pages = await provider.get_chapter_pages(chapter.id)

        if not chapter.pages:
            console.print("[red]No pages available for this chapter.[/red]")
            return

        if chapter.is_downloaded and chapter.download_path:
            download_path = Path(chapter.download_path)
            if download_path.exists():
                console.print(f"[cyan]Reading from: {download_path}[/cyan]")
                self._open_with_external_viewer(download_path)
                return

        with console.status("[bold blue]Preparing chapter for reading..."):
            temp_dir = Path(tempfile.mkdtemp(prefix="fastmanga_"))
            downloaded_pages = []
            for page in chapter.pages:
                image_data = await self.downloader._download_image(page.url)
                if image_data is None:
                    console.print(f"[yellow]Warning: Failed to download page {page.number}[/yellow]")
                    continue
                page_path = temp_dir / f"{page.number:04d}.jpg"
                page_path.write_bytes(image_data)
                downloaded_pages.append(page_path)

        if not downloaded_pages:
            console.print("[red]Failed to download chapter pages.[/red]")
            return

        if self.image_renderer == "none":
            console.print(f"[yellow]Pages downloaded to {temp_dir}[/yellow]")
        else:
            self._display_pages(downloaded_pages)

        self._show_navigation_help()

    async def download_chapter(self, provider: BaseProvider, manga: Manga, chapter: Chapter) -> Path | None:
        return await self.downloader.download_chapter(provider, manga, chapter)

    def _display_pages(self, page_paths: Sequence[Path]) -> None:
        renderers = {
            "chafa": (self._display_with_chafa, "chafa not found. Please install it."),
            "icat": (self._display_with_icat, "kitty icat not found. Please install kitty terminal."),
            "sixel": (self._display_with_sixel, "img2sixel not found. Please install libsixel."),
        }
        renderer = renderers.get(self.image_renderer)
        if renderer is None:
            console.print(f"[yellow]Unknown image renderer: {self.image_renderer}[/yellow]")
            console.print(f"[cyan]Pages saved to: {page_paths[0].parent}[/cyan]")
            return
        display_func, missing_message = renderer
        try:
            display_func(page_paths)
        except KeyboardInterrupt:
            console.print("\n[yellow]Reading stopped.[/yellow]")
        except FileNotFoundError:
            console.print(f"[red]{missing_message}[/red]")

    def _display_with_chafa(self, page_paths: Sequence[Path]) -> None:
        for index, page_path in enumerate(page_paths, 1):
            self._display_page_header(index, len(page_paths))
            subprocess.run(["chafa", "--format", "symbols", "--size", "80x40", str(page_path)], check=False)
            self._prompt_for_next_page(index, len(page_paths))

    def _display_with_icat(self, page_paths: Sequence[Path]) -> None:
        for index, page_path in enumerate(page_paths, 1):
            self._display_page_header(index, len(page_paths))
            subprocess.run(["kitten", "icat", str(page_path)], check=False)
            self._prompt_for_next_page(index, len(page_paths))

    def _display_with_sixel(self, page_paths: Sequence[Path]) -> None:
        for index, page_path in enumerate(page_paths, 1):
            self._display_page_header(index, len(page_paths))
            subprocess.run(["img2sixel", str(page_path)], check=False)
            self._prompt_for_next_page(index, len(page_paths))

    @staticmethod
    def _display_page_header(index: int, total: int) -> None:
        console.print(f"\n[cyan]Page {index}/{total}[/cyan]")

    @staticmethod
    def _prompt_for_next_page(index: int, total: int) -> None:
        if index < total:
            input("Press Enter for next page (Ctrl+C to stop)...")

    def _open_with_external_viewer(self, path: Path) -> None:
        console.print("[cyan]Opening with system viewer...[/cyan]")
        try:
            subprocess.run(["xdg-open", str(path)], check=False)
        except Exception as exc:
            console.print(f"[yellow]Could not open with external viewer: {exc}[/yellow]")
            console.print(f"[cyan]File location: {path}[/cyan]")

    def _show_navigation_help(self) -> None:
        help_text = """
[bold cyan]Navigation:[/bold cyan]
  Press Enter - Next page
  Ctrl+C - Stop reading
  Open file manager to view all pages at once

[bold yellow]Tip:[/bold yellow]
  For better reading experience, consider downloading
  the chapter and opening it with a comic book reader.
"""
        console.print(Panel(help_text, title="Help", border_style="green"))
