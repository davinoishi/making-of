# Making of making-of

The running story of this kit: what got decided, what got tested, and what turned out to
be wrong. Appended to after every working session. Newest entry at the bottom.

The point of this file is the wrong turns. README.md says where things landed; this is
the record of how, so a decision doesn't get re-litigated in six months because nobody
remembers why it went the way it did.

---

## Session 1 — 17 Aug 2026: the README

Reconstructed from git log on 8 Oct; no notes were kept at the time. Four commits in two
minutes (09:51–09:52): the initial commit, the CLAUDE.md block and seed header, and a
last line promising a Stop hook. The hook section ended in a placeholder
(`claude config  # not available here — edit .claude/settings.json directly`) and a line
of chat text offering to "wire that up". Both were pasted from a conversation and never
finished.

## Session 2 — 8 Oct 2026: from a convention to a standard process

Davin asked for the convention to be part of every session, without reminders, across
everything in `~/Documents/Projects-AI`.

**What the audit found.** 11 making-of files across about 28 projects. The rule itself
sat in only three `CLAUDE.md` files (Social, the Empty Folder website, Hawaiian Rummy).
Pipedia, the oldest and longest making-of (44 acts), had no mention of it in its own
`CLAUDE.md`. 14 projects had no making-of at all. There was no `CLAUDE.md` in the
workspace root, so a session started there or in most projects never saw the rule.

**WRONG THEORY: a Stop hook that echoes a reminder enforces the rule.** It doesn't. A
Stop hook's ordinary output is not shown to Claude; only `{"decision": "block",
"reason": ...}` reaches the model. The README had recommended the echo since August.
Replaced by `hooks/making-of-stop.py`, which reads the transcript and blocks once per
batch of unrecorded changes.

**Decided:**
- The block goes into the parent folder's `CLAUDE.md`, once. Claude Code reads every
  `CLAUDE.md` up the tree, so new projects inherit it. Per-project copies had already
  drifted.
- The hook goes in user settings, not project settings: project `.claude/settings.json`
  is not read from parent folders, so a project-level hook at the workspace root would
  miss every session started in a sub-folder.
- The hook blocks rather than nags each turn: once per set of changes, and
  `stop_hook_active` lets the answered turn finish. A trivial change gets a one-line
  "No making-of entry:" instead of an invented entry.
- Company and third-party repositories get their making-of in the wrapper folder.

**Tested.** Nine pipe tests against synthetic transcripts, all as expected: edit with no
entry blocks; same state again is silent; `stop_hook_active` is silent; edit then entry
is silent; entry then a new edit blocks; edits outside `--root` or under `.claude/` and
`/tmp` are silent; read-only Bash (`2>/dev/null`, `2>&1`) is silent; `git -C … commit`
blocks; a new edit after an earlier block blocks again; garbage stdin exits 0.

**Assumed, not verified:** the transcript layout (`type: assistant`, `message.content[]`
with `tool_use` blocks, a `cwd` per entry). The session that built this could not read a
real transcript from inside its sandbox. The first real session after installing the hook
is the test.

**Wrong turns in the session itself:**
- Three cross-references written into the new seed files pointed at passages that don't
  exist (the brand's vendoring "explained" in the root making-of; Social's making-of
  "covering" `DESIGN.md`; Sharks briefs with no location). Caught by grepping each one
  before finishing; rewritten to point at `INDEX.md` and `docs/IMPROVEMENT_PLAN.md`.
- The workspace rules first said every act "ends in a lesson line". Pipedia has 15
  lesson lines across 44 acts. Corrected to name which files use it.
- Cloning this repo into the workspace failed: the session's sandbox refuses writes to
  any `.git/config` and `.git/hooks/`. The work was committed in a scratch clone, and
  Davin pushes it and clones it into `apps/making-of/`.

## Session 3 — 8 Oct 2026: an installer, because "add this to settings.json" wasn't enough

Session 2 ended by telling Davin to paste a `Stop` entry "into the `hooks` section" of
`~/.claude/settings.json`. There was no `hooks` section: the file had never had a hook. An
instruction to merge JSON by hand, into a file the instructions never showed, is a step
for the person to get wrong.

Also caught: the clone into `apps/making-of/` came out on `main` without the new work,
because session 2 pushed a branch and the steps said to clone without saying to merge.
Fixed with a fast-forward of the local `main`; it still needs a push.

Added `hooks/install-hook.py`: loads the settings, adds the hook under `hooks.Stop`, keeps
every other key, backs the file up, and refuses to touch invalid JSON. Tested on scratch
files, all as expected: existing keys (`model`, `permissions`, a `PostToolUse` hook)
kept; second run reports "Already installed" and writes nothing; missing file created;
`{oops` left unchanged with exit 1; the installed command runs and exits 0.

## Session 4 — 15 Oct 2026: `lessons_digest.py`, because a manual pass mis-cited six acts

The workspace's first "learn from past sessions" pass (15 Oct, done by hand in another
session) read 26 making-ofs, grepped for `The lesson` / `WRONG THEORY` / `Correction to`,
and mapped grep line numbers to act numbers by eye. Six citations came out wrong (root
"Act 7" was Act 11; three Social acts were off). The fix is mechanical, so it's now a
script: `lessons_digest.py`. Standard library only, no network, no model.

**Where it lives.** It went here, in a public repo, only because nothing in it is about one
workspace: the root folder, output folder, signature file and rule files are all
arguments, and the markers it knows are the ones this README already documents. A grep
for workspace names in the script finds none. The digests it writes, which quote private
making-ofs, go to the caller's output folder, never here.

**How passages are found.** Section = nearest `##` heading above the line, parsed outside
code fences, never a line number. A marker counts only at the start of a line, list item
or sentence, or in bold: "the lesson lived" and "a wrong theory cheaper than a right one"
in running prose don't count. Text before the first `##` (a file's preamble describing the
convention) is skipped. Headings with no number (`Still open`, Pipedia's `Work: …`,
Nagi's `Change log`) are quoted with the last numbered heading before them, rather than
attributed to that heading, which is the error the hand pass made.

**Checked against the hand pass (verified, run on the real files).** 154 passages from the
26 files: 91 lessons, 38 wrong theories, 25 corrections, in 12 files (14 have none). Every
act number the 15 Oct report cites came out the same: root Acts 1, 9, 10, 11, 12; Social
4, 5, 9, 11, 12, 13, 15, 19, 21, 22, 24, 26, 27; Pipedia 2 and 45. Sample lines were also
mapped with an independent `awk` pass (website L4821 → Session 39, L5195 → Session 44,
L1746 → Session 16; Bus Tourist L791 and L1664 → Session 1; Pipedia L4768 → Act 44;
Nagi L857 → D-015, L1916 → Change log); all agreed. Two runs give byte-identical output
(`cmp`). A run dated 15 Nov against today's digest reports "Nothing new", by passage id.

**WRONG THEORY: a section with no dated heading can borrow the first date in its text.**
First run dated Pipedia Act 44 "19 Feb 2027": a date the text mentions as a future plan.
Now the fallback takes the latest date in the text that lies between the dates of the
sections around it and no later than today, and the digest marks it `~`. Social Act 21
shows why even that is a judgement: "Written 2026-08-30 … recovered 2026-09-30". The
script picks 30 Sep, the day it reached the file, which is what "new since the last
digest" needs. 31 passages remain `n.d.` (early Social and Pipedia acts with no date
anywhere usable); the manifest, not the date, decides what is new.

**Two smaller misses on the first run.** Lessons ending in a colon ("The lesson is in what
the obvious version of it broke:") stopped at the colon; the block after a colon is now
included. Nagi's change-log entries sit under one `## Change log` heading, so their date
comes from the bold date that starts each list item, not the heading.

**The evidence table found something on its first run.** With the 15 Oct report's counts
as `learnings/signatures-2026-10-15.txt` and `--rules` on the root `CLAUDE.md` and
`TOOLS.md`, the Rules column shows `no matches found` and `Operation not permitted` are now
in `CLAUDE.md`: proposal P1 had been adopted between the report and this run. Nobody had
to remember to check.

**A zsh trap, second sighting.** `echo ======` in this session failed with
`(eval):1: ===== not found`, the trap the 15 Oct report held back with one sighting.
Also: importing the script to test the parser wrote `__pycache__/` into this repo despite
`-I`; `-I` doesn't stop bytecode writes. Removed; use `-B` for that.

Not done: nothing committed or pushed (left for Davin). The digest
(`learnings/lessons-2026-10-15.md`) and signature file are outside this repo. Assumed, not
tested: the signature parser on a real paste from the app's search; it was tested on a
table, tab-separated, `count query` and `query ≥40` lines, and skips a line with no count.

## Session 5 — 15 Oct 2026: the sweep joins the kit (collect, review, adopt)

Davin asked for a review of this repo and for the lessons step to live here, "so we collect
and then review as part of the repo workflow". Until now the kit wrote making-ofs and, since
Session 4, collected them (`lessons_digest.py`); the review lived only in his workspace, as a
scheduled task prompt full of his own paths.

**Review findings.** Session 4's script, README §4 and entry were uncommitted and consistent.
The script has no private names or paths (grepped for the workspace's names and `/Users/`).
The README intro still said "Three pieces". There was no `.gitignore`, though Session 4 had
already had `__pycache__/` written into the repo once. `.claude/` holds only the harness's
empty `.cc-writes`, untracked.

**Added.** `skills/lessons-sweep/SKILL.md`: a generic version of that workspace's sweep. Every
path (projects root, learnings folder, rule files, the script) is an input, and the learnings
folder must not be a public repo, because digests quote private making-ofs. Three stages:
collect (optional signature re-count from a transcript search, then the digest), review (gate:
learned independently in 3+ projects or sessions *and* not already in a rule file, read in
full, at most 4 proposals, citations checked against the digest), adopt (only proposals the
user names, applied verbatim, checked by script, recorded in the report). It also checks
whether earlier rules cut their error counts, and proposes a hook if not. The README now
lists five pieces and has §5 with the install command (`cp -R skills/lessons-sweep
~/.claude/skills/lessons-sweep`). `.gitignore`: `__pycache__/`, `*.pyc`, `.claude/`.

**Kept clear of the skill-loader trap.** A sibling skill in the same workspace showed today
that the loader replaces `$0` in SKILL.md text with the first argument ("$0.06/hour" came out
as a URL). The new SKILL.md and README have no `$` followed by a digit and no `$ARGUMENTS`
(grepped).

**Tested (verified).** The skill's collect command, run exactly as written against the real
workspace with `--stdout`: exit 0, 156 passages (154 this morning; today's two new wrong
theories), evidence table intact. The run also confirmed why the gate says to read rule files
rather than trust the digest: `I told you` shows Rules "none", though a rule adopted today
covers it in other words. **Not tested:** a full sweep through the skill (review and adopt),
and installing it from this repo. The workspace's scheduled task still carries its own prompt.

**Wrong turn, a small one.** Checking `.claude/` with `git check-ignore -v $R/.claude/*`
failed with zsh's `no matches found`, the unquoted-glob failure the workspace's rules gained
a line about this morning, and the one the new skill warns about too.

Not done: nothing committed or pushed.
