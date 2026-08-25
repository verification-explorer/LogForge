# Software Requirements Specification (SRS)

## Project Name: LogForge
## Target: Core Specification for Claude Code Autonomous Implementation

**Revision 2.1 — 2026-08-25.** Revision 1 (`5db7b7e`) was structurally corrupted and
contained unresolved ambiguities. See Appendix A for every change and its rationale.

---

## 1. Project Overview & Objective

LogForge is a local, high-performance command-line interface (CLI) data pipeline
designed to parse, clean, and analyze unstructured raw server log files. The parsed
data is structured and stored in a local SQLite database, allowing users to query
metrics and generate markdown summary reports.

This project serves as a testing ground for Claude Code's agentic looping,
self-debugging, and test-driven development (TDD) execution capabilities.

**Performance target:** ingest sustains at least 25,000 lines per second on a single
core for a well-formed 1M-line file. Rationale: "high-performance" was previously
unmeasurable, so nothing could be tested or regressed against it. This figure is the
one number in this document not derivable from Revision 1 — treat it as provisional
and reset it once real measurements exist.

**Bulk insert strategy:** rows are inserted in batches of 5,000 within a single
transaction per file. Rationale: balances memory footprint against transaction
overhead; a 1M-line file commits once, not 200 times or 1M times.

---

## 2. Technical Stack & Constraints

* **Language:** Python 3.12+ (strict type hinting required on all functions)
* **Package & Environment Manager:** `uv` (Astral)
* **Code Quality:** `ruff` for formatting and linting
* **Type Checking:** `mypy` in strict mode, with `disallow_any_explicit = true` in
  `pyproject.toml`. Rationale: without this flag, a function typed `Any -> Any` passes
  strict mode and defeats the purpose.
* **Testing Framework:** `pytest` with `pytest-cov`. Branch coverage of `src/logforge/`
  must exceed 90%; the build fails below that threshold. Rationale: line coverage is
  satisfiable by importing every module without asserting anything; branch coverage
  requires exercising both arms of conditionals.
* **Database:** SQLite via the built-in `sqlite3` module. No ORM, no abstraction layer.
* **CLI Engine:** `click`
* **Version control:** test fixture log files are byte-exact inputs and must not be
  line-ending normalized by git.

---

## 3. Core Architecture & Components

```
LogForge/
├── CLAUDE.md             # Project guidelines and build commands
├── spec.md               # This document
├── pyproject.toml        # Project metadata and dependencies managed by uv
├── README.md             # High-level documentation
├── src/
│   └── logforge/
│       ├── __init__.py
│       ├── cli.py        # CLI argument parsing and commands
│       ├── parser.py     # Log regex parsing and data validation
│       ├── database.py   # SQLite schema and CRUD operations
│       └── reporter.py   # Markdown summary generation and stats queries
└── tests/                # Parallel structure matching src/ for pytest
```

The repository root is `LogForge/`; the importable package is `logforge`.

### 3.1. Data Ingestion & Parser (`parser.py`)

* **Input:** Common Log Format (CLF) **and** Combined Log Format. A single regex
  accepts both: the two Combined-only trailing fields (referrer, user-agent) are
  optional, parsed when present, and discarded.
  * *Example line (CLF):*
    `127.0.0.1 - - [25/Aug/2026:14:32:10 +0000] "GET /api/v1/resource HTTP/1.1" 200 452`
  * *Example line (Combined):*
    `127.0.0.1 - - [25/Aug/2026:14:32:10 +0000] "GET /api/v1/resource HTTP/1.1" 200 452 "https://example.com/" "curl/8.4.0"`
* **Extraction Fields:**
  * IP Address (IPv4 or IPv6). Validation uses `ipaddress.ip_address()` from the
    standard library; any string that function rejects is a malformed line. Rationale:
    regex cannot correctly validate IPv6 zone IDs or mapped addresses; the stdlib can.
  * Timestamp (parsed into a datetime, normalized to UTC)
  * HTTP Method. One of the nine IANA-registered methods: `GET`, `POST`, `PUT`,
    `DELETE`, `HEAD`, `OPTIONS`, `PATCH`, `CONNECT`, `TRACE`. Any other value is a
    malformed line. Rationale: accepting arbitrary strings would allow garbage through
    and complicate downstream analysis.
  * Requested Path (e.g. `/api/v1/resource`)
  * Status Code (integer, e.g. `200`, `404`, `500`)
  * Response Size (integer, bytes). A literal `-` in this field means zero bytes and
    is stored as `0`. Such a line is **valid** and must not be skipped.
* **Line endings:** each line is stripped of trailing `\r` and `\n` before parsing.
* **Malformed lines:** a line is malformed if it is blank (empty or whitespace-only),
  begins with `#` (comment), or fails to match the CLF/Combined regex, or fails IP or
  method validation. Blank and comment lines are skipped silently; regex and validation
  failures emit warnings per the throttling rule below. Rationale: blank and comment
  lines are intentional non-data; regex failures are corruption worth reporting.
* **Resilience:** handle malformed or corrupted log rows gracefully by logging
  warnings to `stderr` and skipping the line instead of crashing the pipeline.
  Warnings are emitted at most once per 1,000 skipped lines, plus a final total on
  completion.

### 3.2. Storage Layer (`database.py`)

* **Database:** local SQLite database file, initialized automatically if missing.
  Default location `./logforge.db`, overridable with the `LOGFORGE_DB` environment
  variable.
* **Corrupt database:** if the file exists but is not a valid SQLite database (e.g.,
  the header bytes do not match), `database.py` raises a descriptive error and the
  command exits 1 without modifying the file. Rationale: silent overwrite would destroy
  user data; silent skip would hide the problem.
* **Schema:**

```sql
  CREATE TABLE logs (
      id             INTEGER PRIMARY KEY AUTOINCREMENT,
      source_file_id INTEGER NOT NULL REFERENCES ingested_files(id),
      ip             TEXT    NOT NULL,
      timestamp      TEXT    NOT NULL,  -- ISO 8601, UTC: YYYY-MM-DDTHH:MM:SS+00:00
      method         TEXT    NOT NULL,
      path           TEXT    NOT NULL,
      status         INTEGER NOT NULL,
      size           INTEGER NOT NULL
  );

  CREATE INDEX idx_logs_status ON logs(status);
  CREATE INDEX idx_logs_path   ON logs(path);
  CREATE INDEX idx_logs_ip     ON logs(ip);

  CREATE TABLE ingested_files (
      id           INTEGER PRIMARY KEY AUTOINCREMENT,
      sha256       TEXT    NOT NULL UNIQUE,
      path         TEXT    NOT NULL,
      ingested_at  TEXT    NOT NULL,
      line_count   INTEGER NOT NULL,
      skipped_count INTEGER NOT NULL
  );
```

  Timestamps are stored as ISO 8601 TEXT in UTC, which sorts lexicographically in
  chronological order.

  **Indexes:** `status`, `path`, and `ip` are indexed because every §3.3 metric groups
  or filters on at least one of them. Without indexes the status breakdown, top-paths,
  and top-IPs queries scan the full table — unacceptable once the database holds
  millions of rows.

* **Operations:**
  * Bulk insertion in batches of 5,000 rows within a single transaction per file.
  * **Re-ingestion guard:** `ingest` computes the SHA-256 of the input file. If that
    hash is already present in `ingested_files`, the command is a no-op that reports
    the prior ingestion and exits 0. Duplicate *rows* are never suppressed.

### 3.3. Reporting Engine (`reporter.py`)

* **Functionality:** query the SQLite database to generate human-readable analytical
  metrics. All aggregate queries live here, including those backing `stats`.
* **Metrics Required:**
  * Total request count.
  * Total data transferred, in MB, where 1 MB = 1,000,000 bytes, to two decimals.
  * Breakdown of HTTP status codes: every distinct status code present in the database
    is reported with its count, sorted by status code ascending. Rationale: filtering
    to a fixed set (200/404/500) would hide unexpected codes like 418 or 599.
  * Top 5 most requested URL paths, by request count. If fewer than five distinct paths
    exist, report all of them. Rationale: "Top 5" means "up to 5"; requiring exactly 5
    would error on small datasets.
  * Top 5 most active IP addresses, by request count. If fewer than five distinct IPs
    exist, report all of them.
  * Ties in either "Top 5" are broken by ascending lexicographic order of the path or
    IP address, so output is deterministic.
* **Output:** save analytical output into a nicely formatted Markdown report file at
  the path supplied by `--output`, defaulting to `report.md` in the current directory.
  If the target path already exists, the file is overwritten without prompting.
  Rationale: prompting would break scripted pipelines; refusing would require the user
  to delete manually every time.

### 3.4. Command Line Interface (`cli.py`)

The pipeline exposes a clear terminal interface using the following command
structures:

```bash
# 1. Parse and ingest a log file into the database
logforge ingest <path_to_log_file>

# 2. Query the current database status (simple stdout summary)
logforge stats

# 3. Export data analysis into a markdown report file
logforge report --output <path_to_markdown_file>

# 4. Clear all existing records from the database
logforge clear --force
```

* `cli.py` parses arguments and delegates; it contains no SQL.
* `ingest`: if the input file does not exist or is not readable, print an error to
  `stderr` and exit 1. Do not create or modify the database.
* `stats`: prints a plain-text summary to `stdout` with the following format (one
  metric per line, label and value separated by a colon and space):
  ```
  Requests: 12345
  Data transferred: 67.89 MB
  Status 200: 10000
  Status 404: 2000
  Status 500: 345
  Top paths:
    /api/v1/users: 5000
    /api/v1/items: 3000
    ...
  Top IPs:
    192.168.1.1: 4000
    10.0.0.5: 2500
    ...
  ```
  Rationale: machine-parseable output enables shell pipelines without requiring JSON.
* `stats` and `report` against a missing or empty database print a message to `stderr`
  and exit 1. They do not create a database.
* `--force` on `clear` is mandatory. Without it, the command prints the current record
  count and exits 2 without deleting anything.
* **Exit codes:** 0 on success, 1 on a handled error (missing file, empty database),
  2 on a usage error.

---

## Appendix A. Amendment log

Revision 1 failed in three distinct ways, and each needed a different fix.

### A.1 Corrupted — the file itself was damaged

All four symptoms share one cause: rendered markdown was copied and pasted back as
source, which consumed emphasis markers and flattened block structure. A partial paste
landed first, then a fuller one.

| ID | Defect | Repair |
|---|---|---|
| C1 | The §3 directory tree was not fenced, so it rendered as one paragraph | Tree placed in a fenced block |
| C2 | `__init__.py` appeared as `init.py` (lines 25, 46) — `__init__` was consumed as bold emphasis | Restored. This one would have produced a non-importable package |
| C3 | Lines 1–28 were a truncated duplicate of §1–§3 | Removed; single document retained |
| C4 | Root directory named `logforge/`, repository named `LogForge` | Root is `LogForge/`, package is `logforge` |

The fenced `bash` block in §3.4 survived intact, underscores and angle brackets
included, which is consistent with this cause and means §3.4 was trustworthy as
written. Anything *outside* a fence was not.

### A.2 Contradictory — two parts could not both hold

| ID | Conflict | Decision and what was dropped |
|---|---|---|
| X1 | §3.1 named Combined Log Format, gave a Common Log Format example, and listed CLF's fields | Accept both; Combined's trailing fields optional and discarded. Nothing dropped — the field list stays CLF because no metric in §3.3 uses referrer or user-agent |
| X2 | "Prevent duplicate records if the same file is processed twice" vs. "a single table with an autoincrementing `id`" | File-level dedup by SHA-256. **The single-table constraint is dropped**, because file identity cannot be expressed in a table of log rows. Row-level dedup was rejected: byte-identical lines occur legitimately behind load balancers and on client retries, so it would silently destroy data |
| X3 | §3.3 fixed the output at `report.md`; §3.4 made it a required `--output` argument | `--output` is optional with a `report.md` default, satisfying both |
| X4 | "Strict type hinting required on all functions" with no type checker in the stack; ">90% coverage" with no coverage tool | Added `mypy` strict and `pytest-cov`. `ruff` lints annotation style but does not type-check, so the strictest requirement in Revision 1 was the only unenforceable one |
| X5 | Response Size declared `Integer`; CLF writes `-` for an empty response | `-` maps to `0` and the line is valid. Treating it as malformed would skip every 304 and corrupt the §3.3 transfer total, with no test derived from the spec catching it |
| X6 | §1 claimed high performance; §3.1 required a `stderr` warning per malformed row | Warnings throttled to 1 per 1,000, plus a final total |

### A.3 Silent — the spec did not say, so an implementer would have invented

| ID | Gap | Decision |
|---|---|---|
| S1 | `sqlite3` **or** an abstraction layer; `click` **or** `argparse` | `sqlite3` and `click`. One table, one backend — an abstraction layer buys nothing. `click` gives subcommands, flags, and exit codes that §3.4 would otherwise need by hand |
| S2 | How an ISO 8601 datetime is stored, given SQLite has no datetime type | UTC-normalized ISO 8601 TEXT; sorts chronologically |
| S3 | Where `logforge.db` lives | `./logforge.db`, overridable via `LOGFORGE_DB` |
| S4 | Behavior against a missing or empty database | Message to `stderr`, exit 1, no database created |
| S5 | Whether `--force` is required | Mandatory. Optional would make it decorative rather than a safety flag |
| S6 | Tie-breaking in "Top 5" | Ascending lexicographic, so reporter tests are not flaky |
| S7 | "Most active" IPs — by requests or by bytes | Request count |
| S8 | Which module owns `stats` | `reporter.py`. `cli.py` contains no SQL |
| S9 | MB definition | 1,000,000 bytes, two decimals |
| S10 | Exit codes | 0 success, 1 handled error, 2 usage error |
| S11 | Line endings on input | Trailing `\r` and `\n` stripped before parsing. A CRLF log read on a machine expecting LF would otherwise put `\r` inside the final field, making every line of a valid file look malformed |

### A.4 Revision 2 audit — defects and gaps closed in Revision 2.1

| ID | Issue | Decision |
|---|---|---|
| D1 | `mypy --strict` does not reject explicit `Any` annotations; every function could be `Any -> Any` | Added `disallow_any_explicit = true` to mypy config. Rationale: closes the loophole that would let an implementer defeat strict typing. |
| D2 | Line coverage is satisfiable by a test that imports all modules and asserts nothing | Changed to branch coverage. Rationale: branch coverage requires exercising conditional paths, not just touching lines. |
| G1 | Whether a literal `-` is valid for response size | Clarified: `-` is valid and stored as `0`. (Already in A.2 X5, now explicit in §3.1.) |
| G2 | IP validation: IPv4 and IPv6 both required; how validation is performed | Use `ipaddress.ip_address()` from stdlib. Rationale: regex cannot correctly handle all IPv6 forms. |
| G3 | HTTP method: whether any string is accepted or an enumerated set | Enumerated: the nine IANA-registered methods. Rationale: arbitrary strings would allow garbage. |
| G4 | Status code breakdown: whether all observed codes are reported or only some | All distinct codes present, sorted ascending. Rationale: a fixed set hides unexpected codes. |
| G5 | Top 5 queries: behavior when fewer than five distinct values exist | Report all that exist. Rationale: "Top 5" means "up to 5". |
| G6 | What counts as a malformed line: blank lines, comment lines, partial matches | Blank and `#`-prefixed lines skipped silently; regex/validation failures warn per throttle rule. Rationale: blanks and comments are intentional. |
| G7 | `stats`: the format of its stdout output | Specified label-colon-value format. Rationale: enables shell parsing without JSON. |
| G8 | `report --output`: behavior when the target path already exists | Overwrite without prompting. Rationale: prompting breaks scripted pipelines. |
| G9 | `ingest`: behavior when the input file does not exist or is not readable | Print error to `stderr`, exit 1, do not touch database. |
| G10 | Bulk insert: batch size and transaction boundaries | 5,000-row batches, one transaction per file. Rationale: balances memory vs. commit overhead for the 25k lines/sec target. |
| G11 | Behavior when `logforge.db` exists but is not a valid SQLite database | Raise descriptive error, exit 1, do not modify file. Rationale: silent overwrite destroys data. |
| G12 | Indexes on the `logs` table | Indexes on `status`, `path`, `ip`. Rationale: every §3.3 metric groups or filters on these columns. |
