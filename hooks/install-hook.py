#!/usr/bin/env python3
"""Add the making-of Stop hook to ~/.claude/settings.json.

    python3 hooks/install-hook.py [--root ~/path/to/projects ...]

Keeps everything already in the file, backs it up first, and does nothing if the
hook is already there. Without --root the hook applies to every project.
"""
import argparse
import json
import os
import shutil
import sys
import time

HOOK = os.path.join(os.path.dirname(os.path.realpath(__file__)), "making-of-stop.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", action="append", default=[])
    ap.add_argument("--settings", default="~/.claude/settings.json")
    args = ap.parse_args()
    path = os.path.expanduser(args.settings)

    settings = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                settings = json.load(f)
        except ValueError as e:
            sys.exit(f"{path} is not valid JSON ({e}). Nothing changed.")

    stops = settings.setdefault("hooks", {}).setdefault("Stop", [])
    for group in stops:
        for h in group.get("hooks", []):
            if "making-of-stop.py" in h.get("command", ""):
                print(f"Already installed in {path}:\n  {h['command']}")
                return

    command = f'python3 "{HOOK}"'
    for r in args.root:
        command += f' --root "{os.path.realpath(os.path.expanduser(r))}"'
    stops.append({"hooks": [{"type": "command", "command": command, "timeout": 10}]})

    if os.path.exists(path):
        backup = f"{path}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
        shutil.copy2(path, backup)
        print(f"Backed up {path} to {backup}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")
    print(f"Added the making-of Stop hook to {path}:\n  {command}")
    print("It applies to sessions started from now on.")


if __name__ == "__main__":
    main()
