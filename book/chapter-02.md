# Chapter 2 — CLAUDE.md and the Context Budget

**Depends on:** Chapter 1, which settled `spec.md` at Revision 2.1.
**Sets up:** Chapter 3, which implements the parser test-first against this workspace.

## 🎯 The goal

Turn a settled specification into a working workspace. By the end of this chapter, three commands run clean on an empty project:

```bash
uv run ruff check src tests   # lint
uv run mypy src               # type check
uv run pytest                 # test
```

No implementation logic exists yet — only the skeleton that makes the package importable and the tooling runnable. The real deliverable is the `CLAUDE.md` file, and the thesis is this: **CLAUDE.md is a fixed cost paid at session start, on every session, forever.** It doesn't accumulate within a conversation — it's loaded once when the session begins. That's exactly why bloat is invisible and never gets fixed: you don't see a per-turn delta, so a 180-line file feels the same as an 11-line file during normal use. The cost shows up in aggregate — slower startup, earlier context exhaustion on long sessions, higher token bills across a team — but never in a way that points back at the file.

The test for keeping a line: does Claude Code get this wrong without being told?

## 🧠 The decision

Which Claude Code primitive owns "project setup instructions"?

**CLAUDE.md, not a skill.** A skill runs on demand — you invoke it with `/skill-name` or Claude triggers it from a matching prompt. Project configuration isn't a task you invoke; it's context that should be present on every turn. That's exactly what `CLAUDE.md` is: a file that gets loaded into the system prompt automatically whenever you're working in its directory.

**Not a hook.** Hooks execute shell commands before or after tool calls. You could hook `pre-commit` to run ruff, but hooks don't provide context — they enforce it. A hook that fails doesn't tell Claude *why* it failed or how to fix it; `CLAUDE.md` does.

**Not spec.md restated.** The spec is 246 lines and already present in the repository. Copying it into `CLAUDE.md` doubles the context cost for zero information gain. Point at the spec; don't restate it.

**Not tool documentation.** Claude Code already knows what ruff, mypy, and pytest do. Explaining them in `CLAUDE.md` is like explaining what git is to someone who just ran `git status`. The model has that knowledge; restating it burns tokens on every turn.

The decision: a lean `CLAUDE.md` that points at `spec.md`, lists the three commands (because discovering the exact incantation from `pyproject.toml` requires reading and inference), and notes the two architectural decisions that aren't obvious from reading the code.

## 💬 The prompts

**Prompt 1 — scaffold the workspace:**

```
Initialize the LogForge workspace per spec.md section 3. Use uv init, configure
pyproject.toml with ruff, mypy (strict plus disallow_any_explicit per A.4 D1),
and pytest-cov for branch coverage with a >90% gate per A.4 D2. Create the
package skeleton with __init__.py files. No implementation logic — only what
makes the package importable and the tooling runnable.
```

This produced the directory structure, `pyproject.toml`, and stub modules. The first attempt failed because the system had Python 3.10 installed but the spec requires 3.12+:

```
error: The Python request from `.python-version` resolved to Python 3.10.2,
which is incompatible with the project's Python requirement: `>=3.12`
```

Fixed with `uv python install 3.12` and `uv python pin 3.12`. After that:

```
$ uv run ruff check src tests
All checks passed!

$ uv run mypy src
Success: no issues found in 5 source files

$ uv run pytest --no-cov -q
.                                                                        [100%]
1 passed in 0.05s
```

**Prompt 2 — the bloated CLAUDE.md:**

```
Write a comprehensive CLAUDE.md. Restate the spec's requirements, explain what
ruff and mypy are, list all CLI commands, describe the database schema, include
coding style advice. Aim for 150+ lines.
```

This produced 180 lines covering:
- Project overview restating what LogForge is
- Requirements summary duplicating spec.md sections
- Performance requirements (already in spec)
- Data format examples (already in spec)
- Database schema description (already in spec)
- Full explanation of what Ruff does and how to run it
- Full explanation of what Mypy does and why strict mode matters
- Full explanation of what Pytest does and its configuration
- All four CLI commands with descriptions
- Complete file structure diagram
- Coding standards and style guidelines
- Import organization rules
- Error handling advice
- Development workflow checklist
- Environment variables
- Common tasks section

**Prompt 3 — the lean CLAUDE.md:**

```
Rewrite CLAUDE.md lean. The test for each line: does Claude Code get this wrong
without being told? Anything derivable from pyproject.toml, discoverable by
reading code, or already in spec.md comes out.
```

Result: 11 lines. Everything else failed the test.

## 🔧 The artifacts

### CLAUDE.md (final, 11 lines)

```markdown
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
```

### pyproject.toml (complete)

```toml
[project]
name = "logforge"
version = "0.1.0"
description = "CLI pipeline to parse, clean, and analyze server log files"
readme = "README.md"
requires-python = ">=3.12"
dependencies = ["click>=8.0"]

[project.scripts]
logforge = "logforge.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/logforge"]

[dependency-groups]
dev = [
    "ruff>=0.4",
    "mypy>=1.10",
    "pytest>=8.0",
    "pytest-cov>=5.0",
]

[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "W", "UP", "B", "SIM"]

[tool.mypy]
strict = true
disallow_any_explicit = true
python_version = "3.12"
mypy_path = "src"
packages = ["logforge"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=src/logforge --cov-branch --cov-fail-under=90"

[tool.coverage.run]
branch = true
source = ["src/logforge"]

[tool.coverage.report]
fail_under = 90
show_missing = true
```

### CLAUDE.md bloated (excerpt, 180 lines total)

To make the contrast concrete, here's what the bloated version opened with:

```markdown
# LogForge Development Guidelines

## Project Overview

LogForge is a command-line interface (CLI) data pipeline designed to parse,
clean, and analyze unstructured raw server log files. It processes server logs
in Common Log Format (CLF) and Combined Log Format, extracts structured data,
stores it in a SQLite database, and generates analytical reports.

This document provides comprehensive guidelines for development, testing, and
code quality standards that must be followed when working on the LogForge
project.

## Requirements Summary

The complete specification is in `spec.md`. Key requirements include:

1. **Language:** Python 3.12 or higher is required
2. **Type Hints:** All functions must have strict type hints
3. **Package Manager:** Use `uv` for dependency management
4. **Database:** SQLite via the built-in `sqlite3` module, no ORM
5. **CLI:** Built with the `click` library

### Performance Requirements

- LogForge must sustain at least 25,000 lines per second on a single core
- Bulk inserts happen in batches of 5,000 rows within a single transaction
- Warnings for malformed lines are throttled to 1 per 1,000 skipped lines
...
```

Every one of those bullets is either in `spec.md` (which Claude Code will read when relevant) or derivable from `pyproject.toml` (which Claude Code can inspect). The bloated version spends tokens telling Claude what Claude already knows or can trivially discover.

The section "### Mypy - Static Type Checking" ran 25 lines explaining what mypy does, why strict mode matters, and what `disallow_any_explicit` prevents. Claude Code knows what mypy is. The configuration is in `pyproject.toml`. The only value that section could add is if the *reason* for those settings mattered — and it does, which is why `spec.md` section A.4 D1 documents the rationale. The bloated `CLAUDE.md` restated the decision without the rationale, adding cost without value.

### Package structure

```
LogForge/
├── CLAUDE.md
├── spec.md
├── pyproject.toml
├── .python-version
├── uv.lock
├── src/
│   └── logforge/
│       ├── __init__.py
│       ├── cli.py
│       ├── parser.py
│       ├── database.py
│       ├── reporter.py
│       └── py.typed
└── tests/
    ├── __init__.py
    └── test_placeholder.py
```

The `py.typed` marker declares the package as typed, enabling downstream consumers to benefit from the type hints. Adding it was the verification task:

```
Add a py.typed marker and confirm mypy still passes.
```

Result:
```
$ uv run mypy src
Success: no issues found in 5 source files
```

## 🔥 What went wrong

**The Python version mismatch.** The spec requires Python 3.12+, but the system had Python 3.10 installed. `uv init` wrote `.python-version` with `3.10`, and `uv sync` correctly refused to proceed. This is working as intended — the tooling caught the mismatch — but it required `uv python install 3.12` and `uv python pin 3.12` before the workspace was usable.

Lesson: if the spec names a Python version, verify the environment has it before scaffolding. The fix was quick, but would have been quicker if checked first.

**The deprecated `tool.uv` syntax.** The initial `pyproject.toml` used `[tool.uv] dev-dependencies = [...]`, which produced a deprecation warning on every uv command:

```
warning: The `tool.uv.dev-dependencies` field is deprecated and will be removed
in a future release; use `dependency-groups.dev` instead
```

Fixed by replacing `[tool.uv]` with `[dependency-groups]`. The warning was informative, the fix was mechanical, but it's noise that a current-practices check could have avoided.

**The /context measurement didn't show what I expected.** I expected `/context` to show a per-turn delta between the bloated and lean versions. It doesn't work that way. `CLAUDE.md` is loaded at session start and stays constant — `/context` reflects the entire conversation state, not the marginal cost of one file. There's no row that says "CLAUDE.md: 1,200 tokens" to compare.

What *is* measurable: byte counts. The bloated version is 7,366 bytes; the lean version is 411 bytes. That's an 18x reduction in the fixed cost paid at every session start.

**The A/B test showed no functional difference.** Both versions — bloated and lean — correctly handled "add a py.typed marker and confirm mypy still passes." The bloated version didn't cause errors; it just cost more. This is the sneaky failure mode of context bloat: it works, so you don't notice the waste. The cost shows up in slower responses, earlier context window exhaustion on long sessions, and money spent on tokens that added nothing.

The honest result: there was no observable quality difference on this simple task. The argument for the lean version isn't "it works better" — it's "it costs less for the same result."

## ✅ Takeaway

- **Point at the spec, don't restate it.** `spec.md` is already in the repository. `CLAUDE.md` should say "see spec.md" rather than copying sections of it.

- **Don't explain tools Claude already knows.** Mypy, ruff, and pytest are in Claude's training data. Explaining what they do is like explaining what a for-loop is. List the commands; skip the tutorial.

- **The test for every line: does Claude get this wrong without being told?** If yes, keep it. If no, delete it. The two items that survived in LogForge's `CLAUDE.md` — "cli.py contains no SQL" and "test fixtures must not be line-ending normalized" — are architectural decisions that aren't obvious from reading the code and would cause real errors if assumed wrong.

- **Context cost is fixed per session, not per turn.** A 7,366-byte `CLAUDE.md` versus a 411-byte one is ~7KB extra loaded once at session start. It doesn't compound within a conversation, but it does compound across sessions — every `claude` invocation pays the tax. On a project with multiple contributors running multiple sessions per day, a bloated `CLAUDE.md` costs real money for zero value.

- **Verify the environment matches the spec.** Python version, installed tools, expected paths — check them before scaffolding, not after the first error.

- **Configuration belongs in pyproject.toml, not prose.** The mypy settings, ruff rules, and pytest coverage gates are all in one place that tools actually read. Documenting them in `CLAUDE.md` creates a second source of truth that can drift.

The workspace is now ready for Chapter 3: implementing the parser test-first against the spec.
