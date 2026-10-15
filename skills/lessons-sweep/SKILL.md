---
name: lessons-sweep
description: Read every MAKING-OF.md under a folder, find the lessons that keep being learned, and stage rule proposals for the user to adopt. Use when the user asks to run the lessons sweep, review the making-ofs, find recurring mistakes, or improve the workflow rules from past sessions; also as a scheduled task every two weeks. Collects with lessons_digest.py, reviews against the existing rule files, writes a staged report, and changes no rule until the user picks what to adopt.
---

# Lessons sweep

A making-of records what went wrong in one project. Read side by side, a dozen of them
show the same lesson learned three times, which means a rule is missing. This skill
finds those and proposes the rule. It never applies one: the user adopts each proposal
by name.

Three stages: **collect** (a deterministic digest), **review** (cluster, gate, propose),
**adopt** (only on the user's word, verified afterwards).

## Inputs

Ask for any you don't know. Don't guess them from folder names.

| Input | What | Example |
|---|---|---|
| Root | Folder that holds the projects and their making-ofs | `~/projects` |
| Learnings folder | Where digests and reports go. **Never a public repo**: digests quote private making-ofs | `~/projects/learnings` |
| Rule files | Files every session reads, where adopted rules land | `~/projects/CLAUDE.md`, `~/projects/TOOLS.md` |
| Digest script | `lessons_digest.py` from the making-of kit | `<kit checkout>/lessons_digest.py` |

Use absolute paths in every command. Quote glob patterns (`--include='*.md'`); unquoted,
zsh fails the whole line with `no matches found`.

## 1. Collect

**Error signatures (optional).** The making-ofs record the clever wrong theories. The
cheap failures that recur most (an unquoted glob, a sandbox refusal) are rarely written
down, so they're counted from transcripts instead. If this agent has a session-transcript
search tool:

- Copy the newest `signatures-<date>.txt` in the learnings folder to
  `signatures-<today>.txt`. If there's none, start one: comment lines begin with `#`,
  data lines are `count | query | last seen | note`.
- Re-run each query. Record the number of sessions it hits and the newest hit date. Write
  a count at the tool's result cap as `≥cap`, because it's a floor.
- Also record how many hits came **after** the previous signatures file's date. That
  number shows whether a rule adopted last time is working.
- Add a query for any repeated error string you notice while reviewing; never remove one.

With no search tool, skip this and say so in the report. Don't read raw transcripts into
the report, and never copy a secret, token or private URL into any file.

**Digest.**

```bash
python3 -I <digest script> <root> --out-dir <learnings folder> --signatures <learnings folder>/signatures-<today>.txt --rules <rule file> --rules <rule file>
```

Drop `--signatures` if step 1 was skipped. The digest groups every `The lesson`,
`WRONG THEORY` and `Correction to` passage by project, cites each by its `##` heading, and
lists what is new since the previous digest. It writes nothing else.

## 2. Review

Read the digest's "New since the last digest" section first, then the by-project
sections, then the previous report in the learnings folder (the newest `<date>.md` that
isn't `lessons-*` or `signatures-*`) for what was already adopted, held back or rejected.

Cluster passages that teach the same thing in different words. A cluster becomes a
proposal only if it passes **both** parts of the gate:

1. **Independence.** It was learned separately in **3 or more projects, or 3 or more
   separate sessions**. Several acts in one project, about one incident, count once.
2. **Not already a rule.** Read the rule files themselves. The digest's Rules column is a
   literal text match and misses a rule written in other words.

At most **4 proposals** per sweep. Fewer is fine; none is a valid result.

Before citing anything, check the act or session number against the digest. Never map
grep line numbers to headings by eye: that is how this skill's predecessor mis-cited six
acts.

Also check the rules adopted at earlier sweeps. For each one with a signature query,
compare its "since last sweep" count with the previous count. If it hasn't fallen, the
written rule isn't enough: propose a check or hook that enforces it instead.

## 3. Stage the report

Write `<learnings folder>/<today>.md`:

- **Sources and limits.** Files read, signature counts, what was skipped and why.
- **Evidence.** The clusters, each with where it was learned (project + heading).
- **Proposals.** For each: the target file, the section it goes in, and the **exact
  text**, in a fenced block, so adopting it is a copy and paste.
- **Held back or rejected.** Every cluster that failed the gate, and which part failed.
- **Earlier rules.** Working or not, from the counts.
- Mark anything not actually checked as assumed.

**Change nothing else.** No rule file, settings file, hook, or commit. The report is the
whole output.

Finish by telling the user where the digest and report are, listing the proposals in one
line each, and asking which to adopt.

## 4. Adopt (only when the user names proposals)

- Apply each named proposal **exactly as staged**, in the target file and section the
  report gives. If it no longer fits (the file changed since), say so and re-stage rather
  than improvise.
- Verify: confirm each staged block appears verbatim in its target file, with a short
  script, not by eye.
- Append an `## Adopted, <date>` section to the report: who approved, what went where,
  the verification result. Leave the rest of the report as written.

## 5. Record

Add an entry to the making-of that covers the folder holding the learnings, following
that file's shape. Give the counts, what passed, what was held, and any wrong turn. A
sweep that found nothing new gets a short entry saying so.

## Cadence

Every two weeks is enough. Lessons accumulate slowly, and a rule needs time to show
whether its failure count falls. If the scheduler only does weekly, run weekly and stop
straight away unless the newest `lessons-*.md` is at least 13 days old.
