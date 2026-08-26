"""Log regex parsing and data validation."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ParseResult:
    """Result of parsing a single log line."""

    ip: str
    timestamp: datetime
    method: str
    path: str
    status: int
    size: int


def parse_line(line: str) -> ParseResult | None:
    """Parse a single CLF/Combined log line.

    Returns ParseResult on success, None on malformed input.
    """
    return None
