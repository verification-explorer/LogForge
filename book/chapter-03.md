# Chapter 3 — Test-Driven Development with Claude Code

**Depends on:** Chapter 2, which set up the workspace and `CLAUDE.md`.
**Sets up:** Chapter 4, which adds enforcement so the loop can't be skipped.

## 🎯 The goal

Ship `parser.py` using the red-green-refactor loop. By the end of this chapter, thirteen tests derived from the spec pass, the implementation has 100% branch coverage, and the git history proves the order: tests committed first, then a red run captured, then the implementation iterated to green.

The real deliverable isn't the parser — it's the answer to a question: does writing tests first actually constrain the implementation, or is it theatre?

## 🧠 The decision

Which Claude Code primitive owns "test-driven development"?

**Not a hook.** You could hook `pre-commit` to reject commits without passing tests, but that's enforcement after the fact. A hook can't make you write tests *before* implementation — it can only reject the commit if you didn't. That's Chapter 4's territory.

**Not CLAUDE.md instructions.** You could write "always write tests first" in `CLAUDE.md`, and Claude Code would try to follow it. But "try" is the problem. Instructions are suggestions the model can override when it thinks it knows better. The model routinely writes a function and its test in the same breath, which looks like TDD but isn't — the test was designed to pass the implementation that already exists in the model's context, not to specify behavior before implementation.

**Not a skill.** A skill runs once per invocation. TDD is a loop: write a test, run it red, implement, run it green, repeat. The loop lives in the conversation, not in a one-shot skill.

**Plan mode for the tests, then direct execution for the loop.** Start in plan mode to write the test file without accidentally scaffolding the implementation. Exit plan mode, run pytest to capture the red output, then iterate. The discipline is manual, which is exactly what this chapter is testing — whether the manual discipline produces anything a hook couldn't enforce.

What I rejected: a `tdd` skill that automates the loop. It would work, but it would hide the part this chapter needs to examine — whether the "red" phase contains real information or is just a formality before the implementation I already designed.

## 💬 The prompts

**Prompt 1 — tests only:**

```
Write tests/test_parser.py derived from spec.md §3.1 and Appendix A.4 items G1,
G2, G3, G6. Every test case must trace to a spec clause.

At minimum cover:
- The CLF example line from the spec
- The Combined example line from the spec
- A "-" response size (G1)
- An IPv6 address (G2)
- A rejected non-IANA method (G3)
- A blank line (G6)
- A "#" comment line (G6)
- A corrupt line
- CRLF line endings (S11)

Do not implement parser.py. The stub should export parse_line and ParseResult so
the tests can import them, but parse_line should return None unconditionally.
```

This produced 13 test cases across three classes: `TestValidLines` (6 tests for lines that must parse), `TestMalformedLines` (5 tests for lines that must be rejected), and `TestTimestampNormalization` (2 tests for UTC conversion).

**Prompt 2 — capture the red run:**

```
Run: uv run pytest tests/test_parser.py -v
```

**Prompt 3 — iterate to green:**

```
Implement parser.py. Run pytest after each change. Keep iterating until all
tests pass, then run ruff check and mypy.
```

## 🔧 The artifacts

### Red run output (verbatim)

```
============================= test session starts =============================
platform win32 -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0
plugins: cov-7.1.0
collected 13 items

tests/test_parser.py::TestValidLines::test_clf_example_from_spec FAILED  [  7%]
tests/test_parser.py::TestValidLines::test_combined_example_from_spec FAILED [ 15%]
tests/test_parser.py::TestValidLines::test_response_size_dash_is_zero FAILED [ 23%]
tests/test_parser.py::TestValidLines::test_ipv6_address FAILED           [ 30%]
tests/test_parser.py::TestValidLines::test_all_iana_methods FAILED       [ 38%]
tests/test_parser.py::TestValidLines::test_crlf_line_endings FAILED      [ 46%]
tests/test_parser.py::TestMalformedLines::test_non_iana_method_rejected PASSED [ 53%]
tests/test_parser.py::TestMalformedLines::test_blank_line_rejected PASSED [ 61%]
tests/test_parser.py::TestMalformedLines::test_comment_line_rejected PASSED [ 69%]
tests/test_parser.py::TestMalformedLines::test_corrupt_line_rejected PASSED [ 76%]
tests/test_parser.py::TestMalformedLines::test_invalid_ip_rejected PASSED [ 84%]
tests/test_parser.py::TestTimestampNormalization::test_timestamp_normalized_to_utc FAILED [ 92%]
tests/test_parser.py::TestTimestampNormalization::test_negative_timezone_offset FAILED [100%]

================================== FAILURES ===================================
__________________ TestValidLines.test_clf_example_from_spec __________________

    def test_clf_example_from_spec(self) -> None:
        """The CLF example line from §3.1 must parse correctly."""
        line = (
            '127.0.0.1 - - [25/Aug/2026:14:32:10 +0000] '
            '"GET /api/v1/resource HTTP/1.1" 200 452'
        )
        result = parse_line(line)
>       assert result is not None
E       assert None is not None

tests\test_parser.py:17: AssertionError
...
=========================== short test summary info ===========================
FAILED tests/test_parser.py::TestValidLines::test_clf_example_from_spec
FAILED tests/test_parser.py::TestValidLines::test_combined_example_from_spec
FAILED tests/test_parser.py::TestValidLines::test_response_size_dash_is_zero
FAILED tests/test_parser.py::TestValidLines::test_ipv6_address
FAILED tests/test_parser.py::TestValidLines::test_all_iana_methods
FAILED tests/test_parser.py::TestValidLines::test_crlf_line_endings
FAILED tests/test_parser.py::TestTimestampNormalization::test_timestamp_normalized_to_utc
FAILED tests/test_parser.py::TestTimestampNormalization::test_negative_timezone_offset
========================= 8 failed, 5 passed in 0.23s =========================
```

Note: 5 tests passed immediately — all the "malformed line" tests. The stub returns `None` for everything, which is the correct behavior for malformed input. This is information: the test suite distinguishes "should parse" from "should reject" by whether `None` is the expected result.

### Iteration log

**Iteration 1:** Wrote the full implementation — regex pattern, IP validation with `ipaddress.ip_address()`, IANA method whitelist, timestamp parsing with timezone normalization, response size `-` handling.

Result: 12 passed, 1 failed.

```
tests/test_parser.py::TestMalformedLines::test_corrupt_line_rejected FAILED

    def test_corrupt_line_rejected(self) -> None:
        """Lines that don't match the CLF/Combined regex are malformed per §3.1."""
        assert parse_line("not a log line at all") is None
        assert parse_line("127.0.0.1 incomplete") is None
>       assert parse_line('127.0.0.1 - - [invalid timestamp] "GET / HTTP/1.1" 200 100') is None

src\logforge\parser.py:91: in parse_line
    timestamp = _parse_timestamp(ts_str)
src\logforge\parser.py:41: in _parse_timestamp
    dt = datetime.strptime(dt_part, "%d/%b/%Y:%H:%M:%S")
E   ValueError: time data 'invalid' does not match format '%d/%b/%Y:%H:%M:%S'
```

The regex matched the line (brackets captured "invalid timestamp"), then `strptime` raised `ValueError` on the malformed date. The implementation assumed regex match implied valid timestamp.

**Fix:** Wrap timestamp parsing in `try/except ValueError: return None`.

**Iteration 2:** All 13 tests pass.

```
============================= 13 passed in 0.16s ==============================
```

Ran `ruff check` and `mypy src` — both clean after fixing import order and switching `timezone.utc` to `datetime.UTC` per ruff's UP017 rule.

### Green run output (verbatim)

```
============================= test session starts =============================
platform win32 -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0
plugins: cov-7.1.0
collected 14 items

tests/test_parser.py::TestValidLines::test_clf_example_from_spec PASSED  [  7%]
tests/test_parser.py::TestValidLines::test_combined_example_from_spec PASSED [ 14%]
tests/test_parser.py::TestValidLines::test_response_size_dash_is_zero PASSED [ 21%]
tests/test_parser.py::TestValidLines::test_ipv6_address PASSED           [ 28%]
tests/test_parser.py::TestValidLines::test_all_iana_methods PASSED       [ 35%]
tests/test_parser.py::TestValidLines::test_crlf_line_endings PASSED      [ 42%]
tests/test_parser.py::TestMalformedLines::test_non_iana_method_rejected PASSED [ 50%]
tests/test_parser.py::TestMalformedLines::test_blank_line_rejected PASSED [ 57%]
tests/test_parser.py::TestMalformedLines::test_comment_line_rejected PASSED [ 64%]
tests/test_parser.py::TestMalformedLines::test_corrupt_line_rejected PASSED [ 71%]
tests/test_parser.py::TestMalformedLines::test_invalid_ip_rejected PASSED [ 78%]
tests/test_parser.py::TestTimestampNormalization::test_timestamp_normalized_to_utc PASSED [ 85%]
tests/test_parser.py::TestTimestampNormalization::test_negative_timezone_offset PASSED [ 92%]
tests/test_placeholder.py::test_version PASSED                           [100%]

=============================== tests coverage ================================
Name                       Stmts   Miss Branch BrPart  Cover   Missing
----------------------------------------------------------------------
src\logforge\parser.py        45      0      8      0   100%
----------------------------------------------------------------------
============================= 14 passed in 0.21s ==============================
```

### parser.py (final)

```python
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
```

### test_parser.py (final)

The full test file is in `tests/test_parser.py`. Key structure:

- **TestValidLines** (6 tests): CLF example, Combined example, `-` response size, IPv6, all IANA methods, CRLF endings
- **TestMalformedLines** (5 tests): non-IANA method, blank lines, comment lines, corrupt lines, invalid IP
- **TestTimestampNormalization** (2 tests): positive and negative timezone offsets

Each test docstring cites the spec clause it verifies (e.g., "per §3.1 and A.4 G1").

## 🔥 What went wrong

**The invalid timestamp test caught a real bug.** The first implementation assumed that if the regex matched, the timestamp was valid. The regex captures anything inside brackets — `[invalid timestamp]` matches just fine. The `strptime` call then raised `ValueError`, which propagated up as an uncaught exception instead of returning `None` for malformed input.

This is exactly the kind of bug TDD is supposed to catch: a failure mode that exists in the gap between "structurally matches the pattern" and "semantically valid data." Without `test_corrupt_line_rejected`, the parser would crash on real-world log files containing garbage lines instead of gracefully skipping them.

**The "tests first" discipline was partially theatre.** I wrote the tests by reading the spec, but I was simultaneously designing the parser in my head. When I wrote `test_response_size_dash_is_zero`, I already knew I'd handle it with `0 if size_str == "-" else int(size_str)`. The test didn't *discover* that requirement — it *documented* a requirement I'd already internalized from reading §3.1 and A.4 G1.

The honest assessment: the spec-to-test phase was genuine — I translated spec clauses into assertions without writing implementation code. But "without writing implementation code" doesn't mean "without designing the implementation." The regex pattern, the validation order, the error handling strategy — all of that was designed while writing the tests, not discovered by running them.

What the red run *did* contribute: it caught the timestamp exception bug, and it confirmed that the "should reject" tests passed against the stub (proving the tests distinguish valid from invalid input, not just "does parse_line return something"). That's real signal, even if the overall shape of the implementation was predetermined.

**The /loop experiment was useful but overkill for this task.** I used `/loop 2m` to schedule recurring edge-case checks — IPv6 zone IDs, mapped addresses, timestamp day rollovers. The parser handled all of them correctly without changes. The loop was cancelled after one iteration because there was nothing to fix.

The lesson: `/loop` is valuable when you expect iterative refinement (watching a build, polling for changes), but for a bounded edge-case audit it's simpler to just do the audit once. Scheduled checks make sense when the thing you're checking might change; the parser wasn't changing while I was checking it.

**Coverage was 100% without adding tests post-hoc.** The 13 tests derived from the spec exercised all 45 statements and all 8 branches in parser.py. I did not have to add coverage-chasing tests to hit the 90% gate.

This is the argument for spec-first testing: if the spec is complete, tests derived from it will naturally cover the implementation. The coverage gate validates that the spec (and thus the tests) didn't miss anything — but in this case, it didn't need to catch anything because the spec was already thorough. Chapter 4 will address what happens when the spec *isn't* thorough and the coverage gate has to do real work.

**I committed lint violations to main and didn't notice.** `CLAUDE.md` — written in Chapter 2, in this repo, listing `uv run ruff check src tests` as the first quick command — instructs running ruff. Chapter 2 configured it: `line-length = 88`, `select = ["E", "F", "I", "W", "UP", "B", "SIM"]`. I did not run it before committing `4f4f77c` ("Add tests for parser.py derived from spec.md §3.1").

Running ruff against that commit's `tests/test_parser.py` after the fact:

```
Found 19 errors.
```

Eleven `E501` (line too long, the worst at 135 characters against an 88-character limit), four `UP017` (`timezone.utc` instead of `datetime.UTC`), two `F401` (`pytest` and `ParseResult` imported but unused), one `I001` (unsorted imports). The stub in `src/logforge/parser.py` from the same commit was clean; every violation was in the test file.

The line-wrapping in `e35fe7e` ("Implement parser.py — all tests green") looks like test churn in the diff, but it isn't. That commit's `tests/test_parser.py` diff is entirely ruff remediation — the long string literals split across implicit-concatenation parentheses, the unused imports dropped, `timezone.utc` swapped for its `UTC` alias, one long assertion extracted to a local named `corrupt`. Both versions define the same 13 test functions and contain the same 36 assertions. No expected value changed, no test case was added or removed, and `UTC` *is* `timezone.utc` — the same object under a newer name. Nothing about what the tests assert is different across those two commits.

The gap between them, by committer date:

```
$ git log -1 --format=%ci 4f4f77c
2026-08-26 10:50:42 +0300
$ git log -1 --format=%ci e35fe7e
2026-08-26 11:04:59 +0300
```

**14 minutes and 17 seconds.** For fourteen minutes, `main` held code that violated the project's own configured lint rules, and it was cleaned up only because the next commit happened to touch those same lines while I was chasing green tests. Not because anything told me to. The instruction to run ruff was sitting in `CLAUDE.md` the entire time. The commit succeeded. Nothing failed. Nothing warned.

This is the gap Chapter 4 closes — an instruction in `CLAUDE.md` is advice, and advice is what you follow when you remember to.

## ✅ Takeaway

- **Write tests from the spec, not from the implementation.** Each test docstring cites a spec clause. This creates traceability and ensures the tests verify requirements, not implementation details.

- **The red run has real signal even when the implementation is pre-designed.** Five "should reject" tests passed against the stub — proof that the test suite distinguishes valid from invalid input. The invalid-timestamp test caught a genuine exception-handling bug.

- **Commit order matters.** The git history shows tests committed before implementation. This is the only durable proof that TDD happened. A hook could enforce this in CI, but that's Chapter 4.

- **100% branch coverage from spec-derived tests is possible when the spec is complete.** The spec enumerated every validation rule, every edge case, every error condition. The tests covered them all. No coverage-chasing was needed.

- **The loop primitive (`/loop`) is for watching, not for bounded tasks.** Scheduled checks make sense when the target might change between iterations. For a one-shot audit, just do the audit.

- **"Tests first" is partially theatre, but the theatre has value.** The discipline of writing tests before implementation — even when you've already designed the implementation in your head — creates artifacts (the test file, the red run, the git history) that make the process auditable. The artifacts matter even if the cognitive process wasn't as pure as the methodology claims.
