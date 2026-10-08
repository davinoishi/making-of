#!/usr/bin/env python3
"""Claude Code Stop hook: don't let a turn end with unrecorded changes.

Reads the session transcript. If files were changed after the session's last
write to a MAKING-OF.md, it blocks the stop once and tells Claude to append an
entry (or to say in one line why none is needed). It blocks again only if more
changes happen after that, so a turn that already answered is never nagged twice.

Usage in settings.json (user level, so it covers sessions started in any
sub-folder):

    "hooks": {"Stop": [{"hooks": [{"type": "command",
        "command": "python3 /path/to/making-of-stop.py --root ~/Documents/Projects-AI"}]}]}

--root limits it to changes under one folder; repeat it for several. Without
--root it applies everywhere. It never fails a session: any error exits 0.
"""
import argparse
import json
import os
import re
import sys
import tempfile

WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
MAKING_OF = re.compile(r"making-of\.md", re.I)
# Bash commands that change files. Deliberately narrow: a false positive costs
# one extra turn, a false negative costs a lost entry, and most edits go
# through the Edit and Write tools anyway.
BASH_WRITE = re.compile(
    r"\bgit\s+(?:-C\s+\S+\s+)?commit\b"
    r"|\bsed\s+-i\b"
    r"|\btee\b"
    r"|(?<![0-9&>])>{1,2}\s*(?!/dev/null|&)[\w~./\"'$-]"
)
IGNORED_PARTS = ("/.claude/", "/tmp/", "/private/tmp/", "/private/var/", "/.git/")

REASON = (
    "MAKING-OF check: this session changed files ({where}) after its last "
    "MAKING-OF.md entry. Before you finish, append to the MAKING-OF.md of each "
    "project you touched, following the rules in the nearest CLAUDE.md: a new "
    "dated entry at the bottom, or extend this session's entry if it already "
    "has one. Record what was decided, what was tested, and what turned out "
    "wrong, with receipts. If the change was trivial (a typo, formatting, a "
    "path fix) or the work is a read-only answer, reply with one line starting "
    "'No making-of entry:' and the reason instead. Do not invent wrong turns."
)


def under(path, roots):
    if not roots:
        return True
    path = os.path.realpath(os.path.expanduser(path))
    return any(path == r or path.startswith(r + os.sep) for r in roots)


def ignored(path):
    p = os.path.realpath(os.path.expanduser(path)) + "/"
    return any(part in p for part in IGNORED_PARTS)


def events(transcript_path, cwd, roots):
    """Yield ('change', where) or ('makingof', path) in transcript order."""
    with open(transcript_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if entry.get("type") != "assistant":
                continue
            content = (entry.get("message") or {}).get("content") or []
            if not isinstance(content, list):
                continue
            here = entry.get("cwd") or cwd
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name, inp = block.get("name"), block.get("input") or {}
                if name in WRITE_TOOLS:
                    path = inp.get("file_path") or inp.get("notebook_path") or ""
                    if not path:
                        continue
                    if not os.path.isabs(path):
                        path = os.path.join(here or "", path)
                    if MAKING_OF.search(os.path.basename(path)):
                        yield "makingof", path
                    elif under(path, roots) and not ignored(path):
                        yield "change", os.path.dirname(path)
                elif name == "Bash":
                    cmd = inp.get("command") or ""
                    if not BASH_WRITE.search(cmd):
                        continue
                    if MAKING_OF.search(cmd):
                        yield "makingof", cmd
                    elif here and under(here, roots) and not ignored(here):
                        yield "change", here


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", action="append", default=[])
    args = ap.parse_args()
    roots = [os.path.realpath(os.path.expanduser(r)) for r in args.root]

    data = json.load(sys.stdin)
    if data.get("stop_hook_active"):
        return  # we already blocked once this turn; let it finish
    transcript = data.get("transcript_path")
    if not transcript or not os.path.exists(transcript):
        return

    count, last_mo, where = 0, -1, []
    for i, (kind, value) in enumerate(events(transcript, data.get("cwd"), roots)):
        if kind == "makingof":
            last_mo = i
            where = []
        else:
            count = i
            if value not in where:
                where.append(value)
    if not where or count < last_mo:
        return  # nothing changed since the last entry

    # Block once per set of changes: remember the last change index we blocked on.
    state_dir = os.path.join(tempfile.gettempdir(), "making-of-hook")
    os.makedirs(state_dir, exist_ok=True)
    state = os.path.join(state_dir, re.sub(r"[^\w-]", "_", data.get("session_id", "x")))
    try:
        with open(state) as f:
            if int(f.read().strip() or -1) >= count:
                return
    except (OSError, ValueError):
        pass
    with open(state, "w") as f:
        f.write(str(count))

    home = os.path.expanduser("~")
    shown = ", ".join(w.replace(home, "~") for w in where[:5])
    if len(where) > 5:
        shown += f" and {len(where) - 5} more"
    print(json.dumps({"decision": "block", "reason": REASON.format(where=shown)}))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # a broken reminder must never break a session
        pass
    sys.exit(0)
