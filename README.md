# making-of

A `MAKING-OF.md` is the running story of a project: what got decided, what got tested, and
what turned out to be wrong. This repo is the kit for making Claude Code keep one, every
session, without being reminded.

Three pieces to write them, from cheapest to strongest:

1. **A CLAUDE.md block.** The rule. It loads into every session.
2. **A seed file.** An empty convention gets ignored. A file that already exists, with a
   shape, gets appended to.
3. **A Stop hook.** CLAUDE.md is a strong nudge, not a guarantee: a long session can end
   without the append. The hook makes it mechanical.

And two to use them, so the same lesson isn't learned a fourth time:

4. **The lessons digest.** A script that collects every lesson, wrong theory and
   correction from every making-of into one dated file.
5. **The lessons sweep.** A skill that reviews the digest, finds the lessons learned in
   three or more places, and stages rule proposals for you to adopt.

Use all three of the first group. Running this since August 2026 across a dozen projects showed each one
alone leaks: the rule sat in three projects' CLAUDE.md files and the other fifteen never
saw it, and the projects that had it still skipped entries when a session ended on a
quick fix.

---

## 1. The CLAUDE.md block

Paste into the project's `CLAUDE.md`. **If you keep many projects under one folder, paste
it once into that folder's `CLAUDE.md` instead.** Claude Code reads every `CLAUDE.md`
from the working directory up to the root, so a session started in any sub-folder sees
it, and you never have to remember to add it to a new project.

```markdown
## MAKING-OF.md

Every project keeps a `MAKING-OF.md` next to its README. It is the running story of the
project: what got decided, what got tested, and what turned out to be wrong.

- **Every working session that changes files or makes a decision adds an entry**, before
  wrapping up, without being asked. A read-only question needs none. A trivial fix (typo,
  formatting, a path) needs none; say so in one line instead.
- **Append, never rewrite.** New dated section at the bottom. Never edit or tidy earlier
  entries. If a past conclusion was wrong, add a "Correction to session N" subsection and
  leave the original in place. Records keep the paths and names that were true when they
  were written, even after a move.
- **The point of the file is the wrong turns.** Bad cost estimates, misread API
  responses, theories that got disproved, instructions that didn't work. An entry that
  only records the clean final answer is a failed entry. Keep superseded theories under a
  `WRONG THEORY:` heading rather than deleting them. Do not invent wrong turns either: a
  session that went straight gets a short entry.
- **Receipts.** The actual numbers, commands, error text, and file paths.
- **Say what was verified vs. assumed.** Mark anything not actually run as assumed.
- **No project file yet?** Create it from the seed header before the first entry.
- **Never put secrets in it.** Making-ofs are source material for public write-ups.
```

## 2. The seed file

```markdown
# Making of <project>

The running story of this project: what got decided, what got tested, and what turned out
to be wrong. Appended to after every working session. Newest entry at the bottom.

The point of this file is the wrong turns. README.md says where things landed; this is
the record of how, so a decision doesn't get re-litigated in six months because nobody
remembers why it went the way it did.

---

## Session 1 — <date>: <what happened>
```

### Two shapes that work

- **Sessions** (`## Session N — <date>: <title>`). The default. One entry per working
  session. Good for apps and infrastructure.
- **Acts** (`## Act N — <title> (<date>)`, each ending in a `> **The lesson:**` line).
  For projects whose making-of is source material for a video or article. An act is a
  story with a turn in it, so one session can produce one act, several, or add to the
  last one. The bar for an act: *would someone competent have believed the wrong thing
  here?*

Pick one per project and keep it. A project that already has a shape keeps its shape.

## 3. The Stop hook

[`hooks/making-of-stop.py`](hooks/making-of-stop.py). At the end of each turn it reads the
session transcript. If files were changed after the session's last `MAKING-OF.md` write,
it blocks the stop once and tells Claude to append an entry, or to say in one line why
none is needed. It blocks again only if more changes follow, and it never fails a
session: any error exits 0.

**Install it with one command** (keeps your existing settings, backs the file up first,
and does nothing if the hook is already there):

```bash
python3 hooks/install-hook.py --root ~/path/to/projects
```

It goes in `~/.claude/settings.json`, at user level, so it covers sessions started in any
sub-folder; project settings files are not read from parent folders. By hand, the entry is:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/path/to/making-of/hooks/making-of-stop.py --root ~/path/to/projects",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

Merge it into any `hooks` you already have rather than replacing them. `--root` limits it
to changes under one folder; repeat it for several, or leave it off to apply everywhere.

What counts as a change: the Edit, Write, MultiEdit and NotebookEdit tools, plus Bash
commands that run `git commit`, `sed -i`, `tee`, or redirect into a file. Paths under
`.claude/`, `.git/` and temp folders are ignored. Writing any file named `MAKING-OF.md`
(any case) counts as the entry.

**Why not just echo a reminder?** The first version of this README suggested a Stop hook
that echoes a reminder. That does nothing: a Stop hook's ordinary output is never shown to
Claude. Only `{"decision": "block", "reason": "..."}` reaches the model, which is why this
hook blocks.

Test it without a session:

```bash
echo '{"session_id":"t","transcript_path":"/path/to/a/transcript.jsonl","stop_hook_active":false}' | python3 hooks/making-of-stop.py --root ~/path/to/projects
```

## 4. Reading them back: the lessons digest

A dozen making-ofs hold the same lesson learned three times, and nobody reads them side by
side. [`lessons_digest.py`](lessons_digest.py) does: it walks a folder for every
`MAKING-OF.md` / `making-of.md` (skipping `node_modules`, `.git`, `_archive` and
`.claude/worktrees`), pulls out each passage marked `The lesson`, `WRONG THEORY` or
`Correction to`, and writes a dated digest grouped by project.

```bash
python3 -I lessons_digest.py ~/path/to/projects --out-dir ~/path/to/learnings
```

- **Cited by heading, not line number.** Each passage is tied to the `##` heading it sits
  under (Act N, Session N, or the heading's own text), found by parsing the file.
  Mapping grep line numbers to acts by eye is how citations go wrong.
- **What's new since last time.** Each digest ends with a manifest of passage ids; the
  next run lists the passages that weren't in it, dated or not.
- **Optional evidence table.** `--signatures FILE` takes error-signature counts you paste
  from a transcript search (`count | query | last seen | note`, one per line) and shows,
  for each, the making-of passages that mention it. `--rules CLAUDE.md` (repeatable) adds
  whether a rule file already covers it.
- Standard library only, no network, no model. Same files in, same digest out. Deciding
  which lessons become rules is section 5.

## 5. Closing the loop: the lessons sweep

[`skills/lessons-sweep/SKILL.md`](skills/lessons-sweep/SKILL.md) turns a digest into rule
changes, in three stages:

1. **Collect.** Runs the digest. Optionally re-counts error strings from a session
   transcript search, because the failures that recur most (an unquoted glob, a sandbox
   refusal) are the ones nobody writes up.
2. **Review.** Clusters lessons that say the same thing, and proposes a rule only for one
   learned independently in **three or more projects or sessions** that no rule file
   already covers. At most four per sweep. Each proposal comes with its exact text and
   target file, written to a dated report in your learnings folder.
3. **Adopt.** Nothing changes until you name the proposals you want. They're applied
   verbatim, checked by script, and recorded in the report. Rules adopted at earlier
   sweeps are checked too: if a rule's error count hasn't fallen, the next sweep proposes
   a hook instead of more words.

Install it as a user-level skill:

```bash
cp -R skills/lessons-sweep ~/.claude/skills/lessons-sweep
```

Then ask Claude to "run the lessons sweep", giving the projects folder, a learnings folder
(**not** inside a public repo: digests quote your making-ofs), your rule files and this
checkout's path. Every two weeks is a good cadence; as a scheduled task that only fires
weekly, have it stop unless the last digest is at least 13 days old.

## Lessons from running it

- **One rule in the parent folder beats a copy in each project.** Copies drift: the three
  per-project copies here had already diverged, and new projects never got one.
- **Code you don't own gets its making-of in the wrapper folder,** not in someone else's
  repository. Keep a wrapper folder around company or third-party checkouts and put the
  file there.
- **Check the branch before trusting a making-of.** A checkout left on an old branch
  shows old decisions. The file is only as current as the commit you are reading.
- **Work done on another machine still gets recorded on the one that decides.** If a
  build or render runs elsewhere from a brief, the session that reviews the result writes
  the entry.

## The one-line version

For a kickoff prompt, if someone won't set up CLAUDE.md: "Create a MAKING-OF.md and append
a dated session entry to it at the end of every session. Record the wrong turns and
disproved theories with receipts, not just the final answer, and never rewrite earlier
entries."
