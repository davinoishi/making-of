# making-of
It is the running story of the project — what got decided, what got tested, and what turned out to be wrong.

Two pieces: a CLAUDE.md block (the durable part — it persists across every session, unlike a prompt) and a seed file.
1. Paste into the project's CLAUDE.md

```
## MAKING-OF.md

This project keeps a `MAKING-OF.md` next to the README. It is the running story of
the project — what got decided, what got tested, and what turned out to be wrong.

- **Append, never rewrite.** New dated `## Session N — <date>` section at the bottom.
  Never edit or tidy earlier sessions. If a past conclusion was wrong, add a
  "Correction to session N" subsection saying so — leave the original in place.
- **The point of the file is the wrong turns.** Bad cost estimates, misread API
  responses, theories that got disproved, instructions that didn't work. A session
  entry that only records the clean final answer is a failed entry. Keep superseded
  theories under a `WRONG THEORY:` heading rather than deleting them.
- **Receipts.** Include the actual numbers, commands, error text, and file paths.
- **Say what was verified vs. assumed.** Mark anything not actually run as assumed.
- **Update it at the end of every working session**, before wrapping up — not only
  when asked. README says where things landed; this says how and why, so a decision
  doesn't get re-litigated in six months because nobody remembers the reasoning.
```

2. Seed MAKING-OF.md with this header

```
# Making of <project>

The running story of this project — what got decided, what got tested, and what turned
out to be wrong. Appended to after every session. Newest session at the bottom.

The point of this file is the wrong turns. Anyone can read README.md and see where
things landed; this is the record of how, so a decision doesn't get re-litigated in six
months because nobody remembers why it went the way it did.
```

Why the seed file matters: an empty convention gets ignored, but a file that already exists with a shape gets appended to.

3. If they want it enforced rather than remembered
CLAUDE.md is a strong nudge, not a guarantee — a long session can end without the append. A Stop hook in .claude/settings.json makes it mechanical:

```
claude config  # not available here — edit .claude/settings.json directly
```

Add a Stop hook that echoes a reminder to update MAKING-OF.md before the session closes. I can wire that up for one of your projects as a reference implementation if you want something to hand them.

The one-line version for a kickoff prompt, if a coworker won't set up CLAUDE.md: "Create a MAKING-OF.md and append a dated session entry to it at the end of every session — record the wrong turns and disproved theories with receipts, not just the final answer, and never rewrite earlier entries."
