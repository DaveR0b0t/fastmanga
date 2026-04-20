# Contributing to FastManga

Thanks for taking a look at FastManga.

## Project status

This repository is an educational CLI prototype. Please keep changes practical and aligned with the current scope.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run checks

```bash
pytest
black fastmanga tests
ruff check fastmanga tests
```

## Guidelines

- Keep the CLI behavior simple and readable
- Prefer small, focused pull requests
- Avoid adding large unfinished feature stubs
- Update docs when behavior changes
- Keep test coverage in place for core behavior

## Good first areas

- CLI wording and help text
- Test coverage improvements
- Provider fallback improvements
- Reader and downloader polish
- Packaging cleanup

## Before opening a PR

- Run the test suite
- Check `python -m fastmanga --help`
- Make sure README examples still match the CLI
