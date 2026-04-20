# FastManga Quick Start

## Install from a local checkout

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Initialize config

```bash
fastmanga config init
```

## Search for manga

```bash
fastmanga search "One Piece"
```

## Read a chapter

```bash
fastmanga read "Naruto" -c 1
```

## Download chapters

```bash
fastmanga download "Berserk" -c 1-5
```

## Explore built-in lists

```bash
fastmanga popular -l 10
fastmanga trending -l 10
```

## View library data

```bash
fastmanga library list
fastmanga library stats
```

## Run tests

```bash
pytest
```

## Current scope

FastManga is a CLI prototype. Some ideas mentioned elsewhere in the repo, like MyAnimeList sync, queue workers, and a full TUI, are future work and are not part of the current working command set.
