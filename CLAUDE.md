# LogForge

See `spec.md` (Revision 2.1) for all requirements and decisions.

## Quick commands

```bash
uv run ruff check src tests   # lint
uv run mypy src               # type check
uv run pytest                 # test (90% branch coverage required)
```

## What's not obvious

- `cli.py` contains no SQL; queries live in `reporter.py`
- Test fixtures in `tests/fixtures/` must not be line-ending normalized
