# FastManga

FastManga is a Python command line manga reader and downloader concept built for learning and experimentation. The current project includes a working CLI, local config and library storage, a MangaDex provider with offline fallback data, and a small test suite.

## Current status

This repository is best described as an educational prototype.

Implemented today:
- CLI commands for search, read, download, popular, trending, config, and library
- Local SQLite-backed library and reading history
- Manga, chapter, and page models
- MangaDex provider structure with mock fallback data for offline use and demos
- Basic tests for core models, config, database, and provider behavior

Not implemented yet:
- MyAnimeList sync
- Background queue workers
- Multi-provider support beyond the MangaDex provider module
- A full Textual TUI experience
- Production-grade image rendering pipeline

## Install

Install directly from GitHub:

```bash
pip install git+https://github.com/DaveR0b0t/fastmanga.git
```

Install from a local checkout:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Run the CLI:

```bash
fastmanga --help
```

Or:

```bash
python -m fastmanga --help
```

## Quick usage

Initialize config:

```bash
fastmanga config init
```

Search:

```bash
fastmanga search "One Piece"
```

Read a chapter:

```bash
fastmanga read "Naruto" -c 1
```

Download chapters:

```bash
fastmanga download "Berserk" -c 1-3
```

Show popular and trending entries:

```bash
fastmanga popular -l 10
fastmanga trending -l 10
```

View your library:

```bash
fastmanga library list
fastmanga library stats
```

## Project layout

```text
fastmanga/
├── cli/
├── core/
├── providers/
├── utils/
└── __main__.py
```

## Development

Install dev tools:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

Format and lint:

```bash
black fastmanga tests
ruff check fastmanga tests
```

## License

MIT
