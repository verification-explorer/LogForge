# Chapter 1 — Interrogate the Spec Before You Write a Line

**Depends on:** nothing. This is where the project starts.
**Sets up:** Chapter 2, which turns the settled spec into a workspace and a `CLAUDE.md`.

## 🎯 The goal

You have a spec and an empty repository. The obvious move is to open Claude Code, paste the spec, and say "build this." Resist it for one session.

This chapter produces no source code. Its deliverable is Revision 2 of `spec.md` — the same document with its corruption repaired and its ambiguities resolved on the page, before a single line of Python depends on them. Nothing in §3 of the spec gets implemented here. The whole document gets read.

The reason is arithmetic. An ambiguity resolved in the spec costs one edit. The same ambiguity resolved after the parser, the schema, and forty tests have quietly assumed one reading costs you all of them. Claude Code is fast enough that you can reach that second state in an afternoon, which makes the spec pass more valuable now than it has ever been, not less.

## 🧠 The decision

Which Claude Code primitive owns "read a spec critically"?

**Not a skill.** You interrogate a project's spec once. Skills earn their keep on the second repetition, and there isn't one.

**Not a hook.** Nothing exists yet to enforce.

**Not a forked subagent.** `context: fork` is right when you want a result and not the reasoning. Here the reasoning *is* the deliverable — you're going to argue with it — and a fork hands you a summary while the argument stays in a context you can't see.

**Plan mode, in the main thread.** Start Claude Code and press `Shift+Tab` until the footer reads plan mode. In plan mode Claude Code cannot edit files. That matters more than it sounds: the failure you're guarding against isn't Claude misreading the spec, it's Claude reading it correctly and *helpfully starting to scaffold*, at which point the spec's ambiguities are baked into a directory tree and you're reviewing code instead of requirements. Asking nicely for restraint works most of the time. Structural containment works every time.

The prompts below are written for plan mode. Run them in order; each is built to make the next harder to answer glibly.

## 💬 The prompts

**Prompt 1 — inventory.** No judgments yet, just an accounting:

```
Read spec.md. Do not write, edit, or create any file. Do not scaffold, do not
propose a project structure, do not tell me what you would build.

Produce only this: a numbered list of every requirement in the spec, stated as a
testable assertion. One line each. If a sentence in the spec cannot be turned
into something a test could pass or fail, write it as "UNTESTABLE: <the
sentence>" and move on.
```

The UNTESTABLE clause does the work. "High-performance" and "nicely formatted" surface immediately as things nobody can verify, and they surface as a category rather than as complaints.

**Prompt 2 — the three buckets.** This is the load-bearing prompt. Spec problems come in three kinds and each needs a different fix, so they have to be separated before anyone tries to fix them:

```
Using the requirement list you just produced, classify every problem you find
into exactly one of three buckets. Do not fix anything yet.

SILENT   — the spec doesn't say, and an implementer would have to invent an answer.
           Record what's missing and what the plausible answers are.
CONTRADICTORY — two parts of the spec cannot both be satisfied. Quote both parts
           verbatim with their section numbers.
CORRUPTED — the file itself is damaged: mangled formatting, lost characters,
           a code block that isn't fenced. Quote the raw text as it appears.

For CONTRADICTORY items, do not pick a winner yet. For CORRUPTED items, state
what you think the original text was and how confident you are.

If a bucket is empty, say so explicitly rather than inventing an entry to fill it.
```

That last line is not politeness. Ask a model for three categories and you will receive three categories, populated. Making the empty bucket a legitimate answer is what keeps the other two honest.

**Prompt 3 — the adversarial pass.** Silence hides best from a cooperative reader, so stop being one:

```
You are now a contractor paid a fixed fee to make LogForge pass any test suite
derived from spec.md, with the least work possible. You are not malicious, just
lazy and literal.

Describe the cheapest implementation that satisfies the spec as written.
Where the spec lets you do something obviously stupid and still comply, say so
and quote the clause that permits it.
```

Everything this turns up is a hole. On LogForge it produced the best find in the pass: the spec says Response Size is an Integer, and real Common Log Format writes a literal `-` for an empty response. Follow the spec literally and every 304 gets classified as a malformed line and skipped — silently, while the "total data transferred" metric comes out wrong and no test written from the spec catches it.

**Prompt 4 — resolve in the spec, never in the code:**

```
For every SILENT and CONTRADICTORY item, write an amendment to spec.md.

Rules:
- The amendment goes in the spec. Do not touch, plan, or reference source code.
- Each amendment states the decision AND one sentence of rationale. A decision
  with no rationale gets re-litigated in three weeks.
- Contradictions: name which side you dropped and why.
- Silences: name the alternative you rejected.
```

The rationale requirement is the trick. It forces a reason to exist, and a bad reason is visible in a way a bare decision never is.

## 🔧 The artifacts

Two things get committed in this chapter. The first is Revision 2 of `spec.md`, whose structure matters more than its prose: an amendment appendix, one table per bucket.

```markdown
## Appendix A. Amendment log

### A.1 Corrupted — the file itself was damaged
| ID | Defect | Repair |

### A.2 Contradictory — two parts could not both hold
| ID | Conflict | Decision and what was dropped |

### A.3 Silent — the spec did not say, so an implementer would have invented
| ID | Gap | Decision |
```

Keep the amendments in the spec rather than in a separate ADR file. In Chapter 2 you will point `CLAUDE.md` at `spec.md` as the source of truth, and a source of truth that requires reading a second document isn't one.

The second artifact is `.gitattributes`, and it has to land before any test fixture does:

```
* text=auto eol=lf
tests/fixtures/** -text
```

The second line is the one that counts. Log fixtures are byte-exact test inputs. If git normalizes line endings on checkout, a parser test passes on your machine and fails in CI for reasons that will take you an hour to see.

## 🔥 What went wrong

Twice, and the same mistake both times.

**The first amendment diff was void.** It was written against the spec as *rendered* — the version you see on GitHub, the version a fetch returns as readable text. Applied against the raw file, every hunk failed, because in the raw file the section heading and the first bullet are welded together on one physical line:

```
---## 2. Technical Stack & Constraints* **Language:** Python 3.12+ ...
```

Reading the actual bytes changed the diagnosis entirely:

```console
$ grep -n 'init.py' spec.md
25:logforge/├── CLAUDE.md  # Project guidelines and build commands├── pyproject.toml ...
46:│ ├── init.py

$ sed -n '25p' spec.md | cat -A | head -c 120
logforge/M-bM-^TM-^\M-bM-^TM-^@M-bM-^TM-^@ CLAUDE.md             # Project guid
```

That `cat -A` output is one physical line running the entire width of the directory tree. And `init.py` is not a typo. In markdown, `__init__` renders as bold `init`. The only way the raw file contains a literal `init.py` is if someone copied *rendered* output and pasted it back as source — which explains every other symptom at once: consumed emphasis markers, flattened blocks, headings glued to their paragraphs, a tree collapsed to one line, and a truncated partial paste sitting above the real document.

That single insight is worth more than the individual fixes, because it tells you what *else* to check. Anything unfenced containing `_`, `*`, or `<` is suspect; the fenced `bash` block in §3.4 came through intact, `<path_to_log_file>` and all, which means §3.4 was trustworthy as written. Don't repair corruption symptom by symptom. Find the event, then ask what else that event touched.

**The second time was worse.** After the repair was committed and pushed, `git log --oneline` showed both commits on `origin/main`. The obvious next step was to move on to the outline. Instead, a re-fetch of `spec.md` came back as Revision 1 — duplicate header, one-line tree, `init.py` intact.

It turned out to be a `raw.githubusercontent.com` cache, and it cleared in minutes. But the checking command was the point:

```console
$ git show 23c9a82:spec.md | wc -l
214
$ git show 23c9a82:spec.md | grep -c 'Appendix A'
2
```

A clean `git log` tells you a commit exists. It tells you nothing about what's inside it. The rule that caught this is the same one that found `init.py`: read the artifact, not the report about the artifact.

## ✅ Takeaway

- **Contain structurally, not verbally.** Plan mode makes "don't start coding" a property of the session instead of a request Claude has to remember.
- **Sort spec problems into silent, contradictory, and corrupted before fixing any of them.** They need different fixes, and lumping them together produces a list of complaints instead of a list of decisions.
- **Make "no problems found" an allowed answer.** A model asked to fill three buckets will fill three buckets.
- **Resolve ambiguity in the spec, with a rationale.** A decision without a reason gets re-argued the first time it's inconvenient.
- **Read the artifact, not the report about it.** `git log` is a report. `git show <sha>:<file>` is the artifact. The same distinction applies to rendered markdown versus raw bytes, and to a passing test run versus the assertion you think it made.