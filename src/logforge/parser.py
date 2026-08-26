"""Log regex parsing and data validation."""

import ipaddress
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone


@dataclass
class ParseResult:
    """Result of parsing a single log line."""

    ip: str
    timestamp: datetime
    method: str
    path: str
    status: int
    size: int


IANA_METHODS = frozenset({
    "GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH", "CONNECT", "TRACE"
})

CLF_COMBINED_PATTERN = re.compile(
    r'^(\S+)'                           # IP address
    r' \S+ \S+'                         # ident and authuser (both ignored, often "-")
    r' \[([^\]]+)\]'                    # timestamp in brackets
    r' "(\S+) (\S+) [^"]+"'             # "METHOD path HTTP/x.x"
    r' (\d+)'                           # status code
    r' (\d+|-)'                         # response size (or "-")
    r'(?: "[^"]*" "[^"]*")?'            # optional Combined fields (discarded)
    r'$'
)


def _parse_timestamp(ts_str: str) -> datetime:
    """Parse CLF timestamp and normalize to UTC."""
    # Format: 25/Aug/2026:14:32:10 +0000
    dt_part, tz_part = ts_str.rsplit(" ", 1)
    dt = datetime.strptime(dt_part, "%d/%b/%Y:%H:%M:%S")

    # Parse timezone offset
    tz_sign = 1 if tz_part[0] == "+" else -1
    tz_hours = int(tz_part[1:3])
    tz_minutes = int(tz_part[3:5])
    tz_offset = timedelta(hours=tz_hours, minutes=tz_minutes) * tz_sign

    # Create aware datetime and convert to UTC
    dt_aware = dt.replace(tzinfo=timezone(tz_offset))
    return dt_aware.astimezone(UTC)


def parse_line(line: str) -> ParseResult | None:
    """Parse a single CLF/Combined log line.

    Returns ParseResult on success, None on malformed input.
    """
    # Strip trailing line endings per §3.1 (S11)
    line = line.rstrip("\r\n")

    # Blank lines are skipped silently per §3.1 (G6)
    if not line or line.isspace():
        return None

    # Comment lines are skipped silently per §3.1 (G6)
    if line.startswith("#"):
        return None

    # Try to match the CLF/Combined pattern
    match = CLF_COMBINED_PATTERN.match(line)
    if not match:
        return None

    ip_str, ts_str, method, path, status_str, size_str = match.groups()

    # Validate IP address per §3.1 (G2)
    try:
        ipaddress.ip_address(ip_str)
    except ValueError:
        return None

    # Validate HTTP method per §3.1 (G3)
    if method not in IANA_METHODS:
        return None

    # Parse response size - "-" means 0 per §3.1 (G1)
    size = 0 if size_str == "-" else int(size_str)

    # Parse and normalize timestamp
    try:
        timestamp = _parse_timestamp(ts_str)
    except ValueError:
        return None

    return ParseResult(
        ip=ip_str,
        timestamp=timestamp,
        method=method,
        path=path,
        status=int(status_str),
        size=size,
    )
