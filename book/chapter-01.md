# Chapter 1 — Interrogate the Spec Before You Write a Line

**Depends on:** nothing. This is where the project starts.
**Sets up:** Chapter 2, which turns the settled spec into a workspace and a `CLAUDE.md`.

## 🎯 The goal

You have a spec and an empty repository. The obvious move is to open Claude Code, paste the spec, and say "build this." Resist it for one session.

This chapter produces no source code. Its deliverable is Revision 2.1 of `spec.md` — the same document with its corruption repaired and its ambiguities resolved on the page, before a single line of Python depends on them. Nothing in §3 gets implemented here. The whole document gets read.

The reason is arithmetic. An ambiguity resolved in the spec costs one edit. The same ambiguity resolved after the parser, the schema, and forty tests have quietly assumed one reading costs you all of them. Claude Code is fast enough to reach that second state in an afternoon, which makes the spec pass more valuable now than it has ever been, not less.

## 🧠 The decision

Which Claude Code primitive owns "read a spec critically"?

**Not a skill.** You interrogate a project's spec once. Skills earn their keep on the second repetition, and there isn't one.

**Not a hook.** Nothing exists yet to enforce.

**Not a forked subagent.** `context: fork` is right when you want a result and not the reasoning. Here the reasoning *is* the deliverable — you're going to argue with it — and a fork hands you a summary while the argument stays in a context you can't see.

**Plan mode, in the main thread.** Start Claude Code and press `Shift+Tab` until the footer reads plan mode. In plan mode Claude Code cannot edit files. That matters more than it sounds: the failure you're guarding against isn't Claude misreading the spec, it's Claude reading it correctly and *helpfully starting to scaffold*, at which point the ambiguities are baked into a directory tree and you're reviewing code instead of requirements. Asking nicely for restraint works most of the time. Structural containment works every time.

Run the prompts in order. Each is built to make the next harder to answer glibly.

## 💬 The prompts

**Prompt 1 — inventory.** No judgments, just an accounting:

```
Read spec.md. Do not write, edit, or create any file. Do not scaffold, do not
propose a project structure, do not tell me what you would build.

Produce only this: a numbered list of every requirement in the spec, stated as a
testable assertion. One line each. If a sentence in the spec cannot be turned
into something a test could pass or fail, write it as "UNTESTABLE: <the
sentence>" and move on.
```

On LogForge this returned 53 items and correctly flagged "high-performance" as untestable without being told what to look for. It also, as you'll see below, silently repaired a corruption while transcribing it.

**Prompt 2 — the three buckets.** The load-bearing prompt. Spec problems come in three kinds and each needs a different fix, so they have to be separated before anyone tries to fix them:

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

The result on LogForge: **3 corrupted, 1 contradictory, 14 silent.**

That split is the finding, not just the output. A silence needs one sentence and the question "and then what?" A contradiction needs two sections held in mind simultaneously plus the realization that they conflict — and the further apart they sit in the document, the less likely that is. Expect this bucket to be underpopulated and go looking yourself.

The corrupted bucket is where you take over with a terminal. Claude Code quoted the raw text as instructed, but reading the actual bytes changes the diagnosis:

```console
$ grep -n 'init.py' spec.md
25:logforge/├── CLAUDE.md  # Project guidelines and build commands├── pyproject.toml ...
46:│ ├── init.py

$ sed -n '25p' spec.md | cat -A | head -c 120
logforge/M-bM-^TM-^\M-bM-^TM-^@M-bM-^TM-^@ CLAUDE.md             # Project guid
```

That `cat -A` output is one physical line running the entire width of a directory tree. And `init.py` is not a typo. In markdown, `__init__` renders as bold `init`. The only way the raw file contains a literal `init.py` is if someone copied *rendered* output and pasted it back as source — which explains every other symptom at once: consumed emphasis markers, flattened blocks, headings welded to their paragraphs, a tree collapsed to one line, and a truncated partial paste above the real document.

Claude Code found all three defects and filed them as three independent items with independent confidences — 99%, 99%, and 90%, with `init.py` hedged as "either a rendering loss of double underscores or a typo." Those two aren't interchangeable. A typo is local. A rendering loss is systemic, and it's the same event that caused the other two.

Knowing the cause tells you what else to check. Anything unfenced containing `_`, `*`, or `<` is suspect. The fenced `bash` block in §3.4 came through intact, `<path_to_log_file>` and all — which means §3.4 was trustworthy as written. Don't repair corruption symptom by symptom. Find the event, then ask what else it touched.

**Prompt 3 — the adversarial pass.** Silence hides best from a cooperative reader, so stop being one:

```
You are now a contractor paid a fixed fee to make LogForge pass any test suite
derived from spec.md, with the least work possible. You are not malicious, just
lazy and literal.

Describe the cheapest implementation that satisfies the spec as written.
Where the spec lets you do something obviously stupid and still comply, say so
and quote the clause that permits it.
```

This produced eight exploits with the enabling clause quoted for each, including "IPv4 or IPv6 — I chose IPv4, so IPv6 lines are malformed and skipped, compliant," and a `logs` table with zero indexes on the grounds that "optimized" names no target. Run this one even when the earlier passes felt thorough.

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

The rationale requirement is the trick: it forces a reason to exist, and a bad reason is visible in a way a bare decision never is.

Be aware this ran twice on LogForge. The first pass produced Revision 2; the audit above then found two defects *in Revision 2*, and a second pass produced Revision 2.1. Budget for that. One amendment round is optimistic.

## 🔧 The artifacts

Revision 2.1 of `spec.md` is the main one, and its structure matters more than its prose — an amendment appendix, one table per bucket, plus a section for what the audit found afterward:

```markdown
## Appendix A. Amendment log

### A.1 Corrupted — the file itself was damaged
| ID | Defect | Repair |

### A.2 Contradictory — two parts could not both hold
| ID | Conflict | Decision and what was dropped |

### A.3 Silent — the spec did not say, so an implementer would have invented
| ID | Gap | Decision |

### A.4 Audit — defects and gaps closed in Revision 2.1
| ID | Finding | Decision |
```

Keep the amendments in the spec rather than a separate ADR file. In Chapter 2 you point `CLAUDE.md` at `spec.md` as the source of truth, and a source of truth that requires reading a second document isn't one.

The second artifact is `.gitattributes`, and it has to land before any test fixture does:

```
* text=auto eol=lf
tests/fixtures/** -text
```

The second line is the one that counts. Log fixtures are byte-exact test inputs. If git normalizes line endings on checkout, a parser test passes on your machine and fails in CI for an hour's worth of reasons.

## 🔥 What went wrong

Three failures, in ascending order of how much they should worry you.

**The inventory silently repaired the corruption.** Prompt 1, item 18:

```
18. src/logforge/__init__.py exists
```

The file says `init.py`. Twice. Claude Code read the raw bytes and wrote `__init__.py` into the inventory anyway — it knew Python packages have `__init__.py`, saw something one character-class away, and completed the pattern. A reviewer skims item 18 and nods, because item 18 is *correct about Python*. The corruption vanished in the direction of looking right.

Prompt 2 recovered it as C3, quoting both line numbers. That recovery is the argument for the bucketing prompt: demanding the raw text be quoted forces a re-read against the file instead of against memory.

**The amendment named tools instead of configuring them.** Revision 2 resolved "strict type hinting required, with no type checker in the stack" by adding `mypy --strict`, and ">90% coverage, with no coverage tool" by adding `pytest-cov` with a line-coverage gate. Both felt like enforcement. Prompt 3 walked through both:

> Type hints: `Any` everywhere. "Strict type hinting required on all functions" — every function is annotated. Strictly. With `Any`.

`mypy --strict` bans *implicit* `Any`, not explicit ones. `def parse_line(line: Any) -> Any:` passes. And line coverage is precisely the metric a test file of `assert True` games. Revision 2.1 adds `disallow_any_explicit = true` and switches to branch coverage. Naming a tool is not configuring it — a distinction Chapter 4 is built on, fumbled here in Chapter 1's own artifact.

**Nothing found the format contradiction.** §3.1 says the input is Combined Log Format. The example line printed directly beneath it is Common Log Format — Combined appends a quoted referrer and user-agent, and the field list underneath enumerates CLF's fields with neither. The spec names one format, exemplifies a second, and specifies the second.

Prompt 3 got within an inch:

> I implement exactly one regex for Combined Log Format. Anything else? Logged to stderr and skipped.

That contractor's parser would **skip the example line printed in the spec**, and it didn't notice — in the one framing built to hunt for exactly this. Three passes, roughly ninety findings, and the contradiction that determines the parser's core regex survived all of them. It was caught by a human who knew what a CLF line looks like.

That's the honest ceiling on this workflow. It is very good at silences, good at corruption once you make it quote raw text, weak at contradictions, and blind to the ones that need domain knowledge the spec never states.

## ✅ Takeaway

- **Contain structurally, not verbally.** Plan mode makes "don't start coding" a property of the session rather than a request Claude has to remember.
- **Sort problems into silent, contradictory, and corrupted before fixing any of them** — and expect the contradictory bucket to be short. That's where to spend your own attention.
- **Make "no problems found" an allowed answer.** A model asked to fill three buckets will fill three buckets.
- **Watch for the model repairing corruption while transcribing it.** Anything it "knows" the right answer to gets quietly corrected in flight. Demanding raw quotes is what catches it.
- **Naming a tool is not configuring it.** `mypy --strict` and `pytest-cov` both pass a spec that specifies nothing. Write the configuration into the amendment.
- **Read the artifact, not the report about it.** `git log` says a commit exists, not what's in it. `git show <sha>:<file>` is the artifact. A raw-host fetch is a report too — during this chapter it served stale content three times, each internally consistent and confidently wrong.