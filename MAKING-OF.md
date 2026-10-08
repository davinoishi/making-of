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
