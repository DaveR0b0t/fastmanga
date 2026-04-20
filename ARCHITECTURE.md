# FastManga Architecture

## Overview

FastManga is organized as a small CLI application with a few clear layers.

## Layers

### CLI
`fastmanga/cli/main.py`

Handles command parsing, user prompts, rich output, and wiring between the config, database, provider, and reader.

### Core
`fastmanga/core/`

Contains the main data models and local storage logic.

- `config.py` manages user settings and file paths
- `database.py` stores manga, chapters, history, and bookmarks
- `manga.py` defines the core models

### Providers
`fastmanga/providers/`

Defines the provider interface and the MangaDex implementation.

- `base.py` defines the provider contract
- `mangadex.py` handles remote fetches and offline fallback data

### Utilities
`fastmanga/utils/`

Contains reading and download helpers.

- `downloader.py` downloads and saves chapter images
- `reader.py` opens chapters for terminal or external viewing

## Current data flow

1. User runs a CLI command
2. CLI loads config and database
3. CLI requests data from the provider
4. Provider returns manga, chapters, or pages
5. Database stores local state
6. Reader or downloader handles chapter output

## Design notes

- The project favors readability over abstraction depth
- Offline fallback data helps local demos and tests
- SQLite keeps the local library simple
- Rich provides clearer terminal output without a heavy UI layer

## Current limitations

- Only one provider is wired in
- TUI support is not implemented
- Sync and background job systems are future ideas, not active subsystems
