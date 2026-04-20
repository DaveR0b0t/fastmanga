"""Main CLI application for FastManga."""

import asyncio
import sys
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .. import __description__, __version__
from ..core.config import Config
from ..core.database import Database
from ..providers.mangadex import MangaDexProvider
from ..utils.reader import MangaReader

console = Console()


class Context:
    """Shared context for CLI commands."""

    PROVIDERS = {"mangadex": MangaDexProvider}

    def __init__(self):
        self.config = Config()
        self.db = Database(self.config.database_path)
        self.provider = None

    def get_provider(self) -> MangaDexProvider:
        """Return the configured content provider."""
        if self.provider is not None:
            return self.provider

        provider_name = self.config.general.default_provider
        provider_class = self.PROVIDERS.get(provider_name)
        if provider_class is None:
            console.print(f"[red]Unknown provider: {provider_name}[/red]")
            sys.exit(1)

        self.provider = provider_class(
            language=self.config.providers.mangadex_language,
            data_saver=self.config.providers.mangadex_data_saver,
        )
        return self.provider


pass_context = click.make_pass_decorator(Context, ensure=True)

TOP_LEVEL_HELP = """Browse, read, and download manga from the terminal.

FastManga is an educational CLI prototype built around a MangaDex-backed
workflow with offline-friendly fallback data.


Common commands:
  fastmanga search "One Piece"
  fastmanga read "Naruto" --latest
  fastmanga download "Berserk" -c 1-3
  fastmanga library list
  fastmanga config path
"""


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    invoke_without_command=True,
    help=TOP_LEVEL_HELP,
)
@click.version_option(
    version=__version__,
    prog_name="fastmanga",
    message="%(prog)s %(version)s",
)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Main FastManga command group."""
    ctx.obj = Context()
    if ctx.invoked_subcommand is None:
        console.print(
            Panel.fit(
                f"[bold]fastmanga[/bold] [cyan]{__version__}[/cyan]\n"
                f"{__description__}\n\n"
                "Run [bold]fastmanga --help[/bold] to view commands.",
                title="FastManga",
                border_style="blue",
            )
        )


def _select_manga(manga_list: list, prompt_text: str = "Select manga number", default: int = 1):
    """Prompt the user to select a manga from a list."""
    if len(manga_list) == 1:
        return manga_list[0]

    console.print("[yellow]Multiple results found:[/yellow]")
    for index, manga in enumerate(manga_list, 1):
        console.print(f"{index}. {manga.title}")

    choice = click.prompt(prompt_text, type=int, default=default)
    return manga_list[choice - 1]


@cli.command()
@click.argument("query")
@click.option("-l", "--limit", default=20, show_default=True, help="Maximum number of results.")
@click.option("-r", "--read", is_flag=True, help="Open a result after the search finishes.")
@pass_context
def search(ctx: Context, query: str, limit: int, read: bool) -> None:
    """Search for manga by title."""

    async def _search() -> None:
        provider = ctx.get_provider()
        with console.status(f"[bold blue]Searching for '{query}'..."):
            results = await provider.search(query, limit=limit)

        if not results:
            console.print("[yellow]No results found.[/yellow]")
            return

        table = Table(title=f"Search Results: {query}")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Title", style="green")
        table.add_column("Author", style="blue")
        table.add_column("Status", style="magenta")
        table.add_column("Year", style="yellow")

        for index, manga in enumerate(results, 1):
            table.add_row(
                str(index),
                manga.title,
                manga.author or "Unknown",
                manga.status.value,
                str(manga.year) if manga.year else "N/A",
            )

        console.print(table)

        if not read:
            return

        try:
            choice = click.prompt("Select manga number, or 0 to cancel", type=int, default=0)
            if not 1 <= choice <= len(results):
                return

            selected = results[choice - 1]
            ctx.db.add_manga(selected)
            console.print(f"[green]Added '{selected.title}' to your library.[/green]")

            with console.status("[bold blue]Fetching chapters..."):
                chapters = await provider.get_chapters(selected.id)
            if not chapters:
                return

            selected.chapters = chapters
            for chapter in chapters:
                ctx.db.add_chapter(chapter)

            reader = MangaReader(ctx.config)
            await reader.read_chapter(provider, selected, chapters[0])
        except (KeyboardInterrupt, click.Abort):
            console.print("\n[yellow]Cancelled.[/yellow]")

    asyncio.run(_search())


@cli.command()
@click.argument("title")
@click.option("-c", "--chapter", type=float, help="Chapter number to read.")
@click.option("--latest", is_flag=True, help="Read the latest available chapter.")
@pass_context
def read(ctx: Context, title: str, chapter: Optional[float], latest: bool) -> None:
    """Read a manga chapter."""

    async def _read() -> None:
        manga_list = ctx.db.search_manga(title)
        provider = ctx.get_provider()

        if not manga_list:
            with console.status(f"[bold blue]Searching for '{title}'..."):
                manga_list = await provider.search(title, limit=5)
            if not manga_list:
                console.print("[red]Manga not found.[/red]")
                return

        manga = _select_manga(manga_list)

        if not manga.chapters:
            with console.status("[bold blue]Fetching chapters..."):
                manga.chapters = await provider.get_chapters(manga.id)
            for stored_chapter in manga.chapters:
                ctx.db.add_chapter(stored_chapter)
            ctx.db.add_manga(manga)

        if not manga.chapters:
            console.print("[red]No chapters available.[/red]")
            return

        if latest:
            selected_chapter = max(manga.chapters, key=lambda item: item.number)
        elif chapter is not None:
            selected_chapter = manga.get_chapter(chapter)
            if selected_chapter is None:
                console.print(f"[red]Chapter {chapter} not found.[/red]")
                return
        else:
            console.print(f"\n[bold]Available chapters for {manga.title}:[/bold]")
            for listed_chapter in manga.chapters[:20]:
                console.print(f"  Ch. {listed_chapter.number} - {listed_chapter.title or 'No title'}")
            if len(manga.chapters) > 20:
                console.print(f"  ... and {len(manga.chapters) - 20} more")

            chapter_num = click.prompt("Enter chapter number", type=float)
            selected_chapter = manga.get_chapter(chapter_num)
            if selected_chapter is None:
                console.print(f"[red]Chapter {chapter_num} not found.[/red]")
                return

        reader = MangaReader(ctx.config)
        await reader.read_chapter(provider, manga, selected_chapter)

        manga.mark_chapter_read(selected_chapter.number)
        ctx.db.add_manga(manga)
        ctx.db.add_to_history(manga.id, selected_chapter.id, selected_chapter.number)

    asyncio.run(_read())


@cli.command()
@click.argument("title")
@click.option("-c", "--chapters", help="Chapter range, e.g. 1-10 or 5.")
@click.option("-o", "--output", help="Optional output directory.")
@pass_context
def download(ctx: Context, title: str, chapters: Optional[str], output: Optional[str]) -> None:
    """Download one or more manga chapters."""

    async def _download() -> None:
        provider = ctx.get_provider()
        manga_list = ctx.db.search_manga(title)

        if not manga_list:
            with console.status(f"[bold blue]Searching for '{title}'..."):
                manga_list = await provider.search(title, limit=5)
            if not manga_list:
                console.print("[red]Manga not found.[/red]")
                return

        manga = _select_manga(manga_list)

        if not manga.chapters:
            with console.status("[bold blue]Fetching chapters..."):
                manga.chapters = await provider.get_chapters(manga.id)

        if not manga.chapters:
            console.print("[red]No chapters available.[/red]")
            return

        selected_chapters = manga.chapters
        if chapters:
            if "-" in chapters:
                start_str, end_str = chapters.split("-", 1)
                start_num = float(start_str)
                end_num = float(end_str)
                selected_chapters = [
                    ch for ch in manga.chapters if start_num <= ch.number <= end_num
                ]
            else:
                chapter_num = float(chapters)
                selected_chapters = [ch for ch in manga.chapters if ch.number == chapter_num]

        if not selected_chapters:
            console.print("[red]No matching chapters found.[/red]")
            return

        reader = MangaReader(ctx.config)
        reader.output_dir = output or reader.output_dir

        for selected_chapter in selected_chapters:
            with console.status(f"[bold blue]Downloading chapter {selected_chapter.number}..."):
                await reader.download_chapter(provider, manga, selected_chapter)
            console.print(
                f"[green]Downloaded {manga.title} chapter {selected_chapter.number}[/green]"
            )

    asyncio.run(_download())


@cli.group()
def library() -> None:
    """Manage your local manga library."""


@library.command("list")
@pass_context
def library_list(ctx: Context) -> None:
    """List manga stored in the local library."""
    manga_items = ctx.db.get_all_manga()
    if not manga_items:
        console.print("[yellow]Your library is empty.[/yellow]")
        return

    table = Table(title="Library")
    table.add_column("Title", style="green")
    table.add_column("Author", style="blue")
    table.add_column("Status", style="magenta")
    table.add_column("Progress", style="yellow")

    for manga in manga_items:
        total = len(manga.chapters)
        read_count = len(manga.read_chapters)
        progress = f"{read_count}/{total}" if total else str(read_count)
        table.add_row(manga.title, manga.author or "Unknown", manga.status.value, progress)

    console.print(table)


@library.command("stats")
@pass_context
def library_stats(ctx: Context) -> None:
    """Show library statistics."""
    stats = ctx.db.get_stats()
    table = Table(title="Library Stats")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    for key, value in stats.items():
        table.add_row(key.replace("_", " ").title(), str(value))

    console.print(table)


@cli.group()
def config() -> None:
    """Inspect or initialize local configuration."""


@config.command("init")
@pass_context
def config_init(ctx: Context) -> None:
    """Create the default configuration files."""
    ctx.config.save()
    console.print(f"[green]Configuration saved to {ctx.config.config_path}[/green]")


@config.command("path")
@pass_context
def config_path(ctx: Context) -> None:
    """Show the current config path."""
    console.print(ctx.config.config_path)


@cli.command()
@click.option("-l", "--limit", default=10, show_default=True, help="Number of results to show.")
@pass_context
def popular(ctx: Context, limit: int) -> None:
    """Show popular manga entries."""

    async def _popular() -> None:
        provider = ctx.get_provider()
        items = await provider.get_popular(limit=limit)
        if not items:
            console.print("[yellow]No popular entries available.[/yellow]")
            return

        table = Table(title="Popular Manga")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Title", style="green")
        table.add_column("Author", style="blue")

        for index, manga in enumerate(items, 1):
            table.add_row(str(index), manga.title, manga.author or "Unknown")

        console.print(table)

    asyncio.run(_popular())


@cli.command()
@click.option("-l", "--limit", default=10, show_default=True, help="Number of results to show.")
@pass_context
def trending(ctx: Context, limit: int) -> None:
    """Show trending manga entries."""

    async def _trending() -> None:
        provider = ctx.get_provider()
        items = await provider.get_trending(limit=limit)
        if not items:
            console.print("[yellow]No trending entries available.[/yellow]")
            return

        table = Table(title="Trending Manga")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Title", style="green")
        table.add_column("Author", style="blue")

        for index, manga in enumerate(items, 1):
            table.add_row(str(index), manga.title, manga.author or "Unknown")

        console.print(table)

    asyncio.run(_trending())
