"""Command-line interface for LogForge."""

import click


@click.group()
def main() -> None:
    """LogForge: parse, clean, and analyze server log files."""


@main.command()
@click.argument("path", type=click.Path(exists=True))
def ingest(path: str) -> None:
    """Parse and ingest a log file into the database."""
    raise NotImplementedError


@main.command()
def stats() -> None:
    """Query the current database status."""
    raise NotImplementedError


@main.command()
@click.option("--output", "-o", default="report.md", help="Output markdown file path")
def report(output: str) -> None:
    """Export data analysis into a markdown report file."""
    raise NotImplementedError


@main.command()
@click.option("--force", is_flag=True, help="Confirm deletion")
def clear(force: bool) -> None:
    """Clear all existing records from the database."""
    raise NotImplementedError
