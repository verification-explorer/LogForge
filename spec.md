# Software Requirements Specification (SRS)
## Project Name: LogForge
## Target: Core Specification for Claude Code Autonomous Implementation

---

## 1. Project Overview & Objective
LogForge is a local, high-performance command-line interface (CLI) data pipeline designed to parse, clean, and analyze unstructured raw server log files. The parsed data is structured and stored in a local SQLite database, allowing users to query metrics and generate markdown summary reports.

This project serves as a testing ground for Claude Code's agentic looping, self-debugging, and test-driven development (TDD) execution capabilities.

---

## 2. Technical Stack & Constraints
* **Language:** Python 3.12+ (Strict type hinting required on all functions)
* **Package & Environment Manager:** `uv` (Astral)
* **Code Quality:** `ruff` for formatting and linting
* **Testing Framework:** `pytest` (Aim for >90% test coverage)
* **Database:** SQLite (Built-in `sqlite3` or standard SQL expressions via an abstraction layer)
* **CLI Engine:** `click` or `argparse`

---

## 3. Core Architecture & Components
logforge/├── CLAUDE.md             # Project guidelines and build commands├── pyproject.toml        # Project metadata and dependencies managed by uv├── README.md             # High-level documentation├── src/│   └── logforge/│       ├── init.py│       ├── cli.py        # CLI argument parsing and commands│       ├── parser.py     # Log regex parsing and data validation│       ├── database.py   # SQLite schema and CRUD operations│       └── reporter.py   # Markdown summary generation└── tests/                # Parallel structure matching src/ for pytest



# Software Requirements Specification (SRS)## Project Name: LogForge## Target: Core Specification for Claude Code Autonomous Implementation---## 1. Project Overview & ObjectiveLogForge is a local, high-performance command-line interface (CLI) data pipeline designed to parse, clean, and analyze unstructured raw server log files. The parsed data is structured and stored in a local SQLite database, allowing users to query metrics and generate markdown summary reports.

This project serves as a testing ground for Claude Code's agentic looping, self-debugging, and test-driven development (TDD) execution capabilities.
---## 2. Technical Stack & Constraints* **Language:** Python 3.12+ (Strict type hinting required on all functions)
* **Package & Environment Manager:** `uv` (Astral)
* **Code Quality:** `ruff` for formatting and linting
* **Testing Framework:** `pytest` (Aim for >90% test coverage)
* **Database:** SQLite (Built-in `sqlite3` or standard SQL expressions via an abstraction layer)
* **CLI Engine:** `click` or `argparse`
---## 3. Core Architecture & Components

logforge/
├── CLAUDE.md # Project guidelines and build commands
├── pyproject.toml # Project metadata and dependencies managed by uv
├── README.md # High-level documentation
├── src/
│ └── logforge/
│ ├── init.py
│ ├── cli.py # CLI argument parsing and commands
│ ├── parser.py # Log regex parsing and data validation
│ ├── database.py # SQLite schema and CRUD operations
│ └── reporter.py # Markdown summary generation
└── tests/ # Parallel structure matching src/ for pytest


### 3.1. Data Ingestion & Parser (`parser.py`)
* **Input:** Standard Combined Log Format or common Nginx/Apache logs.
  * *Example line:* `127.0.0.1 - - [25/Aug/2026:14:32:10 +0000] "GET /api/v1/resource HTTP/1.1" 200 452`
* **Extraction Fields:**
  * IP Address (IPv4 or IPv6 validating string)
  * Timestamp (Parsed into a proper ISO 8601 datetime object)
  * HTTP Method (`GET`, `POST`, `PUT`, `DELETE`, etc.)
  * Requested Path (e.g., `/api/v1/resource`)
  * Status Code (Integer, e.g., `200`, `404`, `500`)
  * Response Size (Integer, bytes)
* **Resilience:** Handle malformed or corrupted log rows gracefully by logging warnings to `stderr` and skipping the line instead of crashing the pipeline.

### 3.2. Storage Layer (`database.py`)
* **Database:** Local SQLite database file named `logforge.db` (initialized automatically if missing).
* **Schema:** A single optimized table `logs` with fields mapped to the extracted parser fields, plus an autoincrementing `id` primary key.
* **Operations:** 
  * Bulk insertion capability to ensure efficient database writing for logs containing thousands of rows.
  * Prevention of duplicate records if the exact same log file is processed twice.

### 3.3. Reporting Engine (`reporter.py`)
* **Functionality:** Query the SQLite database to generate human-readable analytical metrics.
* **Metrics Required:**
  * Total request count.
  * Total data transferred (in MB).
  * Breakdown of HTTP Status Codes (e.g., Number of 200s, 404s, 500s).
  * Top 5 most requested URL paths.
  * Top 5 most active IP addresses.
* **Output:** Save analytical outputs into a nicely formatted Markdown report file (`report.md`).

### 3.4. Command Line Interface (`cli.py`)
The pipeline must expose a clear terminal interface using the following command structures:

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




