"""Simple demo entry point for FastManga."""

from rich.console import Console
from rich.panel import Panel

console = Console()


def main() -> None:
    console.print(
        Panel.fit(
            "FastManga demo\n\nTry these commands:\n- fastmanga --help\n- fastmanga search \"One Piece\"\n- fastmanga popular -l 5",
            title="FastManga Demo",
            border_style="blue",
        )
    )


if __name__ == "__main__":
    main()
