"""Small example showing how to use the provider in Python."""

import asyncio

from fastmanga.providers.mangadex import MangaDexProvider


async def main() -> None:
    provider = MangaDexProvider()
    try:
        results = await provider.search("One Piece", limit=3)
        for manga in results:
            print(manga.title)
    finally:
        await provider.close()


if __name__ == "__main__":
    asyncio.run(main())
