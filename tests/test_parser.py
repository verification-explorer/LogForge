"""Tests for parser.py, derived from spec.md §3.1 and Appendix A.4."""

from datetime import datetime, timezone

import pytest

from logforge.parser import parse_line, ParseResult


class TestValidLines:
    """Tests for lines that must parse successfully."""

    def test_clf_example_from_spec(self) -> None:
        """The CLF example line from §3.1 must parse correctly."""
        line = '127.0.0.1 - - [25/Aug/2026:14:32:10 +0000] "GET /api/v1/resource HTTP/1.1" 200 452'
        result = parse_line(line)
        assert result is not None
        assert result.ip == "127.0.0.1"
        assert result.timestamp == datetime(2026, 8, 25, 14, 32, 10, tzinfo=timezone.utc)
        assert result.method == "GET"
        assert result.path == "/api/v1/resource"
        assert result.status == 200
        assert result.size == 452

    def test_combined_example_from_spec(self) -> None:
        """The Combined example line from §3.1 must parse correctly.

        Combined's trailing fields (referrer, user-agent) are optional,
        parsed when present, and discarded per §3.1.
        """
        line = '127.0.0.1 - - [25/Aug/2026:14:32:10 +0000] "GET /api/v1/resource HTTP/1.1" 200 452 "https://example.com/" "curl/8.4.0"'
        result = parse_line(line)
        assert result is not None
        assert result.ip == "127.0.0.1"
        assert result.timestamp == datetime(2026, 8, 25, 14, 32, 10, tzinfo=timezone.utc)
        assert result.method == "GET"
        assert result.path == "/api/v1/resource"
        assert result.status == 200
        assert result.size == 452

    def test_response_size_dash_is_zero(self) -> None:
        """A literal '-' for response size means zero bytes and is valid.

        Per §3.1 and A.4 G1: '-' is stored as 0, and the line is valid,
        not malformed.
        """
        line = '127.0.0.1 - - [25/Aug/2026:14:32:10 +0000] "GET /empty HTTP/1.1" 304 -'
        result = parse_line(line)
        assert result is not None
        assert result.size == 0

    def test_ipv6_address(self) -> None:
        """IPv6 addresses must be accepted per §3.1 and A.4 G2.

        Validation uses ipaddress.ip_address() from stdlib.
        """
        line = '::1 - - [25/Aug/2026:14:32:10 +0000] "GET /api HTTP/1.1" 200 100'
        result = parse_line(line)
        assert result is not None
        assert result.ip == "::1"

    def test_all_iana_methods(self) -> None:
        """All nine IANA-registered methods must be accepted per §3.1 and A.4 G3."""
        methods = ["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH", "CONNECT", "TRACE"]
        for method in methods:
            line = f'127.0.0.1 - - [25/Aug/2026:14:32:10 +0000] "{method} /api HTTP/1.1" 200 100'
            result = parse_line(line)
            assert result is not None, f"Method {method} should be accepted"
            assert result.method == method

    def test_crlf_line_endings(self) -> None:
        """Lines with CRLF endings must parse correctly.

        Per §3.1 (S11): trailing \\r and \\n are stripped before parsing.
        """
        line = '127.0.0.1 - - [25/Aug/2026:14:32:10 +0000] "GET /api HTTP/1.1" 200 100\r\n'
        result = parse_line(line)
        assert result is not None
        assert result.path == "/api"


class TestMalformedLines:
    """Tests for lines that must be rejected."""

    def test_non_iana_method_rejected(self) -> None:
        """Non-IANA HTTP methods are malformed per §3.1 and A.4 G3."""
        line = '127.0.0.1 - - [25/Aug/2026:14:32:10 +0000] "INVALID /api HTTP/1.1" 200 100'
        result = parse_line(line)
        assert result is None

    def test_blank_line_rejected(self) -> None:
        """Blank lines (empty or whitespace-only) are malformed per §3.1 and A.4 G6."""
        assert parse_line("") is None
        assert parse_line("   ") is None
        assert parse_line("\t\t") is None

    def test_comment_line_rejected(self) -> None:
        """Lines beginning with '#' are comments and skipped per §3.1 and A.4 G6."""
        assert parse_line("# This is a comment") is None
        assert parse_line("#") is None

    def test_corrupt_line_rejected(self) -> None:
        """Lines that don't match the CLF/Combined regex are malformed per §3.1."""
        assert parse_line("not a log line at all") is None
        assert parse_line("127.0.0.1 incomplete") is None
        assert parse_line('127.0.0.1 - - [invalid timestamp] "GET / HTTP/1.1" 200 100') is None

    def test_invalid_ip_rejected(self) -> None:
        """Invalid IP addresses are malformed per §3.1 and A.4 G2."""
        line = 'not.an.ip.address - - [25/Aug/2026:14:32:10 +0000] "GET /api HTTP/1.1" 200 100'
        result = parse_line(line)
        assert result is None


class TestTimestampNormalization:
    """Tests for timestamp handling per §3.1."""

    def test_timestamp_normalized_to_utc(self) -> None:
        """Timestamps are normalized to UTC per §3.1."""
        # +0530 is 5 hours 30 minutes ahead of UTC
        line = '127.0.0.1 - - [25/Aug/2026:20:02:10 +0530] "GET /api HTTP/1.1" 200 100'
        result = parse_line(line)
        assert result is not None
        # 20:02:10 +0530 = 14:32:10 UTC
        assert result.timestamp == datetime(2026, 8, 25, 14, 32, 10, tzinfo=timezone.utc)

    def test_negative_timezone_offset(self) -> None:
        """Negative timezone offsets are handled correctly."""
        line = '127.0.0.1 - - [25/Aug/2026:09:32:10 -0500] "GET /api HTTP/1.1" 200 100'
        result = parse_line(line)
        assert result is not None
        # 09:32:10 -0500 = 14:32:10 UTC
        assert result.timestamp == datetime(2026, 8, 25, 14, 32, 10, tzinfo=timezone.utc)
